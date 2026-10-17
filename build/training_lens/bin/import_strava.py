#!/usr/bin/env python3
"""Training Lens inbox worker and offline import CLI."""
import argparse
import configparser
import json
import os
from pathlib import Path
import sys
import time
from tl.ingest import import_archive,scan

def main():
    os.umask(0o077)
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive',type=Path);parser.add_argument('--state',type=Path)
    parser.add_argument('--summary-only',action='store_true');args=parser.parse_args()
    app=Path(__file__).resolve().parents[1];settings=configparser.ConfigParser()
    settings.read([str(app/'default/training_lens.conf'),str(app/'local/training_lens.conf')])
    section=settings['settings'] if settings.has_section('settings') else {}
    root=args.state or Path(os.environ.get('SPLUNK_HOME',str(app.parent.parent)))/'var/lib/training_lens'
    config_path=root/'config.json'
    config=json.loads(config_path.read_text()) if config_path.exists() else {}
    kwargs={'decode':not args.summary_only and section.get('decode_streams','true').lower()=='true','timezone':section.get('timezone','UTC'),'athlete_id':section.get('athlete_id','personal'),'config':config}
    try:
        result=import_archive(args.archive,root,**kwargs) if args.archive else scan(root,**kwargs)
        failures=[r for r in result if r.get('state')=='failed'] if isinstance(result,list) else []
        count=sum(r.get('state')!='failed' for r in result) if isinstance(result,list) else 1
        print(json.dumps({'timestamp':time.time(),'kind':'worker','status':'failed' if failures else 'ok','imports':count,'failures':len(failures),'error_type':'archive_rejected' if failures else None,'event_id':'worker:'+str(time.time_ns())}))
        return 1 if failures else 0
    except BlockingIOError:return 0
    except Exception as error:
        # Only a category is logged; parser exceptions may include private source values.
        print(json.dumps({'timestamp':time.time(),'kind':'worker','status':'failed','error_type':type(error).__name__}))
        return 1
if __name__=='__main__':sys.exit(main())
