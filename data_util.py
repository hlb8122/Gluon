import json

def fetchtxsfromfile(fn):
    with open(fn, 'r') as f:
        raw = f.read()
    block = json.loads(raw)
    return [tx for tx in block['tx']]

def buildmempool(fns):
    mempool = []
    for fn in fns:
        mempool.extend(fetchtxsfromfile(fn))
    mempool.sort()
    return mempool
