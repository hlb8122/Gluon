# Gluon
The Gluon Relay Protocol is an extension to [Graphene Relay Protocol](https://people.cs.umass.edu/~gbiss/graphene.pdf). Graphene allows the transactions within a block to be reconciled between two peers using Invertible Bloom Lookup Tables (IBLT). In addition to this, Gluon allows transaction order to be reconciled. Under typical conditions, this has the effect of dramatically reducing the amount of data required to transmit a block when compared to transmitting the order information in full. 

## Graphene Algorithm
### Network Phase
1. Sender:    Sends inv for a block.
2. Receiver:  Requests unknown block; includes count of txns in her IDpool, m.
3. Sender:    Creates a Bloom filter S from the set of n txn in the block and IBLT I (both created from the set of n txn ID in the block) and essential Bitcoin header fields. Both, along with the essential header fields are sent.
4. Receiver:  Creates IBLT I' from the txn IDs that pass through S. Calculates the set difference, as described [here](https://dl.acm.org/citation.cfm?id=2018462), of the two sets. Sends a request for the missing txns.
5. Sender:    Sends the requested txns and the entire order information of the block.

### Block Reconciliation Phase
1. Add the missing txns to the block and impose the order. 

## Gluon Algorithm
### Network Phase
1. Sender:    Sends inv for a block.
2. Receiver:  Requests unknown block; includes count of txns in her IDpool, m.
3. Sender:    Creates a Bloom filter S from the set of n txn in the block and IBLT I (both created from the set of n txn ID in the block) and essential Bitcoin header fields. At each height k > 0 (above the leafs) of the Merkle tree the Sender creates an IBLT I<sub>k</sub> from the set of "node<sub>i</sub> short ID || node<sub>i+1</sub> short ID". Everything, along with the essential header fields are sent.
4. Receiver:  Creates IBLT I' from the txn IDs that pass through S. Calculates the set difference using I and I', as described [here](https://dl.acm.org/citation.cfm?id=2018462), of the two sets. Sends a request for the missing txns.
5. Sender:    Sends the requested txns.

### Block Reconciliation Phase
1. Add the txns to the block.
2. Construct leafs of the Merkle Tree. Create IBLT I'<sub>1</sub> from the set of all "txn<sub>i</sub> short ID || txn<sub>(i+1)</sub> short ID".
3. Calculate the set difference using I<sub>1</sub> and I'<sub>1</sub>. Permute the transactions in the block to reconcile ordered pairs.
4. Construct the level one of the Merkle Tree. Create IBLT'<sub>2</sub> from the set of all "node<sub>i</sub> short ID || node<sub>i+1</sub> short ID".
5. Calculate the set difference using I<sub>1</sub> and I'<sub>1</sub>. Permute the transactions in the block to reconcile ordered quadruples.
6. Repeat until the block is order reconciled.

### Notes
+ After reconciliation at the kth height of the Merkle Tree we have prior knowledge at the (k+1)th height. Meaning that we can make our short IDs very short and shorter as height increases.
+ Although we are transfering lg(n) IBLT's, the size of the set seeding I<sub>k</sub> falls off as 1/2<sup>k</sup> as height k increases.
+ Typically, at each height there will be few O(1) operations and the reconciliation will suceed before height lg(n). 

### Advantages
+ Greatly decrease the amount of order information propagated.
+ The IBLTs I and I<sub>k</sub> can be relayed immediately.
+ Order reconciliation and Merkle root validation are done simultaneously.
+ Transaction validation can begin before all order information arrives. 
+ No additional round trips.
