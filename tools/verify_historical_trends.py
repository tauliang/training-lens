#!/usr/bin/env python3
"""Execute yearly dashboard searches against hand-checked synthetic rows in Splunk.

Uses makeresults, so no fixture data is indexed. See verify_enterprise.py for
connection and credential options. Run after generating the dashboard XML.
"""
import argparse,json,os,sys
from pathlib import Path
import xml.etree.ElementTree as ET
from verify_enterprise import Enterprise,substitute_tokens
ROOT=Path(__file__).resolve().parents[1]
PANELS={
 'counts':('overview','Annual activities by sport — all years'),
 'changes':('overview','Annual activity changes by sport — all years'),
 'distance':('run_performance','Annual running distance — all years'),
 'pace':('run_performance','Annual running pace (min/km or min/mile) — all years'),
 'cadence':('run_performance','Annual running cadence (steps/min) — confirm source units'),
 'run_coverage':('run_performance','Annual running metric coverage — all years'),
 'ski':('gear_sports','Annual skiing moving speed (km/h or MPH) — includes lifts if recorded'),
 'speed':('gear_sports','Annual moving speed by sport (km/h or MPH) — all years'),
 'sport_coverage':('gear_sports','Annual sport metric coverage — all years'),
}
def queries():
    result={}
    for key,(view,label) in PANELS.items():
        from generate_dashboards import PANELS as original_panels
        doc={'dataSources':{str(i):{'name':name,'options':{'query':query}} for i,(name,kind,query) in enumerate(original_panels[view][2])}}
        matches=[ds['options']['query'] for ds in doc['dataSources'].values() if ds['name']==label]
        assert len(matches)==1,'Missing yearly panel: '+label
        result[key]=matches[0]
    return result

def verify(api):
    # Unequal durations catch arithmetic means; 2023 has no activities; absent
    # cadence and invalid distance/duration catch zero-filling and denominator bugs.
    source=[
      (2022,'Run',1000,300,80,1,'01-01'),
      (2022,'Run',9000,2700,90,1,'01-02'),
      (2024,'Run',5000,1500,None,1,'01-01'),
      (2024,'Run',5000,1800,100,1,'12-01'),
      (2024,'Run',999999,1,200,0,'01-01'),
      (2022,'Alpine Ski',16093.44,3600,None,1,'01-01'),
      (2022,'Alpine Ski',144840.96,10800,None,1,'01-02'),
      (2024,'Alpine Ski',16093.44,3600,None,1,'01-01'),
      (2024,'Ride',20000,3600,None,1,'01-01'),
    ]
    rows=[]
    for i,(year,sport,meters,seconds,cadence,valid,day) in enumerate(source):
        rows.append(dict(local_year=year,local_date=str(year)+'-'+day,sport=sport,distance_m=meters,moving_time_s=seconds,average_cadence=cadence,pace_valid=valid,distance_valid=valid,duration_valid=valid,gear='All',flagged=0,comparison_month_day='06-30',average_hr=None, timestamp=1700000000+i))
    fixture='| makeresults | eval payload='+json.dumps(json.dumps(rows))+' | spath input=payload path={} output=row | mvexpand row | spath input=row | fields - payload row'
    panels=queries();checks=[]
    def run(key,**overrides):
        tokens=dict(snapshot='latest',sport='All',gear='All',quality_mode='Validated',units='Imperial',history_scope='Full years',cadence_units='Strides/min',**{'time.earliest':'0','time.latest':'+10y'})
        tokens.update(overrides)
        query=fixture+panels[key].split('| dedup event_id',1)[1]
        result=api.search(substitute_tokens(query,tokens));checks.append(dict(panel=key,rows=len(result),tokens=overrides));return result
    def row(results,year,sport=None):
        return next(r for r in results if int(r['local_year'])==year and (sport is None or r['sport']==sport))
    counts=run('counts');assert float(row(counts,2022)['Run'])==2;assert float(row(counts,2023)['Run'])==0;assert float(row(counts,2024)['Run'])==3
    # Returning after a completely inactive year has no finite percent increase.
    changes=run('changes');assert float(row(changes,2023,'Run')['change_activities'])==-2;assert row(changes,2024,'Run').get('yoy_pct') in (None,'')
    pace=run('pace');assert abs(float(row(pace,2022)['pace'])-8.04672)<.001
    assert row(pace,2023).get('pace') in (None,'')
    assert abs(float(row(run('pace',units='Metric'),2022)['pace'])-5)<.001
    assert float(row(run('cadence'),2022)['steps_per_minute'])==178
    assert float(row(run('cadence',cadence_units='Steps/min'),2022)['steps_per_minute'])==89
    assert run('cadence',cadence_units='Unconfirmed')==[]
    coverage=row(run('run_coverage'),2024);assert float(coverage['activities'])==3;assert float(coverage['cadence_activities'])==1;assert float(coverage['pace_activities'])==2
    assert abs(float(row(run('ski'),2022)['Alpine Ski'])-25)<.001
    assert abs(float(row(run('ski',units='Metric'),2022)['Alpine Ski'])-40.23)<.01
    assert set(run('speed',sport='Ride')[0])=={'local_year','Ride'}
    assert len(run('distance'))==2
    assert run('sport_coverage')
    ytd=row(run('counts',history_scope='Comparable YTD'),2024);assert float(ytd['Run'])==2
    assert float(row(run('counts',sport='Run'),2022)['Run'])==2
    assert run('counts',gear='Missing gear')==[]
    assert run('counts',sport='Run" | delete')==[]
    return {'status':'passed','checks':checks}

def main():
    p=argparse.ArgumentParser();p.add_argument('--definitions-only',action='store_true');p.add_argument('--url',default='https://127.0.0.1:38089');p.add_argument('--output',type=Path);p.add_argument('--insecure-local-test',action='store_true');args=p.parse_args()
    if args.definitions_only:queries();print('All nine yearly panels are defined.');return
    from urllib.parse import urlparse
    if args.insecure_local_test and urlparse(args.url).hostname not in ('127.0.0.1','localhost','::1'):p.error('insecure TLS only allowed on localhost')
    result=verify(Enterprise(args.url,os.environ.get('SPLUNK_TEST_USER','admin'),os.environ['SPLUNK_TEST_PASSWORD'],args.insecure_local_test))
    if args.output:args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
if __name__=='__main__':main()
