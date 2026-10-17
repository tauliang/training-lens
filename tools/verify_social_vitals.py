#!/usr/bin/env python3
"""Live SPL calculation fixtures for Social and Vitals; no indexed fixture data."""
import argparse,json,os
from pathlib import Path
import xml.etree.ElementTree as ET
from verify_enterprise import Enterprise,substitute_tokens
ROOT=Path(__file__).resolve().parents[1]

def verify(api):
    cases=[
        dict(sport='Run',local_year=2022,average_hr=100,max_hr=180,moving_time_s=100,duration_valid=1,athlete_weight=70),
        dict(sport='Run',local_year=2022,average_hr=160,max_hr=190,moving_time_s=300,duration_valid=1,athlete_weight=72),
        dict(sport='Run',local_year=2024,average_hr=500,max_hr=190,moving_time_s=100,duration_valid=1),
        dict(sport='Run',local_year=2024,average_hr=120,max_hr=130,moving_time_s=0,duration_valid=1),
        dict(sport='Ride',local_year=2024,average_hr=130,max_hr=180,moving_time_s=200,duration_valid=1),
    ]
    for r in cases:r.update(timestamp=1700000000,gear='All',flagged=0)
    interactions=[dict(social_type='interaction',direction='received',actor_id=actor,is_current_follower=current,interaction_type=kind,timestamp=1700000000) for actor,current,kind in [('11',1,'Comment'),('11',1,'Comment'),('11',1,'Kudos'),('12',1,'Comment'),('12',1,'Kudos'),('99',0,'Kudos')]]
    panels={}
    for view in ('vitals','social'):
        doc=json.loads(ET.parse(ROOT/'build/training_lens/default/data/ui/views'/(view+'.xml')).getroot().findtext('definition'))
        panels.update({ds['name']:ds['options']['query'] for ds in doc['dataSources'].values()})
    tokens={'snapshot':'latest','sport':'All','gear':'All','quality_mode':'Validated','time.earliest':'0','time.latest':'+10y'}
    checks=[]
    def run(name,rows):
        fixture='| makeresults | eval payload='+json.dumps(json.dumps(rows))+' | spath input=payload path={} output=row | mvexpand row | spath input=row | fields - payload row | eval _time=timestamp'
        query=fixture+panels[name].split('| dedup event_id',1)[1]
        result=api.search(substitute_tokens(query,tokens));checks.append({'panel':name,'rows':len(result)});return result
    assert float(run('Time-weighted exercise HR (bpm)',cases)[0]['bpm'])==140
    yearly=run('Annual time-weighted exercise HR by sport (bpm)',cases)
    first=next(r for r in yearly if r['local_year']=='2022');assert float(first['Run'])==145
    gap=next(r for r in yearly if r['local_year']=='2023');assert gap.get('Run') in (None,'')
    assert float(run('Highest recorded activity HR (bpm)',cases)[0]['peak_bpm'])==190
    peaks=run('Annual highest recorded activity HR (bpm)',cases);assert float(next(r for r in peaks if r['local_year']=='2024')['peak_bpm'])==180
    weights=run('Recorded athlete weight by activity year — original export units',cases);assert float(weights[0]['median_recorded_weight'])==71
    coverage=run('Vitals availability and coverage',cases)[0];assert coverage['average_hr_activities']=='4' and coverage['weighted_hr_activities']=='3';assert coverage['vo2_max'].startswith('Not imported')
    ranks=run('Top current followers — received comments and kudos',interactions);assert [(r['follower_athlete_id'],r['interactions']) for r in ranks]==[('11','3'),('12','2')]
    assert run('Top current followers — received comments and kudos',[])==[]
    availability=run('Social data availability',[dict(social_type='network',followers_available=1,following_available=1,received_available=0,comments_available=1,kudos_available=1)])[0]
    assert availability['received_interactions'].startswith('Unavailable')
    unavailable=run('Time-weighted exercise HR (bpm)',[cases[3]])
    assert not unavailable or unavailable[0].get('bpm') in (None,'')
    given=[dict(interactions[i],direction='given') for i in (0,2)]
    history=run('Comments and kudos given — monthly',given)
    assert len(history)==1 and str(history[0]['_time']).startswith('2023-11-'),history
    return {'status':'passed','checks':checks}

def main():
    p=argparse.ArgumentParser();p.add_argument('--url',default='https://localhost:8089');p.add_argument('--output',type=Path);p.add_argument('--insecure-local-test',action='store_true');args=p.parse_args()
    from urllib.parse import urlparse
    if args.insecure_local_test and urlparse(args.url).hostname not in ('localhost','127.0.0.1','::1'):p.error('insecure TLS only allowed on localhost')
    result=verify(Enterprise(args.url,os.environ.get('SPLUNK_TEST_USER','admin'),os.environ['SPLUNK_TEST_PASSWORD'],args.insecure_local_test))
    if args.output:args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
if __name__=='__main__':main()
