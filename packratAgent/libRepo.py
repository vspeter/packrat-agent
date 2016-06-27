import sqlite3
import logging
import os
import hashlib
import time
import json
from threading import Lock, Thread

from packratAgent.LocalRepoManager import hashFile
from packratAgent.AptManager import AptManager
from packratAgent.YumManager import YUMManager
from packratAgent.YastManager import YaSTManager
from packratAgent.JsonManager import JSONManager


def fileSHA256( file_path ):
  sha256 = hashlib.sha256()
  try:
    wrk = open( file_path, 'r' )
  except IOError as e:
    if e.errno == 2:  # file not found
      return None
    else:
      raise RepoException( 'Unknown IOError "%s" getting hash of file "%s"' % ( e, file_path ) )

  buff = wrk.read( 4096 )
  while buff:
    sha256.update( buff )
    buff = wrk.read( 4096 )
  return sha256.hexdigest()


class RepoException( Exception ):
  pass


class PackratPoller( Thread ):
  def __init__( self, repo_uri, packrat, repo_name, cb, *args, **kwargs ):
    super( PackratPoller, self ).__init__( *args, **kwargs )
    self.daemon = True
    self.cont = True
    self.repo_uri = repo_uri
    self.repo_name = repo_name
    self.packrat = packrat
    self.cb = cb

  def run( self ):
    while self.cont:
      try:
        packages = self.packrat.poll( self.repo_uri )[ 'value' ]
      except Exception as e:
        logging.warning( 'libRepo: Exception while polling, "%s"' % e )
        if not self.cont:
          break

        time.sleep( 30 )
        continue

      if packages: # is not an empty Array
        logging.info( 'libRepo: Poller for "%s" got notified for "%s"' % ( self.repo_name, packages ) )
        self.cb( self.repo_uri, self.repo_name, packages )

  def stop( self ):
    self.cont = False

class FileSystemRepo( object ):
  def __init__( self, manager_type, root_dir, name, component, description, mirror_description, distro_map, gpg_key ):
    self.manager_type = manager_type
    self.root_dir = root_dir
    self.name = name
    self.component = component
    self.description = description
    self.mirror_description = mirror_description
    self.gpg_key = gpg_key
    self.update_lock = Lock()
    self.poller = None

    if self.manager_type == 'apt':
      self.manager = AptManager( os.path.join( self.root_dir, self.name ), self.component, self.description, self.mirror_description, distro_map, self.gpg_key )

    elif self.manager_type == 'yum':
      self.manager = YUMManager( os.path.join( self.root_dir, self.name ), self.component, self.description, self.mirror_description, distro_map, self.gpg_key )

    elif self.manager_type == 'yast':
      self.manager = YaSTManager( os.path.join( self.root_dir, self.name ), self.component, self.description, self.mirror_description, distro_map, self.gpg_key )

    elif self.manager_type == 'json':
      self.manager = JSONManager( os.path.join( self.root_dir, self.name ), self.component, self.description, self.mirror_description, distro_map, self.gpg_key )

    else:
      raise RepoException( 'Unknown Manager Type "%s".' % self.manager_type )

  def checkFiles( self, file_list ): # checks sha256 and file existance, removes file and entry upon problem
    for ( filename, distro, distro_version, arch, sha256 ) in file_list:
      file_path = self.manager.filePath( filename, distro, distro_version, arch )
      ( _, file_sha256, _ ) = hashFile( file_path )
      if file_sha256 is None: # file dosen't exist, no point trying to delete it
        continue

      if sha256 != file_sha256:
        logging.info( 'libRepo: hash for "%s" is "%s" expected "%s", removing.' % ( file_path, file_sha256, sha256 ) )
        logging.debug( 'libRepo: Acquiring update lock for repo during checkFiles-bad file removal "%s"' % self.name )
        self.update_lock.acquire()
        self.manager.removeEntry( filename, distro, distro_version, arch )
        if file_sha256 is not None:
          os.unlink( file_path )

        self.update_lock.release()
        logging.debug( 'libRepo: Released update lock for repo during checkFiles-bad file removal "%s"' % self.name )

  def addEntries( self, file_list ):
    logging.debug( 'libRepo: Acquiring update lock for repo during addEntries "%s"' % self.name )
    self.update_lock.acquire()
    for ( file_type, filename, distro, distro_version, arch ) in file_list:
      file_path = self.manager.filePath( filename, distro, distro_version, arch )
      if os.path.exists( file_path ):
        self.manager.addEntry( file_type, filename, distro, distro_version, arch )
    self.update_lock.release()
    logging.debug( 'libRepo: Released update lock for repo during addEntries "%s"' % self.name )

  def addFile( self, wrk_file_path, file_type, filename, distro, distro_version, arch ):
    logging.debug( 'libRepo: Acquiring update lock for repo during addFile "%s"' % self.name )
    self.update_lock.acquire()
    self.manager.loadFile( filename, wrk_file_path, distro, distro_version, arch )
    self.manager.addEntry( file_type, filename, distro, distro_version, arch )
    self.update_lock.release()
    logging.debug( 'libRepo: Released update lock for repo during addFile "%s"' % self.name )

  def removeEntry( self, filename, distro, distro_version, arch ):
    logging.debug( 'libRepo: Acquiring update lock for repo during removeEntry "%s"' % self.name )
    self.update_lock.acquire()
    self.manager.removeEntry( filename, distro, distro_version, arch )
    self.update_lock.release()
    logging.debug( 'libRepo: Released update lock for repo during removeEntry "%s"' % self.name )

  def updateMetaData( self ):
    logging.debug( 'libRepo: Acquiring update lock for repo during updateMetaData "%s"' % self.name )
    self.update_lock.acquire()

    logging.debug( 'libRepo: Repo "%s" Writing Metadata' % self.name )
    self.manager.writeMetadata()

    self.update_lock.release()
    logging.debug( 'libRepo: Released update lock for repo during updateMetaData "%s"' % self.name )

  def startPoller( self, uri, packrat, cb ):
    if self.poller is not None:
      return

    self.poller = PackratPoller( uri, packrat, self.name, cb )
    self.poller.start()

  def stopPoller( self ):
    if self.poller is not None:
      self.poller.stop()

  def joinPoller( self ):
    if self.poller is not None:
      self.poller.join()

  def checkPoller( self ):
    return self.poller is not None and self.poller.isAlive()

class FileSystemMirror( object ):
  def __init__( self, packrat, state_db, root_dir, gpg_key, description ):
    self.packrat = packrat
    self.root_dir = root_dir
    self.description = description
    self.gpg_key = gpg_key
    self._checkDB( state_db ) # check db before we connect to it
    self.conn = sqlite3.connect( state_db )
    self.repos = {}
    self.distroversion_map = {}

    cur = self.conn.cursor()
    cur.execute( 'SELECT "name", "manager", "description", "distro_map" FROM "repos";' )
    for ( name, manager, description, distro_map ) in cur.fetchall():
      self._setupRepo( name, manager, description, json.loads( distro_map ) )
    cur.close()

  def fullSync( self, do_full_clean ):
    self.distroversion_map = self.packrat.getDistroVersions()
    self._updateRepos()
    self._syncMasterToLocalState()
    if do_full_clean: # this is expensive, and could cause problems with running pollers, hopfully the full sync right after fixes anything that could be lost for a bit
      logging.debug( 'libRepo: do_full_clean' )
      expected_file_list = []
      cur = self.conn.cursor()
      cur.execute( 'SELECT "repo", "filename", "distro", "distro_version", "arch" FROM "files"' )
      for ( repo_name, filename, distro, distro_version, arch ) in cur.fetchall():
        expected_file_list.append( self.repos[ repo_name ].manager.filePath( filename, distro, distro_version, arch ) )
      cur.close()

      for repo_name in self.repos:
        expected_file_list += self.repos[ repo_name ].manager.metadataFiles()

      expected_file_list = set( expected_file_list )

      found_file_list = []
      for path, _, file_list in os.walk( self.root_dir ):
        found_file_list += [ os.path.join( path, i ) for i in file_list ]
      found_file_list = set( found_file_list )
      for file_path in found_file_list - expected_file_list:
        logging.debug( 'libRepo: removing "%s"' % file_path )
        os.unlink( file_path )

    self._pruneBadFiles()
    self._retreiveMissingFiles()
    self._updateMetaData()
    self.packrat.heartbeat()

    return True

  def checkPollers( self ):
    for repo_name in self.repos:
      if not self.repos[ repo_name ].checkPoller():
        logging.error( 'libRepo: poller for "%s" died' % repo_name )
        return False

    return True

  def startPollers( self ):
    for repo_name in self.repos:
      cur = self.conn.cursor()
      cur.execute( 'SELECT "uri" FROM "repos" WHERE name=?;', ( repo_name, ) )
      ( uri, ) = cur.fetchone()
      cur.close()

      self.repos[ repo_name ].startPoller( uri, self.packrat, self._updatePackage )

  def stopPollers( self ):
    for repo_name in self.repos:
      self.repos[ repo_name ].stopPoller()

  def waitForPollers( self ):
    for repo_name in self.repos:
      self.repos[ repo_name ].joinPoller()

  def _setupRepo( self, repo_name, manager_type, description, distro_map ):
    logging.debug( 'libRepo: _setupRepo "%s" "%s" "%s"' % ( repo_name, manager_type, description ) )
    self.repos[ repo_name ] = FileSystemRepo( manager_type, os.path.join( self.root_dir, repo_name ), repo_name, 'main', description, self.description, distro_map, self.gpg_key )

    cur = self.conn.cursor()
    cur.execute( 'SELECT "file_type", "filename", "distro", "distro_version", "arch" FROM "files" WHERE "repo"=?;', ( repo_name, ) )
    self.repos[ repo_name ].addEntries( cur.fetchall() ) #TODO: some managers have to re-hash the file, this can take a while, eventually the managers should cache their stuff in the state db, thus fasters startup, and will hopfully simplify the add/remove entry mess
    cur.close()

  def _updateRepos( self ):
    logging.debug( 'libRepo: _updateRepos' )
    mirror = self.packrat.getMirror()
    repo_list = self.packrat.getRepos( mirror[ 'repo_list' ] )
    repo_map = {}
    for repo_name in repo_list:
      repo_map[ repo_list[ repo_name ][ 'name' ] ] = { 'uri': repo_name, 'manager': repo_list[ repo_name ][ 'manager_type' ], 'description': repo_list[ repo_name ][ 'description' ], 'distroversion_list': repo_list[ repo_name ][ 'distroversion_list' ] }

    cur_names = []
    cur = self.conn.cursor()
    cur.execute( 'SELECT "name" FROM "repos";' )
    for ( repo_name, ) in cur.fetchall():
      cur_names.append( repo_name )
    cur.close()

    cur_names = set( cur_names )
    new_names = set( repo_map.keys() )

    for repo_name in cur_names - new_names:
      logging.debug( 'libRepo: Removing repo "%s"' % repo_name )
      self.conn.execute( 'DELETE FROM "repos" WHERE "name"=?;', ( repo_name, ) )
      del self.repos[ repo_name ]

    for repo_name in new_names - cur_names:
      logging.debug( 'libRepo: Adding repo "%s"' % repo_name )
      distro_map = {}
      for distroversion in repo_map[ repo_name ][ 'distroversion_list' ]:
        try:
          distro_map[ self.distroversion_map[ distroversion ][ 'distro' ] ].append( self.distroversion_map[ distroversion ][ 'version' ] )
        except KeyError:
          distro_map[ self.distroversion_map[ distroversion ][ 'distro' ] ] = [ self.distroversion_map[ distroversion ][ 'version' ] ]

      self._setupRepo( repo_name, repo_map[ repo_name ][ 'manager' ], repo_map[ repo_name ][ 'description' ], distro_map )
      self.conn.execute( 'INSERT INTO "repos" ( "name", "uri", "manager", "description", "distro_map" ) VALUES ( ?, ?, ?, ? , ? );', ( repo_name, repo_map[ repo_name ][ 'uri' ], repo_map[ repo_name ][ 'manager' ], repo_map[ repo_name ][ 'description' ], json.dumps( distro_map ) ) )

    for repo_name in new_names & cur_names: # TODO: raise an error if manager or uri changes, URI changes may be allowed?, also need to update distro_map, and tell the Manager about the changes
      self.conn.execute( 'UPDATE "repos" SET "description"=? WHERE "name"=?;', ( repo_map[ repo_name ][ 'description' ], repo_name ) )

    self.conn.commit()

  def _syncMasterToLocalState( self ): #NOTE: do not touch the repos during this, otherwise need to include this in the global lock, and this part can take a while
    logging.debug( 'libRepo: _syncMasterToLocalState' )
    for repo_name in self.repos:
      cur = self.conn.cursor()
      cur.execute( 'SELECT "uri" FROM "repos" WHERE name=?;', ( repo_name, ) )
      ( uri, ) = cur.fetchone()
      cur.close()

      master_packagefile_hashes = {}
      master_packagefile_map = self.packrat.getPackageFiles( uri )
      for packagefile_uri in master_packagefile_map:
        packagefile = master_packagefile_map[ packagefile_uri ]
        distroversion = self.distroversion_map[ packagefile[ 'distroversion' ] ]
        master_packagefile_map[ packagefile_uri ] = ( packagefile[ 'file' ], packagefile[ 'type' ], os.path.basename( packagefile[ 'file' ] ), distroversion[ 'distro' ], distroversion[ 'version' ], packagefile[ 'arch' ], packagefile[ 'sha256' ] )
        md5 = hashlib.md5()
        md5.update( ' '.join( master_packagefile_map[ packagefile_uri ] ) )
        master_packagefile_hashes[ packagefile_uri ] = md5.digest()

      local_packagefile_hashes = {}
      cur = self.conn.cursor()
      cur.execute( 'SELECT "uri", "file_url", "file_type", "filename", "distro", "distro_version", "arch", "sha256" FROM "files" WHERE "repo"=?;', ( repo_name, ) ) # get all the fields and hash them togeather (small fast hash)
      for fields in cur.fetchall():
        packagefile_uri = fields[0]
        md5 = hashlib.md5()
        md5.update( ' '.join( fields[ 1: ] ) )
        local_packagefile_hashes[ packagefile_uri ] = md5.digest()

      cur.close()

      local_packagfiles = set( local_packagefile_hashes.keys() )
      master_packagefiles = set( master_packagefile_hashes.keys() )

      for packagefile_uri in local_packagfiles - master_packagefiles:
        logging.debug( 'libRepo: Removing packagefile "%s" from repo "%s"' % ( packagefile_uri, repo_name ) )
        cur = self.conn.cursor()
        cur.execute( 'SELECT "filename", "distro", "distro_version", "arch" FROM "files" WHERE "repo"=? AND "uri"=?;', ( repo_name, packagefile_uri ) )
        ( filename, distro, distro_version, arch ) = cur.fetchone()
        cur.close()
        self.conn.execute( 'DELETE FROM "files" WHERE "repo"=? AND "uri"=?;', ( repo_name, packagefile_uri ) )
        self.repos[ repo_name ].removeEntry( filename, distro, distro_version, arch )

      for packagefile_uri in master_packagefiles - local_packagfiles:
        logging.debug( 'libRepo: Adding packagefile "%s" to repo "%s"' % ( packagefile_uri, repo_name ) )
        self.conn.execute( 'INSERT INTO "files" ( "repo", "uri", "file_url", "file_type", "filename", "distro", "distro_version", "arch", "sha256", "repo_data") VALUES ( ?, ?, ?, ?, ?, ?, ?, ?, ?, \'{}\' );', ( repo_name, packagefile_uri ) + master_packagefile_map[ packagefile_uri ] )

      for packagefile_uri in master_packagefiles & local_packagfiles:
        if local_packagefile_hashes[ packagefile_uri ] != master_packagefile_hashes[ packagefile_uri ]:
          self.conn.execute( 'UPDATE "files" SET "file_url"=?, "file_type"=?, "filename"=?, "distro"=?, "distro_version"=?, "arch"=?, "sha256"=? WHERE "repo"=? AND "uri"=?;', master_packagefile_map[ packagefile_uri ] + ( repo_name, packagefile_uri ) )
          logging.warning( 'libRepo: Local state does not match master state for "%s" in "%s", updated.' % ( packagefile_uri, repo_name ) )

      self.conn.commit()

  def _pruneBadFiles( self ):
    logging.debug( 'libRepo: _pruneBadFiles' )
    for repo_name in self.repos:
      cur = self.conn.cursor()
      cur.execute( 'SELECT "filename", "distro", "distro_version", "arch", "sha256" FROM "files" WHERE "repo"=?;', ( repo_name, ) )
      self.repos[ repo_name ].checkFiles( cur.fetchall() ) # will cleanup bad sha and missing files from repo, and remove extra files
      cur.close()

  def _retreiveMissingFiles( self ):
    logging.debug( 'libRepo: _retreiveMissingFiles' )
    for repo_name in self.repos:
      cur = self.conn.cursor()
      cur.execute( 'SELECT "file_type", "filename", "distro", "distro_version", "arch", "file_url" FROM "files" WHERE "repo"=?;', ( repo_name, ) )
      for ( file_type, filename, distro, distro_version, arch, file_url ) in cur.fetchall():
        file_path = self.repos[ repo_name ].manager.filePath( filename, distro, distro_version, arch )
        if not os.path.exists( file_path ):
          logging.debug( 'Retrieving "%s"...' % filename )
          wrk_file_path = self.packrat.getFile( file_url )
          self.repos[ repo_name ].addFile( wrk_file_path, file_type, filename, distro, distro_version, arch )

  def _updateMetaData( self ):
    logging.debug( 'libRepo: _updateMetaData' )
    for repo_name in self.repos:
      self.repos[ repo_name ].updateMetaData()

  def _updatePackage( self, repo_uri, repo_name, package_list ): # for now, skipping the db, the full sync will take care of it, hopfully nothing prunes files looking at the db before the db is updated
    logging.debug( 'libRepo: _updatePackage "%s" "%s" "%s"' % ( repo_uri, repo_name, package_list ) )
    packagefile_map = self.packrat.getPackageFiles( repo_uri, package_list )
    for packagefile_uri in packagefile_map:
      packagefile = packagefile_map[ packagefile_uri ]
      distroversion = self.distroversion_map[ packagefile[ 'distroversion' ] ]
      filename = os.path.basename( packagefile[ 'file' ] )
      file_path = self.repos[ repo_name ].manager.filePath( filename, distroversion[ 'distro' ], distroversion[ 'version' ], packagefile[ 'arch' ] )
      if not os.path.exists( file_path ):
        logging.debug( 'Retrieving "%s"...' % filename )
        wrk_file_path = self.packrat.getFile( packagefile[ 'file' ] )
        self.repos[ repo_name ].addFile( wrk_file_path, packagefile[ 'type' ], filename, distroversion[ 'distro' ], distroversion[ 'version' ], packagefile[ 'arch' ] )

    self.repos[ repo_name ].updateMetaData()

  def _checkDB( self, config_db ):
    conn = sqlite3.connect( config_db )
    cur = conn.cursor()
    cur.execute( 'SELECT COUNT(*) FROM "sqlite_master" WHERE type="table" and name="control";' )
    ( count, ) = cur.fetchone()
    if count == 0:
      conn.execute( 'CREATE TABLE "control" ( "key" text, "value" text );' )
      conn.commit()
      conn.execute( 'INSERT INTO "control" VALUES ( "version", "1" );' )
      conn.commit()

    cur = conn.cursor()
    cur.execute( 'SELECT "value" FROM "control" WHERE "key" = "version";' )
    ( version, ) = cur.fetchone()
    if version < '2':
      conn.execute( 'DROP TABLE IF EXISTS "repos";' )
      conn.commit()
      conn.execute( """CREATE TABLE "repos" (
    "name" char(50) PRIMARY KEY,
    "uri" char(100) NOT NULL UNIQUE,
    "manager" char(10) NOT NULL,
    "description" char(200) NOT NULL,
    "distro_map" char(400) NOT NULL,
    "created" datetime DEFAULT CURRENT_TIMESTAMP,
    "modified" datetime DEFAULT CURRENT_TIMESTAMP
  );""" )

      conn.execute( 'DROP TABLE IF EXISTS "files";' )
      conn.commit()
      conn.execute( """CREATE TABLE "files" (
    "repo" char(50),
    "uri" char(100) NOT NULL,
    "file_url" char(100) NOT NULL,
    "file_type" char(100) NOT NULL,
    "filename" char(50) NOT NULL,
    "distro" char(6) NOT NULL,
    "distro_version" char(20) NOT NULL,
    "arch" char(6) NOT NULL,
    "sha256" char(64) NOT NULL,
    "repo_data" text NOT NULL,
    "created" datetime DEFAULT CURRENT_TIMESTAMP,
    "modified" datetime DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (repo, uri),
    FOREIGN KEY (repo) REFERENCES repos(name)
  );""" )

      conn.commit()
      conn.execute( 'UPDATE "control" SET "value" = "2" WHERE "key" = "version";' )
      conn.commit()
