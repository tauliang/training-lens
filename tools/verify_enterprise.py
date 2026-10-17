#!/usr/bin/env python3
"""Read-only runtime verification. Credentials come from environment variables."""
import argparse,base64,json,os,re,ssl,sys,time,urllib.parse,urllib.request
from pathlib import Path
import xml.etree.ElementTree as ET

def substitute_tokens(query,tokens):
    for token,value in tokens.items():query=query.replace('$'+token+'|s$',json.dumps(value)).replace('$'+token+'$',str(value))
    if re.search(r'\$[A-Za-z_][A-Za-z0-9_.]*(?:\|s)?\$',query):raise ValueError('Unresolved dashboard token')
    return query

class Enterprise:
    def __init__(self,url,user,password,insecure=False):
        self.user=user;self.url=url.rstrip('/');self.context=ssl._create_unverified_context() if insecure else ssl.create_default_context();self.auth='Basic '+base64.b64encode((user+':'+password).encode()).decode()
    def request(self,endpoint,data=None):
        body=urllib.parse.urlencode(data).encode() if data is not None else None
        req=urllib.request.Request(self.url+endpoint,body,{'Authorization':self.auth})
        with urllib.request.urlopen(req,context=self.context,timeout=180) as r:return r.read().decode()
    def get(self,endpoint):return json.loads(self.request(endpoint+'?output_mode=json&count=0'))
    def search(self,query):
        if not query.lstrip().startswith(('search ','|')):query='search '+query
        scope='/servicesNS/'+urllib.parse.quote(self.user,safe='')+'/training_lens/search/jobs'
        created=json.loads(self.request(scope,{'search':query,'exec_mode':'blocking','output_mode':'json','earliest_time':'0','latest_time':'+10y'}))
        sid=urllib.parse.quote(created['sid'],safe='');job=self.get(scope+'/'+sid)['entry'][0]['content']
        errors=[m for m in job.get('messages',[]) if m.get('type') in ('ERROR','FATAL')]
        if job.get('isFailed') or errors:raise RuntimeError(json.dumps(errors) or 'Splunk search failed')
        return self.get(scope+'/'+sid+'/results').get('results',[])

def verify(api,expected=None):
    from verify_metric_selectors import verify as verify_metrics
    report=verify_metrics(api)
    if expected is not None:assert int(report['active_activities'])==expected,'Activity count differs'
    return report

def main():
    p=argparse.ArgumentParser();p.add_argument('--url',default='https://127.0.0.1:28089');p.add_argument('--insecure-local-test',action='store_true');p.add_argument('--expected-activities',type=int);p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    if args.insecure_local_test and urllib.parse.urlparse(args.url).hostname not in ('127.0.0.1','localhost','::1'):p.error('insecure TLS only allowed on localhost')
    api=Enterprise(args.url,os.environ.get('SPLUNK_TEST_USER','admin'),os.environ['SPLUNK_TEST_PASSWORD'],args.insecure_local_test)
    try:report=verify(api,args.expected_activities);report['status']='passed'
    except Exception as error:report={'status':'failed','error':str(error)}
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2));return 0 if report['status']=='passed' else 1
if __name__=='__main__':sys.exit(main())
