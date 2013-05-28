from __future__ import absolute_import, unicode_literals

from pool import util
from pool.compat import str

class Transaction(object):
    def __init__(self, tx_data):
        """:param tx_data: transaction data from getblocktemplate"""
        self.raw_tx = util.h2b(tx_data['data'])
        self.tx = tx_data

    def serialize(self):
        return {'data': util.b2h(self.raw_tx)}
