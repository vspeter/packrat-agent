from packratAgent.LocalRepoManager import LocalRepoManager

"""
https://docs.docker.com/v1.6/reference/api/registry_api/

https://docs.docker.com/registry/spec/api/#overview
http://ops4j.github.io/ramler/0.6.0/registry/#Resources
"""


class DockerManager( LocalRepoManager ):
  def __init__( self, *args, **kargs ):
    super().__init__( *args, **kargs )

  def filePaths( self, filename, distro, distro_version, arch ):
    return []

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
