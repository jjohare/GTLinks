"""The hero set piece (v2): a summer alpine lodge on a timber terrace, with a chairlift top station and pylon.

Origin: centre of the terrace, terrace surface at y = 0. Terrace spans x in [-12, 12], z in [-7, 7].
The chalet sits uphill (-Z) behind the terrace, facing +Z (downhill). The chairlift pylon is at x = +17.5 and the
top station (bullwheel, turnstile, cable guides, canopy) sits beyond it at the uphill end of the line (-Z).

Nodes: lodge (root), lodge_building, lodge_roof, lodge_balcony, lodge_terrace, lodge_railings, lodge_furniture,
lodge_flowers, lodge_woodpile, lodge_skirack, lodge_sign, lodge_lanterns, chairlift_pylon, chairlift_cable,
chairlift_station, chairlift_chairs, chair_a, chair_b.

Also exports build_chairlift_pylon() and build_chair() (stand-alone models, see below).
No text, brand names or logos anywhere.
"""
import math, random
from mathutils import Vector, Matrix
from gtl import MB, make_mat, empty, bx

TX, TZ = 12.0, 7.0          # terrace half extents
FZ = -7.0                   # lower facade plane
BW = 10.5                   # building half width (lower storey)
PX = 17.5                   # pylon x
CAB_X = 2.4                 # cable offset either side of pylon centre
Z_E = -21.5                 # bullwheel centre z
Y_E = 4.9                   # bullwheel height
Y_CAB = 9.7                 # cable height at the pylon
Z_SLOPE0 = -1.3             # cable starts descending to the station here


def cab_y(z):
    """Cable height at z (level to the pylon, then a straight descent to the bullwheel)."""
    if z >= Z_SLOPE0:
        return Y_CAB
    t = min(1.0, (Z_SLOPE0 - z) / (Z_SLOPE0 - Z_E))
    return Y_CAB + (Y_E - Y_CAB) * t


# ------------------------------------------------------------------ materials
def mats():
    make_mat("wood_mid", (0.50, 0.31, 0.16), rough=0.85)
    make_mat("wood_mid2", (0.45, 0.28, 0.14), rough=0.85)
    make_mat("wood_mid3", (0.55, 0.35, 0.19), rough=0.85)
    make_mat("wood_dark", (0.28, 0.16, 0.08), rough=0.85)
    make_mat("wood_light", (0.74, 0.55, 0.33), rough=0.8)
    make_mat("wood_log", (0.66, 0.46, 0.27), rough=0.9)
    make_mat("log_end", (0.80, 0.62, 0.40), rough=0.9)
    make_mat("log_bark", (0.30, 0.20, 0.12), rough=0.95)
    make_mat("deck_a", (0.66, 0.46, 0.26), rough=0.85)
    make_mat("deck_b", (0.58, 0.40, 0.22), rough=0.85)
    make_mat("deck_c", (0.62, 0.43, 0.24), rough=0.85)
    make_mat("shingle_a", (0.24, 0.15, 0.11), rough=0.9)
    make_mat("shingle_b", (0.31, 0.19, 0.13), rough=0.9)
    make_mat("shingle_c", (0.20, 0.12, 0.09), rough=0.9)
    make_mat("shingle_dark", (0.09, 0.055, 0.04), rough=0.95)
    make_mat("stone_a", (0.60, 0.58, 0.54), rough=0.95)
    make_mat("stone_b", (0.46, 0.45, 0.43), rough=0.95)
    make_mat("stone_c", (0.53, 0.50, 0.46), rough=0.95)
    make_mat("concrete", (0.62, 0.62, 0.60), rough=0.95)
    make_mat("shutter", (0.62, 0.12, 0.10), rough=0.8)
    make_mat("shutter_b", (0.55, 0.10, 0.09), rough=0.8)
    make_mat("interior", (0.07, 0.06, 0.06), rough=0.9)
    make_mat("glass", (0.55, 0.72, 0.82), rough=0.05, alpha=0.45)
    make_mat("geranium", (0.82, 0.08, 0.14), rough=0.8)
    make_mat("geranium_b", (0.70, 0.05, 0.12), rough=0.8)
    make_mat("pink", (0.95, 0.42, 0.58), rough=0.8)
    make_mat("white_flower", (0.96, 0.94, 0.90), rough=0.8)
    make_mat("leaf", (0.13, 0.40, 0.11), rough=0.9)
    make_mat("leaf_b", (0.10, 0.33, 0.09), rough=0.9)
    make_mat("soil", (0.16, 0.10, 0.07), rough=1.0)
    make_mat("parasol_a", (0.82, 0.12, 0.12), rough=0.8, double=True)
    make_mat("parasol_b", (0.96, 0.93, 0.84), rough=0.8, double=True)
    make_mat("pennant_a", (0.85, 0.15, 0.15), rough=0.8, double=True)
    make_mat("pennant_b", (0.97, 0.85, 0.20), rough=0.8, double=True)
    make_mat("pennant_c", (0.20, 0.45, 0.80), rough=0.8, double=True)
    make_mat("pennant_d", (0.95, 0.95, 0.92), rough=0.8, double=True)
    make_mat("steel", (0.58, 0.61, 0.65), metallic=0.7, rough=0.5)
    make_mat("steel_dark", (0.20, 0.22, 0.25), metallic=0.6, rough=0.55)
    make_mat("iron", (0.10, 0.10, 0.11), metallic=0.5, rough=0.6)
    make_mat("rubber", (0.06, 0.06, 0.07), rough=0.9)
    make_mat("chair_paint", (0.82, 0.12, 0.10), rough=0.45)
    make_mat("chair_seat", (0.12, 0.13, 0.15), rough=0.8)
    make_mat("safety_yellow", (0.93, 0.74, 0.10), rough=0.6)
    make_mat("lantern_glass", (1.0, 0.82, 0.45), rough=0.2, emit=(1.0, 0.72, 0.30), emit_strength=1.5)
    make_mat("clay", (0.62, 0.30, 0.20), rough=0.9)
    make_mat("sign_board", (0.80, 0.66, 0.42), rough=0.8)


# ------------------------------------------------------------------ low-level helpers
def boxf(b, x0, x1, y0, y1, z0, z1, m, sides='tbfkrl'):
    """Axis-aligned box with only the chosen faces: t(+y) b(-y) f(+z) k(-z) r(+x) l(-x)."""
    x0, x1 = sorted((x0, x1)); y0, y1 = sorted((y0, y1)); z0, z1 = sorted((z0, z1))
    if 't' in sides: b.face([(x0, y1, z0), (x1, y1, z0), (x1, y1, z1), (x0, y1, z1)], m, hint=(0, 1, 0))
    if 'b' in sides: b.face([(x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1)], m, hint=(0, -1, 0))
    if 'f' in sides: b.face([(x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)], m, hint=(0, 0, 1))
    if 'k' in sides: b.face([(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0)], m, hint=(0, 0, -1))
    if 'r' in sides: b.face([(x1, y0, z0), (x1, y1, z0), (x1, y1, z1), (x1, y0, z1)], m, hint=(1, 0, 0))
    if 'l' in sides: b.face([(x0, y0, z0), (x0, y1, z0), (x0, y1, z1), (x0, y0, z1)], m, hint=(-1, 0, 0))


class Wall:
    """Wall frame: origin o on the wall face, u along the wall, n horizontal outward normal."""

    def __init__(s, o, u, n):
        s.o = Vector(o); s.u = Vector(u).normalized(); s.n = Vector(n).normalized(); s.y = Vector((0, 1, 0))

    def p(s, u, y, d):
        return s.o + s.u * u + s.y * y + s.n * d

    def box(s, b, u0, u1, y0, y1, d0, d1, m, sides='otblri'):
        P = s.p
        if 'o' in sides: b.face([P(u0, y0, d1), P(u1, y0, d1), P(u1, y1, d1), P(u0, y1, d1)], m, hint=s.n)
        if 'i' in sides: b.face([P(u0, y0, d0), P(u1, y0, d0), P(u1, y1, d0), P(u0, y1, d0)], m, hint=-s.n)
        if 't' in sides: b.face([P(u0, y1, d0), P(u1, y1, d0), P(u1, y1, d1), P(u0, y1, d1)], m, hint=s.y)
        if 'b' in sides: b.face([P(u0, y0, d0), P(u1, y0, d0), P(u1, y0, d1), P(u0, y0, d1)], m, hint=-s.y)
        if 'l' in sides: b.face([P(u0, y0, d0), P(u0, y1, d0), P(u0, y1, d1), P(u0, y0, d1)], m, hint=-s.u)
        if 'r' in sides: b.face([P(u1, y0, d0), P(u1, y1, d0), P(u1, y1, d1), P(u1, y0, d1)], m, hint=s.u)

    def quad(s, b, pts, m, hint):
        b.face([s.p(*q) for q in pts], m, hint=hint)

    def tri_prism(s, b, pts_yd, u0, u1, m):
        """Prism along u with a (y, d) triangle/polygon section."""
        r0 = [s.p(u0, y, d) for (y, d) in pts_yd]
        r1 = [s.p(u1, y, d) for (y, d) in pts_yd]
        b.loft([r0, r1], m)

    def lap_board(s, b, u0, u1, y0, y1, d, m):
        """Lapped clapboard wedge: thick bottom edge, thin top; outer face + bottom lip only."""
        P = s.p
        b.face([P(u0, y0, d + 0.07), P(u1, y0, d + 0.07), P(u1, y1, d + 0.025), P(u0, y1, d + 0.025)], m, hint=s.n)
        b.face([P(u0, y0, d), P(u1, y0, d), P(u1, y0, d + 0.07), P(u0, y0, d + 0.07)], m, hint=-s.y)


def blob(b, c, r, m):
    """Tiny 8-triangle octahedron used for flower heads."""
    b.lathe(c, (0, 1, 0), [(0.0, -r), (r, 0.0), (0.0, r)], 4, m)


def leafclump(b, c, r, m):
    """Flattened five-sided leaf clump (10 triangles)."""
    b.lathe(c, (0, 1, 0), [(0.0, -r * 0.35), (r, 0.0), (0.0, r * 0.55)], 5, m)


def heart_polar(n=96):
    pts = []
    for i in range(n):
        t = 2 * math.pi * i / n
        x = 16 * math.sin(t) ** 3
        y = 13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)
        pts.append((math.atan2(y - 0.5, x), math.hypot(x, y - 0.5) / 16.0, x / 16.0, (y - 0.5) / 16.0))
    pts.sort()
    return pts


_HEART = heart_polar()


def r_heart(th):
    """Radius of a unit heart (half-width 1) about its centre, at polar angle th."""
    th = (th + math.pi) % (2 * math.pi) - math.pi
    for i in range(len(_HEART)):
        a0, r0 = _HEART[i][0], _HEART[i][1]
        a1, r1 = _HEART[(i + 1) % len(_HEART)][0], _HEART[(i + 1) % len(_HEART)][1]
        if i == len(_HEART) - 1:
            a1 += 2 * math.pi
            tt = th if th >= a0 else th + 2 * math.pi
        else:
            tt = th
        if a0 <= tt <= a1:
            f = (tt - a0) / max(1e-9, a1 - a0)
            return r0 + (r1 - r0) * f
    return 1.0


def r_diamond(th):
    return 1.0 / (abs(math.cos(th)) + abs(math.sin(th)))


def plate_hole(W, b, uc, yc, hw, hh, d0, d1, shape, hs, m, back_m=None, ang_n=16):
    """Flat plate (rect 2hw x 2hh centred uc,yc in wall frame W, thickness d0..d1) with a heart/diamond/round cut-out
    of nominal half-size hs, built from real geometry (annulus quads + inner wall)."""
    corner = [math.atan2(hh, hw), math.atan2(hh, -hw), math.atan2(-hh, -hw), math.atan2(-hh, hw)]
    angs = sorted([-math.pi + 2 * math.pi * i / ang_n for i in range(ang_n)] + corner)

    def rin(a):
        if shape == 'heart':
            return hs * r_heart(a)
        if shape == 'diamond':
            return hs * r_diamond(a)
        return hs

    def rout(a):
        ca, sa = abs(math.cos(a)), abs(math.sin(a))
        return min(hw / ca if ca > 1e-9 else 1e9, hh / sa if sa > 1e-9 else 1e9)
    for i in range(len(angs)):
        a, c = angs[i], angs[(i + 1) % len(angs)]
        oa = (uc + rout(a) * math.cos(a), yc + rout(a) * math.sin(a))
        oc = (uc + rout(c) * math.cos(c), yc + rout(c) * math.sin(c))
        ia = (uc + rin(a) * math.cos(a), yc + rin(a) * math.sin(a))
        ic = (uc + rin(c) * math.cos(c), yc + rin(c) * math.sin(c))
        W.quad(b, [(oa[0], oa[1], d1), (oc[0], oc[1], d1), (ic[0], ic[1], d1), (ia[0], ia[1], d1)], m, W.n)
        mid = (a + c) / 2
        hint = -(W.u * math.cos(mid) + W.y * math.sin(mid))
        W.quad(b, [(ia[0], ia[1], d0), (ic[0], ic[1], d0), (ic[0], ic[1], d1), (ia[0], ia[1], d1)], m, hint)
    W.box(b, uc - hw, uc + hw, yc - hh, yc + hh, d0, d1, m, sides='tblr')


def lathe_v(b, x, y, z, prof, segs, m):
    b.lathe((x, y, z), (0, 1, 0), prof, segs, m)


def ring_pts(cx, cy, cz, r, n, axis='y'):
    out = []
    for i in range(n):
        a = 2 * math.pi * i / n
        if axis == 'y':
            out.append((cx + r * math.cos(a), cy, cz + r * math.sin(a)))
    return out


def rbox(b, org, loc, size, m, yaw=0.0, tilt=None):
    """Box at local offset loc rotated by yaw about Y at org."""
    R = Matrix.Rotation(yaw, 3, 'Y')
    p = Vector(org) + R @ Vector(loc)
    rot = R if tilt is None else R @ tilt
    b.box(p, size, m, rot=rot)


# ------------------------------------------------------------------ windows
def window(W, b, fl, u, yc, w, h, d0, shutters=True, style='louvre', flowers=True, rnd=None, small=False, bunting_clear=False):
    """Timber window on wall frame W; d0 is the wall plane offset. Shutters: 'louvre' or cut-out ('heart'/'diamond' mix)."""
    fw = 0.11
    # dark interior so the wall boards do not show through the glass
    W.box(b, u - w / 2, u + w / 2, yc - h / 2, yc + h / 2, d0 + 0.06, d0 + 0.075, "interior", sides='o')
    # frame
    W.box(b, u - w / 2 - fw, u + w / 2 + fw, yc + h / 2, yc + h / 2 + fw, d0 - 0.01, d0 + 0.14, "wood_light", sides='otlr')
    W.box(b, u - w / 2 - fw, u + w / 2 + fw, yc - h / 2 - fw, yc - h / 2, d0 - 0.01, d0 + 0.14, "wood_light", sides='otlr')
    W.box(b, u - w / 2 - fw, u - w / 2, yc - h / 2, yc + h / 2, d0 - 0.01, d0 + 0.14, "wood_light", sides='otb')
    W.box(b, u + w / 2, u + w / 2 + fw, yc - h / 2, yc + h / 2, d0 - 0.01, d0 + 0.14, "wood_light", sides='otb')
    W.quad(b, [(u - w / 2, yc - h / 2, d0 + 0.10), (u + w / 2, yc - h / 2, d0 + 0.10), (u + w / 2, yc + h / 2, d0 + 0.10),
               (u - w / 2, yc + h / 2, d0 + 0.10)], "glass", W.n)
    # glazing bars: one vertical, two horizontal (six panes)
    W.box(b, u - 0.025, u + 0.025, yc - h / 2, yc + h / 2, d0 + 0.10, d0 + 0.145, "wood_light", sides='olr')
    W.box(b, u - w / 2, u + w / 2, yc - 0.02, yc + 0.02, d0 + 0.10, d0 + 0.14, "wood_light", sides='otb')
    # sill and carved lintel with a little pediment
    W.box(b, u - w / 2 - 0.22, u + w / 2 + 0.22, yc - h / 2 - 0.2, yc - h / 2 - 0.09, d0 - 0.02, d0 + 0.26, "wood_dark", sides='otlrb')
    W.box(b, u - w / 2 - 0.2, u + w / 2 + 0.2, yc + h / 2 + fw, yc + h / 2 + fw + 0.1, d0 - 0.02, d0 + 0.2, "wood_dark", sides='otlr')
    W.tri_prism(b, [(yc + h / 2 + fw + 0.1, d0 - 0.02), (yc + h / 2 + fw + 0.1, d0 + 0.2), (yc + h / 2 + fw + 0.28, d0 + 0.09)],
                u - w / 2 - 0.22, u + w / 2 + 0.22, "wood_mid")
    if shutters:
        sw = 0.60 if not small else 0.40
        for k, sx in enumerate((-1, 1)):
            xc = u + sx * (w / 2 + fw + 0.03 + sw / 2)
            ya, yb = yc - h / 2 - 0.1, yc + h / 2 + 0.1
            W.box(b, xc - sw / 2, xc + sw / 2, ya, yb, d0 + 0.04, d0 + 0.055, "interior", sides='o')
            if style == 'louvre':
                st = 0.07
                W.box(b, xc - sw / 2, xc - sw / 2 + st, ya, yb, d0 + 0.045, d0 + 0.11, "shutter", sides='olro')
                W.box(b, xc + sw / 2 - st, xc + sw / 2, ya, yb, d0 + 0.045, d0 + 0.11, "shutter", sides='olro')
                W.box(b, xc - sw / 2 + st, xc + sw / 2 - st, yb - st, yb, d0 + 0.045, d0 + 0.11, "shutter", sides='otlro')
                W.box(b, xc - sw / 2 + st, xc + sw / 2 - st, ya, ya + st, d0 + 0.045, d0 + 0.11, "shutter", sides='otlro')
                n = int((yb - ya - 2 * st) / 0.15)
                for i in range(n):
                    y0 = ya + st + 0.01 + i * (yb - ya - 2 * st - 0.02) / n
                    hgt = (yb - ya - 2 * st - 0.02) / n
                    # slanted slat (thicker at the lower edge so it throws light)
                    ring0 = [W.p(xc - sw / 2 + st, y0, d0 + 0.065), W.p(xc - sw / 2 + st, y0 + hgt * 0.85, d0 + 0.06),
                             W.p(xc - sw / 2 + st, y0 + 0.02, d0 + 0.1)]
                    ring1 = [W.p(xc + sw / 2 - st, y0, d0 + 0.065), W.p(xc + sw / 2 - st, y0 + hgt * 0.85, d0 + 0.06),
                             W.p(xc + sw / 2 - st, y0 + 0.02, d0 + 0.1)]
                    b.loft([ring0, ring1], "shutter_b")
            else:
                shape = style if style in ('heart', 'diamond') else ('heart' if sx < 0 else 'diamond')
                hs = min(sw * 0.36, 0.2)
                # cut-out in the upper third, plain board below with a battened lower panel
                ymid = ya + (yb - ya) * 0.64
                plate_hole(W, b, xc, ymid, sw / 2, (yb - ymid), d0 + 0.055, d0 + 0.10, shape, hs, "shutter", ang_n=12)
                ylow = ymid - (yb - ymid)
                if ylow > ya:
                    W.box(b, xc - sw / 2, xc + sw / 2, ya, ylow, d0 + 0.055, d0 + 0.10, "shutter", sides='otlro')
                    W.box(b, xc - 0.02, xc + 0.02, ya + 0.04, ylow - 0.04, d0 + 0.10, d0 + 0.12, "shutter_b", sides='olrt')
                    W.box(b, xc - sw / 2 + 0.05, xc + sw / 2 - 0.05, (ya + ylow) / 2 - 0.02, (ya + ylow) / 2 + 0.02, d0 + 0.10, d0 + 0.12, "shutter_b", sides='otb')
            # shutter dogs (hold-backs)
            W.box(b, xc + sx * (sw / 2 - 0.03) - 0.02, xc + sx * (sw / 2 - 0.03) + 0.02, yc - 0.04, yc + 0.04, d0 + 0.10, d0 + 0.13, "iron", sides='o')
    if flowers:
        window_box(W, fl, u - w / 2 - 0.1, u + w / 2 + 0.1, yc - h / 2 - 0.42, d0, rnd)


def window_box(W, b, u0, u1, y, d0, rnd, nhead=None):
    """Flower box on the wall with many geranium heads and leaf clumps."""
    ln = u1 - u0
    W.box(b, u0, u1, y, y + 0.26, d0 + 0.07, d0 + 0.36, "wood_dark", sides='otlrb')
    for k in range(3):   # slat lines on the front
        W.box(b, u0 - 0.003, u1 + 0.003, y + 0.04 + k * 0.075, y + 0.045 + k * 0.075, d0 + 0.36, d0 + 0.365, "wood_mid", sides='o')
    for uu in (u0 + 0.12, u1 - 0.12):
        W.box(b, uu - 0.03, uu + 0.03, y - 0.18, y, d0 + 0.0, d0 + 0.07, "iron", sides='otlr')
    W.box(b, u0 + 0.02, u1 - 0.02, y + 0.26, y + 0.30, d0 + 0.10, d0 + 0.33, "soil", sides='t')
    n = nhead or max(6, int(ln / 0.18))
    nl = max(3, int(ln / 0.4))
    mats_h = ["geranium", "pink", "geranium_b", "geranium", "white_flower"]
    for i in range(nl):
        uu = u0 + (i + 0.5) * ln / nl
        leafclump(b, tuple(W.p(uu + rnd.uniform(-0.04, 0.04), y + 0.33, d0 + rnd.uniform(0.15, 0.30))), rnd.uniform(0.08, 0.12),
                  "leaf" if i % 2 else "leaf_b")
    for i in range(n):
        uu = u0 + 0.05 + rnd.random() * (ln - 0.1)
        hh = rnd.uniform(0.38, 0.52)
        blob(b, tuple(W.p(uu, y + hh, d0 + rnd.uniform(0.14, 0.33))), rnd.uniform(0.035, 0.06), mats_h[i % len(mats_h)])
    for i in range(max(2, n // 5)):      # trailing heads over the front board
        uu = u0 + 0.1 + rnd.random() * (ln - 0.2)
        blob(b, tuple(W.p(uu, y + 0.22 + rnd.uniform(0, 0.08), d0 + 0.39)), 0.04, mats_h[i % len(mats_h)])


def mound(b, c, rad, n, nl, rnd, hs=0.07):
    """A dome of geranium heads and leaves (large planters)."""
    cx, cy, cz = c
    mats_h = ["geranium", "pink", "geranium_b", "white_flower", "geranium"]
    for i in range(nl):
        a = rnd.random() * 2 * math.pi
        r = rad * math.sqrt(rnd.random())
        leafclump(b, (cx + r * math.cos(a), cy + 0.03, cz + r * math.sin(a)), rnd.uniform(0.1, 0.16), "leaf" if i % 2 else "leaf_b")
    for i in range(n):
        a = rnd.random() * 2 * math.pi
        r = rad * math.sqrt(rnd.random())
        h = 0.10 + 0.22 * math.sqrt(max(0.0, 1 - (r / rad) ** 2))
        blob(b, (cx + r * math.cos(a), cy + h, cz + r * math.sin(a)), hs * rnd.uniform(0.8, 1.2), mats_h[i % len(mats_h)])


# ------------------------------------------------------------------ lanterns / small bits
def lantern(b, x, y, z, hang=0.0):
    """Little lantern (cap, glass, base) centred at x,y,z; optional chain of length hang above."""
    b.lathe((x, y, z), (0, 1, 0), [(0.0, -0.17), (0.05, -0.17), (0.085, -0.13), (0.085, 0.10), (0.0, 0.10)], 6, "iron")
    b.lathe((x, y + 0.01, z), (0, 1, 0), [(0.075, -0.12), (0.075, 0.1)], 6, "lantern_glass")
    b.lathe((x, y + 0.14, z), (0, 1, 0), [(0.0, 0.07), (0.05, 0.02), (0.11, -0.03), (0.11, -0.04), (0.0, -0.04)], 6, "iron")
    b.lathe((x, y + 0.21, z), (0, 1, 0), [(0.0, 0.0), (0.02, 0.0), (0.02, 0.03), (0.0, 0.03)], 4, "iron")
    if hang > 0:
        b.pipe((x, y + 0.22, z), (x, y + 0.22 + hang, z), 0.008, 3, "iron")


def baluster(b, x, y, z, h, segs=6):
    """Turned baluster (vase profile) of height h from y."""
    k = h / 0.78
    prof = [(0.020, 0.0), (0.030, 0.04), (0.020, 0.12), (0.044, 0.27), (0.022, 0.45), (0.034, 0.62), (0.030, 0.78)]
    b.lathe((x, y, z), (0, 1, 0), [(r, hh * k) for (r, hh) in prof], segs, "wood_mid")


# ------------------------------------------------------------------ main build
def build():
    mats()
    rnd = random.Random(7)
    root = empty("lodge")
    Bm, Rf, Bal, Tm, Rm, Fm, Flm, Wp, Sk, Sg, Ln = MB(), MB(), MB(), MB(), MB(), MB(), MB(), MB(), MB(), MB(), MB()
    Pm, Cb, St, Chs = MB(), MB(), MB(), MB()

    # ------------------------------------------------------------- terrace
    bx(Tm, -TX, TX, -0.42, -0.12, -TZ, TZ, "wood_dark")
    nrow = 40
    pitch = 2 * TZ / nrow
    for i in range(nrow):
        z0 = -TZ + i * pitch
        off = (i * 2.37) % 6.0
        edges = [-TX] + [e for e in (-TX + off + 6.0 * k for k in range(-1, 5)) if -TX + 0.3 < e < TX - 0.3] + [TX]
        edges = sorted(edges)
        for j in range(len(edges) - 1):
            ga = 0.006 if j > 0 else 0.0
            boxf(Tm, edges[j] + ga, edges[j + 1] - 0.006, -0.10, 0.0, z0 + 0.006, z0 + pitch - 0.006,
                 ("deck_a", "deck_b", "deck_c")[(i + j) % 3], sides='tf')
    gap = 4.2

    def stone_wall(x0, x1, z0, z1, axis):
        bx(Tm, x0, x1, -3.2, -0.42, z0, z1, "stone_b")
        rows = 3
        rh = (3.2 - 0.42) / rows
        mm = ("stone_a", "stone_b", "stone_c")
        if axis == 'z':
            ncols = max(2, int((x1 - x0) / 1.5)); cw = (x1 - x0) / ncols
            for r in range(rows):
                off = 0.0 if r % 2 == 0 else cw / 2
                for c in range(ncols + 1):
                    xa, xb = max(x0 + c * cw - off, x0), min(x0 + c * cw - off + cw, x1)
                    if xb - xa < 0.2: continue
                    y0 = -3.2 + r * rh
                    boxf(Tm, xa + 0.04, xb - 0.04, y0 + 0.04, y0 + rh - 0.04, z1, z1 + 0.07 + rnd.uniform(0, 0.05), mm[(c + r + (c * r) % 2) % 3], sides='tfrl')
        else:
            ncols = max(2, int((z1 - z0) / 1.5)); cw = (z1 - z0) / ncols
            sx = 1 if x1 > 0 else -1
            xf = x1 if sx > 0 else x0
            for r in range(rows):
                off = 0.0 if r % 2 == 0 else cw / 2
                for c in range(ncols + 1):
                    za, zb = max(z0 + c * cw - off, z0), min(z0 + c * cw - off + cw, z1)
                    if zb - za < 0.2: continue
                    y0 = -3.2 + r * rh
                    t = 0.07 + rnd.uniform(0, 0.05)
                    xa, xb = (xf, xf + t) if sx > 0 else (xf - t, xf)
                    boxf(Tm, xa, xb, y0 + 0.04, y0 + rh - 0.04, za + 0.04, zb - 0.04, mm[(c + r + (c * r) % 2) % 3], sides='tkf' + ('r' if sx > 0 else 'l'))
    stone_wall(-TX, -gap, TZ - 0.5, TZ, 'z')
    stone_wall(gap, TX, TZ - 0.5, TZ, 'z')
    stone_wall(TX - 0.5, TX, -TZ, TZ - 0.5, 'x')
    stone_wall(-TX, -TX + 0.5, -TZ, TZ - 0.5, 'x')
    for k in range(1, 5):   # stone steps down the middle
        bx(Tm, -gap, gap, -3.2, -0.42 * k, TZ + 0.5 * (k - 1), TZ + 0.5 * k, "stone_a" if k % 2 else "stone_b", bevel=0.02)
    # coping stones along the stone skirt edge (under the deck, never above y = 0)

    # ------------------------------------------------------------- terrace railings
    def rail_run(p0, p1):
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
        nbal = int(length / 0.55)
        for i in range(nbal):
            p = p0 + d * (length * (i + 0.5) / nbal)
            boxf(Rm, p.x - 0.022, p.x + 0.022, 0.08, 1.0, p.z - 0.022, p.z + 0.022, "wood_mid", sides='tfkrl')
    rail_run((-TX + 0.07, 0, TZ - 0.07), (-gap - 0.1, 0, TZ - 0.07))
    rail_run((gap + 0.1, 0, TZ - 0.07), (TX - 0.07, 0, TZ - 0.07))
    rail_run((TX - 0.07, 0, TZ - 0.07), (TX - 0.07, 0, FZ + 0.4))
    rail_run((-TX + 0.07, 0, TZ - 0.07), (-TX + 0.07, 0, FZ + 0.4))
    # steps handrails either side of the stone steps
    # ------------------------------------------------------------- building shell
    bx(Bm, -BW - 0.2, BW + 0.2, -0.2, 1.0, -16.2, FZ + 0.15, "stone_b")          # plinth core
    doorgap = 1.9
    mm = ("stone_a", "stone_b", "stone_c")
    Wf0 = Wall((0, 0, FZ), (1, 0, 0), (0, 0, 1))
    for (x0, x1) in ((-BW - 0.2, -doorgap), (doorgap, BW + 0.2)):     # coursed stone plinth, staggered
        for r in range(3):
            y0 = -0.15 + r * 0.38
            u = x0 + (0.0 if r % 2 == 0 else -0.6)
            while u < x1:
                wdt = rnd.uniform(1.0, 1.8)
                ua, ub = max(u, x0), min(u + wdt, x1)
                if ub - ua > 0.25:
                    Wf0.box(Bm, ua + 0.02, ub - 0.02, y0 + 0.02, y0 + 0.36, 0.15, 0.22 + rnd.uniform(0, 0.05), mm[rnd.randrange(3)], sides='otl')
                u += wdt
    for sx in (-1, 1):
        Ws = Wall((sx * (BW + 0.2), 0, 0), (0, 0, 1), (sx, 0, 0))
        for r in range(3):
            y0 = -0.15 + r * 0.38
            u = -16.2 + (0.0 if r % 2 == 0 else 0.7)
            while u < FZ + 0.15:
                wdt = rnd.uniform(1.0, 1.8)
                ua, ub = max(u, -16.2), min(u + wdt, FZ + 0.15)
                if ub - ua > 0.25:
                    Ws.box(Bm, ua + 0.02, ub - 0.02, y0 + 0.02, y0 + 0.36, 0.0, 0.06 + rnd.uniform(0, 0.05), mm[rnd.randrange(3)], sides='otl')
                u += wdt
    Wb = Wall((0, 0, -16.2), (1, 0, 0), (0, 0, -1))
    for r in range(3):
        y0 = -0.15 + r * 0.38
        u = -BW - 0.2 + (0.0 if r % 2 == 0 else -0.6)
        while u < BW + 0.2:
            wdt = rnd.uniform(0.9, 1.5)
            ua, ub = max(u, -BW - 0.2), min(u + wdt, BW + 0.2)
            if ub - ua > 0.25:
                Wb.box(Bm, ua + 0.02, ub - 0.02, y0 + 0.02, y0 + 0.36, 0.0, 0.06, mm[rnd.randrange(3)], sides='otl')
            u += wdt

    bx(Bm, -BW, BW, 1.0, 3.6, -16.0, FZ, "wood_dark")                 # lower storey core (shadow gaps)
    bx(Bm, -BW - 0.3, BW + 0.3, 3.6, 6.4, -16.3, FZ + 0.25, "wood_dark")   # upper storey core (jetty)
    bx(Bm, -BW - 0.3, BW + 0.3, 6.4, 7.15, -16.3 + 0.2, FZ + 0.12, "wood_dark")   # frieze up to the roof underside
    for y0, y1 in ((0.95, 1.12), (3.5, 3.72), (6.3, 6.5)):             # sill, jetty and top-plate beams
        bx(Bm, -BW - 0.35, BW + 0.35, y0, y1, FZ - 0.0, FZ + 0.32 if y0 > 3 else FZ + 0.22, "wood_dark")
    for sx in (-1, 1):
        bx(Bm, sx * BW - 0.18, sx * BW + 0.18, 1.0, 3.6, FZ, FZ + 0.2, "wood_dark")
        bx(Bm, sx * (BW + 0.3) - 0.18, sx * (BW + 0.3) + 0.18, 3.72, 6.4, FZ + 0.25, FZ + 0.45, "wood_dark")

    wins_x = (-8.0, -4.6, 4.6, 8.0)
    WL = [(Wf0, 0.0)]
    Wf1 = Wall((0, 0, FZ + 0.25), (1, 0, 0), (0, 0, 1))

    def clad_lower(W, u_lo, u_hi, y_lo, y_hi, d0, skip=None):
        pitch_ = 0.17
        n = int((y_hi - y_lo) / pitch_)
        ps = (y_hi - y_lo) / n
        for k in range(n):
            y0 = y_lo + k * ps
            u = u_lo - rnd.uniform(0, 2.0)
            while u < u_hi:
                ln = rnd.uniform(2.6, 4.4)
                ua, ub = max(u, u_lo), min(u + ln, u_hi)
                if ub - ua > 0.2:
                    W.lap_board(Bm, ua + 0.006, ub - 0.006, y0, y0 + ps + 0.03, d0, ("wood_mid", "wood_mid2", "wood_mid3")[rnd.randrange(3)])
                u += ln

    def clad_upper(W, u_lo, u_hi, y_lo, y_hi, d0, bw_=0.4):
        n = int((u_hi - u_lo) / (bw_ + 0.012))
        step = (u_hi - u_lo) / n
        for i in range(n):
            ua = u_lo + i * step
            W.box(Bm, ua + 0.008, ua + step - 0.008, y_lo, y_hi, d0, d0 + 0.045, ("wood_mid", "wood_mid2", "wood_mid3")[(i * 7 + i // 3) % 3], sides='o')
            W.box(Bm, ua + step - 0.045, ua + step + 0.045, y_lo, y_hi, d0 + 0.045, d0 + 0.075, "wood_dark", sides='olro')

    # front, lower (lap boards) and upper (board-and-batten)
    clad_lower(Wf0, -BW, BW, 1.12, 3.5, 0.0)
    clad_upper(Wf1, -BW - 0.3, BW + 0.3, 3.72, 6.3, 0.0)
    # sides
    for sx in (-1, 1):
        Wl = Wall((sx * BW, 0, 0), (0, 0, 1), (sx, 0, 0))
        Wu = Wall((sx * (BW + 0.3), 0, 0), (0, 0, 1), (sx, 0, 0))
        clad_lower(Wl, -16.0, FZ, 1.12, 3.5, 0.0)
        clad_upper(Wu, -16.3, FZ + 0.25, 3.72, 6.3, 0.0)
    Wbl = Wall((0, 0, -16.0), (1, 0, 0), (0, 0, -1))
    Wbu = Wall((0, 0, -16.3), (1, 0, 0), (0, 0, -1))
    clad_lower(Wbl, -BW, BW, 1.12, 3.5, 0.0)
    clad_upper(Wbu, -BW - 0.3, BW + 0.3, 3.72, 6.3, 0.0, bw_=0.44)

    # front windows (ground: louvre shutters + flower boxes; upper: cut-out shutters)
    for wx in wins_x:
        window(Wf0, Bm, Flm, wx, 2.3, 1.7, 1.3, 0.0, style='louvre', flowers=True, rnd=rnd)
        window(Wf1, Bm, Flm, wx, 5.3, 1.7, 1.3, 0.0, style='mix', flowers=True, rnd=rnd)
    # side windows (two per floor each side)
    for sx in (-1, 1):
        Wl = Wall((sx * BW, 0, 0), (0, 0, 1), (sx, 0, 0))
        Wu = Wall((sx * (BW + 0.3), 0, 0), (0, 0, 1), (sx, 0, 0))
        for zz in ((-8.8,) if sx < 0 else (-9.6, -13.4)):
            window(Wl, Bm, Flm, zz, 2.3, 1.3, 1.2, 0.0, style='louvre', flowers=(sx < 0), rnd=rnd, small=True)
        for zz in (-9.6, -13.4):
            window(Wu, Bm, Flm, zz, 5.2, 1.3, 1.3, 0.0, shutters=False, flowers=False, rnd=rnd, small=True)

    # gable ends: pentagon infill, board-and-batten, bracing, diamond window
    ridge_z, ridge_y = -11.5, 9.9
    alpha = math.radians(28.0)
    sa, ca = math.sin(alpha), math.cos(alpha)
    for sx in (-1, 1):
        x0, x1 = sorted((sx * (BW + 0.3), sx * (BW + 0.7)))
        pent = lambda x: [Vector((x, 6.4, FZ + 0.25)), Vector((x, 7.12, FZ + 0.25)), Vector((x, 9.62, ridge_z)),
                          Vector((x, 7.10, -16.3)), Vector((x, 6.4, -16.3))]
        Bm.loft([pent(x0), pent(x1)], "wood_dark")
        Wg = Wall((sx * (BW + 0.7), 0, 0), (0, 0, 1), (sx, 0, 0))

        def ytop(z):
            if z > ridge_z:
                return 7.12 + (9.62 - 7.12) * ((FZ + 0.25 - z) / (FZ + 0.25 - ridge_z))
            return 9.62 - (9.62 - 7.10) * ((ridge_z - z) / (ridge_z + 16.3))
        z = -16.15
        i = 0
        while z < FZ + 0.15:
            yt = ytop(z) - 0.06
            if yt > 6.5:
                Wg.box(Bm, z - 0.14, z + 0.14, 6.4, yt, 0.0, 0.03, ("wood_mid", "wood_mid2", "wood_mid3")[i % 3], sides='o')
                Wg.box(Bm, z + 0.14 - 0.03, z + 0.14 + 0.03, 6.4, yt, 0.0, 0.05, "wood_dark", sides='olro')
            z += 0.28 + 0.0
            i += 1
        # cross bracing, centre post, collar
        for zz in (-9.2, -13.8):
            Bm.pipe((sx * (BW + 0.78), 6.5, zz), (sx * (BW + 0.78), 8.15, ridge_z + (zz - ridge_z) * 0.35), 0.07, 4, "wood_dark")
        Bm.pipe((sx * (BW + 0.78), 6.45, ridge_z), (sx * (BW + 0.78), 9.45, ridge_z), 0.08, 4, "wood_dark")
        Wg2 = Wall((sx * (BW + 0.78), 0, 0), (0, 0, 1), (sx, 0, 0))
        Wg2.box(Bm, ridge_z - 2.5, ridge_z + 2.5, 7.0 - 0.1, 7.0, 0.0, 0.07, "wood_dark", sides='otlro')
        # diamond window with frame and bars
        dw = 0.75
        ring = [(ridge_z, 7.0 + 0.9 + 0.0), (ridge_z + dw, 7.0 + 0.9 + dw * 0), ]
        cy = 8.0
        pts = [(ridge_z, cy - 0.7), (ridge_z + 0.7, cy), (ridge_z, cy + 0.7), (ridge_z - 0.7, cy)]
        Bm.loft([[Vector((sx * (BW + 0.78) + sx * 0.0, y, z_)) for (z_, y) in pts],
                 [Vector((sx * (BW + 0.9), y, z_)) for (z_, y) in pts]], "wood_light")
        Bm.face([Vector((sx * (BW + 0.905), cy + k * 0.58, ridge_z + j * 0.58)) for (j, k) in ((0, -1), (1, 0), (0, 1), (-1, 0))], "glass", hint=(sx, 0, 0))
        Bm.box((sx * (BW + 0.92), cy, ridge_z), (0.03, 1.15, 0.04), "wood_light")
        Bm.box((sx * (BW + 0.92), cy, ridge_z), (0.03, 0.04, 1.15), "wood_light")

    # ------------------------------------------------------------- entrance
    D0 = 0.26
    bx(Bm, -1.35, 1.35, D0, 2.95, FZ - 0.02, FZ + 0.14, "wood_light")               # frame
    Wd = Wall((0, 0, FZ), (1, 0, 0), (0, 0, 1))
    for sx in (-1, 1):
        uc = sx * 0.62
        Wd.box(Bm, uc - 0.55, uc + 0.55, D0 + 0.0, 2.7, 0.14, 0.20, "wood_dark", sides='otlr')
        for (ya, yb, nm) in ((D0 + 0.12, 1.25, "wood_mid"), (1.4, 2.4, None), (2.45, 2.62, "wood_mid")):
            if nm:
                Wd.box(Bm, uc - 0.4, uc + 0.4, ya, yb, 0.20, 0.235, nm, sides='otlro')
        Wd.quad(Bm, [(uc - 0.35, 1.5, 0.206), (uc + 0.35, 1.5, 0.206), (uc + 0.35, 2.35, 0.206), (uc - 0.35, 2.35, 0.206)], "glass", Wd.n)
        Wd.box(Bm, uc - 0.38, uc + 0.38, 1.46, 1.5, 0.20, 0.235, "wood_light", sides='otlr')
        Wd.box(Bm, uc - 0.38, uc + 0.38, 2.35, 2.39, 0.20, 0.235, "wood_light", sides='otlr')
        Wd.box(Bm, uc - 0.02, uc + 0.02, 1.5, 2.35, 0.20, 0.235, "wood_light", sides='olr')
    for xx in (-0.1, 0.1):
        Wd.box(Bm, xx - 0.025, xx + 0.025, 1.0, 1.25, 0.2, 0.28, "steel", sides='otlro')
    # carved door header board with a heart cut-out (dark inset behind)
    Wd.box(Bm, -0.5, 0.5, 3.0, 3.35, 0.08, 0.1, "interior", sides='o')
    plate_hole(Wd, Bm, 0.0, 3.17, 0.5, 0.17, 0.10, 0.14, 'heart', 0.12, "wood_light", ang_n=12)
    # stone entrance step (big blocks, bevelled) and threshold
    for (xa, xb, ya, yb, za, zb, nm) in ((-1.9, -0.6, -0.05, 0.12, FZ + 0.45, FZ + 1.2, "stone_a"), (-0.6, 0.65, -0.05, 0.12, FZ + 0.45, FZ + 1.2, "stone_c"),
                                         (0.65, 1.9, -0.05, 0.12, FZ + 0.45, FZ + 1.2, "stone_a"),
                                         (-1.55, -0.1, 0.12, 0.26, FZ + 0.04, FZ + 0.72, "stone_c"), (-0.1, 1.55, 0.12, 0.26, FZ + 0.04, FZ + 0.72, "stone_a")):
        Bm.box(((xa + xb) / 2, (ya + yb) / 2, (za + zb) / 2), (xb - xa - 0.03, yb - ya, zb - za - 0.03), nm, bevel=0.03)
    bx(Bm, -1.2, 1.2, 0.26, 0.3, FZ + 0.12, FZ + 0.24, "steel_dark")
    # wall lanterns either side of the door
    for sx in (-1, 1):
        Ln.box((sx * 1.65, 2.55, FZ + 0.12), (0.05, 0.3, 0.06), "iron")
        Ln.pipe((sx * 1.65, 2.62, FZ + 0.12), (sx * 1.65, 2.62, FZ + 0.42), 0.015, 3, "iron")
        lantern(Ln, sx * 1.65, 2.42, FZ + 0.42)

    # ------------------------------------------------------------- balcony
    ztip = FZ + 1.75
    xe = BW + 0.3
    bx(Bal, -xe, xe, 3.5, 3.72, FZ + 0.25, ztip, "wood_light")
    for i in range(1, 8):                                  # deck plank lines
        zz = FZ + 0.25 + i * (ztip - FZ - 0.25) / 8
        bx(Bal, -xe, xe, 3.718, 3.722, zz - 0.006, zz + 0.006, "wood_dark")
    for x in [-9.0 + i * 3.0 for i in range(7)]:          # carved knee-brace brackets (curved profile)
        pts = [(2.85, FZ + 0.25), (3.5, FZ + 0.25), (3.5, ztip - 0.15)]
        for k in range(1, 6):
            t = k / 6.0
            pts.append((3.5 - 0.65 * (1 - math.cos(t * math.pi / 2)), ztip - 0.15 - (ztip - 0.4 - FZ) * math.sin(t * math.pi / 2)))
        r0 = [Vector((x - 0.05, y, z)) for (y, z) in pts]
        r1 = [Vector((x + 0.05, y, z)) for (y, z) in pts]
        Bal.loft([r0, r1], "wood_dark")
    # cut-out fascia panels under the deck edge (hearts and diamonds), thin scalloped trim beneath
    Wfa = Wall((0, 0, ztip), (1, 0, 0), (0, 0, 1))
    npan = int(2 * xe / 1.2)
    pw = 2 * xe / npan
    for i in range(npan):
        uc = -xe + (i + 0.5) * pw
        Wfa.box(Bal, uc - pw / 2, uc + pw / 2, 3.1, 3.72, -0.12, -0.115, "interior", sides='o')
        plate_hole(Wfa, Bal, uc, 3.41, pw / 2 - 0.02, 0.31, -0.115, -0.07, 'heart' if i % 2 == 0 else 'diamond', 0.24 if i % 2 == 0 else 0.25, "wood_light", ang_n=8)
    for i in range(int(2 * xe / 0.6)):                    # scalloped drip trim
        uc = -xe + (i + 0.5) * 0.6
        Wfa.tri_prism(Bal, [(3.1, -0.115), (3.1, -0.06), (2.95, -0.09)], uc - 0.27, uc + 0.27, "wood_dark")
    # balustrade: end posts, intermediate posts, turned balusters, top and bottom rails, rail cap
    pz = ztip - 0.07
    nbal = int((2 * xe) / 0.66)
    for i in range(nbal):
        xx = -xe + (i + 0.5) * 2 * xe / nbal
        baluster(Bal, xx, 3.95, pz, 0.62, segs=5)
    for x in [-xe + 0.1 + i * (2 * xe - 0.2) / 7 for i in range(8)]:
        bx(Bal, x - 0.065, x + 0.065, 3.72, 4.62, pz - 0.065, pz + 0.065, "wood_dark")
        Bal.lathe((x, 4.62, pz), (0, 1, 0), [(0.0, 0.0), (0.07, 0.0), (0.05, 0.05), (0.045, 0.1), (0.07, 0.13), (0.0, 0.18)], 6, "wood_light")
    bx(Bal, -xe, xe, 3.72, 3.95, pz - 0.05, pz + 0.05, "wood_light")   # base rail
    bx(Bal, -xe, xe, 4.57, 4.69, pz - 0.09, pz + 0.09, "wood_light")   # top rail
    bx(Bal, -xe, xe, 4.69, 4.72, pz - 0.115, pz + 0.115, "wood_dark")  # rail cap
    for sx in (-1, 1):                                     # side returns with balusters
        xs = sx * xe
        for i in range(4):
            zz = FZ + 0.25 + (i + 0.5) * (ztip - FZ - 0.25 - 0.1) / 4
            baluster(Bal, xs - sx * 0.065, 3.95, zz, 0.62, segs=6)
        bx(Bal, xs - 0.05, xs + 0.05, 3.72, 3.95, FZ + 0.25, ztip, "wood_light")
        bx(Bal, xs - 0.09, xs + 0.09, 4.57, 4.69, FZ + 0.25, ztip, "wood_light")
    # balcony door
    Wbd = Wall((0, 0, FZ + 0.25), (1, 0, 0), (0, 0, 1))
    Wbd.box(Bm, -1.3, 1.3, 3.72, 6.05, 0.0, 0.14, "wood_light", sides='otlr')
    Wbd.box(Bm, -1.1, 1.1, 3.82, 5.95, 0.12, 0.16, "interior", sides='o')
    Wbd.quad(Bm, [(-1.0, 3.9, 0.17), (1.0, 3.9, 0.17), (1.0, 5.85, 0.17), (-1.0, 5.85, 0.17)], "glass", Wbd.n)
    Wbd.box(Bm, -0.03, 0.03, 3.9, 5.85, 0.16, 0.2, "wood_light", sides='olr')
    for yy in (4.45, 5.1):
        Wbd.box(Bm, -1.0, 1.0, yy - 0.025, yy + 0.025, 0.16, 0.2, "wood_light", sides='otb')
    # bunting along the balcony rail, flagpole at the right end
    cols = ["pennant_a", "pennant_b", "pennant_c", "pennant_d"]
    n = 34
    for i in range(n):
        xx = -BW + 0.3 + i * (2 * BW - 0.6) / (n - 1)
        sag = 0.28 * math.sin(math.pi * ((i * 3.0) % (n / 3.0)) / (n / 3.0))
        y = 4.55 - sag
        Bal.face([(xx - 0.15, y, ztip + 0.03), (xx + 0.15, y, ztip + 0.03), (xx, y - 0.36, ztip + 0.03)], cols[i % 4], hint=(0, 0, 1))
    Bal.pipe((9.9, 3.7, ztip - 0.15), (9.9, 8.6, ztip - 0.15), 0.035, 5, "steel")
    Bal.lathe((9.9, 8.6, ztip - 0.15), (0, 1, 0), [(0.0, 0.0), (0.05, 0.0), (0.0, 0.1)], 5, "steel")
    Bal.face([(9.93, 8.55, ztip - 0.15), (10.8, 8.35, ztip - 0.15), (9.93, 8.0, ztip - 0.15)], "pennant_a", hint=(0, 0, 1))
    # lanterns on the balcony end posts
    for sx in (-1, 1):
        Ln.pipe((sx * (xe - 0.1), 4.72, pz), (sx * (xe - 0.1), 5.0, pz), 0.015, 3, "iron")
        lantern(Ln, sx * (xe - 0.1), 4.82, pz, hang=0.0)

    # ------------------------------------------------------------- hanging blank sign (under the balcony)
    sx0, sy0, sz0 = 2.35, 2.2, FZ + 1.2
    for dx in (-0.32, 0.32):
        Sg.pipe((sx0 + dx, 3.4, sz0), (sx0 + dx, sy0 + 0.72, sz0), 0.012, 3, "iron")
    shield = lambda zo: [Vector((sx0 + dx, sy0 + dy, sz0 + zo)) for dx, dy in
                         ((-0.4, 0.7), (-0.33, 0.74), (0.33, 0.74), (0.4, 0.7), (0.4, 0.15), (0.24, 0.0), (0.0, -0.05), (-0.24, 0.0), (-0.4, 0.15))]
    Sg.loft([shield(-0.025), shield(0.025)], "sign_board")
    rim = lambda zo, s_: [Vector((sx0 + dx * s_, sy0 + 0.35 + (dy - 0.35) * s_, sz0 + zo)) for dx, dy in
                          ((-0.4, 0.7), (-0.33, 0.74), (0.33, 0.74), (0.4, 0.7), (0.4, 0.15), (0.24, 0.0), (0.0, -0.05), (-0.24, 0.0), (-0.4, 0.15))]
    Sg.loft([rim(0.025, 1.0), rim(0.04, 0.9)], "wood_dark", caps=False, solid=False)
    Sg.face(rim(0.04, 0.9), "sign_board", hint=(0, 0, 1))
    for dx in (-0.32, 0.32):
        Sg.lathe((sx0 + dx, sy0 + 0.74, sz0), (0, 0, 1), [(0.03, -0.04), (0.03, 0.04)], 6, "iron")

    # ------------------------------------------------------------- roof
    slope_len = abs(ridge_z - (-5.2)) / ca
    RW = 11.5
    for s in (1, -1):
        d = Vector((0, -sa, s * ca))
        n_ = Vector((0, ca, s * sa))
        top = Vector((0, ridge_y, ridge_z))
        P = lambda x, t, h, d=d, n_=n_, top=top: Vector((x, 0, 0)) + top + d * t + n_ * h
        ctr = top + d * (slope_len / 2) - n_ * 0.15
        Rf.box(ctr, (2 * RW, 0.30, slope_len + 0.2), "shingle_dark", rot=Matrix.Rotation(s * alpha, 3, 'X'))
        rows = int(slope_len / 0.5)
        ps = slope_len / rows
        ncols = int(2 * RW / 0.8)
        px_ = 2 * RW / ncols
        for k in range(rows):
            t0, t1 = k * ps, (k + 1) * ps
            half = (k % 2) * px_ / 2
            u = -RW - half
            ci = 0
            while u < RW - 0.01:
                xa, xb = max(u + 0.015, -RW), min(u + px_ - 0.015, RW)
                if xb - xa > 0.08:
                    m = ("shingle_a", "shingle_b", "shingle_c")[(ci * 5 + k * 3 + (ci // 4)) % 3]
                    Rf.face([P(xa, t0, 0.012), P(xb, t0, 0.012), P(xb, t1, 0.065), P(xa, t1, 0.065)], m, hint=n_)
                    Rf.face([P(xa, t1, 0.012), P(xb, t1, 0.012), P(xb, t1, 0.065), P(xa, t1, 0.065)], m, hint=d)
                u += px_
                ci += 1
        # eaves fascia board, gutter
        E = top + d * slope_len
        Rf.box(E + Vector((0, -0.18, s * 0.05)), (2 * RW + 0.2, 0.36, 0.06), "wood_dark")
        Rf.box(E + Vector((0, -0.40, s * 0.02)), (2 * RW + 0.2, 0.05, 0.12), "wood_mid")      # drip board
        Rf.pipe((-RW - 0.05, E.y - 0.34, E.z + s * 0.14), (RW + 0.05, E.y - 0.34, E.z + s * 0.14), 0.06, 6, "steel")
        for dx in (-RW, RW):
            Rf.box((dx, E.y - 0.34, E.z + s * 0.14), (0.02, 0.15, 0.15), "steel")
        # rafter tails under the overhang
        for i in range(int(2 * RW / 1.2) + 1):
            x = -RW + 0.1 + i * 1.2
            tt = slope_len - 1.05
            Rf.box(top + d * (tt + 0.45) - n_ * 0.40 + Vector((x, 0, 0)), (0.11, 0.16, 1.5), "wood_dark", rot=Matrix.Rotation(s * alpha, 3, 'X'))
        # barge boards with pendants and purlin ends
        for sx in (-1, 1):
            xa, xb = sorted((sx * (RW + 0.0), sx * (RW + 0.14)))
            ring = lambda t, xa=xa, xb=xb: [P(xa, t, -0.16), P(xb, t, -0.16), P(xb, t, 0.17), P(xa, t, 0.17)]
            Rf.loft([ring(-0.05), ring(slope_len + 0.05)], "wood_dark")
            for q in range(int((slope_len - 0.3) / 0.8)):
                t = 0.2 + q * 0.8
                tri = lambda x, t=t: [P(x, t, -0.16), P(x, t + 0.34, -0.16), P(x, t + 0.17, -0.40)]
                Rf.loft([tri(xa), tri(xb)], "wood_mid")
            for t in (1.2, 3.1, 5.0, 6.6):
                p = P(sx * (RW - 0.35), t, -0.26)
                Rf.box(p + Vector((sx * 0.30, 0, 0)), (1.0, 0.17, 0.17), "wood_dark")
        # snow guards: two rails on brackets
        for tt in (slope_len - 1.0, slope_len - 2.2):
            Rf.pipe(P(-RW + 0.3, tt, 0.17), P(RW - 0.3, tt, 0.17), 0.018, 4, "steel")
            for i in range(int((2 * RW - 0.6) / 1.9) + 1):
                x = -RW + 0.3 + i * 1.9
                Rf.face([P(x - 0.03, tt - 0.1, 0.065), P(x + 0.03, tt - 0.1, 0.065), P(x + 0.03, tt + 0.02, 0.19), P(x - 0.03, tt + 0.02, 0.19)], "steel_dark", hint=d - n_)
                Rf.face([P(x - 0.03, tt - 0.1, 0.065), P(x - 0.03, tt + 0.02, 0.19), P(x - 0.03, tt + 0.02, 0.065)], "steel_dark", hint=(-1, 0, 0))
                Rf.face([P(x + 0.03, tt - 0.1, 0.065), P(x + 0.03, tt + 0.02, 0.19), P(x + 0.03, tt + 0.02, 0.065)], "steel_dark", hint=(1, 0, 0))
    # ridge cap: overlapped inverted-V sections
    for i in range(int(2 * RW / 0.9)):
        xa = -RW + i * 0.9
        ring = lambda x: [Vector((x, ridge_y + 0.02, ridge_z - 0.46)), Vector((x, ridge_y + 0.17, ridge_z)), Vector((x, ridge_y + 0.02, ridge_z + 0.46)),
                          Vector((x, ridge_y - 0.04, ridge_z + 0.44)), Vector((x, ridge_y + 0.11, ridge_z)), Vector((x, ridge_y - 0.04, ridge_z - 0.44))]
        Rf.loft([ring(xa), ring(xa + 0.96)], "wood_dark" if i % 2 else "wood_mid2")
    # dormers on the front slope
    for dxc in (-6.3, 6.3):
        zf = -7.55
        yb = ridge_y - math.tan(alpha) * (zf - ridge_z) - 0.35
        wy = 8.8
        Wdm = Wall((dxc, 0, zf), (1, 0, 0), (0, 0, 1))
        Wdm.box(Rf, -0.75, 0.75, yb, wy, -0.1, 0.0, "wood_mid", sides='o')
        for i in range(-2, 3):
            Wdm.box(Rf, i * 0.3 - 0.035, i * 0.3 + 0.035, yb, wy, 0.0, 0.03, "wood_dark", sides='olro')
        for sxx in (-1, 1):                                   # cheeks
            boxf(Rf, dxc + sxx * 0.75 - 0.05, dxc + sxx * 0.75 + 0.05, yb, wy, zf - 2.9, zf, "wood_mid", sides='rlf')
        # gable triangle + barge boards + roof panels
        Wdm.tri_prism(Rf, [(wy, -0.1), (wy, 0.0), (wy + 0.65, -0.05)], -0.75, 0.75, "wood_mid")
        for sxx in (-1, 1):
            A = (dxc + sxx * 0.95, wy - 0.05)
            R = (dxc, wy + 0.78)
            dv = Vector((R[0] - A[0], R[1] - A[1])); nv = Vector((-dv.y, dv.x)).normalized()
            if nv.y < 0: nv = -nv
            ring = lambda z, A=A, R=R, nv=nv: [Vector((A[0], A[1], z)), Vector((R[0], R[1], z)), Vector((R[0] + nv.x * 0.07, R[1] + nv.y * 0.07, z)), Vector((A[0] + nv.x * 0.07, A[1] + nv.y * 0.07, z))]
            Rf.loft([ring(zf + 0.12), ring(zf - 3.0)], "shingle_a")
            for q in range(1, 4):
                f = q / 4.0
                pa = Vector((A[0] + (R[0] - A[0]) * f, A[1] + (R[1] - A[1]) * f))
                Rf.box((pa.x + nv.x * 0.075, pa.y + nv.y * 0.075, zf - 1.4), (0.05, 0.04, 3.0), "shingle_b" if q % 2 else "shingle_c",
                       rot=Matrix.Rotation(math.atan2(dv.y, dv.x) , 3, 'Z'))
        Rf.pipe((dxc, wy + 0.8, zf + 0.12), (dxc, wy + 0.98, zf + 0.12), 0.02, 4, "wood_dark")
        Rf.lathe((dxc, wy + 0.98, zf + 0.12), (0, 1, 0), [(0.0, 0.0), (0.04, 0.03), (0.0, 0.1)], 5, "wood_dark")
        window(Wdm, Rf, Flm, 0.0, wy - 0.62, 0.62, 0.62, 0.0, shutters=False, flowers=True, rnd=rnd)
    # chimney: coursed stone, cap, flue pots
    cw_, ccx, ccz = 1.5, 7.55, -13.05
    bx(Rf, ccx - cw_ / 2 + 0.05, ccx + cw_ / 2 - 0.05, 7.6, 11.0, ccz - cw_ / 2 + 0.05, ccz + cw_ / 2 - 0.05, "stone_b")
    faces = [Wall((ccx, 0, ccz + cw_ / 2), (1, 0, 0), (0, 0, 1)), Wall((ccx, 0, ccz - cw_ / 2), (1, 0, 0), (0, 0, -1)),
             Wall((ccx + cw_ / 2, 0, ccz), (0, 0, 1), (1, 0, 0)), Wall((ccx - cw_ / 2, 0, ccz), (0, 0, 1), (-1, 0, 0))]
    for fi, Wc in enumerate(faces):
        y = 8.5 if fi != 1 else 8.3
        row = 0
        while y < 10.95:
            hh = rnd.uniform(0.24, 0.36)
            u = -cw_ / 2 - (0.0 if row % 2 == 0 else rnd.uniform(0.1, 0.4))
            while u < cw_ / 2:
                wdt = rnd.uniform(0.5, 0.85)
                ua, ub = max(u, -cw_ / 2), min(u + wdt, cw_ / 2)
                if ub - ua > 0.12:
                    Wc.box(Rf, ua + 0.012, ub - 0.012, y + 0.012, min(y + hh, 11.0) - 0.012, 0.0, 0.05 + rnd.uniform(0, 0.03),
                           mm[rnd.randrange(3)], sides='otl')
                u += wdt
            y += hh
            row += 1
    bx(Rf, ccx - 1.0, ccx + 1.0, 11.0, 11.18, ccz - 1.0, ccz + 1.0, "stone_a", bevel=0.02)
    bx(Rf, ccx - 0.88, ccx + 0.88, 11.18, 11.3, ccz - 0.88, ccz + 0.88, "stone_b")
    for fx in (-0.38, 0.38):
        Rf.lathe((ccx + fx, 11.3, ccz), (0, 1, 0), [(0.2, 0.0), (0.2, 0.3), (0.24, 0.32), (0.24, 0.38), (0.17, 0.38), (0.17, 0.3)], 8, "clay", closed=False)
        Rf.lathe((ccx + fx, 11.78, ccz), (0, 1, 0), [(0.0, 0.0), (0.3, 0.0), (0.0, 0.16)], 8, "steel_dark")
        for k in (-1, 1):
            Rf.pipe((ccx + fx + k * 0.17, 11.68, ccz), (ccx + fx + k * 0.17, 11.8, ccz), 0.012, 3, "steel_dark")

    # ------------------------------------------------------------- terrace furniture
    def cafe_chair(x, z, yaw):
        org = (x, 0, z)
        for lx in (-0.18, 0.18):
            rbox(Fm, org, (lx, 0.22, 0.18), (0.035, 0.44, 0.035), "wood_dark", yaw)
            rbox(Fm, org, (lx, 0.45, -0.19), (0.035, 0.9, 0.035), "wood_dark", yaw)
        rbox(Fm, org, (0, 0.46, 0), (0.44, 0.04, 0.44), "wood_light", yaw)
        for yy in (0.66, 0.84):
            rbox(Fm, org, (0, yy, -0.19), (0.38, 0.08, 0.025), "wood_light", yaw)

    def round_table(px, pz):
        Fm.lathe((px, 0, pz), (0, 1, 0), [(0.0, 0.0), (0.26, 0.0), (0.26, 0.03), (0.05, 0.08), (0.05, 0.68), (0.30, 0.7), (0.62, 0.72),
                                         (0.64, 0.74), (0.62, 0.77), (0.0, 0.77)], 8, "wood_light")
        Fm.lathe((px, 0.77, pz), (0, 1, 0), [(0.04, 0.0), (0.04, 0.02)], 6, "iron")

    def parasol(px, pz, tilt_a):
        Fm.pipe((px, 0.0, pz), (px, 3.0, pz), 0.035, 6, "steel")
        Fm.lathe((px, 0, pz), (0, 1, 0), [(0.0, 0.0), (0.35, 0.0), (0.35, 0.08), (0.0, 0.1)], 8, "concrete")
        R0, R1 = 1.6, 0.85
        for i in range(8):
            a0, a1 = 2 * math.pi * i / 8 + tilt_a, 2 * math.pi * (i + 1) / 8 + tilt_a
            m_ = "parasol_a" if i % 2 == 0 else "parasol_b"
            top = (px, 3.02, pz)
            mid0 = (px + R1 * math.cos(a0), 2.82, pz + R1 * math.sin(a0)); mid1 = (px + R1 * math.cos(a1), 2.82, pz + R1 * math.sin(a1))
            e0 = (px + R0 * math.cos(a0), 2.48, pz + R0 * math.sin(a0)); e1 = (px + R0 * math.cos(a1), 2.48, pz + R0 * math.sin(a1))
            Fm.face([top, mid0, mid1], m_, hint=(0, 1, 0))
            Fm.face([mid0, e0, e1, mid1], m_, hint=(0, 1, 0))
            am = (a0 + a1) / 2
            for q in range(2):    # scalloped valance flaps
                fa = a0 + (a1 - a0) * (q * 0.5)
                fb = a0 + (a1 - a0) * (q * 0.5 + 0.5)
                pa = (px + R0 * math.cos(fa), 2.48, pz + R0 * math.sin(fa)); pb = (px + R0 * math.cos(fb), 2.48, pz + R0 * math.sin(fb))
                pm_ = (px + (R0 + 0.02) * math.cos((fa + fb) / 2), 2.33, pz + (R0 + 0.02) * math.sin((fa + fb) / 2))
                Fm.face([pa, pb, pm_], m_, hint=(math.cos(am), 0.2, math.sin(am)))
            if i % 2 == 0:
                Fm.pipe((px, 2.99, pz), e0, 0.008, 3, "wood_light")        # rib
        Fm.lathe((px, 3.0, pz), (0, 1, 0), [(0.0, 0.0), (0.05, 0.03), (0.0, 0.13)], 6, "wood_dark")

    for (px, pz) in ((-9.0, 3.2), (-9.0, -2.4), (9.0, 3.2), (9.0, -2.4)):
        round_table(px, pz)
        parasol(px, pz, 0.2)
        for k in range(3):
            a = k * 2.1 + 0.5
            cafe_chair(px + 1.05 * math.cos(a), pz + 1.05 * math.sin(a), math.atan2(-math.cos(a), -math.sin(a)))

    def beer_set(cx, cz):
        Fm.box((cx, 0.76, cz), (2.4, 0.05, 0.8), "wood_light")
        for k in (-1, 1):
            xx = cx + k * 0.9
            rbox(Fm, (xx, 0, cz), (0, 0.38, 0.0), (0.06, 0.76, 0.06), "wood_dark")
            Fm.box((xx, 0.35, cz), (0.07, 0.07, 0.72), "wood_dark")
            for zs in (-1, 1):
                Fm.pipe((xx, 0.0, cz + zs * 0.36), (xx, 0.72, cz + zs * 0.08), 0.03, 4, "wood_dark")
        Fm.box((cx, 0.3, cz), (1.9, 0.05, 0.06), "wood_dark")
        for zs in (-1, 1):
            zz = cz + zs * 0.72
            Fm.box((cx, 0.46, zz), (2.3, 0.05, 0.3), "wood_light")
            for k in (-1, 1):
                Fm.box((cx + k * 0.9, 0.22, zz), (0.07, 0.44, 0.26), "wood_dark")
    beer_set(-4.4, 1.3)
    beer_set(4.4, 1.3)
    for bxp in (-5.2, 5.2):      # benches against the building
        z = FZ + 0.45
        bx(Fm, bxp - 1.1, bxp + 1.1, 0.42, 0.50, z - 0.22, z + 0.22, "wood_light")
        bx(Fm, bxp - 1.1, bxp + 1.1, 0.75, 1.15, z - 0.26, z - 0.20, "wood_light")
        for sx in (-1, 1):
            bx(Fm, bxp + sx * 0.95 - 0.05, bxp + sx * 0.95 + 0.05, 0, 0.42, z - 0.2, z + 0.2, "wood_dark")
            bx(Fm, bxp + sx * 0.95 - 0.04, bxp + sx * 0.95 + 0.04, 0.42, 1.15, z - 0.27, z - 0.19, "wood_dark")
    # barrel planters with geraniums: either side of the door and at the front corners
    def barrel(px, pz, r, h, nflow):
        Fm.lathe((px, 0, pz), (0, 1, 0), [(0.0, 0.0), (r * 0.82, 0.0), (r * 0.95, h * 0.35), (r, h * 0.6), (r * 0.92, h), (0.0, h)], 10, "wood_light")
        for yy, rr in ((h * 0.18, 0.9), (h * 0.8, 0.96)):
            Fm.lathe((px, yy - 0.015, pz), (0, 1, 0), [(r * rr + 0.01, 0.0), (r * rr + 0.01, 0.03)], 10, "iron")
        Fm.lathe((px, h - 0.01, pz), (0, 1, 0), [(0.0, 0.0), (r * 0.9, 0.0)], 10, "soil")
        mound(Flm, (px, h, pz), r * 0.85, nflow, 5, rnd)
    for (px, pz) in ((-2.6, FZ + 0.75), (2.6, FZ + 0.75), (-11.2, 6.0), (11.2, 6.0)):
        barrel(px, pz, 0.42, 0.62, 14)
    # ski rack (summer: a few skis and poles) beside the left terrace rail
    rx, rz0, rz1 = -11.25, -5.6, -2.9
    for zz in (rz0, rz1):
        bx(Sk, rx - 0.07, rx + 0.07, 0, 1.55, zz - 0.07, zz + 0.07, "wood_dark")
        bx(Sk, rx - 0.09, rx + 0.09, 1.55, 1.6, zz - 0.09, zz + 0.09, "wood_light")
    bx(Sk, rx - 0.05, rx + 0.05, 1.1, 1.2, rz0, rz1, "wood_dark")
    bx(Sk, rx - 0.22, rx + 0.22, 0.3, 0.38, rz0, rz1, "wood_dark")
    for k in range(6):
        zz = rz0 + 0.3 + k * (rz1 - rz0 - 0.6) / 5
        for dx, mm_ in ((-0.045, "chair_paint"), (0.045, "steel_dark")):
            Sk.box((rx + dx, 0.95, zz), (0.015, 1.65, 0.08), mm_, rot=Matrix.Rotation(math.radians(5 * (1 if k % 2 else -1) * 0), 3, 'Z'))
            Sk.box((rx + dx, 1.82, zz), (0.015, 0.14, 0.08), mm_, rot=Matrix.Rotation(0.0, 3, 'Z'))
            Sk.box((rx + dx, 1.05, zz), (0.05, 0.14, 0.05), "iron")
    for k in range(4):
        zz = rz0 + 0.45 + k * 0.62
        Sk.pipe((rx + 0.16, 0.0, zz), (rx + 0.04, 1.35, zz), 0.011, 3, "steel")
        Sk.lathe((rx + 0.04, 1.35, zz), (0, 1, 0), [(0.0, 0.0), (0.025, 0.0), (0.02, 0.09)], 5, "chair_paint")
    # woodpile under a lean-to against the west gable
    wx0, wx1 = -BW - 0.2, -BW - 2.7
    wz0, wz1 = -15.4, -11.0
    bx(Wp, wx1 - 0.1, wx0, -0.25, 0.04, wz0 - 0.1, wz1 + 0.1, "wood_dark")            # pallet base
    for zz in (wz0 - 0.05, wz1 + 0.05, (wz0 + wz1) / 2):
        bx(Wp, wx1 - 0.05, wx1 + 0.1, 0.04, 2.5, zz - 0.07, zz + 0.07, "wood_dark")   # front posts
    bx(Wp, wx1 - 0.08, wx0, 2.36, 2.5, wz0 - 0.1, wz1 + 0.1, "wood_dark")            # wall plate
    for i in range(7):
        zz = wz0 - 0.1 + i * (wz1 - wz0 + 0.2) / 6
        Wp.box((wx0 / 2 + wx1 / 2 - 0.05, 2.9 - 0.0, zz), (2.0, 0.1, 0.1), "wood_dark",
               rot=Matrix.Rotation(0.0, 3, 'Z'))
    # lean-to roof: sloped slab from the wall (high) outwards (low), with shingle strips
    pl = [Vector((wx0, 3.0, z_)) for z_ in (wz0 - 0.3, wz1 + 0.3)]
    rr = lambda x, y, thk: [Vector((x, y, wz0 - 0.3)), Vector((x, y, wz1 + 0.3)), Vector((x, y - thk, wz1 + 0.3)), Vector((x, y - thk, wz0 - 0.3))]
    Wp.loft([rr(wx0, 2.95, 0.12), rr(wx1 - 0.3, 2.5, 0.12)], "shingle_dark")
    for k in range(5):
        t0, t1 = k / 5.0, (k + 1) / 5.0
        xa, xb = wx0 + (wx1 - 0.3 - wx0) * t0, wx0 + (wx1 - 0.3 - wx0) * t1
        ya, yb = 2.95 + (2.5 - 2.95) * t0, 2.95 + (2.5 - 2.95) * t1
        for q in range(9):
            za = wz0 - 0.3 + q * (wz1 - wz0 + 0.6) / 9
            zb = za + (wz1 - wz0 + 0.6) / 9 - 0.02
            m = ("shingle_a", "shingle_b", "shingle_c")[(k * 3 + q) % 3]
            Wp.face([Vector((xa, ya + 0.01, za)), Vector((xa, ya + 0.01, zb)), Vector((xb, yb + 0.05, zb)), Vector((xb, yb + 0.05, za))], m, hint=(0, 1, 0))
            Wp.face([Vector((xb, yb, za)), Vector((xb, yb, zb)), Vector((xb, yb + 0.05, zb)), Vector((xb, yb + 0.05, za))], m, hint=(-1, 0, 0))
    # stacked logs: ends facing west (-x) and a dark core behind them
    bx(Wp, wx0 - 0.5, wx0, 0.04, 1.95, wz0, wz1, "log_bark")
    rowh = 0.24
    nrow = int(1.9 / rowh)
    for rrw in range(nrow):
        y = 0.04 + rowh / 2 + rrw * rowh
        zz = wz0 + 0.1 + (0.09 if rrw % 2 else 0.0)
        while zz < wz1 - 0.09:
            r = rnd.uniform(0.085, 0.1)
            xc = wx0 - 0.5 - rnd.uniform(0.0, 0.07)
            ring = lambda x: [Vector((x, y + r * math.sin(a), zz + r * math.cos(a))) for a in [2 * math.pi * i / 5 for i in range(5)]]
            Wp.loft([ring(wx0 - 0.02), ring(xc)], "log_bark", caps=False, solid=False)
            Wp.face(ring(xc), "log_end", hint=(-1, 0, 0))
            zz += 0.245
    # chopping block + split logs beside the pile
    Wp.lathe((wx1 - 0.7, 0.04, -9.0), (0, 1, 0), [(0.0, 0.0), (0.28, 0.0), (0.28, 0.42), (0.0, 0.42)], 8, "log_bark")
    Wp.lathe((wx1 - 0.7, 0.46, -9.0), (0, 1, 0), [(0.0, 0.0), (0.27, 0.0)], 8, "log_end")

    # ------------------------------------------------------------- chairlift (pylon, cable, station, chairs)
    pylon(Pm, PX, 0.0, -1.3, standalone=False)
    cable_lines(Cb, PX)
    station(St, rnd)
    # chairs: chair_a / chair_b swing nodes, others static on the carrier line
    chairs = []
    for name, cx, cz, face in (("chair_a", PX - CAB_X, -5.5, -1), ("chair_b", PX + CAB_X, 6.5, 1)):
        ch = MB()
        chair(ch, cx, cab_y(cz), cz, face)
        chairs.append((name, ch, (cx, cab_y(cz), cz)))
    for cx, cz, face in ((PX - CAB_X, -12.0, -1), (PX + CAB_X, -15.0, 1)):
        chair(Chs, cx, cab_y(cz), cz, face, lite=True)

    # ------------------------------------------------------------- nodes
    for mb_, nm in ((Bm, "lodge_building"), (Rf, "lodge_roof"), (Bal, "lodge_balcony"), (Tm, "lodge_terrace"), (Rm, "lodge_railings"),
                    (Fm, "lodge_furniture"), (Flm, "lodge_flowers"), (Wp, "lodge_woodpile"), (Sk, "lodge_skirack"), (Sg, "lodge_sign"),
                    (Ln, "lodge_lanterns"), (Pm, "chairlift_pylon"), (Cb, "chairlift_cable"), (St, "chairlift_station"), (Chs, "chairlift_chairs")):
        mb_.to_object(nm, parent=root, smooth=None)
    for name, ch, org in chairs:
        ch.to_object(name, origin=org, parent=root, smooth=None)


# ------------------------------------------------------------------ chairlift pieces
def pylon(b, cx, cz, y0, standalone=False):
    """Four-legged lattice pylon, ~11 m: base y0, crossarm at y0 + 10.2, cable at y0 + 11.0 (x = cx +- CAB_X)."""
    hx0, hz0, hx1, hz1 = 1.35, 1.05, 0.55, 0.34
    yb, yt = y0 + 0.35, y0 + 10.2

    def at(y, sx, sz):
        t = (y - yb) / (yt - yb)
        return (cx + sx * (hx0 + (hx1 - hx0) * t), y, cz + sz * (hz0 + (hz1 - hz0) * t))
    corners = [(1, 1), (-1, 1), (1, -1), (-1, -1)]
    # footing and base plates
    if standalone:
        bx(b, cx - 1.75, cx + 1.75, y0, y0 + 0.35, cz - 1.45, cz + 1.45, "concrete")
    else:
        bx(b, cx - 1.75, cx + 1.75, y0 - 1.9, y0 + 0.35, cz - 1.45, cz + 1.45, "concrete")
    for sx, sz in corners:
        p = at(yb, sx, sz)
        bx(b, p[0] - 0.22, p[0] + 0.22, yb, yb + 0.05, p[2] - 0.22, p[2] + 0.22, "steel_dark")
        for bx_, bz_ in ((-0.15, -0.15), (0.15, -0.15), (-0.15, 0.15), (0.15, 0.15)):
            b.lathe((p[0] + bx_, yb + 0.05, p[2] + bz_), (0, 1, 0), [(0.025, 0.0), (0.025, 0.04)], 4, "steel")
        b.pipe(at(yb + 0.05, sx, sz), at(yt, sx, sz), 0.085, 6, "steel")
    n = 8
    ys = [yb + 0.45 + i * (yt - yb - 0.45) / (n - 1) for i in range(n)]
    for y in ys:
        for (a, c) in (((1, 1), (-1, 1)), ((1, -1), (-1, -1)), ((1, 1), (1, -1)), ((-1, 1), (-1, -1))):
            b.pipe(at(y, *a), at(y, *c), 0.05, 3, "steel_dark")
    for i in range(n - 1):
        for (a, c) in (((1, 1), (-1, 1)), ((1, -1), (-1, -1)), ((1, 1), (1, -1)), ((-1, 1), (-1, -1))):
            b.pipe(at(ys[i], *a), at(ys[i + 1], *c), 0.035, 3, "steel_dark")
            b.pipe(at(ys[i], *c), at(ys[i + 1], *a), 0.035, 3, "steel_dark")
    # ladder on the +z face
    def zface(y, dz=0.2):
        t = (y - yb) / (yt - yb)
        return cz + hz0 + (hz1 - hz0) * t + dz
    ladder = []
    ya, yz = yb + 0.6, yt - 0.3
    for sx in (-1, 1):
        b.pipe((cx + sx * 0.28, ya, zface(ya)), (cx + sx * 0.28, yz, zface(yz)), 0.022, 4, "steel")
    nr = int((yz - ya) / 0.32)
    for i in range(nr + 1):
        y = ya + i * (yz - ya) / nr
        b.pipe((cx - 0.28, y, zface(y)), (cx + 0.28, y, zface(y)), 0.016, 3, "steel")
    for i in range(0, nr, 4):        # stand-offs
        y = ya + i * (yz - ya) / nr
        for sx in (-1, 1):
            b.pipe((cx + sx * 0.28, y, zface(y)), (cx + sx * 0.28, y, zface(y, -0.2)), 0.015, 3, "steel")
    # top platform, rails
    py = yt - 0.55
    bx(b, cx - 0.8, cx + 0.8, py, py + 0.05, cz + hz1, cz + 1.2, "steel_dark")
    for dx in (-0.8, 0.8):
        b.pipe((cx + dx, py + 0.05, cz + 1.2), (cx + dx, py + 0.95, cz + 1.2), 0.02, 4, "steel")
        b.pipe((cx + dx, py + 0.95, cz + hz1), (cx + dx, py + 0.95, cz + 1.2), 0.02, 4, "steel")
    b.pipe((cx - 0.8, py + 0.95, cz + 1.2), (cx + 0.8, py + 0.95, cz + 1.2), 0.02, 4, "steel")
    b.pipe((cx - 0.8, py + 0.5, cz + 1.2), (cx + 0.8, py + 0.5, cz + 1.2), 0.015, 3, "steel")
    # tower head, crossarm (I-beam), gussets, knee braces
    bx(b, cx - 0.75, cx + 0.75, yt - 0.1, yt + 0.0, cz - 0.55, cz + 0.55, "steel_dark")
    ca_y0, ca_y1 = yt - 0.05, yt + 0.3
    bx(b, cx - 3.75, cx + 3.75, ca_y0, ca_y0 + 0.04, cz - 0.17, cz + 0.17, "steel_dark")
    bx(b, cx - 3.75, cx + 3.75, ca_y1 - 0.04, ca_y1, cz - 0.17, cz + 0.17, "steel_dark")
    bx(b, cx - 3.75, cx + 3.75, ca_y0 + 0.04, ca_y1 - 0.04, cz - 0.03, cz + 0.03, "steel_dark")
    for sx in (-1, 1):
        for sz in (-1, 1):
            b.pipe((cx + sx * 0.6, yt - 0.85, cz + sz * 0.3), (cx + sx * 3.0, ca_y0, cz + sz * 0.1), 0.045, 4, "steel_dark")
        for xx in (1.0, 2.0, 3.2):
            bx(b, cx + sx * xx - 0.02, cx + sx * xx + 0.02, ca_y0 + 0.04, ca_y1 - 0.04, cz - 0.17, cz + 0.17, "steel_dark")
    # sheave trains: balance beam, two bogies each carrying two grooved wheels, rope guards
    yc = y0 + 11.0
    wprof = [(0.0, -0.07), (0.20, -0.07), (0.20, -0.045), (0.155, -0.02), (0.155, 0.02), (0.20, 0.045), (0.20, 0.07), (0.0, 0.07)]
    for sx in (-1, 1):
        xc = cx + sx * CAB_X
        bx(b, xc - 0.1, xc + 0.1, ca_y1, ca_y1 + 0.12, cz - 0.15, cz + 0.15, "steel_dark")
        b.box((xc, ca_y1 + 0.2, cz), (0.12, 0.1, 2.0), "steel", bevel=0.01)
        for sz in (-1, 1):
            zb = cz + sz * 0.85
            b.box((xc, ca_y1 + 0.26, zb), (0.1, 0.08, 0.8), "steel_dark")
            for dz in (-0.2, 0.2):
                zw = zb + dz
                b.lathe((xc, yc - 0.18, zw), (1, 0, 0), wprof, 10, "rubber")
                b.lathe((xc, yc - 0.18, zw), (1, 0, 0), [(0.0, -0.1), (0.05, -0.1), (0.05, 0.1), (0.0, 0.1)], 6, "steel")
                for kk in (-1, 1):
                    b.box((xc + kk * 0.085, yc - 0.18 - 0.07, zw), (0.02, 0.28, 0.06), "steel_dark")
        for kk in (-1, 1):
            b.pipe((xc + kk * 0.22, yc + 0.11, cz - 0.95), (xc + kk * 0.22, yc + 0.11, cz + 0.95), 0.015, 3, "steel")
            for zz in (-0.95, 0.0, 0.95):
                b.pipe((xc + kk * 0.22, yc - 0.45, cz + zz), (xc + kk * 0.22, yc + 0.11, cz + zz), 0.012, 3, "steel") if zz else None
    if standalone:
        for sx in (-1, 1):
            b.pipe((cx + sx * CAB_X, yc, cz - 4.0), (cx + sx * CAB_X, yc, cz + 4.0), 0.03, 5, "steel_dark")


def cable_lines(b, cx):
    """Both cable lines from the far downhill end to the bullwheel, wrapped around it."""
    for sx in (-1, 1):
        x = cx + sx * CAB_X
        b.pipe((x, Y_CAB, 30.0), (x, Y_CAB, Z_SLOPE0), 0.03, 5, "steel_dark")
        b.pipe((x, Y_CAB, Z_SLOPE0), (x, Y_E, Z_E), 0.03, 5, "steel_dark")
    seg = 12
    for i in range(seg):
        a0, a1 = math.pi * i / seg, math.pi * (i + 1) / seg
        b.pipe((cx + CAB_X * math.cos(a0), Y_E, Z_E - CAB_X * math.sin(a0)), (cx + CAB_X * math.cos(a1), Y_E, Z_E - CAB_X * math.sin(a1)), 0.03, 5, "steel_dark")


def chair(b, ox, oy, oz, facing=1, lite=False):
    """A fixed-grip chair on its hanger. Origin (ox, oy, oz) is the cable grip; hanger runs down -Y.
    Seat width is across the line (X); the passengers face +Z when facing = 1."""
    R = Matrix.Rotation(0.0 if facing >= 0 else math.pi, 3, 'Y')

    def T(x, y, z):
        v = R @ Vector((x, y, z))
        return (ox + v.x, oy + v.y, oz + v.z)

    def bxx(c, size, m, tilt=None):
        rot = R if tilt is None else R @ tilt
        b.box(T(*c), size, m, rot=rot)

    def pp(p0, p1, r, m, segs=5):
        b.pipe(T(*p0), T(*p1), r, segs, m)
    SY = -2.5
    bxx((0, 0.0, 0), (0.16, 0.14, 0.28), "steel_dark")                                   # grip body
    bxx((0, 0.0, 0), (0.22, 0.04, 0.3), "steel")                                         # clamp plate
    for zz in (-0.1, 0.1):
        b.lathe(T(0.1, 0.0, zz), R @ Vector((1, 0, 0)), [(0.022, 0.0), (0.022, 0.05)], 6, "steel")
    bxx((0, -0.15, 0), (0.1, 0.18, 0.1), "steel_dark")                                   # neck
    pp((0, -0.2, 0), (0, SY - 0.02, 0), 0.03, "steel", 6)                                # hanger rod
    bxx((0, SY - 0.04, 0.12), (0.2, 0.1, 0.3), "steel_dark")                             # bracket under the seat
    pp((-0.93, SY, 0.04), (0.93, SY, 0.04), 0.03, "steel")                               # rear seat tube
    pp((-0.93, SY, 0.6), (0.93, SY, 0.6), 0.028, "steel")                                # front seat tube
    for sx in (-1, 1):
        pp((sx * 0.93, SY, 0.04), (sx * 0.93, SY, 0.6), 0.026, "steel")
    bxx((0, SY + 0.05, 0.32), (1.8, 0.06, 0.56), "chair_seat")                           # seat pad
    for k in (-1, 0, 1):
        bxx((k * 0.6, SY + 0.085, 0.32), (0.02, 0.012, 0.5), "steel_dark")
    tb = Matrix.Rotation(-0.2, 3, 'X') if facing >= 0 else Matrix.Rotation(-0.2, 3, 'X')
    bxx((0, SY + 0.37, 0.07), (1.8, 0.62, 0.07), "chair_paint", tilt=tb)                 # back rest (leans back)
    for sx in (-1, 1):
        pp((sx * 0.8, SY + 0.04, 0.1), (sx * 0.8, SY + 0.56, -0.02), 0.024, "steel_dark")  # back stays
        pp((sx * 0.95, SY + 0.5, -0.02), (sx * 0.95, SY + 0.5, 0.58), 0.024, "steel")      # armrests
        pp((sx * 0.95, SY + 0.5, 0.58), (sx * 0.95, SY + 0.03, 0.58), 0.024, "steel")
        pp((sx * 0.95, SY + 0.5, -0.02), (sx * 0.95, SY + 0.05, 0.05), 0.024, "steel")
        if not lite:
            pp((sx * 0.8, SY + 0.0, 0.6), (sx * 0.8, SY - 0.4, 0.68), 0.02, "steel")       # footrest hangers
    if not lite:
        pp((-0.8, SY - 0.4, 0.68), (0.8, SY - 0.4, 0.68), 0.022, "steel")                  # footrest


def station(b, rnd):
    """Top station: concrete podium with timber deck, steel and timber frame, canopy, bullwheel, operator's cabin,
    turnstile, cable guides, rails and a blank name board."""
    cx, ze, ye = PX, Z_E, Y_E
    deck = 1.4
    zf, zb = -12.0, -27.0
    # podium: concrete core with stone facing blocks, timber deck on top
    bx(b, cx - 5.2, cx + 5.2, -3.0, deck, zb, zf, "concrete")
    mm = ("stone_a", "stone_b", "stone_c")
    Wps = [Wall((cx, 0, zf), (1, 0, 0), (0, 0, 1)), Wall((cx - 5.2, 0, 0), (0, 0, 1), (-1, 0, 0)), Wall((cx + 5.2, 0, 0), (0, 0, 1), (1, 0, 0))]
    lens = [(-5.2, 5.2), (zb, zf), (zb, zf)]
    for Wq, (ua, ub_) in zip(Wps, lens):
        for r in range(4):
            y0 = deck - 0.7 - r * 0.7
            u = ua - (0.0 if r % 2 == 0 else 0.5)
            while u < ub_:
                wdt = rnd.uniform(1.1, 1.9)
                a_, c_ = max(u, ua), min(u + wdt, ub_)
                if c_ - a_ > 0.25:
                    Wq.box(b, a_ + 0.02, c_ - 0.02, y0 + 0.02, y0 + 0.68, 0.0, 0.07 + rnd.uniform(0, 0.05), mm[rnd.randrange(3)], sides='ot')
                u += wdt
    for i in range(int((zf - zb) / 0.2)):
        z0 = zb + i * 0.2
        for (x0, x1) in ((cx - 5.2, cx + 5.2),):
            boxf(b, x0, x1, deck, deck + 0.06, z0 + 0.005, z0 + 0.195, ("deck_a", "deck_b", "deck_c")[i % 3], sides='tf')
    bx(b, cx - 5.25, cx + 5.25, deck, deck + 0.08, zf - 0.05, zf + 0.0, "safety_yellow")      # edge band
    for k in range(3):                                                            # exit steps (front, centre)
        bx(b, cx - 1.7, cx + 1.7, deck - 0.45 * (k + 1), deck - 0.45 * k, zf, zf + 0.5 * (k + 1), "stone_a" if k % 2 else "stone_c", bevel=0.02)
    # frame: six timber columns on steel shoes, steel cross beams, wall plates
    colx = (cx - 4.2, cx + 4.2)
    colz = (-14.4, -20.4, -26.4)
    ytop = 7.3
    for x in colx:
        for z in colz:
            bx(b, x - 0.17, x + 0.17, deck + 0.08, ytop, z - 0.17, z + 0.17, "wood_mid2")
            bx(b, x - 0.24, x + 0.24, deck + 0.08, deck + 0.2, z - 0.24, z + 0.24, "steel_dark")
            bx(b, x - 0.22, x + 0.22, ytop, ytop + 0.1, z - 0.22, z + 0.22, "steel_dark")
    for z in colz:
        bx(b, cx - 4.4, cx + 4.4, ytop + 0.1, ytop + 0.4, z - 0.12, z + 0.12, "steel_dark")
        for sx in (-1, 1):                  # knee braces
            b.pipe((cx + sx * 4.2, ytop - 1.0, z), (cx + sx * 3.2, ytop + 0.1, z), 0.06, 4, "wood_dark")
    for x in colx:
        bx(b, x - 0.12, x + 0.12, ytop + 0.1, ytop + 0.4, colz[-1] - 0.17, colz[0] + 0.17, "wood_dark")
    # canopy roof (gable along z): slabs, shingle rows, ridge board, rafters, blank name board on the front
    rise, half, ey = 1.35, 5.3, ytop + 0.4
    zfr, zbk = -13.2, -27.5
    for sx in (-1, 1):
        A = (cx + sx * half, ey)
        R_ = (cx, ey + rise)
        dv = Vector((R_[0] - A[0], R_[1] - A[1])); nv = Vector((-dv.y, dv.x)).normalized()
        if nv.y < 0: nv = -nv
        ring = lambda z: [Vector((A[0], A[1], z)), Vector((R_[0], R_[1], z)), Vector((R_[0] + nv.x * 0.1, R_[1] + nv.y * 0.1, z)), Vector((A[0] + nv.x * 0.1, A[1] + nv.y * 0.1, z))]
        b.loft([ring(zfr), ring(zbk)], "shingle_dark")
        for q in range(6):
            f0, f1 = q / 6.0, (q + 1) / 6.0 - 0.02
            pa = lambda f, hh: Vector((R_[0] + (A[0] - R_[0]) * f + nv.x * hh, R_[1] + (A[1] - R_[1]) * f + nv.y * hh))
            for zz in range(0, 11):
                za = zfr - zz * (zfr - zbk) / 11.0
                zb_ = za - (zfr - zbk) / 11.0 + 0.04
                m = ("shingle_a", "shingle_b", "shingle_c")[(q + zz * 2) % 3]
                b.face([(pa(f0, 0.11).x, pa(f0, 0.11).y, za), (pa(f0, 0.11).x, pa(f0, 0.11).y, zb_), (pa(f1, 0.14).x, pa(f1, 0.14).y, zb_), (pa(f1, 0.14).x, pa(f1, 0.14).y, za)], m, hint=(nv.x, nv.y, 0))
        for i in range(8):                  # rafter tails
            z = zfr - 0.3 - i * (zfr - zbk - 0.6) / 7
            b.box((A[0] + sx * 0.25, A[1] - 0.07, z), (0.7, 0.1, 0.12), "wood_dark")
    b.box((cx, ey + rise + 0.1, (zfr + zbk) / 2), (0.3, 0.16, zfr - zbk + 0.3), "wood_dark")
    # front gable fill with a blank board
    for z in (zfr + 0.02,):
        b.loft([[Vector((cx - half, ey, z)), Vector((cx + half, ey, z)), Vector((cx, ey + rise, z))],
                [Vector((cx - half, ey, z - 0.12)), Vector((cx + half, ey, z - 0.12)), Vector((cx, ey + rise, z - 0.12))]], "wood_mid")
    Wn = Wall((cx, 0, zfr + 0.02), (1, 0, 0), (0, 0, 1))
    Wn.box(b, -2.2, 2.2, ey + 0.2, ey + 0.82, 0.0, 0.08, "sign_board", sides='otblr')
    Wn.box(b, -2.3, 2.3, ey + 0.15, ey + 0.2, 0.0, 0.1, "wood_dark", sides='otblr')
    Wn.box(b, -2.3, 2.3, ey + 0.82, ey + 0.87, 0.0, 0.1, "wood_dark", sides='otblr')
    # bullwheel: grooved rim, hub, spokes, shaft, gearbox
    prof = [(2.28, -0.14), (2.58, -0.14), (2.58, 0.2), (2.46, 0.2), (2.46, 0.07), (2.28, 0.07)]
    b.lathe((cx, ye - 0.1, ze), (0, 1, 0), prof, 24, "steel_dark", closed=True)
    b.lathe((cx, ye - 0.1, ze), (0, 1, 0), [(0.0, -0.2), (0.45, -0.2), (0.45, 0.25), (0.0, 0.25)], 12, "steel")
    for i in range(8):
        a = 2 * math.pi * i / 8 + 0.2
        b.pipe((cx + 0.4 * math.cos(a), ye - 0.1, ze + 0.4 * math.sin(a)), (cx + 2.3 * math.cos(a), ye - 0.1, ze + 2.3 * math.sin(a)), 0.07, 4, "steel")
    b.pipe((cx, deck, ze), (cx, ye + 0.5, ze), 0.2, 8, "steel_dark")
    bx(b, cx - 1.0, cx + 1.0, deck, deck + 1.5, ze - 1.0, ze + 1.0, "steel_dark", bevel=0.05)
    bx(b, cx - 0.7, cx + 0.7, deck + 1.5, ye - 0.35, ze - 0.7, ze + 0.7, "steel", bevel=0.05)
    # operator's cabin behind the wheel, windows facing the platform
    cz0, cz1 = -26.8, -24.8
    bx(b, cx - 1.5, cx + 1.5, deck + 0.08, 4.1, cz0, cz1, "wood_dark")
    Wc = Wall((cx, 0, cz1), (1, 0, 0), (0, 0, 1))
    clad = 0
    for k in range(12):
        Wc.box(b, -1.5 + k * 0.25, -1.5 + (k + 1) * 0.25 - 0.01, deck + 0.12, 3.9, 0.0, 0.04, ("wood_mid", "wood_mid2", "wood_mid3")[k % 3], sides='o')
    Wc.box(b, -1.2, 1.2, 2.3, 3.3, 0.0, 0.1, "wood_light", sides='otlr')
    Wc.quad(b, [(-1.1, 2.4, 0.09), (1.1, 2.4, 0.09), (1.1, 3.2, 0.09), (-1.1, 3.2, 0.09)], "glass", Wc.n)
    Wc.box(b, -0.03, 0.03, 2.4, 3.2, 0.09, 0.12, "wood_light", sides='olr')
    Wc.box(b, -1.65, 1.65, 3.9, 4.0, -0.15, 0.5, "wood_dark", sides='otlrb')
    Wc.box(b, -1.0, -0.2, deck + 0.08, 2.1, 0.0, 0.06, "wood_dark", sides='o')        # door
    for k in range(0, 3):
        zz = cz1 - 0.2 - k * 0.55
    # turnstile and barrier at the exit lane, with rails along both lanes
    tz = zf - 0.0 - 1.4
    bx(b, cx - 0.12, cx + 0.12, deck + 0.08, deck + 1.0, tz - 0.12, tz + 0.12, "steel_dark")
    for k in range(3):
        a = 2 * math.pi * k / 3 + 0.3
        b.pipe((cx, deck + 0.95, tz), (cx + 0.55 * math.cos(a), deck + 0.95 - 0.1 * 0 + 0.0, tz + 0.55 * math.sin(a)), 0.025, 4, "steel")
    b.lathe((cx, deck + 1.0, tz), (0, 1, 0), [(0.0, 0.0), (0.14, 0.0), (0.1, 0.06), (0.0, 0.06)], 6, "steel_dark")
    for sx in (-1, 1):
        for q in range(2):
            xx = cx + sx * 0.85
            tzz = tz + (q - 0.5) * 0.0
        b.pipe((cx + sx * 0.9, deck + 0.08, tz + 0.0), (cx + sx * 0.9, deck + 1.1, tz), 0.04, 5, "steel")
        b.pipe((cx + sx * 0.9, deck + 1.05, tz), (cx + sx * 0.9, deck + 1.05, tz - 4.0), 0.025, 4, "steel")
        b.pipe((cx + sx * 0.9, deck + 0.55, tz), (cx + sx * 0.9, deck + 0.55, tz - 4.0), 0.02, 4, "steel")
        for zz in (tz - 2.0, tz - 4.0):
            b.pipe((cx + sx * 0.9, deck + 0.08, zz), (cx + sx * 0.9, deck + 1.05, zz), 0.03, 4, "steel")
    # perimeter fence rails along both platform sides
    for sx in (-1, 1):
        x = cx + sx * 5.0
        for z in [zf - 0.3 - i * 2.4 for i in range(7)]:
            b.pipe((x, deck + 0.08, z), (x, deck + 1.1, z), 0.035, 4, "steel")
        b.pipe((x, deck + 1.1, zf - 0.3), (x, deck + 1.1, zf - 14.7), 0.03, 4, "steel")
        b.pipe((x, deck + 0.6, zf - 0.3), (x, deck + 0.6, zf - 14.7), 0.022, 4, "steel")
    # cable guides: sheave batteries hung under the cross beams, one pair of rollers each side of each line
    for z in (-14.4, -20.4):
        for sx in (-1, 1):
            xl = cx + sx * CAB_X
            yc = cab_y(z)
            bx(b, xl - 0.05, xl + 0.05, yc + 0.15, ytop + 0.1, z - 0.05, z + 0.05, "steel_dark")
            bx(b, xl - 0.4, xl + 0.4, yc + 0.08, yc + 0.18, z - 0.1, z + 0.1, "steel_dark")
            for k in (-1, 1):
                b.lathe((xl + k * 0.22, yc, z), (0, 1, 0), [(0.0, -0.07), (0.07, -0.07), (0.07, 0.07), (0.0, 0.07)], 6, "rubber")
                b.pipe((xl + k * 0.22, yc - 0.1, z), (xl + k * 0.22, yc + 0.1, z), 0.015, 3, "steel")
    # roller batteries on the approach tower legs (small, sloping with the line)
    for sx in (-1, 1):
        xl = cx + sx * CAB_X
        for z in (-16.4, -18.4):
            yc = cab_y(z)
            bx(b, xl - 0.3, xl + 0.3, yc + 0.14, yc + 0.22, z - 0.08, z + 0.08, "steel_dark")
    # lanterns on the front columns
    # (kept inside the station node)
    for x in colx:
        z = colz[0]
        b.pipe((x, ytop - 0.6, z + 0.17), (x, ytop - 0.6, z + 0.35), 0.015, 3, "iron")
        lantern(b, x, ytop - 0.77, z + 0.35)
    # stacked passenger bench near the exit lane
    bx(b, cx + 3.2, cx + 4.7, deck + 0.46, deck + 0.52, zf - 1.0, zf - 0.6, "wood_light")
    for xx in (cx + 3.3, cx + 4.6):
        bx(b, xx - 0.04, xx + 0.04, deck + 0.08, deck + 0.46, zf - 0.95, zf - 0.65, "wood_dark")


# ------------------------------------------------------------------ stand-alone models
def build_chairlift_pylon():
    """pylon-only model: origin at base centre on the ground, ~11 m tall, cable direction along Z."""
    mats()
    b = MB()
    pylon(b, 0.0, 0.0, 0.0, standalone=True)
    b.to_object("chairlift_pylon", origin=(0, 0, 0), smooth=None)


def build_chair():
    """single chair on its hanger: origin at the cable grip, hanger hangs down -Y, passengers face +Z."""
    mats()
    b = MB()
    chair(b, 0.0, 0.0, 0.0, 1)
    b.to_object("chair", origin=(0, 0, 0), smooth=None)
