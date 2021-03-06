# Gluon
The Gluon Block Propagation Protocol is an extension to the [Graphene Block Propagation Protocol](https://people.cs.umass.edu/~gbiss/graphene.pdf). Graphene allows the transactions within a block to be reconciled between two peers using [Invertible Bloom Lookup Tables](https://arxiv.org/pdf/1101.2245.pdf) (IBLT). In addition to this, Gluon allows transaction order to be reconciled. Under typical conditions, this has the effect of dramatically reducing the amount of data required to transmit a block when compared to transmitting the order information in full. 

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
4. Construct the height one nodes of the Merkle Tree (above the leafs). Create IBLT I'<sub>2</sub> from the set of all "node<sub>i</sub> short ID || node<sub>i+1</sub> short ID".
5. Calculate the set difference using I<sub>1</sub> and I'<sub>1</sub>. Permute the transactions in the block to reconcile ordered quadruples.
6. Repeat until the block is order reconciled.

### Notes
+ We can replace "node<sub>i</sub> short ID || node<sub>i+1</sub> short ID" with a very small encoding. This encoding can get smaller as we height k increases.
+ Although we are transfering lg(n) IBLT's, the size of the set seeding I<sub>k</sub> falls off as 1/2<sup>k</sup> as height k increases.
+ Typically, at each height there will be few O(1) operations and the reconciliation will succeed before height lg(n). 
+ Alice may provide hints to Bob in step 5 as to where the missing transactions (found in the Graphene phase) lie in relation to Bob's transactions. For example if Bob is missing transactions 3 through 8 then Alice may transfer them along with a short ID of transaction 2. This allows Bob to insert the missing transactions in a more appriopriate section of his block and hence smooth the order reconciliation phases. 

### Advantages
+ Greatly decrease the amount of order information propagated.
+ The IBLTs I and I<sub>k</sub> can be relayed immediately.
+ Order reconciliation and Merkle root validation are done simultaneously.
+ Transaction validation can begin before all order information arrives. 
+ No additional round trips over Graphene.

### Disadvantages
+ Parameters need to be tuned as in Graphene.

## Proof of Concept Implementation
### Requirements
Python 3.5+ (Python < 3.5 doesn't preserve order of keys in dictionaries which we leverage)
#### Libraries
+ bitarray
+ mmh3
+ msgpack
+ numpy
+ requests

### Testing
Run test_receive.py and test_send.py on your local machine.

### Parameter Tweaking
Parameter selection is not fully autonomous at the moment, after encountering a decoding error in the transaction reconcilliation phase one should increase the est_missing_tx_perc value in test_send.py. Similarly, in the order reconcilliation phase one should increase the est_missing_pair_perc value. 

Work needs to be done on selection of parameters.

### Architecture
#### Data Structures
The main constituent data structures of the protocol mirror that of Graphene:
+ INV - A message, sent by the sender, initiating the Gluon protocol.
+ GET_GLBLK - A request, from the receiver, indicating that the receiver wants to receive the block.
+ GLBLK(ORD) - A message, sent by the sender, containing Bloom filters and IBLTs for transactions and pairs.
+ GET_GLBLKTX - A request, from the receiver, for transactions missing from the receivers transaction pool.
+ GLBLKTX - A message, sent by the sender, containing missing transactions.

#### Procedures
+ The send and receive protocol main protocol can be seen in node.py under send_block and listen_for_block procedures.
+ Order reconciliation can be seen in node.py under reconcile_pairs and merkle_tree.py in the reconcile_order procedures.
