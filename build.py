#!/usr/bin/env python3
"""
Build Carbone Emoji from the SVG of Microsoft Fluent Emoji

  python build.py            # writes dist/CarboneEmoji-Color.ttf and dist/CarboneEmoji-Mono.ttf

Two fonts, drawn the way Microsoft Word draws emoji with Segoe UI Emoji on Windows 11:

- CarboneEmoji-Color.ttf, COLR v0: every emoji is a stack of glyphs of one solid color each,
  made of the "Flat" art. Word writes those layers into a PDF one by one, each in its color.
- CarboneEmoji-Mono.ttf, plain outlines: what Word draws instead when the run sets a color of
  its own, made of the "High Contrast" art.

The flags of the countries, and of England, Scotland and Wales, which Fluent Emoji draws none
of, are drawn after flag-icons (MIT): 4 by 3, on the box of an emoji as tall as the art
allows, their corners rounded and their edge drawn, so that a white flag still reads on
white paper. They are drawn in color only, as every system but Windows draws them.

Metrics, measured on PDF Word exported (Segoe UI Emoji, 12 and 20 points):

- the ink of a glyph as tall as the art allows runs from 0.206 em below the baseline to
  0.864 em above it, which is also how tall a line holding nothing but emoji stands;
- a glyph advances by its ink and 0.146 em on either side, never more than 1.375 em: the
  airplane by 1.363 em, the person walking by 0.913 em.

Both fonts give an emoji the same advance, read off the Flat art, so that a text lays out
alike whichever of the two draws it.

Variation selectors are not part of the sequences of the font, U+FE0F being dropped from
every one of them as Noto Color Emoji does: whoever shapes a text with these fonts strips
U+FE0E and U+FE0F first, having used them to pick the presentation.
"""
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from xml.etree import ElementTree

import pathops
from fontTools.pens.recordingPen import DecomposingRecordingPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont
from picosvg.svg import SVG
from picosvg.svg_types import SVGPath
from picosvg import svg_pathops

HERE = Path(__file__).resolve().parent
ASSETS = HERE / 'upstream' / 'fluentui-emoji' / 'assets'
FLAGS = HERE / 'upstream' / 'flag-icons' / 'flags' / '4x3'
WORK = HERE / 'build'
DIST = HERE / 'dist'

FAMILY = 'Carbone Emoji'
UPEM = 2048
# the art of Fluent is drawn on 32 units, a glyph as tall as it goes on 28 of them (2 to 30)
ART = 32.0
EM_PER_UNIT = (0.864 + 0.206) / 28
ASCENDER = round((0.864 + 2 * EM_PER_UNIT) * UPEM)
DESCENDER = -round((0.206 + 2 * EM_PER_UNIT) * UPEM)
# the line a font of emoji asks for, the ink of the tallest glyph
LINE_ASCENT = round(0.864 * UPEM)
LINE_DESCENT = round(0.206 * UPEM)
SIDE_BEARING = 0.146 / EM_PER_UNIT
WIDEST = 1.375 / EM_PER_UNIT

SKIN_TONES = {
    'Light': '1f3fb', 'Medium-Light': '1f3fc', 'Medium': '1f3fd', 'Medium-Dark': '1f3fe', 'Dark': '1f3ff'
}
VARIATION_SELECTORS = {'fe0e', 'fe0f'}
SVG_NS = 'http://www.w3.org/2000/svg'
XLINK_NS = 'http://www.w3.org/1999/xlink'
ElementTree.register_namespace('', SVG_NS)
ElementTree.register_namespace('xlink', XLINK_NS)

# The regions Unicode names a flag for which flag-icons files under another name: Ascension
# and Tristan da Cunha under Saint Helena, Ceuta and Melilla under Spain, whose flag they fly
FLAG_OF_REGION = {'ac': 'sh-ac', 'ta': 'sh-ta', 'ea': 'es'}
# the flags of a subdivision, UTS #51 §1.4.6: a black flag, the tags of the region, a cancel tag
SUBDIVISIONS = {'gbeng': 'gb-eng', 'gbsct': 'gb-sct', 'gbwls': 'gb-wls'}
# where a flag stands in the 32 units of the art, as wide as the widest emoji draws: x, y,
# width, height, the radius of its corners, and the line drawn round it
FLAG_BOX = (2.0, 5.5, 28.0, 21.0)
FLAG_CORNER = 1.5
FLAG_EDGE = {'fill': 'none', 'stroke': '#000000', 'stroke-opacity': '0.15', 'stroke-width': '0.5'}


def sequence_of(text):
    return [cp for cp in text.lower().split() if cp not in VARIATION_SELECTORS]


def first_svg(directory):
    found = sorted(directory.glob('*.svg')) if directory.is_dir() else []
    return found[0] if found else None


def emoji_of_assets():
    """Every emoji: its sequence, its Flat art and its High Contrast art"""
    out = {}
    for asset in sorted(ASSETS.iterdir()):
        meta_file = asset / 'metadata.json'
        if not meta_file.is_file():
            continue
        meta = json.loads(meta_file.read_text(encoding='utf-8'))
        tones = meta.get('unicodeSkintones')
        if tones and (asset / 'Default').is_dir():
            mono = first_svg(asset / 'Default' / 'High Contrast')
            for tone_dir in sorted(asset.iterdir()):
                if not tone_dir.is_dir():
                    continue
                tone = SKIN_TONES.get(tone_dir.name)
                matching = [t for t in tones if (tone is None and not any(v in t for v in SKIN_TONES.values()))
                            or (tone is not None and tone in t.split())]
                if not matching:
                    continue
                add(out, sequence_of(matching[0]), first_svg(tone_dir / 'Flat'), mono, asset.name)
        else:
            add(out, sequence_of(meta['unicode']), first_svg(asset / 'Flat'), first_svg(asset / 'High Contrast'), asset.name)
    return out


def add(out, sequence, flat, mono, name):
    if not sequence or flat is None:
        print('  skipped', name, file=sys.stderr)
        return
    key = tuple(sequence)
    if key in out:
        print('  twice', name, '_'.join(key), file=sys.stderr)
        return
    out[key] = (flat, mono)


def rgb_of(color):
    """#rgb or #rrggbb as three numbers, None for anything else"""
    color = (color or '').strip()
    if re.match(r'^#[0-9A-Fa-f]{3}$', color):
        return tuple(int(color[i] * 2, 16) for i in (1, 2, 3))
    if re.match(r'^#[0-9A-Fa-f]{6}$', color):
        return tuple(int(color[i:i + 2], 16) for i in (1, 3, 5))
    return None


def flatten_gradients(root):
    """A gradient filling a shape, which COLR v0 has no room for, becomes the mean of its stops

    A gradient may take its stops from another one it names, SVG 1.1 §13.2.2 xlink:href.
    """
    gradients = {g.get('id'): g for g in root.iter() if g.tag.split('}')[-1] in ('linearGradient', 'radialGradient')}

    def stops_of(gradient, depth=0):
        stops = [s for s in gradient if s.tag.split('}')[-1] == 'stop']
        named = (gradient.get('{%s}href' % XLINK_NS) or gradient.get('href') or '').lstrip('#')
        if not stops and named in gradients and depth < 8:
            return stops_of(gradients[named], depth + 1)
        return stops

    means = {}
    for name, gradient in gradients.items():
        colors = []
        for stop in stops_of(gradient):
            style = dict(part.split(':', 1) for part in (stop.get('style') or '').split(';') if ':' in part)
            rgb = rgb_of(stop.get('stop-color') or style.get('stop-color'))
            if rgb is not None:
                colors.append(rgb)
        if colors:
            means[name] = '#%02X%02X%02X' % tuple(round(sum(c[i] for c in colors) / len(colors)) for i in range(3))
    for element in root.iter():
        for attribute in ('fill', 'stroke'):
            found = re.match(r'^url\(#([^)]+)\)$', element.get(attribute) or '')
            if found and found.group(1) in means:
                element.set(attribute, means[found.group(1)])
    return bool(means)


def regional(code):
    return tuple('%x' % (0x1F1E6 + ord(letter) - ord('a')) for letter in code)


def flags_of_regions():
    """Every flag flag-icons draws, under the sequence of Unicode writing it"""
    out = {}
    for flag in sorted(FLAGS.glob('*.svg')):
        if re.match(r'^[a-z]{2}$', flag.stem):
            out[regional(flag.stem)] = flag
    for region, name in FLAG_OF_REGION.items():
        out[regional(region)] = FLAGS / (name + '.svg')
    for tag, name in SUBDIVISIONS.items():
        out[('1f3f4',) + tuple('%x' % (0xE0000 + ord(letter)) for letter in tag) + ('e007f',)] = FLAGS / (name + '.svg')
    return out


def length_in_units(value):
    """A length an attribute states in points or pixels, as the number of units it is"""
    found = re.match(r'^\s*([-+]?[\d.]+)\s*(pt|px)\s*$', value or '')
    if found is None:
        return value
    return '%g' % (float(found.group(1)) * (4 / 3 if found.group(2) == 'pt' else 1))


def vertices_of(d):
    """The points a path goes through, in order, SVG 1.1 §11.6.2 the vertices markers stand on"""
    points, x, y = [], 0.0, 0.0
    for command, args in SVGPath(d=d).absolute(inplace=False).as_cmd_seq():
        if command == 'H':
            x = args[0]
        elif command == 'V':
            y = args[0]
        elif command in ('Z', 'z'):
            if points:
                x, y = points[0]
        else:
            x, y = args[-2], args[-1]
        points.append((x, y))
    return points


def markers_drawn(root):
    """The markers of the paths, SVG 1.1 §11.6, drawn as copies of what they hold

    picosvg draws none of them. A marker stands with its origin on its vertex, neither turned
    nor scaled, which is what the stars of flag-icons ask for: the default orient, refX and
    refY, on paths stroked by nothing.
    """
    markers = {m.get('id'): m for m in root.iter() if m.tag.split('}')[-1] == 'marker'}
    if not markers:
        return
    for parent in list(root.iter()):
        for index, path in reversed(list(enumerate(list(parent)))):
            uses = {attribute: path.get(attribute) for attribute in ('marker-start', 'marker-mid', 'marker-end') if path.get(attribute)}
            if not uses or path.get('d') is None:
                continue
            points = vertices_of(path.get('d'))
            for attribute, reference in uses.items():
                marker = markers.get(re.sub(r'^url\(#(.*)\)$', r'\1', reference))
                del path.attrib[attribute]
                if marker is None:
                    continue
                stands = points[1:-1] if attribute == 'marker-mid' else points[:1] if attribute == 'marker-start' else points[-1:]
                for x, y in stands:
                    copy = ElementTree.Element('{%s}g' % SVG_NS, {'transform': 'translate(%g %g)' % (x, y)})
                    copy.extend(ElementTree.fromstring(ElementTree.tostring(child)) for child in marker)
                    index += 1
                    parent.insert(index, copy)
    for parent in list(root.iter()):
        for child in list(parent):
            if child.tag.split('}')[-1] == 'marker':
                parent.remove(child)


def flag_svg(flag_file, target):
    """A flag as an emoji: on the box of FLAG_BOX, cut to its rounded corners, its edge drawn"""
    flag = ElementTree.parse(flag_file).getroot()
    flatten_gradients(flag)
    markers_drawn(flag)
    for element in flag.iter():
        if element.get('stroke-width') is not None:
            element.set('stroke-width', length_in_units(element.get('stroke-width')))
    vx, vy, vw, vh = (float(v) for v in flag.get('viewBox').split())
    x, y, w, h = FLAG_BOX
    box = {'x': str(x), 'y': str(y), 'width': str(w), 'height': str(h), 'rx': str(FLAG_CORNER)}
    root = ElementTree.Element('{%s}svg' % SVG_NS, {'viewBox': '0 0 %g %g' % (ART, ART)})
    defs = ElementTree.SubElement(root, '{%s}defs' % SVG_NS)
    clip = ElementTree.SubElement(defs, '{%s}clipPath' % SVG_NS, {'id': 'carbone-flag-box'})
    ElementTree.SubElement(clip, '{%s}rect' % SVG_NS, box)
    cut = ElementTree.SubElement(root, '{%s}g' % SVG_NS, {'clip-path': 'url(#carbone-flag-box)'})
    # what the flag states on its own root, fill-rule and the like, holds for all it draws
    kept = {k: v for k, v in flag.attrib.items() if k.split('}')[-1] not in ('viewBox', 'id', 'width', 'height', 'version')}
    kept['transform'] = 'translate(%g %g) scale(%g %g) translate(%g %g)' % (x, y, w / vw, h / vh, -vx, -vy)
    drawn = ElementTree.SubElement(cut, '{%s}g' % SVG_NS, kept)
    for child in list(flag):
        if child.tag.split('}')[-1] == 'defs':
            defs.extend(list(child))
        else:
            drawn.append(child)
    ElementTree.SubElement(root, '{%s}rect' % SVG_NS, dict(box, **FLAG_EDGE))
    ElementTree.ElementTree(root).write(target, encoding='unicode')


def advance_box(flat_file):
    """The viewBox, in units of the art, a glyph advances by: its ink and a bearing either side"""
    ink = SVG.parse(str(flat_file)).topicosvg().bounding_box()
    width = min(WIDEST, ink.w + 2 * SIDE_BEARING)
    middle = ink.x + ink.w / 2
    return (middle - width / 2, 0.0, width, ART)


def write_svg(root, box, target):
    root.set('viewBox', ' '.join('%.4f' % v for v in box))
    root.set('width', '%.4f' % box[2])
    root.set('height', '%.4f' % box[3])
    ElementTree.ElementTree(root).write(target, encoding='unicode')


def masks_as_clips(root):
    """A mask of the High Contrast art is an opaque shape cutting what it masks: a clip"""
    for element in root.iter():
        if element.tag.split('}')[-1] == 'mask':
            element.tag = '{%s}clipPath' % SVG_NS
            for attribute in ('style', 'maskUnits', 'x', 'y', 'width', 'height', 'fill'):
                element.attrib.pop(attribute, None)
        if element.get('mask') is not None:
            element.set('clip-path', element.attrib.pop('mask'))


def mono_svg(mono_file, box, target):
    """The High Contrast art as one outline: the dark shapes in, the white ones out, in order"""
    root = ElementTree.parse(mono_file).getroot()
    masks_as_clips(root)
    shapes = SVG.fromstring(ElementTree.tostring(root, encoding='unicode')).topicosvg().shapes()
    outline = pathops.Path()
    for shape in shapes:
        path = svg_pathops.skia_path(shape.as_cmd_seq(), shape.fill_rule)
        fill = (shape.fill or '').lower()
        hole = fill in ('white', '#fff', '#ffffff')
        outline = pathops.op(outline, path, pathops.PathOp.DIFFERENCE if hole else pathops.PathOp.UNION, fix_winding=True)
    outline.simplify(fix_winding=True)
    d = ' '.join(cmd + ' ' + ' '.join('%.3f' % v for v in args) for cmd, args in svg_pathops.svg_commands(outline))
    target.write_text('<svg xmlns="%s" viewBox="%s" width="%.4f" height="%.4f"><path d="%s"/></svg>'
                      % (SVG_NS, ' '.join('%.4f' % v for v in box), box[2], box[3], d), encoding='utf-8')


def nanoemoji(svgs, color_format, output):
    build_dir = WORK / ('nanoemoji-' + color_format)
    command = [str(Path(sys.executable).parent / 'nanoemoji'), '--family', FAMILY, '--color_format', color_format,
               '--upem', str(UPEM), '--ascender', str(ASCENDER), '--descender', str(DESCENDER), '--width', '0',
               '--noclip_to_viewbox', '--build_dir', str(build_dir), '--output_file', output.name] + [str(s) for s in svgs]
    # nanoemoji runs ninja, installed beside it
    env = dict(os.environ, PATH=str(Path(sys.executable).parent) + os.pathsep + os.environ.get('PATH', ''))
    subprocess.run(command, check=True, cwd=WORK, env=env)
    shutil.copy(build_dir / output.name, output)


def decompose_composites(font):
    """A shape nanoemoji reuses elsewhere, moved or scaled, becomes an outline of its own

    The glyph referring to another one is a composite glyph, which fontkit, and pdfkit with
    it, fails to draw in a font holding a COLR table: reading the component, it is handed
    a color glyph rather than an outline.
    """
    glyf = font['glyf']
    glyph_set = font.getGlyphSet()
    for name in font.getGlyphOrder():
        if glyf[name].isComposite():
            recording = DecomposingRecordingPen(glyph_set)
            glyph_set[name].draw(recording)
            pen = TTGlyphPen(None)
            recording.replay(pen)
            glyf[name] = pen.glyph()


def finish(font_file, style, description):
    """The names and the line metrics nanoemoji does not write"""
    font = TTFont(font_file)
    if 'COLR' in font:
        decompose_composites(font)
    font['hhea'].ascent = LINE_ASCENT
    font['hhea'].descent = -LINE_DESCENT
    font['hhea'].lineGap = 0
    os2 = font['OS/2']
    os2.sTypoAscender, os2.sTypoDescender, os2.sTypoLineGap = LINE_ASCENT, -LINE_DESCENT, 0
    os2.usWinAscent, os2.usWinDescent = LINE_ASCENT, LINE_DESCENT
    os2.fsSelection |= 1 << 7  # USE_TYPO_METRICS
    version = (HERE / 'VERSION').read_text().strip()
    commit = re.search(r'^fluentui-emoji \S+ (\S+)', (HERE / 'UPSTREAM.txt').read_text(), re.M).group(1)
    names = {
        0: 'Copyright (c) Microsoft Corporation (Fluent Emoji). Flags copyright (c) 2013 Panayiotis Lipiridis (flag-icons). Built by Carbone.',
        1: FAMILY + ' ' + style, 2: 'Regular', 3: 'CarboneEmoji-%s %s' % (style, version), 4: FAMILY + ' ' + style,
        5: 'Version ' + version, 6: 'CarboneEmoji-' + style,
        10: description + ' Built from microsoft/fluentui-emoji ' + commit[:12] + '.',
        13: 'MIT License, see https://github.com/carboneio/carbone-emoji/blob/main/LICENSE',
        16: FAMILY, 17: style,
    }
    table = font['name']
    table.names = [n for n in table.names if n.nameID not in names]
    for name_id, text in names.items():
        table.setName(text, name_id, 3, 1, 0x409)
    font.save(font_file)


def main():
    if not ASSETS.is_dir() or not FLAGS.is_dir():
        sys.exit('run ./fetch.sh first')
    shutil.rmtree(WORK, ignore_errors=True)
    (WORK / 'color').mkdir(parents=True)
    (WORK / 'mono').mkdir(parents=True)
    (WORK / 'flags').mkdir(parents=True)
    DIST.mkdir(exist_ok=True)
    emoji = emoji_of_assets()
    for sequence, flag in flags_of_regions().items():
        composed = WORK / 'flags' / ('emoji_u' + '_'.join(sequence) + '.svg')
        flag_svg(flag, composed)
        if sequence in emoji:
            print('  twice', flag.name, file=sys.stderr)
            continue
        emoji[sequence] = (composed, None)
    color_svgs, mono_svgs = [], []
    for sequence, (flat, mono) in sorted(emoji.items()):
        name = 'emoji_u' + '_'.join(sequence) + '.svg'
        box = advance_box(flat)
        root = ElementTree.parse(flat).getroot()
        flatten_gradients(root)
        write_svg(root, box, WORK / 'color' / name)
        color_svgs.append(WORK / 'color' / name)
        if mono is not None:
            mono_svg(mono, box, WORK / 'mono' / name)
            mono_svgs.append(WORK / 'mono' / name)
    print('%d emoji, %d of them in monochrome' % (len(color_svgs), len(mono_svgs)))
    description = ' Flags drawn after flag-icons.'

    nanoemoji(color_svgs, 'glyf_colr_0', DIST / 'CarboneEmoji-Color.ttf')
    finish(DIST / 'CarboneEmoji-Color.ttf', 'Color', 'Color emoji in COLR v0, drawn after Microsoft Fluent Emoji (Flat).' + description)
    nanoemoji(mono_svgs, 'glyf', DIST / 'CarboneEmoji-Mono.ttf')
    finish(DIST / 'CarboneEmoji-Mono.ttf', 'Mono', 'Monochrome emoji, drawn after Microsoft Fluent Emoji (High Contrast).')


if __name__ == '__main__':
    main()
