from __future__ import absolute_import, unicode_literals

import struct
import logging
logger = logging.getLogger('Coinbase')


from pool import util
from pool.transaction import Transaction


class CoinbaseTransaction(object):
    def __init__(self, block_template, generation_pubkey,
                 extranonce1, extranonce2):
        #BIP 0034
        coinbase_script = util.encode_height(block_template['height'])

        if 'coinbaseaux' in block_template:
            for i in block_template['coinbaseaux']:
                data = util.h2b(block_template['coinbaseaux'][i])
                coinbase_script += data
        if 'coinbaseflags' in block_template:
            data = util.h2b(block_template['coinbaseflags'])
            coinbase_script += data

        coinbase_script += extranonce1
        coinbase_script += extranonce2

        if 'coinbasevalue' in block_template:
            coinbase_value = block_template['coinbasevalue']
        else:
            tx = Transaction(block_template['coinbasetxn'])
            coinbase_value = tx.output[0]['value']

        output_script = b'\x76\xa9\x14' + generation_pubkey + b'\x88\xac'

        result = b'\x01\x00\x00\x00'  # Version
        result += b'\x01'  # In counter(1)
        result += b'\x00' * 32  # Input(None)
        result += b'\xff\xff\xff\xff'  # Input Index (None)
        result += util.encode_size(len(coinbase_script))
        result += coinbase_script
        result += b'\xff\xff\xff\xff'  # Sequence
        result += b'\x01'  # Out counter(1)
        result += struct.pack('<Q', coinbase_value)
        result += util.encode_size(len(output_script))
        result += output_script
        result += b'\x00\x00\x00\x00'  # Lock time

        self.raw_tx = result
        logger.debug('Generated coinbase transaction %s' %
                     util.b2h(self.raw_tx))

    def serialize(self):
        return {'data': util.b2h(self.raw_tx)}

    @classmethod
    def verify(cls, tx, generation_pubkey):
        """Verifies transaction is correct coinbase transaction"""
        """returns length of transaction"""
        version = tx[:4]
        if version != b'\x01\x00\x00\x00':
            raise Exception("Invalid version")
        sizelen, txin_count = util.decode_size(tx[4:13])
        ptr = sizelen + 4
        if txin_count != 1:
            raise Exception("Too many input transaction")
        previous_output = tx[ptr:ptr+36]
        ptr += 36
        if previous_output != b'\x00'*32 + b'\xff\xff\xff\xff':
            raise Exception("Wrong previous output")
        sizelen, coinbase_len = util.decode_size(tx[ptr:ptr+9])
        ptr += sizelen
        ptr += coinbase_len
        ptr += 4  # Sequence

        sizelen, txout_count = util.decode_size(tx[ptr:ptr+9])
        ptr += sizelen
        ptr += 8  # Value
        sizelen, script_len = util.decode_size(tx[ptr:ptr+9])
        ptr += sizelen

        output_script = tx[ptr:ptr+script_len]
        if output_script != b'\x76\xa9\x14' + generation_pubkey + b'\x88\xac':
            raise Exception("Wrong generation pubkey")

        ptr += script_len
        ptr += 4  # Lock time
        return ptr
