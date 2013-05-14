import binascii

from transaction import Transaction
from coinbase_transaction import CoinbaseTransaction
import util


class Work(object):
    def __init__(self, net, target, generation_pubkey):
        self.net = net
        self.target = target
        self.generation_pubkey = generation_pubkey

        self.block_template = self.net.getblocktemplate()
        self._create_tx()

    def _create_tx(self):
        self.coinbase_tx = CoinbaseTransaction(
            self.block_template, self.generation_pubkey)
        self.tx = [Transaction(x) for x in self.block_template['transactions']]

    def _serialize_target(self):
        target_bytes = util.long_to_bytes(self.target, 32)

        return binascii.hexlify(target_bytes)

    def getblocktemplate(self):
        """For worker"""
        block_template = {k: self.block_template[k]
                          for k in self.block_template
                          if k not in
                          ['coinbasevalue', 'coinbaseaux', 'coinbaseflags']}

        block_template['target'] = self._serialize_target()
        block_template['mutable'] = ["coinbase/append", "submit/coinbase"]
        block_template['transactions'] = [x.serialize() for x in self.tx]
        block_template['coinbasetxn'] = self.coinbase_tx.serialize()

        return block_template
