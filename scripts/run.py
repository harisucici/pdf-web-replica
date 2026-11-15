#!/usr/bin/env python3
"""Use an available PDF-capable interpreter, including from a different agent venv."""
import os,shutil,subprocess,sys
from pathlib import Path

def main():
 candidates=[]
 if os.environ.get('PDF_WEB_PYTHON'):candidates.append(os.environ['PDF_WEB_PYTHON'])
 candidates.extend([sys.executable,shutil.which('python3'),shutil.which('python')])
 for v in [Path.cwd()/'work/.pdf-web-env',Path.cwd()/'.pdf-web-env']:
  candidates.append(str(v/('Scripts/python.exe' if os.name=='nt' else 'bin/python')))
 if os.name!='nt':candidates.append('/usr/bin/python3')
 seen=set();selected=None
 for value in candidates:
  if not value or value in seen or not Path(value).is_file():continue
  seen.add(value)
  try:
   r=subprocess.run([value,'-c','import pymupdf'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=15)
   if r.returncode==0:selected=value;break
  except (OSError,subprocess.TimeoutExpired):continue
 cli=Path(__file__).with_name('pdf_web.py')
 if selected:os.execv(selected,[selected,str(cli),*sys.argv[1:]])
 # Doctor or the CLI emits a concrete bootstrap instruction; the skill itself remains loadable.
 os.execv(sys.executable,[sys.executable,str(cli),*sys.argv[1:]])
if __name__=='__main__':main()
