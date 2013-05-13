import struct

b = bytes


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
    s = b('')
    n = long(n)
    pack = struct.pack
    while n > 0:
        s = pack('>I', n & 0xffffffffL) + s
        n = n >> 32
    # strip off leading zeros
    for i in range(len(s)):
        if s[i] != b('\000')[0]:
            break
    else:
        # only happens when n == 0
        s = b('\000')
        i = 0
    s = s[i:]
    # add back some pad bytes. this could be done more efficiently w.r.t. the
    # de-padding being done above, but sigh...
    if blocksize > 0 and len(s) % blocksize:
        s = (blocksize - len(s) % blocksize) * b('\000') + s
    return s


def bytes_to_long(s):
    """bytes_to_long(string) : long
    Convert a byte string to a long integer.

    This is (essentially) the inverse of long_to_bytes().
    """
    acc = 0L
    unpack = struct.unpack
    length = len(s)
    if length % 4:
        extra = (4 - length % 4)
        s = b('\000') * extra + s
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
    data = struct.pack('<Q', height).rstrip('\x00')
    return struct.pack('B', len(data)) + data


def encode_integer(integer):
    if integer < 0xfd:
        return struct.pack('B', integer)
    elif integer < 0xffff:
        return '\xfd' + struct.pack('<H', integer)
    elif integer < 0xffffffff:
        return '\xfe' + struct.pack('<I', integer)
    else:
        return '\xff' + struct.pack('<Q', integer)
