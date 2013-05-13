import bitcoin

class BitcoinTestnet(bitcoin.Bitcoin):
    address_prefix = '\x6f'
