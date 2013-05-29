import ctypes
import os

lib = ctypes.cdll.LoadLibrary(os.path.dirname(__file__) + '/scrypt_native.so')

def get_scrypt_hash(data):
    buffer = ctypes.create_string_buffer(32)
    lib.scrypt_1024_1_1_256(ctypes.cast(data, ctypes.c_char_p), buffer)
    return buffer.raw
