"""Native Studio components with bounded aggregated chart sources and safe IDs."""
import json
import xml.etree.ElementTree as ET
from metric_catalog import load_catalog,eligibility
CAT={r['metric_id']:r for r in load_catalog()}

def quoted(value):return json.dumps(value)
def dropdown(token,title,values,default):
 return {'type':'input.dropdown','title':title,'options':{'token':token,'defaultValue':default,'items':[{'label':v,'value':v} for v in values]}}
def lookup_input(token,title,source,value='metric_id'):
 return {'type':'input.dropdown','title':title,'dataSources':{'primary':source},'context':{'label':'> primary | seriesByName("label") | renameSeries("label")','value':'> primary | seriesByName("'+value+'") | renameSeries("value")'},'options':{'token':token,'defaultValue':'__auto__' if value=='metric_id' else 'All','items':'> frame(label, value) | objects()','selectFirstSearchResult':True}}
def options_query(ids):
 from generate_dashboards import READY
 for i in ids:
  if i not in CAT:raise ValueError('unknown_metric')
 return '| inputlookup training_lens_metric_availability | search [ '+READY+' ] | where sport=$sport|s$ AND gear=$gear|s$ AND valid_count>0 AND metric_id IN ('+','.join(map(quoted,ids))+') | lookup training_lens_metric_catalog metric_id OUTPUT label sort_order prerequisite | where coalesce(prerequisite,"")!="confirmed_cadence" OR $cadence_units|s$!="Unconfirmed" | stats first(label) AS label first(sort_order) AS sort_order max(refreshed_at) AS refreshed_at BY metric_id | eval label=if(now()-refreshed_at>900,label." · cache stale",label) | append [ | makeresults | eval metric_id="__auto__",label="Automatic / first available",sort_order=-1 ] | sort 0 sort_order metric_id'

def zone_source():
 from generate_dashboards import TIME
 q='index=strava sourcetype IN (training_lens:activity,training_lens:zone,training_lens:ready) earliest=0 latest=+10y | dedup event_id keepempty=true | eval candidate_epoch=if(sourcetype="training_lens:ready" AND ($snapshot|s$="latest" OR snapshot_id=$snapshot|s$),import_epoch,null()) | eventstats max(candidate_epoch) AS chosen_epoch'
 q+=' | eval membership=if(sourcetype="training_lens:activity" AND import_epoch=chosen_epoch AND ($sport|s$="All" OR sport=$sport|s$) AND ($gear|s$="All" OR gear=$gear|s$) AND ($quality_mode|s$!="Flagged only" OR flagged=1),json_object("local_date",local_date,"local_month",local_month,"local_week_start",local_week_start,"local_year",local_year,"comparison_month_day",comparison_month_day,"sport",sport,"gear",gear,"timestamp",timestamp),null()) | eventstats values(membership) AS membership BY stream_revision_id | where sourcetype="training_lens:zone" AND mvcount(membership)>0 | mvexpand membership | spath input=membership'
 return q+' | where ($grain|s$="Year" OR ('+TIME.split(' | where ',1)[1]+')) | where $grain|s$!="Year" OR $history_scope|s$!="Comparable YTD" OR substr(local_date,6,5)<=comparison_month_day'

def metric_query(group_id,ids,metric_token='metric',metadata=None):
 from generate_dashboards import base,telemetry,TIME,HISTORY,OBSERVATIONS
 for i in ids:
  if i not in CAT:raise ValueError('unknown_metric')
 token='$'+(metadata+':result.metric_id' if metadata else metric_token)+'|s$'
 if group_id=='sample':q=telemetry('sample',detail=True)
 elif group_id=='zone':q=zone_source()
 elif group_id=='network':q=OBSERVATIONS.replace(' | where followers_available=1','')
 elif group_id=='engagement':q=base('social',filters=False)+' | where social_type="interaction"'
 else:
  q=base(time=False)+' | where ($grain|s$="Year" OR ('+TIME.split(' | where ',1)[1]+')) | where $grain|s$!="Year" OR $history_scope|s$!="Comparable YTD" OR substr(local_date,6,5)<=comparison_month_day'
 q+=' | eval metric_id='+token
 if 'hr_comparison' in ids:
  ids=[i for i in ids if i!='hr_comparison']
  for i in ('avg_hr','peak_hr'):
   if i not in ids:ids.append(i)
  q+=' | eval metric_id=if(metric_id=\"hr_comparison\",mvappend(\"avg_hr\",\"peak_hr\"),metric_id) | mvexpand metric_id'
 if group_id=='engagement':q+=' | where direction=metric_id AND (metric_id!="received" OR is_current_follower=1)'
 conditions=[];nums=[];dens=[]
 for i in ids:
  r=CAT[i];valid=eligibility(r);f=r['source_field'];agg=r['aggregation_key']
  if i=='cadence':valid+=' AND $cadence_units|s$!="Unconfirmed"';f='average_cadence*if($cadence_units|s$="Strides/min",2,1)'
  conditions.extend([quoted(i), 'if('+valid+',1,0)'])
  n='1' if agg=='count' else 'moving_time_s' if agg=='pace' else f+'*moving_time_s' if agg=='weighted' else f
  d='distance_m' if agg=='pace' else 'moving_time_s' if agg in ('speed','weighted') else '1'
  nums.extend(['metric_id='+quoted(i),'if('+valid+','+n+',null())'])
  dens.extend(['metric_id='+quoted(i),'if('+valid+','+d+',null())'])
 q+=' | eval eligible=case('+','.join('metric_id='+conditions[i]+','+conditions[i+1] for i in range(0,len(conditions),2))+'),numerator=case('+','.join(nums)+'),denominator=case('+','.join(dens)+')'
 if group_id=='sample':q+=' | bin elapsed_s span=5 | eval bucket=elapsed_s,series="Activity"'
 elif group_id=='network':q+=' | eval bucket=strftime(timestamp,"%Y-%m-%d %H:%M:%S"),series="Observed at import"'
 else:q+=' | eval bucket=case($grain|s$="Year",coalesce(local_year,strftime(timestamp,"%Y")),$grain|s$="Month",coalesce(local_month,strftime(timestamp,"%Y-%m")),true(),coalesce(local_week_start,strftime(relative_time(timestamp,"@w1"),"%Y-%m-%d"))),series=case('+('true(),interaction_type' if group_id=='engagement' else 'true(),zone' if group_id=='zone' else 'metric_id="zones","Zone ".zone,metric_id IN ("pace","speed") AND $sport|s$="All",coalesce(sport,"Unspecified").if($split|s$="Gear"," · ".coalesce(gear,"Unspecified"),""),$split|s$="Sport",coalesce(sport,"Unspecified"),$split|s$="Gear",coalesce(gear,"Unspecified"),true(),"Selected activities"')+')'
 q+=' | stats sum(numerator) AS numerator sum(denominator) AS denominator max(numerator) AS peak median(numerator) AS midpoint avg(numerator) AS average dc(eval(if(eligible=1,local_date,null()))) AS days sum(eligible) AS valid_count count AS total_count BY bucket series metric_id'
 expressions=[]
 for i in ids:
  agg=CAT[i]['aggregation_key'];v='if(denominator>0,numerator/denominator,null())' if agg in ('weighted','pace','speed') else 'if(total_count>0,valid_count/total_count,null())' if agg=='coverage' else 'peak' if agg=='max' else 'midpoint' if agg=='median' else 'average' if agg=='mean' else 'days' if agg=='distinct' else 'if(valid_count>0,numerator,null())'
  expressions.extend(['metric_id='+quoted(i),v])
 q+=' | eval value=case('+','.join(expressions)+') | lookup training_lens_metric_catalog metric_id OUTPUT label metric_unit imperial_unit metric_factor imperial_factor precision | eval unit=if($units|s$="Imperial",imperial_unit,metric_unit),value=round(value*if($units|s$="Imperial",imperial_factor,metric_factor),precision),coverage=if(total_count>0,100*valid_count/total_count,null()),series_label=series." · ".label." (".unit.")" | fields bucket series_label value unit coverage | sort 0 bucket series_label'
 return q

class Page:
 def __init__(self,name,title,description):
  self.name=name;self.doc={'title':title,'description':description+' Year grain uses snapshot history; Comparable YTD ends at the import calendar date. Empty charts mean no eligible data in the selection. Automatic selects the first available metric; invalid bookmarked IDs show an explicit unavailable state. Availability is snapshot-wide and refreshes every five minutes.','visualizations':{},'dataSources':{},'inputs':{},'layout':{'type':'grid','options':{},'structure':[],'globalInputs':[]}}
  self.y=0;self.metric_ids=[]
  self.input('time',{'type':'input.timerange','title':'Period (Year grain uses history)','options':{'token':'time','defaultValue':'0,now' if name=='vitals' else '-1y,now'}})
  self.input('snapshot',{'type':'input.text','title':'Snapshot (latest or ID)','options':{'token':'snapshot','defaultValue':'latest'}})
  self.ds('dimensions','| inputlookup training_lens_dimension_options | search [ '+__import__('generate_dashboards').READY+' ]')
  for dim in ['sport','gear']:
   self.ds(dim+'_options','| where dimension="'+dim+'" | fields value label | append [ | makeresults | eval value="All",label="All" ] | dedup value | sort 0 label',extend='dimensions')
   self.input(dim,lookup_input(dim,dim.title(),dim+'_options','value'))
  for token,title,values,default in [('quality_mode','Quality',['Validated','Reported','Flagged only'],'Validated'),('units','Units',['Metric','Imperial'],'Metric'),('grain','Time grain',['Week','Month','Year'],'Year' if name in ('vitals','gear_sports','run_performance') else 'Month'),('history_scope','Annual scope',['Full years','Comparable YTD'],'Full years'),('split','Group series',['Total','Sport','Gear'],'Sport'),('cadence_units','CSV cadence convention',['Unconfirmed','Strides/min','Steps/min'],'Unconfirmed')]:self.input(token,dropdown(token,title,values,default))
 def input(self,key,definition):self.doc['inputs'][key]=definition;self.doc['layout']['globalInputs'].append(key)
 def ds(self,key,query,extend=None,smart=False):
  self.doc['dataSources'][key]={'type':'ds.chain' if extend else 'ds.search','name':key,'options':{'query':query,**({'extend':extend} if extend else {'queryParameters':{'earliest':'0','latest':'+10y'}}),**({'enableSmartSources':True} if smart else {})}}
 def panel(self,title,kind,source,unit=None,drill=False):
  key='viz_'+str(len(self.doc['visualizations']));v={'type':'splunk.singlevalue' if kind=='single' else 'splunk.'+kind,'title':title,'dataSources':{'primary':source},'options':{},'showProgressBar':True,'showLastUpdated':True}
  if kind=='line':v['options']['nullValueDisplay']='gaps'
  if unit:v['options']['yAxisTitleText']=unit;v['options']['xAxisTitleText']='Elapsed seconds' if self.name=='activity_detail' else 'Observed import date' if source=='network_chart' else 'Period'
  if kind=='map':v['options']['layers']=[{'type':'bubble','latitude':'> primary | seriesByName("latitude")','longitude':'> primary | seriesByName("longitude")','bubbleSize':'> primary | seriesByName("visits")'}]
  if drill:v['eventHandlers']=[{'type':'drilldown.linkToDashboard','options':{'app':'training_lens','dashboard':'activity_detail','tokens':[{'token':'activity_id','value':'row.activity_id.value'},{'token':'snapshot','value':'row.snapshot_id.value'}],'newTab':False}}]
  self.doc['visualizations'][key]=v;self.doc['layout']['structure'].append({'item':key,'type':'block','position':{'x':0,'y':self.y,'w':1200,'h':160 if kind=='single' else 360}});self.y+=160 if kind=='single' else 360
 def trend(self,key,ids,group='activity',summary=False):
  self.metric_ids.extend(i for i in ids if i not in self.metric_ids)
  # One catalog/availability scan per page; group children are bounded metadata.
  if 'metric_options' not in self.doc['dataSources']:
   self.ds('metric_options',options_query(list(CAT)))
  self.ds(key+'_options','| where metric_id="__auto__" OR metric_id IN ('+','.join(map(quoted,ids))+')',extend='metric_options')
  self.input(key,lookup_input(key,'Metric · '+key.replace('_',' '),key+'_options'))
  meta=key+'_metadata'
  self.ds(meta,'| where metric_id!="__auto__" AND ($'+key+'|s$="__auto__" OR metric_id=$'+key+'|s$) | head 1 | lookup training_lens_metric_catalog metric_id OUTPUT label metric_unit imperial_unit | eval unit=if($units|s$="Imperial",imperial_unit,metric_unit),title=label." (".unit.")" | appendpipe [ stats count | where count=0 | eval metric_id="__none__",unit="",title="Choose an available metric · cache pending or selection unavailable" ] | fields metric_id title unit',extend=key+'_options',smart=True)
  self.ds(key+'_aggregate',metric_query(group,ids,key,meta))
  self.ds(key+'_chart','| xyseries bucket series_label value'+(' | appendpipe [ where $grain|s$=\"Year\" | makecontinuous bucket span=1 | eval _expanded=1 ] | where $grain|s$!=\"Year\" OR _expanded=1 | fields - _expanded' if group not in ('sample','network') else ''),extend=key+'_aggregate')
  if summary:
   # Summary has its own whole-period aggregation, not an average of buckets.
   q=metric_query(group,ids,key,meta).replace('BY bucket series metric_id','BY metric_id').replace('series." · ".label','label').replace(' | fields bucket series_label value unit coverage | sort 0 bucket series_label',' | fields value')
   self.ds(key+'_summary',q);self.panel('$'+meta+':result.title$','single',key+'_summary')
  self.panel('$'+meta+':result.title$','line',key+'_chart','$'+meta+':result.unit$')
 def table(self,title,query,drill=False):
  key='table_'+str(len(self.doc['visualizations']));self.ds(key,query);self.panel(title,'table',key,drill=drill)
 def modes(self,key,title,modes):
  # Static mode IDs choose compiled predicates, never executable query strings.
  self.input(key,dropdown(key,title,list(modes),next(iter(modes))))
  branches=[]
  for label,query in modes.items():
   # Gate each search at the index predicate to avoid scans for inactive modes.
   if query.startswith('index='):
    query=query.replace(' earliest=', ' [ | makeresults | eval search=if($'+key+'|s$='+quoted(label)+',\"*\",\"event_id=__none__\") | return $search ] earliest=',1)
   query+=' | where $'+key+'|s$='+quoted(label)
   branches.append(query)
  self.table(title,branches[0]+' '+ ' '.join('| append [ search '+q+' ]' if not q.lstrip().startswith('|') else '| append [ '+q+' ]' for q in branches[1:]))

def generate(legacy,root):
 from generate_dashboards import base,telemetry,HR,NETWORK,RECEIVED,ACT,RECENT
 panels={name:{label:query for label,kind,query in data[2]} for name,data in legacy.items()}
 def old(name,start):return next(q for label,q in panels[name].items() if label.startswith(start))
 for name,(title,description,_) in legacy.items():
  p=Page(name,title,description)
  if name=='overview':
   p.trend('volume',['activities','hours','distance','elevation','active_days','flagged'],summary=True)
   p.modes('activity_view','Activities and coverage',{'Recent activities':RECENT,'Coverage':old(name,'Coverage'),'Annual changes':old(name,'Annual activity changes')})
   # retain drilldown on the recent activity/table panel in all modes
   p.doc['visualizations']['viz_2']['eventHandlers']=[{'type':'drilldown.linkToDashboard','options':{'app':'training_lens','dashboard':'activity_detail','tokens':[{'token':'activity_id','value':'row.activity_id.value'},{'token':'snapshot','value':'row.snapshot_id.value'}],'newTab':False}}]
  elif name=='training':
   p.trend('load',['effort','hours','activities','zones'],'activity')
   # zone uses a separate selected source; compiled source routing below.
   p.ds('goal_options','| where dimension=\"goal\" | fields value label | append [ | makeresults | eval value=\"All\",label=\"All configured goals\" ]',extend='dimensions')
   p.input('goal',lookup_input('goal','Configured goal','goal_options','value'))
   p.table('Configured goal · progress at import',base('goal',time=False,filters=False)+' | eval goal_key=sport.\" · \".metric.\" · \".period | where $goal|s$=\"All\" OR goal_key=$goal|s$ | table sport metric target period period_start as_of progress_value progress_pct')
   p.modes('training_details','Training details',{'Weekly log':old(name,'Weekly activity log'),'Effort comparison':old(name,'Imported weekly effort'),'HR observation coverage':old(name,'Observed versus'),'Effort coverage':old(name,'Effort coverage')})
  elif name=='run_performance':
   p.trend('performance',['distance','pace','speed','cadence','avg_hr'])
   p.doc['dataSources']['performance_aggregate']['options']['query']=p.doc['dataSources']['performance_aggregate']['options']['query'].replace(' | dedup event_id',' | dedup event_id | where sport="Run"',1)
   p.ds('effort_options','| where dimension=\"effort_target\" | fields value label | append [ | makeresults | eval value=\"All\",label=\"All recorded targets\" ]',extend='dimensions')
   p.input('effort_target',lookup_input('effort_target','Best-effort target','effort_options','value'))
   p.table('Best efforts by target distance · elapsed seconds',telemetry('best_effort')+' | where $effort_target|s$=\"All\" OR tostring(target_m)=$effort_target|s$ | stats min(duration_s) AS elapsed_seconds BY target_m | sort target_m')
   p.modes('run_details','Comparable runs / annual coverage',{'Comparable runs':old(name,'Comparable runs'),'Annual coverage':old(name,'Annual running metric coverage')})
   p.doc['visualizations']['viz_2']['eventHandlers']=[{'type':'drilldown.linkToDashboard','options':{'app':'training_lens','dashboard':'activity_detail','tokens':[{'token':'activity_id','value':'row.activity_id.value'},{'token':'snapshot','value':'row.snapshot_id.value'}],'newTab':False}}]
  elif name=='activity_detail':
   p.input('activity',{'type':'input.text','title':'Activity ID','options':{'token':'activity_id','defaultValue':'none'}})
   p.table('Activity summary',old(name,'Activity summary'))
   p.trend('telemetry',['sample_hr','sample_pace','sample_speed','sample_altitude','sample_cadence','sample_power'],'sample')
   p.doc['dataSources']['metric_options']['options']['query']=telemetry('sample',detail=True)+' | stats '+ ' '.join('count('+CAT[i]['source_field']+') AS '+i for i in CAT if CAT[i]['group_id']=='sample')+' | transpose 0 column_name=metric_id | rename \"row 1\" AS valid_count | where valid_count>0 | lookup training_lens_metric_catalog metric_id OUTPUT label sort_order | append [ | makeresults | eval metric_id=\"__auto__\",label=\"Automatic / first available\",sort_order=-1 ] | sort 0 sort_order'
   p.modes('detail_mode','Activity details',{'Laps':old(name,'Device laps'),'Splits':old(name,'Derived kilometer'),'Zones':old(name,'HR zones'),'Exercises':old(name,'Strength exercises')})
  elif name=='vitals':
   p.trend('vital',['avg_hr','peak_hr','hr_comparison','weight'])
   p.trend('zone_history',['zones'],'zone')
   p.modes('vitals_details','Vitals coverage and limitations',{'Availability':old(name,'Vitals availability'),'Annual coverage':old(name,'Annual HR and weight')})
  elif name=='social':
   p.trend('network',['followers','following','pending','mutual'],'network')
   p.trend('engagement',['given','received'],'engagement')
   p.modes('followers_table','Followers',{'Top interactions':old(name,'Top current followers'),'Roster':old(name,'Network roster'),'Observed changes':old(name,'Follower count changes')})
   p.table('Current network and source availability',NETWORK+' | eval received_interactions=if(received_available=1,"Supplemental records supplied","Unavailable; supply social_interactions.csv"),history="Observed at import; no follow dates",option_cache="'+ 'Refresh every five minutes; absent choices are pending or unsupported'+'" | table followers following pending_followers mutual followers_available following_available comments_available kudos_available received_interactions history option_cache')
  elif name=='gear_sports':
   p.trend('usage',['activities','distance','hours','speed','pace','elevation','avg_hr'])
   p.table('Equipment thresholds · recorded lifetime mileage',old(name,'Equipment thresholds'))
   p.modes('sport_details','Gear / sport details',{'Gear usage':old(name,'Recorded gear usage'),'Sport summaries':old(name,'Sport summaries'),'Strength sessions':old(name,'Strength sessions'),'Annual coverage':old(name,'Annual sport metric coverage')})
  elif name=='geography':
   p.ds('map',old(name,'Personal activity visits'));p.panel('Privacy-masked activity visits · top 1000 cells','map','map')
   p.modes('geo_details','Geography details',{'Cells (top 1000)':old(name,'Visited cells'),'Sport coverage':old(name,'Geography coverage')})
  elif name=='data_health':
   p.modes('readiness','Import readiness',{'Active snapshot':old(name,'Active snapshot'),'Reconciliation':old(name,'Pending and reconciled'),'Availability cache':'| inputlookup training_lens_metric_availability | search [ '+__import__('generate_dashboards').READY+' ] | stats count AS cached_metrics max(refreshed_at) AS refreshed_at | eval age_seconds=now()-refreshed_at,status=case(cached_metrics=0,\"Pending: no cache for selected ready snapshot\",age_seconds>900,\"Stale: investigate refresh search\",true(),\"Current\")'})
   p.trend('coverage',['hr_coverage','effort_coverage','stream_coverage'])
   p.modes('health_details','Diagnostics',{'Completeness':old(name,'Completeness'),'Quality issues':old(name,'Quality issues'),'Import manifests':old(name,'Import manifests'),'Worker status':old(name,'Recent worker')})
  else:
   p.table('Configuration · see Data Health for import readiness',old(name,'Setup checklist').replace('$SPLUNK_HOME','SPLUNK_HOME')+' | eval data_health="Open Data Health from the app navigation"')
  # Fix source routing when Training chooses zone hours: streaming union gated by selected ID.
  if name=='training':
   ds=p.doc['dataSources']['load_aggregate'];q=ds['options']['query'];marker=' | eval metric_id='
   suffix=q[q.index(marker):]
   q=q[:q.index(marker)]+' | where $load_metadata:result.metric_id|s$!="zones" | append [ search '+zone_source()+' | where $load_metadata:result.metric_id|s$="zones" ]'+suffix
   ds['options']['query']=q
  # Useful chart controls only; preserve required query tokens via hidden defaults.
  if name=='setup':pass
  if 'metric_options' in p.doc['dataSources'] and name!='activity_detail':
   p.doc['dataSources']['metric_options']['options']['query']=options_query(p.metric_ids)
   if 'cadence' not in p.metric_ids:
    p.doc['dataSources']['metric_options']['options']['query']=p.doc['dataSources']['metric_options']['options']['query'].replace(' | where coalesce(prerequisite,"")!="confirmed_cadence" OR $cadence_units|s$!="Unconfirmed"','')
  queries=' '.join(d['options']['query'] for d in p.doc['dataSources'].values())
  for key,definition in list(p.doc['inputs'].items()):
   token=definition['options']['token']
   if '$'+token+'|' not in queries and '$'+token+'.' not in queries:
    del p.doc['inputs'][key];p.doc['layout']['globalInputs'].remove(key)
  if name=='setup':
   p.doc['inputs']={};p.doc['layout']['globalInputs']=[]
   p.doc['dataSources']={k:v for k,v in p.doc['dataSources'].items() if k.startswith('table_')}
  if name in ('setup','geography','social','activity_detail'):
   p.doc['description']=description
  r=ET.Element('dashboard',version='2',theme='light');ET.SubElement(r,'label').text=title;ET.SubElement(r,'description').text=p.doc['description'];ET.SubElement(r,'definition').text=json.dumps(p.doc,indent=2)
  ET.ElementTree(r).write(root/'views'/(name+'.xml'),encoding='utf-8',xml_declaration=True)
 from metric_catalog import availability_search,dimension_search
 config=root.parent.parent/'savedsearches.conf'
 text=config.read_text().split('[Training Lens refresh')[0].rstrip()+'\n'
 for title,query in [('metric availability',availability_search()),('dimension options',dimension_search())]:
  text+='\n[Training Lens refresh '+title+']\nsearch = '+query+'\ncron_schedule = */5 * * * *\ndispatch.earliest_time = 0\ndispatch.latest_time = +10y\nenableSched = 1\nschedule_window = auto\n'
 config.write_text(text)
 nav=ET.Element('nav',search_view='search',color='#ED6A27')
 for name in legacy:ET.SubElement(nav,'view',name=name,default='true' if name=='overview' else 'false')
 ET.ElementTree(nav).write(root/'nav/default.xml',encoding='utf-8',xml_declaration=True)
