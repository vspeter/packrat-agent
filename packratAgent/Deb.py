import arpy

from gzip import GzipFile
from tarfile import TarFile


class Deb():
  def __init__( self, filename ):
    super().__init__()
    self.filename = filename

  def _readControl( self ):
    ar = arpy.Archive( self.filename )
    ar.read_all_headers()

    targz = ar.archived_files[ b'control.tar.gz' ]

    tar = GzipFile( fileobj=targz )

    control = TarFile( fileobj=tar ).extractfile( './control' ).read()
    tar.close()

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
