import requests, json, os

#URIBASE = "https://bch-chain.api.btc.com/v3/block/"
URIBASE = 'https://blockchain.info/rawblock/'
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
        resp = requests.get(URIBASE + hash)
        #resp = requests.get(URIBASE + hash + "/tx")
        data = resp.content
        saveCache(hash + ".block", data)
    return json.loads(data)

def getTxsFromBlock(hash):
    jobj = getBlock(hash)
    retval = []
    for tx in jobj["tx"]:
        retval.append(tx["hash"])
    return retval

# For BTC block #497373
orphan = "0000000000000000000d450f4d1ccbc5107f1eaa98284c2c87b6a0702c49c439"
actual = "0000000000000000000907aed7dfdea5e568283b9548a4fc9aed0fc3498acdab"