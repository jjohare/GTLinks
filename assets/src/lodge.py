"""The hero set piece: a summer alpine lodge on a timber terrace with a chairlift pylon.

Origin: centre of the terrace, terrace surface at y = 0. Terrace spans x in [-12, 12], z in [-7, 7].
The chalet sits uphill (-Z) behind the terrace, facing +Z (downhill). Chairlift pylon at x = +17.5.
"""
import math, random
from mathutils import Vector, Matrix
from gtl import MB, make_mat, empty, bx

TX, TZ = 12.0, 7.0          # terrace half extents
FZ = -7.0                   # facade plane
BW = 10.5                   # building half width


def mats():
    make_mat("wood_mid", (0.50, 0.31, 0.16), rough=0.85)
    make_mat("wood_dark", (0.28, 0.16, 0.08), rough=0.85)
    make_mat("wood_light", (0.74, 0.55, 0.33), rough=0.8)
    make_mat("deck_a", (0.66, 0.46, 0.26), rough=0.85)
    make_mat("deck_b", (0.58, 0.40, 0.22), rough=0.85)
    make_mat("shingle_a", (0.24, 0.15, 0.11), rough=0.9)
    make_mat("shingle_b", (0.31, 0.19, 0.13), rough=0.9)
    make_mat("stone_a", (0.60, 0.58, 0.54), rough=0.95)
    make_mat("stone_b", (0.46, 0.45, 0.43), rough=0.95)
    make_mat("shutter", (0.62, 0.12, 0.10), rough=0.8)
    make_mat("glass", (0.55, 0.72, 0.82), rough=0.05, alpha=0.45)
    make_mat("geranium", (0.82, 0.08, 0.14), rough=0.8)
    make_mat("pink", (0.95, 0.42, 0.58), rough=0.8)
    make_mat("leaf", (0.13, 0.40, 0.11), rough=0.9)
    make_mat("parasol_a", (0.82, 0.12, 0.12), rough=0.8, double=True)
    make_mat("parasol_b", (0.96, 0.93, 0.84), rough=0.8, double=True)
    make_mat("pennant_a", (0.85, 0.15, 0.15), rough=0.8, double=True)
    make_mat("pennant_b", (0.97, 0.85, 0.20), rough=0.8, double=True)
    make_mat("pennant_c", (0.20, 0.45, 0.80), rough=0.8, double=True)
    make_mat("pennant_d", (0.95, 0.95, 0.92), rough=0.8, double=True)
    make_mat("steel", (0.58, 0.61, 0.65), metallic=0.7, rough=0.5)
    make_mat("steel_dark", (0.20, 0.22, 0.25), metallic=0.6, rough=0.55)
    make_mat("chair_paint", (0.82, 0.12, 0.10), rough=0.45)
    make_mat("chair_seat", (0.12, 0.13, 0.15), rough=0.8)


def window(b, x, yc, w, h, z, shutters=True, flowers=True, rnd=None):
    """Window on a +Z facing wall at plane z (frame proud of the wall)."""
    bx(b, x - w / 2 - 0.12, x + w / 2 + 0.12, yc - h / 2 - 0.12, yc + h / 2 + 0.12, z - 0.02, z + 0.10, "wood_light")
    b.face([(x - w / 2, yc - h / 2, z + 0.105), (x + w / 2, yc - h / 2, z + 0.105), (x + w / 2, yc + h / 2, z + 0.105),
            (x - w / 2, yc + h / 2, z + 0.105)], "glass", hint=(0, 0, 1))
    bx(b, x - 0.03, x + 0.03, yc - h / 2, yc + h / 2, z + 0.10, z + 0.14, "wood_light")
    bx(b, x - w / 2, x + w / 2, yc - 0.03, yc + 0.03, z + 0.10, z + 0.14, "wood_light")
    bx(b, x - w / 2 - 0.2, x + w / 2 + 0.2, yc - h / 2 - 0.18, yc - h / 2 - 0.08, z - 0.02, z + 0.20, "wood_dark")
    if shutters:
        for sx in (-1, 1):
            xc = x + sx * (w / 2 + 0.12 + 0.30)
            bx(b, xc - 0.30, xc + 0.30, yc - h / 2 - 0.1, yc + h / 2 + 0.1, z - 0.02, z + 0.05, "shutter")
            bx(b, xc - 0.04, xc + 0.04, yc - h / 2 - 0.1, yc + h / 2 + 0.1, z + 0.05, z + 0.07, "wood_light")
    if flowers:
        yb = yc - h / 2 - 0.40
        bx(b, x - w / 2 - 0.1, x + w / 2 + 0.1, yb, yb + 0.26, z + 0.05, z + 0.38, "wood_dark")
        bx(b, x - w / 2 - 0.05, x + w / 2 + 0.05, yb + 0.26, yb + 0.36, z + 0.09, z + 0.34, "leaf")
        n = max(3, int(w / 0.38))
        for i in range(n):
            fx = x - w / 2 + (i + 0.5) * w / n
            blob(b, (fx, yb + 0.44, z + 0.22), 0.085, "geranium" if i % 2 == 0 else "pink")


def blob(m, c, r, mname):
    """Tiny 8-triangle octahedron used for flower heads."""
    m.lathe(c, (0, 1, 0), [(0.0, -r), (r, 0.0), (0.0, r)], 4, mname)


def build():
    mats()
    rnd = random.Random(7)
    root = empty("lodge")
    Bm, Tm, Fm, Cm, Rm = MB(), MB(), MB(), MB(), MB()

    # ------------------------------------------------------------- terrace
    bx(Tm, -TX, TX, -0.42, -0.12, -TZ, TZ, "wood_dark")
    nb = 28
    for i in range(nb):
        z0 = -TZ + i * (2 * TZ / nb)
        bx(Tm, -TX, TX, -0.12, 0.0, z0 + 0.01, z0 + 2 * TZ / nb - 0.01, "deck_a" if i % 2 == 0 else "deck_b")
    # stone retaining skirt, front (two halves) and both sides, deep so it never floats on the slope
    gap = 4.2
    Tm_blocks = []

    def stone_wall(x0, x1, z0, z1, axis):
        # solid core + relief blocks on the outward face
        bx(Tm, x0, x1, -3.2, -0.42, z0, z1, "stone_b")
        rows = 3
        rh = (3.2 - 0.42) / rows
        if axis == 'z':        # front wall faces +Z
            ncols = max(2, int((x1 - x0) / 1.5))
            cw = (x1 - x0) / ncols
            for r in range(rows):
                off = 0.0 if r % 2 == 0 else cw / 2
                for c in range(ncols + 1):
                    xa = x0 + c * cw - off
                    xb = xa + cw
                    xa, xb = max(xa, x0), min(xb, x1)
                    if xb - xa < 0.2:
                        continue
                    y0 = -3.2 + r * rh
                    bx(Tm, xa + 0.04, xb - 0.04, y0 + 0.04, y0 + rh - 0.04, z1, z1 + 0.07 + rnd.uniform(0, 0.05),
                       "stone_a" if (c + r) % 2 == 0 else "stone_b")
        else:                  # side walls face +/-X
            ncols = max(2, int((z1 - z0) / 1.5))
            cw = (z1 - z0) / ncols
            sx = 1 if x1 > 0 else -1
            xf = x1 if sx > 0 else x0
            for r in range(rows):
                off = 0.0 if r % 2 == 0 else cw / 2
                for c in range(ncols + 1):
                    za = z0 + c * cw - off
                    zb = za + cw
                    za, zb = max(za, z0), min(zb, z1)
                    if zb - za < 0.2:
                        continue
                    y0 = -3.2 + r * rh
                    xa, xb = (xf, xf + 0.07 + rnd.uniform(0, 0.05)) if sx > 0 else (xf - 0.07 - rnd.uniform(0, 0.05), xf)
                    bx(Tm, xa, xb, y0 + 0.04, y0 + rh - 0.04, za + 0.04, zb - 0.04, "stone_a" if (c + r) % 2 == 0 else "stone_b")
    stone_wall(-TX, -gap, TZ - 0.5, TZ, 'z')
    stone_wall(gap, TX, TZ - 0.5, TZ, 'z')
    stone_wall(TX - 0.5, TX, -TZ, TZ - 0.5, 'x')
    stone_wall(-TX, -TX + 0.5, -TZ, TZ - 0.5, 'x')
    for k in range(1, 5):   # steps down the middle
        bx(Tm, -gap, gap, -3.2, -0.42 * k - 0.0, TZ + 0.5 * (k - 1), TZ + 0.5 * k, "stone_a" if k % 2 else "stone_b", bevel=0.02)
    # railings
    def rail_run(p0, p1, sgn_out):
        p0, p1 = Vector(p0), Vector(p1)
        length = (p1 - p0).length
        d = (p1 - p0).normalized()
        n_posts = max(2, int(length / 2.0) + 1)
        for i in range(n_posts):
            p = p0 + d * (length * i / (n_posts - 1))
            bx(Rm, p.x - 0.07, p.x + 0.07, 0, 1.08, p.z - 0.07, p.z + 0.07, "wood_light")
            bx(Rm, p.x - 0.09, p.x + 0.09, 1.08, 1.12, p.z - 0.09, p.z + 0.09, "wood_dark")
        for y0, th in ((1.0, 0.10), (0.52, 0.06)):
            ctr = (p0 + p1) / 2
            if abs(d.x) > 0.5:
                bx(Rm, p0.x, p1.x, y0, y0 + th, ctr.z - 0.05, ctr.z + 0.05, "wood_light")
            else:
                bx(Rm, ctr.x - 0.05, ctr.x + 0.05, y0, y0 + th, p0.z, p1.z, "wood_light")
        nbal = int(length / 0.42)
        for i in range(nbal):
            p = p0 + d * (length * (i + 0.5) / nbal)
            bx(Rm, p.x - 0.022, p.x + 0.022, 0.08, 1.0, p.z - 0.022, p.z + 0.022, "wood_mid")
    rail_run((-TX + 0.07, 0, TZ - 0.07), (-gap - 0.1, 0, TZ - 0.07), 1)
    rail_run((gap + 0.1, 0, TZ - 0.07), (TX - 0.07, 0, TZ - 0.07), 1)
    rail_run((TX - 0.07, 0, TZ - 0.07), (TX - 0.07, 0, FZ + 0.4), 1)
    rail_run((-TX + 0.07, 0, TZ - 0.07), (-TX + 0.07, 0, FZ + 0.4), 1)

    # ------------------------------------------------------------- building
    # stone plinth with relief blocks front and sides
    bx(Bm, -BW - 0.2, BW + 0.2, -0.2, 1.0, -16.2, FZ + 0.15, "stone_b")
    doorgap = 1.5
    for (x0, x1) in ((-BW - 0.2, -doorgap), (doorgap, BW + 0.2)):
        ncols = int((x1 - x0) / 1.5)
        cw = (x1 - x0) / ncols
        for r in range(2):
            for c in range(ncols):
                off = 0.0 if r == 0 else cw / 2
                xa = max(x0, x0 + c * cw - off)
                xb = min(x1, x0 + (c + 1) * cw - off + (cw if r else 0) * 0)
                if xb - xa < 0.3:
                    continue
                y0 = r * 0.6
                bx(Bm, xa + 0.04, xb - 0.04, y0 + 0.03, y0 + 0.57, FZ + 0.15, FZ + 0.22 + rnd.uniform(0, 0.05),
                   "stone_a" if (c + r) % 2 == 0 else "stone_b")
    for sx in (-1, 1):
        for c in range(6):
            for r in range(2):
                z0 = FZ - 0.4 - c * 1.5
                xa = sx * (BW + 0.2)
                bx(Bm, min(xa, xa + sx * 0.07), max(xa, xa + sx * 0.07), r * 0.6 + 0.03, r * 0.6 + 0.57, z0 - 1.4, z0, "stone_a" if (c + r) % 2 == 0 else "stone_b")
    # timber storeys
    bx(Bm, -BW, BW, 1.0, 3.6, -16.0, FZ, "wood_mid")
    bx(Bm, -BW - 0.3, BW + 0.3, 3.6, 6.4, -16.3, FZ + 0.25, "wood_mid")
    # beams and corner posts
    for y0, y1 in ((0.95, 1.12), (3.5, 3.72), (6.3, 6.5)):
        bx(Bm, -BW - 0.35, BW + 0.35, y0, y1, FZ - 0.0, FZ + 0.32 if y0 > 3 else FZ + 0.22, "wood_dark")
    for sx in (-1, 1):
        bx(Bm, sx * BW - 0.18, sx * BW + 0.18, 1.0, 3.6, FZ, FZ + 0.2, "wood_dark")
        bx(Bm, sx * (BW + 0.3) - 0.18, sx * (BW + 0.3) + 0.18, 3.72, 6.4, FZ + 0.25, FZ + 0.45, "wood_dark")
    # gable ends: triangular infill
    ridge_z, ridge_y = -11.5, 9.9
    for sx in (-1, 1):
        x0, x1 = sorted((sx * (BW + 0.3), sx * (BW + 0.7)))
        tri = lambda x: [Vector((x, 6.4, FZ + 0.25)), Vector((x, 6.4, -16.3)), Vector((x, 9.55, ridge_z))]
        Bm.loft([tri(x0), tri(x1)], "wood_mid")
        xo = sx * (BW + 0.72)
        # cross bracing and a diamond window
        for zz in (-9.2, -13.8):
            Bm.pipe((xo, 6.5, zz), (xo, 8.2, ridge_z + (zz - ridge_z) * 0.35), 0.06, 4, "wood_dark")
        Bm.pipe((xo, 6.45, ridge_z), (xo, 9.4, ridge_z), 0.07, 4, "wood_dark")
        Bm.face([(xo + sx * 0.005, 7.0, ridge_z), (xo + sx * 0.005, 7.7, ridge_z + 0.7), (xo + sx * 0.005, 8.4, ridge_z),
                 (xo + sx * 0.005, 7.7, ridge_z - 0.7)], "glass", hint=(sx, 0, 0))
    # roof
    alpha = math.radians(28.0)
    half = (ridge_z - (-5.2))
    slope_len = abs(half) / math.cos(alpha)
    for s in (1, -1):
        d = Vector((0, -math.sin(alpha), s * math.cos(alpha)))
        n = Vector((0, math.cos(alpha), s * math.sin(alpha)))
        top = Vector((0, ridge_y, ridge_z))
        ctr = top + d * (slope_len / 2) - n * 0.15
        Bm.box(ctr, (23.0, 0.30, slope_len + 0.2), "shingle_a", rot=Matrix.Rotation(s * alpha, 3, 'X'))
        nrows = 10
        for k in range(nrows):
            t = (k + 0.5) / nrows * slope_len
            p = top + d * t + n * 0.03
            Bm.box(p, (22.8, 0.05, slope_len / nrows * 0.62), "shingle_b" if k % 2 else "shingle_a", rot=Matrix.Rotation(s * alpha, 3, 'X'))
        eave = top + d * slope_len
        Bm.box(eave + Vector((0, -0.13, 0)), (23.0, 0.22, 0.14), "wood_dark")
    Bm.box((0, ridge_y + 0.1, ridge_z), (23.2, 0.16, 0.5), "wood_dark", rot=Matrix.Rotation(0, 3, 'X'))
    # chimney
    bx(Bm, 6.8, 8.3, 5.0, 11.2, -13.8, -12.3, "stone_a")
    bx(Bm, 6.65, 8.45, 11.2, 11.4, -13.95, -12.15, "stone_b")
    bx(Bm, 7.1, 8.0, 11.4, 11.6, -13.5, -12.6, "steel_dark")
    # facade battens (skipping window and door zones)
    ground_win = (-8.0, -4.6, 4.6, 8.0)
    upper_win = (-8.0, -4.6, 4.6, 8.0)
    def free(x, wins, extra=()):
        return all(abs(x - w) > 1.55 for w in wins) and all(abs(x - e) > 1.6 for e in extra)
    x = -BW + 0.35
    while x < BW - 0.2:
        if free(x, ground_win, (0.0,)):
            bx(Bm, x - 0.04, x + 0.04, 1.12, 3.5, FZ, FZ + 0.05, "wood_dark")
        if free(x, upper_win, (0.0,)):
            bx(Bm, x - 0.04, x + 0.04, 3.72, 6.3, FZ + 0.25, FZ + 0.30, "wood_dark")
        x += 0.55
    for sx in (-1, 1):
        z = -7.6
        while z > -15.8:
            bx(Bm, sx * BW, sx * BW + sx * 0.05, 1.12, 3.5, z - 0.04, z + 0.04, "wood_dark")
            bx(Bm, sx * (BW + 0.3), sx * (BW + 0.3) + sx * 0.05, 3.72, 6.3, z - 0.04, z + 0.04, "wood_dark")
            z -= 0.85
    # windows
    for wx in ground_win:
        window(Bm, wx, 2.3, 1.7, 1.3, FZ + 0.0, rnd=rnd)
    for wx in upper_win:
        window(Bm, wx, 4.95, 1.7, 1.4, FZ + 0.25, rnd=rnd)
    # entrance: double door and porch step
    bx(Bm, -1.3, 1.3, 0.0, 2.7, FZ - 0.02, FZ + 0.14, "wood_light")
    for sx in (-1, 1):
        bx(Bm, sx * 0.62 - 0.55, sx * 0.62 + 0.55, 0.08, 2.6, FZ + 0.14, FZ + 0.20, "wood_dark")
        Bm.face([(sx * 0.62 - 0.35, 1.5, FZ + 0.205), (sx * 0.62 + 0.35, 1.5, FZ + 0.205), (sx * 0.62 + 0.35, 2.4, FZ + 0.205),
                 (sx * 0.62 - 0.35, 2.4, FZ + 0.205)], "glass", hint=(0, 0, 1))
        bx(Bm, sx * 0.1 - 0.03, sx * 0.1 + 0.03, 1.1, 1.2, FZ + 0.2, FZ + 0.25, "steel")
    bx(Bm, -1.6, 1.6, 0.0, 0.12, FZ + 0.2, FZ + 0.9, "stone_a", bevel=0.02)
    # balcony deck, brackets, railing
    bx(Bm, -BW - 0.3, BW + 0.3, 3.5, 3.72, FZ + 0.25, FZ + 1.75, "wood_light")
    ztip = FZ + 1.75
    for x in [-9.0 + i * 3.0 for i in range(7)]:
        Bm.pipe((x, 2.9, FZ + 0.25), (x, 3.5, ztip - 0.15), 0.07, 4, "wood_dark")
    nb2 = int((2 * BW + 0.6) / 0.4)
    for i in range(nb2):
        xx = -BW - 0.3 + (i + 0.5) * (2 * BW + 0.6) / nb2
        bx(Bm, xx - 0.022, xx + 0.022, 3.76, 4.55, ztip - 0.08, ztip - 0.04, "wood_mid")
    bx(Bm, -BW - 0.3, BW + 0.3, 4.55, 4.65, ztip - 0.11, ztip - 0.01, "wood_light")
    bx(Bm, -BW - 0.3, BW + 0.3, 3.95, 4.01, ztip - 0.09, ztip - 0.03, "wood_light")
    for x in [-BW - 0.25 + i * (2 * BW + 0.5) / 7 for i in range(8)]:
        bx(Bm, x - 0.06, x + 0.06, 3.72, 4.68, ztip - 0.12, ztip, "wood_dark")
    for sx in (-1, 1):
        xe = sx * (BW + 0.3)
        bx(Bm, xe - 0.05, xe + 0.05, 3.72, 4.65, FZ + 0.25, ztip, "wood_light")
    # balcony door
    bx(Bm, -1.2, 1.2, 3.72, 6.0, FZ + 0.25, FZ + 0.38, "wood_light")
    Bm.face([(-1.0, 3.8, FZ + 0.385), (1.0, 3.8, FZ + 0.385), (1.0, 5.9, FZ + 0.385), (-1.0, 5.9, FZ + 0.385)], "glass", hint=(0, 0, 1))
    bx(Bm, -0.03, 0.03, 3.8, 5.9, FZ + 0.38, FZ + 0.42, "wood_light")
    bx(Bm, -1.0, 1.0, 4.8, 4.86, FZ + 0.38, FZ + 0.42, "wood_light")
    # bunting along the balcony rail, flagpole on the right end
    cols = ["pennant_a", "pennant_b", "pennant_c", "pennant_d"]
    n = 34
    for i in range(n):
        xx = -BW + 0.3 + i * (2 * BW - 0.6) / (n - 1)
        sag = 0.28 * math.sin(math.pi * ((i * 3.0) % (n / 3.0)) / (n / 3.0))
        y = 4.55 - sag
        Bm.face([(xx - 0.15, y, ztip + 0.02), (xx + 0.15, y, ztip + 0.02), (xx, y - 0.36, ztip + 0.02)], cols[i % 4], hint=(0, 0, 1))
    Bm.pipe((9.9, 3.7, ztip - 0.15), (9.9, 8.6, ztip - 0.15), 0.035, 5, "steel")
    Bm.face([(9.93, 8.55, ztip - 0.15), (10.8, 8.35, ztip - 0.15), (9.93, 8.0, ztip - 0.15)], "pennant_a", hint=(0, 0, 1))
    # parasols, tables, stools
    for (px, pz) in ((-9.0, 3.2), (-9.0, -2.4), (9.0, 3.2), (9.0, -2.4)):
        Fm.pipe((px, 0.0, pz), (px, 2.9, pz), 0.04, 6, "steel")
        for i in range(8):
            a0, a1 = 2 * math.pi * i / 8, 2 * math.pi * (i + 1) / 8
            Fm.face([(px, 2.95, pz), (px + 1.55 * math.cos(a0), 2.3, pz + 1.55 * math.sin(a0)),
                     (px + 1.55 * math.cos(a1), 2.3, pz + 1.55 * math.sin(a1))],
                    "parasol_a" if i % 2 == 0 else "parasol_b", hint=(0, 1, 0))
        Fm.lathe((px, 0, pz), (0, 1, 0), [(0.0, 0.74), (0.62, 0.74), (0.62, 0.70), (0.06, 0.70), (0.05, 0.0), (0.0, 0.0)], 10, "wood_light")
        for k in range(4):
            a = k * math.pi / 2 + 0.4
            sx_, sz_ = px + 1.0 * math.cos(a), pz + 1.0 * math.sin(a)
            Fm.lathe((sx_, 0, sz_), (0, 1, 0), [(0.20, 0.0), (0.20, 0.46), (0.0, 0.46)], 8, "wood_dark")
    # benches against the building
    for bxp in (-5.2, 5.2):
        z = FZ + 0.45
        bx(Fm, bxp - 1.1, bxp + 1.1, 0.42, 0.50, z - 0.22, z + 0.22, "wood_light")
        bx(Fm, bxp - 1.1, bxp + 1.1, 0.75, 1.15, z - 0.26, z - 0.20, "wood_light")
        for sx in (-1, 1):
            bx(Fm, bxp + sx * 0.95 - 0.05, bxp + sx * 0.95 + 0.05, 0, 0.42, z - 0.2, z + 0.2, "wood_dark")
            bx(Fm, bxp + sx * 0.95 - 0.04, bxp + sx * 0.95 + 0.04, 0.42, 1.15, z - 0.27, z - 0.19, "wood_dark")
    # flower boxes on the terrace rail
    for fx in (-10.0, -6.5, 6.5, 10.0):
        z = TZ - 0.07
        bx(Fm, fx - 0.9, fx + 0.9, 1.12, 1.38, z - 0.17, z + 0.17, "wood_dark")
        bx(Fm, fx - 0.85, fx + 0.85, 1.38, 1.46, z - 0.14, z + 0.14, "leaf")
        for i in range(5):
            blob(Fm, (fx - 0.7 + i * 0.35, 1.55, z), 0.09, "geranium" if i % 2 == 0 else "pink")

    # ------------------------------------------------------------- chairlift
    PX = 17.5
    def leg(x, z, tx, tz):
        Cm.pipe((PX + x, -2.0, z), (PX + tx, 9.0, tz), 0.15, 4, "steel")
    for sx in (-1, 1):
        for sz in (-1, 1):
            leg(sx * 1.3, sz * 1.1, sx * 0.5, sz * 0.3)
    def at(y, sx, sz):
        t = (y + 2.0) / 11.0
        return (PX + sx * (1.3 + (0.5 - 1.3) * t), y, sz * (1.1 + (0.3 - 1.1) * t))
    for y in (0.5, 3.0, 5.5, 7.8):
        for (a, b) in (((1, 1), (-1, 1)), ((1, -1), (-1, -1)), ((1, 1), (1, -1)), ((-1, 1), (-1, -1))):
            Cm.pipe(at(y, *a), at(y, *b), 0.07, 4, "steel_dark")
    for y0, y1 in ((0.5, 3.0), (3.0, 5.5), (5.5, 7.8)):
        for (sx, sz) in ((1, 1), (-1, 1)):
            Cm.pipe(at(y0, sx, sz), at(y1, -sx, sz), 0.06, 4, "steel_dark")
        Cm.pipe(at(y0, 1, -1), at(y1, 1, 1), 0.06, 4, "steel_dark")
    bx(Cm, PX - 3.4, PX + 3.4, 8.95, 9.25, -0.4, 0.4, "steel_dark", bevel=0.04)
    for sx in (-1, 1):
        xc = PX + sx * 2.4
        bx(Cm, xc - 0.14, xc + 0.14, 9.05, 9.55, -0.9, 0.9, "steel")
        for k in range(-1, 2):
            Cm.lathe((xc, 9.62, k * 0.55), (1, 0, 0), [(0.22, -0.09), (0.22, 0.09), (0.0, 0.09)], 10, "steel_dark")
        Cm.pipe((xc, 9.72, -30.0), (xc, 9.72, 30.0), 0.025, 4, "steel_dark")
    bx(Cm, PX - 0.6, PX + 0.6, -3.2, -1.9, -1.5, 1.5, "stone_b")   # footing
    # chairs (separate nodes so the front end can swing them from the cable)
    chairs = []
    for name, cx, cz, tilt in (("chair_a", PX - 2.4, -5.5, 4.0), ("chair_b", PX - 2.4, 6.5, -3.0)):
        ch = MB()
        yc = 9.7
        ch.box((cx, yc, cz), (0.22, 0.14, 0.22), "steel_dark")
        ch.pipe((cx, yc, cz), (cx, yc - 2.6, cz), 0.035, 4, "steel")
        ys = yc - 2.7
        bx(ch, cx - 0.30, cx + 0.30, ys, ys + 0.09, cz - 0.85, cz + 0.85, "chair_seat", bevel=0.02)
        bx(ch, cx + 0.28, cx + 0.36, ys + 0.05, ys + 0.72, cz - 0.85, cz + 0.85, "chair_paint", bevel=0.02)
        for sz in (-1, 1):
            bx(ch, cx - 0.32, cx - 0.26, ys - 0.14, ys + 0.09, cz + sz * 0.82 - 0.03, cz + sz * 0.82 + 0.03, "steel")
            ch.pipe((cx - 0.30, ys + 0.60, cz + sz * 0.88), (cx - 0.30, ys + 0.10, cz + sz * 0.88), 0.025, 4, "steel")
        ch.pipe((cx - 0.30, ys + 0.60, cz - 0.88), (cx - 0.30, ys + 0.60, cz + 0.88), 0.025, 4, "steel")
        chairs.append((name, ch, (cx, yc, cz), tilt))

    # ------------------------------------------------------------- nodes
    Bm.to_object("lodge_building", parent=root, smooth=None)
    Tm.to_object("lodge_terrace", parent=root, smooth=None)
    Rm.to_object("lodge_railings", parent=root, smooth=None)
    Fm.to_object("lodge_furniture", parent=root, smooth=None)
    Cm.to_object("chairlift_pylon", parent=root, smooth=None)
    for name, ch, org, tilt in chairs:
        ch.to_object(name, origin=org, parent=root, smooth=None)
