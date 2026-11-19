"""Police helicopter prop: an original light utility helicopter in a made-up patrol livery.

Game frame (+X helicopter's left, +Y up, +Z nose).  `fuselage` origin is at the cabin centre
(0, 0, 0); skid tube bottoms sit at y = -1.0.  Livery: fluorescent yellow-green (`hivis`) and dark
blue (`navy`) blocks with chevrons on the boom, no text, crest or roundel.

Nodes (all children of `heli`, origins in heli space):
  fuselage      (0, 0, 0)            hull, glass, interior, crew, cowl, boom, fin, stabilisers, mast, yoke
  rotor_main    (0, 1.95, -0.70)     on the mast axis at the hub; spins about Y (3 blades, 120 deg symmetric)
  rotor_tail    (0.20, 1.10, -6.95)  at its hub; spins about X (2 blades, 180 deg symmetric)
  spotlight     (0, -0.82, 1.50)     nose-mounted pod, origin at the gimbal pivot; lens material `spot_lens`
  camera_ball   (0.42, -0.80, 1.15)  sensor turret (extra), origin at the ball centre
  skids         (0, 0, 0)            two skid tubes and four cross-tube arches
  nav_red / nav_green / strobe       small emissive lamps, origins at their centres
"""
import math
from mathutils import Vector, Matrix
from gtl import MB, make_mat, empty, bx
from propkit import limb, tube, loft_mat, blob

HUB_MAIN = (0.0, 1.95, -0.70)
HUB_TAIL = (0.20, 1.10, -6.95)
PIVOT = (0.0, -0.82, 1.50)
BALL = (0.42, -0.80, 1.15)
NAV_RED = (0.50, 0.90, -0.30)       # left (+X) roof edge
NAV_GREEN = (-0.50, 0.90, -0.30)    # right
STROBE = (0.0, 1.76, -6.96)

# --------------------------------------------------------------------------- hull sections
# (z, top, bottom, half-width, superellipse exponent); sampled with a monotone cubic
KEYS = [
    (2.20, -0.12, -0.36, 0.06, 2.0),
    (2.00, 0.28, -0.52, 0.42, 2.2),
    (1.60, 0.68, -0.64, 0.70, 2.3),
    (1.00, 0.88, -0.68, 0.84, 2.5),
    (0.30, 0.95, -0.70, 0.88, 2.6),
    (-0.50, 0.95, -0.70, 0.86, 2.6),
    (-1.10, 0.90, -0.66, 0.80, 2.6),
    (-1.70, 0.76, -0.55, 0.62, 2.8),
    (-2.40, 0.66, -0.22, 0.40, 3.0),
    (-3.10, 0.68, -0.04, 0.31, 3.2),
    (-5.00, 0.66, 0.12, 0.25, 3.4),
    (-7.00, 0.60, 0.26, 0.10, 3.4),
]
S = [2.20, 2.10, 1.95, 1.75, 1.50, 1.25] + [round(1.0 - 0.25 * k, 3) for k in range(17)] + \
    [-3.5, -4.0, -4.5, -5.0, -5.5, -6.0, -6.5, -7.0]
NRING = 16


def sect(z):
    ks = KEYS
    s = -z
    xs = [-k[0] for k in ks]
    if s <= xs[0]:
        return ks[0][1:]
    if s >= xs[-1]:
        return ks[-1][1:]
    for k in range(len(ks) - 1):
        if xs[k] <= s <= xs[k + 1]:
            break
    out = []
    h = xs[k + 1] - xs[k]
    t = (s - xs[k]) / h
    for c in range(1, 5):
        def slope(a):
            if a == 0 or a == len(ks) - 1:
                b = a + 1 if a == 0 else a - 1
                return (ks[b][c] - ks[a][c]) / (xs[b] - xs[a])
            d0 = (ks[a][c] - ks[a - 1][c]) / (xs[a] - xs[a - 1])
            d1 = (ks[a + 1][c] - ks[a][c]) / (xs[a + 1] - xs[a])
            return 0.0 if d0 * d1 <= 0 else (d0 + d1) / 2
        p0, p1 = ks[k][c], ks[k + 1][c]
        m0, m1 = slope(k), slope(k + 1)
        h00, h10, h01, h11 = 2 * t ** 3 - 3 * t ** 2 + 1, t ** 3 - 2 * t ** 2 + t, -2 * t ** 3 + 3 * t ** 2, t ** 3 - t ** 2
        out.append(h00 * p0 + h10 * h * m0 + h01 * p1 + h11 * h * m1)
    return tuple(out)


def _se(v, e):
    return math.copysign(abs(v) ** (2.0 / e), v)


def ring(z, n=NRING):
    top, bot, w, e = sect(z)
    cy, h = (top + bot) / 2, (top - bot) / 2
    pts = []
    for j in range(n):
        a = 2 * math.pi * j / n
        pts.append(Vector((w * _se(math.cos(a), e), cy + h * _se(math.sin(a), e), z)))
    return pts


_RINGS = {}


def station_ring(i):
    if i not in _RINGS:
        _RINGS[i] = ring(S[i])
    return _RINGS[i]


def surf_x(z, y):
    """x of the +X hull side at height y and position z, following the faceted loft."""
    i = 0
    while i < len(S) - 2 and S[i + 1] > z:
        i += 1
    t = (S[i] - z) / (S[i] - S[i + 1])
    xs = []
    for r in (station_ring(i), station_ring(i + 1)):
        best = 0.0
        for a in range(len(r)):
            p, q = r[a], r[(a + 1) % len(r)]
            if p.x > 0.01 or q.x > 0.01:
                if (p.y - y) * (q.y - y) <= 0 and abs(q.y - p.y) > 1e-9:
                    u = (y - p.y) / (q.y - p.y)
                    best = max(best, p.x + (q.x - p.x) * u)
        xs.append(best)
    return xs[0] + (xs[1] - xs[0]) * t


# --------------------------------------------------------------------------- materials
def materials():
    make_mat("hivis", "#c6ee0c", rough=0.42, double=True)
    make_mat("navy", "#0b1f4d", rough=0.38, metallic=0.1, double=True)
    make_mat("glass", "#a8cfe0", rough=0.05, alpha=0.30)
    make_mat("steel", "#9aa1a9", metallic=0.75, rough=0.38)
    make_mat("dark", "#1d2024", rough=0.65)
    make_mat("door_line", "#0c0e11", rough=0.7)
    make_mat("skid", "#2c3036", metallic=0.4, rough=0.5)
    make_mat("blade", "#1b1d22", rough=0.55)
    make_mat("seat", "#30343c", rough=0.8)
    make_mat("panel", "#2a3a4e", rough=0.3, metallic=0.2)
    make_mat("vest", "#d4f21a", rough=0.7)
    make_mat("crew_suit", "#17254f", rough=0.8)
    make_mat("boots", "#14161a", rough=0.7)
    make_mat("helmet", "#eef0f2", rough=0.3)
    make_mat("visor", "#0b1218", metallic=0.7, rough=0.08)
    make_mat("exhaust", "#59534d", metallic=0.6, rough=0.5)
    make_mat("cam_lens", "#0a1220", metallic=0.6, rough=0.06)
    make_mat("spot_lens", "#fff3d2", rough=0.2, emit="#fff0c0", emit_strength=1.0)
    make_mat("nav_red", "#ff2a1f", rough=0.3, emit="#ff1a10", emit_strength=1.0)
    make_mat("nav_green", "#1fff55", rough=0.3, emit="#10ff40", emit_strength=1.0)
    make_mat("strobe", "#ffffff", rough=0.3, emit="#ffffff", emit_strength=1.0)


# --------------------------------------------------------------------------- fuselage
def hull_mat(i, j):
    zm = (S[i] + S[i + 1]) * 0.5
    upper = j < NRING // 2
    band = {8: 0, 15: 0, 9: 1, 14: 1}
    if zm > -0.95:
        if upper:
            if j in (3, 4) and zm < 0.75:
                return 'hivis'
            if j not in (3, 4) and abs(zm + 0.375) < 0.01:
                return 'navy'
            return 'glass'
        if zm <= 1.0 and j in band:
            return 'hivis' if (int(math.floor((1.0 - zm) / 0.5)) + band[j]) % 2 == 0 else 'navy'
        return 'navy'
    if upper:
        return 'hivis'
    if zm > -2.8 and j in band:
        return 'hivis' if (int(math.floor((1.0 - zm) / 0.5)) + band[j]) % 2 == 0 else 'navy'
    return 'navy' if zm > -3.0 else 'hivis'


def bar(m, p0, p1, r, mat, segs=6):
    limb(m, p0, p1, r, r, segs, mat)


def decal(m, pts, mat, sx):
    """Quad lying on the hull side (pts are (z, y, x) triples), normal outward (sign sx)."""
    m.face([Vector((p[2], p[1], p[0])) for p in pts], mat, hint=(sx, 0, 0))


def hull(m):
    rings = [station_ring(i) for i in range(len(S))]
    loft_mat(m, rings, hull_mat)
    # door lines (dark) on both sides: a door frame below the sill
    for sx in (1, -1):
        def X(z, y):
            return sx * (surf_x(z, y) + 0.010)
        zf, zr, yb, yt, wd = 1.10, -0.38, -0.50, 0.075, 0.018
        for z0 in (zf, zr):
            decal(m, [(z0, yb, X(z0, yb)), (z0 + wd, yb, X(z0 + wd, yb)), (z0 + wd, yt, X(z0 + wd, yt)), (z0, yt, X(z0, yt))],
                  "door_line", sx)
        for y0 in (yb, yt):
            decal(m, [(zr, y0, X(zr, y0)), (zf + wd, y0, X(zf + wd, y0)), (zf + wd, y0 + wd, X(zf + wd, y0 + wd)),
                      (zr, y0 + wd, X(zr, y0 + wd))], "door_line", sx)
        # door handle and hinge pads
        hx = X(-0.12, -0.18)
        bx(m, hx - 0.015 if sx > 0 else hx - 0.05, hx + 0.05 if sx > 0 else hx + 0.015, -0.20, -0.16, -0.24, 0.0, "steel", bevel=0.01)
        # grab handle on the rear door post: vertical bar on two stubs
        gx = sx * (surf_x(-0.52, -0.05) + 0.07)
        sxs = sx * (surf_x(-0.52, -0.05) - 0.01)
        bar(m, (gx, -0.40, -0.52), (gx, 0.18, -0.52), 0.014, "steel")
        for yy in (-0.40, 0.18):
            bar(m, (sxs, yy, -0.52), (gx, yy, -0.52), 0.012, "steel")
        # grab handle on the front post
        gx2 = sx * (surf_x(1.12, -0.05) + 0.06)
        bar(m, (gx2, -0.38, 1.12), (gx2, 0.05, 1.12), 0.012, "steel")
        for yy in (-0.38, 0.05):
            bar(m, (sx * (surf_x(1.12, yy) - 0.01), yy, 1.12), (gx2, yy, 1.12), 0.010, "steel")
    # chevrons on the boom: bold navy arms pointing forward, on both flanks and on top
    run, th = 0.40, 0.22
    zcs = (-3.4, -4.0, -4.6, -5.2)          # last band ends at z = -5.82, forward of the stabiliser root (-5.85)
    for zc in zcs:
        top, bot, w, e = sect(zc - run / 2)
        cy, hh = (top + bot) / 2, (top - bot) / 2 * 0.58
        for sx in (1, -1):
            def X(z, y):
                return sx * (surf_x(z, y) + 0.014)
            for ss in (1, -1):
                ya, yb2 = cy, cy + ss * hh
                za, zb = zc, zc - run
                decal(m, [(za, ya, X(za, ya)), (zb, yb2, X(zb, yb2)), (zb - th, yb2, X(zb - th, yb2)), (za - th, ya, X(za - th, ya))],
                      "navy", sx)
        # top chevron following the faceted roof (ring vertices 3, 4, 5 of the stations)
        def roof(z):
            i = 0
            while i < len(S) - 2 and S[i + 1] > z:
                i += 1
            t = (S[i] - z) / (S[i] - S[i + 1])
            r0, r1 = station_ring(i), station_ring(i + 1)
            return [r0[k] + (r1[k] - r0[k]) * t for k in (3, 4, 5)]
        for sx in (1, -1):
            def P(z, side):
                r = roof(z)
                v = r[0] if sx > 0 else r[2]
                return (v.x * side, v.y + 0.012, z) if side else (0.0, r[1].y + 0.012, z)
            m.face([Vector(P(zc, 0)), Vector(P(zc - run, 1)), Vector(P(zc - run - th, 1)), Vector(P(zc - th, 0))],
                   "navy", hint=(0, 1, 0))


def cowl(m):
    zs = [-0.25, -0.50, -0.90, -1.30, -1.60, -1.95, -2.35, -2.80]
    tops = [0.99, 1.20, 1.32, 1.34, 1.32, 1.24, 1.08, 0.82]
    ws = [0.30, 0.46, 0.52, 0.52, 0.50, 0.46, 0.36, 0.22]
    rings = []
    for z, t, w in zip(zs, tops, ws):
        n = 12
        cy, h = (t + 0.50) / 2, (t - 0.50) / 2
        rings.append([Vector((w * _se(math.cos(2 * math.pi * j / n), 2.6), cy + h * _se(math.sin(2 * math.pi * j / n), 2.6), z)) for j in range(n)])
    loft_mat(m, rings, lambda i, j: 'navy' if (i in (2, 3) and j in (1, 2, 3, 4, 5)) else 'hivis')
    # intake, vents, exhaust
    bx(m, -0.22, 0.22, 1.04, 1.16, -0.52, -0.36, "dark", bevel=0.01)
    for k in range(4):
        bx(m, -0.19, 0.19, 1.045 + 0.0, 1.06 + 0.0, -0.50 + k * 0.035, -0.485 + k * 0.035, "steel")
    for sx in (1, -1):
        for k in range(4):
            z0 = -1.15 - k * 0.12
            bx(m, sx * 0.505 - 0.01 if sx > 0 else sx * 0.505 - 0.01, sx * 0.505 + 0.012 if sx > 0 else sx * 0.505 + 0.01,
               0.95, 1.18, z0, z0 - 0.045, "door_line")
    # exhaust stack, left side of the deck, angled up and back
    bar(m, (0.20, 1.02, -2.20), (0.22, 1.20, -2.66), 0.095, "exhaust", segs=8)
    bar(m, (0.22, 1.19, -2.64), (0.225, 1.215, -2.72), 0.072, "dark", segs=8)


def mast(m):
    hx, hy, hz = HUB_MAIN
    m.lathe((hx, 0, hz), (0, 1, 0), [(0.0, 1.10), (0.30, 1.10), (0.24, 1.35), (0.17, 1.58), (0.0, 1.60)], 14, "navy")   # gearbox fairing
    bar(m, (hx, 1.55, hz), (hx, hy - 0.10, hz), 0.07, "steel", segs=10)                                                 # mast
    m.lathe((hx, 0, hz), (0, 1, 0), [(0.0, 1.60), (0.26, 1.60), (0.26, 1.64), (0.0, 1.64)], 14, "steel")                # lower swashplate
    for k in range(3):                                                                                                 # scissor links
        a = k * 2 * math.pi / 3 + 0.4
        p0 = (hx + 0.20 * math.cos(a), 1.63, hz + 0.20 * math.sin(a))
        p1 = (hx + 0.09 * math.cos(a), 1.80, hz + 0.09 * math.sin(a))
        bar(m, p0, p1, 0.012, "steel", segs=4)


def tail(m):
    # fin
    ys = [0.45, 0.90, 1.30, 1.72]
    le = [-5.95, -6.20, -6.50, -6.78]
    te = [-7.12, -7.14, -7.12, -7.08]
    th = [0.05, 0.045, 0.038, 0.030]
    rings = []
    for y, a, b, t in zip(ys, le, te, th):
        c = a - b
        rings.append([Vector(p) for p in ((0, y, a), (t, y, a - 0.25 * c), (t * 0.8, y, a - 0.70 * c), (0, y, b),
                                          (-t * 0.8, y, a - 0.70 * c), (-t, y, a - 0.25 * c))])
    loft_mat(m, rings, lambda i, j: 'navy' if i == 0 else ('hivis' if i == 1 else 'navy'))
    bx(m, -0.06, 0.06, 1.69, 1.76, -6.90, -6.98, "navy", bevel=0.008)
    # tail skid / bumper
    bar(m, (0, 0.55, -6.55), (0, 0.10, -6.90), 0.028, "skid")
    bx(m, -0.05, 0.05, 0.05, 0.11, -6.98, -6.84, "skid", bevel=0.01)
    # tail rotor gearbox and mounting boss
    bar(m, (0.02, 1.10, -6.95), (HUB_TAIL[0] - 0.03, HUB_TAIL[1], HUB_TAIL[2]), 0.075, "steel", segs=8)
    # horizontal stabiliser with end plates
    xs = [-0.95, -0.50, 0.0, 0.50, 0.95]
    chord = [0.36, 0.48, 0.54, 0.48, 0.36]
    yb = 0.43
    rings = []
    for x, c in zip(xs, chord):
        z0 = -5.85 - abs(x) * 0.12
        t = 0.030
        rings.append([Vector(p) for p in ((x, yb, z0), (x, yb + t, z0 - 0.25 * c), (x, yb + t * 0.6, z0 - 0.75 * c), (x, yb, z0 - c),
                                          (x, yb - t * 0.6, z0 - 0.75 * c), (x, yb - t, z0 - 0.25 * c))])
    # loft order runs along x: ring orientation handled by recalc
    loft_mat(m, rings, lambda i, j: 'hivis' if i in (1, 2) else 'navy')
    for sx in (1, -1):
        x = sx * 0.955
        bx(m, x - 0.015, x + 0.015, yb - 0.10, yb + 0.25, -6.20, -5.80, "navy", bevel=0.01)


def interior(m):
    # floor, rear bulkhead, dash, console
    bx(m, -0.58, 0.58, -0.64, -0.60, -0.90, 1.00, "dark")
    bx(m, -0.72, 0.72, -0.60, 0.80, -0.96, -0.90, "dark")
    bx(m, -0.60, 0.60, -0.35, 0.02, 1.08, 1.30, "dark", bevel=0.03)                 # dash body
    bx(m, -0.58, 0.58, 0.02, 0.07, 1.00, 1.28, "dark", bevel=0.015)                 # glare shield
    for sx in (-0.38, 0.38):
        bx(m, sx - 0.15, sx + 0.15, -0.14, -0.04, 1.075, 1.085, "panel")          # instrument screens
    for sx in (-0.12, 0.0, 0.12):
        bx(m, sx - 0.03, sx + 0.03, -0.10, -0.02, 1.075, 1.085, "panel")
    bx(m, -0.12, 0.12, -0.60, -0.22, 0.15, 1.05, "dark", bevel=0.02)                # centre console
    bx(m, -0.09, 0.09, -0.22, -0.18, 0.40, 0.70, "panel")                           # radio stack
    # seats
    for sx in (-0.38, 0.38):
        bx(m, sx - 0.24, sx + 0.24, -0.50, -0.40, 0.14, 0.64, "seat", bevel=0.03)
        m.box((sx, 0.0, 0.08), (0.48, 0.78, 0.09), "seat", bevel=0.03, rot=Matrix.Rotation(-0.16, 3, 'X'))
        bx(m, sx - 0.10, sx + 0.10, 0.34, 0.50, 0.015, 0.075, "seat", bevel=0.02)
        for dx in (-0.22, 0.22):
            bx(m, sx + dx - 0.02, sx + dx + 0.02, -0.40, -0.18, 0.18, 0.60, "seat", bevel=0.01)   # armrest pads
    # cyclic and collective
    bar(m, (-0.38, -0.60, 0.90), (-0.38, -0.12, 0.84), 0.016, "dark")
    m.ico((-0.38, -0.10, 0.83), 0.035, "dark", subdiv=1)
    bar(m, (-0.17, -0.45, 0.35), (-0.17, -0.30, 0.78), 0.014, "steel")
    bar(m, (-0.06, -0.55, 0.60), (-0.06, -0.28, 0.80), 0.012, "dark")      # second stick (co-pilot side)
    # crew
    for k, sx in enumerate((-0.38, 0.38)):
        crew(m, sx, pilot=(k == 0))


def crew(m, c, pilot):
    hips, sh = Vector((c, -0.36, 0.40)), Vector((c, 0.17, 0.21))
    limb(m, hips, sh, 0.19, 0.205, 10, "vest", scale=(1.05, 0.70))
    blob(m, (c, 0.17, 0.21), (0.23, 0.10, 0.12), "crew_suit", subdiv=2)
    limb(m, sh, sh + Vector((0, 0.14, -0.01)), 0.07, 0.06, 8, "crew_suit")                 # neck
    head = Vector((c, 0.44, 0.19))
    blob(m, head, (0.140, 0.155, 0.170), "helmet", subdiv=2)
    blob(m, head + Vector((0, -0.01, 0.13)), (0.12, 0.07, 0.06), "visor", subdiv=2)
    # legs: thighs spread either side of the stick, shins down to boots
    for dx in (-0.12, 0.12):
        hip = Vector((c + dx, -0.37, 0.40))
        knee = Vector((c + dx * 1.2, -0.25, 0.94))
        foot = Vector((c + dx * 1.2, -0.57, 1.00))
        limb(m, hip, knee, 0.085, 0.07, 8, "crew_suit")
        limb(m, knee, foot, 0.065, 0.055, 8, "crew_suit")
        blob(m, foot + Vector((0, -0.03, 0.06)), (0.06, 0.04, 0.12), "boots", subdiv=1)
    # arms
    for sgn in (-1, 1):
        shoulder = Vector((c + sgn * 0.21, 0.15, 0.19))
        if pilot:
            hand = Vector((-0.39, -0.08, 0.83)) if sgn < 0 else Vector((-0.18, -0.30, 0.76))
            elbow = Vector((c + sgn * 0.27, -0.12, 0.46))
        else:
            hand = Vector((c + sgn * 0.14, -0.20, 0.62))
            elbow = Vector((c + sgn * 0.27, -0.10, 0.40))
        limb(m, shoulder, elbow, 0.058, 0.05, 8, "crew_suit")
        limb(m, elbow, hand, 0.05, 0.04, 8, "crew_suit")
        blob(m, hand, (0.04, 0.04, 0.045), "boots", subdiv=1)


def details(m):
    # roof: wire-strike cutter wedge, aerials, GPS puck
    bx(m, -0.012, 0.012, 0.93, 1.10, 0.72, 0.80, "steel", bevel=0.004)
    m.box((0.0, 0.97, 0.76), (0.03, 0.2, 0.05), "steel", rot=Matrix.Rotation(-0.35, 3, 'X'))
    for (x, z, tip, r) in ((0.30, 0.30, (0.34, 1.34, 0.22), 0.012), (-0.34, -0.15, (-0.40, 1.28, -0.22), 0.010)):
        limb(m, (x, 0.92, z), tip, r, 0.004, 5, "steel")
    bx(m, -0.02, 0.02, 0.93, 1.16, 0.15, 0.40, "dark", bevel=0.008)                      # blade antenna
    m.lathe((0, 0.95, 0.62), (0, 1, 0), [(0.0, 0.0), (0.09, 0.0), (0.07, 0.04), (0.0, 0.05)], 8, "dark")       # GPS puck
    # boom: aerial whips and a tail position strip
    limb(m, (0.0, 0.18, -4.0), (0.0, -0.10, -4.35), 0.010, 0.004, 5, "steel")
    limb(m, (0.0, 0.62, -5.3), (0.0, 0.88, -5.45), 0.010, 0.004, 5, "steel")
    m.lathe((0.0, 0.58, -3.4), (0, 1, 0), [(0.0, 0.0), (0.05, 0.0), (0.04, 0.03), (0.0, 0.035)], 8, "dark")
    # pitot tube and wipers on the nose
    limb(m, (0.0, -0.42, 2.02), (0.0, -0.40, 2.40), 0.009, 0.004, 5, "steel")                 # chin pitot
    # nose mullions over the bubble (dark frames)
    for k, z in enumerate((1.80, 1.45)):
        top, bot, w, e = sect(z)
        cy, h = (top + bot) / 2, (top - bot) / 2
        pts = [Vector((w * _se(math.cos(a), e) * 1.008, cy + h * _se(math.sin(a), e) * 1.008 + 0.004, z))
               for a in [math.radians(d) for d in range(0, 181, 22)]]
        tube(m, pts, 0.014, 5, "navy", caps=True)
    # spotlight yoke and camera-ball stalk
    for sx in (1, -1):
        bar(m, (sx * 0.20, -0.62, 1.50), (sx * 0.215, -0.82, 1.50), 0.018, "steel", segs=6)
        bar(m, (sx * 0.19, -0.82, 1.50), (sx * 0.225, -0.82, 1.50), 0.03, "steel", segs=8)
    bar(m, (BALL[0], -0.58, BALL[2]), (BALL[0], -0.72, BALL[2]), 0.035, "steel", segs=8)


def build_fuselage(root):
    m = MB()
    hull(m)
    cowl(m)
    mast(m)
    tail(m)
    interior(m)
    details(m)
    return m.to_object("fuselage", origin=(0, 0, 0), parent=root, smooth=50)


# --------------------------------------------------------------------------- rotors
def build_rotor_main(root):
    H = Vector(HUB_MAIN)
    m = MB()
    # hub, cuffs, blades, upper swashplate ring, pitch links (3-fold symmetric about the mast axis)
    m.lathe(H, (0, 1, 0), [(0.0, -0.10), (0.20, -0.10), (0.26, -0.04), (0.26, 0.10), (0.16, 0.17), (0.0, 0.18)], 12, "steel")
    m.lathe(H, (0, 1, 0), [(0.0, -0.17), (0.22, -0.17), (0.22, -0.10), (0.0, -0.10)], 12, "steel")
    m.lathe(H, (0, 1, 0), [(0.0, 0.18), (0.07, 0.18), (0.07, 0.24), (0.0, 0.24)], 12, "dark")
    us = [0.45, 0.95, 1.9, 3.0, 3.9, 4.5, 4.8]
    chords = [0.26, 0.30, 0.30, 0.30, 0.30, 0.30, 0.22]
    thick = [0.034, 0.030, 0.026, 0.024, 0.022, 0.020, 0.016]
    for k in range(3):
        # one blade assembly authored at angle 0, then rotated about the mast axis: exact 120 degree symmetry
        arm = MB()
        rings = []
        for u, c, t in zip(us, chords, thick):
            phi = 0.13 - 0.07 * u / 4.8
            cone = 0.10 * (u / 4.8) ** 2
            ring_ = []
            for zc, yy in ((-0.5, 0.0), (-0.30, 1.0), (0.10, 0.7), (0.5, 0.0), (0.10, -0.7), (-0.30, -1.0)):
                z, y = zc * c, yy * t
                z2, y2 = z * math.cos(phi) - y * math.sin(phi), z * math.sin(phi) + y * math.cos(phi)
                ring_.append(H + Vector((u, 0.04 + y2 + cone, z2)))
            rings.append(ring_)
        loft_mat(arm, rings, lambda i, j: 'hivis' if i == 5 else 'blade')
        limb(arm, H + Vector((0.18, 0.04, 0.0)), H + Vector((0.52, 0.04, 0.0)), 0.06, 0.05, 8, "steel")       # blade grip
        bar(arm, H + Vector((0.20 * math.cos(0.5), -0.13, -0.20 * math.sin(0.5))), H + Vector((0.34, 0.04, 0.03)), 0.011, "steel", segs=4)
        Rk = Matrix.Rotation(k * 2 * math.pi / 3 + math.pi / 2, 3, 'Y')
        for v in arm.bm.verts:
            v.co = H + Rk @ (v.co - H)
        m.merge(arm)
    m.lathe(H, (0, 1, 0), [(0.0, -0.24), (0.27, -0.24), (0.27, -0.20), (0.0, -0.20)], 12, "steel")      # rotating swashplate ring
    return m.to_object("rotor_main", origin=tuple(H), parent=root, smooth=50)


def build_rotor_tail(root):
    H = Vector(HUB_TAIL)
    m = MB()
    m.lathe(H, (1, 0, 0), [(0.0, -0.04), (0.06, -0.04), (0.06, 0.05), (0.0, 0.07)], 10, "steel")
    m.lathe(H, (1, 0, 0), [(0.0, 0.05), (0.03, 0.05), (0.03, 0.10), (0.0, 0.10)], 8, "dark")
    rs = [0.07, 0.20, 0.40, 0.55]
    cs = [0.10, 0.13, 0.13, 0.10]
    tt = [0.016, 0.016, 0.014, 0.012]
    for sgn in (1, -1):
        rings = []
        for r, c, t in zip(rs, cs, tt):
            phi = 0.36
            ring_ = []
            for zc, xx in ((-0.5, 0.0), (-0.25, 1.0), (0.15, 0.7), (0.5, 0.0), (0.15, -0.7), (-0.25, -1.0)):
                z, x = zc * c, xx * t
                x2, z2 = x * math.cos(phi) + z * math.sin(phi), -x * math.sin(phi) + z * math.cos(phi)
                ring_.append(H + Vector((x2, sgn * r, sgn * z2)))
            rings.append(ring_)
        loft_mat(m, rings, lambda i, j: 'hivis' if i == 2 else 'blade')
    return m.to_object("rotor_tail", origin=tuple(H), parent=root, smooth=50)


# --------------------------------------------------------------------------- spotlight, camera, skids, lamps
def build_spotlight(root):
    P = Vector(PIVOT)
    m = MB()
    m.lathe(P + Vector((0, 0, 0.0)), (0, 0, 1), [(0.0, -0.24), (0.11, -0.24), (0.16, -0.17), (0.17, -0.05), (0.17, 0.15),
                                                   (0.19, 0.15), (0.19, 0.19), (0.0, 0.19)], 14, "navy")
    m.lathe(P, (0, 0, 1), [(0.0, 0.185), (0.145, 0.185), (0.145, 0.20), (0.10, 0.222), (0.0, 0.230)], 14, "spot_lens")
    for sx in (1, -1):
        bar(m, (P.x + sx * 0.16, P.y, P.z), (P.x + sx * 0.20, P.y, P.z), 0.03, "steel", segs=8)
    bx(m, -0.06, 0.06, P.y + 0.15, P.y + 0.19, P.z - 0.16, P.z - 0.06, "dark", bevel=0.008)   # cooling fins block
    return m.to_object("spotlight", origin=tuple(P), parent=root, smooth=50)


def build_camera_ball(root):
    C = Vector(BALL)
    m = MB()
    m.ico(C, 0.15, "dark", subdiv=2)
    m.lathe(C + Vector((0, 0, 0.0)), (0, 0, 1), [(0.0, 0.0), (0.075, 0.0), (0.075, 0.148), (0.0, 0.148)], 12, "cam_lens")
    m.lathe(C + Vector((0, 0, 0.11)), (0, 0, 1), [(0.0, 0.0), (0.095, 0.0), (0.095, 0.03), (0.0, 0.03)], 12, "steel")
    m.lathe(C + Vector((0, 0, 0.12)), (0, 0, 1), [(0.0, 0.0), (0.065, 0.0), (0.065, 0.045), (0.0, 0.045)], 12, "cam_lens")
    return m.to_object("camera_ball", origin=tuple(C), parent=root, smooth=50)


def build_skids(root):
    m = MB()
    for sx in (1, -1):
        x = sx * 0.82
        path = [(-1.68, -0.84), (-1.55, -0.93), (-1.30, -0.96), (1.00, -0.96), (1.35, -0.95), (1.62, -0.86), (1.78, -0.68)]
        tube(m, [(x, y, z) for z, y in path], 0.040, 8, "skid")
        for z0 in (0.95, -0.80):
            arch = [(x, -0.96, z0), (sx * 0.81, -0.86, z0), (sx * 0.73, -0.75, z0), (sx * 0.60, -0.62, z0), (sx * 0.50, -0.50, z0)]
            tube(m, arch, 0.034, 8, "skid")
            bx(m, sx * 0.84 - 0.03, sx * 0.84 + 0.03, -1.00, -0.92, z0 - 0.07, z0 + 0.07, "dark", bevel=0.01)
            bx(m, sx * 0.52 - 0.06, sx * 0.52 + 0.06, -0.55, -0.48, z0 - 0.07, z0 + 0.07, "steel", bevel=0.01)
        # skid shoe
        bx(m, x - 0.045, x + 0.045, -1.00, -0.97, -1.25, 0.95, "dark", bevel=0.005)
    return m.to_object("skids", origin=(0, 0, 0), parent=root, smooth=50)


def lamp(root, name, c, mat, r=0.05):
    m = MB()
    m.ico(c, r, mat, subdiv=2, scale=(1.0, 0.8, 1.2))
    return m.to_object(name, origin=tuple(c), parent=root, smooth=50)


def build_helicopter():
    materials()
    root = empty("heli")
    build_fuselage(root)
    build_rotor_main(root)
    build_rotor_tail(root)
    build_spotlight(root)
    build_camera_ball(root)
    build_skids(root)
    lamp(root, "nav_red", NAV_RED, "nav_red")
    lamp(root, "nav_green", NAV_GREEN, "nav_green")
    lamp(root, "strobe", STROBE, "strobe", r=0.055)
    return root
