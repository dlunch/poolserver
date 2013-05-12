import urllib2
import json
import base64
import time


class RPCError(Exception):
    pass


class Bitcoin(object):
    address_prefix = '\x00'

    def __init__(self, host, port, username, password):
        self.rpc_host = 'http://%s:%d' % (host, port)
        self.auth = base64.encodestring('%s:%s' % (username, password))\
                          .replace('\n', '')

    def _send_rpc(self, method, params=[]):
        request_data = json.dumps({'id': 0, 'method': method, 'params': params})

        while True:
            try:
                req = urllib2.Request(self.rpc_host)
                req.add_header("Authorization", "Basic %s" % self.auth)
                req.add_header("Content-Type", "text/plain")
                req.add_data(request_data)
                
                file = urllib2.urlopen(req)

                result = ''
                while True:
                    data = file.read(1024)
                    if not data:
                        break
                    result += data
                file.close()
                result = json.loads(result)
                if result['error']:
                    raise RPCError(result['error'])
                break
            except IOError:
                print 'Bitcoin RPC IOError'
                time.sleep(1)
        return result['result']

    def getblocktemplate(self):
        return self._send_rpc('getblocktemplate')
