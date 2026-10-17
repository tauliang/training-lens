import csv,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from metric_catalog import load_catalog,validate_catalog,aggregate
class MetricCatalogTests(unittest.TestCase):
 def test_supported_catalog(self):
  rows=load_catalog();self.assertGreater(len(rows),20);validate_catalog(rows)
 def test_reject_duplicates_and_executable_metadata(self):
  row=load_catalog()[0]
  for rows in ([row,row],[dict(row,source_field='distance_m | delete')],[dict(row,aggregation_key='eval')],[dict(row,metric_factor='nan')]):
   with self.assertRaises(ValueError):validate_catalog(rows)
 def test_weight_and_cadence_contracts(self):
  rows={r['metric_id']:r for r in load_catalog()}
  self.assertEqual(rows['weight']['imperial_unit'],'export units')
  self.assertEqual(rows['cadence']['prerequisite'],'confirmed_cadence')
  self.assertNotIn('vo2_max',rows)
 def test_weighted_ratios_and_empty(self):
  self.assertEqual(aggregate('weighted',[100,160],[100,300]),145)
  self.assertEqual(aggregate('ratio',[10,90],[1,3]),25)
  self.assertIsNone(aggregate('ratio',[0],[0]))
 def test_native_refresh_has_completeness_guards_and_no_raw_join(self):
  from metric_catalog import availability_search,dimension_search
  for q in (availability_search(),dimension_search()):
   self.assertNotIn(' | join ',q);self.assertNotIn(' | append [',q)
   self.assertIn('_actual_rows=_expected_rows',q)
   self.assertIn('`tl_reconciliation`',q)
   self.assertIn('override_if_empty=false',q)
 def test_lookup_seeds_and_permissions(self):
  root=Path(__file__).resolve().parents[1]/'build/training_lens'
  for name in ('metric_availability','dimension_options'):
   self.assertEqual(len((root/'lookups'/('training_lens_'+name+'.csv')).read_text().splitlines()),1)
  meta=(root/'metadata/default.meta').read_text()
  self.assertNotIn('training_lens_viewer',meta)
  self.assertIn('write : [ admin ]',meta)

 def test_package_rejects_populated_runtime_lookup(self):
  import package
  from unittest.mock import patch
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);lookups=root/'build/training_lens/lookups';lookups.mkdir(parents=True)
   (lookups/'training_lens_metric_availability.csv').write_text('snapshot_id,metric_id\nprivate,speed\n')
   with patch.object(package,'ROOT',root):
    with self.assertRaisesRegex(ValueError,'populated_runtime_cache'):package.package(root/'bad.spl')
