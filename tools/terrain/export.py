import json, numpy as np, math
from PIL import Image
import importlib.util, sys
m = json.load(open('manifest.json'))
L = {l['name']: l for l in m['layers']}
for n in ('mid', 'near'):
    w = np.asarray(Image.open(f'{n}_water.png').convert('L')) > 127
    a = np.zeros(w.shape + (4,), np.uint8); a[..., :3] = 255; a[..., 3] = np.where(w, 255, 0)
    Image.fromarray(a, 'RGBA').save(f'{n}_wa.png', optimize=True)
# where along the line the lake is in view (near band has water in the lower window)
nw = np.asarray(Image.open('near_water.png').convert('L')) > 127
F, s0 = L['near']['F'], L['near']['s0']
runs = []; prev = None
for s in range(53000, 79700, 250):
    c = int((s - s0) * F); frac = nw[150:200, max(c - 20, 0):c + 20].mean()
    lake = frac > .25
    if lake != prev: runs.append((s, lake, round(float(frac), 2))); prev = lake
print('lake runs', runs)
# peak label heights, as the renderer projects them
Y0, FOC, VEX = 140, 260.0, 1.25
for p in m['peaks']:
    d = p['d']; p['y'] = round(Y0 - FOC * VEX * (p['alt'] - d * d / (2 * 6371000) * .87 - 570) / d, 1)
print([(p['n'], p['y']) for p in m['peaks']])
json.dump(m, open('manifest.json', 'w'), ensure_ascii=False, indent=1)
