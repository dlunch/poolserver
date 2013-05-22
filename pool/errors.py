class RPCError(Exception):
    pass


class IsStratumConnection(Exception):
    def __init__(self, firstline):
        self.firstline = firstline


