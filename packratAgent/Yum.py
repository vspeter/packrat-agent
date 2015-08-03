import os
import time
import logging
import gpgme
import shutil
from yum.packages import YumLocalPackage
from rpm import rpm

from LocalRepoManager import LocalRepoManager, hashFile

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

    if arch == 'all':
      arch = 'noarch'

    full_rpm_path = '%s/%s/%s/%s/%s/%s' % ( self.root_dir, distro, self.component, distro_version, arch, filename )
    self.entry_list[ distro ][ distro_version ][ filename ] = ( full_rpm_path, arch )

  def loadFile( self, filename, temp_file, distro, distro_version, arch ):
    if arch == 'all':
      arch = 'noarch'

    dir_path = '%s/%s/%s/%s/%s/' % ( self.root_dir, distro, self.component, distro_version, arch )
    if not os.path.exists( dir_path ):
        os.makedirs( dir_path )

    file_path = '%s%s' % ( dir_path, filename )
    if self.gpg_key:
      logging.info( 'yum: signing %s' % temp_file )
      rpm.addMacro( '_gpg_name', self.gpg_key ) # not sure if it's bad to add this macro multiple times
      if not rpm.addSign( temp_file, '' ): # '' -> passpharase
        raise Exception( 'Error Signing "%s"' % temp_file )

    shutil.move( temp_file, file_path )

  def checkFile( self, filename, distro, distro_version, arch ):
    if arch == 'all':
      arch = 'noarch'

    rpm_path = '%s/%s/%s/%s/%s/%s' % ( self.root_dir, distro, self.component, distro_version, arch, filename )
    return os.path.exists( rpm_path )

  def _writeArchMetadata( self, base_path, distro, distro_version ):
    timestamp = int( time.time() )
    repo_files = []
    dir_path = '%s/repodata' % base_path
    if not os.path.exists( dir_path ):
      os.makedirs( dir_path )

    other_full_path = '%s/other.xml' % dir_path
    other_fd = open( other_full_path, 'w' )
    other_fd.write( '<?xml version="1.0" encoding="UTF-8"?>\n' )
    other_fd.write( '<otherdata xmlns="http://linux.duke.edu/metadata/other" packages="%s">\n' % len( self.entry_list[ distro ][ distro_version ] ) )

    filelists_full_path = '%s/filelists.xml' % dir_path
    filelists_fd = open( filelists_full_path, 'w' )
    filelists_fd.write( '<?xml version="1.0" encoding="UTF-8"?>\n' )
    filelists_fd.write( '<filelists xmlns="http://linux.duke.edu/metadata/filelists" packages="%s">\n' % len( self.entry_list[ distro ][ distro_version ] ) )

    primary_full_path = '%s/primary.xml' % dir_path
    primary_fd = open( primary_full_path, 'w' )
    primary_fd.write( '<?xml version="1.0" encoding="UTF-8"?>\n' )
    primary_fd.write( ( '<metadata packages="%s" xmlns="http://linux.duke.edu/metadata/common" xmlns:rpm="http://linux.duke.edu/metadata/rpm">\n' ) % len( self.entry_list[ distro ][ distro_version ] ) )

    for filename in self.entry_list[ distro ][ distro_version ]:
      ( full_rpm_path, arch ) = self.entry_list[ distro ][ distro_version ][ filename ]
      pkg = YumLocalPackage( filename=full_rpm_path )
      pkg._reldir = base_path
      other_fd.write( pkg.xml_dump_other_metadata() )
      filelists_fd.write( pkg.xml_dump_filelists_metadata() )
      primary_fd.write( pkg.xml_dump_primary_metadata() )

    other_fd.write( '</otherdata>\n' )
    other_fd.close()
    filelists_fd.write( '</filelists>\n' )
    filelists_fd.close()
    primary_fd.write( '</metadata>\n' )
    primary_fd.close()

    ( sha1orig, sha256orig, md5orig ) = hashFile( other_full_path )
    ( sha1, sha256, md5 ) = hashFile( other_full_path )  # techincially the .gzed one
    repo_files.append( { 'type': 'other', 'href': 'other.xml', 'checksum': sha256, 'open-checksum': sha256orig } )

    ( sha1orig, sha256orig, md5orig ) = hashFile( filelists_full_path )
    ( sha1, sha256, md5 ) = hashFile( filelists_full_path )
    repo_files.append( { 'type': 'filelists', 'href': 'filelists.xml', 'checksum': sha256, 'open-checksum': sha256orig } )

    ( sha1orig, sha256orig, md5orig ) = hashFile( primary_full_path )
    ( sha1, sha256, md5 ) = hashFile( primary_full_path )
    repo_files.append( { 'type': 'primary', 'href': 'primary.xml', 'checksum': sha256, 'open-checksum': sha256orig } )

    repomod_full_path = '%s/repomd.xml' % dir_path
    repomod_fd = open( repomod_full_path, 'w' )
    repomod_fd.write( '<?xml version="1.0" encoding="UTF-8"?>\n' )
    repomod_fd.write( '<repomd xmlns="http://linux.duke.edu/metadata/repo">\n' )
    for file in repo_files:
      repomod_fd.write( '  <data type="%s">\n' % file[ 'type' ] )
      repomod_fd.write( '    <location href="repodata/%s"/>\n' % file[ 'href' ] )
      repomod_fd.write( '    <timestamp>%s</timestamp>\n' % timestamp )
      repomod_fd.write( '    <checksum type="sha256">%s</checksum>\n' % file[ 'checksum' ] )
      repomod_fd.write( '    <open-checksum type="sha256">%s</open-checksum>\n' % file[ 'open-checksum' ] )
      repomod_fd.write( '  </data>\n' )
    repomod_fd.write( '</repomd>\n' )
    repomod_fd.close()

  def writeMetadata(self):
    for distro in self.entry_list:
      for distro_version in self.entry_list[ distro ]:
        base_path = '%s/%s/%s/%s' % ( self.root_dir, distro, self.component, distro_version )
        self._writeArchMetadata( base_path, distro, distro_version )

    if self.gpg_key:
      ctx = gpgme.Context()
      ctx.armor = True
      ctx.textmode = True
      key = ctx.get_key( self.gpg_key )
      ctx.signers = [ key ]

      for distro in self.entry_list:
        logging.info( 'yum: Signing distro %s' % distro )
        for distro_version in self.entry_list[ distro ]:
          base_path = '%s/%s/%s/%s/repodata' % ( self.root_dir, distro, self.component, distro_version )

          plain = open( '%s/repomd.xml' % base_path, 'r' )
          sign = open( '%s/repomd.xml.asc' % base_path, 'w' )

          ctx.sign( plain, sign, gpgme.SIG_MODE_DETACH )

          plain.close()
          sign.close()
