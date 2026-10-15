"""Download the elevation tiles render.py reads (AWS Terrain Tiles, terrarium encoding, zoom 12).

The tile range comes from bbox.txt: "x0 x1 y0 y1". Run from this folder: python3 fetch_tiles.py
"""
import os, urllib.request

x0, x1, y0, y1 = map(int, open('bbox.txt').read().split())
os.makedirs('tiles', exist_ok=True)
for x in range(x0, x1 + 1):
    for y in range(y0, y1 + 1):
        out = f'tiles/{x}_{y}.png'
        if os.path.exists(out):
            continue
        urllib.request.urlretrieve(f'https://s3.amazonaws.com/elevation-tiles-prod/terrarium/12/{x}/{y}.png', out)
        print(out)
