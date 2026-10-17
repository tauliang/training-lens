import gzip,io,json,tempfile,unittest,zipfile
from pathlib import Path
from tests.test_csv import data
from tl import archive,ingest

def make_zip(path,payload=None,extras=None):
    with zipfile.ZipFile(path,'w') as z:
        z.writestr('activities.csv',data() if payload is None else payload)
        for name,value in (extras or {}).items():z.writestr(name,value)
    return path
class ArchiveTests(unittest.TestCase):
    def test_traversal_symlink_duplicate_and_expansion_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'a.zip'
            for name in ['../escape','/absolute','activities/../../x','activities\\x']:
                make_zip(p,extras={name:b'x'})
                with self.assertRaises(ValueError):archive.inspect_archive(p)
            with zipfile.ZipFile(p,'w') as z:
                info=zipfile.ZipInfo('link');info.create_system=3;info.external_attr=0o120777<<16;z.writestr(info,'outside')
            with self.assertRaises(ValueError):archive.inspect_archive(p)
            make_zip(p,extras={'activities/a.fit.gz':gzip.compress(b'0'*1000)})
            with zipfile.ZipFile(p) as z:
                with self.assertRaises(ValueError):archive.read_member(z,'activities/a.fit.gz',max_bytes=100)
    def test_outer_limits_and_missing_schema(self):
        with tempfile.TemporaryDirectory() as t:
            p=make_zip(Path(t)/'a.zip')
            with self.assertRaises(ValueError):archive.inspect_archive(p,max_archive_bytes=10)
            make_zip(p,payload=b'wrong\n1\n')
            with self.assertRaises(ValueError):ingest.import_archive(p,Path(t)/'state',decode=False)
class LifecycleTests(unittest.TestCase):
    def test_deterministic_reimport_and_new_snapshot(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);p=make_zip(root/'a.zip');state=root/'state'
            a=ingest.import_archive(p,state,decode=False);b=ingest.import_archive(p,state,decode=False)
            self.assertEqual(a['snapshot_id'],b['snapshot_id']);self.assertEqual(a['counts']['activity'],1)
            before={p.name:p.read_bytes() for p in (state/'spool').rglob('*.json')}
            make_zip(p,payload=data(**{'10':'5000'}));c=ingest.import_archive(p,state,decode=False)
            self.assertNotEqual(a['snapshot_id'],c['snapshot_id']);self.assertEqual(before.keys()-{p.name for p in (state/'spool').rglob('*.json')},set())
            self.assertFalse((state/'active.json').exists(),'spooling must not activate a snapshot')
    def test_two_stable_scans_and_recovery(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);inbox=root/'inbox';inbox.mkdir();make_zip(inbox/'a.zip')
            self.assertEqual(ingest.scan(root,now=100,decode=False),[])
            self.assertEqual(ingest.scan(root,now=159,decode=False),[])
            result=ingest.scan(root,now=160,decode=False);self.assertEqual(len(result),1)
            self.assertEqual(ingest.scan(root,now=220,decode=False),[])
            manifest=json.loads(next((root/'manifests').glob('*.json')).read_text());chunk=root/manifest['chunks'][0]['path'];chunk.unlink()
            self.assertEqual(len(ingest.scan(root,now=280,decode=False)),1);self.assertTrue(chunk.exists())
    def test_config_change_creates_new_snapshot(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);p=make_zip(root/'a.zip');a=ingest.import_archive(p,root/'s',decode=False);b=ingest.import_archive(p,root/'s',decode=False,timezone='America/New_York');self.assertNotEqual(a['snapshot_id'],b['snapshot_id'])
