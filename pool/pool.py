import gevent
import gevent.monkey
import gevent.server
gevent.monkey.patch_all()

import traceback
import logging
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s:%(levelname)s:%(name)s:%(message)s')
logger = logging.getLogger('Pool')

from . import config
from . import work
from . import jsonrpc
from .stratum import Stratum
from .errors import IsStratumConnection


class Pool(object):
    def __init__(self):
        if config.net == 'bitcoin':
            from .net import bitcoin
            self.net = bitcoin.Bitcoin(
                config.rpc_host,
                config.rpc_port,
                config.rpc_username,
                config.rpc_password)
        elif config.net == 'bitcoin_testnet':
            from .net import bitcoin_testnet
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
            except Exception as e:
                logger.error("Cannot connect to bitcoind:")
                logger.error(traceback.format_exc())
            gevent.sleep(1)

        logger.info('Running on %s, version %d' %
                    (config.net, version['version']))
        logger.info('Current difficulty: %f' % info['difficulty'])

        self.generation_pubkey =\
            self.net.address_to_pubkey(config.generation_address)
        self.target_difficulty =\
            self.net.difficulty_to_target(config.target_difficulty)
        self.work = work.Work(self.net, self.target_difficulty,
                              self.generation_pubkey)

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

            logger.debug('\nRequest: %s' % (data))
            code, result = jsonrpc.process_request(headers, uri, data,
                                                   self.work)
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
