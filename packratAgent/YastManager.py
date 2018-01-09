from packratAgent.LocalRepoManager import LocalRepoManager


class YaSTManager( LocalRepoManager ):
  def __init__( self, *args, **kargs ):
    super().__init__( *args, **kargs )
