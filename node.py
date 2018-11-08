from merkle_tree import PartialMerkleTree
from networking import NodeServer
import byte_tools as bt
import filter_ops as fo
import threading

class Node():
    def __init__(self, mempool, block_tx_ids, ip, port):
        # Initialise network parameters
        self.ip = ip
        self.port = port
        self.server = None

        # Initialise encoding parameters
        # TODO: Implement better encodings see self.setup_id_encoding, self.setup_pair_encoding and byte_tools.py
        self.id_encoding_size = 8
        self.pair_encoding_size = 3 # TODO: This should dynamically change as we progress in height

        #Initialise transaction pool
        self.txpool = dict(zip([bt.sha256(tx.encode()) for tx in mempool], mempool))
        self.txpool[bt.empty_hash] = ""
        self.proto_block = None

        #Initialise leafs
        self.partial_tree = PartialMerkleTree.from_leaf_values(block_tx_ids)

        # Initialise encoding scheme for pairs
        self.id_encoding_scheme = None
        self.pair_encoding_scheme = None

    def init_server(self):
        self.server = NodeServer(self.ip, self.port)
        self.server.start()

    def open_connection(self, ip, port):
        self.server.connectTo(ip, port)

    def close_connection(self):
        self.server.shutdown()

    def get_block_tx_ids(self):
        return self.partial_tree.get_leafs()

    def get_merkle_root(self):
        top_nodes = self.partial_tree.top_nodes

        temp_tree = PartialMerkleTree(top_nodes)

        temp_tree.make_tree()
        return temp_tree.get_top_values()[0]

    def get_block(self):
        # Get block by using leafs as keys to txpool
        return [self.txpool[ref] for ref in self.partial_tree.get_leafs()]

    def add_to_txpool(self, txs):
        # Add transactions to txpool
        # TODO: This can be more efficiently done (insert instead of append)
        self.txpool = {**self.txpool, **txs}

    def remove_from_block(self, tx_ids):
        # Remove transactions from block
        block_tx_refs = self.get_block_tx_ids()
        for tx_id in tx_ids:
            block_tx_refs.remove(tx_id)

        self.partial_tree = PartialMerkleTree.from_leaf_values(block_tx_refs) # TODO: Very wasteful, fix this

    def create_block_bloom(self, error_rate=0.1):
        # Create bloom filter from memory/orphan pool
        block_tx_ids = self.get_block_tx_ids()
        block_length = len(block_tx_ids)
        return fo.create_bloom(block_tx_ids, block_length, error_rate=error_rate)

    def create_block_iblt(self, n_cells=300):
        # Create IBLT from block
        enc_block_tx_ids = [self.id_encoding_scheme.encode(tx) for tx in self.get_block_tx_ids()]
        key_size = self.id_encoding_scheme.length
        return fo.create_iblt(enc_block_tx_ids, key_size=key_size, n_cells=n_cells)

    def setup_id_encoding(self, priors):
        self.id_encoding_scheme = bt.IdEncodingScheme.BasicTruncatedEncoding(priors, n_bytes=self.id_encoding_size)

    def setup_pair_encoding(self):
        # Set up pair encoding
        # At 3 bytes and 2000 tx's this collides ~12% of the time
        # At 4 bytes and 2000 tx's this collides ~0.04% of the time
        top_values = self.partial_tree.get_top_values()
        node_id_enc = bt.IdEncodingScheme.BasicTruncatedEncoding(top_values, n_bytes=self.pair_encoding_size)
        self.pair_encoding_scheme = bt.PairEncodingScheme.DoubleIdEncoding(node_id_enc)

    def create_pairs_iblt(self, n_cells=300):
        # Create IBLT from pairs at top on partial tree
        encoded_pairs = [self.pair_encoding_scheme.encode(*pair) for pair in self.partial_tree.get_top_value_pairs()]
        key_size = self.pair_encoding_scheme.length
        return fo.create_iblt(encoded_pairs, n_cells=n_cells, key_size=key_size)

    def create_pairs_bloom(self, error_rate=0.1):
        # Create Bloom filter for pairs

        # Encode pairs (no compression needed)
        encoded_pairs = [a+b for a,b in self.partial_tree.get_top_value_pairs()]
        n_enc_pairs = len(encoded_pairs)

        # Create bloom
        return fo.create_bloom(encoded_pairs, capacity=n_enc_pairs, error_rate=error_rate)

    def prereconcile(self, bloom, iblt_other):
        # Begin to reconcile block by creating a protoblock
        self.proto_block = [tx_id for tx_id in self.txpool.keys() if tx_id in bloom]
        self.setup_id_encoding(self.proto_block)
        encoded_proto_block = [self.id_encoding_scheme.encode(tx_id) for tx_id in self.proto_block]

        # Create IBLT from bloom filtered mempool
        n_cells = len(iblt_other.T)
        key_size = self.id_encoding_scheme.length
        iblt = fo.create_iblt(encoded_proto_block, key_size=key_size, n_cells=n_cells)

        # Calculate missing transactions
        enc_missing_tx_ids, enc_excess_tx_ids = fo.get_iblt_missing_excess(iblt_other,iblt)
        excess_tx_ids = [self.id_encoding_scheme.decode(enc_excess_tx_id) for enc_excess_tx_id in enc_excess_tx_ids]

        # Remove excess transactions from mempool using IBLT
        if len(excess_tx_ids) > 0:
            for tx_id in excess_tx_ids:
                #print('IBLT removed ', self.txpool[tx_id], ' from protoblock')
                self.proto_block.remove(tx_id)

        # Return missing
        return enc_missing_tx_ids

    def finalize_protoblock(self, response):
        # Finalise tx reconciliation
        missing_tx_ids = []
        missing_txs = []

        for segment in response:
            segment_txs = segment[1]
            if segment[0] == b'\x00':
                # Don't decode the flag
                next_id = segment[0]
            else:
                next_id = self.id_encoding_scheme.decode(segment[0])

            for tx in segment_txs:
                missing_txs.append(tx)
                tx_id = bt.sha256(tx.encode())
                missing_tx_ids.append(tx_id)
                if next_id in self.proto_block:
                    self.proto_block.insert(self.proto_block.index(next_id), tx_id)
                elif next_id == b'\x00':
                    self.proto_block.append(tx_id)

        # Add missing txs to mempool
        self.add_to_txpool(dict(zip(missing_tx_ids, missing_txs)))

        # Reconstruct block
        self.partial_tree = PartialMerkleTree.from_leaf_values(self.proto_block) # TODO: Wasteful, fix this

    def missing_response(self, enc_missing_tx_ids):
        # Calculate response to missing tx request
        # TODO: Catch no responses
        missing_tx_ids = [self.id_encoding_scheme.decode(tx_id) for tx_id in enc_missing_tx_ids]
        block_tx_ids = self.get_block_tx_ids()

        # Sort missing tx IDs by the order in which they appear in own block
        def get_block_index(v):
            return block_tx_ids.index(v)

        missing_tx_ids.sort(key=get_block_index)

        # Get missing txs from mempool
        missing_tx = [self.txpool[tx_id] for tx_id in missing_tx_ids]

        # Get ID after (in own block) each missing tx
        missing_tx_ids_next = [block_tx_ids[block_tx_ids.index(tx_id) + 1] for tx_id in missing_tx_ids[:-1]] # TODO: Shorten
        last_missing_id = missing_tx_ids[-1]

        if block_tx_ids[-1] == last_missing_id:
            # If last missing ID is the last ID in the block then flag it
            missing_tx_ids_next.append(b'\x00')
        else:
            missing_tx_ids_next.append(block_tx_ids[block_tx_ids.index(last_missing_id) + 1])
        missing_tx_ids_next.append(None) #TODO: Needed?
        # Consecutive transactions are grouped into segments
        # Segments are labelled with the first transactions previous tx id
        segments = []
        segment = []
        for i in range(len(missing_tx) - 1):
            if missing_tx_ids[i + 1] == missing_tx_ids_next[i]:
                segment.append(missing_tx[i])
            else:
                segment.append(missing_tx[i])
                segments.append((self.id_encoding_scheme.encode(missing_tx_ids_next[i]), segment))
                segment = []
        i = len(missing_tx) - 1
        segment.append(missing_tx[i])
        if missing_tx_ids_next[i] != b'\x00':
            # If the last missing ID is not last in the block don't encode the flag
            segments.append((missing_tx_ids_next[i], segment))
        else:
            segments.append((self.id_encoding_scheme.encode(missing_tx_ids_next[i]), segment))

        return segments

    def reconcile_pairs(self, bloom, other_iblt):
        # Encode top pairs which pass bloom filter
        encoded_top_pairs_bloomed = [self.pair_encoding_scheme.encode(*pair) for pair in self.partial_tree.get_top_value_pairs() if pair[0]+pair[1] in bloom]

        # Create IBLT from these pairs
        cell_count = len(other_iblt.T)
        key_size = self.pair_encoding_scheme.length
        iblt = fo.create_iblt(encoded_top_pairs_bloomed, n_cells=cell_count, key_size=key_size)

        ## No bloom here?
        #encoded_top_pairs = [self.pair_encoding_scheme.encode(*pair) for pair in self.partial_tree.get_top_value_pairs()]
        #iblt = fo.create_iblt(encoded_top_pairs, n_cells=cell_count, key_size=key_size)

        # Get missing pairs via subtraction and IBLT decoding
        encoded_missing_pairs, _ = fo.get_iblt_missing_excess(other_iblt, iblt)

        # Decode missing pairs
        missing_pairs = [self.pair_encoding_scheme.decode(encoded_pair) for encoded_pair in encoded_missing_pairs]

        # Perform reconciliation
        if missing_pairs != []:
            self.partial_tree.reconcile_order(missing_pairs)
            return False
        else:
            # If no missing pairs return True
            return True



    def send_block(self, est_missing_tx_perc, est_missing_pair_perc):
        from networking import NetworkMsg
        block = self.get_block()
        self.setup_id_encoding(self.get_block_tx_ids())

        # Create INV (~ Merkle Root)
        merkle_root = self.get_merkle_root()

        # Send Inv
        self.server.send(NetworkMsg.INV, merkle_root)

        # Wait for Get Gluon block message
        self.server.waitOn(NetworkMsg.GET_GLBLK)

        # Calculate Gluon block
        n = len(block)
        print('Sending block consisting of %d transactions...' % n)
        m = self.server.other_txpool_size
        cell_overhead = 1.5
        cell_size = 8*(3 + self.id_encoding_scheme.length + 4) * cell_overhead
        est_excess_tx_perc = (m - n * (1 - est_missing_tx_perc)) / m

        multiplier = 1

        fpr, n_cells = fo.optimum_params(n, m, est_missing_tx_perc, est_excess_tx_perc, cell_size)
        n_cells = max([n_cells, 5])  # TODO: Bound n_cell fall off in a less hacky way

        block_bloom = self.create_block_bloom(error_rate=fpr)
        block_iblt = self.create_block_iblt(int(multiplier*n_cells))

        # Send Gluon block
        self.server.send(NetworkMsg.GLBLK, [block_bloom, block_iblt])

        def send_order():
            # Send order information
            while len(self.partial_tree.top_nodes) > 1:
                # Python is the bottleneck here, slowing down transfer speed makes it more realistic
                # Also makes it easy on the network threading
                import time
                time.sleep(2)

                # Check whether reconciliation is complete
                if self.server.complete is not None:
                    self.close_connection()
                    print('Transfer complete')
                    print('Analytics:')
                    print('Total of %d bytes received' % self.server.total_received)
                    print('Total of %d bytes sent' % self.server.total_sent)
                    print('Total of %d order bytes sent' % self.server.total_ord_sent)
                    # TODO: Nodes communicate analytics for future parameter improvements
                    break

                # Setup pair encoding
                self.setup_pair_encoding()

                # Calculate Gluon block order data
                n = len(self.partial_tree.top_nodes)  # Not quite 2
                cell_size = 8 * (3 + self.pair_encoding_scheme.length + 4) * cell_overhead

                multiplier = 1

                fpr, n_cells = fo.optimum_params(n, m, est_missing_pair_perc, est_missing_pair_perc, cell_size)
                n_cells = max([n_cells, 5]) # TODO: Bound n_cell fall off in a less hacky way
                # n_cells = max(18, n_cells)
                pair_bloom = self.create_pairs_bloom(fpr)
                pair_iblt = self.create_pairs_iblt(int(multiplier * n_cells))

                # Send Gluon block order data
                self.server.send(NetworkMsg.GLBLKORD, [pair_bloom, pair_iblt])

                # Increment Merkle tree height
                self.partial_tree.add_merkle_level()

        # Send Gluon block order data
        threading.Thread(target=send_order).start()

        # Wait for Get Gluon block data message
        self.server.waitOn(NetworkMsg.GET_GLBLKDAT)

        # Calculate Gluon block tx data
        missing_tx_response = self.missing_response(self.server.tx_missing_ids)

        # Send Gluon block tx data
        self.server.send(NetworkMsg.GLBLKTX, missing_tx_response)

    def listen_for_blocks(self):
        from networking import NetworkMsg
        # Wait for INV
        self.server.waitOn(NetworkMsg.INV)

        # Pretend lacking block
        # TODO: Actually check
        incoming_merkle_root = self.server.merkle_root

        # Send the Get Gluon Block message (size of mempool)
        m = len(self.txpool)

        self.server.send(NetworkMsg.GET_GLBLK, m)

        # Wait for Gluon Block
        self.server.waitOn(NetworkMsg.GLBLK)

        # Calculate missing transactions
        print('Construct GET_GLBLKDAT')
        enc_missing_ids = self.prereconcile(self.server.tx_filters[0], self.server.tx_filters[1])
        print('Constructed')

        # Send GET_GLBLKDAT
        self.server.send(NetworkMsg.GET_GLBLKDAT, enc_missing_ids)

        # Wait for GLBLKTX
        self.server.waitOn(NetworkMsg.GLBLKTX)

        # Finish reconciling transactions
        print('Reconciling transactions...')
        self.finalize_protoblock(self.server.tx_missing)
        print('Reconciled')

        # Reconcile order
        while len(self.partial_tree.top_nodes) > 1:
            # Setup pair encoding
            self.setup_pair_encoding()

            # Wait for GLBLKORD
            self.server.waitOn(NetworkMsg.GLBLKORD)
            print('Cached pairs', len(self.server.pair_filters))
            oldest_pair_filter = self.server.pair_filters.pop(0)

            print('Reconciling order...')
            empty_missing_flag = self.reconcile_pairs(oldest_pair_filter[0], oldest_pair_filter[1])
            print('Reconciled')

            # Increment Merkle tree height
            self.partial_tree.add_merkle_level()

            if empty_missing_flag:
                print('Checking Merkle root...')
                current_merkle_root = self.get_merkle_root()
                if current_merkle_root == incoming_merkle_root:
                    print('Complete reconciliation')
                    self.server.send(NetworkMsg.COMPLETE, None)
                    print('Analytics:')
                    print('Total of %d bytes received' % self.server.total_received)
                    print('Total of %d order bytes received' % self.server.total_ord_received)
                    print('Total of %d bytes sent' % self.server.total_sent)
                    break
                else:
                    print('Incomplete reconciliation, continuing...')

        self.close_connection()
        exit()