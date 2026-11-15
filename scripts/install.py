#!/usr/bin/env python3
"""Install the portable folder without changing agent settings or permissions."""
import argparse,json,os,shutil,sys,time
from pathlib import Path
NAME='pdf-web-replica'
def target(agent,root=None):
 if root:return Path(root).expanduser()/NAME
 home=Path.home()
 if agent=='hermes':base=Path(os.environ.get('HERMES_HOME',str(home/'.hermes')))/'skills'
 elif agent=='codex':base=Path(os.environ.get('CODEX_HOME',str(home/'.codex')))/'skills'
 elif agent=='opencode':base=Path(os.environ.get('XDG_CONFIG_HOME',str(home/'.config')))/'opencode/skills'
 elif agent=='openclaw':base=home/'.openclaw/skills'
 else:base=home/'.agents/skills'
 return base/NAME

def main():
 p=argparse.ArgumentParser();p.add_argument('--agent',choices=['hermes','codex','opencode','openclaw','generic'],required=True);p.add_argument('--root',help='Explicit skill-root directory, useful for profiles or tests');p.add_argument('--update',action='store_true');p.add_argument('--dry-run',action='store_true');a=p.parse_args()
 src=Path(__file__).resolve().parents[1];dst=target(a.agent,a.root).resolve()
 if src==dst:print(json.dumps({'status':'already-installed','path':str(dst)}));return 0
 if a.dry_run:print(json.dumps({'source':str(src),'target':str(dst),'agent':a.agent}));return 0
 backup=None
 if dst.exists():
  if not a.update:p.error(f'Already exists: {dst}; use --update to preserve a backup and replace it')
  backup=dst.parent.parent/'skill-backups'/(dst.name+'-'+str(time.time_ns()));backup.parent.mkdir(parents=True,exist_ok=True);dst.rename(backup)
 dst.parent.mkdir(parents=True,exist_ok=True)
 try:shutil.copytree(src,dst,ignore=shutil.ignore_patterns('__pycache__','*.pyc','.venv','.git'))
 except Exception:
  if dst.exists():shutil.rmtree(dst)
  if backup:backup.rename(dst)
  raise
 print(json.dumps({'status':'installed','agent':a.agent,'path':str(dst),'backup':str(backup) if backup else None},ensure_ascii=False));return 0
if __name__=='__main__':raise SystemExit(main())
