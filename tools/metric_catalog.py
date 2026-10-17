"""Validated metadata. Executable SPL is compiled from fixed Python mappings only."""
import csv,math
from pathlib import Path
CATALOG=Path(__file__).resolve().parents[1]/'build/training_lens/lookups/training_lens_metric_catalog.csv'
SOURCES={'activity','sample','zone','social'}
FIELDS={'activity_id','moving_time_s','distance_m','elevation_gain_m','relative_effort','local_date','average_cadence','average_hr','max_hr','athlete_weight','flagged','stream_status','seconds','hr','pace_min_km','speed_mps','altitude_m','cadence','watts','power','followers','following','pending_followers','mutual','interaction_type'}
AGGREGATIONS={'count','sum','distinct','pace','speed','weighted','max','median','coverage','mean'}
def load_catalog(path=CATALOG):
 with Path(path).open() as f:rows=list(csv.DictReader(f))
 validate_catalog(rows);return rows

def validate_catalog(rows):
 seen=set()
 for r in rows:
  if r['metric_id'] in seen or not r['metric_id'].replace('_','').isalnum():raise ValueError('invalid_metric_id')
  seen.add(r['metric_id'])
  if r['source_kind'] not in SOURCES or r['source_field'] not in FIELDS or r['aggregation_key'] not in AGGREGATIONS:raise ValueError('unsupported_mapping')
  for key in ('metric_factor','imperial_factor'):
   if not math.isfinite(float(r[key])) or float(r[key])<=0:raise ValueError('invalid_conversion')
  if r['source_field']=='athlete_weight' and (r['metric_unit']!='export units' or r['imperial_unit']!='export units' or float(r['metric_factor'])!=1 or float(r['imperial_factor'])!=1):raise ValueError('unknown_weight_unit')
  if r['metric_id']=='cadence' and r['prerequisite']!='confirmed_cadence':raise ValueError('cadence_requires_confirmation')

def aggregate(key,values,weights):
 denominator=sum(weights)
 if key=='weighted':return sum(v*w for v,w in zip(values,weights))/denominator if denominator else None
 if key=='ratio':return sum(values)/denominator if denominator else None
 raise ValueError('unsupported_aggregation')

# Eligibility is independent of display units and is shared by caches and searches.
def eligibility(r):
 i=r['metric_id'];f=r['source_field']
 if i in ('speed','pace'):return 'pace_valid=1 AND distance_m>0 AND moving_time_s>0'
 if i in ('avg_hr','hr_comparison'):return 'average_hr>0 AND average_hr<=255 AND duration_valid=1 AND moving_time_s>0'
 if i=='peak_hr':return 'max_hr>0 AND max_hr<=255 AND (isnull(average_hr) OR max_hr>=average_hr)'
 if i=='cadence':return 'sport="Run" AND average_cadence>0 AND duration_valid=1 AND moving_time_s>0'
 if i=='hours':return 'isnotnull(moving_time_s) AND ($quality_mode|s$!="Validated" OR duration_valid=1)'
 if i=='distance':return 'isnotnull(distance_m) AND ($quality_mode|s$!="Validated" OR distance_valid=1)'
 if i=='stream_coverage':return 'stream_status="decoded"'
 if i in ('weight','hr_coverage'):return f+'>0'
 if i=='effort_coverage':return 'isnotnull(relative_effort)'
 if i in ('activities','active_days','flagged'):return 'true()'
 if r['group_id']=='network':return ('followers_available=1' if i in ('followers','pending') else 'following_available=1' if i=='following' else 'followers_available=1 AND following_available=1')+' AND social_type="network"'
 if r['group_id']=='engagement':return 'social_type="interaction" AND direction="'+i+'"'+(' AND is_current_follower=1' if i=='received' else '')
 return 'isnotnull('+f+')'

def expansion_guard(field):
 return ' | eval _expand_n=mvcount('+field+') | eventstats sum(_expand_n) AS _expected_rows | mvexpand '+field+' | eventstats count AS _actual_rows | where _actual_rows=_expected_rows | fields - _expand_n _expected_rows _actual_rows'

def availability_search():
 rows=load_catalog();stream=[r for r in rows if r['source_kind'] in ('sample','zone')];direct=[r for r in rows if r['source_kind'] in ('activity','social')]
 q='search index=strava sourcetype IN (training_lens:activity,training_lens:social,training_lens:sample,training_lens:zone,training_lens:ready) earliest=0 latest=+10y | dedup event_id keepempty=true'
 q+=' | eval record_kind=replace(sourcetype,"training_lens:",""),reference=if(isnotnull(stream_revision_id) AND stream_revision_id!="",stream_revision_id,coalesce(event_id,snapshot_id."_ready"))'
 props=['"snapshot_id",snapshot_id','"sport",coalesce(sport,"All")','"gear",coalesce(gear,"All")','"record_kind",record_kind']
 for r in direct:
  condition='record_kind="'+r['source_kind']+'" AND ('+eligibility(r).replace('$quality_mode|s$','"Reported"')+')'
  props.append('"v_'+r['metric_id']+'",if('+condition+',1,0)')
 q+=' | eval membership=if(record_kind IN ("activity","social","ready"),json_object('+','.join(props)+'),null())'
 counters=[]
 for r in stream:
  i=r['metric_id'];condition='record_kind="'+r['source_kind']+'" AND ('+eligibility(r)+')'
  q+=' | eval v_'+i+'=if('+condition+',1,0)';counters.append('sum(v_'+i+') AS v_'+i)
 q+=' | stats values(membership) AS membership count(eval(record_kind="sample")) AS sample_total count(eval(record_kind="zone")) AS zone_total '+' '.join(counters)+' BY reference | where mvcount(membership)>0'
 q+=expansion_guard('membership')+' | spath input=membership | eval is_ready=if(record_kind="ready",1,0) | eventstats max(is_ready) AS has_ready BY snapshot_id | where has_ready=1 AND is_ready=0'
 q+=' | eval metric_id=split("'+','.join(r['metric_id'] for r in rows)+'",",")'+expansion_guard('metric_id')
 valid=[];totals=[]
 for r in rows:
  i=r['metric_id'];source=r['source_kind'];valid.extend(['metric_id="'+i+'"','v_'+i]);totals.extend(['metric_id="'+i+'"',source+'_total' if source in ('sample','zone') else 'if(record_kind="'+source+'",1,0)'])
 q+=' | eval valid_count=case('+','.join(valid)+'),total_count=case('+','.join(totals)+') | where total_count>0 | eval sport=if(sport="All","All",mvappend(sport,"All")),gear=if(gear="All","All",mvappend(gear,"All"))'
 q+=expansion_guard('sport')+expansion_guard('gear')
 q+=' | where [ search `tl_reconciliation` | where is_ready=1 AND (groups!=expected_groups OR matched!=expected_groups) | stats count AS bad | eval guard=if(bad=0,\"true()\",\"false()\") | return $guard ]'
 return q+' | stats sum(valid_count) AS valid_count sum(total_count) AS total_count BY snapshot_id metric_id sport gear | eval source_available=1,status="ready",refreshed_at=now() | outputlookup override_if_empty=false training_lens_metric_availability'

def dimension_search():
 q='search index=strava sourcetype IN (training_lens:activity,training_lens:best_effort,training_lens:goal,training_lens:ready) earliest=0 latest=+10y | dedup event_id keepempty=true | eval record_kind=replace(sourcetype,"training_lens:",""),reference=if(isnotnull(stream_revision_id) AND stream_revision_id!="",stream_revision_id,coalesce(event_id,snapshot_id."_ready"))'
 q+=' | eval membership=if(record_kind IN ("activity","goal","ready"),json_object("snapshot_id",snapshot_id,"sport",coalesce(sport,"All"),"gear",coalesce(gear,"All"),"record_kind",record_kind,"metric",metric,"period",period),null()) | stats values(membership) AS membership values(target_m) AS target_m BY reference | where mvcount(membership)>0'
 q+=expansion_guard('membership')+' | spath input=membership | eval is_ready=if(record_kind="ready",1,0) | eventstats max(is_ready) AS has_ready BY snapshot_id | where has_ready=1 AND is_ready=0'
 q+=' | eval dimension=if(record_kind="goal","goal",mvappend("sport","gear","effort_target"))'+expansion_guard('dimension')
 q+=' | eval value=case(dimension="sport",sport,dimension="gear",gear,dimension="effort_target",target_m,dimension="goal",sport." · ".metric." · ".period) | where isnotnull(value) AND value!=""'+expansion_guard('value')
 q+=' | where [ search `tl_reconciliation` | where is_ready=1 AND (groups!=expected_groups OR matched!=expected_groups) | stats count AS bad | eval guard=if(bad=0,"true()","false()") | return $guard ]'
 return q+' | dedup snapshot_id dimension value | eval label=if(dimension="effort_target",value." m",value),sort_order=if(dimension="effort_target",tonumber(value),1) | fields snapshot_id dimension value label sort_order | outputlookup override_if_empty=false training_lens_dimension_options'
