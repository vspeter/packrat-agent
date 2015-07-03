import os
import logging
import shutil
import gpgme
from datetime import datetime

from Deb import Deb
from LocalRepoManager import LocalRepoManager, hashFile

"""
see https://wiki.debian.org/RepositoryFormat

TODO: Run add entry into a db, and then read the db to generate the Meta data
"""


class AptManager( LocalRepoManager ):
  def __init__( self, *args, **kargs ):
    super( AptManager, self ).__init__( *args, **kargs )
    self.arch_list = ( 'i386', 'amd64' )
    self.entry_list = {}

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

    logging.debug( 'apt: Got Entry for package: %s arch: %s distro: %s' % ( filename, arch, distro_version ) )
    deb_path = 'pool/%s/%s' % ( filename[ 0:5 ], filename )
    full_deb_path = '%s/%s' % ( self.root_dir, deb_path )
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

  def loadFile( self, filename, temp_file, distro, distro_version, arch ):
    dir_path = '%s/pool/%s/' % ( self.root_dir, filename[ 0:5 ] )
    if not os.path.exists( dir_path ):
        os.makedirs( dir_path )

    file_path = '%s%s' % ( dir_path, filename )
    shutil.move( temp_file, file_path )

  def checkFile( self, filename, distro, distro_version, arch ):
    deb_path = '%s/pool/%s/%s' % ( self.root_dir, filename[ 0:5 ], file_name )
    return os.path.exists( deb_path )

  def _writeArchMetadata( self, base_path, distro, arch, file_hashes, file_sizes ):
    dir_path = '%s/%s/binary-%s' % ( base_path, self.component, arch )
    if not os.path.exists( dir_path ):
      os.makedirs( dir_path )

    file_path = '%s/binary-%s/Release' % ( self.component, arch )
    full_path = '%s/%s' % ( base_path, file_path )
    wrk = open( full_path, 'w' )
    wrk.write( 'Component: %s\n' % self.component )
    wrk.write( 'Origin: Rubicon\n' )
    wrk.write( 'Label: %s\n' % self.repo_description )
    wrk.write( 'Architecture: %s\n' % arch )
    wrk.write( 'Description: %s of %s\n' % ( self.repo_description, self.mirror_description ) )
    wrk.close()
    file_hashes[ file_path ] = hashFile( full_path )
    file_sizes[ file_path ] = os.path.getsize( full_path )

    file_path = '%s/binary-%s/Packages' % ( self.component, arch )
    full_path = '%s/%s' % ( base_path, file_path )
    wrk = open( full_path, 'w' )
    for filename in self.entry_list[ distro ][ arch ]:
      logging.debug( 'apt: Writing package %s' % filename )
      ( deb_path, sha1, sha256, md5, size, field_order, fields ) = self.entry_list[ distro ][ arch ][ filename ]

      for field in field_order:
        if field in ( 'Filename', 'Size', 'SHA256', 'SHA1', 'MD5sum', 'Description' ):
          continue
        wrk.write( '%s: %s\n' % ( field, fields[ field ] ) )

      wrk.write( 'Filename: %s\n' % deb_path )
      wrk.write( 'Size: %s\n' % size )
      wrk.write( 'SHA256: %s\n' % sha256 )
      wrk.write( 'SHA1: %s\n' % sha1 )
      wrk.write( 'MD5sum: %s\n' % md5 )
      wrk.write( 'Description: %s\n' % fields[ 'Description' ] )
      wrk.write( '\n' )

    wrk.close()
    file_hashes[ file_path ] = hashFile( full_path )
    file_sizes[ file_path ] = os.path.getsize( full_path )

  def writeMetadata( self ):
    file_hashes = {}
    file_sizes = {}

    for distro in self.entry_list:
      logging.debug( 'apt: Writing distro %s' % distro )
      base_path = '%s/dists/%s' % ( self.root_dir, distro )
      if not os.path.exists( base_path ):
        os.makedirs( base_path )

      for arch in self.arch_list:
        logging.debug( 'apt: Writing arch %s' % arch )
        self._writeArchMetadata( base_path, distro, arch, file_hashes, file_sizes )

      wrk = open( '%s/Release' % base_path, 'w' )
      wrk.write( 'Origin: Rubicon\n' )
      wrk.write( 'Label: %s\n' % self.repo_description )
      wrk.write( 'Codename: %s\n' % distro )
      wrk.write( 'Date: %s\n' % datetime.utcnow().strftime( '%a, %d %b %Y %H:%M:%S UTC' ) )
      wrk.write( 'Architectures: %s\n' % ' '.join( self.arch_list ) )
      wrk.write( 'Components: %s\n' % self.component )
      wrk.write( 'Description: %s of %s\n' % ( self.repo_description, self.mirror_description ) )

      wrk.write( 'MD5Sum:\n' )
      for file in file_hashes:
        wrk.write( ' %s %s %s\n' % ( file_hashes[ file ][2], file_sizes[ file ], file ) )

      wrk.write( 'SHA1:\n' )
      for file in file_hashes:
        wrk.write( ' %s %s %s\n' % ( file_hashes[ file ][0], file_sizes[ file ], file ) )

      wrk.write( 'SHA256:\n' )
      for file in file_hashes:
        wrk.write( ' %s %s %s\n' % ( file_hashes[ file ][1], file_sizes[ file ], file ) )

      wrk.close()

  def sign( self, gpg_key ):
    ctx = gpgme.Context()
    ctx.armor = True
    ctx.textmode = True
    key = ctx.get_key( gpg_key )
    ctx.signers = [ key ]

    for distro in self.entry_list:
      logging.debug( 'apt: Signing distro %s' % distro )
      base_path = '%s/dists/%s' % ( self.root_dir, distro )

      plain = open( '%s/Release' % base_path, 'r' )
      sign = open( '%s/Release.gpg' % base_path, 'w' )

      ctx.sign( plain, sign, gpgme.SIG_MODE_DETACH )

      plain.close()
      sign.close()
