import gevent
import gevent.monkey
import gevent.server
gevent.monkey.patch_all()

import traceback
import json
import time
import logging
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s:%(levelname)s:%(name)s:%(message)s')
logger = logging.getLogger('Pool')

import config
import work
from errors import RPCQuitError


class JSONRPCException(Exception):
    def __init__(self, code, message):
        self.code = code
        self.message = message


class IsStratumConnection(Exception):
    def __init__(self, firstline):
        self.firstline = firstline


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

    def _read_http_request(self, file):
        headers = {}
        data = None
        uri = None
        with gevent.Timeout(10, False):
            first = True
            while True:
                line = file.readline()
                if not line:
                    break
                if line[0] == '{':
                    #Stratum
                    raise IsStratumConnection(line)
                if first:
                    method, uri, version = line.split(' ', 2)
                    first = False
                if not line or line == '\r\n':
                    break
                if line.find(':') != -1:
                    k, v = line.split(':', 1)
                    headers[k.strip().lower()] = v.strip()
            if 'content-length' in headers:
                data = file.read(int(headers['content-length']))
        return headers, uri, data

    def _send_http_response(self, file, code, content, headers=None):
        if code == 200:
            message = 'OK'
        elif code == 500:
            message = 'Internal Server Error'
        elif code == 400:
            message = 'Bad Request'
        file.write('HTTP/1.1 %d %s\r\n' % (code, message))
        file.write('Server: dlunchpool\r\n')
        if content:
            file.write('Content-Length: %d\r\n' % len(content))
            file.write('Content-Type: application/json\r\n')
        if headers:
            for i in headers:
                file.write('%s: %s\r\n' % (i, headers[i]))
        file.write('\r\n')
        if content:
            file.write(content)

    def _serve_worker(self, socket, remote):
        logger.debug('Connection from %s:%d' % remote)
        try:
            file = socket.makefile()
            headers, uri, data = self._read_http_request(file)
            if not data:
                raise Exception()

            try:
                data = json.loads(data)
            except:
                raise JSONRPCException(-32700, 'Parse Error')
            if 'method' not in data or\
               'id' not in data or 'params' not in data:
                raise JSONRPCException(-32600, 'Invalid Request')

            headers, result = self._process_worker(headers, uri, data)
            logger.debug('\nRequest: %s\nResponse:%s' % (data, result))
            self._send_http_response(file, 200, result, headers)
        except JSONRPCException as e:
            id = data['id'] if data and 'id' in data else None
            result = self._create_error_response(id, e.message, e.code)
            self._send_http_response(file, 500, result)
        except RPCQuitError:
            return
        except IsStratumConnection as e:
            self._handle_stratum(file, e.firstline)
        except:
            self._send_http_response(file, 400, None)
        finally:
            logger.debug('Request process complete')
            file.close()
            socket.close()

    def _create_request(self, method, params):
        return json.dumps({'id': 0, 'method': method, 'params': params})

    def _create_response(self, id, result, error=None):
        return json.dumps({'id': id, 'error': error, 'result': result})

    def _create_error_response(self, id, error_message, error_code):
        return self._create_response(id, None, {'code': error_code,
                                                'message': error_message,
                                                'data': None})

    def _process_worker(self, headers, uri, data):
        method_name = '_handle_' + data['method']
        if not hasattr(self, method_name):
            raise JSONRPCException(-32601, 'Method Not Found')
        try:
            method = getattr(self, method_name)
            params = data['params']
            if type(params) == list:
                new_params = {}
                for i in params:
                    new_params.update(i)
                params = new_params
            response = self._create_response(data['id'], method(params, uri))
            headers = self._get_extended_headers(headers)
            return headers, response
        except RPCQuitError:
            raise
        except:
            logger.error('Exception while processing request')
            logger.error(traceback.format_exc())

            raise JSONRPCException(-32603, 'Internal Error')

    def _handle_getblocktemplate(self, params, uri):
        return self.work.getblocktemplate(params, uri)

    """def _handle_getwork(self, params, uri):
        return self.work.getwork(params)"""

    def _handle_stratum(self, file, firstline):
        logger.debug('Handling stratum connection')
        line = firstline
        lasttime = time.time() - 60
        while True:
            try:
                data = json.dumps(line)
            except:
                pass
            if time.time() - lasttime >= 59:
                request = self._create_request('mining.notify',
                                               self.work.get_stratum_work())
                file.write(request + '\n')
                file.flush()
                lasttime = time.time()
            with gevent.Timeout(60, False):
                line = file.readline()
                if not line:
                    break

        logger.debug('Stratum connection terminated')
