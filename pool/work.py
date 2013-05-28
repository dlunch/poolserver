from __future__ import absolute_import, unicode_literals

import gevent
import gevent.event
import logging
import struct
import traceback
import hashlib

from pool.transaction import Transaction
from pool.coinbase_transaction import CoinbaseTransaction
from pool import util
from pool import config
from pool.errors import RPCError
from pool.merkletree import MerkleTree
from pool import user

logger = logging.getLogger('Work')


class Work(object):
    def __init__(self, net, generation_pubkey):
        self.seq = 0
        self.net = net
        self.generation_pubkey = generation_pubkey
        self.longpoll_events = []
        self.work_data = {}
        self.block_event = gevent.event.Event()
        self.block_template = None

    def add_longpoll_event(self, event):
        self.longpoll_events.append(event)

    def start_refresher(self):
        self.wait_event = gevent.event.Event()
        gevent.spawn(self.refresher)
        self.wait_event.wait()
        self.wait_event = None

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
            if not self.block_template or\
                self.block_template['height'] != block_template['height'] or\
                self.block_template['transactions'] !=\
                    block_template['transactions']:

                self.block_template = block_template
                self.tx = [Transaction(x) for x in
                           self.block_template['transactions']]
                events = self.longpoll_events
                self.longpoll_events = []
                self.work_data = {}

                merkle = MerkleTree([b''] + [x.raw_tx for x in self.tx])
                self.merkle_branches = merkle.branches

                for i in events:
                    i.set()
                if self.wait_event:
                    self.wait_event.set()

                logger.debug('Block refresh done')
            self.block_event.wait(60)
            self.block_event.clear()

    def create_coinbase_tx(self, extranonce1, extranonce2):
        return CoinbaseTransaction(
            self.block_template, self.generation_pubkey,
            extranonce1, extranonce2)

    def _get_target(self, difficulty):
        target = self.net.difficulty_to_target(difficulty)
        return util.long_to_bytes(target, 32)

    def get_work_id(self):
        self.seq += 1
        return util.b2h(struct.pack(b'<I', self.seq))

    def process_block(self, block, auth):
        logger.debug('process_block %s' % util.b2h(block))
        hash = hashlib.sha256(
            hashlib.sha256(block[:80]).digest()).digest()[::-1]
        logger.debug('hash %s' % util.b2h(hash))
        logger.debug('target %s' %
                     util.b2h(self._get_target(auth['difficulty'])))
        hash_long = util.bytes_to_long(hash)
        if hash_long > self.target:
            logger.debug("Hash is bigger than target")
            return False
        real_target = util.bytes_to_long(
            util.h2b(self.block_template['target']))
        logger.debug('real target %s' % self.block_template['target'])
        user.share_accepted(auth['username'])
        if hash_long < real_target:
            logger.debug("Found block candidate")
            for i in self.tx:
                block += i.raw_tx
            logger.debug("Submitting %s" % util.b2h(block))
            result = self.net.submitblock(block)
            if result is None:
                user.block_found(auth['username'],
                                 self.block_template['height'])

        return True

    def create_block_header(self, merkle_root, ntime, nonce):
        version = self.block_template['version']

        prevblockhash = util.h2b(
            self.block_template['previousblockhash'])[::-1]
        bits = util.h2b(self.block_template['bits'])[::-1]

        block_header = struct.pack('<I', version) +\
            prevblockhash +\
            merkle_root +\
            ntime +\
            bits +\
            nonce

        return block_header

    def getwork(self, params, uri, auth):
        if len(params) > 0:
            block = util.h2b(params[0])
            merkle_root = block[36:68]

            if merkle_root not in self.work_data:
                logger.error("Unknown worker submission")
                return False
            coinbase_tx = self.work_data[merkle_root].raw_tx
            block += util.encode_size(len(self.tx) + 1)
            block += coinbase_tx

            result = self.process_block(block, auth)

            del self.work_data[merkle_root]
            return result

        if uri == config.longpoll_uri:
            event = gevent.event.Event()
            self.add_longpoll_event(event)
            event.wait()

        coinbase_tx = self.create_coinbase_tx(
            util.h2b(self.get_work_id()), b'')
        merkle_root = MerkleTree.merkle_root_from_branch(
            coinbase_tx.raw_tx, self.merkle_branches)
        ntime = struct.pack('<I', self.block_template['curtime'])
        block_header = self.create_block_header(merkle_root, ntime,
                                                b'\x00\x00\x00\x00')
        block_header += (b"\x80\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
                         b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
                         b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
                         b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x02\x80")

        self.work_data[merkle_root] = coinbase_tx

        # To little endian
        block_header = b''.join([block_header[x:x+4][::-1]
                                for x in range(0, len(block_header), 4)])
        target = util.b2h(self._get_target(auth['difficulty'])[::-1])
        block_header = util.b2h(block_header)
        #TODO midstate, hash1 (deprecated)
        return {'data': block_header,
                'target': target}

    def getblocktemplate(self, params, uri, auth):
        """For worker"""

        longpollid = 'init'
        mode = 'template'  # For older client
        data = None
        for i in params:
            if 'longpollid' in i:
                longpollid = i['longpollid']
            if 'mode' in i:
                mode = i['mode']
            if 'data' in i:
                data = i['data']
        if mode == 'submit':
            try:
                block = util.h2b(data)
                sizelen, tx_size = util.decode_size(block[80:89])
                ptr = 80 + sizelen

                txlen = CoinbaseTransaction.verify(block[ptr:],
                                                   self.generation_pubkey)
                result = self.process_block(block[:ptr+txlen], auth)
                if result:
                    return None
            except:
                logger.error("Exception while processing block")
                logger.error(traceback.format_exc())
            return 'Rejected'

        if longpollid != 'init' or uri == config.longpoll_uri:
            event = gevent.event.Event()
            self.add_longpoll_event(event)
            event.wait()
            longpollid = self.get_work_id()
        coinbase_tx = self.create_coinbase_tx(b'', b'')
        block_template = {k: self.block_template[k]
                          for k in self.block_template
                          if k not in
                          ['coinbasevalue', 'coinbaseaux', 'coinbaseflags']}

        block_template['target'] = util.b2h(
            self._get_target(auth['difficulty']))
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
        result.append(self.get_work_id())  # Job id
        prevblockhash = util.h2b(
            self.block_template['previousblockhash'])[::-1]
        prevblockhash = b''.join([prevblockhash[x:x+4][::-1]
                                 for x in range(0, len(prevblockhash), 4)])
        result.append(util.b2h(prevblockhash))

        coinbase_tx = self.create_coinbase_tx(
            extranonce1, b'\x00\x00\x00\x00')
        coinbase_data = bytearray(coinbase_tx.raw_tx)
        orig_len = coinbase_data[41]
        firstpart_len = orig_len - 4 - config.extranonce2_size
        result.append(util.b2h(coinbase_data[:42+firstpart_len]))
        result.append(util.b2h(coinbase_data[42+orig_len:]))
        result.append([util.b2h(x) for x in self.merkle_branches])
        result.append(util.b2h(
                      struct.pack('>I', self.block_template['version'])))
        result.append(self.block_template['bits'])
        result.append(util.b2h(
                      struct.pack('>I', self.block_template['curtime'])))
        result.append(True)

        return result

    def submitblock(self, params, uri, auth):
        block = util.h2b(params[0])
        result = self.process_block(block, auth)
        if not result:
            return "Rejected"
        return None
