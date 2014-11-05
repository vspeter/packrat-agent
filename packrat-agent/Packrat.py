import urllib
import urllib2
import socket
import logging
import json


class PackratConnectionException(Exception):
    pass


class PackratException(Exception):
    pass


class Packrat(object):

    def __init__(self, host, name, psk, proxy):
        self.host = host
        self.name = name
        self.psk = psk
        if proxy:
            logging.debug('Packrat: setting proxy to %s' % proxy)
            self.opener = urllib2.build_opener(
                urllib2.ProxyHandler({'http': proxy, 'https': proxy}))
        else:
            self.opener = urllib2.build_opener(urllib2.ProxyHandler(
                {}))  # no proxying, not matter what is in the enviornment

    def _doRequest(self, function, data, timeout=30):
        url = 'http://%s/repos/sync/?%s' % (
            self.host, urllib.urlencode({'function': function}))
        logging.debug('Packrat: url: "%s"' % url)
        logging.debug('Packrat: data:')

        POSTData = {}
        POSTData['data'] = json.dumps(data)
        POSTData['psk'] = self.psk
        POSTData['name'] = self.name
        try:
            resp = self.opener.open(
                url, data=urllib.urlencode(POSTData), timeout=timeout)

        except urllib2.HTTPError, e:
            logging.error('Packrat: _doRequest returned "%s"' % e.code)
            raise PackratConnectionException(
                'HTTPError Sending Request(%s), "%s"' % (e.code, e.reason))

        except urllib2.URLError, e:
            if isinstance(e.reason, socket.timeout):
                raise PackratException(
                    'Request Timeout after %s seconds.' % timeout)

            raise PackratConnectionException(
                'URLError Sending Request, "%s"' % e.reason)

        if resp.code != 200:
            raise PackratException(
                'Error with request, HTTP Error %s' % resp.status)

        result = resp.read()
        resp.close()
        return json.loads(result)

    def getFile(self, path, timeout=30):
        url = 'http://%s/%s' % (self.host, path)
        try:
            resp = self.opener.open(url, timeout=timeout)

        except urllib2.HTTPError, e:
            logging.error('Packrat: getFile returned "%s"' % e.code)
            raise PackratConnectionException(
                'HTTPError Retreiving File(%s), "%s"' % (e.code, e.reason))

        except urllib2.URLError, e:
            if isinstance(e.reason, socket.timeout):
                raise PackratException(
                    'Request Timeout after %s seconds.' % timeout)

            raise PackratConnectionException(
                'URLError Retreiving File, "%s"' % e.reason)

        if resp.code != 200:
            raise PackratException(
                'Error with file retreival, HTTP Error %s' % resp.status)

        tmpfile = open('/tmp/getfile', 'w')
        while True:
            buff = resp.read(4096)
            if not buff:
                break
            tmpfile.write(buff)

        tmpfile.close()

        return '/tmp/getfile'

    def getMirrorInfo(self):
        return self._doRequest('mirror.info', {})

    def syncStart(self):
        self._doRequest('sync.start', {})

    def syncComplete(self):
        self._doRequest('sync.complete', {})

    def getRepoList(self):
        return self._doRequest('repo.list', {})

    def getRepo(self, repo_id):
        return self._doRequest('repo.get', {'id': repo_id})

    def getPackage(self, package_id, release):
        return self._doRequest('package.get', {'id': package_id,
                               'release': release})

    def getPackageVersion(self, package_version_id, manager_type):
        return self._doRequest('package-version.get',
                               {'id': package_version_id,
                                'manager_type': manager_type})
