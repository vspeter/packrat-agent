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

    def _createURL(self, resource, key, subresource=None):
        if subresource:
            url = 'http://%s/api/v1/%s/%s/%s/?format=json' % (self.host,
                                                              resource, key,
                                                              subresource)
        else:
            url = 'http://%s/api/v1/%s/%s/?format=json' % (self.host,
                                                           resource, key)
        logging.debug('Packrat: API URL: "%s"' % url)
        return url

    def _doGETRequest(self, module, key, subresource=None, timeout=30):
        url = self._createURL(module, key, subresource)

        try:
            resp = self.opener.open(url, timeout=timeout)

        except urllib2.HTTPError, e:
            logging.error('Packrat: _doGETRequest returned "%s"' % e.code)
            raise PackratConnectionException(
                'HTTPError Sending Request(%s), "%s"' % (e.code, e.reason))

        except urllib2.URLError, e:
            if isinstance(e.reason, socket.timeout):
                raise PackratException(
                    'Packrat: _doGETRequest Timeout after %s seconds.' %
                    timeout)

            raise PackratConnectionException(
                'Packrat: _doGETRequest URLError Sending Request, "%s"' %
                e.reason)

        if resp.code != 200:
            raise PackratException(
                'Packrat: _doGETRequest Error with request, HTTP Error %s' %
                resp.status)

        result = resp.read()
        resp.close()
        return json.loads(result)

    def _doPOSTRequest(self, module, key, data, timeout=30):
        url = self._createURL(module, key)

        logging.debug('Packrat: data:')
        logging.debug('Packrat: %s' % data)

        try:
            resp = self.opener.open(url,
                                    data=urllib.urlencode(json.dumps(data)),
                                    timeout=timeout)

        except urllib2.HTTPError, e:
            logging.error('Packrat: _doPOSTRequest returned "%s"' % e.code)
            raise PackratConnectionException(
                'HTTPError Sending Request(%s), "%s"' % (e.code, e.reason))

        except urllib2.URLError, e:
            if isinstance(e.reason, socket.timeout):
                raise PackratException(
                    'Packrat: _doPOSTRequest Timeout after %s seconds.' %
                    timeout)

            raise PackratConnectionException(
                'Packrat: _doPOSTRequest URLError Sending Request, "%s"' %
                e.reason)

        if resp.code != 200:
            raise PackratException(
                'Packrat: _doPOSTRequest Error with request, HTTP Error %s' %
                resp.status)

        result = resp.read()
        resp.close()
        return json.loads(result)

    def getFile(self, path, timeout=30):
        url = 'http://%s%s' % (self.host, path)
        logging.debug('Packrat: File URL: "%s"' % url)
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

    def getMirror(self):
        return self._doGETRequest('mirror', self.name)

    def syncStart(self):
        return
        self._doRequest('sync.start', {})

    def syncComplete(self):
        return
        self._doRequest('sync.complete', {})

    def getRepo(self, repo_id):
        return self._doGETRequest('repo', repo_id)

    def getPackages(self, repo_id):
        return self._doGETRequest('repo', repo_id, 'packages')['objects']

    def getPackageFiles(self, repo_id, package_name):
        return self._doGETRequest('repo', repo_id,
                                  'files/%s' % package_name)['objects']

    def getDistroVersion(self, version_id):
        return self._doGETRequest('distroversion', version_id)
