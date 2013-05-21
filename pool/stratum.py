import gevent
import gevent.event
import logging
import struct
logger = logging.getLogger('Stratum')

from . import util
from . import jsonrpc
from . import config
from .compat import str, bytes


class Stratum(object):
    seq = 0

    def __init__(self, file, work):
        self.file = file
        self.work = work
        self.extranonce1 = struct.pack('<I', Stratum.seq ^ 0xdeadbeef)
        self.difficulty = config.target_difficulty
        self.pusher = None
        Stratum.seq += 1

    def _send_stratum_message(self, message):
        logger.debug('Stratum send: %s' % message)
        self.file.write(bytes(message + '\n', 'ascii'))
        self.file.flush()

    def block_pusher(self):
        event = gevent.event.Event()
        while True:
            self._send_stratum_message(jsonrpc.create_request(
                                       'mining.set_difficulty',
                                       [self.difficulty]))

            self._send_stratum_message(jsonrpc.create_request(
                                       'mining.notify',
                                       self.work.get_stratum_work(
                                           self.extranonce1)))

            self.work.add_longpoll_event(event)
            event.wait()

    def handle(self, firstline):
        line = firstline
        while True:
            logger.debug('Stratum receive: %s' % line)
            _, response = jsonrpc.process_request(None, None, line, self)
            self._send_stratum_message(response)

            line = str(self.file.readline(), 'ascii')
            if not line:
                break

        if self.pusher:
            self.pusher.kill()

    def mining_subscribe(self, uri, params):
        self.pusher = gevent.spawn(self.block_pusher)
        nonce1 = util.b2h(self.extranonce1)
        return [['mining.notify', 'ae6812eb4cd7735a302a8a9dd95cf71f'],
                nonce1, config.extranonce2_size]

    def mining_authorize(self, uri, params):
        return True
