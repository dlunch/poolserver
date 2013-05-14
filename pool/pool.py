import eventlet
eventlet.monkey_patch()

import logging
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s:%(levelname)s:%(name)s:%(message)s')
logger = logging.getLogger('Pool')

import config
import work


class Pool(object):
    def __init__(self):
        if config.net == 'bitcoin':
            import net.bitcoin
            self.net = net.bitcoin.Bitcoin(
                config.rpc_host,
                config.rpc_port,
                config.rpc_username,
                config.rpc_password)
        elif config.net == 'bitcoin_testnet':
            import net.bitcoin_testnet
            self.net = net.bitcoin_testnet.BitcoinTestnet(
                config.rpc_host,
                config.rpc_port,
                config.rpc_username,
                config.rpc_password)

        self.generation_pubkey =\
            self.net.address_to_pubkey(config.generation_address)
        self.work = work.Work(self.net, self.net.difficulty_to_target(
            config.target_difficulty), self.generation_pubkey)

    def run(self):
        print self.work.getblocktemplate()
