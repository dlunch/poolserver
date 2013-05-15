import urllib2
import json
import base64
import hashlib
import logging
logger = logging.getLogger('Bitcoin')


from .. import util


class RPCError(Exception):
    pass


class Bitcoin(object):
    address_prefix = '\x00'

    def __init__(self, host, port, username, password):
        self.rpc_host = 'http://%s:%d' % (host, port)
        self.auth = base64.encodestring('%s:%s' % (username, password))\
                          .replace('\n', '')

    def _send_rpc(self, method, params=[]):
        request_data = json.dumps({'id': 0,
                                   'method': method,
                                   'params': params})

        req = urllib2.Request(self.rpc_host)
        req.add_header("Authorization", "Basic %s" % self.auth)
        req.add_header("Content-Type", "text/plain")
        req.add_data(request_data)

        file = urllib2.urlopen(req)
        result = file.read()
        file.close()
        result = json.loads(result)
        if result['error']:
            raise RPCError(result['error'])
        return result['result']

    def getblocktemplate(self):
        return self._send_rpc('getblocktemplate')

    @classmethod
    def address_to_pubkey(cls, address):
        data = util.base58_decode(address, 25)
        if data[0] != cls.address_prefix:
            raise Exception("Unknown address type")
        return data[1:21]

    @classmethod
    def pubkey_to_address(cls, pubkey):
        data = cls.address_prefix + pubkey
        checksum = hashlib.sha256(hashlib.sha256(data).digest()).digest()[:4]
        result = util.base58_encode(data + checksum)

        return util.base58_data[0]*(34-len(result)) + result

    @classmethod
    def difficulty_to_target(cls, difficulty):
        return (0xffff << (26*8) / difficulty
