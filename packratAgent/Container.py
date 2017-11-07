import json
import os
import hashlib
import shutil
import tempfile
from tarfile import TarFile

CHUNK_SIZE = 4096 * 4096


class Container():
  def __init__( self, filename ):
    super().__init__()
    self.filename = filename
    self._manifest = None
    self._config = None
    self._layerInfo = {}

  def _readManifest( self ):
    raw = TarFile( self.filename )

    manifest = raw.extractfile( 'manifest.json' ).read().decode()

    raw.close()

    self._manifest = json.loads( manifest )[0]

  @property
  def layers( self ):
    if self._manifest is None:
      self._readManifest()

    return [ i.split( '/' )[0] for i in self._manifest[ 'Layers' ] ]

  @property
  def config( self ):
    if self._config is not None:
      return self._config

    if self._manifest is None:
      self._readManifest()

    raw = TarFile( self.filename )
    config = raw.extractfile( self._manifest[ 'Config' ] ).read().decode()
    self._config = json.loads( config )
    raw.close()

    return self._config

  def layerInfo( self, layer ):
    try:
      return self._layerInfo[ layer ]
    except KeyError:
      pass

    raw = TarFile( self.filename )
    config = raw.extractfile( '{0}/json'.format( layer ) ).read().decode()
    self._layerInfo[ layer ] = json.loads( config )
    raw.close()

    return self._layerInfo[ layer ]

  def saveLayer( self, layer, dir_path ):
    target_writer = tempfile.NamedTemporaryFile( delete=False )

    raw = TarFile( self.filename )

    layer_reader = raw.extractfile( '{0}/layer.tar'.format( layer ) )
    hasher = hashlib.sha256()
    buff = layer_reader.read( CHUNK_SIZE )
    while buff:
      hasher.update( buff )
      target_writer.write( buff )
      buff = layer_reader.read( CHUNK_SIZE )

    layer_reader.close()
    target_writer.close()
    raw.close()

    shutil.move( target_writer.name, os.path.join( dir_path, 'sha256:' + hasher.hexdigest() ) )
