from __future__ import absolute_import, unicode_literals

from pool.net import bitcoin
from pool.net.scrypt import scrypt


class Litecoin(bitcoin.Bitcoin):
    address_prefix = b'\x30'

    def _get_default_port(self):
        return 9332

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
