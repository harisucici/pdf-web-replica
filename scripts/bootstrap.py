#!/usr/bin/env python3
"""Create an isolated runtime; does not alter an agent's global environment."""
import argparse,json,subprocess,sys,venv
from pathlib import Path

def main():
 p=argparse.ArgumentParser();p.add_argument('--venv',type=Path,required=True);p.add_argument('--offline',action='store_true');a=p.parse_args()
 dest=a.venv.expanduser().resolve();venv.EnvBuilder(with_pip=True).create(dest)
 python=dest/('Scripts/python.exe' if sys.platform=='win32' else 'bin/python')
 cmd=[str(python),'-m','pip','install','-r',str(Path(__file__).resolve().parents[1]/'requirements.txt')]
 if a.offline:cmd.append('--no-index')
 result=subprocess.run(cmd,stdout=sys.stderr,stderr=sys.stderr)
 if result.returncode:return result.returncode
 print(json.dumps({'python':str(python),'venv':str(dest)},ensure_ascii=False));return 0
if __name__=='__main__':raise SystemExit(main())
