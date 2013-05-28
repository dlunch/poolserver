from __future__ import absolute_import, unicode_literals

try:
    from urllib.request import Request, urlopen
    from urllib.error import HTTPError
except:
    from urllib2 import Request, HTTPError, urlopen
import os
import json
import base64
import hashlib
import logging

from pool import util
from pool.errors import RPCError
from pool.compat import str, bytes

logger = logging.getLogger('Bitcoin')


class Bitcoin(object):
    address_prefix = b'\x00'

    def __init__(self, host, port, username, password):
        if not host or not port or not username or not password:
            config_file = self._get_config_file()
            if not os.path.exists(config_file):
                raise Exception("Cannot find configuration")

            if not host:
                host = 'localhost'
            if not port:
                port = self._get_default_port()

            with open(config_file, 'r') as f:
                data = f.read()
            data = data.splitlines(False)
            for i in data:
                if i.find('=') == -1:
                    continue
                k, v = i.split('=')
                if k == 'rpcuser':
                    username = v
                elif k == 'rpcpassword':
                    password = v
                elif k == 'rpcport':
                    port = v

        self.rpc_host = 'http://%s:%r' % (host, port)
        self.auth = base64.encodestring(bytes('%s:%s' % (username, password),
                                        'ascii'))
        self.auth = str(self.auth, 'ascii').replace('\n', '')
        logger.debug('RPC Host: %s' % self.rpc_host)

    def _get_config_file(self):
        return os.path.join(os.path.expanduser('~/.bitcoin'), 'bitcoin.conf')

    def _get_default_port(self):
        return 8332

    def _send_rpc(self, method, params=[]):
        request_data = json.dumps({'id': 0,
                                   'method': method,
                                   'params': params})

        req = Request(self.rpc_host)
        req.add_header("Authorization", "Basic %s" % self.auth)
        req.add_header("Content-Type", "text/plain")
        req.add_data(bytes(request_data, 'ascii'))

        try:
            file = urlopen(req)
            result = file.read()
            file.close()
        except HTTPError as e:
            result = e.read()
        result = json.loads(str(result, 'ascii'))
        if result['error']:
            raise RPCError(result['error'])
        return result['result']

    def getblocktemplate(self):
        return self._send_rpc('getblocktemplate')

    def getinfo(self):
        return self._send_rpc('getinfo')

    def getmininginfo(self):
        return self._send_rpc('getmininginfo')

    def submitblock(self, block):
        return self._send_rpc('submitblock', [block])

    @classmethod
    def address_to_pubkey(cls, address):
        data = util.base58_decode(address, 25)
        if data[0] != cls.address_prefix[0]:
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
        # 208 == 26*8
        return int((0xffff << 208) / difficulty)

    @classmethod
    def hash_block_header(cls, header):
        return hashlib.sha256(hashlib.sha256(header).digest()).digest()[::-1]
