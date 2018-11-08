import blocks_util
import byte_tools as bt
from node import Node

# Initialise Bobs txpool, currently modeled by a block
# Ordered by arrival at node
bob_mempool = blocks_util.getTxsFromBlock(blocks_util.actual)

# Initialise Bob's block (Not really needed/will be discarded)
block_size = 2048
bob_block_tx_ids = [bt.sha256(tx.encode()) for tx in bob_mempool][:block_size]

bob = Node(bob_mempool, bob_block_tx_ids, 'localhost', 100)

bob.init_server()
bob.open_connection('localhost', 99)
bob.listen_for_blocks()