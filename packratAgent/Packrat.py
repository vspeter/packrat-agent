import logging
import os
import errno
# import time
# from threading import Thread

from cinp import client


class PackratConnectionException( Exception ):
  pass


class PackratException( Exception ):
  pass


PACKRAT_API_VERSION = '1.5'
DOWNLOAD_TMP_DIR = '/tmp/packratAgent'

"""
class KeepAlive( Thread ):
  def __init__( self, cinp, *args, **kwargs ):
    super( KeepAlive, self ).__init__( *args, **kwargs )
    self.daemon = True
    self.cinp = cinp

  def run( self ):
    while self.cinp:
      rc = self.cinp.call( '/api/v1/Auth(keepalive)' ) # detect if the keepalive failes, if it does... re-auth
      print( "Keep alive saies '{0}'".format( rc ) )
      time.sleep( 60 )
"""


class Packrat():
  def __init__( self, host, proxy, name, psk ):
    super().__init__()

    try:
      os.makedirs( DOWNLOAD_TMP_DIR )
    except OSError as e:
      if e.errno == errno.EEXIST and os.path.isdir( DOWNLOAD_TMP_DIR ):
        pass
      else:
        raise e

    self.cinp = client.CInP( host, '/api/v1/', proxy )
    # self.token = self.cinp.call( '/api/v1/Auth(login)', { 'username': name, 'password': psk } )[ 'value' ]
    # self.cinp.setAuth( name, self.token )
    # self.keepalive = KeepAlive( self.cinp )
    # self.keepalive.start()
    self.name = name
    root = self.cinp.describe( '/api/v1/Repo' )
    if root[ 'api-version' ] != PACKRAT_API_VERSION:
      raise PackratException( 'Expected API version "{0}" found "{1}"'.format( PACKRAT_API_VERSION, root[ 'api-version' ] ) )

  def getFile( self, url, timeout=30 ):
    logging.debug( 'Packrat: File URL: "%s"', url )

    return self.cinp.getFile( url, target_dir=DOWNLOAD_TMP_DIR, timeout=timeout )

  def getMirror( self ):
    return self.cinp.get( '/api/v1/Repo/Mirror:{0}:'.format( self.name ) )

  def heartbeat( self ):
    self.cinp.call( '/api/v1/Repo/Mirror:{0}:(heartbeat)'.format( self.name ), {} )

  def getRepos( self, repo_uri_list ):  # TODO: make sure it is a repo URI
    return self.cinp.getMulti( repo_uri_list )

  def poll( self, repo_uri, timeout=30 ):
    return self.cinp.call( '{0}(poll)'.format( repo_uri ), { 'timeout': timeout }, timeout=( timeout + 30 ) )

  def getPackageFiles( self, repo_uri, package_list=None ):
    result = {}
    for key, value in self.cinp.getFilteredObjects( '/api/v1/Repo/PackageFile', 'repo', { 'repo': repo_uri, 'package_list': package_list } ):
      result[ key ] = value

    return result

  def getDistroVersions( self ):
    result = {}
    for key, value in self.cinp.getFilteredObjects( '/api/v1/Repo/DistroVersion' ):
      result[ key ] = value

    return result
