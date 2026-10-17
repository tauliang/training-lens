import importlib.util,unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location('verifier',Path(__file__).resolve().parents[1]/'tools/verify_enterprise.py');v=importlib.util.module_from_spec(spec);spec.loader.exec_module(v)
class VerifierTests(unittest.TestCase):
    def test_regex_end_anchor_is_not_an_unresolved_token(self):
        self.assertEqual(v.substitute_tokens('where match(id,"^[0-9]+$") AND id=$id|s$',{'id':'123'}),'where match(id,"^[0-9]+$") AND id="123"')
        with self.assertRaises(ValueError):v.substitute_tokens('where id=$missing|s$',{})
    def test_search_job_failure_is_not_treated_as_an_empty_success(self):
        class JobTransport(v.Enterprise):
            def request(self,endpoint,data=None):
                if endpoint.endswith('/search/jobs') and data is not None:return '{"sid":"job1"}'
                if '/job1?' in endpoint:return '{"entry":[{"content":{"isFailed":true,"messages":[{"type":"FATAL","text":"bad where expression"}]}}]}'
                raise AssertionError('Unexpected request boundary')
        api=JobTransport('https://localhost','user','temporary')
        with self.assertRaisesRegex(RuntimeError,'bad where expression'):api.search('| makeresults')
