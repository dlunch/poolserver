import struct
import logging
logger = logging.getLogger('Coinbase')


from . import util
from .transaction import Transaction


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
