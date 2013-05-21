import gevent
import json
import logging
import traceback
logger = logging.getLogger('JsonRPC')


from errors import RPCQuitError, IsStratumConnection


class JSONRPCError(Exception):
    def __init__(self, code, message):
        self.code = code
        self.message = message


def read_http_request(file):
    headers = {}
    data = None
    uri = None
    with gevent.Timeout(10, False):
        while True:
            line = file.readline()
            if not line or line == '\r\n':
                break
            if line[0] == '{':
                #Stratum
                raise IsStratumConnection(line)
            if not uri:
                method, uri, version = line.split(' ', 2)
                continue
            if line.find(':') != -1:
                k, v = line.split(':', 1)
                headers[k.strip().lower()] = v.strip()
        if 'content-length' in headers:
            data = file.read(int(headers['content-length']))
    return headers, uri, data


def send_http_response(file, code, content, headers=None):
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


def create_request(method, params):
    return json.dumps({'id': 0, 'method': method, 'params': params})


def create_response(id, result, error=None):
    return json.dumps({'id': id, 'error': error, 'result': result})


def create_error_response(id, error_code, error_message):
    return create_response(id, None, {'code': error_code,
                                      'message': error_message,
                                      'data': None})


def process_request(headers, uri, data, handler):
    try:
        try:
            data = json.loads(data)
        except:
            raise JSONRPCError(-32700, 'Parse Error')
        if 'method' not in data or\
           'id' not in data or 'params' not in data:
            raise JSONRPCError(-32600, 'Invalid Request')

        method_name = data['method'].replace('.', '_')
        if not hasattr(handler, method_name):
            raise JSONRPCError(-32601, 'Method Not Found')
        method = getattr(handler, method_name)
        params = data['params']
        response = create_response(data['id'], method(params, uri))
        return 200, response
    except RPCQuitError:
        raise
    except JSONRPCError as e:
        id = data['id'] if type(data) == dict and 'id' in data else None
        return 500, create_error_response(id, e.code, e.message)
    except:
        logger.error('Exception while processing request')
        logger.error(traceback.format_exc())

        id = data['id'] if type(data) == dict and 'id' in data else None
        return 500, create_error_response(id, -32603, 'Internal Error')
