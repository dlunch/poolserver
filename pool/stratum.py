import gevent
import gevent.event
import logging
import struct
logger = logging.getLogger('Stratum')

from . import util
from . import jsonrpc
from . import config
from .compat import str, bytes
from .merkletree import MerkleTree


class Stratum(object):
    seq = 0

    def __init__(self, file, work):
        self.file = file
        self.work = work
        self.last_work_id = ''
        self.extranonce1 = struct.pack('<I', Stratum.seq)
        self.difficulty = config.target_difficulty
        self.pusher = None
        Stratum.seq += 1

    def _send_stratum_message(self, message):
        logger.debug('Stratum send: %s' % message)
        self.file.write(bytes(message + '\n', 'ascii'))
        self.file.flush()

    def block_pusher(self):
        try:
            event = gevent.event.Event()
            while True:
                self._send_stratum_message(jsonrpc.create_request(
                                           'mining.set_difficulty',
                                           [self.difficulty]))

                params = self.work.get_stratum_work(self.extranonce1)
                self._send_stratum_message(jsonrpc.create_request(
                                           'mining.notify', params))

                self.last_work_id = params[0]
                self.work.add_longpoll_event(event)
                event.wait()
                event.clear()
        except:
            pass

    def handle(self, firstline):
        try:
            line = firstline
            while True:
                logger.debug('Stratum receive: %s' % line)
                _, response = jsonrpc.process_request(None, None, line, self)
                self._send_stratum_message(response)

                line = str(self.file.readline(), 'ascii')
                if not line:
                    break
        except:
            pass
        finally:
            if self.pusher:
                self.pusher.kill()

    def mining_subscribe(self, params, uri):
        self.pusher = gevent.spawn(self.block_pusher)
        nonce1 = util.b2h(self.extranonce1)
        return [['mining.notify', 'ae6812eb4cd7735a302a8a9dd95cf71f'],
                nonce1, config.extranonce2_size]

    def mining_authorize(self, params, uri):
        return True

    def mining_submit(self, params, uri):
        worker_name = params[0]  # From authorize
        work_id = params[1]
        extranonce2 = params[2]
        ntime = util.h2b(params[3])[::-1]
        nonce = util.h2b(params[4])[::-1]

        logger.debug("Received block from %s" % worker_name)

        if work_id != self.last_work_id:
            logger.debug("Wrong work id (%s expected, %s received)" %
                         (self.last_work_id, work_id))
            return False

        coinbase_tx = self.work.create_coinbase_tx(self.extranonce1,
                                                   util.h2b(extranonce2))
        merkle_root = MerkleTree.merkle_root_from_branch(
            coinbase_tx.raw_tx, self.work.merkle_branch)
        block_header = self.work.create_block_header(merkle_root, ntime, nonce)

        block_header += util.encode_size(len(self.work.tx) + 1) +\
            coinbase_tx.raw_tx
        return self.work.process_block(block_header)
