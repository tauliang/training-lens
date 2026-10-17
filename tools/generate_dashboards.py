"""Generate native Dashboard Studio dashboards from reviewable panel searches."""
import json
from pathlib import Path
import xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[1]/'build/training_lens/default/data/ui'
READY='search index=training_lens sourcetype=training_lens:ready earliest=0 latest=+10y | where $snapshot|s$="latest" OR snapshot_id=$snapshot|s$ | sort 0 - import_epoch | head 1 | stats count AS selection_count first(snapshot_id) AS snapshot_id | eval snapshot_id=coalesce(snapshot_id,"__none__") | fields snapshot_id'
def time_expression(token):
    value='$'+token+'|s$';numeric='match('+value+',"^[0-9]+([.][0-9]+)?$")'
    # Splunk validates/evaluates constant arguments even in an unselected if branch.
    return 'if('+numeric+',tonumber(if('+numeric+','+value+',"0")),relative_time(now(),if(('+numeric+' OR '+value+'="now"),"+0s",'+value+')))'
TIME=' | where timestamp>='+time_expression('time.earliest')+' AND timestamp<='+time_expression('time.latest')
FILTER=' | where ($sport|s$="All" OR sport=$sport|s$) AND ($gear|s$="All" OR gear=$gear|s$) AND ($quality_mode|s$!="Flagged only" OR flagged=1)'
def base(kind='activity',time=True,filters=True):
    query='index=training_lens sourcetype=training_lens:'+kind+' earliest=0 latest=+10y [ '+READY+' ] | dedup event_id'
    if time:query+=TIME
    if filters:query+=FILTER
    return query

def revisions(detail=False):
    selected=' | where activity_id=$activity_id|s$ AND match($activity_id|s$,"^[0-9]{1,24}$")' if detail else ''
    return 'search '+base(time=False,filters=False)+selected+' | where ($sport|s$="All" OR sport=$sport|s$) AND ($gear|s$="All" OR gear=$gear|s$) AND stream_revision_id!="" | fields stream_revision_id'

def telemetry(kind,index='training_lens',detail=False):
    membership=revisions(detail)
    return 'index='+index+' sourcetype=training_lens:'+kind+' earliest=0 latest=+10y [ '+membership+' | appendpipe [ stats count | where count=0 | eval stream_revision_id="__none__" ] | fields stream_revision_id ] | dedup event_id'+(' | where activity_id=$activity_id|s$ AND match($activity_id|s$,"^[0-9]{1,24}$")' if detail else TIME)

VALID=' | where $quality_mode|s$!="Validated" OR (distance_valid=1 AND duration_valid=1)'
DVALID=' | where $quality_mode|s$!="Validated" OR distance_valid=1'
TVALID=' | where $quality_mode|s$!="Validated" OR duration_valid=1'
GUARDS=' | eval distance_m=if($quality_mode|s$="Validated" AND distance_valid!=1,null(),distance_m), moving_time_s=if($quality_mode|s$="Validated" AND duration_valid!=1,null(),moving_time_s)'
DIST=' | eval display_distance=distance_m/if($units|s$="Imperial",1609.344,1000)'
ACT=base()
# Yearly panels deliberately use the complete selected snapshot. Other panels
# retain the Period filter. Comparable YTD is anchored to the import's date.
HISTORY=base(time=False)+' | where $history_scope|s$!="Comparable YTD" OR substr(local_date,6,5)<=comparison_month_day'
YEAR_COUNTS=HISTORY+' | chart count OVER local_year BY sport limit=0 useother=f usenull=f | makecontinuous local_year span=1 | fillnull value=0'
YEAR_SPEED=HISTORY+' | where pace_valid=1 AND distance_m>0 AND moving_time_s>0'
CADENCE=' | eval cadence_factor=case($cadence_units|s$="Strides/min",2,$cadence_units|s$="Steps/min",1,true(),null())'
YEAR_RUN=HISTORY+' | where sport="Run"'
YEAR_CADENCE=YEAR_RUN+' | where duration_valid=1 AND moving_time_s>0 AND average_cadence>0'+CADENCE+' | where isnotnull(cadence_factor) | eval cadence_seconds=average_cadence*cadence_factor*moving_time_s'
HR=ACT+' | eval valid_hr=if(average_hr>0 AND average_hr<=255,average_hr,null()), valid_max_hr=if(max_hr>0 AND max_hr<=255 AND (isnull(average_hr) OR max_hr>=average_hr),max_hr,null()), hr_seconds=if(isnotnull(valid_hr) AND duration_valid=1 AND moving_time_s>0,moving_time_s,null()), weighted_hr=valid_hr*hr_seconds'
SOCIAL=base('social',filters=False)
NETWORK=base('social',time=False,filters=False)+' | where social_type="network"'
RECEIVED=SOCIAL+' | where social_type="interaction" AND direction="received" AND is_current_follower=1'
OBSERVATIONS='index=training_lens sourcetype=training_lens:social social_type=network earliest=0 latest=+10y [ search index=training_lens sourcetype=training_lens:ready earliest=0 latest=+10y | dedup snapshot_id | appendpipe [ stats count | where count=0 | eval snapshot_id="__none__" ] | fields snapshot_id ] | dedup event_id | sort 0 import_epoch | dedup archive_hash | where followers_available=1'+TIME+' | sort 0 timestamp'
RECENT=ACT+DIST+' | sort 0 - timestamp | head 100 | table activity_id snapshot_id local_date activity_name sport display_distance moving_time_s average_hr relative_effort stream_status quality_flags'
PANELS={
'overview':('Training Lens','Recorded volume, consistency and activity history. Reported mode preserves source anomalies; Validated excludes affected distance/duration comparisons.',[
 ('Activities','single',ACT+' | stats count AS Activities'),
 ('Moving hours','single',ACT+' | where $quality_mode|s$!="Validated" OR duration_valid=1 | stats sum(moving_time_s) AS seconds | eval Hours=round(seconds/3600,2) | fields Hours'),
 ('Distance (selected units)','single',ACT+' | where $quality_mode|s$!="Validated" OR distance_valid=1'+DIST+' | stats sum(display_distance) AS Distance | eval Distance=round(Distance,2)'),
 ('Flagged activities','single',ACT+' | stats count(eval(flagged=1)) AS Flagged'),
 ('Weekly moving hours by sport','column',ACT+' | where $quality_mode|s$!="Validated" OR duration_valid=1 | chart sum(moving_time_s) OVER local_week_start BY sport | foreach * [ eval <<FIELD>>=if(isnum(\'<<FIELD>>\'),round(\'<<FIELD>>\'/3600,2),\'<<FIELD>>\') ]'),
 ('Sport mix by moving hours','bar',ACT+TVALID+' | stats sum(moving_time_s) AS seconds BY sport | eval hours=round(seconds/3600,2) | fields sport hours'),
 ('Annual comparison through import calendar date','column',base(time=False)+ ' | where substr(local_date,6,5)<=comparison_month_day | stats count AS activities BY local_year | sort local_year'),
 ('Annual activities by sport — all years','column',YEAR_COUNTS),
 ('Annual activity changes by sport — all years','table',YEAR_COUNTS+' | untable local_year sport activities | sort 0 sport local_year | streamstats current=f window=1 last(activities) AS previous_year_activities BY sport | eval change_activities=activities-previous_year_activities, yoy_pct=if(previous_year_activities>0,round(100*change_activities/previous_year_activities,1),null()) | table local_year sport activities previous_year_activities change_activities yoy_pct'),
 ('Coverage','table',ACT+' | stats count AS activities count(average_hr) AS with_hr count(relative_effort) AS with_effort count(eval(stream_status="decoded")) AS decoded_streams count(eval(stream_status="summary_only")) AS summary_only'),
 ('Recent activities — click to inspect','table',RECENT),
]),
'training':('Training','Weekly activity, imported Relative Effort and confirmed custom heart-rate zones. Missing effort is unknown; no proprietary fitness or readiness score is inferred.',[
 ('Weekly activity log','table',ACT+GUARDS+' | stats count AS activities dc(local_date) AS active_days sum(moving_time_s) AS seconds sum(relative_effort) AS effort count(relative_effort) AS known_effort BY local_week_start | eval hours=round(seconds/3600,2), missing_effort=activities-known_effort | sort local_week_start'),
 ('Imported weekly effort and preceding four recorded weeks','line',ACT+' | stats sum(relative_effort) AS effort count AS activities count(relative_effort) AS known BY local_week_start | eval effort=if(known=0,null(),effort) | sort local_week_start | streamstats current=f window=4 avg(effort) AS preceding_recorded_weeks | fields local_week_start effort preceding_recorded_weeks'),
 ('HR-zone minutes — configure boundaries in config.json','column',telemetry('zone')+' | eval minutes=seconds/60 | chart sum(minutes) OVER local_week_start BY zone'),
 ('Observed versus unobserved HR time','table',telemetry('zone')+' | dedup activity_id | stats sum(observed_s) AS observed_seconds sum(unobserved_s) AS unobserved_seconds sum(paused_s) AS paused_seconds'),
 ('Configured goals — progress at import','table',base('goal',time=False,filters=False)+' | table sport metric target period period_start as_of progress_value progress_pct'),
 ('Effort coverage','table',ACT+' | stats count AS activities count(relative_effort) AS known_effort BY sport | eval coverage_pct=round(100*known_effort/activities,1)'),
]),
'run_performance':('Run Performance','Compare like runs by distance and terrain. Pace is distance-weighted. Best efforts are derived from continuous time-distance streams and include elapsed pause time.',[
 ('Running distance (selected units)','single',ACT+' | where sport="Run"'+DVALID+DIST+' | stats sum(display_distance) AS Distance'),
 ('Distance-weighted pace (minutes per selected distance unit)','single',ACT+' | where sport="Run" AND pace_valid=1 | stats sum(moving_time_s) AS seconds sum(distance_m) AS meters | eval Pace=round(seconds*if($units|s$="Imperial",1609.344,1000)/(60*meters),2) | fields Pace'),
 ('Weekly running distance','column',ACT+' | where sport="Run"'+DVALID+DIST+' | stats sum(display_distance) AS distance BY local_week_start | sort local_week_start'),
 ('Weekly distance-weighted pace','line',ACT+' | where sport="Run" AND pace_valid=1 | stats sum(distance_m) AS meters sum(moving_time_s) AS seconds BY local_week_start | eval pace=seconds*if($units|s$="Imperial",1609.344,1000)/(60*meters) | fields local_week_start pace | sort local_week_start'),
 ('Annual running distance — all years','column',YEAR_RUN+DVALID+DIST+' | stats sum(display_distance) AS distance BY local_year | sort local_year'),
 ('Annual running pace (min/km or min/mile) — all years','line',YEAR_RUN+' | where pace_valid=1 AND distance_m>0 AND moving_time_s>0 | stats sum(distance_m) AS meters sum(moving_time_s) AS seconds BY local_year | eval pace=round(seconds*if($units|s$="Imperial",1609.344,1000)/(60*meters),3) | fields local_year pace | sort local_year | makecontinuous local_year span=1'),
 ('Annual running cadence (steps/min) — confirm source units','line',YEAR_CADENCE+' | stats sum(cadence_seconds) AS cadence_seconds sum(moving_time_s) AS seconds BY local_year | eval steps_per_minute=round(cadence_seconds/seconds,2) | fields local_year steps_per_minute | sort local_year | makecontinuous local_year span=1'),
 ('Annual running metric coverage — all years','table',YEAR_RUN+CADENCE+' | eval pace_ok=if(pace_valid=1 AND distance_m>0 AND moving_time_s>0,1,0), cadence_ok=if(duration_valid=1 AND moving_time_s>0 AND average_cadence>0 AND isnotnull(cadence_factor),1,0) | stats count AS activities sum(pace_ok) AS pace_activities sum(cadence_ok) AS cadence_activities BY local_year | eval cadence_coverage_pct=round(100*cadence_activities/activities,1), pace_coverage_pct=round(100*pace_activities/activities,1) | sort local_year'),
 ('App-derived best efforts','table',telemetry('best_effort')+' | stats min(duration_s) AS elapsed_seconds BY target_m | sort target_m'),
 ('Comparable runs','table',ACT+' | where sport="Run" AND pace_valid=1 | eval distance_km=round(distance_m/1000,2), pace_min_km=round(pace_min_km,2) | table activity_id snapshot_id local_date distance_km pace_min_km average_hr elevation_gain_m grade_adjusted_pace'),
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
 ('Recorded gear usage','table',ACT+GUARDS+DIST+' | stats count AS activities sum(display_distance) AS distance sum(moving_time_s) AS seconds BY gear sport | eval hours=round(seconds/3600,2) | fields gear sport activities distance hours'),
 ('Gear distance by month','column',ACT+DVALID+DIST+' | chart sum(display_distance) OVER local_month BY gear'),
 ('Annual skiing moving speed (km/h or MPH) — includes lifts if recorded','line',YEAR_SPEED+' | where sport IN ("Alpine Ski","Backcountry Ski","Nordic Ski","AlpineSki","BackcountrySki","NordicSki","Snowboard") | stats sum(distance_m) AS meters sum(moving_time_s) AS seconds BY local_year sport | eval speed=round(meters/seconds*if($units|s$="Imperial",2.2369362920544,3.6),2) | xyseries local_year sport speed | sort local_year | makecontinuous local_year span=1'),
 ('Annual moving speed by sport (km/h or MPH) — all years','line',YEAR_SPEED+' | stats sum(distance_m) AS meters sum(moving_time_s) AS seconds BY local_year sport | eval speed=round(meters/seconds*if($units|s$="Imperial",2.2369362920544,3.6),2) | xyseries local_year sport speed | sort local_year | makecontinuous local_year span=1'),
 ('Annual sport metric coverage — all years','table',HISTORY+' | eval speed_ok=if(pace_valid=1 AND distance_m>0 AND moving_time_s>0,1,0), valid_meters=if(speed_ok=1,distance_m,null()), valid_seconds=if(speed_ok=1,moving_time_s,null()) | stats count AS activities sum(speed_ok) AS speed_activities sum(valid_meters) AS meters sum(valid_seconds) AS seconds BY local_year sport | eval speed_coverage_pct=round(100*speed_activities/activities,1), speed=if(speed_activities>0,round(meters/seconds*if($units|s$="Imperial",2.2369362920544,3.6),2),null()), speed_unit=if($units|s$="Imperial","MPH","km/h") | table local_year sport activities speed_activities speed_coverage_pct speed speed_unit | sort 0 sport local_year'),
 ('Equipment thresholds — recorded lifetime mileage','table',base('gear_threshold',time=False,filters=False)+' | table gear target_m recorded_m remaining_m'),
 ('Strength sessions','table',ACT+' | where sport="Weight Training" | table activity_id local_date moving_time_s average_hr sets reps'),
 ('Sport summaries','table',ACT+GUARDS+' | stats count AS activities sum(moving_time_s) AS seconds sum(elevation_gain_m) AS elevation_m BY sport | eval hours=round(seconds/3600,2) | fields sport activities hours elevation_m'),
]),


'vitals':('Vitals','Exercise measurements from activities, not resting HR or clinical assessments. VO2 max is not imported by this release and is not estimated. HR trends use recorded activities with valid HR and duration. Weight values retain export units and activity dates; they are not dated weigh-ins.',[
 ('Activities with average HR','single',HR+' | stats count(valid_hr) AS activities_with_hr'),
 ('Time-weighted exercise HR (bpm)','single',HR+' | stats sum(weighted_hr) AS weighted sum(hr_seconds) AS seconds | eval bpm=if(seconds>0,round(weighted/seconds,1),null()) | fields bpm'),
 ('Highest recorded activity HR (bpm)','single',HR+' | stats max(valid_max_hr) AS peak_bpm'),
 ('Activities with weight recorded','single',ACT+' | stats count(eval(athlete_weight>0)) AS activities_with_weight'),
 ('Vitals availability and coverage','table',HR+' | stats count AS activities count(valid_hr) AS average_hr_activities count(hr_seconds) AS weighted_hr_activities count(valid_max_hr) AS max_hr_activities count(eval(athlete_weight>0)) AS weight_activities | eval vo2_max="Not imported by this release; no estimate made", resting_hr="Exercise HR is not resting HR", hrv="No supported HRV measurements imported", weight_basis="Export units; activity dates, not weigh-in dates"'),
 ('Annual time-weighted exercise HR by sport (bpm)','line',HR+' | where isnotnull(hr_seconds) | stats sum(weighted_hr) AS weighted sum(hr_seconds) AS seconds BY local_year sport | eval bpm=round(weighted/seconds,1) | xyseries local_year sport bpm | sort local_year | makecontinuous local_year span=1'),
 ('Monthly time-weighted exercise HR by sport (bpm)','line',HR+' | where isnotnull(hr_seconds) | stats sum(weighted_hr) AS weighted sum(hr_seconds) AS seconds BY local_month sport | eval bpm=round(weighted/seconds,1) | xyseries local_month sport bpm | sort local_month'),
 ('Annual highest recorded activity HR (bpm)','line',HR+' | stats max(valid_max_hr) AS peak_bpm BY local_year | sort local_year | makecontinuous local_year span=1'),
 ('Annual heart-rate-zone hours — configured boundaries','column',telemetry('zone')+' | where isnotnull(local_year) | eval hours=seconds/3600 | chart sum(hours) OVER local_year BY zone'),
 ('Recorded athlete weight by activity year — original export units','line',ACT+' | where athlete_weight>0 | stats median(athlete_weight) AS median_recorded_weight BY local_year | sort local_year | makecontinuous local_year span=1'),
 ('Annual HR and weight coverage by sport','table',HR+' | stats count AS activities count(valid_hr) AS average_hr_activities count(hr_seconds) AS weighted_hr_activities count(valid_max_hr) AS max_hr_activities count(eval(athlete_weight>0)) AS weight_activities BY local_year sport | sort 0 local_year sport'),
]),
'social':('Social','Follower counts are snapshots observed at import, with no historical follow dates. Native comments/kudos are contributions given. Received interactions and follower rankings require supplemental records; an empty ranking is not zero engagement.',[
 ('Accepted followers','single',NETWORK+' | fields followers'),
 ('Following','single',NETWORK+' | fields following'),
 ('Pending follower requests','single',NETWORK+' | fields pending_followers'),
 ('Mutual connections','single',NETWORK+' | fields mutual'),
 ('Social data availability','table',NETWORK+' | eval follower_history="Growth requires two or more distinct exports; dates are import observations", received_interactions=if(received_available=1,"Supplemental file supplied; coverage depends on its contents","Unavailable in native export; provide social_interactions.csv"), follower_roster=if(followers_available=1,"Available","Not supplied; follower metrics unknown"), following_roster=if(following_available=1,"Available","Not supplied; following metrics unknown"), given_comments=if(comments_available=1,"Available","Not supplied"), given_kudos=if(kudos_available=1,"Available","Not supplied") | table follower_roster following_roster follower_history received_interactions given_comments given_kudos'),
 ('Follower growth — observed at import dates','line',OBSERVATIONS+' | eval _time=timestamp | table _time followers following'),
 ('Follower count changes between observed exports','table',OBSERVATIONS+' | streamstats current=f window=1 last(followers) AS previous_followers | eval net_change=followers-previous_followers, observed_at=strftime(timestamp,"%Y-%m-%d %H:%M:%S") | table observed_at followers previous_followers net_change'),
 ('Comments and kudos given — monthly','column',SOCIAL+' | where social_type="interaction" AND direction="given" | timechart span=1mon fixedrange=f cont=f count BY interaction_type limit=0 useother=f'),
 ('Interactions received from current followers — monthly','column',RECEIVED+' | timechart span=1mon fixedrange=f cont=f count BY interaction_type limit=0 useother=f'),
 ('Top current followers — received comments and kudos','table',RECEIVED+' | stats count(eval(interaction_type="Comment")) AS comments count(eval(interaction_type="Kudos")) AS kudos BY actor_id | eval interactions=comments+kudos | sort 0 - interactions - comments actor_id | head 20 | rename actor_id AS follower_athlete_id | table follower_athlete_id comments kudos interactions'),
 ('Network roster — selected snapshot','table',base('social',time=False,filters=False)+' | where social_type="relationship" | table actor_id relationship follow_status'),
]),
'data_health':('Data Health','An emitted import is not yet active. Reconciliation compares distinct record IDs against expected logical groups before publishing a ready marker.',[
 ('Active snapshot','table','index=training_lens sourcetype=training_lens:ready earliest=0 latest=+10y | sort 0 - import_epoch | head 1 | table snapshot_id import_epoch groups matched'),
 ('Pending and reconciled groups','table','`tl_reconciliation` | table snapshot_id groups matched expected_groups import_epoch'),
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
        if name=='vitals':
            doc['inputs'].pop('units');doc['layout']['globalInputs'].remove('units')
            doc['inputs']['time']['options']['defaultValue']='0,now'
        if name=='social':
            doc['inputs']={key:doc['inputs'][key] for key in ('time','snapshot')}
            doc['layout']['globalInputs']=['time','snapshot']
        if name=='activity_detail':doc['inputs']['activity']={'type':'input.text','title':'Activity ID','options':{'token':'activity_id','defaultValue':'none'}};doc['layout']['globalInputs'].append('activity')
        if name in ('overview','run_performance','gear_sports'):
            doc['inputs']['history']=dropdown('history_scope','Annual panels (ignore Period)',['Full years','Comparable YTD'],'Full years')
            doc['layout']['globalInputs'].append('history')
            doc['description']+=' Annual panels use full snapshot history; Full years includes a partial latest year. Comparable YTD ends each year at the import calendar date.'
        if name=='run_performance':
            doc['inputs']['cadence']=dropdown('cadence_units','CSV cadence convention',['Unconfirmed','Strides/min','Steps/min'],'Unconfirmed')
            doc['layout']['globalInputs'].append('cadence')
            doc['description']+=' Pace is minutes/km or minutes/mile. Confirm CSV cadence units to show steps/min: strides are doubled; existing steps are unchanged. Cadence is weighted by recorded moving duration.'
        if name=='gear_sports':doc['description']+=' Annual speed is distance divided by moving time, in km/h or MPH. Skiing summaries do not isolate descents from lifts or traverses.'
        y=0
        for i,(label,kind,query) in enumerate(panels):
            ds='ds_'+str(i);viz='viz_'+str(i)
            query=query.replace('$SPLUNK_HOME','SPLUNK_HOME')
            doc['dataSources'][ds]={'type':'ds.search','name':label,'options':{'query':query,'queryParameters':{'earliest':'0','latest':'+10y'}}}
            visual={'type':'splunk.singlevalue' if kind=='single' else 'splunk.'+kind,'title':label,'dataSources':{'primary':ds},'options':{},'showProgressBar':True,'showLastUpdated':True}
            if name in ('run_performance','gear_sports','vitals') and kind=='line':visual['options']={'nullValueDisplay':'gaps'}
            if kind=='map':visual['options']={'layers':[{'type':'bubble','latitude':'> primary | seriesByName("latitude")','longitude':'> primary | seriesByName("longitude")','bubbleSize':'> primary | seriesByName("visits")'}]}
            if label.startswith('Recent activities') or label=='Comparable runs':visual['eventHandlers']=[{'type':'drilldown.linkToDashboard','options':{'app':'training_lens','dashboard':'activity_detail','tokens':[{'token':'activity_id','value':'row.activity_id.value'},{'token':'snapshot','value':'row.snapshot_id.value'}],'newTab':False}}]
            doc['visualizations'][viz]=visual
            # One clear panel per row in grid for portability; single-value pairs share the first rows.
            single=kind=='single';w=600 if single else 1200;h=150 if single else 300
            x=600 if single and i%2 else 0
            doc['layout']['structure'].append({'item':viz,'type':'block','position':{'x':x,'y':y,'w':w,'h':h}})
            if not single or i%2 or i==len(panels)-1 or panels[i+1][1]!='single':y+=h
        root=ET.Element('dashboard',version='2',theme='light');ET.SubElement(root,'label').text=title;ET.SubElement(root,'description').text=doc['description'];ET.SubElement(root,'definition').text=json.dumps(doc,indent=2)
        views=ROOT/'views';views.mkdir(parents=True,exist_ok=True);ET.ElementTree(root).write(views/(name+'.xml'),encoding='utf-8',xml_declaration=True)
    nav=ET.Element('nav',search_view='search',color='#ED6A27')
    for name,(title,_,_) in PANELS.items():ET.SubElement(nav,'view',name=name,default='true' if name=='overview' else 'false')
    (ROOT/'nav').mkdir(exist_ok=True);ET.ElementTree(nav).write(ROOT/'nav/default.xml',encoding='utf-8',xml_declaration=True)
if __name__=='__main__':generate()
