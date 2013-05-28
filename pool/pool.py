from __future__ import absolute_import, unicode_literals

import os
import gevent
import gevent.server

import sys
if sys.version_info[0] < 3:
    import gevent.monkey
    gevent.monkey.patch_all()

import traceback
import base64
import logging
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s:%(levelname)s:%(name)s:%(message)s')
logger = logging.getLogger('Pool')

from pool import config
from pool import work
from pool import jsonrpc
from pool import user
from pool.stratum import Stratum
from pool.errors import IsStratumConnection
from pool.compat import str, bytes


class Pool(object):
    def __init__(self):
        if config.net == 'bitcoin':
            from pool.net import bitcoin
            self.net = bitcoin.Bitcoin(
                config.rpc_host,
                config.rpc_port,
                config.rpc_username,
                config.rpc_password)
        elif config.net == 'bitcoin_testnet':
            from pool.net import bitcoin_testnet
            self.net = bitcoin_testnet.BitcoinTestnet(
                config.rpc_host,
                config.rpc_port,
                config.rpc_username,
                config.rpc_password)
        while True:
            try:
                version = self.net.getinfo()
                info = self.net.getmininginfo()
                break
            except Exception:
                logger.error("Cannot connect to bitcoind:")
                logger.error(traceback.format_exc())
            gevent.sleep(1)

        logger.info('Running on %s, version %d' %
                    (config.net, version['version']))
        logger.info('Current difficulty: %f' % info['difficulty'])

        self.generation_pubkey =\
            self.net.address_to_pubkey(config.generation_address)
        self.work = work.Work(self.net, self.generation_pubkey)

    def run(self):
        self.work.start_refresher()
        server = gevent.server.StreamServer((config.worker_host,
                                             config.worker_port),
                                            self._serve_worker)
        server.serve_forever()

    def _get_extended_headers(self, original_headers):
        return {'X-Long-Polling': config.longpoll_uri,
                'X-Stratum': 'stratum+tcp://%s' % original_headers['host']}

    def _serve_worker(self, socket, remote):
        logger.debug('Connection from %s:%d' % remote)
        try:
            file = socket.makefile()
            headers, uri, data = jsonrpc.read_http_request(file)

            auth = {'username': 'NotAuthorized', 'difficulty': 1}
            if 'authorization' in headers:
                _, auth = headers['authorization'].split(' ')
                username, password = str(base64.decodestring(
                    bytes(auth, 'ascii')), 'ascii').split(':')
                auth = user.authenticate(username, password)
                if not auth['result']:
                    jsonrpc.send_http_response(file, 403, None, {})
                    return

            logger.debug('\nRequest: %s' % (data))
            code, result = jsonrpc.process_request(headers, uri, data,
                                                   self.work, auth)
            logger.debug('\nResponse:%s' % (result))
            jsonrpc.send_http_response(file, code, result,
                                       self._get_extended_headers(headers))
        except IsStratumConnection as e:
            self._handle_stratum(file, e.firstline)
        except:
            logger.debug('Request handle exception')
            logger.debug(traceback.format_exc())
            jsonrpc.send_http_response(file, 400, None)
        finally:
            logger.debug('Request process complete')
            try:
                file.close()
                socket.close()
            except:
                pass

    def _handle_stratum(self, file, firstline):
        logger.debug('Handling stratum connection')
        stratum = Stratum(file, self.work)

        stratum.handle(firstline)

        logger.debug('Stratum connection terminated')
