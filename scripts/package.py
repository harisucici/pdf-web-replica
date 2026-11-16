#!/usr/bin/env python3
"""Build a versioned skill archive using an explicit source allowlist."""
import argparse,hashlib,json,re,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
FILES=['SKILL.md','README.md','README.en.md','README.ja.md','LICENSE','requirements.txt','requirements-ocr.txt','CHANGELOG.md']
DIRECTORIES=['agents','assets','references','scripts','docs']
def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 match=re.search(r'^  version:\s*"([0-9]+\.[0-9]+\.[0-9]+(?:-[A-Za-z0-9.-]+)?)"\s*$',(ROOT/'SKILL.md').read_text(),re.M)
 if not match:raise SystemExit('SKILL.md needs metadata.version in semantic version format')
 version=match.group(1);out=a.out.expanduser().resolve();out.mkdir(parents=True,exist_ok=True);archive=out/f'pdf-web-replica-v{version}.zip'
 selected=[ROOT/name for name in FILES if (ROOT/name).is_file()]
 for name in DIRECTORIES:
  selected.extend(p for p in (ROOT/name).rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix not in ['.pyc','.pyo'] and not any(x.startswith('.') for x in p.relative_to(ROOT).parts))
 with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
  for path in sorted(set(selected)):z.write(path,Path('pdf-web-replica')/path.relative_to(ROOT))
 sha=hashlib.sha256(archive.read_bytes()).hexdigest();checksum=archive.with_suffix('.sha256');checksum.write_text(sha+'  '+archive.name+'\n')
 with zipfile.ZipFile(archive) as z:
  if z.testzip():raise SystemExit('Archive integrity check failed')
 print(json.dumps({'version':version,'archive':str(archive),'sha256_file':str(checksum),'sha256':sha,'files':len(set(selected))},indent=2))
if __name__=='__main__':main()
