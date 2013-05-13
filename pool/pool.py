import eventlet
eventlet.monkey_patch()

import logging
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s:%(levelname)s:%(name)s:%(message)s')
logger = logging.getLogger('Pool')

import config
import net.bitcoin
import work


class Pool(object):
    def __init__(self):
        if config.net == 'bitcoin':
            self.net = net.bitcoin.Bitcoin(
                config.rpc_host,
                config.rpc_port,
                config.rpc_username,
                config.rpc_password)
        self.generation_pubkey =\
            self.net.address_to_pubkey(config.generation_address)
        self.work = work.Work(self.net, self.net.difficulty_to_target(
            config.target_difficulty))

    def run(self):
        pass
