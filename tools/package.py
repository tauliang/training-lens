#!/usr/bin/env python3
"""Create an allowlisted deterministic Splunk app archive."""
import argparse,gzip,hashlib,io,tarfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def package(output):
    source=ROOT/'build/training_lens';output.parent.mkdir(parents=True,exist_ok=True)
    with output.open('wb') as raw:
        with gzip.GzipFile(filename='',mode='wb',fileobj=raw,mtime=0) as gz:
            with tarfile.open(fileobj=gz,mode='w',format=tarfile.USTAR_FORMAT) as tar:
                for path in sorted(source.rglob('*')):
                    rel=path.relative_to(source)
                    if path.is_symlink():raise ValueError('symlink_in_package')
                    if not path.is_file() or '__pycache__' in rel.parts or path.suffix in ('.pyc','.pyo'):continue
                    if rel.parts[0] not in ('bin','default','metadata','README') and rel.as_posix() not in ('README.md','LICENSE','THIRD_PARTY_LICENSES','CHANGELOG.md'):raise ValueError('unexpected_package_file: '+str(rel))
                    if path.suffix.lower() in ('.zip','.fit','.gpx','.ndjson'):raise ValueError('personal_data_in_package')
                    info=tarfile.TarInfo('training_lens/'+rel.as_posix());data=path.read_bytes();info.size=len(data);info.mtime=0;info.uid=info.gid=0;info.mode=0o755 if rel.as_posix()=='bin/import_strava.py' else 0o644;tar.addfile(info,io.BytesIO(data))
    digest=hashlib.sha256(output.read_bytes()).hexdigest();output.with_suffix(output.suffix+'.sha256').write_text(digest+'  '+output.name+'\n');return digest
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,default=ROOT/'dist/training_lens-1.0.0.spl');args=parser.parse_args();print(package(args.output))
