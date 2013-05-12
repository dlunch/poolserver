class Transaction(object):
    def __init__(self, tx_data):
        """:param tx_data: transaction data from getblocktemplate"""
        self.tx_data = tx_data

    def serialize(self):
        return {'data': self.tx_data['data']}
