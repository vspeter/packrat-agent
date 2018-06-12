import rpm  # from python3-rpm
import os
import hashlib
import stat
import struct
from xml.sax import saxutils
from operator import itemgetter


_share_data_store = {}


def share_data(value):
    """ Take a value and use the same value from the store,
        if the value isn't in the store this one becomes the shared version. """
    if isinstance( value, tuple):
        return value
    return _share_data_store.setdefault(value, value)


def hdrFromPackage(ts, package):
    """hand back the rpm header or raise an Error if the pkg is fubar"""
    try:
        fdno = os.open(package, os.O_RDONLY)
    except OSError:
        raise Exception('Unable to open file')

    try:
        hdr = ts.hdrFromFdno(fdno)
    except rpm.error:
        os.close(fdno)
        raise Exception("RPM Error opening Package")

    if type(hdr) != rpm.hdr:
        os.close(fdno)
        raise Exception("RPM Error opening Package (type)")

    os.close(fdno)
    return hdr


def to_xml(item, attrib=False):
    item = item.rstrip()
    if attrib:
        item = saxutils.escape(item, entities={'"': "&quot;"})
    else:
        item = saxutils.escape(item)
    return item


def re_primary_filename(filename):
    """ Tests if a filename string, can be matched against just primary.
        Note that this can produce false negatives (but not false
        positives). Note that this is a superset of re_primary_dirname(). """
    if re_primary_dirname(filename):
        return True
    if filename == '/usr/lib/sendmail':
        return True
    return False


def re_primary_dirname(dirname):
    """ Tests if a dirname string, can be matched against just primary. Note
        that this is a subset of re_primary_filename(). """
    if 'bin/' in dirname:
        return True
    if dirname.startswith('/etc/'):
        return True
    return False


def decode_value( value ):
  if isinstance( value, bytes ):
    return value.decode()

  if isinstance( value, list ):
    return [ decode_value( i ) for i in value ]

  return value


def flagToString(flags):
    flags = flags & 0xf

    if flags == 0:
        return None
    elif flags == 2:
        return 'LT'
    elif flags == 4:
        return 'GT'
    elif flags == 8:
        return 'EQ'
    elif flags == 10:
        return 'LE'
    elif flags == 12:
        return 'GE'

    return flags


def stringToVersion(verstring):
    if verstring in [None, '']:
        return (None, None, None)
    i = verstring.find(':')
    if i != -1:
        try:
            epoch = str(int(verstring[:i]))
        except ValueError:
            # look, garbage in the epoch field, how fun, kill it
            epoch = '0'  # this is our fallback, deal
    else:
        epoch = '0'
    j = verstring.find('-')
    if j != -1:
        if verstring[i + 1:j] == '':
            version = None
        else:
            version = verstring[i + 1:j]
        release = verstring[j + 1:]
    else:
        if verstring[i + 1:] == '':
            version = None
        else:
            version = verstring[i + 1:]
        release = None
    return (epoch, version, release)


def compareEVR(xxx_todo_changeme, xxx_todo_changeme1):
    # return 1: a is newer than b
    # 0: a and b are the same version
    # -1: b is newer than a
    (e1, v1, r1) = xxx_todo_changeme
    (e2, v2, r2) = xxx_todo_changeme1
    if e1 is None:
        e1 = '0'
    else:
        e1 = str(e1)
    v1 = str(v1)
    r1 = str(r1)
    if e2 is None:
        e2 = '0'
    else:
        e2 = str(e2)
    v2 = str(v2)
    r2 = str(r2)
    rc = rpm.labelCompare((e1, v1, r1), (e2, v2, r2))
    return rc


def compareVerOnly(v1, v2):
    """compare version strings only using rpm vercmp"""
    return compareEVR(('', v1, ''), ('', v2, ''))


class PackageObject(object):
    """Base Package Object - sets up the default storage dicts and the
       most common returns"""

    def __init__(self):
        self.name = None
        self.version = None
        self.release = None
        self.epoch = None
        self.arch = None


# see: YumAvailablePackage.
class RpmBase(object):
    """return functions and storage for rpm-specific data"""

    def __init__(self):
        self.prco = {}
        self.prco['obsoletes'] = []  # (name, flag, (e,v,r))
        self.prco['conflicts'] = []  # (name, flag, (e,v,r))
        self.prco['requires'] = []  # (name, flag, (e,v,r))
        self.prco['provides'] = []  # (name, flag, (e,v,r))
        self.files = {}
        self.files['file'] = []
        self.files['dir'] = []
        self.files['ghost'] = []
        self.licenses = []
        self._hash = None


class YumAvailablePackage(PackageObject, RpmBase):
    """derived class for the  packageobject and RpmBase packageobject yum
       uses this for dealing with packages in a repository"""

    def __init__(self):
        PackageObject.__init__(self)
        RpmBase.__init__(self)
        self.state = None
        self._loadedfiles = False
        self._verify_local_pkg_cache = None
        self._checksum = None
        self.pkgtup = (self.name, self.arch, self.epoch, self.version, self.release)


#  This is a tweak on YumAvailablePackage() and is a base class for packages
# which are actual rpms.
class YumHeaderPackage(YumAvailablePackage):
    """Package object built from an rpm header"""
    def __init__(self, hdr):
        """hand in an rpm header, we'll assume it's installed and query from there"""

        YumAvailablePackage.__init__(self)

        self.hdr = hdr
        self.name = share_data( self.hdr['name'].decode() )
        this_a = self.hdr['arch'].decode()
        if not this_a:  # this should only happen on gpgkeys and other "odd" pkgs
            this_a = 'noarch'
        self.arch = share_data( this_a )
        self.epoch = share_data( self.doepoch() )
        self.version = share_data( self.hdr['version'].decode() )
        self.release = share_data( self.hdr['release'].decode() )
        self.ver = self.version
        self.rel = self.release
        self.pkgtup = (self.name, self.arch, self.epoch, self.version, self.release)
        self._loaded_summary = None
        self._loaded_description = None
        self.pkgid = self.hdr[rpm.RPMTAG_SHA1HEADER].decode()
        if not self.pkgid:
            self.pkgid = "{0}.{1}".format(self.hdr['name'].decode(), self.hdr['buildtime'].decode())
        self.packagesize = self.hdr['size']
        self._mode_cache = {}
        self._prcoPopulated = False

    def doepoch(self):
        tmpepoch = self.hdr['epoch']
        if tmpepoch is None:
            epoch = '0'
        else:
            epoch = str(tmpepoch)

        return epoch

    def __getattr__(self, thing):
        print( '----{0}----'.format(  thing ))
        # FIXME - if an error - return AttributeError, not KeyError
        # ONLY FIX THIS AFTER THE API BREAK
        if thing.startswith('__') and thing.endswith('__'):
            # If these existed, then we wouldn't get here ...
            # So these are missing.
            raise AttributeError("{0} has no attribute {1}".format(self, thing))
        try:
            return decode_value( self.hdr[thing] )

        except KeyError:
            raise KeyError("{0} has no attribute {1}".format(self, thing))
        except ValueError as e:
          if e.args[0] == 'unknown header tag':
            raise AttributeError("{0} has no attribute {1}".format(self, thing))
          else:
            raise e


class YumLocalPackage(YumHeaderPackage):
    """Class to handle an arbitrary package from a file path
       this inherits most things from YumInstalledPackage because
       installed packages and an arbitrary package on disk act very
       much alike. init takes a ts instance and a filename/path
       to the package."""

    def __init__(self, filename, relpath):
        print( 'Loading "{0}"...'.format(filename))
        self.pkgtype = 'local'
        self.localpath = filename

        try:
            ts = rpm.TransactionSet('/')
            ts.setVSFlags(rpm._RPMVSF_NOSIGNATURES | rpm._RPMVSF_NODIGESTS)
            hdr = hdrFromPackage(ts, self.localpath)
        except Exception as e:
            raise Exception('Could not open local rpm file: {0}: {1}'.format(self.localpath, e))

        YumHeaderPackage.__init__(self, hdr)

        self.id = self.pkgid
        self._stat = os.stat(self.localpath)
        self.filetime = str(self._stat[-2])
        self.packagesize = str(self._stat[6])
        self.arch = self.isSrpm()
        self.pkgtup = (self.name, self.arch, self.epoch, self.ver, self.rel)
        self._hdrstart = None
        self._hdrend = None
        self.checksum_type = 'sha256'
        self.relpath = relpath

    def isSrpm(self):
        if self.sourcepackage == 1 or not self.sourcerpm:
            return 'src'
        else:
            return self.arch

    @property
    def checksum( self ):
      if self._checksum is not None:
        return self._checksum

      sha256 = hashlib.sha256()
      wrk = open( self.localpath, 'rb' )
      buff = wrk.read( 4096 )
      while buff:
        sha256.update( buff )
        buff = wrk.read( 4096 )

      self._checksum = sha256.hexdigest()
      return self._checksum

    @property
    def changelog(self):
        if len(self.hdr['changelogname']) > 0:
            return list( zip(decode_value( self.hdr['changelogtime'] ), decode_value( self.hdr['changelogname'] ), decode_value( self.hdr['changelogtext'] ) ) )
        return []

    def _get_header_byte_range(self):
        """takes an rpm file or fileobject and returns byteranges for location of the header"""
        if self._hdrstart and self._hdrend:
            return (self._hdrstart, self._hdrend)

        fo = open(self.localpath, 'rb')
        # read in past lead and first 8 bytes of sig header
        fo.seek(104)
        # 104 bytes in
        binindex = fo.read(4)
        # 108 bytes in
        (sigindex, ) = struct.unpack('>I', binindex)
        bindata = fo.read(4)
        # 112 bytes in
        (sigdata, ) = struct.unpack('>I', bindata)
        # each index is 4 32bit segments - so each is 16 bytes
        sigindexsize = sigindex * 16
        sigsize = sigdata + sigindexsize
        # we have to round off to the next 8 byte boundary
        disttoboundary = (sigsize % 8)
        if disttoboundary != 0:
            disttoboundary = 8 - disttoboundary
        # 112 bytes - 96 == lead, 8 = magic and reserved, 8 == sig header data
        hdrstart = 112 + sigsize + disttoboundary

        fo.seek(hdrstart)  # go to the start of the header
        fo.seek(8, 1)  # read past the magic number and reserved bytes

        binindex = fo.read(4)
        (hdrindex, ) = struct.unpack('>I', binindex)
        bindata = fo.read(4)
        (hdrdata, ) = struct.unpack('>I', bindata)

        # each index is 4 32bit segments - so each is 16 bytes
        hdrindexsize = hdrindex * 16
        # add 16 to the hdrsize to account for the 16 bytes of misc data b/t the
        # end of the sig and the header.
        hdrsize = hdrdata + hdrindexsize + 16

        # header end is hdrstart + hdrsize
        hdrend = hdrstart + hdrsize
        fo.close()
        self._hdrstart = hdrstart
        self._hdrend = hdrend

        return (hdrstart, hdrend)

    hdrend = property(fget=lambda self: self._get_header_byte_range()[1])
    hdrstart = property(fget=lambda self: self._get_header_byte_range()[0])

    def _populatePrco(self):
        "Populate the package object with the needed PRCO interface."

        tag2prco = { "OBSOLETE": share_data("obsoletes"),
                     "CONFLICT": share_data("conflicts"),
                     "REQUIRE": share_data("requires"),
                     "PROVIDE": share_data("provides") }

        for tag in tag2prco:
            name = decode_value( self.hdr[getattr(rpm, 'RPMTAG_%sNAME' % tag)] )
            name = list(map(share_data, name))
            if not name:  # empty or none or whatever, doesn't matter
                continue

            lst = decode_value( self.hdr[getattr(rpm, 'RPMTAG_%sFLAGS' % tag)] )
            flag = list(map(flagToString, lst))
            flag = list(map(share_data, flag))

            lst = decode_value( self.hdr[getattr(rpm, 'RPMTAG_%sVERSION' % tag)] )
            vers = list(map(stringToVersion, lst))
            vers = [(share_data(x[0]), share_data(x[1]), share_data(x[2])) for x in vers]

            prcotype = tag2prco[tag]
            self.prco[prcotype] = list(map(share_data, list(zip(name, flag, vers))))

    def inPrcoRange(self, prcotype, reqtuple):
        """returns true if the package has a the prco that satisfies
           the reqtuple range, assume false.
           Takes: prcotype, requested prco tuple"""
        return bool(self.matchingPrcos(prcotype, reqtuple))

    def checkPrco(self, prcotype, prcotuple):
        """returns 1 or 0 if the pkg contains the requested tuple/tuple range"""
        # get rid of simple cases - nothing
        if prcotype not in self.prco:
            return 0

        # First try and exact match, then search
        # Make it faster, if it's "big".
        if len(self.prco[prcotype]) <= 8:
            if prcotuple in self.prco[prcotype]:
                return 1
        else:
            if not hasattr(self, '_prco_lookup'):
                self._prco_lookup = {'obsoletes': None, 'conflicts': None,
                                     'requires': None, 'provides': None}

            if self._prco_lookup[prcotype] is None:
                self._prco_lookup[prcotype] = set(self.prco[prcotype])

            if prcotuple in self._prco_lookup[prcotype]:
                return 1

        # make us look it up and compare
        (reqn, reqf, (reqe, reqv, reqr)) = prcotuple
        if reqf is not None:
            return self.inPrcoRange(prcotype, prcotuple)
        else:
            for (n, f, (e, v, r)) in self.returnPrco(prcotype):
                if reqn.encode() == n.encode():
                    return 1

        return 0

    def returnPrco(self, prcotype, printable=False):
        """return list of provides, requires, conflicts or obsoletes"""
        if not self._prcoPopulated:
            self._populatePrco()
            self._prcoPopulated = True

        return self.prco.get(prcotype, [])

    def returnPrcoNames(self, prcotype):
        if not hasattr(self, '_cache_prco_names_' + prcotype):
            data = [n for (n, f, v) in self.returnPrco(prcotype)]
            setattr(self, '_cache_prco_names_' + prcotype, data)
        return getattr(self, '_cache_prco_names_' + prcotype)

    requires = property(fget=lambda self: self.returnPrco('requires'))
    provides = property(fget=lambda self: self.returnPrco('provides'))
    obsoletes = property(fget=lambda self: self.returnPrco('obsoletes'))
    conflicts = property(fget=lambda self: self.returnPrco('conflicts'))
    provides_names = property(fget=lambda self: self.returnPrcoNames('provides'))
    requires_names = property(fget=lambda self: self.returnPrcoNames('requires'))
    conflicts_names = property(fget=lambda self: self.returnPrcoNames('conflicts'))
    obsoletes_names = property(fget=lambda self: self.returnPrcoNames('obsoletes'))

    def _loadFiles(self):
        files = decode_value( self.hdr['filenames'] )
        fileflags = decode_value( self.hdr['fileflags'] )
        filemodes = decode_value( self.hdr['filemodes'] )
        filetuple = list(zip(files, filemodes, fileflags))
        if not self._loadedfiles:
            for (fn, mode, flag) in filetuple:
                # garbage checks
                if mode is None or mode == '':
                    if 'file' not in self.files:
                        self.files['file'] = []
                    self.files['file'].append(fn)
                    continue
                if mode not in self._mode_cache:
                    self._mode_cache[mode] = stat.S_ISDIR(mode)

                fkey = 'file'
                if self._mode_cache[mode]:
                    fkey = 'dir'
                elif flag is not None and (flag & 64):
                    fkey = 'ghost'
                self.files.setdefault(fkey, []).append(fn)

            self._loadedfiles = True

    def returnFileEntries(self, ftype='file', primary_only=False):
        """return list of files based on type, you can pass primary_only=True
           to limit to those files in the primary repodata"""
        self._loadFiles()

        if self.files:
            if ftype in self.files:
                if primary_only:
                    if ftype == 'dir':
                        match = re_primary_dirname
                    else:
                        match = re_primary_filename
                    return [fn for fn in self.files[ftype] if match(fn)]
                return self.files[ftype]
        return []

    filelist = property(fget=lambda self: self.returnFileEntries(ftype='file'))
    dirlist = property(fget=lambda self: self.returnFileEntries(ftype='dir'))
    ghostlist = property(fget=lambda self: self.returnFileEntries(ftype='ghost'))

    def _is_pre_req(self, flag):
        """check the flags for a requirement, return 1 or 0 whether or not requires
           is a pre-requires or a not"""
        # FIXME this should probably be put in rpmUtils.miscutils since
        # - that's what it is
        if flag is not None:
            # Note: RPMSENSE_PREREQ == 0 since rpm-4.4'ish
            if flag & (rpm.RPMSENSE_PREREQ |
                       rpm.RPMSENSE_SCRIPT_PRE |
                       rpm.RPMSENSE_SCRIPT_POST):
                return 1
        return 0

    def _requires_with_pre(self):
        """returns requires with pre-require bit"""
        name = decode_value( self.hdr[rpm.RPMTAG_REQUIRENAME] )
        lst = decode_value( self.hdr[rpm.RPMTAG_REQUIREFLAGS] )
        flag = list(map(flagToString, lst))
        pre = list(map(self._is_pre_req, lst))
        lst = decode_value( self.hdr[rpm.RPMTAG_REQUIREVERSION] )
        vers = list(map(stringToVersion, lst))
        if name is not None:
            lst = list(zip(name, flag, vers, pre))
        mylist = list(set(lst))
        return mylist

    def _dump_base_items(self):
        packager = url = ''
        if self.packager:
            packager = to_xml(self.packager)

        if self.url:
            url = to_xml(self.url)

        msg = """
  <name>{0}</name>
  <arch>{1}</arch>
  <version epoch="{2}" ver="{3}" rel="{4}"/>
  <checksum type="{5}" pkgid="YES">{6}</checksum>
  <summary>{7}</summary>
  <description>{8}</description>
  <packager>{9}</packager>
  <url>{10}</url>
  <time file="{11}" build="{12}"/>
  <size package="{13}" installed="{14}" archive="{15}"/>\n""".format(self.name, self.arch, self.epoch, self.ver, self.rel, 'sha256', self.checksum, to_xml(self.summary), to_xml(self.description), packager, url, self.filetime, self.buildtime, self.packagesize, self.size, self.archivesize)

        msg += """<location href="{0}"/>\n""".format( to_xml(self.relpath, attrib=True) )
        return msg

    def _dump_format_items(self):
        msg = "  <format>\n"
        if self.license:
            msg += """    <rpm:license>{0}</rpm:license>\n""".format( to_xml(self.license) )
        else:
            msg += """    <rpm:license/>\n"""

        if self.vendor:
            msg += """    <rpm:vendor>{0}</rpm:vendor>\n""".format( to_xml(self.vendor) )
        else:
            msg += """    <rpm:vendor/>\n"""

        if self.group:
            msg += """    <rpm:group>{0}</rpm:group>\n""".format( to_xml(self.group) )
        else:
            msg += """    <rpm:group/>\n"""

        if self.buildhost:
            msg += """    <rpm:buildhost>{0}</rpm:buildhost>\n""".format( to_xml(self.buildhost) )
        else:
            msg += """    <rpm:buildhost/>\n"""

        if self.sourcerpm:
            msg += """    <rpm:sourcerpm>{0}</rpm:sourcerpm>\n""".format( to_xml(self.sourcerpm) )
        else:  # b/c yum 2.4.3 and OLD y-m-p willgfreak out if it is not there.
            msg += """    <rpm:sourcerpm/>\n"""

        msg += """    <rpm:header-range start="{0}" end="{1}"/>""".format( self.hdrstart, self.hdrend)
        msg += self._dump_pco('provides')
        msg += self._dump_requires()
        msg += self._dump_pco('conflicts')
        msg += self._dump_pco('obsoletes')
        msg += self._dump_files(True)
        if msg[-1] != '\n':
            msg += """\n"""
        msg += """  </format>"""

        return msg

    def _dump_pco(self, pcotype):
        msg = ""
        mylist = getattr(self, pcotype)
        if mylist:
          msg = "\n    <rpm:{0}>\n".format( pcotype )
        for (name, flags, (e, v, r)) in mylist:
            pcostring = '''      <rpm:entry name="{0}"'''.format( to_xml(name, attrib=True) )
            if flags:
                pcostring += ''' flags="{0}"'''.format( to_xml(flags, attrib=True) )
                if e:
                    pcostring += ''' epoch="{0}"'''.format( to_xml(e, attrib=True) )
                if v:
                    pcostring += ''' ver="{0}"'''.format( to_xml(v, attrib=True) )
                if r:
                    pcostring += ''' rel="{0}"'''.format( to_xml(r, attrib=True) )

            pcostring += "/>\n"
            msg += pcostring

        if mylist:
          msg += "    </rpm:{0}>".format( pcotype )
        return msg

    def _dump_requires(self):
        """returns deps in XML format"""
        mylist = self._requires_with_pre()

        msg = ""

        if mylist:
          msg = "\n    <rpm:requires>\n"

        if getattr(self, '_collapse_libc_requires', False):
            libc_requires = [x for x in mylist if x[0].startswith('libc.so.6')]
            if libc_requires:
                rest = sorted(libc_requires, cmp=compareVerOnly, key=itemgetter(0))
                best = rest.pop()
                if len(rest) > 0 and best[0].startswith('libc.so.6()'):  # rpmvercmp will sort this one as 'highest' so we need to remove it from the list
                    best = rest.pop()
                newlist = []
                for i in mylist:
                    if i[0].startswith('libc.so.6') and i != best:
                        continue
                    newlist.append(i)
                mylist = newlist

        for (name, flags, (e, v, r), pre) in mylist:
            if name.startswith('rpmlib('):
                continue
            # this drops out requires that the pkg provides for itself.
            if name in self.provides_names or (name.startswith('/') and (name in self.filelist or name in self.dirlist or name in self.ghostlist)):
                if not flags:
                    continue
                else:
                    if self.checkPrco('provides', (name, flags, (e, v, r))):
                        continue
            prcostring = '''      <rpm:entry name="{0}"'''.format( to_xml(name, attrib=True) )
            if flags:
                prcostring += ''' flags="{0}"'''.format( to_xml(flags, attrib=True) )
                if e:
                    prcostring += ''' epoch={0}'''.format( to_xml(e, attrib=True) )
                if v:
                    prcostring += ''' ver="{0}"'''.format( to_xml(v, attrib=True) )
                if r:
                    prcostring += ''' rel="{0}"'''.format( to_xml(r, attrib=True) )
            if pre:
                prcostring += ''' pre="{0}"'''.format( pre )

            prcostring += "/>\n"
            msg += prcostring

        if mylist:
          msg += "    </rpm:requires>"
        return msg

    def _dump_files(self, primary=False):
        msg = "\n"
        if not primary:
            files = self.returnFileEntries('file')
            dirs = self.returnFileEntries('dir')
            ghosts = self.returnFileEntries('ghost')
        else:
            files = self.returnFileEntries('file', primary_only=True)
            dirs = self.returnFileEntries('dir', primary_only=True)
            ghosts = self.returnFileEntries('ghost', primary_only=True)

        for fn in files:
            msg += """    <file>{0}</file>\n""".format( to_xml(fn) )
        for fn in dirs:
            msg += """    <file type="dir">{0}</file>\n""".format( to_xml(fn) )
        for fn in ghosts:
            msg += """    <file type="ghost">{0}</file>\n""".format( to_xml(fn) )

        return msg

    def _dump_changelog(self, clog_limit):
        if not self.changelog:
            return ""

        msg = "\n"
        # We need to output them "backwards", so the oldest is first
        if not clog_limit:
            clogs = self.changelog
        else:
            clogs = self.changelog[:clog_limit]
        last_ts = 0
        hack_ts = 0
        for (ts, author, content) in reversed(clogs):
            if ts != last_ts:
                hack_ts = 0
            else:
                hack_ts += 1
            last_ts = ts
            ts += hack_ts
            msg += """<changelog author="{0}" date="{1}">{2}</changelog>\n""".format( to_xml(author, attrib=True), to_xml(str(ts)), to_xml(content))
        return msg

    def xml_dump_primary_metadata(self):
        msg = """\n<package type="rpm">"""
        msg += self._dump_base_items()
        msg += self._dump_format_items()
        msg += """\n</package>"""
        return msg

    def xml_dump_filelists_metadata(self):
        msg = """\n<package pkgid="{0}" name="{1}" arch="{2}">
  <version epoch="{3}" ver="{4}" rel="{5}"/>\n""".format(self.checksum, self.name, self.arch, self.epoch, self.ver, self.rel)
        msg += self._dump_files()
        msg += "</package>\n"
        return msg

    def xml_dump_other_metadata(self, clog_limit=0):
        msg = """\n<package pkgid="{0}" name="{1}" arch="{2}">
  <version epoch="{3}" ver="{4}" rel="{5}"/>\n""".format( self.checksum, self.name, self.arch, self.epoch, self.ver, self.rel)
        msg += "{0}\n</package>\n".format( self._dump_changelog(clog_limit) )
        return msg
