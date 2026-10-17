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
    def test_privacy_zone_from_export_masks_shared_geography(self):
        from tests.test_streams import GPX
        payload=data(**{'7':'activities/track.gpx'})
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);p=make_zip(root/'a.zip',payload=payload,extras={'activities/track.gpx':('<gpx><trk><trkseg>'+''.join('<trkpt lat="'+str(40+i*.01)+'" lon="-74"><time>2026-01-01T12:00:'+str(i*10).zfill(2)+'Z</time></trkpt>' for i in range(5))+'</trkseg></trk></gpx>').encode(),'privacy_zones.csv':b'Address,Radius,Latitude & Longitude\nprivate,5 kilometers,"40,-74"\n'})
            result=ingest.import_archive(p,root/'state')
            self.assertEqual(result['counts'].get('geography',0),0);self.assertEqual(result['counts']['sample'],5)
            text=''.join(p.read_text() for p in (root/'state/spool').rglob('*.json'));self.assertNotIn('private',text);self.assertNotIn('latitude',text)
    def test_goals_have_period_progress_and_unknown_metric_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);p=make_zip(root/'a.zip')
            result=ingest.import_archive(p,root/'state',decode=False,config={'goals':[{'sport':'Run','metric':'distance_m','target':10000,'period':'year'}]})
            goals=[json.loads(line) for chunk in result['chunks'] if '/goal/' in chunk['path'] for line in (root/'state'/chunk['path']).read_text().splitlines()]
            self.assertIn('progress_value',goals[0]);self.assertEqual(goals[0]['period_start'][5:],'01-01')
            with self.assertRaises(ValueError):ingest.import_archive(p,root/'other',decode=False,config={'goals':[{'sport':'Run','metric':'watts','target':10,'period':'year'}]})
    def test_derived_revision_changes_with_sport_and_timezone(self):
        from tests.test_streams import GPX
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);p=make_zip(root/'a.zip',payload=data(**{'7':'activities/track.gpx'}),extras={'activities/track.gpx':GPX})
            one=ingest.import_archive(p,root/'s',timezone='UTC',config={'hr_zones':[100,130,150,170]})
            def revision(manifest):
                return next(json.loads(line)['stream_revision_id'] for c in manifest['chunks'] if '/membership/' in c['path'] for line in (root/'s'/c['path']).read_text().splitlines())
            first=revision(one)
            make_zip(p,payload=data(**{'3':'Ride','7':'activities/track.gpx'}),extras={'activities/track.gpx':GPX})
            two=ingest.import_archive(p,root/'s',timezone='UTC',config={'hr_zones':[100,130,150,170]});self.assertNotEqual(first,revision(two))
            three=ingest.import_archive(p,root/'s',timezone='America/New_York',config={'hr_zones':[100,130,150,170]});self.assertNotEqual(revision(two),revision(three))
    def test_cli_worker_reports_rejected_archive_without_private_details(self):
        import subprocess,sys
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);(root/'inbox').mkdir();make_zip(root/'inbox/a.zip',payload=b'wrong\nprivate-value\n')
            ingest.scan(root,now=0,decode=False)
            command=[sys.executable,str(Path(__file__).resolve().parents[1]/'build/training_lens/bin/import_strava.py'),'--state',str(root)]
            result=subprocess.run(command,text=True,capture_output=True)
            output=json.loads(result.stdout);self.assertEqual(output['status'],'failed');self.assertEqual(output['imports'],0);self.assertEqual(output['failures'],1);self.assertNotIn('private-value',result.stdout)
    def test_gear_threshold_uses_valid_recorded_distance(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);p=make_zip(root/'a.zip');m=ingest.import_archive(p,root/'s',decode=False,config={'gear_thresholds':[{'gear':'Shoe','distance_m':60000}]})
            gear=[json.loads(line) for c in m['chunks'] if '/gear_threshold/' in c['path'] for line in (root/'s'/c['path']).read_text().splitlines()]
            self.assertEqual(len(gear),1);self.assertAlmostEqual(gear[0]['remaining_m'],53452.6)
