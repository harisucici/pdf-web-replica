"""Keep native inference crashes outside the PDF build process.

A persistent child keeps models warm. EOF, native exit and timeout become ordinary
backend failures, so auto fallback and the per-page ledger still work.
"""
import atexit
import json
import os
from pathlib import Path
import queue
import subprocess
import sys
import tempfile
import threading
import time

PREFIX='PDF_WEB_OCR_RESULT\t'
_CLIENT=None


class Worker:
    def __init__(self):
        self.log=tempfile.TemporaryFile(mode='w+b')
        env={**os.environ,'PYTHONUNBUFFERED':'1','PYTHONIOENCODING':'utf-8'}
        self.process=subprocess.Popen([sys.executable,str(Path(__file__).resolve())],
            stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=self.log,text=True,
            encoding='utf-8',env=env,bufsize=1)
        self.queue=queue.Queue();self.lock=threading.Lock()
        threading.Thread(target=self.read,daemon=True).start()

    def read(self):
        try:
            for line in self.process.stdout:self.queue.put(line)
        except (OSError,ValueError):pass
        finally:self.queue.put(None)

    def call(self,payload,timeout=300):
        with self.lock:
            self.process.stdin.write(json.dumps(payload,ensure_ascii=False)+'\n');self.process.stdin.flush()
            deadline=time.monotonic()+timeout
            while True:
                remaining=deadline-time.monotonic()
                if remaining<=0:raise RuntimeError('rapidocr_worker_timeout')
                try:line=self.queue.get(timeout=remaining)
                except queue.Empty:raise RuntimeError('rapidocr_worker_timeout')
                if line is None:
                    code=self.process.wait(timeout=5)
                    raise RuntimeError('rapidocr_native_worker_exited:'+str(code))
                if line.startswith(PREFIX):
                    result=json.loads(line[len(PREFIX):])
                    if 'error' in result:raise RuntimeError(result['error'])
                    return result['result']

    def close(self):
        if self.process.poll() is None:
            self.process.kill();self.process.wait(timeout=5)
        for stream in (self.process.stdin,self.process.stdout):
            if stream:
                try:stream.close()
                except (OSError,ValueError):pass
        self.log.close()


def call(payload,timeout=300):
    global _CLIENT
    if _CLIENT is None or _CLIENT.process.poll() is not None:
        if _CLIENT is not None:_CLIENT.close()
        _CLIENT=Worker()
    try:return _CLIENT.call(payload,timeout)
    except Exception:
        _CLIENT.close();_CLIENT=None;raise


def shutdown():
    global _CLIENT
    if _CLIENT is not None:_CLIENT.close();_CLIENT=None


atexit.register(shutdown)


def serve():
    import rapid_ocr
    for line in sys.stdin:
        try:
            data=json.loads(line)
            if data['operation']=='recognize':
                result=rapid_ocr.recognize_local(data['image'],data['languages'],data['cache'])
            elif data['operation']=='recognize_crops':
                import cv2
                crops=[cv2.imread(p) for p in data['images']]
                if any(c is None for c in crops):raise ValueError('cannot_read_small_annotation_crop')
                a=rapid_ocr.engine(data['cache']).recognize_txt(crops)
                b=rapid_ocr.engine(data['cache'],japanese=True).recognize_txt(crops)
                result={'main':list(zip(a.txts,map(float,a.scores))),
                        'japanese':list(zip(b.txts,map(float,b.scores)))}
            else:raise ValueError('unknown_ocr_operation')
            response={'result':result}
        except Exception as exc:response={'error':type(exc).__name__+':'+str(exc)}
        print(PREFIX+json.dumps(response,ensure_ascii=False),flush=True)


if __name__=='__main__':serve()
