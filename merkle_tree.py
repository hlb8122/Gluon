import byte_tools

class PartialMerkleTree:
    def __init__(self, top_nodes):
        self.top_nodes = top_nodes

    @classmethod
    def from_leaf_values(cls, leaf_values):
        leaf_nodes = [MerkleNode.from_leaf_value(leaf) for leaf in leaf_values]
        if len(leaf_values) % 2 == 1:
            leaf_nodes.append(MerkleNode.null())
        return cls(leaf_nodes)

    def add_merkle_level(self):
        # Construct height above in the Merkle Tree

        # Make current height even
        if len(self.top_nodes) % 2 == 1:
            self.top_nodes.append(MerkleNode.null())

        top_nodes = self.top_nodes
        self.top_nodes = [MerkleNode(top_nodes[2 * i], top_nodes[2 * i + 1]) for i in range(int(len(self.top_nodes) / 2))]

    def get_top_values(self):
        return [node.value for node in self.top_nodes]

    def rotate(self):
        self.top_nodes = self.top_nodes[-1:] + self.top_nodes[:-1]

    def get_top_value_pairs(self):
        # Get the pairs of consecutive values of the top nodes
        top = self.get_top_values()
        l = list(zip(top[::2], top[1::2]))
        return l

    def get_leafs(self):
        # Get the values of all leaf nodes
        leafs = []
        for node in self.top_nodes:
            leafs.extend(node.get_leaf_values())
        return leafs

    def make_tree(self):
        # Construct entire tree
        while(len(self.top_nodes) > 1):
            self.add_merkle_level()

    def reconcile_order(self, missing_pairs):
        # Reconcile order given missing pairs

        top_pairs = self.get_top_value_pairs()
        top_values = self.get_top_values()
        new_top_pairs = self.get_top_value_pairs()

        # Find values that are out of order
        excess_values = []
        for missing_pair in missing_pairs:
            excess_values.append(missing_pair[0])
            excess_values.append(missing_pair[1])

        # Find pairs that are erroneous
        excess_pairs = []
        for pair in top_pairs:
            if pair[0] in excess_values or pair[1] in excess_values:
                excess_pairs.append(pair)

        # Replace error pairs with missing pairs
        for i, missing_pair in enumerate(missing_pairs):
            new_top_pairs[top_pairs.index(excess_pairs[i])] = missing_pair

        # Reorder pairs into sensible order
        # TODO: Make this more succinct remodeling this entire procedure
        def new_sort(pair):
            return top_values.index(pair[1])


        new_top_pairs.sort(key=new_sort)

        # Recalculate top values by expanding new top pairs
        expand = []
        for pair in new_top_pairs:
            expand.append(pair[0])
            expand.append(pair[1])

        new_order = [top_values.index(v) for v in expand]

        # Permute top nodes based on the new order
        self.top_nodes = [self.top_nodes[i] for i in new_order]


class MerkleNode:
    def __init__(self, left, right, value=None):
        if value is None:
            self.value = byte_tools.sha256(left.value + right.value)
        else:
            self.value = value
        self.left = left
        self.right = right

    def is_null(self):
        return (self.value == byte_tools.empty_hash)

    def is_leaf(self):
        return ((self.left == None) & (not self.is_null()))

    @classmethod
    def from_leaf_value(cls, leaf):
        return cls(None, None, leaf)

    @classmethod
    def null(cls):
        return cls(None, None, byte_tools.empty_hash)

    def get_leaf_values(self):
        if self.is_null():
            # TODO: Is this necessary?
            return []

        if self.is_leaf():
            return [self.value]

        return self.left.get_leaf_values() + self.right.get_leaf_values()