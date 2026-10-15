"""Render real-terrain parallax strips for the Meiringen -> Brienz -> Interlaken stretch.

Each layer is a slit-scan: for every column we stand on the track at route position s,
look out of the left (lake-side) window perpendicular to the line, and horizon-scan the
DEM between that layer's near and far distance. Output: daytime pixel-art PNG strips,
water masks, and a JSON manifest the game reads.
"""
import math, json, numpy as np
from PIL import Image

Z = 12
x0, x1, y0, y1 = map(int, open('bbox.txt').read().split())
TS = 256
# --- DEM mosaic (terrarium encoding) ---
mos = np.zeros(((y1 - y0 + 1) * TS, (x1 - x0 + 1) * TS), np.float32)
for x in range(x0, x1 + 1):
    for y in range(y0, y1 + 1):
        a = np.asarray(Image.open(f'tiles/{x}_{y}.png').convert('RGB')).astype(np.float32)
        mos[(y - y0) * TS:(y - y0 + 1) * TS, (x - x0) * TS:(x - x0 + 1) * TS] = a[..., 0] * 256 + a[..., 1] + a[..., 2] / 256 - 32768
N = 2 ** Z * TS
def px(lat, lon):
    r = np.radians(lat)
    gx = (lon + 180) / 360 * N - x0 * TS
    gy = (1 - np.log(np.tan(r) + 1 / np.cos(r)) / np.pi) / 2 * N - y0 * TS
    return gx, gy
LAT0 = 46.72
mpp = 156543.03392 * math.cos(math.radians(LAT0)) / 2 ** Z  # metres per DEM pixel
gy_, gx_ = np.gradient(mos, mpp)  # d/dy (south), d/dx (east)
from PIL import ImageFilter
k = np.ones(5) / 5
mos_s = np.apply_along_axis(lambda r: np.convolve(r, k, 'same'), 1, mos); mos_s = np.apply_along_axis(lambda r: np.convolve(r, k, 'same'), 0, mos_s).astype(np.float32)
gys_, gxs_ = np.gradient(mos_s, mpp)  # smoothed normals for distant slopes
def bil(arr, gx, gy):
    gx = np.clip(gx, 0, arr.shape[1] - 2.001); gy = np.clip(gy, 0, arr.shape[0] - 2.001)
    ix = gx.astype(int); iy = gy.astype(int); fx = gx - ix; fy = gy - iy
    return (arr[iy, ix] * (1 - fx) * (1 - fy) + arr[iy, ix + 1] * fx * (1 - fy) + arr[iy + 1, ix] * (1 - fx) * fy + arr[iy + 1, ix + 1] * fx * fy)

# --- local metric frame ---
KX = 111320 * math.cos(math.radians(LAT0)); KY = 110540
def toLL(e, n): return LAT0 + n / KY, 8.0 + e / KX
def toEN(lat, lon): return (lon - 8.0) * KX, (lat - LAT0) * KY

# --- track (rough waypoints along the real line, north shore of the lake) ---
WP = [('Meiringen', 46.7275, 8.1870), (None, 46.7380, 8.1500), (None, 46.7470, 8.1100), ('Brienzwiler', 46.7487, 8.0978), (None, 46.7530, 8.0620),
      ('Brienz', 46.7545, 8.0366), (None, 46.7480, 8.0100), (None, 46.7400, 7.9850), ('Oberried', 46.7363, 7.9590), ('Niederried', 46.7200, 7.9310),
      ('Ringgenberg', 46.7015, 7.8960), ('Interlaken Ost', 46.6905, 7.8693)]
S_MEIRINGEN = 53000
P0 = np.array([toEN(la, lo) for _, la, lo in WP])
def chaikin(p, it=5):
    for _ in range(it):
        q = [p[0]]
        for a, b in zip(p[:-1], p[1:]): q += [a * .75 + b * .25, a * .25 + b * .75]
        q.append(p[-1]); p = np.array(q)
    return p
P = chaikin(P0)
seglen = np.hypot(*np.diff(P, axis=0).T)
cum = np.concatenate([[0], np.cumsum(seglen)]) + S_MEIRINGEN
def nearest_s(pt):
    d = np.hypot(*(P - pt).T); return float(cum[np.argmin(d)])
stations = {n: nearest_s(P0[i]) for i, (n, _, _) in enumerate(WP) if n}
S_END = float(cum[-1])
print('stations', {k: round(v) for k, v in stations.items()})

def track(s):
    """position (e,n) and unit heading at route position s, extended straight past both ends"""
    s = np.asarray(s, float)
    i = np.clip(np.searchsorted(cum, s) - 1, 0, len(seglen) - 1)
    d = (P[i + 1] - P[i]) / seglen[i][:, None]
    pos = P[i] + d * (s - cum[i])[:, None]
    return pos, d

# --- render settings shared with the game ---
VEX = 1.25
H = 240; Y0 = 140; FOC = 260.0; CX = 330; W = 560
LAKE = 564.0
SUN_AZ, SUN_EL = 330, 45  # art-directed key light from behind the window so the slopes facing us read clearly
SUN = np.array([math.sin(math.radians(SUN_AZ)) * math.cos(math.radians(SUN_EL)), math.cos(math.radians(SUN_AZ)) * math.cos(math.radians(SUN_EL)), math.sin(math.radians(SUN_EL))])  # east, north, up
PAL = {
  'water': np.array([76, 191, 182]), 'waterfar': np.array([95, 159, 192]),
  'snow': np.array([[244, 247, 252], [214, 222, 240], [182, 192, 222]]),
  'rock': np.array([[176, 168, 178], [140, 134, 150], [106, 102, 122]]),
  'alp': np.array([[170, 198, 108], [134, 162, 84], [100, 126, 72]]),
  'forest': np.array([[70, 128, 72], [46, 96, 56], [31, 70, 42]]),
  'meadow': np.array([[140, 200, 84], [106, 168, 62], [80, 132, 52]]),
}
HAZE = np.array([180, 203, 228])

def vnoise(e, n, scale, seed):
    """cheap value noise in metres, for breaking up forest edges"""
    gx, gy = e / scale, n / scale
    ix, iy = np.floor(gx).astype(np.int64), np.floor(gy).astype(np.int64)
    fx, fy = gx - ix, gy - iy
    def h(a, b): v = (a * 374761393 + b * 668265263 + seed * 1442695041) & 0xffffffff; v = (v ^ (v >> 13)) * 1274126177 & 0xffffffff; return ((v ^ (v >> 16)) & 0xffff) / 65535
    u, v = fx * fx * (3 - 2 * fx), fy * fy * (3 - 2 * fy)
    return h(ix, iy) * (1 - u) * (1 - v) + h(ix + 1, iy) * u * (1 - v) + h(ix, iy + 1) * (1 - u) * v + h(ix + 1, iy + 1) * u * v

def hcell(e, n, sz, seed):
    a = np.floor(e / sz).astype(np.int64); b = np.floor(n / sz).astype(np.int64)
    v = (a * 374761393 + b * 668265263 + seed * 1442695041) & 0xffffffff; v = (v ^ (v >> 13)) * 1274126177 & 0xffffffff
    return ((v ^ (v >> 16)) & 0xffff) / 65535

def colour(h, slope, nx, ny, d, e, n, water):
    """daytime material colour with 3-step shading and distance haze"""
    lam = np.clip(nx * SUN[0] + ny * SUN[1] + 1 * SUN[2], 0, 1) / np.sqrt(nx * nx + ny * ny + 1)
    lvl = np.where(lam > .78, 0, np.where(lam > .5, 1, 2))
    nz = vnoise(e, n, 400, 3)
    out = np.zeros(h.shape + (3,))
    snow = (h > 2650) | ((h > 2250) & (slope < .75) & (nz > .45))
    rock = ~snow & ((slope > 1.25) | (h > 2400))
    alp = ~snow & ~rock & (h > 1750 + nz * 200)
    forest = ~snow & ~rock & ~alp & ((slope > .28) | (h > 1050)) & (nz < .78)
    meadow = ~snow & ~rock & ~alp & ~forest
    cell = lambda sz, seed: vnoise(np.floor(e / sz) * sz + .5, np.floor(n / sz) * sz + .5, 1e9, seed) if False else hcell(e, n, sz, seed)
    fld = cell(140, 5); tre = cell(28, 7); stp = cell(22, 9)
    lvl_f = np.where(stp > .55, np.minimum(lvl + 1, 2), lvl)  # forest stipple: crowns in light and shadow
    lvl_m = np.where(fld > .66, np.maximum(lvl - 1, 0), np.where(fld < .25, np.minimum(lvl + 1, 2), lvl))  # field patchwork
    for mask, key, lv in [(snow, 'snow', lvl), (rock, 'rock', np.where(stp > .7, np.minimum(lvl + 1, 2), lvl)), (alp, 'alp', lvl_m), (forest, 'forest', lvl_f), (meadow, 'meadow', lvl_m)]:
        out[mask] = PAL[key][lv[mask]]
    trees = meadow & (tre > .86); out[trees] = PAL['forest'][np.minimum(lvl, 1)[trees]]
    hay = meadow & (fld > .9); out[hay] = np.array([196, 206, 110])
    houses = meadow & (h < 700) & (cell(60, 13) > .965); out[houses] = np.array([226, 214, 196])
    roofs = meadow & (h < 700) & (cell(60, 13) > .985); out[roofs] = np.array([168, 92, 52])
    wk = np.clip((d - 600) / 9000, 0, 1)[:, None]
    out[water] = (PAL['water'] * (1 - wk) + PAL['waterfar'] * wk)[water]
    hz = (np.clip((d - 1200) / 42000, 0, 1) ** .75 * .62)[:, None]
    return out * (1 - hz) + HAZE * hz

BASEDIR = track(np.array([S_END]))[0][0] - track(np.array([S_MEIRINGEN]))[0][0]; BASEDIR /= np.hypot(*BASEDIR)
def look(name, ss):
    # far and mid look along one fixed direction (parallel rays never cross, so no slit-scan stripes);
    # the near band follows a long chord of the track so the shore stays square to the window
    if name in ('far', 'mid'):
        hd = np.tile(BASEDIR, (len(ss), 1))
    else:
        hd = track(ss + 2500)[0] - track(ss - 2500)[0]; hd /= np.hypot(*hd.T)[:, None]
    return np.stack([-hd[:, 1], hd[:, 0]], 1)  # 90 deg left of the heading

def render(name, F, d0, d1, step, fill_bottom):
    pad = CX / F + 50
    s_a, s_b = S_MEIRINGEN - (CX + 40) / F, S_END + (W - CX + 40) / F
    ncol = int((s_b - s_a) * F) + 1
    img = np.zeros((H, ncol, 4), np.uint8); wmask = np.zeros((H, ncol), np.uint8); dep = np.full((H, ncol), np.inf)
    # march the whole view (so every ridge keeps its true outline) and keep only pixels nearer than d1
    dl = [40.0]
    while dl[-1] < 48000: dl.append(dl[-1] + max(step, dl[-1] * .004))
    dist = np.array(dl)
    labels = []
    ss = s_a + np.arange(ncol) / F
    pos, hd = track(ss)
    left = look(name, ss)
    # camera height: the line's own level, lifted where the DEM says the ground is higher, smoothed over ~600 m
    cla, clo = toLL(pos[:, 0], pos[:, 1]); cg = bil(mos_s, *px(cla, clo))
    base = np.interp(ss, [S_MEIRINGEN, stations['Brienz'] - 800], [598, LAKE + 7])
    raw = np.maximum(base, cg + 6); win = max(3, int(600 * F)) | 1
    CAM = np.convolve(np.pad(raw, win // 2, mode='edge'), np.ones(win) / win, 'valid')
    e0 = pos[:, 0] + left[:, 0] * d0; n0 = pos[:, 1] + left[:, 1] * d0; la0, lo0 = toLL(e0, n0)
    w0 = (bil(mos, *px(la0, lo0)) < LAKE + 2.5) & (lo0 < 8.07)
    k_ = max(3, int(250 * F)) | 1; w0 = np.convolve(np.pad(w0.astype(float), k_ // 2, mode='edge'), np.ones(k_) / k_, 'valid') > .5
    for c in range(ncol):
        e = pos[c, 0] + left[c, 0] * dist; n = pos[c, 1] + left[c, 1] * dist
        la, lo = toLL(e, n); gx, gy = px(la, lo)
        h = bil(mos, gx, gy)
        camH = CAM[c]
        far = dist > 6000
        dzx = np.where(far, bil(gxs_, gx, gy), bil(gx_, gx, gy)); dzs = np.where(far, bil(gys_, gx, gy), bil(gy_, gx, gy))  # east slope, south slope
        slope = np.hypot(dzx, dzs)
        water = (h < LAKE + 2.5) & (slope < .04) & (lo < 8.07)
        # terrain nearer than this band's start is pressed down below eye level, so it never walls off the view
        flat = max(camH - 25, LAKE); t = np.clip((dist - d0 * .55) / (d0 * .45), 0, 1); t = t * t * (3 - 2 * t)
        hv = np.where(water, LAKE, h); hv = np.where(hv > flat, flat + (hv - flat) * t, hv)
        hh = hv - dist ** 2 / (2 * 6371000) * .87
        y = Y0 - FOC * VEX * (hh - camH) / dist
        col = colour(h, slope, -dzx, dzs, dist, e, n, water)
        top = H
        if False:
            yb = int(math.ceil(y[0]));
            wf = bool(w0[c]); base = PAL['water'] if wf else np.array([106, 168, 62])
            if yb < H: img[max(yb, 0):H, c, :3] = base; img[max(yb, 0):H, c, 3] = 255; dep[max(yb, 0):H, c] = dist[0]; wmask[max(yb, 0):H, c] = 255 if wf else 0; top = max(yb, 0)
        for k in range(len(dist)):
            yk = y[k]
            if yk < top:
                a = max(int(math.ceil(yk)), 0)
                if a < top:
                    img[a:top, c, :3] = col[k]; img[a:top, c, 3] = 255; dep[a:top, c] = dist[k]; wmask[a:top, c] = 255 if water[k] else 0
                    top = a
                if top <= 0: break
    cut = dep > d1
    img[cut] = 0; wmask[cut] = 0
    # pixel-art touches: a light rim on the top edge of every nearer ridge, a dark line under farther ones
    up = np.vstack([np.full((1, ncol), np.inf), dep[:-1]])
    rim = (img[..., 3] > 0) & (dep < up * .72) & ~np.isinf(up) & (wmask == 0)
    rgb = img[..., :3].astype(np.float32)
    rgb[rim] = rgb[rim] * .8 + np.array([255, 250, 225]) * .2
    sky = np.isinf(up) & (img[..., 3] > 0) & (wmask == 0)
    rgb[sky] = rgb[sky] * .88 + np.array([255, 255, 255]) * .12
    img[..., :3] = rgb.clip(0, 255).astype(np.uint8)
    return img, wmask, s_a, ncol

LAYERS = [('far', FOC / 16000, 7000, 1e9, 60, False), ('mid', FOC / 4000, 2200, 7500, 12, False), ('near', FOC / 1000, 300, 2300, 6, True)]
man = {'stations': stations, 's_start': S_MEIRINGEN, 's_end': S_END, 'Y0': Y0, 'layers': []}
for name, F, d0, d1, step, fb in LAYERS:
    img, wm, s_a, ncol = render(name, F, d0, d1, step, fb)
    q = Image.fromarray(img[..., :3]).quantize(colors=40, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    idx = np.asarray(q).astype(np.int16); idx = np.where(img[..., 3] > 0, idx, -1)
    # horizontal mode filter: slit-scan grazing slopes come out as 1-px stripes; fold them into blocks
    R_ = 3; pad = np.pad(idx, ((0, 0), (R_, R_)), mode='edge'); win = np.stack([pad[:, k:k + idx.shape[1]] for k in range(2 * R_ + 1)])
    cnt = (win[:, None] == win[None, :]).sum(1); best = win[np.argmax(cnt, 0), np.arange(idx.shape[0])[:, None], np.arange(idx.shape[1])[None, :]]
    pal = np.array(q.getpalette()[:40 * 3]).reshape(-1, 3).astype(np.uint8)
    rgb = np.where(best[..., None] >= 0, pal[np.clip(best, 0, None)], 0).astype(np.uint8)
    out = np.dstack([rgb, np.where(best >= 0, 255, 0).astype(np.uint8)])
    Image.fromarray(out, 'RGBA').save(f'{name}.png', optimize=True)
    has_w = bool(wm.any())
    if has_w: Image.fromarray(wm).convert('1').save(f'{name}_water.png', optimize=True)
    man['layers'].append({'name': name, 'F': F, 's0': s_a, 'w': ncol, 'water': has_w})
    print(name, ncol, 'px', has_w)

# peak labels: a peak shows in the column where the left-looking ray passes it
PEAKS = [('FAULHORN', 2681, 46.6747, 8.0175), ('SCHWARZHORN', 2928, 46.6716, 8.0938), ('AXALPHORN', 2321, 46.7099, 8.0626), ('EIGER', 3967, 46.5776, 8.0053),
         ('MÖNCH', 4107, 46.5586, 7.9973), ('JUNGFRAU', 4158, 46.5369, 7.9625), ('SCHYNIGE PLATTE', 2076, 46.6516, 7.9122), ('WETTERHORN', 3692, 46.6375, 8.1190),
         ('NIESEN', 2362, 46.6455, 7.6513), ('SCHRECKHORN', 4078, 46.5895, 8.1183)]
ss = np.arange(S_MEIRINGEN - 25000, S_END + 20000, 20.0)
pos, hd = track(ss)
for nm, alt, la, lo in PEAKS:
    pe, pn = toEN(la, lo)
    rel = np.stack([pe - pos[:, 0], pn - pos[:, 1]], 1)
    lf = look('far', ss); hdf = np.stack([lf[:, 1], -lf[:, 0]], 1)
    along = (rel * hdf).sum(1); side = (rel * lf).sum(1)
    i = np.argmin(np.abs(along));
    if side[i] <= 0 or abs(along[i]) > 40: continue
    man.setdefault('peaks', []).append({'n': nm, 'alt': alt, 's': float(ss[i]), 'd': float(side[i])})
ts = np.arange(S_MEIRINGEN, S_END + 1, 500.0); tp, _ = track(ts); tla, tlo = toLL(tp[:, 0], tp[:, 1])
man['trk'] = [[float(a), round(float(b), 5), round(float(c), 5)] for a, b, c in zip(ts, tla, tlo)]
json.dump(man, open('manifest.json', 'w'), ensure_ascii=False, indent=1)
print(json.dumps(man.get('peaks'), ensure_ascii=False))
