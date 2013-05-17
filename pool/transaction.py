import binascii

class Transaction(object):
    def __init__(self, tx_data):
        """:param tx_data: transaction data from getblocktemplate"""
        self.raw_tx = binascii.unhexlify(tx_data['data'])
        self.tx = tx_data

    def serialize(self):
        return {'data': binascii.hexlify(self.tx_data)}
