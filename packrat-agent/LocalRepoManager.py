import hashlib


def hashFile(filename):
    md5 = hashlib.md5()
    sha1 = hashlib.sha1()
    sha256 = hashlib.sha256()
    wrk = open(filename, 'r')
    buff = wrk.read(4096)
    while buff:
        md5.update(buff)
        sha1.update(buff)
        sha256.update(buff)
        buff = wrk.read(4096)
    return (sha1.hexdigest(), sha256.hexdigest(), md5.hexdigest())


class LocalRepoManager(object):
    def __init__(self, root_dir, distro, component, repo_description,
                 mirror_description):
        self.root_dir = root_dir
        self.distro = distro
        self.component = component
        self.repo_description = repo_description
        self.mirror_description = mirror_description
