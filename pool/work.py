import gevent
import binascii
import logging
import struct

from .transaction import Transaction
from .coinbase_transaction import CoinbaseTransaction
import util
import config
from .errors import RPCError
from .merkletree import MerkleTree

logger = logging.getLogger('Work')


class Work(object):
    def __init__(self, net, target, generation_pubkey):
        self.seq = 0
        self.net = net
        self.target = target
        self.generation_pubkey = generation_pubkey

    def refresh_work(self):
        while True:
            try:
                self.block_template = self.net.getblocktemplate()
                break
            except RPCError as e:
                logger.error("Bitcoin RPCError:%r" % e)
            gevent.sleep(1)
        self.seq += 1
        self._create_tx()

    def _create_tx(self):
        self.coinbase_tx = CoinbaseTransaction(
            self.block_template, self.generation_pubkey)
        self.tx = [Transaction(x) for x in self.block_template['transactions']]
        self.merkle = MerkleTree([x.raw_tx for x in
                                  self.tx + [self.coinbase_tx]])

    def _serialize_target(self):
        target_bytes = util.long_to_bytes(self.target, 32)

        return binascii.hexlify(target_bytes)

    def _get_work_id(self):
        return binascii.hexlify(struct.pack('<I', self.seq ^ 0xdeadbeef))

    def getwork(self, params, uri):
        if uri == config.longpoll_uri:
            gevent.sleep(60)
        block_header = struct.pack('<I', self.block_template['version']) +\
            binascii.unhexlify(self.block_template['previousblockhash']) +\
            self.merkle.root +\
            struct.pack('<I', self.block_template['curtime']) +\
            binascii.unhexlify(self.block_template['bits']) +\
            '\x00\x00\x00\x00' + \
            ("\x80\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
            "\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
            "\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
            "\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x02\x80")

        # To little endian
        block_header = ''.join([block_header[x:x+4][::-1]
                               for x in range(0, len(block_header), 4)])

        #TODO midstate, hash1 (deprecated)
        return {'data': binascii.hexlify(block_header),
                'target': self._serialize_target()}

    def getblocktemplate(self, params, uri):
        """For worker"""

        longpollid = 'init'
        if 'longpollid' in params:
            longpollid = params['longpollid']
        if longpollid != 'init' or uri == config.longpoll_uri:
            gevent.sleep(60)
            longpollid = self._get_work_id()
        block_template = {k: self.block_template[k]
                          for k in self.block_template
                          if k not in
                          ['coinbasevalue', 'coinbaseaux', 'coinbaseflags']}

        block_template['target'] = self._serialize_target()
        block_template['mutable'] = ["coinbase/append", "submit/coinbase"]
        block_template['transactions'] = [x.serialize() for x in self.tx]
        block_template['coinbasetxn'] = self.coinbase_tx.serialize()

        #Long polling extension
        block_template['longpollid'] = longpollid
        block_template['expires'] = 120
        block_template['submitold'] = True
        block_template['longpolluri'] = config.longpoll_uri

        return block_template

    def get_stratum_work(self):
        result = []
        result.append(self._get_work_id())  # Job id
        prevblockhash = binascii.unhexlify(
            self.block_template['previousblockhash'])
        result.append(binascii.hexlify(prevblockhash[::-1]))

        coinbase_data = bytearray(self.coinbase_tx.raw_tx)
        orig_len = coinbase_data[41]
        firstpart_len = orig_len - 4 - config.extranonce2_size
        result.append(binascii.hexlify(coinbase_data[:42+firstpart_len]))
        result.append(binascii.hexlify(coinbase_data[42+orig_len:]))
        result.append([binascii.hexlify(x) for x in self.merkle.branches])
        result.append(binascii.hexlify(
                      struct.pack('>I', self.block_template['version'])))
        result.append(self.block_template['bits'])
        result.append(binascii.hexlify(
                      struct.pack('>I', self.block_template['curtime'])))
        result.append(True)

        return result
