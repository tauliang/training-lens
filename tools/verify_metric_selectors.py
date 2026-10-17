#!/usr/bin/env python3
"""Verify installed native sources and catalog choices using completed jobs.

Uses only synthetic fixtures supplied by an operator. Credentials are environment
variables. It expands ds.chain searches and resolves result tokens independently.
"""
import argparse,json,os,time,urllib.parse,xml.etree.ElementTree as ET
from pathlib import Path
from verify_enterprise import Enterprise,substitute_tokens
from metric_catalog import load_catalog,availability_search,dimension_search

def defaults(doc):
 result={'sport':'All','gear':'All','quality_mode':'Validated','units':'Metric','grain':'Month','history_scope':'Full years','cadence_units':'Unconfirmed','snapshot':'latest','time.earliest':'0','time.latest':'now'}
 for definition in doc['inputs'].values():
  o=definition['options'];token=o['token'];v=o.get('defaultValue','')
  if definition['type']=='input.timerange':result[token+'.earliest'],result[token+'.latest']=v.split(',')
  else:result[token]=v
 return result

def resolve_source(doc,key,tokens):
 ds=doc['dataSources'][key];q=ds['options']['query']
 if ds['type']=='ds.chain':q=resolve_source(doc,ds['options']['extend'],tokens)+' '+q
 return substitute_tokens(q,tokens)

def verify_calculations(api):
 from dashboard_components import metric_query
 tokens={'sport':'All','metric':'speed','units':'Imperial','grain':'Year','split':'Sport','cadence_units':'Strides/min'}
 fixture='| makeresults count=2 | streamstats count AS i | eval sport="Run",local_year=2022,local_date=if(i=1,"2022-01-01","2022-01-02"),moving_time_s=if(i=1,3600,10800),distance_m=if(i=1,16093.44,144840.96),average_hr=if(i=1,100,160),max_hr=if(i=1,120,180),average_cadence=if(i=1,80,90),athlete_weight=if(i=1,75,73),pace_valid=1,duration_valid=1,distance_valid=1'
 checks=[]
 for metric,expected,unit in [('speed',25,'MPH'),('avg_hr',145,'bpm'),('cadence',175,'steps/min'),('peak_hr',180,'bpm'),('weight',74,'export units')]:
  q=metric_query('activity',[metric]);q=fixture+q[q.index(' | eval metric_id='):];t=dict(tokens,metric=metric)
  rows=api.search(substitute_tokens(q,t));assert len(rows)==1,(metric,rows)
  assert abs(float(rows[0]['value'])-expected)<.01,(metric,rows)
  assert rows[0]['unit']==unit,(metric,rows)
  checks.append({'fixture':metric,'value':rows[0]['value'],'unit':unit})
 q=metric_query('activity',['speed']);q=fixture+' | eval moving_time_s=0,pace_valid=0'+q[q.index(' | eval metric_id='):]
 rows=api.search(substitute_tokens(q,tokens));assert not rows or not rows[0].get('value'),rows
 checks.append({'fixture':'zero_denominator','status':'null'})
 return checks

def verify(api,matrix=False,refresh=False):
 report={'version':api.get('/services/server/info')['entry'][0]['content']['version'],'checks':verify_calculations(api)}
 if refresh:
  for q in (availability_search(),dimension_search()):api.search(q)
 active=api.search('`tl_active`');assert active and active[0]['snapshot_id']!='__none__','No active snapshot'
 report['active_activities']=api.search('`tl_activities` | stats count AS count')[0]['count']
 views=[v for v in api.get('/servicesNS/nobody/training_lens/data/ui/views')['entry'] if v['acl']['app']=='training_lens' and v['name']!='metric_compat']
 assert len(views)==10,len(views)
 count=0
 activity=api.search('`tl_activities` | head 1 | fields activity_id')[0]['activity_id']
 for view in views:
  doc=json.loads(ET.fromstring(view['content']['eai:data']).findtext('definition'));tokens=defaults(doc);tokens.update({'activity_id':activity,'time.earliest':'0','time.latest':'now','cadence_units':'Strides/min'})
  for key,ds in doc['dataSources'].items():
   if not ds['options'].get('enableSmartSources'):continue
   try:rows=api.search(resolve_source(doc,key,tokens))
   except Exception as e:raise RuntimeError(view['name']+'/'+key+': '+str(e)) from e
   assert rows,key
   for field,value in rows[0].items():tokens[ds['name']+':result.'+field]=value
  for key,ds in doc['dataSources'].items():
   start=time.monotonic()
   try:rows=api.search(resolve_source(doc,key,tokens))
   except Exception as e:
    detail=e.read().decode() if hasattr(e,'read') else str(e)
    raise RuntimeError(view['name']+'/'+key+': '+detail) from e
   report['checks'].append({'view':view['name'],'source':key,'rows':len(rows),'seconds':round(time.monotonic()-start,3)})
  count+=len(doc['visualizations'])
  if matrix:
   for key,ds in doc['dataSources'].items():
    if not key.endswith('_metadata'):continue
    token=key[:-9];options=api.search(resolve_source(doc,token+'_options',tokens))
    for row in options:
     if row['metric_id']=='__auto__':continue
     for unit in ('Metric','Imperial'):
      t=dict(tokens,**{token:row['metric_id'],'units':unit})
      meta=api.search(resolve_source(doc,key,t))[0]
      for field,value in meta.items():t[key+':result.'+field]=value
      for grain in ('Week','Month','Year'):
       t['grain']=grain;rows=api.search(resolve_source(doc,token+'_aggregate',t))
       report['checks'].append({'view':view['name'],'metric':row['metric_id'],'unit':unit,'grain':grain,'rows':len(rows)})
  if matrix:
   modes=('activity_view','training_details','run_details','detail_mode','vitals_details','followers_table','sport_details','geo_details','readiness','health_details')
   for mode in modes:
    if mode not in doc['inputs']:continue
    source=next(k for k,d in doc['dataSources'].items() if k.startswith('table_') and '$'+mode+'|s$' in d['options']['query'])
    for item in doc['inputs'][mode]['options']['items']:
     rows=api.search(resolve_source(doc,source,dict(tokens,**{mode:item['value']})))
     if item['value'] in ('Recent activities','Weekly log','Comparable runs','Availability','Top interactions','Roster','Observed changes','Gear usage','Sport summaries','Annual coverage','Active snapshot','Completeness','Import manifests'):assert rows,(view['name'],item['value'])
     report['checks'].append({'view':view['name'],'mode':item['value'],'rows':len(rows)})
 assert count==28,count
 report['panels']=count;return report

def main():
 p=argparse.ArgumentParser();p.add_argument('--url',required=True);p.add_argument('--matrix',action='store_true');p.add_argument('--refresh',action='store_true');p.add_argument('--output',type=Path,required=True);p.add_argument('--insecure-local-test',action='store_true');a=p.parse_args()
 if a.insecure_local_test and urllib.parse.urlparse(a.url).hostname not in ('localhost','127.0.0.1'):p.error('localhost only')
 api=Enterprise(a.url,os.environ.get('SPLUNK_TEST_USER','admin'),os.environ['SPLUNK_TEST_PASSWORD'],a.insecure_local_test)
 try:r=verify(api,a.matrix,a.refresh);r['status']='passed'
 except Exception as e:r={'status':'failed','error':str(e)}
 a.output.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:v for k,v in r.items() if k!='checks'}));return int(r['status']!='passed')
if __name__=='__main__':raise SystemExit(main())
