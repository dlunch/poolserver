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

    @classmethod
    def _get_hash(cls, data):
        return hashlib.sha256(hashlib.sha256(data).digest()).digest()

    @classmethod
    def merkle_root_from_branch(cls, first, branches):
        merkle_root = first
        for i in branches:
            merkle_root = cls._get_hash(merkle_root + i)
        return merkle_root
