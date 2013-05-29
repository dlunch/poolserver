from __future__ import absolute_import, unicode_literals

from pool.net import litecoin


class LitecoinTestnet(litecoin.Litecoin):
    address_prefix = b'\x6f'

    def _get_default_port(self):
        return 19332
