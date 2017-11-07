import os
import re
import logging
import shutil
import json
import base64
from datetime import datetime

from packratAgent.LocalRepoManager import LocalRepoManager
from packratAgent.Container import Container

TRAILING_ZEROS = re.compile( '(\.0+)*$' )


def normalize_version( value ):  # from https://stackoverflow.com/questions/1714027/version-number-comparison
  return [ int( x ) for x in TRAILING_ZEROS.sub( '', value[1] ).split( '.' ) ]


def _make_manifest( container_name, entry, tag_override=None ):
  result = {
             'schemaVersion': 1,
             'name': container_name,
             'tag': tag_override if tag_override is not None else entry[1],
             'architecture': entry[2]
            }

  result[ 'fsLayers' ] = []
  result[ 'history' ] = []
  for i in range( 0, len( entry[3] ) ):
    result[ 'fsLayers' ].insert( 0, { 'blobSum': entry[3][ i ] } )
    v1 = {}
    for key in ( 'id', 'parent' ):
      try:
        v1[ key ] = entry[4][ i ][ key ]
      except KeyError:
        pass

    if entry[4][ i ][ 'created' ] != '0001-01-01T00:00:00Z':
      v1[ 'created' ] = entry[4][ i ][ 'created' ]

    result[ 'history' ].insert( 0, { 'v1Compatibility': json.dumps( v1 ) } )

  payload = json.dumps( result, indent=2 ).encode()

  protected = {
                'formatLength': len( payload ) - 2,
                'formatTail': base64.encodebytes( payload[ -2: ] ).rstrip( b'=\n' ).decode(),
                'time': datetime.utcnow().isoformat() + 'Z'
              }
  protected = base64.encodebytes( json.dumps( protected ).encode() ).rstrip( b'=\n' ).decode()

  signatures = []  # https://github.com/docker/libtrust/blob/master/jsonsign.go
  signatures.append( {
                        #'header': { 'a': 'b' },
                        #'signature': 'asdfasdfasd',
                        'protected': protected
                      } )

  return payload[ :-2 ].decode() + ',\n"signatures": ' + json.dumps( signatures, indent=2 ) + '\n}\n'


class DockerManager( LocalRepoManager ):
  def __init__( self, *args, **kargs ):
    super().__init__( *args, **kargs )
    self.entry_list = {}

  def filePaths( self, filename, distro, distro_version, arch ):
    ( container_name, _ ) = filename.split( '_', 1 )
    cache_dir = container_name[ 0:6 ]

    cache_path = os.path.join( self.root_dir, 'cache', cache_dir )

    file_path = os.path.join( cache_path, filename )

    return [ file_path ]

  def metadataFiles( self ):
    result = []
    result.append( os.path.join( self.root_dir, 'v2/_catalog' ) )

    for container_name in self.entry_list:
      base_path = os.path.join( self.root_dir, 'v2', container_name )
      blob_path = os.path.join( base_path, 'blobs' )
      manifest_path = os.path.join( base_path, 'manifests' )
      tag_path = os.path.join( base_path, 'tags' )

      result.append( os.path.join( tag_path, 'list' ) )
      result.append( os.path.join( manifest_path, 'latest' ) )
      for entry in self.entry_list[ container_name ]:
        result.append( os.path.join( manifest_path, entry[1] ) )

        for blob in entry[3]:
          result.append( os.path.join( blob_path, blob ) )

    return result

  def addEntry( self, type, filename, distro, distro_version, arch ):
    logging.debug( 'docker: Got Entry for package: {0} arch: {1} distro: {2}'.format( filename, arch, distro_version ) )

    ( container_name, version ) = filename.split( '_', 1 )
    cache_dir = container_name[ 0:6 ]
    version = version.strip( '.tar' )

    base_path = os.path.join( self.root_dir, 'v2', container_name )
    blob_path = os.path.join( base_path, 'blobs' )

    cache_path = os.path.join( self.root_dir, 'cache', cache_dir )
    file_path = os.path.join( cache_path, filename )

    if not os.path.exists( blob_path ):
      os.makedirs( blob_path )

    container = Container( file_path )

    if container_name not in self.entry_list:
      self.entry_list[ container_name ] = []

    for layer in container.layers:
      container.saveLayer( layer, blob_path )

    self.entry_list[ container_name ].append( ( filename, version, arch, container.config[ 'rootfs' ][ 'diff_ids' ], [ container.layerInfo( i ) for i in container.layers ] ) )

    self.entry_list[ container_name ].sort( key=normalize_version )

  def removeEntry( self, filename, distro, distro_version, arch ):
    ( container_name, _ ) = filename.split( '_', 1 )

    for i in range( 0, len( self.entry_list[ container_name ] ) ):
      if self.entry_list[ container_name ][i][0] == filename:
        del self.entry_list[ container_name ][i]
        return

    logging.warning( 'docker: unable to remove entry "%s" "%s", ignored.', container_name, filename )

  def loadFile( self, filename, temp_file, distro, distro_version, arch ):
    ( container_name, _ ) = filename.split( '_', 1 )
    cache_dir = container_name[ 0:6 ]

    cache_path = os.path.join( self.root_dir, 'cache', cache_dir )
    if not os.path.exists( cache_path ):
        os.makedirs( cache_path )

    file_path = os.path.join( cache_path, filename )
    shutil.move( temp_file, file_path )

  def writeMetadata( self ):
    for container_name in self.entry_list:
      logging.debug( 'docker: writing manifests/tags for "{0}"'.format( container_name ) )
      base_path = os.path.join( self.root_dir, 'v2', container_name )
      manifest_path = os.path.join( base_path, 'manifests' )
      tag_path = os.path.join( base_path, 'tags' )

      if not os.path.exists( manifest_path ):
        os.makedirs( manifest_path )

      if not os.path.exists( tag_path ):
        os.makedirs( tag_path )

      tag_list = []

      tag_list.append( 'latest' )
      manifest = _make_manifest( container_name, self.entry_list[ container_name ][0], 'latest' )
      wrk = open( os.path.join( manifest_path, 'latest' ), 'w' )
      wrk.write( manifest )  # "latest" is the top of the list
      wrk.close()

      for entry in self.entry_list[ container_name ]:
        tag_list.append( entry[1] )
        wrk = open( os.path.join( manifest_path, entry[1] ), 'w' )  # TODO: do we trust the version to be fs safe?
        wrk.write( _make_manifest( container_name, entry ) )
        wrk.close()

      wrk = open( os.path.join( tag_path, 'list' ), 'w' )
      wrk.write( json.dumps( { 'name': container_name, 'tags': tag_list }, indent=2 ) )
      wrk.close()

    logging.debug( 'docker: writing catalog' )
    wrk = open( os.path.join( self.root_dir, 'v2/_catalog' ), 'w' )
    wrk.write( json.dumps( { 'repositories': list( self.entry_list.keys() ) }, indent=2 ) )
    wrk.close()

  def sign( self, gpg_key ):
    pass  # not signed?
