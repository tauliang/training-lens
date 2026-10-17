#!/usr/bin/env python3
"""Read-only runtime verification. Credentials come from environment variables."""
import argparse,base64,json,os,ssl,sys,time,urllib.parse,urllib.request
from pathlib import Path
import xml.etree.ElementTree as ET

class Enterprise:
    def __init__(self,url,user,password,insecure=False):
        self.url=url.rstrip('/');self.context=ssl._create_unverified_context() if insecure else ssl.create_default_context();self.auth='Basic '+base64.b64encode((user+':'+password).encode()).decode()
    def request(self,endpoint,data=None):
        body=urllib.parse.urlencode(data).encode() if data is not None else None
        req=urllib.request.Request(self.url+endpoint,body,{'Authorization':self.auth})
        with urllib.request.urlopen(req,context=self.context,timeout=180) as r:return r.read().decode()
    def get(self,endpoint):return json.loads(self.request(endpoint+'?output_mode=json&count=0'))
    def search(self,query):
        if not query.lstrip().startswith(('search ','|')):query='search '+query
        output=self.request('/servicesNS/admin/training_lens/search/jobs/export',{'search':query,'output_mode':'json','preview':'false','earliest_time':'0','latest_time':'+10y'})
        entries=[json.loads(line) for line in output.splitlines() if line.strip()];errors=[]
        for entry in entries:
            errors.extend(x for x in entry.get('messages',[]) if x.get('type') in ('ERROR','FATAL'))
            if entry.get('type') in ('ERROR','FATAL'):errors.append(entry)
        if errors:raise RuntimeError(json.dumps(errors))
        return [x['result'] for x in entries if 'result' in x and not x.get('preview')]

def verify(api,expected=None):
    version=api.get('/services/server/info')['entry'][0]['content']['version'];report={'version':version,'checks':[]}
    current=api.search('`tl_active`');assert len(current)==1 and current[0]['snapshot_id']!='__none__','No reconciled active snapshot'
    stats=api.search('`tl_activities` | stats count AS activities sum(distance_m) AS meters')[0]
    if expected is not None:assert int(stats['activities'])==expected,'Activity count differs'
    report['checks'].append({'name':'active_summary','activities':int(stats['activities'])})
    views=[v for v in api.get('/servicesNS/admin/training_lens/data/ui/views')['entry'] if v['acl']['app']=='training_lens'];assert len(views)==8
    first=api.search('`tl_activities` | head 1 | fields activity_id')[0]['activity_id']
    tokens={'snapshot':'latest','sport':'All','gear':'All','quality_mode':'Reported','units':'Metric','activity_id':first,'time.earliest':'0','time.latest':'+10y'}
    for view in views:
        definition=json.loads(ET.fromstring(view['content']['eai:data']).findtext('definition'))
        for ds in definition['dataSources'].values():
            query=ds['options']['query']
            for token,value in tokens.items():query=query.replace('$'+token+'|s$',json.dumps(value)).replace('$'+token+'$',value)
            assert '$' not in query,'Unresolved token in '+view['name']+'/'+ds['name']
            start=time.monotonic();rows=api.search(query);report['checks'].append({'view':view['name'],'panel':ds['name'],'rows':len(rows),'seconds':round(time.monotonic()-start,3)})
    return report

def main():
    p=argparse.ArgumentParser();p.add_argument('--url',default='https://127.0.0.1:28089');p.add_argument('--insecure-local-test',action='store_true');p.add_argument('--expected-activities',type=int);p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    if args.insecure_local_test and urllib.parse.urlparse(args.url).hostname not in ('127.0.0.1','localhost','::1'):p.error('insecure TLS only allowed on localhost')
    api=Enterprise(args.url,os.environ.get('SPLUNK_TEST_USER','admin'),os.environ['SPLUNK_TEST_PASSWORD'],args.insecure_local_test)
    try:report=verify(api,args.expected_activities);report['status']='passed'
    except Exception as error:report={'status':'failed','error':str(error)}
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2));return 0 if report['status']=='passed' else 1
if __name__=='__main__':sys.exit(main())
