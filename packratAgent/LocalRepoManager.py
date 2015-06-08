import hashlib

def hashFile( filename ):
  md5 = hashlib.md5()
  sha1 = hashlib.sha1()
  sha256 = hashlib.sha256()
  wrk = open( filename, 'r' )
  buff = wrk.read( 4096 )
  while buff:
    md5.update( buff )
    sha1.update( buff )
    sha256.update( buff )
    buff = wrk.read( 4096 )
  return ( sha1.hexdigest(), sha256.hexdigest(), md5.hexdigest() )


class LocalRepoManager( object ):
  def __init__( self, root_dir, component, repo_description, mirror_description ):
    self.root_dir = root_dir
    self.component = component
    self.repo_description = repo_description
    self.mirror_description = mirror_description

  def addEntry( self, type, filename, distro, distro_version, arch ):
    pass

  def loadFile( self, file_name, temp_file, distro, distro_version, arch ):
    pass

  def checkFile( self, file_name, distro, distro_version, arch ):
    return True

  def writeMetadata( self ):
    pass

  def sign( self, gpg_key ):
    pass
