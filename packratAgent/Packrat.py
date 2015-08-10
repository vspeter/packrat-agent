import logging
from cinp import client

class PackratConnectionException( Exception ):
  pass


class PackratException( Exception ):
  pass

DISTRO_VERSION_CACHE = {}

class Packrat( object ):
  def __init__( self, host, proxy, name, psk ):
    self.cinp = client.CInP( host, '/api/v1', proxy )
    #self.cinp.setAuth( name, psk )
    self.name = name

  def getFile( self, url, timeout=30 ):
    logging.debug( 'Packrat: File URL: "%s"' % url )

    tmpfile = open( '/tmp/getfile', 'w' )
    self.cinp.getFile( url, tmpfile, timeout=timeout )
    tmpfile.close()

    return '/tmp/getfile' #TODO: a real tmpfile

  def getMirror( self ):
    return self.cinp.get( '/api/v1/Repos/Mirror:%s:' % self.name )

  def syncStart( self ):
    return self.cinp.call( '/api/v1/Repos/Mirror:%s:(syncStart)' % self.name )

  def syncComplete( self ):
    return self.cinp.call( '/api/v1/Repos/Mirror:%s:(syncComplete)' % self.name )

  def getRepo( self, repo_uri ): #TODO: make sure it is a repo URI
    return self.cinp.get( repo_uri )

  def getPackages( self, repo_uri ): #TODO: iterate over all of the chunks
    return self.cinp.list( '/api/v1/Repos/Package', 'repo-sync', { 'repo': repo_uri }, count=5000 )[ 0 ]

  def getPackageFiles( self, repo_uri, package_uri ): #TODO: iterate over all of the list chunks
    return self.cinp.getObjects( list_args={ 'uri': '/api/v1/Repos/PackageFile', 'filter': 'repo-sync', 'values': { 'repo': repo_uri, 'package': package_uri } } )

  def getDistroVersion( self, version_uri ): #TODO: make sure it is a distro version uri
    global DISTRO_VERSION_CACHE

    if version_uri in DISTRO_VERSION_CACHE:
      return DISTRO_VERSION_CACHE[ version_uri ]

    DISTRO_VERSION_CACHE[ version_uri ] = self.cinp.get( version_uri )

    return DISTRO_VERSION_CACHE[ version_uri ]
