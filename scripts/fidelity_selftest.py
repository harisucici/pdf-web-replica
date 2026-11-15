#!/usr/bin/env python3
"""Synthetic region/evidence regressions. Captures here are NOT browser evidence."""
import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path
import pymupdf as fitz
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / 'scripts/pdf_web.py'


def call(*args, codes=(0,)):
    result = subprocess.run([sys.executable, str(CLI), *map(str, args)], capture_output=True, text=True)
    assert result.returncode in codes, (args, result.stdout, result.stderr)
    return result


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def save(path, data):
    Path(path).write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')


def checks(work):
    doc = fitz.open()
    page = doc.new_page(width=240, height=320)
    page.draw_rect(page.rect, fill=(.98, .96, .92), color=None)
    page.draw_rect((24, 60, 216, 172), fill=(.78, .86, .92), color=None)
    page.insert_text((32, 90), 'Small source text', fontsize=11)
    page.insert_text((32, 125), 'Ruby / table / colors', fontsize=9)
    scan = page.get_pixmap(matrix=fitz.Matrix(2, 2)).tobytes('png')
    scanned = doc.new_page(width=240, height=320)
    scanned.insert_image((25, 30, 215, 290), stream=scan, keep_proportion=False)
    source = work / 'unseen-layout.pdf'
    doc.save(source)
    doc.close()
    out = work / 'out'
    call('build', source, '--out', out, '--ocr', 'none')
    call('analyze', out)
    plan = read(out / 'reconstruction-plan.json')
    assert len(plan['pages']) == 2
    analysis = read(out / 'analysis/00001.json')
    assert any(c['kind'] == 'panel_candidate' and abs(c['bbox'][0] - 24) < 4
               and abs(c['bbox'][1] - 60) < 4 for c in analysis['candidates'])
    assert (out / 'analysis/contact-001.jpg').exists()
    plan['pages'][0]['notes'] = 'manual family decision'
    save(out / 'reconstruction-plan.json', plan)
    call('analyze', out)
    assert read(out / 'reconstruction-plan.json')['pages'][0]['notes'] == 'manual family decision'
    call('review', out, '--pages', '1', '--checks', 'layout', '--note', 'No screenshot yet', codes=(2,))
    page_path = out / 'pages/00001.json'
    before = read(page_path)
    call('review', out, '--pages', '1', '--checks', 'text', '--note', 'Synthetic source comparison')
    assert read(page_path)['review']['text']
    call('refresh', out)
    assert read(page_path)['render_fingerprint'] == before['render_fingerprint']
    assert read(page_path)['review']['text']  # Build timestamps do not invalidate proof.
    patch = work / 'patch.json'
    save(patch, {'background_color': '#faf5eb'})
    call('apply-layout', out, '--page', '1', '--json', patch)
    current = read(page_path)
    assert current['render_fingerprint'] != before['render_fingerprint'] and not any(current['review'].values())
    save(patch, {'review': {'layout': True}})
    call('apply-layout', out, '--page', '1', '--json', patch, codes=(2,))
    capture = work / 'captures'
    capture.mkdir()
    reference = out / 'references/00001.png'
    # Synthetic equality/difference inputs test mathematics and evidence binding only.
    Image.open(reference).save(capture / '00001.png')
    meta = {'page': 1, 'render_fingerprint': current['render_fingerprint'], 'default_view': True,
            'page_only': True, 'ready': True, 'visible_text_elements': 2,
            'captured_with': 'synthetic comparator unit fixture, NOT a browser capture'}
    save(capture / '00001.json', dict(meta, default_view=False))
    call('compare', out, '--captures', capture, '--pages', '1', codes=(3,))
    save(capture / '00001.json', meta)
    call('compare', out, '--captures', capture, '--pages', '1')
    comparison = read(out / 'qa/comparisons/00001.json')
    assert comparison['metrics']['changed_pixel_ratio'] == 0
    assert (out / 'qa/comparisons/00001-diff.png').exists()
    changed = Image.open(reference).convert('RGB')
    draw = ImageDraw.Draw(changed)
    draw.rectangle((48, 120, 432, 344), fill='white')
    changed.save(capture / '00001.png')
    call('compare', out, '--captures', capture, '--pages', '1', codes=(3,))
    comparison = read(out / 'qa/comparisons/00001.json')
    assert comparison['status'] == 'needs_revision' and comparison['worst_regions'][0]['changed_ratio'] > .1
    call('review', out, '--pages', '1', '--checks', 'layout,fonts', '--note', 'Still different', codes=(2,))
    Image.open(reference).save(capture / '00001.png')
    call('compare', out, '--captures', capture, '--pages', '1')
    call('review', out, '--pages', '1', '--checks', 'text,layout,fonts,languages', '--note', 'Test-only synthetic evidence gate')
    audited = json.loads(call('audit', out, codes=(3,)).stdout)
    assert not any(i.get('page') == 1 for i in audited['issues'])
    assert any(i.get('page') == 2 for i in audited['issues'])
    save(patch, {'remaining_differences': ['Unresolved source annotation at top right']})
    call('apply-layout', out, '--page', '1', '--json', patch)
    call('review', out, '--pages', '1', '--checks', 'text', '--note', 'Cannot approve open differences', codes=(2,))
    audited = json.loads(call('audit', out, codes=(3,)).stdout)
    assert any(i['issue'] == 'unresolved_source_difference' for i in audited['issues'])
    save(patch, {'remaining_differences': []})
    call('apply-layout', out, '--page', '1', '--json', patch)
    call('review', out, '--pages', '1', '--checks', 'text,layout,fonts,languages', '--note', 'Test-only resolved residual')
    # Editing the actual stylesheet invalidates both the review and the screenshot.
    css = out / 'site/reader.css'
    css.write_text(css.read_text() + '\n/* changed renderer */\n')
    audited = json.loads(call('audit', out, codes=(3,)).stdout)
    assert any(i.get('page') == 1 and i['issue'] == 'review_record_stale' for i in audited['issues'])
    assert any(i.get('page') == 1 and i['issue'] == 'visual_evidence_stale' for i in audited['issues'])
    call('refresh', out)
    # Updating OCR without updating a manual layout cannot be accepted.
    page = read(page_path)
    save(patch, {'web_layout': {'elements': [], 'blocks': []}})
    call('apply-layout', out, '--page', '1', '--json', patch)
    save(patch, {'coordinate_space': 'normalized', 'blocks': [{'text': 'Changed OCR', 'bbox': [.1, .1, .8, .15]}]})
    call('import-ocr', out, '--page', '1', '--json', patch)
    assert read(page_path)['layout_needs_sync'] is True
    call('review', out, '--pages', '1', '--checks', 'text', '--note', 'Stale visible layout', codes=(2,))
    # A toolbar-sized or distorted capture cannot be silently stretched to fit.
    meta['render_fingerprint'] = read(page_path)['render_fingerprint']
    save(capture / '00001.json', meta)
    Image.new('RGB', (500, 500), 'white').save(capture / '00001.png')
    call('compare', out, '--captures', capture, '--pages', '1', codes=(3,))
    assert 'aspect_ratio' in read(out / 'qa/comparison-report.json')['pages'][0]['error']
    # OCR auto mode continues to the next installed route after failure/empty output.
    import ocr_backends
    saved_cap, saved_vision, saved_tesseract = ocr_backends.capabilities, ocr_backends.vision, ocr_backends.tesseract
    try:
        ocr_backends.capabilities = lambda: {'vision': True, 'tesseract': 'test-only'}
        def failed_vision(*args):
            raise RuntimeError('synthetic unavailable Vision runtime')
        ocr_backends.vision = failed_vision
        ocr_backends.tesseract = lambda *args: {'coordinate_space': 'pixels', 'blocks': [{'text': 'Fallback', 'bbox': [1, 1, 4, 4]}]}
        result = ocr_backends.run('synthetic.png', ['en'], 10, 10, 'auto', work)
        assert result['blocks'][0]['text'] == 'Fallback'
        assert any('ocr_auto_failed:vision' in w for w in result['warnings'])
    finally:
        ocr_backends.capabilities, ocr_backends.vision, ocr_backends.tesseract = saved_cap, saved_vision, saved_tesseract
    return {'status': 'passed', 'checks': ['source color/region analysis', 'complete worklist and contact sheets',
            'manual plan notes preserved', 'visual evidence required', 'stable timestamps', 'layout edits invalidate review',
            'reject review flags in patches', 'reject source-comparison capture', 'pixel difference and worst regions',
            'large differences block layout approval', 'current evidence gate', 'renderer edits invalidate evidence',
            'OCR/manual-layout synchronization', 'reject distorted captures', 'unresolved source differences block acceptance', 'OCR route fallback'],
            'scope': 'Synthetic component checks; does not claim an arbitrary PDF was fully reconstructed.'}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path)
    args = parser.parse_args()
    if args.out:
        args.out.mkdir(parents=True, exist_ok=True)
        result = checks(args.out.resolve())
    else:
        with tempfile.TemporaryDirectory(prefix='replica-fidelity-tests-') as tmp:
            result = checks(Path(tmp))
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
