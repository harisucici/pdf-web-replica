"""Versioned render evidence and pixel diagnostics, never a fidelity percentage."""
import hashlib
import json
import math
import re
import shutil
import time
from pathlib import Path

RENDER_FIELDS = ('page', 'width', 'height', 'rotation', 'kind', 'blocks', 'shapes',
                 'images', 'web_layout', 'background_color', 'text', 'layout_needs_sync')
CHECKS = ('text', 'layout', 'fonts', 'languages')


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def contained(root, value):
    target = (Path(root) / value).resolve()
    if not target.is_relative_to(Path(root).resolve()):
        raise ValueError('asset_path_outside_site: ' + value)
    return target


def fingerprint(out, data):
    site = Path(out) / 'site'
    payload = {k: data.get(k) for k in RENDER_FIELDS}
    assets = {}
    for name in ('index.html', 'reader.css', 'reader.js'):
        path = site / name
        if path.exists():
            content = re.sub(r'([?&]v=)[0-9.]+', r'\1BUILD', path.read_text(encoding='utf-8'))
            assets[name] = hashlib.sha256(content.encode()).hexdigest()
        else:
            assets[name] = 'missing'
    files = {im['file'] for im in data.get('images', []) if im.get('file')}
    files.update(b['font_file'] for b in data.get('blocks', []) if b.get('font_file'))
    for name in sorted(files):
        path = contained(site, name)
        assets[name] = sha(path) if path.is_file() else 'missing'
    payload['assets'] = assets
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False,
                                      allow_nan=False).encode()).hexdigest()


def evidence_issue(out, data, require_threshold=True):
    out = Path(out)
    report = out / 'qa' / 'comparisons' / f"{data['page']:05}.json"
    if not report.exists():
        return 'visual_evidence_missing'
    try:
        record = json.loads(report.read_text(encoding='utf-8'))
        if record.get('render_fingerprint') != fingerprint(out, data):
            return 'visual_evidence_stale'
        if record.get('source_sha256') != json.loads((out / 'manifest.json').read_text())['source_sha256']:
            return 'visual_evidence_wrong_document'
        reference = out / 'references' / f"{data['page']:05}.png"
        capture = contained(out / 'qa', record['capture'])
        if sha(reference) != record['reference_sha256'] or sha(capture) != record['capture_sha256']:
            return 'visual_evidence_file_changed'
        if require_threshold and record.get('status') != 'within_threshold':
            return 'visual_difference_needs_revision'
    except (ValueError, KeyError, OSError):
        return 'visual_evidence_invalid'
    return None


def pillow():
    try:
        from PIL import Image, ImageChops, ImageDraw, ImageStat
    except ImportError as error:
        raise ValueError('Pillow missing: run scripts/bootstrap.py --venv work/.pdf-web-env') from error
    return Image, ImageChops, ImageDraw, ImageStat


def compare_page(out, data, capture_dir):
    Image, ImageChops, ImageDraw, ImageStat = pillow()
    out, capture_dir = Path(out), Path(capture_dir)
    no = data['page']
    stem = f'{no:05}'
    sidecar = capture_dir / (stem + '.json')
    if not sidecar.exists():
        raise ValueError('capture_metadata_missing: ' + str(sidecar))
    meta = json.loads(sidecar.read_text(encoding='utf-8'))
    current = fingerprint(out, data)
    if meta.get('page') != no or meta.get('render_fingerprint') != current:
        raise ValueError('capture_is_stale_or_wrong_page')
    if meta.get('default_view') is not True or meta.get('page_only') is not True or meta.get('ready') is not True or meta.get('search_active'):
        raise ValueError('capture_must_be_ready_default_web_page_only')
    if not meta.get('captured_with'):
        raise ValueError('capture_tool_description_required')
    if data['kind'] != 'blank' and not meta.get('visible_text_elements', 0):
        raise ValueError('capture_has_no_visible_selectable_text')
    candidate = next((capture_dir / (stem + ext) for ext in ('.png', '.jpg', '.jpeg')
                      if (capture_dir / (stem + ext)).is_file()), None)
    if candidate is None:
        raise ValueError('page_capture_missing: ' + stem)
    reference_path = out / 'references' / (stem + '.png')
    with Image.open(reference_path) as im:
        reference = im.convert('RGB')
    with Image.open(candidate) as im:
        rendered = im.convert('RGB')
    width, height = rendered.size
    if min(width, height) < 64 or width * height > 36_000_000:
        raise ValueError('capture_resolution_out_of_bounds')
    expected_ratio = data['width'] / data['height']
    if abs(width / height / expected_ratio - 1) > .005:
        raise ValueError('capture_not_cropped_to_page_aspect_ratio')
    if abs(reference.width / reference.height / expected_ratio - 1) > .005:
        raise ValueError('source_reference_geometry_mismatch')
    reference_original_size = reference.size
    # Only the source is resampled to the browser capture scale, never the capture.
    reference = reference.resize(rendered.size, Image.Resampling.LANCZOS)
    diff = ImageChops.difference(reference, rendered)
    channels = diff.split()
    max_delta = ImageChops.lighter(ImageChops.lighter(channels[0], channels[1]), channels[2])
    tolerance = 24
    mask = max_delta.point(lambda v: 255 if v > tolerance else 0)
    changed = mask.histogram()[255] / (width * height)
    mean_error = sum(ImageStat.Stat(diff).mean) / (3 * 255)
    tiles = []
    grid = 8
    for row in range(grid):
        for col in range(grid):
            box = (col * width // grid, row * height // grid,
                   (col + 1) * width // grid, (row + 1) * height // grid)
            tile = mask.crop(box)
            ratio = tile.histogram()[255] / (tile.width * tile.height)
            tiles.append({'bbox_pixels': list(box), 'changed_ratio': round(ratio, 6)})
    worst = max(t['changed_ratio'] for t in tiles)
    within = changed <= .01 and mean_error <= .005 and worst <= .10
    qa = out / 'qa'
    directory = qa / 'comparisons'
    directory.mkdir(parents=True, exist_ok=True)
    captures = qa / 'captures'
    captures.mkdir(exist_ok=True)
    screenshot_hash = sha(candidate)
    saved = captures / (stem + '-' + screenshot_hash[:16] + candidate.suffix.lower())
    if candidate.resolve() != saved.resolve():
        shutil.copyfile(candidate, saved)
    overlay = Image.blend(reference, rendered, .5)
    heat = Image.new('RGB', rendered.size, 'white')
    heat.paste(Image.new('RGB', rendered.size, '#c83232'), mask=mask)
    overlay.save(directory / (stem + '-overlay.png'))
    heat.save(directory / (stem + '-diff.png'))
    board = Image.new('RGB', (width * 2, height + 32), 'white')
    draw = ImageDraw.Draw(board)
    draw.text((10, 8), 'SOURCE', fill='black')
    draw.text((width + 10, 8), 'WEB', fill='black')
    board.paste(reference, (0, 32))
    board.paste(rendered, (width, 32))
    board.save(directory / (stem + '-side-by-side.png'))
    result = {'page': no, 'render_fingerprint': current,
              'source_sha256': json.loads((out / 'manifest.json').read_text())['source_sha256'],
              'reference_sha256': sha(reference_path), 'capture_sha256': screenshot_hash,
              'capture': str(saved.relative_to(qa)), 'captured_with': meta['captured_with'],
              'status': 'within_threshold' if within else 'needs_revision',
              'reference_original_size': list(reference_original_size),
              'capture_size': [width, height], 'source_resampled': reference_original_size != rendered.size,
              'metrics': {'changed_pixel_ratio': round(changed, 6), 'normalized_mean_error': round(mean_error, 6),
                          'worst_tile_ratio': worst, 'channel_tolerance': tolerance},
              'thresholds': {'changed_pixel_ratio': .01, 'normalized_mean_error': .005, 'worst_tile_ratio': .10},
              'worst_regions': sorted(tiles, key=lambda t: t['changed_ratio'], reverse=True)[:8],
              'time': time.time(),
              'note': 'Pixel diagnostics are not a reconstruction percentage or proof of correct Unicode, fonts or meaning.'}
    (directory / (stem + '.json')).write_text(json.dumps(result, indent=2), encoding='utf-8')
    return result
