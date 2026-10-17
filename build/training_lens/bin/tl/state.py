"""Single writer and atomic private state."""
import contextlib
import fcntl
import json
import os
from pathlib import Path

@contextlib.contextmanager
def lock(root):
    root=Path(root);root.mkdir(parents=True,exist_ok=True,mode=0o700)
    with (root/'worker.lock').open('a') as f:
        fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
        try:yield
        finally:fcntl.flock(f,fcntl.LOCK_UN)

def atomic(path,data):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    temp=path.with_name(path.name+'.partial')
    with temp.open('wb') as f:
        os.chmod(temp,0o600);f.write(data);f.flush();os.fsync(f.fileno())
    os.replace(temp,path)

def write_json(path,value):atomic(path,(json.dumps(value,sort_keys=True,allow_nan=False)+'\n').encode())
def load(path,default=None):
    try:return json.loads(Path(path).read_text())
    except FileNotFoundError:return default
