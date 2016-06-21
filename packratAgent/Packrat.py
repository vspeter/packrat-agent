import logging
import os
#import time
import tempfile
#from threading import Thread

from cinp import client

class PackratConnectionException( Exception ):
  pass


class PackratException( Exception ):
  pass

PACKRAT_API_VERSION = 'v1.1'

"""
class KeepAlive( Thread ):
  def __init__( self, cinp, *args, **kwargs ):
    super( KeepAlive, self ).__init__( *args, **kwargs )
    self.daemon = True
    self.cinp = cinp

  def run( self ):
    while self.cinp:
      rc = self.cinp.call( '/api/v1/Auth(keepalive)' ) # detect if the keepalive failes, if it does... re-auth
      print "Keep alive saies '%s'" % rc
      time.sleep( 60 )
"""

class Packrat( object ):
  def __init__( self, host, proxy, name, psk ):
    self.cinp = client.CInP( host, '/api/v1', proxy )
    #self.token = self.cinp.call( '/api/v1/Auth(login)', { 'username': name, 'password': psk } )[ 'value' ]
    #self.cinp.setAuth( name, self.token )
    #self.keepalive = KeepAlive( self.cinp )
    #self.keepalive.start()
    self.name = name
    root = self.cinp.describe( '/api/v1/Repos' )[0]
    if root[ 'api-version' ] != PACKRAT_API_VERSION:
      raise PackratException( 'Expected API version "%s" found "%s"' % ( PACKRAT_API_VERSION, root[ 'api-version' ] ) )

  def getFile( self, url, timeout=30 ):
    logging.debug( 'Packrat: File URL: "%s"' % url )

    ( fd, file_path ) = tempfile.mkstemp( prefix='packrat-' )
    tmpfile = os.fdopen( fd, 'w' )
    self.cinp.getFile( url, tmpfile, timeout=timeout )
    tmpfile.close()

    return file_path

  def getMirror( self ):
    return self.cinp.get( '/api/v1/Repos/Mirror:%s:' % self.name )

  def heartbeat( self ):
    self.cinp.call( '/api/v1/Repos/Mirror:%s:(heartbeat)' % self.name )

  def getRepos( self, repo_uri_list ): #TODO: make sure it is a repo URI
    return self.cinp.getObjects( repo_uri_list )

  def poll( self, repo_uri, timeout=30 ):
    return self.cinp.call( '%s(poll)' % repo_uri, { 'timeout': timeout }, timeout=( timeout + 30 ) )

  def getPackageFiles( self, repo_uri, package_list=None ):
    return self.cinp.getObjects( list_args={ 'uri': '/api/v1/Repos/PackageFile', 'filter': 'repo', 'values': { 'repo': repo_uri, 'package_list': package_list } } )

  def getDistroVersions( self ):
    return self.cinp.getObjects( list_args={ 'uri': '/api/v1/Repos/DistroVersion' } )
