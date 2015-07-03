import os
import logging
import shutil
import gpgme
import json

from LocalRepoManager import LocalRepoManager, hashFile

class JSONManager( LocalRepoManager ):
  def __init__( self, *args, **kargs ):
    super( JSONManager, self ).__init__( *args, **kargs )
    self.entry_list = {}

  def addEntry( self, type, filename, distro, distro_version, arch ):
    logging.debug( 'json: Got Entry for package: %s arch: %s distro: %s' % ( filename, arch, distro_version ) )
    ( package, _ ) = filename.split( '-' )
    file_path = '%s/%s' % ( package, filename )
    full_file_path = '%s/%s' % ( self.root_dir, file_path )
    size = os.path.getsize( full_file_path )
    ( sha1, sha256, md5 ) = hashFile( full_file_path )
    self.entry_list[ distro ][ distro_version ][ arch ][ filename ] = ( file_path, type, sha1, sha256, md5, size )

  def loadFile( self, filename, temp_file, distro, distro_version, arch ):
    ( package, _ ) = filename.split( '-' )
    dir_path = '%s/%s/' % ( self.root_dir, package )

    if not os.path.exists( dir_path ):
        os.makedirs( dir_path )

    file_path = '%s%s' % ( dir_path, filename )
    shutil.move( temp_file, file_path )

  def checkFile( self, filename, distro, distro_version, arch ):
    ( package, version ) = filename.split( '-' )
    file_path = '%s/%s/%s' % ( self.root_dir, package, filename )
    return os.path.exists( file_path )

  def writeMetadata( self ):
    base_path = '%s/%s' % ( self.root_dir, self.component )

    for distro in self.entry_list:
      for distro_version in self.entry_list[ distro ]:
        for arch in self.entry_list[ distro ][ distro_version ]:
          logging.debug( 'json: Writing distro %s, distro version %s, arch %s' % ( distro, distro_version, arch ) )
          data = {}
          for filename in self.entry_list[ distro ]:
            entry = self.entry_list[ distro ][ distro_version ][ arch ]
            ( package, version ) = filename.split( '-' )
            if package not in data:
              data[ package ] = []

            data[ package ].append( {
                                     'version': version,
                                     'path': entry[0],
                                     'type': entry[1],
                                     'sha1': entry[2],
                                     'sha256': entry[3],
                                     'md5': entry[4],
                                     'size': entry[5]
                                     } )

          wrk = open( '%s/MANIFEST_%s-%s-%s.json' % ( base_path, distro, distro_version, arch ), 'w' )
          wrk.write( json.dumps( data, indent=2, sort_keys=True ) )
          wrk.close()

  def sign( self, gpg_key ):
    ctx = gpgme.Context()
    ctx.armor = True
    ctx.textmode = True
    key = ctx.get_key( gpg_key )
    ctx.signers = [ key ]

    base_path = '%s/%s' % ( self.root_dir, self.component )

    for distro in self.entry_list:
      for distro_version in self.entry_list[ distro ]:
        for arch in self.entry_list[ distro ][ distro_version ]:
          logging.debug( 'json: Signing distro %s, distro version %s, arch %s' % ( distro, distro_version, arch ) )

          plain = open( '%s/MANIFEST_%s-%s-%s.json' % ( base_path, distro, distro_version, arch ), 'r' )
          sign = open( '%s/MANIFEST_%s-%s-%s.json.gpg' % ( base_path, distro, distro_version, arch ), 'w' )

          ctx.sign( plain, sign, gpgme.SIG_MODE_DETACH )

          plain.close()
          sign.close()
