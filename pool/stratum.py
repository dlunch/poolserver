import gevent
import gevent.event
import logging
logger = logging.getLogger('Stratum')

import jsonrpc


class Stratum(object):
    def __init__(self, file, work):
        self.file = file
        self.work = work

    def _send_stratum_message(self, message):
        logger.debug('Stratum send: %s' % message)
        self.file.write(message + '\n')
        self.file.flush()

    def block_pusher(self):
        event = gevent.event.Event()
        while True:
            request = jsonrpc.create_request('mining.notify',
                                             self.work.get_stratum_work())
            self._send_stratum_message(request)

            self.work.add_longpoll_event(event)
            event.wait(60)

    def handle(self, firstline):
        line = firstline
        while True:
            logger.debug('Stratum receive: %s' % line)
            _, response = jsonrpc.process_request(None, None, line, self)
            self._send_stratum_message(response)

            line = self.file.readline()
            if not line:
                break

    def mining_subscribe(self, uri, params):
        gevent.spawn(self.block_pusher)
        return {}
