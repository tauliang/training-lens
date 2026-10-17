import unittest
from tl import reconcile
class ReconciliationTests(unittest.TestCase):
    def test_delayed_and_duplicated_records(self):
        expected={'snapshot':2,'revision':3}
        actual={'snapshot':['a','b','b'],'revision':['x','y']}
        self.assertFalse(reconcile.complete(expected,actual))
        actual['revision']+=['z','z'];self.assertTrue(reconcile.complete(expected,actual))
        actual['revision'].append('unexpected');self.assertFalse(reconcile.complete(expected,actual))
    def test_missing_group_and_empty_export_never_ready(self):
        self.assertFalse(reconcile.complete({},{}));self.assertFalse(reconcile.complete({'s':2,'r':1},{'s':['a','b']}))
