try:
    bytes('test', 'ascii')
    str = str
    bytes = bytes
except:
    import __builtin__

    def str(string, encoding):
        return __builtin__.str(string)

    def bytes(string, encoding):
        return __builtin__.bytes(string)
