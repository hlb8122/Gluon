import requests, json, os

URIBASE = "https://bch-chain.api.btc.com/v3/"
DATADIR = "./blockdata/"

if not os.path.exists(DATADIR):
    os.makedirs(DATADIR)

def saveCache(filename, data):
    with open(os.path.join(DATADIR, filename), 'wb') as f:
        f.write(data)

def getCached(filename):
    fname = os.path.join(DATADIR, filename)
    if(os.path.exists(fname)):
        with open(fname) as f:
            return f.read()
    else:
        return None

def getBlock(hash):
    data = getCached(hash + ".block")
    if(data is None):
        resp = requests.get("https://blockchain.info/rawblock/" + hash)
        #resp = requests.get(URIBASE + "block/" + hash + "/tx")
        data = resp.content
        saveCache(hash + ".block", data)
    return json.loads(data)

def getTxsFromBlock(hash):
    jobj = getBlock(hash)
    retval = []
    for tx in jobj["tx"]:
        retval.append(tx["hash"])
    return retval

# For BTC block height 540801
orphan = "0000000000000000000d450f4d1ccbc5107f1eaa98284c2c87b6a0702c49c439"
actual = "0000000000000000000907aed7dfdea5e568283b9548a4fc9aed0fc3498acdab"

# for BCH block height of 546817
# orphan = "000000000000000001aea4db16fb3ebc0528680549fcc713412bd0e44e92daa9"
# actual = "000000000000000001a3893ae17d46b0ed36a4cd28d0e63ac73de2d6cca62b2a"
