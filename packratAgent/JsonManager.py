import os
import logging
import shutil
import gpgme
import json

from packratAgent.LocalRepoManager import LocalRepoManager, hashFile


OTHER_TYPES = ( 'tar', 'img' )


# get this info from packrat, no point in re-parsing everything, update the other managers too, for them need to do a little comparing
def _splitFileName( filename ):  # compare with packrat/Repos/Resource.py -> load
  filename = os.path.basename( filename )

  if filename.endswith( ( '.tar.gz', '.tar.bz2', '.tar.xz', 'img.gz', 'img.bz2', 'img.xz' ) ):
    ( filename, _, _ ) = filename.rsplit( '.', 2 )

  else:
    ( filename, _ ) = filename.rsplit( '.', 1 )

  try:
    ( package, version ) = filename.split( '_' )
  except ValueError:
    package = filename
    version = None

  return ( package, version )


class JSONManager( LocalRepoManager ):
  def __init__( self, *args, **kargs ):
    super().__init__( *args, **kargs )
    self.arch_list = ( 'all', )
    self.entry_list = {}

  def filePaths( self, filename, distro, distro_version, arch ):
    ( package, version ) = _splitFileName( filename )
    return [ os.path.join( self.root_dir, package, filename ) ]

  def metadataFiles( self ):
    result = []
    base_path = '{0}/_repo_{1}'.format( self.root_dir, self.component )
    for arch in self.arch_list:
      result.append( '{0}/MANIFEST_{1}.json'.format( base_path, arch ) )
      result.append( '{0}/MANIFEST_{1}.json.gpg'.format( base_path, arch ) )

    return result

  def addEntry( self, type, filename, distro, distro_version, arch ):
    logging.debug( 'json: Got Entry for package: "%s" arch: "%s"', filename, arch )
    ( package, _ ) = _splitFileName( filename )
    file_path = os.path.join( package, filename )
    full_file_path = os.path.join( self.root_dir, file_path )
    size = os.path.getsize( full_file_path )
    ( _, sha256, _ ) = hashFile( full_file_path )

    if arch not in self.entry_list:
      self.entry_list[ arch ] = {}

    self.entry_list[ arch ][ filename ] = ( file_path, type, sha256, size )

  def removeEntry( self, filename, distro, distro_version, arch ):
    try:
      del self.entry_list[ arch ][ filename ]
    except KeyError:
      logging.warning( 'json: unable to remove entry "%s" "%s", ignored.', filename, arch )

  def loadFile( self, filename, temp_file, distro, distro_version, arch ):
    ( package, _ ) = _splitFileName( filename )
    dir_path = '{0}/{1}/'.format( self.root_dir, package )

    if not os.path.exists( dir_path ):
        os.makedirs( dir_path )

    file_path = os.path.join( dir_path, filename )
    shutil.move( temp_file, file_path )

  def writeMetadata( self ):
    base_path = '{0}/_repo_{1}'.format( self.root_dir, self.component )

    if not os.path.exists( base_path ):
      os.makedirs( base_path )

    for arch in self.arch_list:
      logging.debug( 'json: Writing arch "%s"', arch )
      data = {}
      try:
        filename_list = self.entry_list[ arch ]
      except KeyError:
        filename_list = []

      for filename in filename_list:
        entry = self.entry_list[ arch ][ filename ]
        ( package, version ) = _splitFileName( filename )
        if package not in data:
          data[ package ] = []

        data[ package ].append( {
                                  'version': version,
                                  'path': entry[0],
                                  'type': entry[1],
                                  'sha256': entry[2],
                                  'size': entry[3]
                                 } )

      wrk = open( '{0}/MANIFEST_{1}.json'.format( base_path, arch ), 'w' )
      wrk.write( json.dumps( data, indent=2, sort_keys=True ) )
      wrk.close()

    if self.gpg_key:
      ctx = gpgme.Context()
      ctx.armor = True
      ctx.textmode = True
      key = ctx.get_key( self.gpg_key )
      ctx.signers = [ key ]

      base_path = '{0}/_repo_{1}'.format( self.root_dir, self.component )

      for arch in self.arch_list:
        logging.info( 'json: Signing "%s"', arch )

        plain = open( '{0}/MANIFEST_{1}.json'.format( base_path, arch ), 'rb' )
        sign = open( '{0}/MANIFEST_{1}.json.gpg'.format( base_path, arch ), 'wb' )

        ctx.sign( plain, sign, gpgme.SIG_MODE_DETACH )

        plain.close()
        sign.close()
