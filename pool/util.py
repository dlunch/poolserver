import struct
import binascii
from .compat import str


def long_to_bytes(n, blocksize=0):
# From https://github.com/dlitz/pycrypto/blob/master/lib/Crypto/Util/number.py
# (Public domain)
    """long_to_bytes(n:long, blocksize:int) : string
    Convert a long integer to a byte string.

    If optional blocksize is given and greater than zero, pad the front of the
    byte string with binary zeros so that the length is a multiple of
    blocksize.
    """
    # after much testing, this algorithm was deemed to be the fastest
    s = b''
    pack = struct.pack
    while n > 0:
        s = pack('>I', n & 0xffffffff) + s
        n = n >> 32
    # strip off leading zeros
    for i in range(len(s)):
        if s[i] != b'\x00'[0]:
            break
    else:
        # only happens when n == 0
        s = b'\x00'
        i = 0
    s = s[i:]
    # add back some pad bytes. this could be done more efficiently w.r.t. the
    # de-padding being done above, but sigh...
    if blocksize > 0 and len(s) % blocksize:
        s = (blocksize - len(s) % blocksize) * b'\x00' + s
    return s


def bytes_to_long(s):
    """bytes_to_long(string) : long
    Convert a byte string to a long integer.

    This is (essentially) the inverse of long_to_bytes().
    """
    acc = 0
    unpack = struct.unpack
    length = len(s)
    if length % 4:
        extra = (4 - length % 4)
        s = b'\x00' * extra + s
        length = length + extra
    for i in range(0, length, 4):
        acc = (acc << 32) + unpack('>I', s[i:i+4])[0]
    return acc


base58_data = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'


def base58_encode(data):
    result = ''
    value = bytes_to_long(data)
    while value > 0:
        value, c = divmod(value, 58)
        result += base58_data[c]

    return result[::-1]


def base58_decode(data, size):
    value = 0
    mul = 1
    for i in data[::-1]:
        value += base58_data.find(i) * mul
        mul *= 58

    return long_to_bytes(value, size)


def encode_height(height):
    data = struct.pack('<Q', height)
    for i in range(len(data)):
        if data[i] == b'\x00'[0]:
            break
    data = data[:i]
    if len(data) == 2:
        data = data + b'\x00'
    return struct.pack('B', len(data)) + data


def encode_size(size):
    if size < 0xfd:
        return struct.pack('B', size)
    elif size < 0xffff:
        return b'\xfd' + struct.pack('<H', size)
    elif size < 0xffffffff:
        return b'\xfe' + struct.pack('<I', size)
    else:
        return b'\xff' + struct.pack('<Q', size)


def decode_size(data):
    if data[0] < b'\xfd':
        return 1, struct.unpack('B', data[0])[0]
    elif data[0] == b'\xfd':
        return 3, struct.unpack('<H', data[0:2])[0]
    elif data[0] == b'\xfe':
        return 5, struct.unpack('<I', data[0:4])[0]
    elif data[0] == b'\xff':
        return 9, struct.unpack('<I', data[0:8])[0]

def b2h(data):
    return str(binascii.hexlify(data), 'ascii')


def h2b(data):
    return binascii.unhexlify(data)
