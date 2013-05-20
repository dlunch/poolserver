import gevent
import gevent.monkey
import gevent.server
gevent.monkey.patch_all()

import traceback
import time
import logging
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s:%(levelname)s:%(name)s:%(message)s')
logger = logging.getLogger('Pool')

import config
import work
import jsonrpc
from errors import RPCQuitError, IsStratumConnection


class Pool(object):
    def __init__(self):
        if config.net == 'bitcoin':
            import net.bitcoin
            self.net = net.bitcoin.Bitcoin(
                config.rpc_host,
                config.rpc_port,
                config.rpc_username,
                config.rpc_password)
        elif config.net == 'bitcoin_testnet':
            import net.bitcoin_testnet
            self.net = net.bitcoin_testnet.BitcoinTestnet(
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
                logger.error("Cannot connect to bitcoind: %r" % e)
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
        self.work.refresh_work()
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

            code, result = jsonrpc.process_request(headers, uri, data, self)
            logger.debug('\nRequest: %s\nResponse:%s' % (data, result))
            jsonrpc.send_http_response(file, code, result,
                                       self._get_extended_headers(headers))
        except RPCQuitError:
            return
        except IsStratumConnection as e:
            self._handle_stratum(file, e.firstline)
        except:
            logger.debug('Request handle exception')
            logger.debug(traceback.format_exc())
            jsonrpc.send_http_response(file, 400, None)
        finally:
            logger.debug('Request process complete')
            file.close()
            socket.close()

    def _handle_getblocktemplate(self, params, uri):
        return self.work.getblocktemplate(params, uri)

    def _handle_getwork(self, params, uri):
        return self.work.getwork(params, uri)

    def _send_stratum_message(self, file, message):
        logger.debug('Stratum send: %s' % message)
        file.write(message + '\n')
        file.flush()

    def _handle_stratum(self, file, firstline):
        logger.debug('Handling stratum connection')
        line = firstline
        lasttime = time.time() - 60
        while True:
            logger.debug('Stratum receive: %s' % line)
            _, response = jsonrpc.process_request(None, None, line, self)
            self._send_stratum_message(file, response)

            if time.time() - lasttime >= 59:
                request = jsonrpc.create_request('mining.notify',
                                                 self.work.get_stratum_work())
                self._send_stratum_message(file, request)
                lasttime = time.time()
            with gevent.Timeout(60, False):
                line = file.readline()
                if not line:
                    break

        logger.debug('Stratum connection terminated')
