import os
import logging
import shutil

from packratAgent.LocalRepoManager import LocalRepoManager, hashFile


class PyPiManager( LocalRepoManager ):
  def __init__( self, *args, **kargs ):
    super().__init__( *args, **kargs )
    self.entry_list = {}

  def filePath( self, filename, distro, distro_version, arch ):
    ( simple_dir, _ ) = filename.split( '-', 1 )
    package_dir = simple_dir[ 0:6 ]

    return '{0}/packages/{1}/{2}'.format( self.root_dir, package_dir, filename )

  def metadataFiles( self ):
    results = []

    for simple_dir in self.simple_dir:
      results.append( '{0}/simple/{1}/index.html'.format( self.root_dir, simple_dir ) )

    return results

  def addEntry( self, type, filename, distro, distro_version, arch ):
    if type != 'python':
      logging.warning( 'apt: New entry not a deb, skipping...' )
      return

    if distro != 'PyPI':
      logging.warning( 'apt: Not a debian distro, skipping...' )
      return

    logging.debug( 'pypi: Got Entry for package: %s', filename )
    ( simple_dir, _ ) = filename.split( '-', 1 )
    package_dir = simple_dir[ 0:6 ]
    package_path = '%s/packages/%s'.format( self.root_dir, package_dir )
    ( _, _, md5 ) = hashFile( package_dir )

    self.entry_list[ simple_dir ][ filename ] = ( package_path, md5 )

  def removeEntry( self, filename, distro, distro_version, arch ):
    ( simple_dir, _ ) = filename.split( '-', 1 )

    try:
      del self.entry_list[ simple_dir ][ filename ]
    except KeyError:
      logging.warning( 'pypi: unable to remove entry "%s" "%s", ignored.', simple_dir, filename )

  def loadFile( self, filename, temp_file, distro, distro_version, arch ):
    ( simple_dir, _ ) = filename.split( '-', 1 )
    package_dir = simple_dir[ 0:6 ]

    dir_path = '{0}/package/{1}/'.format( self.root_dir, package_dir )
    if not os.path.exists( dir_path ):
        os.makedirs( dir_path )

    file_path = os.path.join( dir_path, filename )
    shutil.move( temp_file, file_path )

  def writeMetadata( self ):
    for simple_dir in self.entry_list:
      wrk = open( '{0}/simple/{1}/index.html'.format( self.root_dir, simple_dir ), 'w' )
      wrk.write( """<!DOCTYPE html>
<html>
<head>
  <meta http-equiv="content-type" content="text/html; charset=UTF-8">
  <title>Links for {0}</title>
</head>
<body>
  <h1>Links for {0}</h1>""".format( simple_dir ) )
      for filename in self.entry_list[ simple_dir ]:
        ( package_path, md5  ) = self.entry_list[ simple_dir ][ filename ]
        wrk.write( '  <a href="/{0}#md5={1}" rel="internal">{2}</a><br>'.format( package_path, md5, filename ) )  # might need http:// prefix on <a/>

      wrk.write( """</body>
</html>""" )
      wrk.close()

  def sign( self, gpg_key ):
    pass  # PyPi dosen't support signing?
