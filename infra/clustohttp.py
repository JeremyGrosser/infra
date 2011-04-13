#!/usr/bin/env python

try:
    import simplejson as json
except ImportError:
    import json

from urllib import urlencode, quote
from urlparse import urlsplit, urljoin
from time import time
import httplib
import logging
import os

handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('%(levelname)s %(message)s'))

log = logging.getLogger('clustohttp')
log.addHandler(handler)
#log.setLevel(logging.DEBUG)

try:
    AUTH_BASIC = file('%s/.infra' % os.environ['HOME'], 'r').read()
except:
    AUTH_BASIC = None

def request(method, url, body='', headers={}):
    log.debug('%s %s' % (method, url))
    start = time()
    if type(body) != type(''):
        body = urlencode(body)
    url = urlsplit(url, 'http')

    if AUTH_BASIC:
        headers['Authorization'] = 'Basic %s' % AUTH_BASIC.encode('base64')

    conn = httplib.HTTPConnection(url.hostname, url.port)
    if url.query:
        query = '%s?%s' % (url.path, url.query)
    else:
        query = url.path
    conn.request(method, query, body, headers)
    response = conn.getresponse()
    length = response.getheader('Content-length', None)
    if length:
        data = response.read(int(length))
    else:
        data = response.read()
    conn.close()
    if response.status >= 400:
        log.error('Server error %s: %s' % (response.status, data))
    log.debug('Response time: %.03f' % (time() - start))
    return (response.status, response.getheaders(), data)

class ClustoProxy(object):
    def __init__(self, url):
        self.url = url

    def get_entities(self, **kwargs):
        for k, v in kwargs.items():
            kwargs[k] = json.dumps(v)
        status, headers, response = request('POST', self.url + '/query/get_entities?%s' % urlencode(kwargs))
        if status != 200:
            raise Exception(response)
        return [EntityProxy(self.url, x) for x in json.loads(response)]

    def get(self, name):
        status, headers, response = request('GET', self.url + '/query/get?name=%s' % quote(name))
        if status != 200:
            raise Exception(response)
        return [EntityProxy(self.url, x['object'], cache=x) for x in json.loads(response)]

    def get_by_name(self, name):
        status, headers, response = request('GET', self.url + '/query/get_by_name?name=%s' % quote(name))
        if status != 200:
            raise Exception(response)
        obj = json.loads(response)
        return EntityProxy(self.url, obj['object'], cache=obj)

    def get_from_pools(self, pools, clusto_types=None):
        url = self.url + '/query/get_from_pools?pools=%s' % ','.join(pools)
        if clusto_types:
            url += '&types=' + ','.join(clusto_types)
        status, headers, response = request('GET', url)
        if status != 200:
            raise Exception(response)
        return [EntityProxy(self.url, x) for x in json.loads(response)]

    def get_ip_manager(self, ip):
        status, headers, response = request('GET', self.url + '/query/get_ip_manager?ip=%s' % ip)
        if status != 200:
            raise Exception(response)
        return EntityProxy(self.url, json.loads(response))

class EntityProxy(object):
    def __init__(self, baseurl, path, cache={}):
        self.baseurl = baseurl
        self.path = path
        self.cache = cache

        self.url = baseurl + path
        self.name = self.path.rsplit('/', 1)[1]

    def __getattr__(self, action):
        def method(**kwargs):
            data = {}
            for k, v in kwargs.items():
                if isinstance(v, bool):
                    v = int(v)
                if not type(v) in (int, str, unicode):
                    v = json.dumps(v)
                data[k] = v
            if data:
                status, headers, response = request('GET', '%s/%s?%s' % (self.url, action, urlencode(data)))
            else:
                status, headers, response = request('GET', '%s/%s' % (self.url, action))
            if status != 200:
                raise Exception(response)
            if response:
                return json.loads(response)
            else:
                return None
        return method

    @property
    def type(self):
        return self.path.lstrip('/').split('/', 1)[0]

    def show(self, use_cache=True):
        if use_cache and self.cache:
            result = self.cache
        else:
            result = self.__getattr__('show')()
            self.cache = result
        return result

    def contents(self, use_cache=True):
        if use_cache and 'contents' in self.cache:
            result = self.cache['contents']
        else:
            result = self.show()['contents']
            self.cache['contents'] = result
        return [EntityProxy(self.baseurl, x) for x in result]

    def parents(self, use_cache=True):
        if use_cache and 'parents' in self.cache:
            result = self.cache['parents']
        else:
            result = self.show()['parents']
            self.cache['parents'] = result
        return [EntityProxy(self.baseurl, x) for x in result]

    def attrs(self, use_cache=True, **kwargs):
        if use_cache and 'attrs' in self.cache:
            result = []
            for attr in self.cache['attrs']:
                if 'key' in kwargs and kwargs['key'] != attr['key']:
                    continue
                if 'subkey' in kwargs and kwargs['subkey'] != attr['subkey']:
                    continue
                if 'number' in kwargs and kwargs['number'] != attr['number']:
                    continue
                if 'value' in kwargs and kwargs['value'] != attr['value']:
                    continue
                result.append(attr)
        else:
            result = self.__getattr__('attrs')(**kwargs)['attrs']
        return result

    def attr_values(self, **kwargs):
        return [x['value'] for x in self.attrs(**kwargs)]

    def attr_value(self, **kwargs):
        a = self.attrs(**kwargs)
        if len(a) > 1:
            raise Exception('Too many values for attr_value: %i' % len(a))
        if not a:
            return None
        return a[0]['value']

    def set_port_attr(self, porttype, portnum, key, value):
        return self.__getattr__('set_port_attr')(porttype=porttype, portnum=portnum, key=key, value=value)

    def get_port_attr(self, porttype, portnum, key):
        return self.__getattr__('get_port_attr')(porttype=porttype, portnum=portnum, key=key)

    def __str__(self):
        return self.path

    def __repr__(self):
        return 'EntityProxy(%s, %s)' % (repr(self.baseurl), repr(self.path))

    def __cmp__(self, other):
        return cmp(self.name, other.name)

    def __eq__(self, other):
        return self.name == other.name

    def __hash__(self):
        return hash(self.name)


def test():
    clusto = ClustoProxy('http://127.0.0.1:9996')
    server = clusto.get_entities(attrs=[{'subkey': 'mac', 'value': '00:a0:d1:e9:3d:dc'}])
    server = server[0]
    print server
    assert server.name == 's0104'
    attr = server.get_port_attr('nic-eth', 1, 'mac')
    server.set_port_attr('nic-eth', 1, 'mac', attr)
    newattr = server.get_port_attr('nic-eth', 1, 'mac')
    print repr((attr, newattr))
    assert newattr == attr
    #print server.parents()
    #obj = clusto.get_by_name('s1100')
    #pprint(obj.ports())
    #pprint(obj.attrs(key='dhcp', merge_container_attrs=True))
    #webservers = clusto.get_from_pools(['webservers-lolcat', 'production'])
    #pprint(webservers)
    #pprint(webservers[0].contents())

if __name__ == '__main__':
    test()
