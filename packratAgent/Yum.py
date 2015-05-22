import os
import time
import logging
import shutil
from xml.sax import saxutils
from LocalRepoManager import LocalRepoManager, hashFile
from Rpm import Rpm


class YUMManager( LocalRepoManager ):
  def __init__( self, *args, **kargs ):
    super( YUMManager, self ).__init__( *args, **kargs )
    self.arch_list = ( 'x86_64', 'i386' )
    self.entry_list = {}

  def addEntry( self, type, filename, distro, distro_version, arch ):
    if type != 'rpm':
      logging.warning( 'yum: New entry not a rpm, skipping...' )
      return

    logging.debug( ( 'yum: Got Entry for package: %s arch: %s distro: %s distro_version: %s') % ( filename, arch, distro, distro_version ) )

    try:
      self.entry_list[ distro ]
    except KeyError:
      self.entry_list[ distro ] = {}

    if distro_version not in self.entry_list[ distro ]:
        self.entry_list[ distro ][ distro_version ] = {}
        for tmp in self.arch_list:
          self.entry_list[ distro ][ distro_version ][ tmp ] = {}

    full_rpm_path = '%s/%s/%s/%s/%s/%s' % ( self.root_dir, distro, self.component, distro_version, arch, filename )
    rpm = Rpm( full_rpm_path )
    ( fields, changelog ) = rpm.getDefs()
    try:
      fields['epoch']
    except KeyError:
      fields['epoch'] = 0

    if arch == 'all':
      arch = 'noarch'
    if arch != fields[ 'arch' ]:
      logging.warning( 'apt: New entry arch mismatched, skipping...' )
      return

    if fields[ 'arch' ] == 'i386':
        arch_list = ( 'i386', )
    elif fields[ 'arch' ] == 'x86_64':
        arch_list = ( 'x86_64', )
    elif fields[ 'arch' ] == 'noarch':
        arch_list = ( 'i386', 'x86_64' )

    size = os.path.getsize( full_rpm_path )
    ( sha1, sha256, md5 ) = hashFile( full_rpm_path )
    for arch in arch_list:
      self.entry_list[ distro ][ distro_version ][ arch ][ filename ] = ( sha1, size, changelog, fields )

  def loadFile( self, file_name, temp_file, distro, distro_version, arch ):
    dir_path = '%s/%s/%s/%s/%s/' % ( self.root_dir, distro, self.component, distro_version, arch )
    if not os.path.exists( dir_path ):
        os.makedirs( dir_path )

    file_path = '%s%s' % ( dir_path, file_name )
    shutil.move( temp_file, file_path )

  def checkFile( self, file_name, distro, distro_version, arch ):
    rpm_path = '%s/%s/%s/%s/%s/%s' % ( self.root_dir, distro, self.component, distro_version, arch, file_name )
    return os.path.exists( rpm_path )

  def _writeArchMetadata( self, base_path, distro, distro_version, arch ):
    timestamp = int( time.time() )
    repo_files = []
    dir_path = '%s/%s/repodata' % ( base_path, arch )
    if not os.path.exists( dir_path ):
      os.makedirs( dir_path )

    full_path = '%s/other.xml' % dir_path
    wrk = open( full_path, 'w' )
    wrk.write( '<?xml version="1.0" encoding="UTF-8"?>\n' )
    wrk.write( '<otherdata xmlns="http://linux.duke.edu/metadata/other" packages="%s">\n' % len( self.entry_list[ distro ][ distro_version ][ arch ] ) )
    for filename in self.entry_list[ distro ][ distro_version ][ arch ]:
        ( sha1, size, changelog, fields ) = self.entry_list[ distro ][ distro_version ][ arch ][ filename ]
        wrk.write( '  <package pkgid="%s" name="%s" arch="%s">\n' % ( sha1, filename, fields[ 'arch' ] ) )
        wrk.write( '    <version epoch="%s" ver="%s" rel="%s"/>\n' % ( fields[ 'epoch' ], fields[ 'version' ], fields[ 'release' ] ) )
        for change in changelog:
            wrk.write( ( '    <changelog author="%s; %s-%s" date="%s">%s</changelog>\n')) % (change[ 'auth' ], change[ 'version' ], change[ 'rev' ].split( '.' )[0], change[ 'date' ], change[ 'entry' ] )
        wrk.write( '  </package>\n' )

    wrk.write( '</otherdata>\n' )
    wrk.close()
    ( sha1orig, sha256orig, md5orig ) = hashFile( full_path )
    ( sha1, sha256, md5 ) = hashFile( full_path )  # techincially the .gzed one
    repo_files.append( { 'type': 'other', 'href': 'other.xml', 'checksum': sha1, 'open-checksum': sha1orig } )

    full_path = '%s/filelists.xml' % dir_path
    wrk = open( full_path, 'w' )
    wrk.write( '<?xml version="1.0" encoding="UTF-8"?>\n' )
    wrk.close()
    ( sha1orig, sha256orig, md5orig ) = hashFile( full_path )
    ( sha1, sha256, md5 ) = hashFile( full_path )
    repo_files.append( { 'type': 'filelists', 'href': 'filelists.xml', 'checksum': sha1, 'open-checksum': sha1orig } )

    full_path = '%s/primary.xml' % dir_path
    wrk = open( full_path, 'w' )
    wrk.write( '<?xml version="1.0" encoding="UTF-8"?>\n' )
    wrk.write( ( '<metadata packages="%s" xmlns="http://linux.duke.edu/metadata/common" xmlns:rpm="http://linux.duke.edu/metadata/rpm">\n' ) % len( self.entry_list[ distro ][ distro_version ][ arch ] ) )

    for filename in self.entry_list[ distro ][ distro_version ][ arch ]:
      ( sha1, size, changelog, fields ) = self.entry_list[ distro ][ distro_version ][ arch ][ filename ]
      wrk.write( '  <package type="rpm">\n' )
      wrk.write( '    <name>%s</name>\n' % fields[ 'name' ] )
      wrk.write( '    <arch>%s</arch>\n' % fields[ 'arch' ] )
      wrk.write( '    <version epoch="%s" rel="%s" ver="%s/>\n' % ( fields[ 'epoch' ], fields[ 'release' ], fields[ 'version' ] ) )
      wrk.write( '    <checksum pkgid="YES" type="sha">%s</checksum>\n' % sha1 )
      for field in fields:
        if field in ('epoch', 'name', 'version', 'arch', 'release'):
          continue
        wrk.write( '    <%s>%s</%s>\n' % ( field, saxutils.escape( fields[ field ] ), field ) )
      wrk.write( '  </package>\n' )
    wrk.write( '</metadata>\n' )
    wrk.close()
    ( sha1orig, sha256orig, md5orig ) = hashFile( full_path )
    ( sha1, sha256, md5 ) = hashFile( full_path )
    repo_files.append( { 'type': 'primary', 'href': 'primary.xml', 'checksum': sha1, 'open-checksum': sha1orig } )

    full_path = '%s/repomd.xml' % dir_path
    wrk = open( full_path, 'w' )
    wrk.write( '<?xml version="1.0" encoding="UTF-8"?>\n' )
    wrk.write( '<repomd xmlns="http://linux.duke.edu/metadata/repo">\n' )
    for file in repo_files:
      wrk.write( '  <data type="%s">\n' % file[ 'type' ] )
      wrk.write( '    <location href="repodata/%s"/>\n' % file[ 'href' ] )
      wrk.write( '    <timestamp>%s</timestamp>\n' % timestamp )
      wrk.write( '    <checksum type="sha">%s</checksum>\n' % file[ 'checksum' ] )
      wrk.write( '    <open-checksum type="sha">%s</open-checksum>\n' % file[ 'open-checksum' ] )
      wrk.write( '  </data>\n' )
    wrk.write( '</repomd>\n' )
    wrk.close()

  def writeMetadata(self):
    for distro in self.entry_list:
      for distro_version in self.entry_list[ distro ]:
        for arch in self.entry_list[ distro ][ distro_version ]:
          base_path = '%s/%s/%s/%s' % ( self.root_dir, distro, self.component, distro_version )
          self._writeArchMetadata( base_path, distro, distro_version, arch )
