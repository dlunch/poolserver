from transaction import Transaction
from coinbase_transaction import CoinbaseTransaction


class Work(object):
    def __init__(self, net, target):
        self.net = net
        self.target = target

        self.block_template = self.net.getblocktemplate()
        self._create_tx()

    def _create_tx(self):
        self.coinbase_tx = CoinbaseTransaction(self.block_template)
        self.tx = [Transaction(x) for x in self.block_template['transactions']]

    def getblocktemplate(self):
        """For worker"""
        block_template = self.block_template.copy()
        block_template['target'] = self.target
        block_template['mutable'] = ["coinbase/append", "submit/coinbase"]
        block_template['transactions'] = [x.serialize() for x in self.tx]
        block_template['coinbasetxn'] = self.coinbase_tx.serialize()

        return block_template
