import _pickle as cpickle
import socket
import threading
import time
from iblt_slim import SIBLT
from bloom import BloomFilter
from enum import Enum

class NetworkMsg(Enum):
    INV=0
    GET_GLBLK=1
    GLBLK=2
    GET_GLBLKDAT=3
    GLBLKTX=4
    GLBLKORD=5
    COMPLETE=6


class NodeServer:
    def __init__(self, ip, port):
        # Network Parameters
        self.ip = ip
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client_sock = None

        # Analytics
        self.total_sent = 0
        self.total_received = 0
        self.total_ord_sent = 0
        self.total_ord_received = 0

        # Cached values
        self.tx_filters = None
        self.merkle_root = None
        self.tx_missing_ids = None
        self.tx_missing = None
        self.pair_filters = []
        self.other_txpool_size = None
        self.complete = None

    def start(self):
        threading.Thread(target=self.server_handler).start()

    def connectTo(self, ip, port):
        self.client_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        while True:
            try:
                self.client_sock.connect((ip, port))
                break
            except socket.error:
                pass

    def send(self, typ, obj):
        if self.client_sock is None:
            print("Unable to send data -- not connected!")
        else:
            # Send type
            # TODO: Don't send length for fixed length types
            self.client_sock.send(typ.value.to_bytes(1, 'big'))
            if typ == NetworkMsg.INV:
                # Send message
                print('Sending INV...')
                self.client_sock.send(obj)

                length = len(obj)
                print('Sent INV of size %d bytes' % length)
                self.total_sent += length
            if typ == NetworkMsg.GET_GLBLK:
                # Encode message
                message = obj.to_bytes(3, 'big')

                # Send message
                length = len(message)
                print('Sending GET_GLBLK...')
                self.client_sock.send(message)
                print('Sent GET_GLBLK of size %d bytes' % length)
                self.total_sent += length
            if typ == NetworkMsg.GLBLK:
                # Encode message
                bloom = obj[0]
                iblt = obj[1]
                iblt_b = iblt.serialise()
                bloom_b = bloom.serialise()

                print('Sending GLBLK...')
                # Send Bloom Length
                bloom_length = len(bloom_b)
                self.client_sock.send(bloom_length.to_bytes(3, 'big'))

                # Send bloom
                self.client_sock.send(bloom_b)

                # Send Bloom Length
                iblt_length = len(iblt_b)
                self.client_sock.send(iblt_length.to_bytes(3, 'big'))

                # Send bloom
                self.client_sock.send(iblt_b)
                print('Sent GLBLK of size %d bytes' % (bloom_length + iblt_length))
                self.total_sent += bloom_length + iblt_length
            if typ == NetworkMsg.GET_GLBLKDAT:
                # Encode message
                message = bytes(cpickle.dumps(obj))

                # Send message length
                length = len(message)
                self.client_sock.send(length.to_bytes(3, 'big'))

                # Send message
                print('Sending GET_GLBLKDAT...')
                self.client_sock.send(message)
                print('Sent GLBLKDAT of size %d bytes' % length)
                self.total_sent += length
            elif typ == NetworkMsg.GLBLKTX:
                # Encode message
                message = bytes(cpickle.dumps(obj))

                # Send message length
                length = len(message)
                self.client_sock.send(length.to_bytes(3, 'big'))

                # Send message
                print('Sending GLBLKTX...')
                self.client_sock.send(message)
                print('Sent GLBLKTX of size %d bytes' % length)
                self.total_sent += length
            elif typ == NetworkMsg.GLBLKORD:
                # Encode message
                bloom = obj[0]
                iblt = obj[1]
                iblt_b = iblt.serialise()
                bloom_b = bloom.serialise() # TODO: Better serialization

                print('Sending GLBLKORD...')
                # Send Bloom Length
                bloom_length = len(bloom_b)
                self.client_sock.send(bloom_length.to_bytes(3, 'big'))

                # Send bloom
                self.client_sock.send(bloom_b)

                # Send IBLT Length
                iblt_length = len(iblt_b)
                self.client_sock.send(iblt_length.to_bytes(3, 'big'))

                # Send bloom
                self.client_sock.send(iblt_b)
                print('Sent GLBLKORD of size %d bytes' % (bloom_length + iblt_length))
                self.total_sent += bloom_length + iblt_length
                self.total_ord_sent += bloom_length + iblt_length
            elif typ == NetworkMsg.COMPLETE:
                # Send reconciliation analytics
                # TODO: Implement

                # Create analytics
                message = int(0).to_bytes(1,'big')

                # Send analytics
                self.client_sock.send(message)
                self.total_sent += 1

    def waitOn(self, typ):
        if typ == NetworkMsg.INV:
            print('Waiting for INV...')
            while(self.merkle_root is None):
                time.sleep(1)
        elif typ == NetworkMsg.GET_GLBLK:
            print('Waiting for GET_GLBLK...')
            while(self.other_txpool_size is None):
                time.sleep(1)
        elif typ == NetworkMsg.GLBLK:
            print('Waiting for GLBLK...')
            while(self.tx_filters is None):
                time.sleep(1)
        elif typ == NetworkMsg.GET_GLBLKDAT:
            print('Waiting for GET_GLBLKDAT...')
            while(self.tx_missing_ids is None):
                time.sleep(1)
        elif typ == NetworkMsg.GLBLKTX:
            print('Waiting for GLBLKTX...')
            while(self.tx_missing is None):
                time.sleep(1)
        elif typ == NetworkMsg.GLBLKORD:
            print('Waiting for GET_GLBLKORD...')
            while(self.pair_filters == []):
                time.sleep(1)

    def server_handler(self):
        self.sock.bind((self.ip, self.port))
        self.sock.listen(1)
        print("Starting server on %s : %d" % (self.ip, self.port))

        try:
            conn, addr = self.sock.accept()
        except:
            print("Server never received a connection...closing")
            return

        print("Connection from %s" % (addr[0]))
        while True:
            data = conn.recv(1)
            if not data: break
            # First we're always going to get the NodeServerMsg data
            typ = int.from_bytes(data, 'big')

            if typ == NetworkMsg.INV.value:
                # Receive INV
                print('Receiving INV...')
                data = conn.recv(32)
                self.merkle_root = data
                print("Received INV of size 32 bytes")
                self.total_received += 32
            elif typ == NetworkMsg.GET_GLBLK.value:
                # Receive GET_GLBLK
                print('Receiving GET_GLBLK...')
                data = conn.recv(3)
                self.other_txpool_size = int.from_bytes(data, 'big')
                print("Received GET_GRBLK of size 3 bytes")
                self.total_received += 3
            elif typ == NetworkMsg.GLBLK.value:
                # Receive TX Bloom
                print('Receiving GLBLK...')
                data = conn.recv(3)
                tx_bloom_len = int.from_bytes(data, 'big')

                data = conn.recv(tx_bloom_len)
                tx_bloom = BloomFilter.deserialise(data)
                print("Received TX Bloom of size %d bytes" % tx_bloom_len)

                # Receive TX IBLT
                data = conn.recv(3)
                tx_iblt_len = int.from_bytes(data, 'big')

                data = conn.recv(tx_iblt_len)
                tx_iblt = SIBLT.deserialise(data)
                print("Received TX IBLT of size %d bytes" % tx_iblt_len)
                self.total_received += tx_bloom_len + tx_iblt_len

                # Construct GLBLK
                self.tx_filters = [tx_bloom, tx_iblt]
            elif typ == NetworkMsg.GET_GLBLKDAT.value:
                # Receive GET_GLBLKDAT
                print('Receiving GET_GLBLKDAT...')
                data = conn.recv(3)
                pair_filter_len = int.from_bytes(data, 'big')

                data = conn.recv(pair_filter_len)
                self.tx_missing_ids = cpickle.loads(data)
                print("Received GET_GLBLKDAT of size %d bytes" % pair_filter_len)
                self.total_received += pair_filter_len
            elif typ == NetworkMsg.GLBLKTX.value:
                # Receive GLBLKTX
                print('Receiving GLBLKTX...')
                data = conn.recv(3)
                tx_missing_length = int.from_bytes(data, 'big')

                data = conn.recv(tx_missing_length)
                self.tx_missing = cpickle.loads(data)
                print("Received GLBLKTX of size %d bytes" % tx_missing_length)
                self.total_received += tx_missing_length
            elif typ == NetworkMsg.GLBLKORD.value:
                # Receive TX
                print('Receiving GLBLKORD...')
                data = conn.recv(3)
                bloom_len = int.from_bytes(data, 'big')

                data = conn.recv(bloom_len)
                pair_bloom = BloomFilter.deserialise(data)
                print("Received Bloom of size %d bytes" % bloom_len)

                # Receive IBLT
                data = conn.recv(3)
                iblt_len = int.from_bytes(data, 'big')

                data = conn.recv(iblt_len)
                pair_iblt = SIBLT.deserialise(data)
                print("Received IBLT of size %d bytes" % iblt_len)
                self.total_received += bloom_len + iblt_len
                self.total_ord_received += bloom_len + iblt_len

                # Construct GLBLK
                self.pair_filters.append([pair_bloom, pair_iblt])
            elif typ == NetworkMsg.COMPLETE.value:
                # Receive reconciliation analytics
                print('Receiving reconciliation analytics...')
                data = conn.recv(1)
                # TODO: Implement
                self.complete = data
                print('Received analytics of size %d bytes' % 1)
                self.total_received += 1

        conn.close()

    def shutdown(self):
        if(self.sock is not None):
            self.sock.close()
            print("Server shutdown %s : %d" % (self.ip, self.port))
        if(self.client_sock is not None):
            self.client_sock.close()