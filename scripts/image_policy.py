"""Conservative raster classification shared by extraction, refresh and audit.

Geometry flags likely scans; it cannot establish that pixels are an illustration.
Only explicitly reviewed, isolated artwork may enter normal web content.
"""
import math


def image_rect(image):
    boxes = []
    bbox = image.get('bbox')
    if isinstance(bbox, (list, tuple)) and len(bbox) == 4:
        boxes.append(list(bbox))
    matrix = image.get('matrix')
    if isinstance(matrix, (list, tuple)) and len(matrix) == 6:
        if not all(isinstance(v, (float, int)) and math.isfinite(v) for v in matrix):
            return None
        a, b, c, d, e, f = matrix
        corners = [(e, f), (a + e, b + f), (c + e, d + f), (a + c + e, b + d + f)]
        boxes.append([min(p[0] for p in corners), min(p[1] for p in corners),
                      max(p[0] for p in corners), max(p[1] for p in corners)])
    if not boxes or not all(isinstance(v, (float, int)) and math.isfinite(v) for box in boxes for v in box):
        return None
    return [min(box[0] for box in boxes), min(box[1] for box in boxes),
            max(box[2] for box in boxes), max(box[3] for box in boxes)]


def clipped_rect(image, width, height):
    box = image_rect(image)
    if box is None or width <= 0 or height <= 0:
        return None
    x0, y0, x1, y1 = box
    box = [max(0, x0), max(0, y0), min(width, x1), min(height, y1)]
    return box if box[2] > box[0] and box[3] > box[1] else None


def union_area(boxes):
    """Rectangle union, so overlapping images are not counted twice."""
    xs = sorted({x for box in boxes for x in (box[0], box[2])})
    area = 0
    for left, right in zip(xs, xs[1:]):
        intervals = sorted((b[1], b[3]) for b in boxes if b[0] < right and b[2] > left)
        covered = 0
        end = -math.inf
        for low, high in intervals:
            covered += max(0, high - max(low, end))
            end = max(end, high)
        area += (right - left) * covered
    return area


def scan_flags(images, width, height):
    boxes = [clipped_rect(im, width, height) for im in images]
    union = union_area([b for b in boxes if b]) / max(1, width * height)
    grouped_scan = union >= .5
    flags = []
    for box in boxes:
        if not box:
            flags.append('invalid_image_geometry')
            continue
        w, h = box[2] - box[0], box[3] - box[1]
        if w * h / max(1, width * height) >= .5 or (w / width >= .6 and h / height >= .6):
            flags.append('page_scan_or_large_raster')
        elif grouped_scan:
            flags.append('possible_tiled_page_scan')
        else:
            flags.append(None)
    return flags, union


def image_approved(image, reason):
    return not reason and image.get('role') == 'illustration' and image.get('reviewed') is True


def enforce_image_policy(data):
    """Migrate legacy images without deleting files or discarding text/manual edits."""
    images = data.get('images', [])
    flags, _ = scan_flags(images, data['width'], data['height'])
    kept, excluded = [], data.setdefault('excluded_images', [])
    warnings = data.setdefault('warnings', [])
    changed = False
    for image, reason in zip(images, flags):
        if reason or image.get('role') in ('page_scan', 'reference'):
            reason = reason or 'page_scan_or_reference'
            excluded.append({**image, 'role': 'reference', 'exclusion_reason': reason})
            changed = True
        else:
            if not image_approved(image, reason):
                if image.get('role') != 'illustration_candidate' or image.get('reviewed') is not False:
                    image = {**image, 'role': 'illustration_candidate', 'reviewed': False}
                    changed = True
            kept.append(image)
    data['images'] = kept
    if excluded:
        warnings.append('page_rasters_excluded_from_web_content')
    if any(not image_approved(im, None) for im in kept):
        warnings.append('illustration_candidates_require_source_review')
    if changed:
        data['review'] = {k: False for k in ('text', 'layout', 'fonts', 'languages')}
        if data.get('status') not in ('error', 'needs_ocr', 'blank'):
            data['status'] = 'draft'
    data['warnings'] = sorted(set(warnings))
    return changed
