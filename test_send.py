import blocks_util
import byte_tools as bt
from node import Node
import time

# Initialise Alice's txpool, currently modeled by a orphaned block
# Ordered by arrival at node
alice_mempool = blocks_util.getTxsFromBlock(blocks_util.orphan)

# Initialise Alice's block, currently modeled by a slice of her txpool
block_size = 2048
offset = 30
alice_block_tx_ids = [bt.sha256(tx.encode()) for tx in alice_mempool][offset:block_size+offset]

alice = Node(alice_mempool, alice_block_tx_ids, 'localhost', 99)

alice.init_server()
alice.open_connection('localhost', 100)
time.sleep(1)
# Estimated percentage in the block which of transactions missing from receivers txpool
est_missing_tx_perc = 0.05
# Estimated percentage of missing pairs at height 1
est_missing_pair_perc = 0.02
alice.send_block(est_missing_tx_perc, est_missing_pair_perc)