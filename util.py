import struct


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
