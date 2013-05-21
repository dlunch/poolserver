from . import bitcoin


class BitcoinTestnet(bitcoin.Bitcoin):
    address_prefix = b'\x6f'

    def _get_default_port(self):
        return 18332
