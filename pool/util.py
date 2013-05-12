import struct
import binascii
import hashlib

base58_data = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'

def base58_encode(data):
    result = ''
    value = long(binascii.hexlify(data), 16)
    while value > 0:
        value, c = divmod(value, 58)
        result += base58_data[c]

    for i in data:
        if i == '\x00':
            result += base58_data[0]
            continue
        break

    return result[::-1]


def base58_decode(data):
    value = 0
    mul = 1
    for i in data[::-1]:
        value += base58_data.find(i) * mul
        mul *= 58

    result = ''
    for i in data:
        if i == base58_data[0]:
            result += '\x00'
            continue
        break
    result += binascii.unhexlify(hex(value)[2:].rstrip('L'))

    return result


def address_to_pubkey(address):
    data = base58_decode(address)
    return data[1:21]


def pubkey_to_address(pubkey, net):
    data = net.address_prefix + pubkey
    checksum = hashlib.sha256(hashlib.sha256(data).digest()).digest()[:4]
    return base58_encode(data + checksum)


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
