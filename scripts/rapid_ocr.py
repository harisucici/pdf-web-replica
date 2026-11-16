"""Local PP-OCR recognition with source character boxes and explicit model routes.

No document is uploaded. Model weights may be downloaded on first use. Engines
persist across pages; raw alternative readings stay in work/, never become truth
merely because a different script received a larger confidence bonus.
"""
import json
import hashlib
from importlib import metadata
import re
from pathlib import Path

SUPPORTED = {'auto', 'ja', 'zh', 'zh-hant', 'en', 'ko', 'vi'}
_ENGINES = {}
_MODEL_HASHES = {}


def supported(languages):
    return set(languages) <= SUPPORTED


def engine(cache, korean=False, japanese=False):
    from rapidocr import RapidOCR, ModelType, OCRVersion
    key = (str(Path(cache).resolve()), korean, japanese)
    if key not in _ENGINES:
        params = {
            'Global.model_root_dir': str(Path(cache) / 'models'),
            'Global.log_level': 'warning', 'Global.max_side_len': 5000,
            'Global.return_word_box': True, 'Global.return_single_char_box': True,
            'Global.text_score': .01, 'Det.limit_side_len': 2560,
            'Det.limit_type': 'max', 'Det.unclip_ratio': 1.3,
            'Det.ocr_version': OCRVersion.PPOCRV6, 'Det.model_type': ModelType.SMALL,
            'Rec.ocr_version': OCRVersion.PPOCRV6, 'Rec.model_type': ModelType.SMALL,
            'EngineConfig.onnxruntime.intra_op_num_threads': 4,
            'EngineConfig.onnxruntime.inter_op_num_threads': 1,
        }
        if korean:
            params.update({'Rec.lang_type': 'korean', 'Rec.ocr_version': OCRVersion.PPOCRV5,
                           'Rec.model_type': ModelType.MOBILE})
        if japanese:
            params.update({'Rec.lang_type':'japan','Rec.ocr_version':OCRVersion.PPOCRV4,
                           'Rec.model_type':ModelType.MOBILE})
        _ENGINES[key] = RapidOCR(params=params)
    return _ENGINES[key]


def bounds(box):
    xs, ys = zip(*box)
    return [float(min(xs)), float(min(ys)), float(max(xs)), float(max(ys))]


def language(text):
    if re.search('[가-힣]', text):
        return 'ko'
    if re.search('[ぁ-ヿ]', text):
        return 'ja'
    if re.search('[一-龯]', text):
        return 'zh'
    if re.search('[ĂăĐđƠơƯưẠ-ỹ]', text):
        return 'vi'
    return 'en'


def choose_segments(text, chars, score, ko_text='', ko_chars=(), ko_score=0):
    """Keep mixed-script prefixes; a Korean pass must not replace Japanese rows."""
    hangul = [(i, c) for i, c in enumerate(ko_chars)
              if re.search('[가-힣]', c[0]) and c[1] > .5]
    if len(hangul) < 2 or ko_score < .7:
        return [(text, chars, language(text), score)]
    start = hangul[0][0]
    boundary = bounds(ko_chars[start][2])[0]
    prefix = [c for c in chars if bounds(c[2])[2] < boundary + 2]
    prefix_text = ''.join(c[0] for c in prefix)
    if re.search('[一-龯ぁ-ヿ]', prefix_text):
        tail = ko_chars[start:]
        return [(prefix_text, prefix, language(prefix_text), score),
                (''.join(c[0] for c in tail), tail, 'ko', ko_score)]
    # A confident complete Japanese/Chinese reading beats a false Hangul reading.
    if score >= .94 and re.search('[一-龯ぁ-ヿ]', text):
        return [(text, chars, language(text), score)]
    return [(ko_text, ko_chars, 'ko', ko_score)]


def recognize_local(image, languages, cache):
    import cv2
    import numpy as np
    if not supported(languages):
        raise ValueError('rapidocr_language_route_not_available:' + ','.join(languages))
    cache = Path(cache)
    cache.mkdir(parents=True, exist_ok=True)
    img = cv2.imread(str(image))
    if img is None:
        raise ValueError('cannot_read_ocr_image:' + str(image))
    main = engine(cache)
    det = main(img, use_rec=False, use_cls=False)
    if det.boxes is None:
        return {'coordinate_space': 'pixels', 'width': img.shape[1],
                'height': img.shape[0], 'blocks': [], 'warnings': []}
    crops = main.crop_text_regions(img, det.boxes)
    rec = main.recognize_txt(crops)
    # Unlike calc_word_boxes, this preserves empty rows, so parallel alternatives
    # cannot shift their indices when one model fails to recognize a crop.
    chars = main.cal_rec_boxes(crops, det.boxes, rec, True).word_results
    kor = kr_chars = None
    if 'ko' in languages or languages == ['auto']:
        model = engine(cache, korean=True)
        kor = model.recognize_txt(crops)
        kr_chars = model.cal_rec_boxes(crops, det.boxes, kor, True).word_results
    models=[]
    for file in sorted((cache/'models').glob('*.onnx')):
        key=(str(file),file.stat().st_size,file.stat().st_mtime_ns)
        if key not in _MODEL_HASHES:_MODEL_HASHES[key]=hashlib.sha256(file.read_bytes()).hexdigest()
        models.append({'file':file.name,'sha256':_MODEL_HASHES[key]})
    (cache/'ocr-runtime.json').write_text(json.dumps({'packages':{n:metadata.version(n) for n in ('rapidocr','onnxruntime','opencv-python-headless','numpy')},'models':models},indent=2),encoding='utf-8')
    blocks, raw = [], []
    for i, box in enumerate(det.boxes):
        text, confidence = rec.txts[i], float(rec.scores[i])
        kt, kc, ks = (kor.txts[i], kr_chars[i], float(kor.scores[i])) if kor else ('', (), 0)
        raw.append({'box': box.tolist(), 'text': text, 'score': confidence,
                    'characters': chars[i], 'ko_text': kt, 'ko_score': ks, 'ko_characters': kc})
        segments = choose_segments(text, chars[i], confidence, kt, kc, ks)
        for t, cc, lang, score in segments:
            if not t.strip() or score < .25:
                continue
            bb = bounds(np.concatenate([np.array(c[2]) for c in cc])) if len(segments) > 1 and cc else bounds(box)
            vertical = bb[3] - bb[1] > (bb[2] - bb[0]) * 1.35
            if vertical and cc:
                for ch, conf, cb in cc:
                    blocks.append({'text': ch, 'bbox': bounds(cb), 'confidence': float(conf),
                                   'language': lang, 'role': 'vertical_text'})
            else:
                blocks.append({'text': t, 'bbox': bb, 'confidence': float(score), 'language': lang,
                               'characters': [{'text': c[0], 'confidence': float(c[1]), 'bbox': bounds(c[2])} for c in cc]})
    def serial(v):
        return v.item() if hasattr(v, 'item') else v.tolist()
    (cache / (Path(image).stem + '.rapidocr.json')).write_text(
        json.dumps({'lines': raw}, ensure_ascii=False, default=serial), encoding='utf-8')
    return {'coordinate_space': 'pixels', 'width': img.shape[1], 'height': img.shape[0],
            'blocks': blocks, 'warnings': ['rapidocr_small_annotations_and_script_conflicts_require_source_review']}


def recognize(image, languages, cache):
    import ocr_worker
    return ocr_worker.call({'operation':'recognize','image':str(Path(image).resolve()),
                            'languages':languages,'cache':str(Path(cache).resolve())})


def recognize_crops(crops,cache):
    import cv2
    import tempfile
    import ocr_worker
    Path(cache).mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='ruby-crops-',dir=cache) as temp:
        files=[]
        for i,img in enumerate(crops):
            p=Path(temp)/f'{i:05}.png'
            if not cv2.imwrite(str(p),img):raise ValueError('cannot_write_annotation_crop')
            files.append(str(p.resolve()))
        return ocr_worker.call({'operation':'recognize_crops','images':files,
                                'cache':str(Path(cache).resolve())})
