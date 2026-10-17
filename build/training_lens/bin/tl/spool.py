import hashlib
import json
from .state import atomic

class Spool:
    def __init__(self,root,chunk_size=5000):
        self.root=root;self.chunk_size=chunk_size;self.buffers={};self.receipts=[];self.counts={}
    def add(self,record):
        kind=record['kind'];self.counts[kind]=self.counts.get(kind,0)+1
        buf=self.buffers.setdefault(kind,[]);buf.append(record)
        if len(buf)>=self.chunk_size:self.flush(kind)
    def flush(self,kind):
        buf=self.buffers.get(kind,[])
        if not buf:return
        data=b''.join((json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode() for x in buf)
        digest=hashlib.sha256(data).hexdigest();rel='spool/'+kind+'/'+digest+'.json';path=self.root/rel
        if not path.exists() or hashlib.sha256(path.read_bytes()).hexdigest()!=digest:atomic(path,data)
        self.receipts.append({'path':rel,'sha256':digest,'records':len(buf)});self.buffers[kind]=[]
    def finish(self):
        for kind in list(self.buffers):self.flush(kind)
        return self.receipts
