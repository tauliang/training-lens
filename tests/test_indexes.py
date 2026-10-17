import configparser,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]/'build/training_lens/default'
class IndexTests(unittest.TestCase):
    def test_ingested_records_use_strava_and_keep_location_separate(self):
        indexes=configparser.ConfigParser();indexes.read(ROOT/'indexes.conf');self.assertIn('strava',indexes.sections())
        inputs=configparser.ConfigParser();inputs.read(ROOT/'inputs.conf')
        for section in inputs.sections():
            kind=section.rsplit('/',1)[-1].rstrip(']')
            if kind in ('gps','geography'):continue
            if section.startswith('monitor:'):self.assertEqual(inputs[section]['index'],'strava')
        self.assertEqual(inputs['monitor://$SPLUNK_HOME/var/lib/training_lens/spool/gps']['index'],'strava_private')
