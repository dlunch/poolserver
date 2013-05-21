import gevent
import gevent.event
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
        self.longpoll_events = []
        self.block_event = gevent.event.Event()

    def add_longpoll_event(self, event):
        self.longpoll_events.append(event)

    def start_refresher(self):
        gevent.spawn(self.refresher)

    def refresher(self):
        while True:
            logger.debug('Block refresh')
            while True:
                try:
                    block_template = self.net.getblocktemplate()
                    break
                except RPCError as e:
                    logger.error("Bitcoin RPCError:%r" % e)
                gevent.sleep(1)

            # XXX GIL will prevent these values read from other thread
            self.block_template = block_template
            self.tx = [Transaction(x) for x in
                       self.block_template['transactions']]
            events = self.longpoll_events
            self.longpoll_events = []
            for i in events:
                i.set()
            self.block_event.wait(60)
            self.block_event.clear()

    def _create_coinbase_tx(self, extranonce1, extranonce2):
        return CoinbaseTransaction(
            self.block_template, self.generation_pubkey,
            extranonce1, extranonce2)

    def _create_merkle(self, coinbase_tx):
        return MerkleTree([x.raw_tx for x in self.tx + [coinbase_tx]])

    def _serialize_target(self):
        return util.long_to_bytes(self.target, 32)

    def _get_work_id(self):
        self.seq += 1
        return binascii.hexlify(struct.pack('<I', self.seq ^ 0xdeadbeef))

    def getwork(self, params, uri):
        if uri == config.longpoll_uri:
            event = gevent.event.Event()
            self.add_longpoll_event(event)
            event.wait()
        coinbase_tx = self._create_coinbase_tx(
            binascii.unhexlify(self._get_work_id()), '')
        merkle = self._create_merkle(coinbase_tx)
        prevblockhash = binascii.unhexlify(
            self.block_template['previousblockhash'])[::-1]
        prevblockhash = ''.join([prevblockhash[x:x+4]
                                for x in range(0, len(prevblockhash), 4)])

        block_header = struct.pack('<I', self.block_template['version']) +\
            prevblockhash +\
            merkle.root +\
            struct.pack('<I', self.block_template['curtime']) +\
            binascii.unhexlify(self.block_template['bits'])[::-1] +\
            '\x00\x00\x00\x00' + \
            ("\x80\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
            "\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
            "\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
            "\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x02\x80")

        # To little endian
        block_header = ''.join([block_header[x:x+4][::-1]
                               for x in range(0, len(block_header), 4)])
        target = binascii.hexlify(self._serialize_target()[::-1])

        #TODO midstate, hash1 (deprecated)
        return {'data': binascii.hexlify(block_header),
                'target': target}

    def getblocktemplate(self, params, uri):
        """For worker"""

        longpollid = 'init'
        if len(params) > 1 and 'longpollid' in params[0]:
            longpollid = params[0]['longpollid']
        if longpollid != 'init' or uri == config.longpoll_uri:
            event = gevent.event.Event()
            self.add_longpoll_event(event)
            event.wait()
            longpollid = self._get_work_id()
        coinbase_tx = self._create_coinbase_tx('', '')
        block_template = {k: self.block_template[k]
                          for k in self.block_template
                          if k not in
                          ['coinbasevalue', 'coinbaseaux', 'coinbaseflags']}

        block_template['target'] = binascii.hexlify(self._serialize_target())
        block_template['mutable'] = ["coinbase/append", "submit/coinbase"]
        block_template['transactions'] = [x.serialize() for x in self.tx]
        block_template['coinbasetxn'] = coinbase_tx.serialize()

        #Long polling extension
        block_template['longpollid'] = longpollid
        block_template['expires'] = 120
        block_template['submitold'] = True
        block_template['longpolluri'] = config.longpoll_uri

        return block_template

    def get_stratum_work(self, extranonce1):
        result = []
        result.append(self._get_work_id())  # Job id
        prevblockhash = binascii.unhexlify(
            self.block_template['previousblockhash'])[::-1]
        prevblockhash = ''.join([prevblockhash[x:x+4][::-1]
                                for x in range(0, len(prevblockhash), 4)])
        result.append(binascii.hexlify(prevblockhash))

        coinbase_tx = self._create_coinbase_tx(
            extranonce1, '\x00\x00\x00\x00')
        merkle = self._create_merkle(coinbase_tx)
        coinbase_data = bytearray(coinbase_tx.raw_tx)
        orig_len = coinbase_data[41]
        firstpart_len = orig_len - 4 - config.extranonce2_size
        result.append(binascii.hexlify(coinbase_data[:42+firstpart_len]))
        result.append(binascii.hexlify(coinbase_data[42+orig_len:]))
        result.append([binascii.hexlify(x) for x in merkle.branches])
        result.append(binascii.hexlify(
                      struct.pack('>I', self.block_template['version'])))
        result.append(self.block_template['bits'])
        result.append(binascii.hexlify(
                      struct.pack('>I', self.block_template['curtime'])))
        result.append(True)

        return result
