import gevent
import gevent.monkey
import gevent.server
gevent.monkey.patch_all()

import traceback
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

        while True:
            try:
                version = self.net.getinfo()
                info = self.net.getmininginfo()
                break
            except Exception as e:
                logger.error("Cannot connect to bitcoind: %r" % e)
            gevent.sleep(1)


        self.generation_pubkey =\
            self.net.address_to_pubkey(config.generation_address)
        self.target_difficulty =\
            self.net.difficulty_to_target(config.target_difficulty)
        self.work = work.Work(self.net, self.target_difficulty,
                              self.generation_pubkey)

    def run(self):
        server = gevent.server.StreamServer((config.worker_host,
                                             config.worker_port),
                                             self.serve_worker)
        server.serve_forever()

    def serve_worker(self, socket, remote):
        pass
