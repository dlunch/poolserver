import gevent
import logging
import time
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

    def handle(self, firstline):
        line = firstline
        lasttime = time.time() - 60
        while True:
            logger.debug('Stratum receive: %s' % line)
            _, response = jsonrpc.process_request(None, None, line, self)
            self._send_stratum_message(response)

            if time.time() - lasttime >= 59:
                request = jsonrpc.create_request('mining.notify',
                                                 self.work.get_stratum_work())
                self._send_stratum_message(request)
                lasttime = time.time()
            with gevent.Timeout(60, False):
                line = self.file.readline()
                if not line:
                    break

    def mining_subscribe(self, uri, params):
        return {}
