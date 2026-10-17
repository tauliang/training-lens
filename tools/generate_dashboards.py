"""Generate native Dashboard Studio dashboards from reviewable panel searches."""
import json
from pathlib import Path
import xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[1]/'build/training_lens/default/data/ui'
READY='search index=training_lens_ops sourcetype=training_lens:ready earliest=0 latest=+10y | where $snapshot|s$="latest" OR snapshot_id=$snapshot|s$ | sort 0 - import_epoch | head 1 | stats first(snapshot_id) AS snapshot_id | eval snapshot_id=coalesce(snapshot_id,"__none__") | fields snapshot_id'
TIME=' | where timestamp>=if(isnum($time.earliest|s$),tonumber($time.earliest|s$),relative_time(now(),$time.earliest|s$)) AND timestamp<=if($time.latest|s$="now",now(),if(isnum($time.latest|s$),tonumber($time.latest|s$),relative_time(now(),$time.latest|s$)))'
FILTER=' | where ($sport|s$="All" OR sport=$sport|s$) AND ($gear|s$="All" OR gear=$gear|s$) AND ($quality_mode|s$!="Flagged only" OR flagged=1)'
def base(kind='activity',time=True,filters=True):
    query='index=training_lens sourcetype=training_lens:'+kind+' earliest=0 latest=+10y [ '+READY+' ] | dedup event_id'
    if time:query+=TIME
    if filters:query+=FILTER
    return query

def revisions():
    return 'search '+base(time=False,filters=False)+' | where ($sport|s$="All" OR sport=$sport|s$) AND ($gear|s$="All" OR gear=$gear|s$) AND stream_revision_id!="" | fields stream_revision_id'

def telemetry(kind,index='training_lens',detail=False):
    membership=revisions()
    return 'index='+index+' sourcetype=training_lens:'+kind+' earliest=0 latest=+10y [ '+membership+' | appendpipe [ stats count | where count=0 | eval stream_revision_id="__none__" ] | fields stream_revision_id ] | dedup event_id'+(' | where activity_id=$activity_id|s$ AND match($activity_id|s$,"^[0-9]{1,24}$")' if detail else TIME)

VALID=' | where $quality_mode|s$!="Validated" OR (distance_valid=1 AND duration_valid=1)'
DIST=' | eval display_distance=distance_m/if($units|s$="Imperial",1609.344,1000)'
ACT=base()
RECENT=ACT+DIST+' | sort 0 - timestamp | head 100 | table activity_id local_date activity_name sport display_distance moving_time_s average_hr relative_effort stream_status quality_flags'
PANELS={
'overview':('Training Lens','Recorded volume, consistency and activity history. Reported mode preserves source anomalies; Validated excludes affected distance/duration comparisons.',[
 ('Activities','single',ACT+' | stats count AS Activities'),
 ('Moving hours','single',ACT+' | where $quality_mode|s$!="Validated" OR duration_valid=1 | stats sum(moving_time_s) AS seconds | eval Hours=round(seconds/3600,2) | fields Hours'),
 ('Distance (selected units)','single',ACT+' | where $quality_mode|s$!="Validated" OR distance_valid=1'+DIST+' | stats sum(display_distance) AS Distance | eval Distance=round(Distance,2)'),
 ('Flagged activities','single',ACT+' | stats count(eval(flagged=1)) AS Flagged'),
 ('Weekly moving hours by sport','column',ACT+' | where $quality_mode|s$!="Validated" OR duration_valid=1 | chart sum(moving_time_s) OVER local_week_start BY sport | foreach * [ eval <<FIELD>>=if(isnum(\'<<FIELD>>\'),round(\'<<FIELD>>\'/3600,2),\'<<FIELD>>\') ]'),
 ('Sport mix by moving hours','bar',ACT+' | stats sum(moving_time_s) AS seconds BY sport | eval hours=round(seconds/3600,2) | fields sport hours'),
 ('Same elapsed part of each year','column',base(time=False)+ ' | where tonumber(strftime(timestamp,"%j"))<=tonumber(strftime(now(),"%j")) | stats count AS activities BY local_year | sort local_year'),
 ('Coverage','table',ACT+' | stats count AS activities count(average_hr) AS with_hr count(relative_effort) AS with_effort count(eval(stream_status="decoded")) AS decoded_streams count(eval(stream_status="summary_only")) AS summary_only'),
 ('Recent activities — click to inspect','table',RECENT),
]),
'training':('Training','Weekly activity, imported Relative Effort and confirmed custom heart-rate zones. Missing effort is unknown; no proprietary fitness or readiness score is inferred.',[
 ('Weekly activity log','table',ACT+' | stats count AS activities dc(local_date) AS active_days sum(moving_time_s) AS seconds sum(relative_effort) AS effort count(relative_effort) AS known_effort BY local_week_start | eval hours=round(seconds/3600,2), missing_effort=activities-known_effort | sort local_week_start'),
 ('Imported weekly effort and preceding four recorded weeks','line',ACT+' | stats sum(relative_effort) AS effort count AS activities count(relative_effort) AS known BY local_week_start | sort local_week_start | streamstats current=f window=4 avg(effort) AS preceding_recorded_weeks | eval effort=if(known=0,null(),effort) | fields local_week_start effort preceding_recorded_weeks'),
 ('HR-zone minutes — configure boundaries in config.json','column',telemetry('zone')+' | eval minutes=seconds/60 | chart sum(minutes) OVER local_week_start BY zone'),
 ('Observed versus unobserved HR time','table',telemetry('zone')+' | dedup activity_id | stats sum(observed_s) AS observed_seconds sum(unobserved_s) AS unobserved_seconds sum(paused_s) AS paused_seconds'),
 ('Configured goals','table',base('goal',time=False,filters=False)+' | table sport metric target period'),
 ('Effort coverage','table',ACT+' | stats count AS activities count(relative_effort) AS known_effort BY sport | eval coverage_pct=round(100*known_effort/activities,1)'),
]),
'run_performance':('Run Performance','Compare like runs by distance and terrain. Pace is distance-weighted. Best efforts are derived from continuous time-distance streams and include elapsed pause time.',[
 ('Running distance (selected units)','single',ACT+' | where sport="Run"'+VALID+DIST+' | stats sum(display_distance) AS Distance'),
 ('Distance-weighted pace (minutes per selected distance unit)','single',ACT+' | where sport="Run" AND pace_valid=1 | stats sum(moving_time_s) AS seconds sum(distance_m) AS meters | eval Pace=round(seconds*if($units|s$="Imperial",1609.344,1000)/(60*meters),2) | fields Pace'),
 ('Weekly running distance','column',ACT+' | where sport="Run"'+VALID+DIST+' | stats sum(display_distance) AS distance BY local_week_start | sort local_week_start'),
 ('Weekly distance-weighted pace','line',ACT+' | where sport="Run" AND pace_valid=1 | stats sum(distance_m) AS meters sum(moving_time_s) AS seconds BY local_week_start | eval pace=seconds*if($units|s$="Imperial",1609.344,1000)/(60*meters) | fields local_week_start pace | sort local_week_start'),
 ('App-derived best efforts','table',telemetry('best_effort')+' | stats min(duration_s) AS elapsed_seconds BY target_m | sort target_m'),
 ('Comparable runs','table',ACT+' | where sport="Run" AND pace_valid=1 | eval distance_km=round(distance_m/1000,2), pace_min_km=round(pace_min_km,2) | table activity_id local_date distance_km pace_min_km average_hr elevation_gain_m grade_adjusted_pace'),
]),
'activity_detail':('Activity Detail','Select an activity from Overview or enter its numeric Strava ID. Missing-stream activities retain summaries. Zone charts require configured boundaries; no power curve is inferred from average watts.',[
 ('Activity summary','table',base(time=False,filters=False)+' | where activity_id=$activity_id|s$ AND match($activity_id|s$,"^[0-9]{1,24}$") | table activity_id local_date activity_name sport distance_m moving_time_s elapsed_time_s average_hr relative_effort gear stream_status quality_flags'),
 ('Heart rate over elapsed seconds','line',telemetry('sample',detail=True)+' | bin elapsed_s span=5 | stats avg(hr) AS bpm BY elapsed_s | sort elapsed_s'),
 ('Pace over elapsed seconds (minutes/km)','line',telemetry('sample',detail=True)+' | bin elapsed_s span=5 | stats avg(pace_min_km) AS pace_min_km BY elapsed_s | sort elapsed_s'),
 ('Elevation over elapsed seconds (meters)','line',telemetry('sample',detail=True)+' | bin elapsed_s span=5 | stats avg(altitude_m) AS meters BY elapsed_s | sort elapsed_s'),
 ('Cadence over elapsed seconds (raw device units)','line',telemetry('sample',detail=True)+' | bin elapsed_s span=5 | stats avg(cadence) AS device_cadence BY elapsed_s | sort elapsed_s'),
 ('Device laps','table',telemetry('lap',detail=True)+' | sort timestamp | table elapsed_s distance_m elapsed_time_s moving_time_s hr cadence'),
 ('Derived kilometer splits','table',telemetry('split',detail=True)+' | table split distance_m duration_s'),
 ('HR zones and coverage','table',telemetry('zone',detail=True)+' | eval minutes=round(seconds/60,2) | table zone minutes observed_s unobserved_s paused_s'),
 ('Strength exercises','table',base('exercise',time=False,filters=False)+' | where activity_id=$activity_id|s$ | table exercise repetitions duration_s weight_raw'),
]),
'geography':('Geography','Privacy-masked cells count activity visits, not GPS samples. Endpoint buffers and exported privacy zones are applied before indexing. The table remains usable without a basemap.',[
 ('Personal activity visits','map',telemetry('geography',index='training_lens_shared')+' | stats sum(visits) AS visits BY latitude longitude | sort 0 - visits | head 1000'),
 ('Visited cells (one visit per activity and cell)','table',telemetry('geography',index='training_lens_shared')+' | stats sum(visits) AS visits dc(activity_id) AS activities BY latitude longitude | sort 0 - visits | head 1000'),
 ('Geography coverage by sport','bar',telemetry('geography',index='training_lens_shared')+' | stats dc(activity_id) AS mapped_activities BY sport'),
]),
'gear_sports':('Gear and Sports','Recorded gear usage can be incomplete. Names are preserved; correct aliases through overrides. No combined pace is calculated across sports.',[
 ('Recorded gear usage','table',ACT+VALID+DIST+' | stats count AS activities sum(display_distance) AS distance sum(moving_time_s) AS seconds BY gear sport | eval hours=round(seconds/3600,2) | fields gear sport activities distance hours'),
 ('Gear distance by month','column',ACT+VALID+DIST+' | chart sum(display_distance) OVER local_month BY gear'),
 ('Strength sessions','table',ACT+' | where sport="Weight Training" | table activity_id local_date moving_time_s average_hr sets reps'),
 ('Sport summaries','table',ACT+' | stats count AS activities sum(moving_time_s) AS seconds sum(elevation_gain_m) AS elevation_m BY sport | eval hours=round(seconds/3600,2) | fields sport activities hours elevation_m'),
]),
'data_health':('Data Health','An emitted import is not yet active. Reconciliation compares distinct record IDs against expected logical groups before publishing a ready marker.',[
 ('Active snapshot','table','index=training_lens_ops sourcetype=training_lens:ready earliest=0 latest=+10y | sort 0 - import_epoch | head 1 | table snapshot_id import_epoch groups matched'),
 ('Pending and reconciled groups','table','`tl_reconcile` | table snapshot_id groups matched expected_groups import_epoch'),
 ('Recent worker status','table','index=training_lens_ops sourcetype=training_lens:worker earliest=-7d | sort 0 - _time | head 20 | table _time status imports error_type'),
 ('Quality issues','table',base(time=False,filters=False)+' | where flagged=1 | table activity_id local_date sport quality_flags distance_m moving_time_s elapsed_time_s raw_relative_effort relative_effort'),
 ('Completeness by year and sport','table',base(time=False,filters=False)+' | stats count AS activities count(average_hr) AS hr count(relative_effort) AS effort count(eval(stream_status="decoded")) AS decoded BY local_year sport'),
 ('Import manifests','table','index=training_lens sourcetype=training_lens:snapshot earliest=0 latest=+10y | dedup event_id | sort 0 - import_epoch | table snapshot_id import_epoch expected_records expected_groups quarantined_streams timezone exact_gps'),
]),
'setup':('Setup','Enable the worker in local/inputs.conf, then place exports in $SPLUNK_HOME/var/lib/training_lens/inbox/. Settings are admin-owned files; see the app README for HR zones, goals, corrections, timezone, roles and privacy.',[
 ('Latest imports','table','index=training_lens sourcetype=training_lens:snapshot earliest=0 latest=+10y | dedup snapshot_id | sort 0 - import_epoch | table import_epoch snapshot_id timezone decode_enabled exact_gps quarantined_streams'),
 ('Setup checklist','table','| makeresults | eval worker="Enable script input in local/inputs.conf", inbox="$SPLUNK_HOME/var/lib/training_lens/inbox/", config="Admin-managed config.json in the runtime directory", zones="Configure effective-dated custom HR boundaries", privacy="Export zones and 200m endpoint buffers applied; exact GPS off by default", access="Assign athlete role; location role only for optional exact GPS" | table worker inbox config zones privacy access'),
])}

def dropdown(token,title,values,default):return {'type':'input.dropdown','title':title,'options':{'token':token,'defaultValue':default,'items':[{'label':x,'value':x} for x in values]}}

def generate():
    for name,(title,description,panels) in PANELS.items():
        doc={'title':title,'description':description,'visualizations':{},'dataSources':{},'inputs':{'time':{'type':'input.timerange','title':'Period','options':{'token':'time','defaultValue':'-1y,now'}},'sport':dropdown('sport','Sport',['All','Run','Ride','Hike','Alpine Ski','Weight Training','Workout','Walk','Swim','Nordic Ski','Backcountry Ski','Kayaking'],'All'),'gear':{'type':'input.text','title':'Gear (exact name or All)','options':{'token':'gear','defaultValue':'All'}},'quality':dropdown('quality_mode','Quality',['Validated','Reported','Flagged only'],'Validated'),'units':dropdown('units','Units',['Metric','Imperial'],'Metric'),'snapshot':{'type':'input.text','title':'Snapshot (latest or ID)','options':{'token':'snapshot','defaultValue':'latest'}}},'layout':{'type':'grid','options':{},'structure':[],'globalInputs':['time','sport','gear','quality','units','snapshot']}}
        if name=='activity_detail':doc['inputs']['activity']={'type':'input.text','title':'Activity ID','options':{'token':'activity_id','defaultValue':'none'}};doc['layout']['globalInputs'].append('activity')
        y=0
        for i,(label,kind,query) in enumerate(panels):
            ds='ds_'+str(i);viz='viz_'+str(i)
            query=query.replace('$SPLUNK_HOME','SPLUNK_HOME')
            doc['dataSources'][ds]={'type':'ds.search','name':label,'options':{'query':query,'queryParameters':{'earliest':'0','latest':'+10y'}}}
            visual={'type':'splunk.singlevalue' if kind=='single' else 'splunk.'+kind,'title':label,'dataSources':{'primary':ds},'options':{},'showProgressBar':True,'showLastUpdated':True}
            if kind=='map':visual['options']={'layers':[{'type':'bubble','latitude':'> primary | seriesByName("latitude")','longitude':'> primary | seriesByName("longitude")','bubbleSize':'> primary | seriesByName("visits")'}]}
            if label.startswith('Recent activities') or label=='Comparable runs':visual['eventHandlers']=[{'type':'drilldown.linkToDashboard','options':{'app':'training_lens','dashboard':'activity_detail','tokens':[{'token':'activity_id','value':'row.activity_id.value'}],'newTab':False}}]
            doc['visualizations'][viz]=visual
            # One clear panel per row in grid for portability; single-value pairs share the first rows.
            single=kind=='single';w=600 if single else 1200;h=150 if single else 300
            x=600 if single and i%2 else 0
            doc['layout']['structure'].append({'item':viz,'type':'block','position':{'x':x,'y':y,'w':w,'h':h}})
            if not single or i%2 or i==len(panels)-1 or panels[i+1][1]!='single':y+=h
        root=ET.Element('dashboard',version='2',theme='light');ET.SubElement(root,'label').text=title;ET.SubElement(root,'description').text=description;ET.SubElement(root,'definition').text=json.dumps(doc,indent=2)
        views=ROOT/'views';views.mkdir(parents=True,exist_ok=True);ET.ElementTree(root).write(views/(name+'.xml'),encoding='utf-8',xml_declaration=True)
    nav=ET.Element('nav',search_view='search',color='#ED6A27')
    for name,(title,_,_) in PANELS.items():ET.SubElement(nav,'view',name=name,default='true' if name=='overview' else 'false')
    (ROOT/'nav').mkdir(exist_ok=True);ET.ElementTree(nav).write(ROOT/'nav/default.xml',encoding='utf-8',xml_declaration=True)
if __name__=='__main__':generate()
