import hashlib


def hashFile( file_path ):
  md5 = hashlib.md5()
  sha1 = hashlib.sha1()
  sha256 = hashlib.sha256()
  try:
    wrk = open( file_path, 'r' )
  except IOError as e:
    if e.errno == 2:  # file not found
      return ( None, None, None )
    else:
      raise Exception( 'Unknown IOError "{0}" getting hash of file "{1}"'.format( e, file_path ) )

  buff = wrk.read( 4096 )
  while buff:
    md5.update( buff )
    sha1.update( buff )
    sha256.update( buff )
    buff = wrk.read( 4096 )
  return ( sha1.hexdigest(), sha256.hexdigest(), md5.hexdigest() )


class LocalRepoManager():
  def __init__( self, root_dir, component, repo_description, mirror_description, distro_map, gpg_key=None ):
    super().__init__()
    self.root_dir = root_dir
    self.component = component
    self.repo_description = repo_description
    self.mirror_description = mirror_description
    self.distro_map = distro_map
    self.gpg_key = gpg_key

  def filePath( self, filename, distro, distro_version, arch ):
    return None

  def metadataFiles( self ):
    return []

  def addEntry( self, type, filename, distro, distro_version, arch ):
    pass

  def removeEntry( self, filename, distro, distro_version, arch ):
    pass

  def loadFile( self, filename, temp_file, distro, distro_version, arch ):
    pass

  def writeMetadata( self ):
    pass

  def sign( self, gpg_key ):
    pass
