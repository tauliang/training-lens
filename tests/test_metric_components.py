import sys,unittest,json,xml.etree.ElementTree as ET
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from dashboard_components import metric_query,options_query
class MetricComponentsTests(unittest.TestCase):
 def test_safe_selection(self):
  q=metric_query('activity',['speed','avg_hr'])
  self.assertIn('$metric|s$',q);self.assertNotIn('$metric$',q)
  self.assertIn('sum(numerator)',q);self.assertIn('sum(denominator)',q)
 def test_no_raw_postprocessing(self):
  q=metric_query('activity',['speed']);self.assertIn('BY bucket series',q)
 def test_unsupported_metric_rejected(self):
  with self.assertRaises(ValueError):metric_query('activity',['arbitrary | delete'])
 def test_availability_scope_and_explicit_empty(self):
  q=options_query(['speed']);self.assertIn('snapshot_id',q);self.assertIn('valid_count>0',q);self.assertIn('__auto__',q)
 def test_annual_zone_and_sport_rate_rules(self):
  from dashboard_components import zone_source
  q=zone_source();self.assertIn('comparison_month_day',q);self.assertIn('$grain|s$="Year"',q)
  self.assertIn('metric_id IN ("pace","speed") AND $sport|s$="All"',metric_query('activity',['speed']))
 def test_mode_gate_always_emits_a_search_predicate(self):
  from dashboard_components import Page
  p=Page('test','Test','Fixture');p.modes('mode','Details',{'A':'index=strava earliest=0 | stats count','B':'index=strava earliest=0 | stats count'})
  query=next(d['options']['query'] for k,d in p.doc['dataSources'].items() if k.startswith('table_'))
  self.assertIn('return $search',query);self.assertIn('"*"',query)
 def test_release_metadata(self):
  import configparser
  c=configparser.ConfigParser();c.read(Path(__file__).resolve().parents[1]/'build/training_lens/default/app.conf')
  self.assertEqual(c['launcher']['version'],'1.0.1');self.assertEqual(c['id']['version'],'1.0.1');self.assertTrue(c.getboolean('package','check_for_updates'));self.assertEqual(c['launcher']['author'],'Tau Liang')
