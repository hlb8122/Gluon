from bloom import BloomFilter
from iblt_slim import SIBLT
import numpy as np

def get_iblt_missing_excess(iblt1, iblt2):
    # Calculate subtraction of iblt2 from iblt1 then decode
    print('Calculating IBLT Subtraction...')
    iblt1.subtract(iblt2)
    diff_results = iblt1.decode()
    print('IBLT decoding result: ', diff_results[0], len(diff_results[1]), len(diff_results[2]))
    assert diff_results[0] == 'Success', 'IBLT decoding failure'

    return diff_results[1], diff_results[2]

def create_bloom(set, capacity=3000, error_rate=0.001):
    # Create Bloom filter
    bf = BloomFilter(capacity=capacity, error_rate=error_rate)
    for x in set:
        bf.add(x)
    return bf

def create_iblt(set, n_cells = 800, n_hashes=4, key_size=32, hash_key_sum_size=4):
    # Create IBLT
    iblt = SIBLT(n_cells, key_size, hash_key_sum_size, n_hashes)
    iblt.encode(set)
    return iblt

def optimum_params_bf(n_block_tx, n_receiver_pool_tx, cell_size):
    # Calculate optimum n_cells (copied from BU Graphene)
    # TODO: Didn't have much luck with this producing optimal params
    # TODO: Perhaps it's the fact that we're assuming that Bob's mempool is missing only one TX?
    # TODO: Need to talk to someone about this...
    assert(n_receiver_pool_tx >= n_block_tx - 1)
    n_block_and_receiver_pool_tx = n_block_tx - 1
    filter_cell_size = 1

    def calc_fpr(a):
        # Calculate error rate
        fpr_min = 0.001
        fpr_max = 0.999
        return max([fpr_min, min([a / (n_receiver_pool_tx - n_block_and_receiver_pool_tx), fpr_max])])

    def F(a):
        # Size of bloom
        return np.floor(filter_cell_size * (-1 / np.log(2)**2 * n_block_tx * np.log(calc_fpr(a))/ 8))

    def L(a):
        # Size of IBLT
        n_iblt_hash = 4 # TODO: Lookup from table?
        iblt_overhead = 1.5 # TODO: Lookup from table?
        padded_cells = a * iblt_overhead
        cells = n_iblt_hash * np.ceil(padded_cells / n_iblt_hash)
        return cell_size * cells

    # Brute force search
    opt_diff = 1
    opt_T = 10**6
    for a in range(1, n_receiver_pool_tx):
        T = F(a) + L(a)
        if T < opt_T:
            opt_T = T
            opt_diff = a

    return opt_diff

def optimum_params(set_size, pool_size, percentage_set_missing, percentage_pool_excess, cell_size):
    # Modified optimum parameters
    # More geared to our applications?
    fpr_min = 0.0001
    fpr_max = 0.9999
    opt_fpr = np.clip(set_size / (cell_size * pool_size * percentage_pool_excess * np.power(np.log(2),2)), fpr_min, fpr_max)
    opt_n_cells = set_size * percentage_set_missing + pool_size * percentage_pool_excess * opt_fpr
    return opt_fpr, opt_n_cells