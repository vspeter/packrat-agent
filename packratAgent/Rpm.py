
class RpmException(Exception):
    pass


class Rpm(object):

    def __init__(self, filename):
        self.rpm = RPM_file(filename)
        if not self.rpm.binary:
            raise RpmException('Unvalid RPM file')

    def getDefs(self):
        result = {}
        for tag in RPMTAGS:
            value = self.rpm[tag]
            if value is not None:
                result[RPMTAGS[tag]] = value

        return (result, [])


# http://www.rubydoc.info/github/dmacvicar/ruby-rpm-ffi/RPM/FFI

# NOTE: RPM Reading code is from PyRPM by Mario Morgado, Licensed BSD
# From Here down is primarly from PyRPM, modified to comply with pep8
# and other minor tweeks

# from StringIO import StringIO
from cStringIO import StringIO
import struct
import re

RPM_LEAD_MAGIC_NUMBER = '\xed\xab\xee\xdb'
RPM_HEADER_MAGIC_NUMBER = '\x8e\xad\xe8'

RPMTAG_MIN_NUMBER = 1000
RPMTAG_MAX_NUMBER = 1146

# signature tags
RPMSIGTAG_SIZE = 1000
RPMSIGTAG_LEMD5_1 = 1001
RPMSIGTAG_PGP = 1002
RPMSIGTAG_LEMD5_2 = 1003
RPMSIGTAG_MD5 = 1004
RPMSIGTAG_GPG = 1005
RPMSIGTAG_PGP5 = 1006


MD5_SIZE = 16  # 16 bytes long
PGP_SIZE = 152  # 152 bytes long


# data types definition
RPM_DATA_TYPE_NULL = 0
RPM_DATA_TYPE_CHAR = 1
RPM_DATA_TYPE_INT8 = 2
RPM_DATA_TYPE_INT16 = 3
RPM_DATA_TYPE_INT32 = 4
RPM_DATA_TYPE_INT64 = 5
RPM_DATA_TYPE_STRING = 6
RPM_DATA_TYPE_BIN = 7
RPM_DATA_TYPE_STRING_ARRAY = 8
RPM_DATA_TYPE_I18NSTRING_TYPE = 9

RPM_DATA_TYPES = (RPM_DATA_TYPE_NULL,
                  RPM_DATA_TYPE_CHAR,
                  RPM_DATA_TYPE_INT8,
                  RPM_DATA_TYPE_INT16,
                  RPM_DATA_TYPE_INT32,
                  RPM_DATA_TYPE_INT64,
                  RPM_DATA_TYPE_STRING,
                  RPM_DATA_TYPE_BIN,
                  RPM_DATA_TYPE_STRING_ARRAY,)


RPMTAGS = {
    1000: 'name',
    1001: 'version',
    1002: 'release',
    1003: 'epoch',
    1004: 'summary',
    1005: 'description',
    1006: 'buildtime',
    1007: 'buildhost',
    1008: 'installtime',
    1009: 'size',
    1010: 'distribution',
    1011: 'vendor',
    1014: 'license',
    1015: 'packager',
    1016: 'group',
    1017: 'changelog',
    1018: 'source',
    1019: 'patch',
    1020: 'url',
    1022: 'arch'
}

HEADER_MAGIC_NUMBER = re.compile('(\x8e\xad\xe8)')


def find_magic_number(regexp, data):
    ''' find a magic number in a buffer
    '''
    string = data.read(1)
    while True:
        match = regexp.search(string)
        if match:
            return data.tell() - 3
        byte = data.read(1)
        if not byte:
            return None
        else:
            string += byte


class Entry(object):

    ''' RPM Header Entry
    '''

    def __init__(self, entry, store):
        self.entry = entry
        self.store = store

        self.switch = {RPM_DATA_TYPE_CHAR:            self.__readchar,
                       RPM_DATA_TYPE_INT8:            self.__readint8,
                       RPM_DATA_TYPE_INT16:           self.__readint16,
                       RPM_DATA_TYPE_INT32:           self.__readint32,
                       RPM_DATA_TYPE_INT64:           self.__readint64,
                       RPM_DATA_TYPE_STRING:         self.__readstring,
                       RPM_DATA_TYPE_BIN:             self.__readbin,
                       RPM_DATA_TYPE_I18NSTRING_TYPE: self.__readstring
                       }

        self.store.seek(entry[2])
        self.value = self.switch[entry[1]]()
        self.tag = entry[0]

    def __str__(self):
        return "(%s, %s)" % (self.tag, self.value, )

    def __repr__(self):
        return "(%s, %s)" % (self.tag, self.value, )

    def __readchar(self, offset=1):
        ''' store is a pointer to the store offset
        where the char should be read
        '''
        data = self.store.read(offset)
        fmt = '!' + str(offset) + 'c'
        value = struct.unpack(fmt, data)
        return value

    def __readint8(self, offset=1):
        ''' int8 = 1byte
        '''
        return self.__readchar(offset)

    def __readint16(self, offset=1):
        ''' int16 = 2bytes
        '''
        data = self.store.read(offset * 2)
        fmt = '!' + str(offset) + 'i'
        value = struct.unpack(fmt, data)
        return value

    def __readint32(self, offset=1):
        ''' int32 = 4bytes
        '''
        data = self.store.read(offset * 4)
        fmt = '!' + str(offset) + 'i'
        value = struct.unpack(fmt, data)
        return value

    def __readint64(self, offset=1):
        ''' int64 = 8bytes
        '''
        data = self.store.read(offset * 4)
        fmt = '!' + str(offset) + 'l'
        value = struct.unpack(fmt, data)
        return value

    def __readstring(self):
        ''' read a string entry
        '''
        string = ''
        while True:
            char = self.__readchar()
            if char[0] == '\x00':  # read until '\0'
                break
            string += char[0]
        return string

    def __readbin(self):
        ''' read a binary entry
        '''
        if self.entry[0] == RPMSIGTAG_MD5:
            data = self.store.read(MD5_SIZE)
            value = struct.unpack('!' + MD5_SIZE + 's', data)
            return value
        elif self.entry[0] == RPMSIGTAG_PGP:
            data = self.store.read(PGP_SIZE)
            value = struct.unpack('!' + PGP_SIZE + 's', data)
            return value


class Header(object):

    ''' RPM Header Structure
    '''

    def __init__(self, header, entries, store):
        '''
        '''
        self.header = header
        self.entries = entries
        self.store = store
        self.pentries = []
        self.rentries = []

        self.__readentries()

    def __readentry(self, entry):
        ''' [4bytes][4bytes][4bytes][4bytes]
               TAG    TYPE   OFFSET  COUNT
        '''
        entryfmt = '!llll'
        entry = struct.unpack(entryfmt, entry)
        if entry[0] < RPMTAG_MIN_NUMBER or\
                entry[0] > RPMTAG_MAX_NUMBER:
            return None
        return entry

    def __readentries(self):
        ''' read a rpm entry
        '''
        for entry in self.entries:
            entry = self.__readentry(entry)
            if entry:
                if entry[0] in RPMTAGS:
                    self.pentries.append(entry)

        for pentry in self.pentries:
            entry = Entry(pentry, self.store)
            if entry:
                self.rentries.append(entry)


class RPMError(BaseException):
    pass


class RPM_file(object):

    def __init__(self, rpm):
        ''' rpm - StringIO.StringIO | file
        '''
        self.rpmfile = open(rpm, 'r')

        self.binary = None
        self.source = None
        self.__entries = []
        self.__headers = []

        self.__readlead()
        offset = self.__read_sigheader()
        self.__readheaders(offset)

    def __readlead(self):
        ''' reads the rpm lead section

            struct rpmlead {
               unsigned char magic[4];
               unsigned char major, minor;
               short type;
               short archnum;
               char name[66];
               short osnum;
               short signature_type;
               char reserved[16];
               } ;
        '''
        lead_fmt = '!4sBBhh66shh16s'
        data = self.rpmfile.read(96)
        value = struct.unpack(lead_fmt, data)

        magic_num = value[0]
        ptype = value[3]

        if magic_num != RPM_LEAD_MAGIC_NUMBER:
            raise RPMError('wrong magic number this is not a RPM file')

        if ptype == 1:
            self.binary = False
            self.source = True
        elif ptype == 0:
            self.binary = True
            self.source = False
        else:
            raise RPMError('wrong package type this is not a RPM file')

    def __read_sigheader(self):
        ''' read signature header

            ATN: this will not return any usefull information
            besides the file offset
        '''
        start = find_magic_number(HEADER_MAGIC_NUMBER, self.rpmfile)
        if not start:
            raise RPMError('invalid RPM file, signature header not found')
        # return the offsite after the magic number
        return start + 3

    def __readheader(self, header):
        ''' reads the header-header section
        [3bytes][1byte][4bytes][4bytes][4bytes]
          MN      VER   UNUSED  IDXNUM  STSIZE
        '''
        headerfmt = '!3sc4sll'
        if not len(header) == 16:
            raise RPMError('invalid header size')

        header = struct.unpack(headerfmt, header)
        magic_num = header[0]
        if magic_num != RPM_HEADER_MAGIC_NUMBER:
            raise RPMError('invalid RPM header')
        return header

    def __readheaders(self, offset):
        ''' read information headers
        '''
        # lets find the start of the header
        self.rpmfile.seek(offset)
        start = find_magic_number(HEADER_MAGIC_NUMBER, self.rpmfile)
        # go back to the begining of the header
        self.rpmfile.seek(start)
        header = self.rpmfile.read(16)
        header = self.__readheader(header)
        entries = []
        for entry in range(header[3]):
            _entry = self.rpmfile.read(16)
            entries.append(_entry)
        store = StringIO(self.rpmfile.read(header[4]))
        self.__headers.append(Header(header, entries, store))

        for header in self.__headers:
            for entry in header.rentries:
                self.__entries.append(entry)

    def __iter__(self):
        for entry in self.__entries:
            yield entry

    def __getitem__(self, item):
        for entry in self:
            if entry.tag == item:
                if entry.value and isinstance(entry.value, str):
                    return entry.value
