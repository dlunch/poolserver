import hashlib


class MerkleTree(object):
    def __init__(self, data):
        self.branches = []
        data = [self._get_hash(x) for x in data]

        while len(data) > 1:
            self.branches.append(data[1])
            if len(data) % 2 == 1:
                data.append(data[len(data)-1])
            data = [self._get_hash(data[i]+data[i+1])
                    for i in range(0, len(data), 2)]
        self.root = data[0]

    def _get_hash(self, data):
        return hashlib.sha256(hashlib.sha256(data).digest()).digest()
