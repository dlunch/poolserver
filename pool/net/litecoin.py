from __future__ import absolute_import, unicode_literals

import os

from pool.net import bitcoin
from pool.net.scrypt import scrypt


class Litecoin(bitcoin.Bitcoin):
    address_prefix = b'\x30'

    def _get_default_port(self):
        return 9332

    def _get_config_file(self):
        return os.path.join(os.path.expanduser('~/.litecoin'), 'litecoin.conf')

    def getblocktemplate(self):
        return self._send_rpc('getblocktemplate', [{}])

    def submitblock(self, data):
        return self._send_rpc('getblocktemplate',
                              [{'data': data, 'mode': 'submit'}])

    @classmethod
    def hash_block_header(cls, header):
        return scrypt.get_scrypt_hash(header)[::-1]

    @classmethod
    def difficulty_to_target(cls, difficulty):
        return int((0xffff << 224) / difficulty)
