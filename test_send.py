import blocks_util
import byte_tools as bt
from node import Node
import time

# Initialise Alice's mempool, currently modeled by a orphaned block
# Ordered by arrival at node
alice_mempool = blocks_util.getTxsFromBlock(blocks_util.orphan)

# Initalise Alice's block, currently modeled by a slice of her mempool
block_size = 2048
offset = 30
alice_block_tx_ids = [bt.sha256(tx.encode()) for tx in alice_mempool][offset:block_size+offset]

alice = Node(alice_mempool, alice_block_tx_ids, 'localhost', 99)

alice.init_server()
alice.open_connection('localhost', 100)
time.sleep(1)
est_missing_tx_perc = 0.05 # Estimated number of missing transactions
est_missing_pair_perc = 0.02 # Estimated number of missing pairs at height 1
alice.send_block(est_missing_tx_perc, est_missing_pair_perc)