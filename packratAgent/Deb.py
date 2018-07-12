import arpy
from gzip import GzipFile
from lzma import LZMAFile
from tarfile import TarFile


class Deb():
  def __init__( self, filename ):
    super().__init__()
    self.filename = filename

  def _readControl( self ):
    ar = arpy.Archive( self.filename )
    ar.read_all_headers()

    if b'control.tar.xz' in ar.archived_files:
      tar = LZMAFile( filename=ar.archived_files[ b'control.tar.xz' ] )
      # NOTE: this requires https://github.com/viraptor/arpy/pull/5

    elif b'control.tar.gz' in ar.archived_files:
      tar = GzipFile( fileobj=ar.archived_files[ b'control.tar.gz' ] )

    else:
      raise ValueError( 'Unable to find control file' )

    raw = TarFile( fileobj=tar )

    control = raw.extractfile( './control' ).read()
    raw.close()
    tar.close()
    ar.close()

    return control

  def getControlFields( self ):
    order = []
    results = {}
    results[ 'Description' ] = ''
    control = self._readControl()
    doDescription = False
    for line in control.splitlines():
      line = line.decode()
      if doDescription:
        results[ 'Description' ] += '\n'
        results[ 'Description' ] += str( line )
      else:
        pos = line.find( ':' )
        key = line[ 0:pos ]
        value = line[ pos + 1: ]
        key = key.strip()
        order.append( key )
        results[ key ] = value.strip()
        if key == 'Description':
          doDescription = True

    return ( order, results )
