from LocalRepoManager import LocalRepoManager


class ZypperManager(LocalRepoManager):
    def __init__(self, *args, **kargs):
        super(ZypperManager).__init__(*args, **kargs)

    def addEntry(self, type, arch, filename):
        if type != 'rpm':
            print 'WARNING! New entry not a rpm, skipping...'
            return
