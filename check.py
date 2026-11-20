#!/usr/bin/env python3
"""
Check the fonts of dist/ hold what their users count on

  python check.py
"""
import sys
from pathlib import Path

from fontTools.ttLib import TTFont

DIST = Path(__file__).resolve().parent / 'dist'
failures = []


def expect(condition, message):
    if not condition:
        failures.append(message)


color = TTFont(DIST / 'CarboneEmoji-Color.ttf')
mono = TTFont(DIST / 'CarboneEmoji-Mono.ttf')
upem = color['head'].unitsPerEm

for font, name in ((color, 'Color'), (mono, 'Mono')):
    cmap = font.getBestCmap()
    expect(0x1F6B2 in cmap, name + ': no bicycle')
    expect(0xFE0F not in cmap, name + ': U+FE0F is mapped')
    expect(font['hhea'].ascent == round(0.864 * upem) and font['hhea'].descent == -round(0.206 * upem), name + ': line metrics')
    airplane = font['hmtx'][cmap[0x2708]][0] / upem
    walking = font['hmtx'][cmap[0x1F6B6]][0] / upem
    expect(abs(airplane - 1.363) < 0.02, name + ': airplane advances by %.3f em, Word 1.363' % airplane)
    expect(abs(walking - 0.913) < 0.02, name + ': person walking advances by %.3f em, Word 0.913' % walking)
    expect(font['name'].getDebugName(1) == 'Carbone Emoji ' + name, name + ': family name')

# fontkit, which pdfkit draws with, fails on a composite glyph in a font holding COLR
glyf = color['glyf']
expect(not any(glyf[n].isComposite() for n in color.getGlyphOrder()), 'Color: composite glyphs')
colr = color['COLR']
expect(colr.version == 0, 'Color: COLR version %d' % colr.version)
expect(len(colr.ColorLayers) > 3000, 'Color: %d color glyphs' % len(colr.ColorLayers))
expect('COLR' not in mono, 'Mono: COLR table')
# the flags are drawn in color alone: their regional indicators and tags are the only
# characters the outlines leave out
extra = set(color.getBestCmap()) - set(mono.getBestCmap())
expect(set(mono.getBestCmap()) <= set(color.getBestCmap()), 'the outlines map characters the colors do not')
expect(all(0x1F1E6 <= c <= 0x1F1FF or 0xE0020 <= c <= 0xE007F for c in extra), 'the colors alone map %s' % sorted(hex(c) for c in extra)[:5])
# the flag of France is one glyph of the colors, the two regional indicators ligated
gsub = color['GSUB'].table
ligatures = {}
for lookup in gsub.LookupList.Lookup:
    for table in lookup.SubTable:
        for first, sets in getattr(table, 'ligatures', {}).items():
            for ligature in sets:
                ligatures[(first,) + tuple(ligature.Component)] = ligature.LigGlyph
cmap = color.getBestCmap()
expect((cmap[0x1F1EB], cmap[0x1F1F7]) in ligatures, 'Color: no flag of France')
france = ligatures.get((cmap[0x1F1EB], cmap[0x1F1F7]))
expect(france is not None and abs(color['hmtx'][france][0] / upem - 1.36) < 0.02, 'Color: the flag of France advances by another width')

for failure in failures:
    print('FAIL', failure)
print('%d color glyphs, %d characters' % (len(colr.ColorLayers), len(color.getBestCmap())))
sys.exit(1 if failures else 0)
