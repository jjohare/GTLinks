"""Course furniture props, set 2: grandstand, leaderboard, bench, sprinkler, yardage post, OB stake,
ball washer, halfway hut, bunker rake, parasol, footbridge unit.

Game frame throughout (+X left, +Y up, +Z forward/downhill, objects face +Z); `MB.to_object` maps to Blender.
Every build_<name>() makes its own materials in a clean scene and a root empty named <name>.
No text anywhere: every sign / plate / panel is blank.
"""
import math
from mathutils import Vector
import bmesh
from gtl import MB, make_mat, empty, bx

UP = Vector((0, 1, 0))


# ------------------------------------------------------------------ helpers
def _basis(t, ref):
    """Orthonormal (s, n) perpendicular to tangent t, with s as close to ref as possible."""
    t = Vector(t).normalized()
    r = Vector(ref)
    if abs(t.dot(r.normalized())) > 0.98:
        r = Vector((1, 0, 0)) if abs(t.x) < 0.9 else Vector((0, 0, 1))
    s = (r - t * r.dot(t)).normalized()
    n = t.cross(s).normalized()
    return s, n


def sweep(m, path, sec, mat, ref=UP):
    """Sweep a 2D section [(x, y), ...] (x along s, y along n) along a 3D polyline; solid with caps."""
    path = [Vector(p) for p in path]
    rings = []
    for i, c in enumerate(path):
        a = path[max(i - 1, 0)]
        b = path[min(i + 1, len(path) - 1)]
        s, n = _basis(b - a, ref)
        rings.append([c + s * x + n * y for x, y in sec])
    return m.loft(rings, mat)


def rect(w, d):
    return [(w / 2, d / 2), (-w / 2, d / 2), (-w / 2, -d / 2), (w / 2, -d / 2)]


def circ(r, n=6, phase=0.0):
    return [(r * math.cos(phase + 2 * math.pi * i / n), r * math.sin(phase + 2 * math.pi * i / n)) for i in range(n)]


def beam(m, p0, p1, w, d, mat, ref=UP):
    """Square-section member between two points; w across `ref`-ish side, d the other way."""
    return sweep(m, [p0, p1], rect(w, d), mat, ref)


def rod(m, p0, p1, r, mat, n=4):
    return sweep(m, [p0, p1], circ(r, n, math.pi / 4 if n == 4 else 0.0), mat)


def ext(m, poly, o, u, v, w, t0, t1, mat):
    """Extrude convex/simple polygon `poly` (x, y) living in the plane o + u*x + v*y along w from t0 to t1."""
    o, u, v, w = Vector(o), Vector(u), Vector(v), Vector(w)
    rings = [[o + u * x + v * y + w * t for x, y in poly] for t in (t0, t1)]
    return m.loft(rings, mat)


def grid_face(m, fn, nu, nv, mat, hint):
    """Open surface from fn(u, v) -> point over an nu x nv quad grid."""
    pts = [[Vector(fn(i / nu, j / nv)) for j in range(nv + 1)] for i in range(nu + 1)]
    for i in range(nu):
        for j in range(nv):
            m.face([pts[i][j], pts[i + 1][j], pts[i + 1][j + 1], pts[i][j + 1]], mat, hint=hint)


def tri_face(m, a, b, c, mat, hint):
    m.face([a, b, c], mat, hint=hint)


def finish(m, name, root, smooth=35.0):
    return m.to_object(name + "_mesh", parent=root, smooth=smooth)


def catenary(p0, p1, sag, n):
    p0, p1 = Vector(p0), Vector(p1)
    pts = []
    for i in range(n + 1):
        u = i / n
        p = p0.lerp(p1, u)
        p.y -= sag * 4 * u * (1 - u)
        pts.append(p)
    return pts


def bunting(m, p0, p1, sag, nflags, mats, drop=0.24, wid=0.17, rope="rope", n=12):
    """Rope along a sagging line with triangular pennants (double-sided cloth)."""
    pts = catenary(p0, p1, sag, n)
    sweep(m, pts, circ(0.008, 4), rope)
    d = (Vector(p1) - Vector(p0)).normalized()
    for k in range(nflags):
        u = (k + 0.5) / nflags
        c = Vector(p0).lerp(Vector(p1), u)
        c.y -= sag * 4 * u * (1 - u)
        a = c - d * (wid / 2)
        b = c + d * (wid / 2)
        tip = c + Vector((0, -drop, 0))
        m.face([a, b, tip], mats[k % len(mats)], hint=(0, 0, 1))


# ================================================================== grandstand
def _gs_mats():
    make_mat("steel_frame", (0.36, 0.42, 0.48), metallic=0.6, rough=0.5)
    make_mat("steel_rail", (0.78, 0.80, 0.84), metallic=0.7, rough=0.4)
    make_mat("deck_timber", (0.58, 0.41, 0.24), rough=0.85)
    make_mat("riser_paint", (0.90, 0.90, 0.85), rough=0.8)
    make_mat("seat_slat", (0.74, 0.57, 0.34), rough=0.8)
    make_mat("seat_red", (0.84, 0.14, 0.13), rough=0.55)
    make_mat("seat_blue", (0.14, 0.34, 0.74), rough=0.55)
    make_mat("seat_yellow", (0.97, 0.78, 0.16), rough=0.55)
    make_mat("seat_white", (0.94, 0.94, 0.92), rough=0.55)
    make_mat("concrete", (0.64, 0.64, 0.61), rough=0.95)
    make_mat("canopy_a", (0.95, 0.95, 0.90), rough=0.85, double=True)
    make_mat("canopy_b", (0.16, 0.46, 0.30), rough=0.85, double=True)
    make_mat("banner_panel_a", (0.16, 0.38, 0.66), rough=0.7)
    make_mat("banner_panel_b", (0.94, 0.94, 0.90), rough=0.7)
    make_mat("rope", (0.86, 0.80, 0.64), rough=0.9)
    for k, c in zip("abcd", [(0.85, 0.15, 0.15), (0.97, 0.85, 0.20), (0.20, 0.45, 0.80), (0.95, 0.95, 0.92)]):
        make_mat("pennant_" + k, c, rough=0.8, double=True)


def build_grandstand():
    _gs_mats()
    root = empty("grandstand")
    m = MB()
    G = 0.08                                  # slab thickness
    NR, RD, RISE, Y0, ZF = 6, 0.9, 0.5, 0.5, 3.0
    FX = [-6.9, -5.5, -4.1, -2.9, -1.45, 0.0, 1.45, 2.9, 4.1, 5.5, 6.9]   # steel frames
    FRM = [-6.9, -4.1, -2.9, -1.45, 0.0, 1.45, 2.9, 4.1, 6.9]
    BLK = [(-6.9, -4.1), (-2.9, 2.9), (4.1, 6.9)]                          # seat blocks (aisles between)
    AISLE = [(-4.1, -2.9), (2.9, 4.1)]
    yt = lambda i: Y0 + i * RISE
    zf = lambda i: ZF - i * RD                # front edge of row i (rows climb toward -Z)

    # ground slab
    bx(m, -7.45, 7.45, 0, G, -3.9, 3.9, "concrete")
    for sx in (-1, 1):
        bx(m, sx * 7.45 - 0.0, sx * 7.45 + sx * 0.05, 0, G + 0.02, -3.9, 3.9, "concrete")

    # ---- transverse steel frames (YZ profile at each x)
    stair_x = {-4.1, -2.9, 2.9, 4.1}
    braced = {-6.9, -4.1, -2.9, 0.0, 2.9, 4.1, 6.9}
    for x in FRM:
        # ground beam and verticals under every tread front edge + rear
        beam(m, (x, G + 0.04, 3.0), (x, G + 0.04, -3.0), 0.09, 0.08, "steel_frame", ref=(1, 0, 0))
        for i in range(NR):
            z = zf(i)
            beam(m, (x, G + 0.04, z), (x, yt(i) - 0.07, z), 0.08, 0.08, "steel_frame", ref=(1, 0, 0))
            beam(m, (x, yt(i) - 0.10, z), (x, yt(i) - 0.10, z - RD), 0.07, 0.08, "steel_frame", ref=(1, 0, 0))
        beam(m, (x, G + 0.04, -3.0), (x, yt(NR - 1) - 0.07, -3.0), 0.08, 0.08, "steel_frame", ref=(1, 0, 0))
        beam(m, (x, yt(NR - 1) - 0.10, zf(NR - 1) - RD), (x, yt(NR - 1) - 0.10, -3.0), 0.07, 0.08, "steel_frame", ref=(1, 0, 0))
        if x in stair_x:                       # raking stair stringer
            beam(m, (x, G + 0.1, 3.45), (x, 2.9, -1.5), 0.06, 0.2, "steel_frame", ref=(1, 0, 0))
        elif x in braced:
            for i in range(NR - 1):
                beam(m, (x, G + 0.05, zf(i)), (x, yt(i + 1) - 0.11, zf(i + 1)), 0.05, 0.05, "steel_frame", ref=(1, 0, 0))
        # base plate feet
        for z in (zf(0), zf(NR - 1), -3.0):
            bx(m, x - 0.11, x + 0.11, G, G + 0.02, z - 0.11, z + 0.11, "steel_frame")

    # longitudinal ties under each tread front edge and X-bracing in the rear elevation
    for i in range(NR):
        y = yt(i) - 0.14
        beam(m, (-6.9, y, zf(i) - 0.0), (6.9, y, zf(i)), 0.05, 0.07, "steel_frame", ref=(0, 0, 1))
    beam(m, (-6.9, G + 0.12, -3.0), (6.9, G + 0.12, -3.0), 0.05, 0.07, "steel_frame", ref=(0, 0, 1))
    top = yt(NR - 1) - 0.14
    for xa, xb in [(-6.9, -5.5), (-1.45, 0.0), (0.0, 1.45), (5.5, 6.9)]:
        beam(m, (xa, G + 0.12, -3.0), (xb, top, -3.0), 0.04, 0.04, "steel_frame", ref=(0, 0, 1))
        beam(m, (xb, G + 0.12, -3.0), (xa, top, -3.0), 0.04, 0.04, "steel_frame", ref=(0, 0, 1))

    # ---- treads, risers, seats
    for i in range(NR):
        zc = zf(i) - RD / 2
        z_hi = zf(i)
        z_lo = zf(i) - RD if i < NR - 1 else -3.0
        for (xa, xb) in BLK:
            for k in range(2):                  # two deck boards per tread
                za = z_hi - k * (z_hi - z_lo) / 2
                zb = z_hi - (k + 1) * (z_hi - z_lo) / 2
                bx(m, xa, xb, yt(i) - 0.05, yt(i), zb + 0.005, za - 0.005, "deck_timber")
            y_low = yt(i - 1) if i else G
            bx(m, xa, xb, y_low, yt(i) - 0.05, z_hi - 0.03, z_hi, "riser_paint")
            # seat bearers
            for zb_ in (zc - 0.26, zc + 0.04):
                bx(m, xa + 0.02, xb - 0.02, yt(i) + 0.31, yt(i) + 0.36, zb_ - 0.03, zb_ + 0.03, "steel_frame")
        # modules of seat slats
        mods = []
        for (xa, xb) in BLK:
            n = max(1, round((xb - xa) / 1.45))
            w = (xb - xa) / n
            mods += [(xa + j * w, xa + (j + 1) * w) for j in range(n)]
        for mi, (xa, xb) in enumerate(mods):
            vip = (-2.9 <= xa and xb <= 2.9 and i < 2)
            colour = {(1, 1): "seat_red", (3, 1): "seat_blue", (5, 2): "seat_yellow", (6, 4): "seat_red",
                      (2, 3): "seat_blue", (4, 5): "seat_yellow", (0, 3): "seat_yellow", (7, 0): "seat_blue",
                      (7, 5): "seat_red", (0, 5): "seat_blue"}.get((mi, i), "seat_slat")
            if vip:
                n = int(round((xb - xa) / 0.46)) or 1
                cw = (xb - xa) / n
                for c in range(n):
                    cx = xa + (c + 0.5) * cw
                    cm = ["seat_red", "seat_white", "seat_blue", "seat_yellow"][(c + mi + i) % 4]
                    bx(m, cx - cw / 2 + 0.02, cx + cw / 2 - 0.02, yt(i) + 0.40, yt(i) + 0.45, zc - 0.28, zc + 0.12, cm)
                    bx(m, cx - cw / 2 + 0.03, cx + cw / 2 - 0.03, yt(i) + 0.45, yt(i) + 0.78, zc - 0.31, zc - 0.26, cm)
            else:
                for k in range(3):
                    z0 = zc - 0.30 + k * 0.15
                    bx(m, xa + 0.02, xb - 0.02, yt(i) + 0.36, yt(i) + 0.40, z0, z0 + 0.12, colour)
            for xs in (xa, xb):
                xs2 = xs + (0.03 if xs == xa else -0.03)
                bx(m, xs2 - 0.025, xs2 + 0.025, yt(i), yt(i) + 0.36, zc - 0.28, zc + 0.08, "steel_frame")

    # ---- stair aisles
    for (xa, xb) in AISLE:
        for k in range(12):
            top = 0.25 * (k + 1)
            z_hi = 3.45 - 0.45 * k
            z_lo = z_hi - 0.45 if k < 11 else -3.0
            bx(m, xa, xb, top - 0.05, top, z_lo, z_hi, "deck_timber")
            bx(m, xa, xb, top - 0.25 if k else G, top - 0.05, z_hi - 0.03, z_hi, "riser_paint")
        xr = [xa, xb]
        for x in xr:
            _stair_rail(m, x, 0.0)
    for sx in (-1, 1):
        _stair_rail(m, sx * 7.0, 0.0)

    # ---- rear guard rail on the top landing
    zr = -2.94
    yb = yt(NR - 1)
    xs_ = [-6.9 + 0.5 * k for k in range(0, 28)]
    for x in FX:
        rod(m, (x, yb, zr), (x, yb + 1.05, zr), 0.025, "steel_rail")
    for yy in (yb + 1.05, yb + 0.55):
        rod(m, (-6.95, yy, zr), (6.95, yy, zr), 0.022, "steel_rail")
    for x in xs_:
        if not any(abs(x - f) < 0.12 for f in FX):
            bx(m, x - 0.01, x + 0.01, yb, yb + 1.05, zr - 0.01, zr + 0.01, "steel_rail")
    # front barrier (between aisles) and fascia banners
    for (xa, xb) in BLK:
        for yy in (Y0 + 0.9, Y0 + 0.45):
            rod(m, (xa, yy, ZF - 0.05), (xb, yy, ZF - 0.05), 0.02, "steel_rail")
        n = max(1, round((xb - xa) / 1.45))
        for j in range(n + 1):
            x = xa + j * (xb - xa) / n
            rod(m, (x, Y0, ZF - 0.05), (x, Y0 + 0.9, ZF - 0.05), 0.025, "steel_rail")
        w = (xb - xa) / n
        for j in range(n):
            mat_ = "banner_panel_a" if (j + (xa > 0) + (xa > -3)) % 2 == 0 else "banner_panel_b"
            bx(m, xa + j * w + 0.05, xa + (j + 1) * w - 0.05, G + 0.08, Y0 - 0.1, ZF + 0.02, ZF + 0.06, mat_)
            bx(m, xa + j * w + 0.02, xa + (j + 1) * w - 0.02, G + 0.05, G + 0.08, ZF + 0.0, ZF + 0.07, "steel_frame")
            bx(m, xa + j * w + 0.02, xa + (j + 1) * w - 0.02, Y0 - 0.1, Y0 - 0.07, ZF + 0.0, ZF + 0.07, "steel_frame")

    # ---- roof structure
    RP = [-6.9, -4.25, -1.45, 1.45, 4.25, 6.9]
    yf, yr, zF_, zR_ = 4.4, 5.05, 3.05, -3.1
    ry = lambda z: yf + (zF_ - z) * (yr - yf) / (zF_ - zR_)
    for x in RP:
        beam(m, (x, G, zR_), (x, yr, zR_), 0.13, 0.13, "steel_frame", ref=(1, 0, 0))
        beam(m, (x, Y0, zF_), (x, yf, zF_), 0.11, 0.11, "steel_frame", ref=(1, 0, 0))
        bx(m, x - 0.16, x + 0.16, G, G + 0.02, zR_ - 0.16, zR_ + 0.16, "steel_frame")
        bx(m, x - 0.15, x + 0.15, Y0, Y0 + 0.02, zF_ - 0.15, zF_ + 0.15, "steel_frame")
        # knee braces from rear posts into rafters, front posts into rafters
        beam(m, (x, yr - 0.7, zR_), (x, yr, zR_ + 0.7), 0.05, 0.05, "steel_frame", ref=(1, 0, 0))
        beam(m, (x, yf - 0.6, zF_), (x, ry(zF_ - 0.6) - 0.1, zF_ - 0.6), 0.05, 0.05, "steel_frame", ref=(1, 0, 0))
    # tie rails between posts along x
    for z, y in ((zR_, yr - 0.15), (zF_, yf - 0.15)):
        beam(m, (-6.9, y, z), (6.9, y, z), 0.09, 0.12, "steel_frame", ref=(0, 0, 1))
    beam(m, (-6.9, 3.0 + 0.9, zR_), (6.9, 3.0 + 0.9, zR_), 0.06, 0.06, "steel_frame", ref=(0, 0, 1))
    for x in FX:                                          # rafters
        beam(m, (x, ry(3.6) - 0.06, 3.6), (x, ry(-3.6) - 0.06, -3.6), 0.07, 0.12, "steel_frame", ref=(1, 0, 0))
    for z in (2.2, 0.7, -0.8, -2.3):                      # purlins
        beam(m, (-7.1, ry(z) - 0.0, z), (7.1, ry(z) - 0.0, z), 0.07, 0.05, "steel_frame", ref=(0, 0, 1))
    # X bracing on the roof plane end bays
    for xa, xb in [(-6.9, -5.5), (5.5, 6.9)]:
        beam(m, (xa, ry(2.2) - 0.07, 2.2), (xb, ry(-2.3) - 0.07, -2.3), 0.03, 0.03, "steel_frame", ref=(0, 1, 0))
        beam(m, (xb, ry(2.2) - 0.07, 2.2), (xa, ry(-2.3) - 0.07, -2.3), 0.03, 0.03, "steel_frame", ref=(0, 1, 0))
    # gutter and downpipes
    sweep(m, [(-7.2, ry(3.62) - 0.12, 3.62), (7.2, ry(3.62) - 0.12, 3.62)],
          [(-0.07, 0.0), (-0.06, 0.07), (0.06, 0.07), (0.07, 0.0)], "steel_rail", ref=(0, 0, 1))
    for sx in (-1, 1):
        rod(m, (sx * 7.05, yr - 0.3, zR_ - 0.12), (sx * 7.05, G + 0.2, zR_ - 0.12), 0.035, "steel_rail")
        for yy in (1.2, 2.6, 4.0):
            bx(m, sx * 7.05 - 0.05, sx * 7.05 + 0.05, yy, yy + 0.04, zR_ - 0.2, zR_ - 0.02, "steel_frame")

    # ---- fabric canopy (alternating bays), with sag and scalloped valance
    for j in range(len(FX) - 1):
        xa, xb = FX[j], FX[j + 1]
        mat_ = "canopy_a" if j % 2 == 0 else "canopy_b"

        def pf(u, v, xa=xa, xb=xb):
            x = xa + (xb - xa) * u
            z = 3.6 - 7.2 * v
            return (x, ry(z) + 0.01 - 0.045 * math.sin(math.pi * u), z)
        grid_face(m, pf, 4, 6, mat_, (0, 1, 0))
        n = 4
        for k in range(n):                                # valance teeth hanging from the front edge
            x0 = xa + (xb - xa) * k / n
            x1 = xa + (xb - xa) * (k + 1) / n
            y0 = ry(3.6) + 0.01
            m.face([(x0, y0, 3.6), (x1, y0, 3.6), ((x0 + x1) / 2, y0 - 0.32, 3.6)], mat_, hint=(0, 0, 1))
        for k in range(n):                                # rear valance (shorter)
            x0 = xa + (xb - xa) * k / n
            x1 = xa + (xb - xa) * (k + 1) / n
            y0 = ry(-3.6) + 0.01
            m.face([(x0, y0, -3.6), (x1, y0, -3.6), ((x0 + x1) / 2, y0 - 0.22, -3.6)], mat_, hint=(0, 0, -1))
    # side valance triangles
    for sx in (-1, 1):
        x = sx * 6.9
        for k in range(6):
            za, zb = 3.6 - 1.2 * k, 3.6 - 1.2 * (k + 1)
            m.face([(x, ry(za) + 0.01, za), (x, ry(zb) + 0.01, zb), (x, (ry(za) + ry(zb)) / 2 - 0.2, (za + zb) / 2)],
                   "canopy_a" if k % 2 == 0 else "canopy_b", hint=(sx, 0, 0))

    # ---- bunting: front span between front posts, plus sides
    ms = ["pennant_a", "pennant_b", "pennant_c", "pennant_d"]
    for a, b in zip(RP[:-1], RP[1:]):
        bunting(m, (a, yf - 0.05, 3.2), (b, yf - 0.05, 3.2), 0.28, 9, ms)
    for sx in (-1, 1):
        bunting(m, (sx * 7.05, yf - 0.1, 3.2), (sx * 7.05, yr - 0.25, -3.1), 0.35, 14, ms)
    # flagpoles on the roof
    for sx in (-1, 1):
        x = sx * 6.9
        rod(m, (x, yr + 0.1, -3.0), (x, yr + 2.0, -3.0), 0.028, "steel_rail")
        m.ico((x, yr + 2.05, -3.0), 0.045, "steel_rail", subdiv=1)
        m.face([(x, yr + 1.9, -3.0), (x, yr + 1.45, -3.0), (x + sx * 0.7, yr + 1.7, -3.0)], ms[(sx + 1) // 2 * 2], hint=(0, 0, 1))
        m.face([(x, yr + 1.9, -3.0), (x, yr + 1.45, -3.0), (x + sx * 0.7, yr + 1.7, -3.0)], ms[(sx + 1) // 2 * 2], hint=(0, 0, -1))
    finish(m, "grandstand", root)


def _stair_rail(m, x, _unused, outer=False):
    """Slanted handrail along a stair line at lateral position x (posts, top rail, mid rail)."""
    pts = []
    for k in (0, 2, 4, 6, 8, 10):
        z = 3.45 - 0.45 * k - 0.225
        pts.append((z, 0.25 * (k + 1)))
    pts.append((-1.725, 3.0))
    h = 0.95
    for z, y in pts:
        rod(m, (x, y, z), (x, y + h, z), 0.03, "steel_rail", n=6)
    top = [(x, y + h, z) for z, y in pts]
    mid = [(x, y + h * 0.5, z) for z, y in pts]
    for a, b in zip(top[:-1], top[1:]):
        rod(m, a, b, 0.026, "steel_rail")
    for a, b in zip(mid[:-1], mid[1:]):
        rod(m, a, b, 0.018, "steel_rail")
    # landing section
    rod(m, (x, 3.0 + h, -1.725), (x, 3.0 + h, -2.95), 0.026, "steel_rail")
    rod(m, (x, 3.0 + h * 0.5, -1.725), (x, 3.0 + h * 0.5, -2.95), 0.018, "steel_rail")
    rod(m, (x, 3.0, -2.95), (x, 3.0 + h, -2.95), 0.03, "steel_rail")
    # end post at the foot
    rod(m, (x, 0.0, 3.3), (x, 0.0 + h + 0.1, 3.3), 0.03, "steel_rail")
    rod(m, (x, h + 0.1, 3.3), (x, 0.25 + h, 3.225), 0.026, "steel_rail")


# ================================================================== leaderboard
def _uv_front(m, prefix):
    """Give every face whose material starts with `prefix` a 0..1 UV over its own front rectangle (game x / y)."""
    uvl = m.bm.loops.layers.uv.verify()
    for f in m.bm.faces:
        if not m.slots[f.material_index].startswith(prefix):
            continue
        xs = [v.co.x for v in f.verts]
        ys = [v.co.y for v in f.verts]
        x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
        for lp in f.loops:
            lp[uvl].uv = ((lp.vert.co.x - x0) / (x1 - x0), (lp.vert.co.y - y0) / (y1 - y0))


def build_leaderboard():
    make_mat("frame_dark", (0.12, 0.17, 0.15), metallic=0.3, rough=0.55)
    make_mat("steel_dark", (0.24, 0.27, 0.31), metallic=0.65, rough=0.5)
    make_mat("backing", (0.20, 0.23, 0.27), rough=0.7)
    make_mat("trim_gold", (0.86, 0.66, 0.20), metallic=0.5, rough=0.4)
    make_mat("medal_gold", (0.95, 0.76, 0.20), metallic=0.6, rough=0.35)
    make_mat("medal_silver", (0.80, 0.82, 0.86), metallic=0.7, rough=0.35)
    make_mat("medal_bronze", (0.72, 0.45, 0.22), metallic=0.6, rough=0.4)
    make_mat("lamp_glow", (1.0, 0.92, 0.62), rough=0.3, emit=(1.0, 0.85, 0.45), emit_strength=2.0)
    make_mat("bolt", (0.70, 0.72, 0.75), metallic=0.8, rough=0.35)
    make_mat("panel_title", (0.05, 0.10, 0.17), rough=0.5)
    for r in range(1, 7):
        make_mat("panel_%d" % r, (0.06, 0.12, 0.20) if r % 2 else (0.07, 0.15, 0.22), rough=0.5)
    root = empty("leaderboard")
    m = MB()
    X, YB, YT = 2.5, 0.75, 2.75
    # backing plate and frame (z: back -0.12, front +0.12)
    bx(m, -X, X, YB, YT, -0.12, -0.08, "backing")
    bx(m, -X, X, YT - 0.10, YT, -0.12, 0.12, "frame_dark")
    bx(m, -X, X, YB, YB + 0.10, -0.12, 0.12, "frame_dark")
    for sx in (-1, 1):
        bx(m, sx * X - (0.10 if sx > 0 else 0), sx * X + (0.0 if sx > 0 else 0.10), YB, YT, -0.12, 0.12, "frame_dark")
    # gold trim line inside the frame
    bx(m, -X + 0.10, X - 0.10, YT - 0.115, YT - 0.10, 0.10, 0.125, "trim_gold")
    bx(m, -X + 0.10, X - 0.10, YB + 0.10, YB + 0.115, 0.10, 0.125, "trim_gold")
    # title panel
    yA, yB = 2.30, 2.62
    m.face([(-X + 0.14, yA, 0.09), (X - 0.14, yA, 0.09), (X - 0.14, yB, 0.09), (-X + 0.14, yB, 0.09)], "panel_title", hint=(0, 0, 1))
    for y0, y1 in ((yA - 0.03, yA), (yB, yB + 0.03)):
        bx(m, -X + 0.10, X - 0.10, y0, y1, -0.08, 0.11, "frame_dark")
    # six row slots, one material each
    pitch, rh = 0.22, 0.19
    ytop = 2.25
    med = ["medal_gold", "medal_silver", "medal_bronze"]
    for r in range(6):
        y1 = ytop - r * pitch - 0.01
        y0 = y1 - rh
        m.face([(-X + 0.14, y0, 0.09), (X - 0.14, y0, 0.09), (X - 0.14, y1, 0.09), (-X + 0.14, y1, 0.09)], "panel_%d" % (r + 1), hint=(0, 0, 1))
        bx(m, -X + 0.10, X - 0.10, y0 - 0.03, y0, -0.08, 0.11, "frame_dark")
        for xd in (-1.85, 1.55):                      # column dividers (rank | name | score)
            bx(m, xd - 0.015, xd + 0.015, y0, y1, 0.09, 0.115, "frame_dark")
        if r < 3:                                     # rank medal disc
            m.lathe((-2.12, (y0 + y1) / 2, 0.095), (0, 0, 1), [(0, 0), (0.075, 0), (0.075, 0.02), (0.06, 0.035), (0, 0.035)], 12, med[r])
        else:
            m.lathe((-2.12, (y0 + y1) / 2, 0.095), (0, 0, 1), [(0, 0), (0.06, 0), (0.06, 0.012), (0, 0.012)], 8, "trim_gold")
    # corner bolts
    for x in (-X + 0.05, X - 0.05):
        for y in (YB + 0.05, YT - 0.05, (YB + YT) / 2):
            m.cyl((x, y, 0.125), (0, 0, 1), 0.022, 0.025, 6, "bolt")
    # light bar: housing, hood, lamps, arms
    bx(m, -2.3, 2.3, YT + 0.10, YT + 0.24, 0.02, 0.26, "frame_dark")
    beam(m, (-2.3, YT + 0.24, 0.26), (2.3, YT + 0.24, 0.26), 0.01, 0.01, "frame_dark", ref=(0, 1, 0))
    bx(m, -2.34, 2.34, YT + 0.24, YT + 0.27, -0.04, 0.32, "frame_dark")
    for k in range(9):
        x = -2.0 + k * 0.5
        m.lathe((x, YT + 0.17, 0.26), (0, 0, 1), [(0, 0), (0.055, 0), (0.06, 0.01), (0.045, 0.04), (0, 0.045)], 10, "lamp_glow")
        m.lathe((x, YT + 0.17, 0.255), (0, 0, 1), [(0.07, 0), (0.07, 0.012)], 10, "steel_dark", solid=False, flip=False)
    for sx in (-1, 1):
        bx(m, sx * 2.0 - 0.05, sx * 2.0 + 0.05, YT, YT + 0.10, -0.08, 0.12, "steel_dark")
    # legs, splayed rear struts, bracing, feet
    for sx in (-1, 1):
        x = sx * 2.1
        beam(m, (x, 0.02, 0.0), (x, YB + 0.05, 0.0), 0.16, 0.16, "steel_dark", ref=(1, 0, 0))
        bx(m, x - 0.26, x + 0.26, 0, 0.03, -0.26, 0.26, "steel_dark")
        for dx in (-0.2, 0.2):
            for dz in (-0.2, 0.2):
                m.cyl((x + dx, 0.04, dz), (0, 1, 0), 0.025, 0.025, 6, "bolt")
        beam(m, (x, 2.25, -0.12), (x, 0.04, -1.15), 0.10, 0.10, "steel_dark", ref=(1, 0, 0))
        bx(m, x - 0.2, x + 0.2, 0, 0.03, -1.35, -0.95, "steel_dark")
    beam(m, (-2.1, 0.30, 0.0), (2.1, 0.30, 0.0), 0.09, 0.09, "steel_dark", ref=(0, 1, 0))
    beam(m, (-2.1, 0.06, 0.0), (0.0, 0.30, 0.0), 0.07, 0.07, "steel_dark", ref=(0, 0, 1))
    beam(m, (2.1, 0.06, 0.0), (0.0, 0.30, 0.0), 0.07, 0.07, "steel_dark", ref=(0, 0, 1))
    beam(m, (-2.1, 0.04, -1.15), (2.1, 0.04, -1.15), 0.08, 0.06, "steel_dark", ref=(0, 1, 0))
    for xa, xb in ((-2.1, 0.0), (2.1, 0.0)):
        beam(m, (xa, 0.04, -1.15), (xb, 0.04, 0.0), 0.04, 0.04, "steel_dark", ref=(0, 1, 0))
    # rear stiffeners and diagonals
    for x in (-1.6, -0.8, 0.0, 0.8, 1.6):
        bx(m, x - 0.04, x + 0.04, YB + 0.1, YT - 0.1, -0.20, -0.12, "steel_dark")
    for y in (YB + 0.3, YT - 0.3):
        bx(m, -2.4, 2.4, y - 0.04, y + 0.04, -0.20, -0.12, "steel_dark")
    for xa, xb in ((-2.4, -0.8), (0.8, 2.4)):
        beam(m, (xa, YB + 0.3, -0.21), (xb, YT - 0.3, -0.21), 0.04, 0.03, "steel_dark", ref=(0, 1, 0))
        beam(m, (xb, YB + 0.3, -0.21), (xa, YT - 0.3, -0.21), 0.04, 0.03, "steel_dark", ref=(0, 1, 0))
    for sx in (-1, 1):                                # gussets leg->frame
        beam(m, (sx * 2.1, 1.4, -0.12), (sx * 2.4, 1.8, -0.12), 0.05, 0.05, "steel_dark", ref=(0, 0, 1))
    _uv_front(m, "panel_")
    finish(m, "leaderboard", root, smooth=30.0)


# ================================================================== bench
def _spline(pts, per=4):
    """Catmull-Rom through 3D points."""
    P = [Vector(p) for p in pts]
    out = []
    for i in range(len(P) - 1):
        p0 = P[max(i - 1, 0)]
        p1, p2 = P[i], P[i + 1]
        p3 = P[min(i + 2, len(P) - 1)]
        for k in range(per):
            t = k / per
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    out.append(P[-1])
    return out


def build_bench():
    make_mat("cast_iron", (0.10, 0.28, 0.20), metallic=0.5, rough=0.5)
    make_mat("bench_slat", (0.70, 0.50, 0.27), rough=0.8)
    make_mat("bolt", (0.62, 0.64, 0.67), metallic=0.8, rough=0.4)
    root = empty("bench")
    m = MB()
    for sx in (-1, 1):
        x = sx * 0.74
        sec = rect(0.045, 0.045)
        P = lambda z, y: (x, y, z)
        # front leg (curved), rear leg continuing as the raked back upright
        sweep(m, _spline([P(0.26, 0.0), P(0.235, 0.12), P(0.20, 0.28), P(0.19, 0.43), P(0.20, 0.545)], 4), sec, "cast_iron", ref=(1, 0, 0))
        sweep(m, _spline([P(-0.31, 0.0), P(-0.28, 0.16), P(-0.25, 0.32), P(-0.25, 0.44), P(-0.27, 0.62), P(-0.31, 0.78), P(-0.345, 0.90)], 4), rect(0.045, 0.05), "cast_iron", ref=(1, 0, 0))
        # armrest with scroll
        arm = [P(-0.27, 0.63), P(-0.15, 0.655), P(0.0, 0.67), P(0.15, 0.665), P(0.225, 0.655)]
        sc = [(0.225 + 0.055 * math.sin(a), 0.60 + 0.055 * math.cos(a)) for a in [math.radians(v) for v in (20, 70, 120, 170, 220, 270)]]
        for z, y in sc:
            arm.append(P(z, y))
        sweep(m, _spline(arm, 3), rect(0.045, 0.032), "cast_iron", ref=(1, 0, 0))
        # seat rail and stretcher, lower scroll brace
        sweep(m, [P(0.20, 0.405), P(-0.26, 0.405)], rect(0.045, 0.05), "cast_iron", ref=(1, 0, 0))
        sweep(m, _spline([P(0.20, 0.38), P(0.12, 0.27), P(0.0, 0.20), P(-0.12, 0.26), P(-0.25, 0.37)], 4), rect(0.04, 0.025), "cast_iron", ref=(1, 0, 0))
        # feet pads
        for z in (0.26, -0.31):
            bx(m, x - 0.04, x + 0.04, 0, 0.02, z - 0.06, z + 0.06, "cast_iron", bevel=0.005)
        # finial knob on the back top
        m.ico((x, 0.925, -0.352), 0.032, "cast_iron", subdiv=1)
    # seat slats
    for k in range(5):
        z = -0.22 + k * 0.10
        beam(m, (-0.89, 0.43, z), (0.89, 0.43, z), 0.085, 0.04, "bench_slat", ref=(0, 0, 1))
    # back slats along the rake (line from (-0.275,0.55) to (-0.345,0.87))
    for k in range(4):
        u = k / 3.0
        z = -0.285 - 0.065 * u
        y = 0.56 + 0.30 * u
        beam(m, (-0.89, y, z - 0.03), (0.89, y, z - 0.03), 0.075, 0.032, "bench_slat", ref=(0, 0.97, -0.24))
    # centre bearers under the seat and bolts
    for x in (-0.37, 0.0, 0.37):
        beam(m, (x, 0.395, 0.22), (x, 0.395, -0.26), 0.04, 0.03, "cast_iron", ref=(1, 0, 0))
    for sx in (-1, 1):
        for k in range(5):
            m.cyl((sx * 0.74, 0.452, -0.22 + k * 0.10 + 0.0), (0, 1, 0), 0.014, 0.014, 6, "bolt")
        for k in range(4):
            u = k / 3.0
            m.cyl((sx * 0.74, 0.56 + 0.30 * u, -0.285 - 0.065 * u - 0.05), (0, 0.24, -0.97), 0.013, 0.014, 6, "bolt")
    finish(m, "bench", root, smooth=40.0)


# ================================================================== sprinkler
def build_sprinkler():
    make_mat("turf_cap", (0.30, 0.58, 0.18), rough=0.95)
    make_mat("turf_blade", (0.22, 0.50, 0.14), rough=0.95)
    make_mat("cap_rubber", (0.12, 0.14, 0.13), rough=0.8)
    make_mat("riser_steel", (0.70, 0.72, 0.75), metallic=0.85, rough=0.3)
    make_mat("nozzle_brass", (0.80, 0.60, 0.22), metallic=0.8, rough=0.35)
    make_mat("arc_ring", (0.16, 0.38, 0.78), rough=0.5)
    make_mat("riser_ring", (0.15, 0.15, 0.16), rough=0.6)
    root = empty("sprinkler")
    m = MB()
    # cut-turf cap, slightly domed, with a skirt of turf
    m.lathe((0, 0, 0), (0, 1, 0), [(0.0, 0.034), (0.10, 0.034), (0.16, 0.02), (0.185, 0.0)], 16, "turf_cap", solid=False)
    m.lathe((0, 0, 0), (0, 1, 0), [(0.185, 0.0), (0.185, 0.02), (0.16, 0.026)], 16, "turf_cap", solid=False, flip=True)
    # rubber cover annulus around the riser hole
    m.lathe((0, 0, 0), (0, 1, 0), [(0.075, 0.034), (0.095, 0.034), (0.10, 0.04), (0.10, 0.048), (0.075, 0.048), (0.052, 0.044), (0.052, 0.034)], 14, "cap_rubber", closed=True)
    # riser ring (retainer) and wiper seal
    m.lathe((0, 0, 0), (0, 1, 0), [(0.048, 0.044), (0.062, 0.044), (0.062, 0.062), (0.048, 0.062)], 14, "riser_ring", closed=True)
    # popped-up riser: lower sleeve, stepped shaft
    m.lathe((0, 0, 0), (0, 1, 0), [(0.0, 0.05), (0.040, 0.05), (0.040, 0.14), (0.034, 0.145), (0.034, 0.22), (0.0, 0.22)], 14, "riser_steel")
    m.lathe((0, 0, 0), (0, 1, 0), [(0.038, 0.14), (0.046, 0.14), (0.046, 0.155), (0.038, 0.155)], 14, "riser_ring", closed=True)
    # rotor head, arc adjuster ring, nozzle barrel + tip, flow screw
    m.lathe((0, 0, 0), (0, 1, 0), [(0.0, 0.22), (0.044, 0.22), (0.048, 0.235), (0.048, 0.262), (0.04, 0.272), (0.0, 0.278)], 14, "nozzle_brass")
    m.lathe((0, 0, 0), (0, 1, 0), [(0.047, 0.226), (0.054, 0.226), (0.054, 0.242), (0.047, 0.242)], 14, "arc_ring", closed=True)
    q = Vector((0, 0.42, 1)).normalized()
    m.cyl(Vector((0, 0.250, 0.052)), q, 0.0125, 0.06, 10, "riser_steel")
    m.cyl(Vector((0, 0.256, 0.081)), q, 0.017, 0.012, 10, "riser_ring")
    m.cyl((0, 0.279, 0.0), (0, 1, 0), 0.010, 0.012, 8, "riser_steel")
    # tufts of grass around the cap
    import random
    rnd = random.Random(7)
    for i in range(18):
        a = 2 * math.pi * i / 18 + rnd.uniform(-0.1, 0.1)
        r = 0.20 + rnd.uniform(0, 0.03)
        h = 0.05 + rnd.uniform(0, 0.03)
        c = Vector((r * math.cos(a), 0, r * math.sin(a)))
        d = Vector((math.cos(a), 0, math.sin(a)))
        t = Vector((-d.z, 0, d.x)) * 0.012
        m.face([c - t, c + t, c + d * 0.012 + Vector((0, h, 0))], "turf_blade", hint=d)
        m.face([c - t, c + t, c + d * 0.012 + Vector((0, h, 0))], "turf_blade", hint=-d)
    finish(m, "sprinkler", root, smooth=45.0)


# ================================================================== yardage post
def build_yardage_post():
    make_mat("post_wood", (0.55, 0.38, 0.20), rough=0.85)
    make_mat("post_paint", (0.94, 0.94, 0.90), rough=0.7)
    make_mat("marker", (0.95, 0.80, 0.12), rough=0.6)
    make_mat("plate", (0.97, 0.97, 0.95), rough=0.55)
    make_mat("plate_rim", (0.25, 0.28, 0.32), metallic=0.5, rough=0.5)
    make_mat("collar", (0.52, 0.52, 0.50), rough=0.95)
    make_mat("bolt", (0.70, 0.72, 0.75), metallic=0.8, rough=0.35)
    root = empty("yardage_post")
    m = MB()
    m.lathe((0, 0, 0), (0, 1, 0), [(0.0, 0.035), (0.10, 0.035), (0.13, 0.02), (0.14, 0.0)], 10, "collar", solid=False)
    m.lathe((0, 0, 0), (0, 1, 0), [(0.14, 0.0), (0.12, 0.034), (0.0, 0.034)], 10, "collar", solid=False, flip=True)
    bx(m, -0.045, 0.045, 0.03, 0.54, -0.045, 0.045, "post_wood", bevel=0.007)
    bx(m, -0.049, 0.049, 0.54, 0.66, -0.049, 0.049, "marker", bevel=0.004)          # tintable colour band
    bx(m, -0.045, 0.045, 0.66, 0.86, -0.045, 0.045, "post_paint", bevel=0.007)        # blank painted top
    m.lathe((0, 0.86, 0), (0, 1, 0), [(0.056, 0), (0.054, 0.0), (0.02, 0.04), (0.0, 0.043)], 4, "post_paint", phase=math.pi / 4)
    # blank plate on stand-offs
    for sx in (-1, 1):
        for sy in (0.72, 0.80):
            m.cyl((sx * 0.07, sy, 0.056), (0, 0, 1), 0.007, 0.022, 6, "bolt")
    bx(m, -0.095, 0.095, 0.69, 0.83, 0.058, 0.066, "plate_rim")
    m.face([(-0.085, 0.70, 0.0665), (0.085, 0.70, 0.0665), (0.085, 0.82, 0.0665), (-0.085, 0.82, 0.0665)], "plate", hint=(0, 0, 1))
    finish(m, "yardage_post", root, smooth=40.0)


# ================================================================== ob stake
def build_ob_stake():
    make_mat("stake_white", (0.96, 0.96, 0.93), rough=0.7)
    make_mat("stake_band", (0.98, 0.58, 0.10), rough=0.6)
    make_mat("stake_ground", (0.36, 0.30, 0.20), rough=1.0)
    make_mat("stake_scuff", (0.82, 0.82, 0.78), rough=0.9)
    root = empty("ob_stake")
    m = MB()
    ph = math.pi / 8
    m.lathe((0, 0, 0), (0, 1, 0), [(0.0, 0.0), (0.030, 0.0), (0.0285, 0.35), (0.026, 0.80), (0.0245, 1.02)], 8, "stake_white", phase=ph)
    m.lathe((0, 0, 0), (0, 1, 0), [(0.0252, 1.02), (0.0252, 1.14)], 8, "stake_band", phase=ph, solid=False)
    m.lathe((0, 0, 0), (0, 1, 0), [(0.0245, 1.14), (0.0245, 1.15), (0.016, 1.185), (0.0, 1.20)], 8, "stake_white", phase=ph, solid=False)
    m.lathe((0, 0, 0), (0, 1, 0), [(0.0245, 1.02), (0.0262, 1.02), (0.0262, 1.14), (0.0245, 1.14)], 8, "stake_band", phase=ph, closed=True)
    m.lathe((0, 0, 0), (0, 1, 0), [(0.0262, 1.0), (0.0275, 1.0), (0.0275, 1.02), (0.0262, 1.02)], 8, "stake_scuff", phase=ph, closed=True)
    # dirt heap at the foot, three chunky stones
    m.lathe((0, 0, 0), (0, 1, 0), [(0.0, 0.05), (0.04, 0.045), (0.085, 0.015), (0.10, 0.0)], 8, "stake_ground", solid=False)
    m.lathe((0, 0, 0), (0, 1, 0), [(0.10, 0.0), (0.085, 0.012), (0.0, 0.05)], 8, "stake_ground", solid=False, flip=True)
    finish(m, "ob_stake", root, smooth=45.0)


# ================================================================== ball washer
def build_ball_washer():
    make_mat("washer_green", (0.12, 0.34, 0.22), metallic=0.3, rough=0.5)
    make_mat("washer_dark", (0.10, 0.14, 0.13), metallic=0.5, rough=0.5)
    make_mat("chrome", (0.80, 0.82, 0.85), metallic=0.95, rough=0.2)
    make_mat("grip_wood", (0.62, 0.40, 0.18), rough=0.7)
    make_mat("plate", (0.97, 0.96, 0.92), rough=0.55)
    make_mat("plate_rim", (0.22, 0.26, 0.30), metallic=0.5, rough=0.5)
    make_mat("towel", (0.93, 0.93, 0.90), rough=0.95)
    make_mat("towel_stripe", (0.18, 0.42, 0.72), rough=0.95)
    make_mat("bolt", (0.70, 0.72, 0.75), metallic=0.8, rough=0.35)
    root = empty("ball_washer")
    m = MB()
    # base flange, post, collars
    m.lathe((0, 0, 0), (0, 1, 0), [(0.0, 0.0), (0.12, 0.0), (0.12, 0.018), (0.07, 0.03), (0.042, 0.05), (0.042, 0.06), (0.0, 0.06)], 10, "washer_dark")
    for a in range(4):
        t = a * math.pi / 2 + math.pi / 4
        m.cyl((0.095 * math.cos(t), 0.02, 0.095 * math.sin(t)), (0, 1, 0), 0.012, 0.012, 6, "bolt")
    m.lathe((0, 0, 0), (0, 1, 0), [(0.0, 0.06), (0.035, 0.06), (0.032, 0.40), (0.030, 0.72), (0.0, 0.72)], 10, "washer_green")
    m.lathe((0, 0, 0), (0, 1, 0), [(0.034, 0.30), (0.044, 0.30), (0.044, 0.325), (0.034, 0.325)], 10, "washer_dark", closed=True)
    # blank plate on the post
    bx(m, -0.075, 0.075, 0.44, 0.58, 0.026, 0.034, "plate_rim")
    m.face([(-0.066, 0.45, 0.0345), (0.066, 0.45, 0.0345), (0.066, 0.57, 0.0345), (-0.066, 0.57, 0.0345)], "plate", hint=(0, 0, 1))
    for sx in (-1, 1):
        for sy in (0.46, 0.56):
            m.cyl((sx * 0.06, sy, 0.036), (0, 0, 1), 0.006, 0.005, 6, "bolt")
    # mounting saddle + barrel (cup, body, lid, funnel)
    bx(m, -0.07, 0.07, 0.70, 0.74, -0.07, 0.07, "washer_dark")
    m.lathe((0, 0, 0), (0, 1, 0), [(0.0, 0.73), (0.075, 0.73), (0.092, 0.76), (0.092, 0.985), (0.0, 0.985)], 14, "washer_green")
    m.lathe((0, 0, 0), (0, 1, 0), [(0.094, 0.80), (0.099, 0.80), (0.099, 0.82), (0.094, 0.82)], 14, "chrome", closed=True)
    m.lathe((0, 0, 0), (0, 1, 0), [(0.094, 0.935), (0.099, 0.935), (0.099, 0.955), (0.094, 0.955)], 14, "chrome", closed=True)
    m.lathe((0, 0, 0), (0, 1, 0), [(0.0, 0.985), (0.099, 0.985), (0.095, 1.015), (0.075, 1.05), (0.05, 1.07), (0.0, 1.075)], 14, "washer_green")
    m.lathe((0, 0, 0), (0, 1, 0), [(0.052, 1.06), (0.046, 1.06), (0.036, 1.095), (0.041, 1.098), (0.050, 1.07)], 10, "chrome", closed=True)
    m.ico((0, 1.01, 0.093), 0.022, "chrome", subdiv=1, scale=(1, 1, 0.5))          # window boss
    # crank: shaft, hub, arm, grip (+X side)
    m.cyl((0.13, 0.86, 0), (1, 0, 0), 0.010, 0.07, 8, "chrome")
    m.lathe((0.17, 0.86, 0), (1, 0, 0), [(0.022, 0.0), (0.022, 0.012), (0.012, 0.018), (0.0, 0.018)], 8, "chrome", closed=False)
    beam(m, (0.185, 0.86, 0), (0.185, 0.77, 0.04), 0.024, 0.014, "chrome", ref=(1, 0, 0))
    m.lathe((0.185, 0.77, 0.04), (1, 0, 0), [(0.016, 0.0), (0.018, 0.03), (0.018, 0.07), (0.012, 0.085), (0.0, 0.088)], 10, "grip_wood")
    # towel loop (-X side) with a draped towel
    loop = _spline([(-0.03, 0.64, 0), (-0.12, 0.64, 0), (-0.17, 0.60, 0), (-0.17, 0.53, 0), (-0.12, 0.49, 0), (-0.03, 0.49, 0)], 3)
    sweep(m, loop, circ(0.008, 6), "chrome", ref=(0, 0, 1))
    bx(m, -0.15, -0.04, 0.30, 0.655, 0.014, 0.024, "towel")
    bx(m, -0.15, -0.04, 0.30, 0.655, -0.024, -0.014, "towel")
    bx(m, -0.15, -0.04, 0.645, 0.655, -0.024, 0.024, "towel")
    bx(m, -0.15, -0.04, 0.34, 0.37, 0.0135, 0.0245, "towel_stripe")
    bx(m, -0.15, -0.04, 0.34, 0.37, -0.0245, -0.0135, "towel_stripe")
    finish(m, "ball_washer", root, smooth=40.0)


# ================================================================== halfway hut
def _lantern(m, x, y, z, glow="lantern_glow"):
    """Cage lantern hanging from the attachment point (x, y, z); total drop ~0.4."""
    rod(m, (x, y, z), (x, y - 0.12, z), 0.006, "lantern_metal")
    m.lathe((x, y - 0.12, z), (0, 1, 0), [(0.0, 0.0), (0.075, 0.0), (0.075, -0.012), (0.04, -0.045), (0.0, -0.05)][::-1], 8, "lantern_metal", solid=False)
    # glowing glass chimney
    m.lathe((x, y - 0.17, z), (0, 1, 0), [(0.0, -0.17 + 0.0), (0.05, -0.17), (0.062, -0.13), (0.062, -0.04), (0.05, 0.0), (0.0, 0.0)], 8, glow)
    # cage bars and base
    for a in range(4):
        t = a * math.pi / 2 + math.pi / 4
        px, pz = x + 0.066 * math.cos(t), z + 0.066 * math.sin(t)
        rod(m, (px, y - 0.34, pz), (px, y - 0.17, pz), 0.005, "lantern_metal")
    m.lathe((x, y - 0.35, z), (0, 1, 0), [(0.0, 0.0), (0.07, 0.0), (0.07, 0.025), (0.0, 0.03)], 8, "lantern_metal")


def build_halfway_hut():
    make_mat("stone_a", (0.60, 0.58, 0.54), rough=0.95)
    make_mat("stone_b", (0.47, 0.46, 0.44), rough=0.95)
    make_mat("log_a", (0.52, 0.34, 0.18), rough=0.9)
    make_mat("log_b", (0.44, 0.28, 0.15), rough=0.9)
    make_mat("wood_light", (0.75, 0.56, 0.34), rough=0.8)
    make_mat("wood_dark", (0.30, 0.18, 0.09), rough=0.85)
    make_mat("floor_plank", (0.62, 0.45, 0.26), rough=0.85)
    make_mat("gable_board", (0.58, 0.40, 0.22), rough=0.85)
    make_mat("roof_deck", (0.22, 0.14, 0.09), rough=0.9)
    make_mat("shingle_a", (0.26, 0.16, 0.11), rough=0.9)
    make_mat("shingle_b", (0.34, 0.21, 0.14), rough=0.9)
    make_mat("awning_a", (0.84, 0.14, 0.12), rough=0.85, double=True)
    make_mat("awning_b", (0.96, 0.94, 0.86), rough=0.85, double=True)
    make_mat("iron", (0.17, 0.18, 0.20), metallic=0.7, rough=0.55)
    make_mat("steel", (0.58, 0.61, 0.65), metallic=0.7, rough=0.5)
    make_mat("glass", (0.60, 0.76, 0.85), rough=0.05, alpha=0.4)
    make_mat("shutter", (0.62, 0.12, 0.10), rough=0.8)
    make_mat("sign_board", (0.93, 0.90, 0.80), rough=0.8)
    make_mat("chalkboard", (0.10, 0.16, 0.14), rough=0.9)
    make_mat("planter", (0.40, 0.25, 0.13), rough=0.9)
    make_mat("geranium", (0.82, 0.08, 0.14), rough=0.8)
    make_mat("leaf", (0.13, 0.40, 0.11), rough=0.9)
    make_mat("bottle_g", (0.18, 0.45, 0.22), rough=0.2)
    make_mat("bottle_b", (0.20, 0.32, 0.62), rough=0.2)
    make_mat("can_red", (0.80, 0.12, 0.10), metallic=0.5, rough=0.35)
    make_mat("jar_glass", (0.85, 0.90, 0.88), rough=0.1)
    make_mat("jar_lid", (0.80, 0.62, 0.20), metallic=0.5, rough=0.4)
    make_mat("crate", (0.66, 0.50, 0.28), rough=0.85)
    make_mat("lantern_metal", (0.14, 0.15, 0.17), metallic=0.7, rough=0.5)
    make_mat("lantern_glow", (1.0, 0.88, 0.55), rough=0.3, emit=(1.0, 0.78, 0.35), emit_strength=2.5)
    make_mat("chain", (0.30, 0.31, 0.33), metallic=0.7, rough=0.5)
    make_mat("cloth", (0.93, 0.93, 0.90), rough=0.95)
    root = empty("halfway_hut")
    m = MB()
    import random
    rnd = random.Random(11)
    FY = 0.45                     # floor / footing top
    ZW, XW = 1.9, 2.9             # wall centre lines
    HX, HY0, HY1 = 0.95, 1.15, 2.05   # serving hatch opening (+Z wall)

    # ---- stone footing: random coursed stones around a dark core
    bx(m, -3.0, 3.0, 0, FY, -2.0, 2.0, "stone_b")
    for c in range(2):
        y0, y1 = c * 0.225, (c + 1) * 0.225
        for side in ("f", "b"):
            x = -3.1 + (0.3 if c else 0.0)
            while x < 3.1 - 0.05:
                w = min(rnd.uniform(0.38, 0.7), 3.1 - x)
                zc = (2.1 - 0.15) * (1 if side == "f" else -1)
                bx(m, x + 0.012, x + w - 0.012, y0 + 0.004, y1 - rnd.uniform(0, 0.012), zc - 0.15, zc + 0.15, "stone_a" if rnd.random() < 0.55 else "stone_b")
                x += w
        for side in ("l", "r"):
            z = -2.1 + 0.3 + (0.25 if c else 0.0)
            while z < 2.1 - 0.3 - 0.05:
                w = min(rnd.uniform(0.38, 0.7), 2.1 - 0.3 - z)
                xc = (3.1 - 0.15) * (1 if side == "r" else -1)
                bx(m, xc - 0.15, xc + 0.15, y0 + 0.004, y1 - rnd.uniform(0, 0.012), z + 0.012, z + w - 0.012, "stone_a" if rnd.random() < 0.5 else "stone_b")
                z += w
    # door steps (+X) and flagstones at the hatch
    bx(m, 3.1, 3.55, 0, 0.22, 0.25, 1.35, "stone_a")
    bx(m, 3.55, 3.95, 0, 0.11, 0.30, 1.30, "stone_b")
    for fx, fz in ((-1.2, 2.45), (-0.1, 2.5), (1.0, 2.45), (0.4, 3.1), (-0.8, 3.05)):
        bx(m, fx - 0.4, fx + 0.4, 0, 0.03, fz - 0.3, fz + 0.3, "stone_a")
    # floor boards and sill plates
    for k in range(8):
        bx(m, -3.0, 3.0, FY - 0.0, FY + 0.05, -2.0 + k * 0.5 + 0.01, -2.0 + (k + 1) * 0.5 - 0.01, "floor_plank")
    FY2 = FY + 0.05
    for z in (-ZW, ZW):
        bx(m, -3.15, 3.15, FY, FY2, z - 0.1, z + 0.1, "wood_dark")
    for x in (-XW, XW):
        bx(m, x - 0.1, x + 0.1, FY, FY2, -2.0, 2.0, "wood_dark")

    # ---- log walls (cabin notched corners; front/back courses and side courses interleave)
    def hlog(x0, x1, z, yc, k):
        rod(m, (x0, yc, z), (x1, yc, z), 0.1, "log_a" if k % 2 else "log_b", n=6)

    def slog(x, z0, z1, yc, k):
        rod(m, (x, yc, z0), (x, yc, z1), 0.1, "log_a" if k % 2 else "log_b", n=6)
    for k in range(10):                                   # front and back
        yc = FY2 + 0.1 + 0.2 * k
        hlog(-3.12, 3.12, -ZW, yc, k)
        if HY0 < yc + 0.1 and yc - 0.1 < HY1:
            hlog(-3.12, -HX, ZW, yc, k)
            hlog(HX, 3.12, ZW, yc, k)
        else:
            hlog(-3.12, 3.12, ZW, yc, k)
    for k in range(9):                                    # sides
        yc = FY2 + 0.2 + 0.2 * k
        # left (-X) wall with a window opening
        if 1.10 < yc + 0.1 and yc - 0.1 < 1.95:
            slog(-XW, -2.12, -0.50, yc, k)
            slog(-XW, 0.80, 2.12, yc, k)
        else:
            slog(-XW, -2.12, 2.12, yc, k)
        # right (+X) wall with a door opening
        if yc - 0.1 < 2.05:
            slog(XW, -2.12, 0.35, yc, k)
            slog(XW, 1.25, 2.12, yc, k)
        else:
            slog(XW, -2.12, 2.12, yc, k)
    # wall plates
    PY = FY2 + 2.0 + 0.06
    for z in (-ZW, ZW):
        bx(m, -3.15, 3.15, PY - 0.06, PY + 0.06, z - 0.08, z + 0.08, "wood_dark")
    for x in (-XW, XW):
        bx(m, x - 0.08, x + 0.08, PY - 0.06, PY + 0.06, -2.05, 2.05, "wood_dark")
    # door lintel and window lintel beams are the cut log ends; frames below

    # ---- gable ends: vertical boards up to the roof underside
    RY, SL = 3.85, 0.6
    roof_y = lambda z: RY - SL * abs(z)
    for sx in (-1, 1):
        x = sx * 2.97
        n = 19
        for k in range(n):
            zc = -1.9 + (k + 0.5) * 3.8 / n
            top = roof_y(abs(zc) + 0.1) - 0.10
            bx(m, x - 0.03, x + 0.03, PY + 0.06, top, zc - 0.095, zc + 0.095, "gable_board")
        bx(m, x - 0.04, x + 0.04, PY + 0.06, PY + 0.10, -1.95, 1.95, "wood_dark")
        # vent louvres in the gable
        for k in range(4):
            bx(m, x + sx * 0.04 - 0.012, x + sx * 0.04 + 0.012, PY + 0.55 + k * 0.1, PY + 0.62 + k * 0.1, -0.35, 0.35, "wood_dark")

    # ---- roof: sheathing, shingle rows, ridge, barge boards, rafters
    EZ, RXE = 2.75, 3.55
    for sz in (1, -1):
        slope_len = math.hypot(EZ, SL * EZ)
        dv = slope_len / 15.0
        v = Vector((0, -SL * sz * 1.0, sz * 1.0)).normalized() if False else Vector((0, -SL, sz)).normalized()
        nrm = Vector((0, 1, SL * sz)).normalized()
        o = Vector((0, RY, 0))
        ext(m, [(-RXE, 0), (RXE, 0), (RXE, slope_len), (-RXE, slope_len)], o, Vector((1, 0, 0)), v, nrm, -0.10, -0.02, "roof_deck")
        for j in range(15):
            v0, v1 = j * dv, (j + 1) * dv
            tw, g, nd = 0.5, 0.035, 0.07
            nt = int(round(2 * RXE / tw))
            tw = 2 * RXE / nt
            off = (tw / 2) if j % 2 else 0.0
            pts = [(-RXE, v0), (RXE, v0), (RXE, v1)]
            xs = [RXE - off - i * tw for i in range(nt + 1)]
            bounds = [xx for xx in xs if -RXE + 0.05 < xx < RXE - 0.05]
            for xb in bounds:
                pts += [(xb + g / 2, v1), (xb + g / 2, v1 - nd), (xb - g / 2, v1 - nd), (xb - g / 2, v1)]
            pts.append((-RXE, v1))
            P3 = [o + Vector((1, 0, 0)) * x_ + v * v_ + nrm * 0.006 for x_, v_ in pts]
            m.face(P3, "shingle_a" if j % 2 == 0 else "shingle_b", hint=nrm)
            # a lip: shows thickness along the butt line
            m.face([o + Vector((1, 0, 0)) * -RXE + v * v1 + nrm * 0.006, o + Vector((1, 0, 0)) * RXE + v * v1 + nrm * 0.006,
                    o + Vector((1, 0, 0)) * RXE + v * v1 + nrm * -0.014, o + Vector((1, 0, 0)) * -RXE + v * v1 + nrm * -0.014],
                   "roof_deck", hint=v)
        # fascia at the eave
        ye = roof_y(EZ)
        bx(m, -RXE, RXE, ye - 0.16, ye + 0.0, sz * EZ - 0.03, sz * EZ + 0.03, "wood_dark")
    bx(m, -RXE - 0.05, RXE + 0.05, RY - 0.06, RY + 0.10, -0.10, 0.10, "wood_dark")
    for sx in (-1, 1):                                    # barge boards
        for sz in (-1, 1):
            beam(m, (sx * RXE, roof_y(EZ) - 0.12, sz * EZ), (sx * RXE, RY - 0.02, 0), 0.04, 0.22, "wood_dark", ref=(0, 0, 1))
    # rafters and ties under the roof
    for i in range(11):
        x = -3.3 + i * 0.66
        for sz in (-1, 1):
            beam(m, (x, RY - 0.12, 0.05 * sz), (x, roof_y(EZ) - 0.12, sz * EZ), 0.07, 0.12, "wood_dark", ref=(1, 0, 0))
        beam(m, (x, PY - 0.02 + 0.08, -ZW), (x, PY - 0.02 + 0.08, ZW), 0.07, 0.10, "wood_dark", ref=(1, 0, 0))
    beam(m, (-3.4, RY - 0.18, 0), (3.4, RY - 0.18, 0), 0.10, 0.12, "wood_dark", ref=(0, 1, 0))

    # ---- serving hatch: frame, sill, awning, counter ledge
    zf = ZW + 0.1
    bx(m, -HX - 0.12, -HX, HY0 - 0.1, HY1 + 0.1, zf - 0.03, zf + 0.06, "wood_light")
    bx(m, HX, HX + 0.12, HY0 - 0.1, HY1 + 0.1, zf - 0.03, zf + 0.06, "wood_light")
    bx(m, -HX - 0.12, HX + 0.12, HY1, HY1 + 0.12, zf - 0.03, zf + 0.06, "wood_light")
    bx(m, -HX - 0.12, HX + 0.12, HY0 - 0.12, HY0, zf - 0.03, zf + 0.06, "wood_light")
    bx(m, -HX - 0.2, HX + 0.2, HY0 - 0.02, HY0 + 0.04, zf - 0.03, zf + 0.44, "wood_dark")       # counter ledge
    for sx in (-1, 1):
        beam(m, (sx * 0.75, HY0 - 0.02, zf + 0.0), (sx * 0.75, HY0 - 0.42, zf + 0.40), 0.05, 0.05, "wood_dark", ref=(1, 0, 0))
        bx(m, sx * 0.75 - 0.03, sx * 0.75 + 0.03, HY0 - 0.44, HY0 - 0.02, zf - 0.03, zf + 0.0, "wood_dark")
    # awning: fabric stripes (sloping away from the wall), roller bar, arms, scalloped valance
    ay0, ay1, az0, az1 = 2.26, 1.82, ZW + 0.1, 3.25
    stripes = 8
    aw = 1.40
    for k in range(stripes):
        xa = -aw + 2 * aw * k / stripes
        xb = -aw + 2 * aw * (k + 1) / stripes
        mat_ = "awning_a" if k % 2 == 0 else "awning_b"

        def pf(u, vv, xa=xa, xb=xb):
            return (xa + (xb - xa) * u, ay0 + (ay1 - ay0) * vv - 0.03 * math.sin(math.pi * vv) , az0 + (az1 - az0) * vv)
        grid_face(m, pf, 1, 3, mat_, (0, 1, 0.2))
        m.face([(xa, ay1, az1), (xb, ay1, az1), ((xa + xb) / 2, ay1 - 0.2, az1 + 0.0)], mat_, hint=(0, 0, 1))
    for sx in (-1, 1):
        m.face([(sx * aw, ay0, az0), (sx * aw, ay1, az1), (sx * aw, ay1 - 0.2, az1)], "awning_a", hint=(sx, 0, 0))
    rod(m, (-aw - 0.05, ay1 + 0.0, az1 + 0.0), (aw + 0.05, ay1 + 0.0, az1 + 0.0), 0.02, "iron", n=6)
    rod(m, (-aw - 0.05, ay0 + 0.02, az0 + 0.02), (aw + 0.05, ay0 + 0.02, az0 + 0.02), 0.02, "iron", n=6)
    for sx in (-1, 1):
        x = sx * aw
        beam(m, (x, ay0 + 0.0, az0), (x, ay1 - 0.02, az1), 0.04, 0.05, "wood_dark", ref=(1, 0, 0))
        beam(m, (x, 1.55, az0 + 0.0), (x, ay1 - 0.04, az1 - 0.02), 0.035, 0.04, "wood_dark", ref=(1, 0, 0))
    # ---- sign (blank) and menu board on the wall either side of the hatch
    for xc, mat_ in ((-2.05, "sign_board"), (2.05, "chalkboard")):
        zb = ZW + 0.1
        bx(m, xc - 0.7, xc + 0.7, 1.28, 1.88, zb + 0.0, zb + 0.03, "wood_dark")
        bx(m, xc - 0.64, xc + 0.64, 1.34, 1.82, zb + 0.03, zb + 0.045, mat_)
        for sx in (-1, 1):
            rod(m, (xc + sx * 0.5, 1.88, zb + 0.03), (xc + sx * 0.5, 2.1, zb + 0.03), 0.006, "chain")
            m.cyl((xc + sx * 0.5, 2.12, zb + 0.03), (0, 0, 1), 0.02, 0.012, 6, "iron")
    # ---- door (+X wall)
    xd = XW + 0.1
    bx(m, xd - 0.04, xd + 0.05, 0.5, 2.1, 0.25, 0.37, "wood_light")
    bx(m, xd - 0.04, xd + 0.05, 0.5, 2.1, 1.23, 1.35, "wood_light")
    bx(m, xd - 0.04, xd + 0.05, 2.05, 2.17, 0.25, 1.35, "wood_light")
    for k in range(4):                                    # vertical boards
        zb = 0.37 + k * 0.215
        bx(m, xd - 0.02, xd + 0.03, 0.5, 2.05, zb + 0.005, zb + 0.21, "wood_dark")
    for y in (0.8, 1.7):
        bx(m, xd + 0.03, xd + 0.05, y, y + 0.12, 0.37, 1.23, "iron")
    m.cyl((xd + 0.07, 1.15, 1.12), (1, 0, 0), 0.03, 0.03, 8, "iron")
    # ---- window (-X wall): frame, glass, shutters, planter
    xw = -XW - 0.1
    bx(m, xw - 0.05, xw + 0.04, 1.03, 1.13, -0.58, 0.88, "wood_light")                 # sill
    bx(m, xw - 0.03, xw + 0.04, 1.95, 2.05, -0.55, 0.85, "wood_light")                 # head
    for z0 in (-0.55, 0.75):
        bx(m, xw - 0.03, xw + 0.04, 1.13, 1.95, z0, z0 + 0.10, "wood_light")
    m.face([(xw + 0.04, 1.13, -0.45), (xw + 0.04, 1.13, 0.75), (xw + 0.04, 1.95, 0.75), (xw + 0.04, 1.95, -0.45)], "glass", hint=(1, 0, 0))
    bx(m, xw + 0.03, xw + 0.06, 1.13, 1.95, 0.14, 0.18, "wood_light")
    bx(m, xw + 0.03, xw + 0.06, 1.50, 1.54, -0.45, 0.75, "wood_light")
    for z0, z1 in ((0.95, 1.55), (-1.15, -0.55)):                                      # open shutters flat on the wall
        bx(m, xw - 0.04, xw, 1.03, 2.05, z0, z1, "shutter")
        for k in range(3):
            bx(m, xw - 0.06, xw - 0.04, 1.08 + k * 0.45, 1.16 + k * 0.45, z0 + 0.04, z1 - 0.04, "wood_light")
    bx(m, xw - 0.34, xw - 0.04, 0.82, 1.03, -0.5, 0.80, "planter")
    for k in range(6):
        m.ico((xw - 0.19, 1.07 + 0.01 * (k % 2), -0.40 + k * 0.22), 0.085, "geranium" if k % 2 == 0 else "leaf", subdiv=1, scale=(1, 0.8, 1))

    # ---- interior: counter cabinet, shelves, stove, crates
    bx(m, -1.9, 1.9, FY2, 1.08, 1.30, 1.82, "wood_light")
    bx(m, -1.95, 1.95, 1.08, 1.12, 1.26, 1.86, "wood_dark")
    for k in range(4):
        x0 = -1.8 + k * 0.9
        bx(m, x0 + 0.04, x0 + 0.86, FY2 + 0.08, 1.0, 1.255, 1.30, "wood_dark")
        m.cyl((x0 + 0.45, 0.82, 1.24), (0, 0, 1), 0.022, 0.03, 6, "iron")
    for y, nbk in ((1.15, 5), (1.62, 5), (2.06, 4)):
        bx(m, -1.9, 2.2, y, y + 0.04, -ZW + 0.08, -ZW + 0.42, "wood_light")
        for x in (-1.7, 0.2, 2.0):
            beam(m, (x, y, -ZW + 0.1), (x, y - 0.22, -ZW + 0.1), 0.035, 0.04, "wood_dark", ref=(1, 0, 0))
        for k in range(nbk):
            xx = -1.6 + k * (3.6 / nbk) + rnd.uniform(-0.05, 0.05)
            kind = rnd.choice(["bg", "bb", "can", "jar"])
            zz = -ZW + 0.25
            if kind in ("bg", "bb"):
                mt = "bottle_g" if kind == "bg" else "bottle_b"
                m.lathe((xx, y + 0.04, zz), (0, 1, 0), [(0.0, 0.0), (0.036, 0.0), (0.036, 0.17), (0.014, 0.23), (0.014, 0.28), (0.0, 0.28)], 8, mt)
            elif kind == "can":
                m.cyl((xx, y + 0.04 + 0.07, zz), (0, 1, 0), 0.04, 0.14, 8, "can_red")
            else:
                m.cyl((xx, y + 0.04 + 0.08, zz), (0, 1, 0), 0.05, 0.16, 8, "jar_glass")
                m.cyl((xx, y + 0.04 + 0.17, zz), (0, 1, 0), 0.052, 0.025, 8, "jar_lid")
    # iron stove + chimney pipe
    sx_, sz_ = -2.35, -1.25
    m.lathe((sx_, FY2, sz_), (0, 1, 0), [(0.0, 0.0), (0.26, 0.0), (0.27, 0.06), (0.27, 0.62), (0.20, 0.70), (0.0, 0.70)], 10, "iron")
    for a in range(3):
        t = a * 2 * math.pi / 3
        rod(m, (sx_ + 0.2 * math.cos(t), FY2, sz_ + 0.2 * math.sin(t)), (sx_ + 0.2 * math.cos(t), FY2 + 0.08, sz_ + 0.2 * math.sin(t)), 0.03, "iron")
    pipe_top = 4.12
    m.lathe((sx_, FY2 + 0.70, sz_), (0, 1, 0), [(0.0, 0.0), (0.06, 0.0), (0.06, pipe_top - FY2 - 0.70), (0.0, pipe_top - FY2 - 0.70)], 10, "steel")
    for yy in (1.9, 2.8, 3.55):
        m.lathe((sx_, yy, sz_), (0, 1, 0), [(0.062, 0.0), (0.075, 0.0), (0.075, 0.05), (0.062, 0.05)], 10, "iron", closed=True)
    m.lathe((sx_, pipe_top, sz_), (0, 1, 0), [(0.0, 0.0), (0.12, -0.0), (0.12, 0.0), (0.09, 0.05), (0.0, 0.14)], 10, "iron")
    for a in range(3):
        t = a * 2 * math.pi / 3 + 0.5
        rod(m, (sx_ + 0.05 * math.cos(t), pipe_top - 0.02, sz_ + 0.05 * math.sin(t)), (sx_ + 0.10 * math.cos(t), pipe_top + 0.01, sz_ + 0.10 * math.sin(t)), 0.006, "iron")
    # roof collar around the pipe
    cy_ = roof_y(sz_) + 0.02
    bx(m, sx_ - 0.17, sx_ + 0.17, cy_ - 0.02, cy_ + 0.06, sz_ - 0.17, sz_ + 0.17, "iron")
    # crates and sack stack, inside to the right
    for k, (cx, cz, cy, s_) in enumerate(((2.35, 1.2, 0, 0.5), (2.35, 0.4, 0, 0.5), (2.35, 0.8, 0.5, 0.45), (2.4, -0.55, 0, 0.55))):
        bx(m, cx - s_ / 2, cx + s_ / 2, FY2 + cy, FY2 + cy + s_, cz - s_ / 2, cz + s_ / 2, "crate")
        for dy in (0.1, 0.3):
            bx(m, cx - s_ / 2 - 0.005, cx + s_ / 2 + 0.005, FY2 + cy + dy * s_ / 0.5, FY2 + cy + dy * s_ / 0.5 + 0.03, cz - s_ / 2 - 0.005, cz + s_ / 2 + 0.005, "wood_dark")

    # ---- outside: barrels, stools, woodpile, lanterns
    def barrel(x, z, h=0.78):
        prof = [(0.0, 0.0), (0.22, 0.0), (0.27, h * 0.2), (0.30, h * 0.5), (0.27, h * 0.8), (0.23, h), (0.0, h)]
        m.lathe((x, 0, z), (0, 1, 0), prof, 12, "wood_light")
        for t, rr in ((0.07, 0.235), (0.28, 0.285), (0.72, 0.285), (0.93, 0.245)):
            y = h * t
            m.lathe((x, y - 0.015, z), (0, 1, 0), [(rr, 0.0), (rr + 0.012, 0.0), (rr + 0.012, 0.03), (rr, 0.03)], 12, "iron", closed=True)
    barrel(-2.4, 2.55)
    barrel(-1.85, 2.75, 0.7)
    barrel(2.5, 2.5)
    bx(m, 2.15, 2.85, 0.78, 0.82, 2.15, 2.85, "wood_dark")                      # board lying across the third barrel
    for sx in (-0.9, -0.15, 0.7):
        z = 2.95
        m.lathe((sx, 0.48, z), (0, 1, 0), [(0.0, 0.0), (0.17, 0.0), (0.18, 0.035), (0.0, 0.04)], 10, "wood_light")
        for a in range(3):
            t = a * 2 * math.pi / 3 + 0.4
            rod(m, (sx + 0.13 * math.cos(t), 0.48, z + 0.13 * math.sin(t)), (sx + 0.19 * math.cos(t), 0.0, z + 0.19 * math.sin(t)), 0.017, "wood_dark")
        rod(m, (sx - 0.14, 0.2, z), (sx + 0.14, 0.2, z), 0.012, "wood_dark")
    # woodpile against the -X wall near the back corner
    stack = [(0, 6), (1, 5), (2, 4), (3, 3)]
    for row, cnt in stack:
        for k in range(cnt):
            zc = -1.9 + 0.5 * row * 0.5 + 0.18 * k + 0.1
            yc = 0.09 + row * 0.17
            rod(m, (-XW - 0.7, yc, zc), (-XW - 0.12, yc, zc), 0.075, "log_a" if (k + row) % 2 else "log_b", n=6)
    bx(m, -XW - 0.74, -XW - 0.70, 0, 0.7, -2.05, -0.55, "wood_dark")
    bx(m, -XW - 0.14, -XW - 0.10, 0, 0.7, -2.05, -0.55, "wood_dark")
    # lanterns: awning corners, hut front corners, door
    _lantern(m, -aw + 0.12, ay1 - 0.02, az1 - 0.05)
    _lantern(m, aw - 0.12, ay1 - 0.02, az1 - 0.05)
    for sx in (-1, 1):
        x = sx * 3.0
        beam(m, (x, 2.28, ZW + 0.1), (x, 2.28, 2.45), 0.04, 0.04, "iron", ref=(1, 0, 0))
        beam(m, (x, 1.98, ZW + 0.1), (x, 2.28, 2.45), 0.03, 0.03, "iron", ref=(1, 0, 0))
        _lantern(m, x, 2.26, 2.45)
    beam(m, (XW + 0.1, 2.3, 1.9), (XW + 0.55, 2.3, 1.9), 0.04, 0.04, "iron", ref=(0, 0, 1))
    _lantern(m, XW + 0.55, 2.28, 1.9)
    finish(m, "halfway_hut", root, smooth=35.0)


# ================================================================== bunker rake
def build_bunker_rake():
    make_mat("rake_handle", (0.78, 0.60, 0.36), rough=0.8)
    make_mat("rake_head", (0.58, 0.38, 0.20), rough=0.85)
    make_mat("tine_steel", (0.62, 0.65, 0.68), metallic=0.8, rough=0.4)
    make_mat("rake_grip", (0.14, 0.34, 0.60), rough=0.7)
    root = empty("bunker_rake")
    m = MB()
    zh = 0.62                                              # head position along the handle
    y_h = 0.115                                            # handle height at the head
    # handle: gently raking up to the head (lying on its tines)
    p0, p1 = Vector((0.0, 0.020, -0.98)), Vector((0.0, y_h, zh))
    rod(m, p0, p1, 0.016, "rake_handle", n=8)
    m.ico(p0 + Vector((0, 0, -0.012)), 0.019, "rake_handle", subdiv=1)
    # grip band near the free end
    d = (p1 - p0).normalized()
    m.lathe(p0 + d * 0.20, d, [(0.0185, 0.0), (0.0185, 0.28)], 8, "rake_grip", solid=False)
    m.lathe(p0 + d * 0.20, d, [(0.0185, 0.0), (0.0, 0.0)], 8, "rake_grip", solid=False)
    # head: wooden bar, steel strap and tines
    bx(m, -0.26, 0.26, 0.075, 0.12, zh - 0.03, zh + 0.03, "rake_head")
    bx(m, -0.265, 0.265, 0.074, 0.082, zh + 0.03, zh + 0.036, "tine_steel")
    bx(m, -0.265, 0.265, 0.112, 0.12, zh + 0.03, zh + 0.036, "tine_steel")
    n = 14
    for i in range(n):
        x = -0.234 + i * 0.468 / (n - 1)
        m.lathe((x, 0.0, zh), (0, 1, 0), [(0.0035, 0.0), (0.0075, 0.078)], 4, "tine_steel", phase=math.pi / 4)
    # ferrule and braces
    m.lathe(Vector((0, y_h, zh)) - d * 0.10, d, [(0.022, 0.0), (0.022, 0.10), (0.017, 0.10)], 8, "tine_steel", solid=False)
    for sx in (-1, 1):
        beam(m, (0.0, 0.078, zh - 0.34), (sx * 0.22, 0.092, zh - 0.02), 0.022, 0.016, "rake_head", ref=(0, 1, 0))
        m.cyl((sx * 0.22, 0.12, zh), (0, 1, 0), 0.008, 0.01, 6, "tine_steel")
    m.cyl((0.0, 0.108, zh - 0.34 + 0.0), (0, 1, 0), 0.008, 0.01, 6, "tine_steel")
    finish(m, "bunker_rake", root, smooth=45.0)


# ================================================================== parasol
def build_parasol():
    make_mat("parasol_a", (0.84, 0.13, 0.12), rough=0.8, double=True)
    make_mat("parasol_b", (0.96, 0.93, 0.84), rough=0.8, double=True)
    make_mat("pole_steel", (0.74, 0.76, 0.79), metallic=0.8, rough=0.35)
    make_mat("rib_wood", (0.66, 0.48, 0.26), rough=0.7)
    make_mat("crank_housing", (0.20, 0.22, 0.25), metallic=0.5, rough=0.5)
    make_mat("grip_wood", (0.62, 0.40, 0.18), rough=0.7)
    make_mat("base_steel", (0.30, 0.33, 0.37), metallic=0.65, rough=0.5)
    make_mat("base_stone", (0.60, 0.59, 0.56), rough=0.95)
    root = empty("parasol")
    m = MB()
    R, Y_A, DROP = 1.5, 2.42, 0.44
    yr = lambda r: Y_A - DROP * (r / R) ** 1.7
    NG, NA, NRI = 8, 4, 6

    def pt(r, ang, u):
        s = math.sin(math.pi * u)
        k = (r / R) ** 2
        rr = r * (1 - 0.05 * s * k)
        yy = yr(r) - 0.035 * s * k
        return (rr * math.cos(ang), yy, rr * math.sin(ang))
    for g in range(NG):
        mat_ = "parasol_a" if g % 2 == 0 else "parasol_b"
        a0 = 2 * math.pi * g / NG
        da = 2 * math.pi / NG

        def fn(i_, j_, a0=a0, da=da):
            u = i_
            r = 0.07 + (R - 0.07) * j_
            return pt(r, a0 + da * u, u)
        grid_face(m, fn, NA, NRI, mat_, (0, 1, 0))
        # hanging valance with a scalloped hem
        for i in range(NA):
            ua, ub = i / NA, (i + 1) / NA
            pa, pb = pt(R, a0 + da * ua, ua), pt(R, a0 + da * ub, ub)
            ha = (pa[0], pa[1] - 0.15 + 0.07 * math.sin(math.pi * ua), pa[2])
            hb = (pb[0], pb[1] - 0.15 + 0.07 * math.sin(math.pi * ub), pb[2])
            m.face([pa, pb, hb, ha], mat_, hint=(pa[0] + pb[0], 0, pa[2] + pb[2]))
    # ribs under the fabric, stretchers, runner
    runner_y = 1.55
    for g in range(NG):
        a = 2 * math.pi * g / NG
        path = [(r * math.cos(a), yr(r) - 0.02, r * math.sin(a)) for r in (0.07, 0.3, 0.55, 0.8, 1.05, 1.3, R * 0.985)]
        sweep(m, path, rect(0.026, 0.02), "rib_wood", ref=(-math.sin(a), 0, math.cos(a)))
        r_s = 0.85
        rod(m, (0.05 * math.cos(a), runner_y + 0.04, 0.05 * math.sin(a)), (r_s * math.cos(a), yr(r_s) - 0.04, r_s * math.sin(a)), 0.009, "rib_wood")
        m.cyl((R * 0.985 * math.cos(a), yr(R * 0.985) - 0.03, R * 0.985 * math.sin(a)), (0, 1, 0), 0.016, 0.03, 6, "pole_steel")
    m.lathe((0, runner_y, 0), (0, 1, 0), [(0.058, 0.0), (0.058, 0.13), (0.04, 0.13), (0.04, 0.0)], 10, "pole_steel", closed=True)
    # pole, hub, finial
    m.lathe((0, 0, 0), (0, 1, 0), [(0.0, 0.18), (0.044, 0.18), (0.044, 1.02), (0.030, 1.02), (0.030, 2.40), (0.0, 2.40)], 12, "pole_steel")
    m.lathe((0, 0, 0), (0, 1, 0), [(0.0, 2.38), (0.075, 2.38), (0.08, 2.41), (0.05, 2.44), (0.03, 2.46), (0.02, 2.48),
                                    (0.032, 2.50), (0.03, 2.53), (0.0, 2.56)], 10, "pole_steel")
    # crank housing, shaft, arm and grip
    bx(m, -0.06, 0.06, 1.02, 1.22, -0.06, 0.06, "crank_housing", bevel=0.01)
    m.cyl((0.095, 1.12, 0), (1, 0, 0), 0.011, 0.07, 8, "pole_steel")
    beam(m, (0.13, 1.12, 0), (0.13, 1.03, 0.05), 0.024, 0.014, "pole_steel", ref=(1, 0, 0))
    m.lathe((0.13, 1.03, 0.05), (1, 0, 0), [(0.016, 0.0), (0.018, 0.04), (0.018, 0.09), (0.012, 0.11), (0.0, 0.112)], 10, "grip_wood")
    # weighted cross base with concrete slabs and a socket sleeve
    bx(m, -0.62, 0.62, 0.0, 0.07, -0.05, 0.05, "base_steel")
    bx(m, -0.05, 0.05, 0.0, 0.07, -0.62, 0.62, "base_steel")
    for sx in (-1, 1):
        bx(m, sx * 0.40 - 0.20, sx * 0.40 + 0.20, 0.07, 0.17, -0.23, 0.23, "base_stone")
        bx(m, -0.23, 0.23, 0.07, 0.17, sx * 0.40 - 0.20, sx * 0.40 + 0.20, "base_stone")
        for k in (-1, 1):
            m.cyl((sx * 0.40, 0.17, k * 0.14), (0, 1, 0), 0.016, 0.02, 6, "base_steel")
            m.cyl((k * 0.14, 0.17, sx * 0.40), (0, 1, 0), 0.016, 0.02, 6, "base_steel")
    m.lathe((0, 0, 0), (0, 1, 0), [(0.0, 0.07), (0.10, 0.07), (0.10, 0.12), (0.072, 0.17), (0.072, 0.52), (0.062, 0.54), (0.062, 0.18), (0.0, 0.18)][:6], 12, "base_steel")
    for a in range(4):
        t = a * math.pi / 2 + math.pi / 4
        beam(m, (0.09 * math.cos(t), 0.08, 0.09 * math.sin(t)), (0.065 * math.cos(t), 0.40, 0.065 * math.sin(t)), 0.03, 0.02, "base_steel", ref=(0, 1, 0))
    finish(m, "parasol", root, smooth=40.0)


# ================================================================== footbridge (unit)
def build_footbridge():
    make_mat("plank", (0.60, 0.42, 0.24), rough=0.85)
    make_mat("plank_b", (0.54, 0.37, 0.20), rough=0.85)
    make_mat("rail_wood", (0.70, 0.52, 0.30), rough=0.8)
    make_mat("post_wood", (0.46, 0.30, 0.16), rough=0.85)
    make_mat("stringer", (0.38, 0.25, 0.13), rough=0.9)
    make_mat("nail", (0.25, 0.26, 0.28), metallic=0.7, rough=0.5)
    make_mat("pier_stone", (0.56, 0.55, 0.52), rough=0.95)
    root = empty("footbridge")
    m = MB()
    # deck planks across the 1 m width (5 per metre)
    for k in range(5):
        z0 = 0.005 + k * 0.2
        mat_ = "plank" if k % 2 == 0 else "plank_b"
        bx(m, -0.5, 0.5, -0.05, 0.0, z0, z0 + 0.19, mat_)
        z = z0 + 0.095
        for x in (-0.40, 0.40):
            for dz in (-0.045, 0.045):
                m.cyl((x, 0.0, z + dz), (0, 1, 0), 0.009, 0.006, 4, "nail", phase=math.pi / 4)
    # side stringers and a centre joist; kick boards
    for x in (-0.40, 0.0, 0.40):
        bx(m, x - 0.035, x + 0.035, -0.27, -0.05, 0.0, 1.0, "stringer")
    for sx in (-1, 1):
        bx(m, sx * 0.5 - (0.025 if sx > 0 else 0), sx * 0.5 + (0 if sx > 0 else 0.025), 0.0, 0.10, 0.0, 1.0, "rail_wood")
        # rails: top, mid, low
        for y, h_ in ((0.97, 0.05), (0.62, 0.04), (0.30, 0.04)):
            bx(m, sx * 0.46 - 0.03, sx * 0.46 + 0.03, y, y + h_, 0.0, 1.0, "rail_wood")
        for zb in (0.2, 0.4, 0.6, 0.8):                    # balusters
            bx(m, sx * 0.46 - 0.012, sx * 0.46 + 0.012, 0.10, 0.97, zb - 0.015, zb + 0.015, "post_wood")
    # end posts at z = 0 and z = 1 (centred on the ends so tiled units share them), transoms, piers, bracing
    for z in (0.0, 1.0):
        bx(m, -0.5, 0.5, -0.27, -0.10, z - 0.04, z + 0.04, "stringer")
        for sx in (-1, 1):
            x = sx * 0.46
            bx(m, x - 0.04, x + 0.04, -0.27, 1.05, z - 0.04, z + 0.04, "post_wood")
            m.lathe((x, 1.05, z), (0, 1, 0), [(0.058, 0.0), (0.058, 0.0), (0.02, 0.05), (0.0, 0.055)], 4, "rail_wood", phase=math.pi / 4)
            # pier leg beneath, footing block, and knee brace across the width
            bx(m, x - 0.045, x + 0.045, -0.95, -0.27, z - 0.045, z + 0.045, "post_wood")
            bx(m, x - 0.14, x + 0.14, -1.05, -0.95, z - 0.14, z + 0.14, "pier_stone")
            beam(m, (x, -0.80, z), (x - sx * 0.30, -0.27, z), 0.035, 0.035, "post_wood", ref=(0, 0, 1))
        beam(m, (-0.46, -0.80, z), (0.46, -0.45, z), 0.035, 0.035, "post_wood", ref=(0, 0, 1))
        beam(m, (0.46, -0.80, z), (-0.46, -0.45, z), 0.035, 0.035, "post_wood", ref=(0, 0, 1))
        for sx in (-1, 1):
            for yy in (0.2, 0.75):
                m.cyl((sx * 0.46, yy, z + 0.04), (0, 0, 1), 0.016, 0.012, 6, "nail")
    finish(m, "footbridge", root, smooth=40.0)
