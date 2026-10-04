# -*- coding: utf-8 -*-
"""Build docs/icons/icon-maskable-512.png from the plain 512.

WHY A SEPARATE FILE AND NOT A LABEL. The manifest used to declare the one 512
icon as `"purpose": "any maskable"`, which tells Android it may crop the image
to a circle or a squircle. That artwork runs edge to edge: sky at the top,
sand at the bottom, the truck's wheels almost touching the sides. Cropped to
the maskable safe zone, which is the middle 80 percent, the wheels and the sun
both lose their edges. Labelling an unpadded icon maskable does not make it
maskable, it just licenses the phone to cut into it.

Landfall, Hok Gong and CitySteps Reader all ship a dedicated
`icon-maskable-512.png`, so this brings Coilover Remastered into line with
them and with rule 6.

HOW. The picture is scaled to 76 percent and centred, which puts the truck and
the sun inside the safe circle, and the margin is filled by stretching the
outermost row and column of pixels outward. That matters: a flat colour border
would read as a frame sitting around a smaller picture, whereas continuing the
sky upward and the sand downward looks like the same scene with more room.

Run it again if the icon is ever redrawn.
"""
import os
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ICONS = os.path.join(HERE, '..', 'docs', 'icons')
SRC = os.path.join(ICONS, 'icon-512.png')
OUT = os.path.join(ICONS, 'icon-maskable-512.png')

S = 512
INNER = 0.76                      # the safe circle is the middle 80 percent

src = Image.open(SRC).convert('RGB')
if src.size != (S, S):
    src = src.resize((S, S), Image.LANCZOS)

side = int(round(S * INNER))
pad = (S - side) // 2
small = src.resize((side, side), Image.LANCZOS)

canvas = Image.new('RGB', (S, S))

# bleed: stretch the picture's own edges out into the margin, so the sky keeps
# going up and the sand keeps going down instead of meeting a border
top = small.crop((0, 0, side, 1)).resize((side, pad), Image.NEAREST)
bot = small.crop((0, side - 1, side, side)).resize((side, S - pad - side), Image.NEAREST)
canvas.paste(top, (pad, 0))
canvas.paste(small, (pad, pad))
canvas.paste(bot, (pad, pad + side))
left = canvas.crop((pad, 0, pad + 1, S)).resize((pad, S), Image.NEAREST)
right = canvas.crop((pad + side - 1, 0, pad + side, S)).resize((S - pad - side, S), Image.NEAREST)
canvas.paste(left, (0, 0))
canvas.paste(right, (pad + side, 0))

canvas.save(OUT, 'PNG', optimize=True)
print('wrote %s  %d bytes  (content inset to %d%%)'
      % (os.path.relpath(OUT, HERE), os.path.getsize(OUT), round(INNER * 100)))
