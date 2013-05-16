import gevent
import gevent.monkey
import gevent.server
gevent.monkey.patch_all()

import traceback
import json
import logging
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s:%(levelname)s:%(name)s:%(message)s')
logger = logging.getLogger('Pool')

import config
import work


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

        self.generation_pubkey =\
            self.net.address_to_pubkey(config.generation_address)
        self.target_difficulty =\
            self.net.difficulty_to_target(config.target_difficulty)
        self.work = work.Work(self.net, self.target_difficulty,
                              self.generation_pubkey)

    def run(self):
        server = gevent.server.StreamServer((config.worker_host,
                                             config.worker_port),
                                            self._serve_worker)
        server.serve_forever()

    def _serve_worker(self, socket, remote):
        try:
            file = socket.makefile()
            headers = {}
            data = None
            with gevent.Timeout(2):
                while True:
                    line = file.readline()
                    if not line or line == '\r\n':
                        break
                    if line.find(':') != -1:
                        k, v = line.split(':', 1)
                        headers[k.strip().lower()] = v.strip()
                if 'content-length' in headers:
                    data = file.read(int(headers['content-length']))

            file.write(self._process_worker(headers, data))
        except:
            logger.error('Exception while processing request from client')
            logger.error(traceback.format_exc())
            file.write(self._create_error_response(None,
                                                   'Internal Error', -32603))
        finally:
            file.close()
            socket.close()

    def _create_response(self, id, result, error=None):
        return json.dumps({'id': id, 'error': error, 'result': result})

    def _create_error_response(self, id, error_message, error_code):
        return self._create_response(id, None, {'code': error_code,
                                                'message': error_message,
                                                'data': None})

    def _process_worker(self, headers, data):
        try:
            data = json.loads(data)
        except:
            return self._create_error_response(None, 'Parse Error', -32700)
        if 'method' not in data or 'id' not in data or 'params' not in data:
            return self._create_error_response(data['id'],
                                               'Invalid Request', -32600)

        method = getattr(self, '_handle_' + data['method'])
        if not method:
            return self._create_error_response(data['id'],
                                               'Method Not Found', -32601)
        try:
            return self._create_response(data['id'], method(data['params']))
        except:
            logger.error('Exception while processing request')
            logger.error(traceback.format_exc())
            return self._create_error_response(data['id'],
                                               'Internal Error', -32603)


    def _handle_getblocktemplate(self, params):
        return {}
