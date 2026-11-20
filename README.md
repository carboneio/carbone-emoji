# Carbone Emoji

Two emoji fonts built from [Microsoft Fluent Emoji](https://github.com/microsoft/fluentui-emoji)
(MIT), made to draw emoji in a PDF the way Microsoft Word does with Segoe UI Emoji on
Windows 11. They are the fonts [Carbone](https://carbone.io) falls back on when a document
writes an emoji its own font has no glyph for.

| File | Format | Drawn from | Used for |
|---|---|---|---|
| `CarboneEmoji-Color.ttf` | COLR v0 / CPAL | Fluent Emoji *Flat* | an emoji written in the automatic color |
| `CarboneEmoji-Mono.ttf` | plain TrueType outlines | Fluent Emoji *High Contrast* | an emoji written in a color of its own |

Word draws an emoji in color only when its text is in the automatic color, and in one color,
the color of the text, otherwise: hence two fonts.

## Flags

Fluent Emoji, like Segoe UI Emoji, draws no flag of a country. Every other system does, so
the color font draws them after [flag-icons](https://github.com/lipis/flag-icons) (MIT): the
258 flags of countries and regions of Unicode and those of England, Scotland and Wales, at
4 by 3, their corners rounded and their edge drawn so that a white flag reads on white
paper. Ascension, Tristan da Cunha and Ceuta & Melilla are drawn with the flag they fly.
Sark, which flag-icons does not draw, is the one flag left out.

The flags are in the color font only: a text in a color of its own draws them in color all
the same, as every system drawing flags does.

## Why COLR v0

A COLR v0 glyph is a stack of glyphs of one solid color each. Word writes those layers into
the PDF it exports one by one, each in its color, so the emoji stays vector, sharp at any
zoom, light, and its text can be copied. Bitmap formats (sbix, CBDT) and gradients (COLR v1,
OT-SVG) are what most PDF libraries cannot draw.

The few gradients of the Flat art (3 files) are replaced by the mean of their stops.

## Metrics

Measured on PDF Word exported with Segoe UI Emoji, at 12 and 20 points:

- the ink of a glyph as tall as the art allows runs from 0.206 em below the baseline to
  0.864 em above it, which is also the height of the line (`hhea`, `OS/2` typo and win);
- a glyph advances by its ink and 0.146 em on either side, never more than 1.375 em.

Both fonts give an emoji the same advance, so that a text lays out alike in either.

## Sequences

Skin tones, ZWJ sequences and keycaps are ligatures of the font. Variation selectors are
not: U+FE0F is dropped from every sequence, as Noto Color Emoji does, and a text is shaped
with U+FE0E and U+FE0F removed, once they have been read to pick text or emoji presentation.


## Build

```sh
./fetch.sh                                  # the SVG of fluentui-emoji and flag-icons at the commits of UPSTREAM.txt
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python build.py                   # dist/CarboneEmoji-Color.ttf, dist/CarboneEmoji-Mono.ttf
```

The build takes about fifteen minutes. The version of the fonts is in `VERSION`.

## License

MIT, see [LICENSE](LICENSE). Microsoft, Fluent and Segoe are trademarks of Microsoft
Corporation; this project is not affiliated with or endorsed by Microsoft.
