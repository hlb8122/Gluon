import mmh3
import byte_tools as bt
import hashlib as hl

# Slim Invertible Bloom Lookup Table
# Barebones implemenation of IBLT with values removed
# Uses murmur3 hash for the indexing and SHA256 for the key sum hash

class SIBLT:
    def __init__(self, n_cells, key_size, key_sum_size, n_hash_functions=4):
        self.n_cells = n_cells
        self.n_hash_functions = n_hash_functions
        self.key_size = key_size
        self.key_sum_size = key_sum_size
        self.T = [[0, int(0).to_bytes(key_size, 'big'), int(0).to_bytes(key_sum_size, 'big')] for i in range(n_cells)]

    def hash(self, i, key):
        return mmh3.hash(key, i) % self.n_cells

    def key_sum_hash(self, key):
        return hl.sha256(key).digest()[:self.key_sum_size]

    def encode(self, keys):
        for key in keys:
            indicies = [self.hash(i, key) for i in range(self.n_hash_functions)]
            for j in indicies:
                self.T[j][0] += 1
                self.T[j][1] = bt.xor(self.T[j][1], key)
                self.T[j][2] = bt.xor(self.T[j][2], self.key_sum_hash(key))

    def subtract(self, other):
        for i in range(len(self.T)):
            self.T[i][0] = self.T[i][0] - other.T[i][0]
            self.T[i][1] = bt.xor(self.T[i][1], other.T[i][1])
            self.T[i][2] = bt.xor(self.T[i][2], other.T[i][2])

    def is_pure(self, i):
        return (self.T[i][0] == -1 or self.T[i][0] == 1) and (self.T[i][2] == self.key_sum_hash(self.T[i][1]))

    def get_pure(self):
        pure_list = []
        for i in range(len(self.T)):
            if self.is_pure(i):
                pure_list.append(i)

        return pure_list

    def decode(self):
        pure_list = self.get_pure()

        a_minus_b = []
        b_minus_a = []
        while len(pure_list) > 0:
            i = pure_list[-1]

            s = self.T[i][1]
            c = self.T[i][0]
            if c > 0:
                a_minus_b.append(s)
            else:
                b_minus_a.append(s)

            indicies = [self.hash(i, s) for i in range(self.n_hash_functions)]
            for j in indicies:
                self.T[j][0] -= c
                self.T[j][1] = bt.xor(self.T[j][1], s)
                self.T[j][2] = bt.xor(self.T[j][2], self.key_sum_hash(s))

            pure_list = self.get_pure()

        if self.is_empty():
            return 'Success', a_minus_b, b_minus_a
        else:
            return 'Fail', a_minus_b, b_minus_a

    def is_empty(self):
        return self.T ==  [[0, int(0).to_bytes(self.key_size, 'big'), int(0).to_bytes(self.key_sum_size, 'big')] for i in range(self.n_cells)]

    def serialise(self):
        import msgpack
        short_int_T = self.T
        b = msgpack.packb(short_int_T)
        return b

    @classmethod
    def deserialise(cls, b):
        import msgpack
        T = msgpack.unpackb(b)
        n_cells = len(T)
        key_size = len(T[0][1])
        key_sum_size = len(T[0][2])
        iblt = cls(n_cells, key_size, key_sum_size) # TODO: Assuming n_hash_funcs is default
        iblt.T = T

        return iblt