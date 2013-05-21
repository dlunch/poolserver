import gevent
import gevent.event
import logging
import struct
import binascii
logger = logging.getLogger('Stratum')

import jsonrpc
import config


class Stratum(object):
    seq = 0

    def __init__(self, file, work):
        self.file = file
        self.work = work
        self.extranonce1 = Stratum.seq ^ 0xdeadbeef
        self.difficulty = config.target_difficulty
        Stratum.seq += 1

    def _send_stratum_message(self, message):
        logger.debug('Stratum send: %s' % message)
        self.file.write(message + '\n')
        self.file.flush()

    def block_pusher(self):
        event = gevent.event.Event()
        while True:
            self._send_stratum_message(jsonrpc.create_request(
                                       'mining.set_difficulty',
                                       [self.difficulty]))

            self._send_stratum_message(jsonrpc.create_request(
                                       'mining.notify',
                                       self.work.get_stratum_work()))

            self.work.add_longpoll_event(event)
            event.wait()

    def handle(self, firstline):
        line = firstline
        while True:
            logger.debug('Stratum receive: %s' % line)
            _, response = jsonrpc.process_request(None, None, line, self)
            self._send_stratum_message(response)

            line = self.file.readline()
            if not line:
                break

        self.pusher.kill()

    def mining_subscribe(self, uri, params):
        self.pusher = gevent.spawn(self.block_pusher)
        nonce1 = binascii.hexlify(struct.pack('<I', self.extranonce1))
        return [['mining.notify', 'ae6812eb4cd7735a302a8a9dd95cf71f'],
                nonce1, config.extranonce2_size]

    def mining_authorize(self, uri, params):
        return True
