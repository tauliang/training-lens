import configparser,re,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]/'build/training_lens/default'
class RetentionTests(unittest.TestCase):
    def test_active_snapshot_marker_lives_as_long_as_activity_history(self):
        macros=configparser.ConfigParser(interpolation=None);macros.read(ROOT/'macros.conf')
        indexes=configparser.ConfigParser(interpolation=None);indexes.read(ROOT/'indexes.conf')
        ready_index=re.search(r'index=([a-z_]+)',macros['tl_active']['definition'])[1]
        self.assertGreaterEqual(int(indexes[ready_index]['frozenTimePeriodInSecs']),int(indexes['strava']['frozenTimePeriodInSecs']))
