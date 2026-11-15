"""Source-driven region candidates and a complete reconstruction worklist.

This analyzes raster colors/geometry; it does not infer words, fonts, or approval.
Candidate regions are never automatically inserted into the published site.
"""
import hashlib
import json
import math
from collections import Counter, deque
from pathlib import Path
import fidelity


def regions(reference, page_width, page_height):
    Image, _, _, _ = fidelity.pillow()
    with Image.open(reference) as im:
        image = im.convert('RGB')
    image.thumbnail((320, 480), Image.Resampling.LANCZOS)
    indexed = image.quantize(colors=16)
    width, height = indexed.size
    pixels = list(indexed.getdata())
    palette = indexed.getpalette()
    colors = {i: tuple(palette[i * 3:i * 3 + 3]) for i in set(pixels)}
    common = Counter(pixels)
    seen = bytearray(width * height)
    output = []
    for seed in range(width * height):
        if seen[seed]:
            continue
        key = pixels[seed]
        seen[seed] = 1
        rgb = colors[key]
        queue = deque([seed])
        count = 0
        x0 = x1 = seed % width
        y0 = y1 = seed // width
        while queue:
            at = queue.popleft()
            x, y = at % width, at // width
            count += 1
            x0, x1, y0, y1 = min(x0, x), max(x1, x), min(y0, y), max(y1, y)
            for neighbor in (at - width if y else -1, at + width if y + 1 < height else -1,
                             at - 1 if x else -1, at + 1 if x + 1 < width else -1):
                if neighbor >= 0 and not seen[neighbor] and pixels[neighbor] == key:
                    seen[neighbor] = 1
                    queue.append(neighbor)
        rw, rh = x1 - x0 + 1, y1 - y0 + 1
        area = count / (width * height)
        occupancy = count / (rw * rh)
        if min(rgb) > 248:
            continue
        if rw >= width * .12 and rh <= 3 and count >= width * .08:
            kind = 'horizontal_rule_candidate'
        elif rh >= height * .12 and rw <= 3 and count >= height * .08:
            kind = 'vertical_rule_candidate'
        elif area >= .006 and occupancy >= .65 and min(rw, rh) >= 5:
            kind = 'panel_candidate'
        else:
            continue
        box = [x0 / width * page_width, y0 / height * page_height,
               (x1 + 1) / width * page_width, (y1 + 1) / height * page_height]
        output.append({'kind': kind, 'bbox': [round(v, 3) for v in box],
                       'color': '#%02x%02x%02x' % rgb, 'occupancy': round(occupancy, 3),
                       'requires_source_review': True})
    return {'analysis_size': [width, height], 'candidates': output,
            'palette': [{'color': '#%02x%02x%02x' % colors[i], 'area_ratio': round(n / len(pixels), 4)}
                        for i, n in common.most_common(8)],
            'limitations': 'Color components are provisional. Inspect rounded corners, borders, gradients, text holes and artwork; never trace glyphs from these components.'}


def analyze(out, selected, write_json):
    Image, _, ImageDraw, _ = fidelity.pillow()
    out = Path(out)
    manifest = json.loads((out / 'manifest.json').read_text(encoding='utf-8'))
    prior_path = out / 'reconstruction-plan.json'
    prior = json.loads(prior_path.read_text(encoding='utf-8')) if prior_path.exists() else {}
    entries = {p['page']: p for p in prior.get('pages', [])}
    directory = out / 'analysis'
    directory.mkdir(exist_ok=True)
    for no in selected:
        page_path = out / 'pages' / f'{no:05}.json'
        ref = out / 'references' / f'{no:05}.png'
        if not page_path.exists() or not ref.exists():
            entries[no] = {**entries.get(no, {}), 'page': no, 'state': 'missing_page_or_reference'}
            continue
        page = json.loads(page_path.read_text(encoding='utf-8'))
        facts = regions(ref, page['width'], page['height'])
        facts.update(page=no, reference_sha256=fidelity.sha(ref))
        write_json(directory / f'{no:05}.json', facts)
        signature = [round(page['width'] / page['height'], 2), page['kind'],
                     sorted((c['kind'], tuple(round(v / (page['width'] if i % 2 == 0 else page['height']), 1)
                                             for i, v in enumerate(c['bbox'])))
                            for c in facts['candidates'])]
        family = hashlib.sha256(json.dumps(signature).encode()).hexdigest()[:10]
        old = entries.get(no, {})
        tasks = ['verify_text_and_all_languages', 'match_fonts_and_small_annotations',
                 'compare_default_web_render', 'resolve_local_differences']
        if page['kind'] in ('scan', 'hybrid', 'image-or-scan', 'outlined-or-graphics', 'invalid-text-map'):
            tasks.insert(0, 'rebuild_panels_rules_labels_and_isolated_artwork')
        if page['status'] in ('needs_ocr', 'error'):
            tasks.insert(0, 'resolve_' + page['status'])
        entries[no] = {**old, 'page': no, 'family': old.get('family_override', family),
                       'state': 'draft', 'analysis': f'analysis/{no:05}.json', 'tasks': tasks,
                       'review': page.get('review', {})}
    families = {}
    for p in entries.values():
        if p.get('family'):
            families.setdefault(p['family'], []).append(p['page'])
    # All selected pages remain in the ledger, including unanalyzed and failed pages.
    for no in manifest['selected_pages']:
        entries.setdefault(no, {'page': no, 'state': 'not_analyzed'})
    result = {'source_sha256': manifest['source_sha256'], 'pages': sorted(entries.values(), key=lambda x: x['page']),
              'families': families, 'note': 'Families are hints, not proof of identical pages. Reuse structure only; verify every page, including exceptions.'}
    write_json(prior_path, result)
    # Small contact sheets are working references, never site/background assets.
    for start in range(0, len(selected), 24):
        batch = selected[start:start + 24]
        board = Image.new('RGB', (4 * 180, math.ceil(len(batch) / 4) * 250), '#ecebe7')
        draw = ImageDraw.Draw(board)
        for i, no in enumerate(batch):
            x, y = i % 4 * 180, i // 4 * 250
            ref = out / 'references' / f'{no:05}.png'
            draw.text((x + 8, y + 8), f'PDF {no}', fill='black')
            if ref.exists():
                with Image.open(ref) as image:
                    thumb = image.convert('RGB')
                    thumb.thumbnail((164, 218), Image.Resampling.LANCZOS)
                    board.paste(thumb, (x + 8, y + 26))
        board.save(directory / f'contact-{start // 24 + 1:03}.jpg')
    return {'analyzed_pages': len(selected), 'families': len(families), 'plan': str(prior_path), 'status': 'draft'}
