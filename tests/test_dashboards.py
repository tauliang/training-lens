import json,subprocess,sys,unittest,xml.etree.ElementTree as ET
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class DashboardTests(unittest.TestCase):
    def test_generated_views_have_resolvable_sources_and_escaped_filters(self):
        subprocess.run([sys.executable,str(ROOT/'tools/generate_dashboards.py')],check=True)
        views=list((ROOT/'build/training_lens/default/data/ui/views').glob('*.xml'));self.assertEqual(len(views),8)
        for file in views:
            doc=ET.parse(file).getroot();self.assertEqual(doc.attrib.get('version'),'2');definition=json.loads(doc.findtext('definition'))
            for viz in definition['visualizations'].values():
                for key in viz.get('dataSources',{}).values():self.assertIn(key,definition['dataSources'])
            for ds in definition['dataSources'].values():
                query=ds['options']['query']
                for token in ['sport','gear','snapshot','quality_mode','activity_id']:
                    self.assertNotIn('$'+token+'$',query,'Unescaped SPL token')
            self.assertEqual(definition['inputs']['time']['options']['defaultValue'],'-1y,now')
    def test_package_reproducible_and_no_private_material(self):
        import tempfile,tarfile
        with tempfile.TemporaryDirectory() as t:
            files=[]
            for name in ['a.spl','b.spl']:
                p=Path(t)/name;subprocess.run([sys.executable,str(ROOT/'tools/package.py'),'--output',str(p)],check=True,capture_output=True);files.append(p.read_bytes())
                with tarfile.open(p) as tar:
                    names=tar.getnames();self.assertTrue(all(x.startswith('training_lens/') for x in names));self.assertFalse(any('.private' in x or '__pycache__' in x or x.endswith('.zip') for x in names))
            self.assertEqual(files[0],files[1])
