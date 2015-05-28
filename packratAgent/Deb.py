import arpy
from StringIO import StringIO
from gzip import GzipFile
from tarfile import TarFile


class Deb(object):
  def __init__( self, filename ):
    self.filename = filename

  def _readControl( self ):
    ar = arpy.Archive( self.filename )
    ar.read_all_headers()

    targz = ar.archived_files[ 'control.tar.gz' ].read()

    tar = GzipFile( fileobj=StringIO( targz ) ).read()

    control = TarFile( fileobj=StringIO( tar ) ).extractfile( './control' ).read()

    return control

  def getControlFields( self ):
    order = []
    results = {}
    control = self._readControl()
    doDescription = False
    for line in control.splitlines():
      if doDescription:
        results[ 'Description' ] += '\n'
        results[ 'Description' ] += line
      else:
        pos = line.find( ':' )
        key = line[ 0 : pos ]
        value = line[ pos + 1 : ]
        key = key.strip()
        order.append( key )
        results[ key ] = value.strip()
        if key == 'Description':
          doDescription = True

    return ( order, results )
