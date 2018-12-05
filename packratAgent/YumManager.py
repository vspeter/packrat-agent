import os
import time
import logging
import gpgme
import shutil
from packratAgent.yum.packages import YumLocalPackage
import rpm

from packratAgent.LocalRepoManager import LocalRepoManager, hashFile

"""
the  python lib to write some of the  repo files  'yum' has not been,
and  will not (semininly) be ported to  python3, we will have to revisit later.
"""


class YUMManager( LocalRepoManager ):
  def __init__( self, *args, **kargs ):
    super().__init__( *args, **kargs )
    self.arch_list = ( 'x86_64', 'i386' )
    self.entry_list = {}

  def filePaths( self, filename, distro, distro_version, arch ):
    if arch == 'all':
      arch = 'noarch'

    return [ '{0}/{1}/{2}/{3}/{4}/{5}'.format( self.root_dir, distro, self.component, distro_version, arch, filename ) ]

  def metadataFiles( self ):
    result = []
    for distro in self.distro_map:
      for distro_version in self.distro_map[ distro ]:
        base_path = '{0}/{1}/{2}/{3}'.format( self.root_dir, distro, self.component, distro_version )
        dir_path = '{0}/repodata'.format( base_path )
        result.append( '{0}/other.xml'.format( dir_path ) )
        result.append( '{0}/filelists.xml'.format( dir_path ) )
        result.append( '{0}/primary.xml'.format( dir_path ) )
        result.append( '{0}/repomd.xml'.format( dir_path ) )
        result.append( '{0}/repomd.xml.asc'.format( dir_path ) )

    return result

  def addEntry( self, type, filename, distro, distro_version, arch ):
    if type != 'rpm':
      logging.warning( 'yum: New entry not a rpm, skipping...' )
      return

    logging.debug( 'yum: Got Entry for package: %s arch: %s distro: %s distro_version: %s', filename, arch, distro, distro_version )

    try:
      self.entry_list[ distro ]
    except KeyError:
      self.entry_list[ distro ] = {}

    if distro_version not in self.entry_list[ distro ]:
        self.entry_list[ distro ][ distro_version ] = {}

    if arch == 'all':
      arch = 'noarch'

    full_rpm_path = '{0}/{1}/{2}/{3}/{4}/{5}'.format( self.root_dir, distro, self.component, distro_version, arch, filename )
    self.entry_list[ distro ][ distro_version ][ filename ] = ( full_rpm_path, arch )

  def removeEntry( self, filename, distro, distro_version, arch ):
    if arch == 'all':
      arch = 'noarch'

    try:
      del self.entry_list[ distro ][ distro_version ][ filename ]
    except KeyError:
      logging.warning( 'rpm: unable to remove entry "%s" "%s" "%s" "%s", ignored.', filename, distro, distro_version, arch )

  def loadFile( self, filename, temp_file, distro, distro_version, arch ):
    if arch == 'all':
      arch = 'noarch'

    dir_path = '{0}/{1}/{2}/{3}/{4}'.format( self.root_dir, distro, self.component, distro_version, arch )
    if not os.path.exists( dir_path ):
        os.makedirs( dir_path )

    file_path = os.path.join( dir_path, filename )
    if self.gpg_key:
      logging.info( 'yum: signing %s', temp_file )
      if not rpm.addSign( path=temp_file, keyid=self.gpg_key, passPhrase='' ):
        raise Exception( 'Error Signing "{0}"'.format( temp_file ) )

#  in the stock python3-rpm addSign is missing due to (xenial):
#  https://github.com/rpm-software-management/rpm/commit/eb632e5158fa4ef993b0e5df2a354f0be7a7a71d
#  so, get and empty dir and:
#  apt source python3-rpm
#  cd rpm-4.12.0.1+dfsg1
#  nano python/setup.py.in and change line 51 'b' to 's'
#  dpkg-buildpackage -b
#  cd ..
#  dpkg -i python3-rpm_4.12.0.1+dfsg1-3build3_amd64.deb
#  all set
#  bionic there is this bug: https://bugs.launchpad.net/ubuntu/+source/rpm/+bug/1776815
#  follow simmaler steps

    shutil.move( temp_file, file_path )
    ( _, sha256, _ ) = hashFile( file_path )
    return sha256

  def _writeArchMetadata( self, base_path, distro, distro_version ):
    timestamp = int( time.time() )
    repo_files = []
    dir_path = '{0}/repodata'.format( base_path )
    if not os.path.exists( dir_path ):
      os.makedirs( dir_path )

    try:
      filename_list = self.entry_list[ distro ][ distro_version ]
    except KeyError:
      filename_list = []

    other_full_path = '{0}/other.xml'.format( dir_path )
    other_fd = open( other_full_path, 'w' )
    other_fd.write( '<?xml version="1.0" encoding="UTF-8"?>\n' )
    other_fd.write( '<otherdata xmlns="http://linux.duke.edu/metadata/other" packages="{0}">\n'.format( len( filename_list ) ) )

    filelists_full_path = '{0}/filelists.xml'.format( dir_path )
    filelists_fd = open( filelists_full_path, 'w' )
    filelists_fd.write( '<?xml version="1.0" encoding="UTF-8"?>\n' )
    filelists_fd.write( '<filelists xmlns="http://linux.duke.edu/metadata/filelists" packages="{0}">\n'.format( len( filename_list ) ) )

    primary_full_path = '{0}/primary.xml'.format( dir_path )
    primary_fd = open( primary_full_path, 'w' )
    primary_fd.write( '<?xml version="1.0" encoding="UTF-8"?>\n' )
    primary_fd.write( '<metadata packages="{0}" xmlns="http://linux.duke.edu/metadata/common" xmlns:rpm="http://linux.duke.edu/metadata/rpm">\n'.format( len( filename_list ) ) )

    for filename in filename_list:
      ( full_rpm_path, arch ) = self.entry_list[ distro ][ distro_version ][ filename ]
      pkg = YumLocalPackage( filename=full_rpm_path, relpath='{0}/{1}'.format( arch, filename ) )
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

    repomod_full_path = '{0}/repomd.xml'.format( dir_path )
    repomod_fd = open( repomod_full_path, 'w' )
    repomod_fd.write( '<?xml version="1.0" encoding="UTF-8"?>\n' )
    repomod_fd.write( '<repomd xmlns="http://linux.duke.edu/metadata/repo">\n' )
    for file in repo_files:
      repomod_fd.write( '  <data type="{0}">\n'.format( file[ 'type' ] ) )
      repomod_fd.write( '    <location href="repodata/{0}"/>\n'.format( file[ 'href' ] ) )
      repomod_fd.write( '    <timestamp>{0}</timestamp>\n'.format( timestamp ) )
      repomod_fd.write( '    <checksum type="sha256">{0}</checksum>\n'.format( file[ 'checksum' ] ) )
      repomod_fd.write( '    <open-checksum type="sha256">{0}</open-checksum>\n'.format( file[ 'open-checksum' ] ) )
      repomod_fd.write( '  </data>\n' )
    repomod_fd.write( '</repomd>\n' )
    repomod_fd.close()

  def writeMetadata(self):
    for distro in self.distro_map:
      for distro_version in self.distro_map[ distro ]:
        base_path = '{0}/{1}/{2}/{3}'.format( self.root_dir, distro, self.component, distro_version )
        self._writeArchMetadata( base_path, distro, distro_version )

    if self.gpg_key:
      ctx = gpgme.Context()
      ctx.armor = True
      ctx.textmode = True
      key = ctx.get_key( self.gpg_key )
      ctx.signers = [ key ]

      for distro in self.distro_map:
        logging.info( 'yum: Signing distro %s', distro )
        for distro_version in self.entry_list[ distro ]:
          base_path = '{0}/{1}/{2}/{3}/repodata'.format( self.root_dir, distro, self.component, distro_version )

          plain = open( '{0}/repomd.xml'.format( base_path ), 'rb' )
          sign = open( '{0}/repomd.xml.asc'.format( base_path ), 'wb' )

          ctx.sign( plain, sign, gpgme.SIG_MODE_DETACH )

          plain.close()
          sign.close()
