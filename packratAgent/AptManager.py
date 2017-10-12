import os
import logging
import shutil
import gpgme
from datetime import datetime

from packratAgent.Deb import Deb
from packratAgent.LocalRepoManager import LocalRepoManager, hashFile

"""
see https://wiki.debian.org/RepositoryFormat

TODO: Run add entry into a db, and then read the db to generate the Meta data
"""


class AptManager( LocalRepoManager ):
  def __init__( self, *args, **kargs ):
    super().__init__( *args, **kargs )
    self.arch_list = ( 'i386', 'amd64' )
    self.entry_list = {}

  def filePath( self, filename, distro, distro_version, arch ):
    ( pool_dir, _ ) = filename.split( '_', 1 )
    pool_dir = pool_dir[ 0:6 ]

    return '{0}/pool/{1}/{2}'.format( self.root_dir, pool_dir, filename )

  def metadataFiles( self ):
    result = []
    for distro in self.distro_map[ 'debian' ]:
      base_path = '{0}/dists/{1}'.format( self.root_dir, distro )
      result.append( '{0}/Release'.format( base_path ) )
      result.append( '{0}/Release.gpg'.format( base_path ) )

      for arch in self.arch_list:
        result.append( '{0}/{1}/binary-{2}/Release'.format( base_path, self.component, arch ) )
        result.append( '{0}/{1}/binary-{2}/Packages'.format( base_path, self.component, arch ) )

    return result

  def addEntry( self, type, filename, distro, distro_version, arch ):
    if type != 'deb':
      logging.warning( 'apt: New entry not a deb, skipping...' )
      return

    if distro != 'debian':
      logging.warning( 'apt: Not a debian distro, skipping...' )
      return

    if distro_version not in self.entry_list:
      self.entry_list[ distro_version ] = {}
      for tmp in self.arch_list:
        self.entry_list[ distro_version ][ tmp ] = {}

    logging.debug( 'apt: Got Entry for package: %s arch: %s distro: %s', filename, arch, distro_version )
    ( pool_dir, _ ) = filename.split( '_', 1 )
    pool_dir = pool_dir[ 0:6 ]
    deb_path = 'pool/{0}/{1}'.format( pool_dir, filename )
    full_deb_path = os.path.join( self.root_dir, deb_path )
    deb = Deb( full_deb_path )
    ( field_order, fields ) = deb.getControlFields()

    if arch == 'x86_64':
      arch = 'amd64'

    if arch != fields[ 'Architecture' ]:
      logging.warning( 'apt: New entry arch mismatched, skipping...' )
      return

    if fields[ 'Architecture' ] == 'i386':
      arch_list = ( 'i386', )
    elif fields[ 'Architecture' ] == 'amd64':
      arch_list = ( 'amd64', )
    elif fields[ 'Architecture' ] == 'all':
      arch_list = ( 'i386', 'amd64' )

    size = os.path.getsize( full_deb_path )
    ( sha1, sha256, md5 ) = hashFile( full_deb_path )
    for arch in arch_list:
      self.entry_list[ distro_version ][ arch ][ filename ] = ( deb_path, sha1, sha256, md5, size, field_order, fields )

  def removeEntry( self, filename, distro, distro_version, arch ):
    if arch == 'i386':
      arch_list = ( 'i386', )
    elif arch == 'x86_64':
      arch_list = ( 'amd64', )
    elif arch == 'all':
      arch_list = ( 'i386', 'amd64' )

    for arch in arch_list:
      try:
        del self.entry_list[ distro_version ][ arch ][ filename ]
      except KeyError:
        logging.warning( 'apt: unable to remove entry "%s" "%s" "%s" "%s", ignored.', filename, distro, distro_version, arch )

  def loadFile( self, filename, temp_file, distro, distro_version, arch ):
    ( pool_dir, _ ) = filename.split( '_', 1 )
    pool_dir = pool_dir[ 0:6 ]

    dir_path = '{0}/pool/{1}/'.format( self.root_dir, pool_dir )
    if not os.path.exists( dir_path ):
        os.makedirs( dir_path )

    file_path = os.path.join( dir_path, filename )
    shutil.move( temp_file, file_path )

  def _writeArchMetadata( self, base_path, distro, arch, file_hashes, file_sizes ):
    dir_path = '{0}/{1}/binary-{2}'.format( base_path, self.component, arch )
    if not os.path.exists( dir_path ):
      os.makedirs( dir_path )

    file_path = '{0}/binary-{1}/Release'.format( self.component, arch )
    full_path = os.path.join( base_path, file_path )
    wrk = open( full_path, 'w' )
    wrk.write( 'Component: {0}\n'.format( self.component ) )
    wrk.write( 'Origin: Rubicon\n' )
    wrk.write( 'Label: {0}\n'.format( self.repo_description ) )
    wrk.write( 'Architecture: {0}\n'.format( arch ) )
    wrk.write( 'Description: {0} of {1}\n'.format( self.repo_description, self.mirror_description ) )
    wrk.close()
    file_hashes[ file_path ] = hashFile( full_path )
    file_sizes[ file_path ] = os.path.getsize( full_path )

    file_path = '{0}/binary-{1}/Packages'.format( self.component, arch )
    full_path = os.path.join( base_path, file_path )
    wrk = open( full_path, 'w' )
    try:
      filename_list = self.entry_list[ distro ][ arch ]
    except KeyError:
      filename_list = []
    for filename in filename_list:
      logging.debug( 'apt: Writing package %s', filename )
      ( deb_path, sha1, sha256, md5, size, field_order, fields ) = self.entry_list[ distro ][ arch ][ filename ]

      for field in field_order:
        if field in ( 'Filename', 'Size', 'SHA256', 'SHA1', 'MD5sum', 'Description' ):
          continue
        wrk.write( '{0}: {1}\n'.format( field, fields[ field ] ) )

      wrk.write( 'Filename: {0}\n'.format( deb_path ) )
      wrk.write( 'Size: {0}\n'.format( size ) )
      wrk.write( 'SHA256: {0}\n'.format( sha256 ) )
      wrk.write( 'SHA1: {0}\n'.format( sha1 ) )
      wrk.write( 'MD5sum: {0}\n'.format( md5 ) )
      wrk.write( 'Description: {0}\n'.format( fields[ 'Description' ] ) )
      wrk.write( '\n' )

    wrk.close()
    file_hashes[ file_path ] = hashFile( full_path )
    file_sizes[ file_path ] = os.path.getsize( full_path )

  def writeMetadata( self ):
    file_hashes = {}
    file_sizes = {}

    for distro in self.distro_map[ 'debian' ]:
      logging.debug( 'apt: Writing distro %s', distro )
      base_path = '{0}/dists/{1}'.format( self.root_dir, distro )
      if not os.path.exists( base_path ):
        os.makedirs( base_path )

      for arch in self.arch_list:
        logging.debug( 'apt: Writing arch %s', arch )
        self._writeArchMetadata( base_path, distro, arch, file_hashes, file_sizes )

      wrk = open( '{0}/Release'.format( base_path ), 'w' )
      wrk.write( 'Origin: Rubicon\n' )
      wrk.write( 'Label: {0}\n'.format( self.repo_description ) )
      wrk.write( 'Codename: {0}\n'.format( distro ) )
      wrk.write( 'Date: {0}\n'.format( datetime.utcnow().strftime( '%a, %d %b %Y %H:%M:%S UTC' ) ) )
      wrk.write( 'Architectures: {0}\n'.format( ' '.join( self.arch_list ) ) )
      wrk.write( 'Components: {0}\n'.format( self.component ) )
      wrk.write( 'Description: {0} of {1}\n'.format( self.repo_description, self.mirror_description ) )

      wrk.write( 'MD5Sum:\n' )
      for file in file_hashes:
        wrk.write( ' {0} {1} {2}\n'.format( file_hashes[ file ][2], file_sizes[ file ], file ) )

      wrk.write( 'SHA1:\n' )
      for file in file_hashes:
        wrk.write( ' {0} {1} {2}\n'.format( file_hashes[ file ][0], file_sizes[ file ], file ) )

      wrk.write( 'SHA256:\n' )
      for file in file_hashes:
        wrk.write( ' {0} {1} {2}\n'.format( file_hashes[ file ][1], file_sizes[ file ], file ) )

      wrk.close()

    if self.gpg_key:
      ctx = gpgme.Context()
      ctx.armor = True
      ctx.textmode = True
      key = ctx.get_key( self.gpg_key )
      ctx.signers = [ key ]

      for distro in self.entry_list:
        logging.info( 'apt: Signing distro %s', distro )
        base_path = '{0}/dists/{1}'.format( self.root_dir, distro )

        plain = open( '{0}/Release'.format( base_path ), 'r' )
        sign = open( '{0}/Release.gpg'.format( base_path ), 'w' )

        ctx.sign( plain, sign, gpgme.SIG_MODE_DETACH )

        plain.close()
        sign.close()
