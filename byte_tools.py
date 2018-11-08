import hashlib

def sha256(preimage):
    return hashlib.sha256(preimage).digest()

empty_hash = sha256("".encode())

def xor(x, y):  # use xor for bytes
    assert(len(x) == len(y))

    return bytes((x ^ y) % 256 for x, y in zip(x, y))

def invert(b):
    parts = []
    for i in b:
        parts.append(~i % 256)

    return bytes(parts)

def reverse(b):
    parts = []
    for i in range(0,len(b),-1):
        parts.append(b[i])
    return bytes(parts)

def concat(x, y):
    return x + y

# def encode(x, y):
#     return hash(concat(x, y))[:64]
#
# def decode(b, priors):
#     for prior_a in priors:
#         for prior_b in priors:
#             if b == hash(concat(prior_a, prior_b))[:64]:
#                 return (prior_a, prior_b)

# def encode(x, y):
#     s = lz4.frame.compress(bytes(x+y), compression_level=16)
#     s = s[19:-4]
#     # print('Digest:', len(s), s.hex())
#     return s
#
# def decode(pair, priors):
#     pair = b'\x04"M\x18h@(\x00\x00\x00\x00\x00\x00\x00u(\x00\x00\x80' + pair + b'\x00\x00\x00\x00'
#     s = lz4.frame.decompress(pair)
#     return (s[:20], s[20:40])

class PairEncodingScheme:
    def __init__(self, encode, decode, length):
        self.encode = encode
        self.decode = decode
        self.length = length

    @classmethod
    def DoubleIdEncoding(cls, id_enc):
        length = 2*id_enc.length
        def decode(b):
            half = int(len(b) / 2)
            b1, b2 = b[:half], b[half:]

            return (id_enc.decode(b1), id_enc.decode(b2))

        def encode(x, y):
            return id_enc.encode(x) + id_enc.encode(y)

        return cls(encode, decode, length)

class IdEncodingScheme:
    def __init__(self, encode, decode, length):
        self.encode = encode
        self.decode = decode
        self.length = length

    @classmethod
    def BasicTruncatedEncoding(cls, priors, n_bytes=32):
        def encode(x):
            return x[:n_bytes]

        def decode(b):
            x = None
            for prior_a in priors:
                if prior_a[:n_bytes] == b[:n_bytes]:
                    x = prior_a

            if x == None:
                print('Catch')
            assert x != None, 'Failure decoding shortened ID!'
            return x

        return cls(encode, decode, n_bytes)
