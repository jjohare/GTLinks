"""Lofted body cage for the cars (v2).

A car body is a dense set of cross-section rings (stations) along its length.  Every ring has the
same 27 points (13 per side + centre), so the surface is a regular grid we can cut windows into,
bend wheel arches into (the arch is a notch in the ring itself), offset into an inner shell, and
lift panels (bonnet) from.  Everything is expressed in the GAME frame (x left, y up, z forward).

Ring layout, right half, index 0..13 (13 is the centre line):
  0 floor inner  1 floor/well inner  2 well ceiling inner  3 well ceiling outer / sill
  4 lower door   5 shoulder           6 belt tuck
  7 8 9 glasshouse side (window rows 7-8, 8-9)       10 roof edge  11 12 roof arch  13 centre
"""
import math
from mathutils import Vector
from gtl import MB, mat

NR = 27                      # ring size: 13 right + centre + 13 left
HALF = 14


def pchip(pts):
    """Monotone cubic Hermite interpolation through (x, y) points (Fritsch-Carlson)."""
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    n = len(xs)
    d = [(ys[i + 1] - ys[i]) / (xs[i + 1] - xs[i]) for i in range(n - 1)]
    m = [d[0]] + [0.0 if d[i - 1] * d[i] <= 0 else 2 * d[i - 1] * d[i] / (d[i - 1] + d[i]) for i in range(1, n - 1)] + [d[-1]]

    def f(x):
        if x <= xs[0]:
            return ys[0]
        if x >= xs[-1]:
            return ys[-1]
        i = 0
        while xs[i + 1] < x:
            i += 1
        h = xs[i + 1] - xs[i]
        t = (x - xs[i]) / h
        h00 = 2 * t ** 3 - 3 * t ** 2 + 1
        h10 = t ** 3 - 2 * t ** 2 + t
        h01 = -2 * t ** 3 + 3 * t ** 2
        h11 = t ** 3 - t ** 2
        return h00 * ys[i] + h10 * h * m[i] + h01 * ys[i + 1] + h11 * h * m[i + 1]
    return f


def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


class Cage:
    def __init__(self, c, st):
        self.c, self.st = c, st
        L, H = c.L, c.roof
        self.T = pchip([(f, v * H) for f, v in st["top"]])
        self.belt = pchip([(f, v * H) for f, v in st["belt"]])
        self.yb = pchip([(f, v) for f, v in st["floor"]])
        self.roof_frac = st["roof_frac"]
        self.wheels = [(c.tr / 2, c.r, c.wb / 2), (c.tr / 2, c.r, -c.wb / 2)]
        self.zc = [c.wb / 2, -c.wb / 2]
        self.Ra = c.r + 0.075
        self.xi = c.tr / 2 - c.ww / 2 - 0.06

    # ---- plan shape: superellipse rounding at nose and tail
    def plan(self, f):
        st = self.st
        fe, p = st["nose_fe"], st["nose_p"]
        if f < fe:
            return max(1e-3, (1 - ((fe - f) / fe) ** p)) ** (1 / p)
        fe2, p2 = st["tail_fe"], st["tail_p"]
        if f > 1 - fe2:
            return max(1e-3, (1 - ((f - (1 - fe2)) / fe2) ** p2)) ** (1 / p2)
        return 1.0

    def d_of_f(self, f):
        return f * self.c.L

    def z_of_f(self, f):
        return self.c.zF - f * self.c.L

    def flare(self, z):
        k = 0.0
        for zc in self.zc:
            dz = abs(z - zc)
            k = max(k, clamp(1 - dz / (self.Ra + 0.22)))
        return self.st["flare"] * (k ** 0.8)

    def ring_half(self, f):
        """Right-half ring points [(x, y)] * 14 at fraction f of the length (0 front, 1 rear)."""
        c, st = self.c, self.st
        z = self.z_of_f(f)
        yb = self.yb(f)
        T = self.T(f)
        w = c.bw * self.plan(f) * (1 + self.flare(z))
        # arch notch
        ya, inarch = yb + 0.03, False
        for zc in self.zc:
            dz = z - zc
            if abs(dz) < self.Ra:
                ya = max(ya, c.r + math.sqrt(self.Ra ** 2 - dz * dz))
                inarch = True
        ysh = min(self.belt(f), T - 0.07)
        ysh = max(ysh, ya + 0.13, yb + 0.35)
        ysh = min(ysh, T - 0.05)
        h = max(T - ysh, 0.02)
        wgt = clamp(h / 0.5)
        wcb = w * (0.985 - 0.04 * wgt)
        wcr = w * (0.955 - (0.955 - self.roof_frac) * wgt)
        crown = st["hood_crown"] + (st["roof_crown"] - st["hood_crown"]) * wgt
        xi = min(self.xi, 0.8 * w)
        if inarch:
            p1, p2, p3 = (xi, yb), (xi, ya), (w * 0.995, ya)
            y4 = ya + 0.22 * (ysh - ya)
        else:
            p1, p2, p3 = (0.9 * w, yb), (0.9 * w, yb), (w * 0.965, yb + 0.035)
            y4 = yb + 0.035 + 0.28 * (ysh - yb)
        pts = [(0.40 * w, yb), p1, p2, p3,
               (w, y4),
               (w * 0.992, ysh - 0.08),
               (wcb, ysh)]
        sh = st.get("float_roof", 0.0)
        for fr in (0.28, 0.62, 0.90):
            x = wcb + (wcr + 0.03 - wcb) * fr - sh * wgt
            y = min(ysh + h * fr, T - crown - 0.03)
            pts.append((x, y))
        pts.append((wcr, T - crown))                       # 10 roof edge
        pts.append((0.7 * wcr, T - crown * 0.49))          # 11
        pts.append((0.35 * wcr, T - crown * 0.12))         # 12
        pts.append((0.0, T))                               # 13
        return pts

    def stations(self):
        c, st = self.c, self.st
        L = c.L
        ds = set()
        d = 0.0
        while d < L:
            end = min(d, L - d)
            ds.add(round(d, 4))
            d += 0.03 if end < 0.4 else 0.085
        ds.add(round(L, 4))
        for zc in self.zc:
            dc = c.zF - zc
            n = int((2 * self.Ra) / 0.045) + 2
            for i in range(n + 1):
                ds.add(round(dc - self.Ra - 0.02 + i * (2 * self.Ra + 0.04) / n, 4))
        for key in ("wind", "rear_glass", "bonnet"):
            for f in st[key]:
                ds.add(round(f * L, 4))
        for (a, b) in st["side_glass"]:
            ds.add(round(a * L, 4)); ds.add(round(b * L, 4))
        for f in st["seams"]:
            ds.add(round(f * L, 4))
        out = sorted(x for x in ds if 0 <= x <= L)
        pruned = [out[0]]
        for x in out[1:]:
            if x - pruned[-1] > 0.012 or x == L:
                if x == L and x - pruned[-1] <= 0.012:
                    pruned[-1] = x
                else:
                    pruned.append(x)
        return [x / L for x in pruned]

    def full_ring(self, f):
        half = self.ring_half(f)
        z = self.z_of_f(f)
        right = [Vector((x, y, z)) for x, y in half]
        left = [Vector((-x, y, z)) for x, y in reversed(half[:-1])]
        return right + left          # 14 + 13 = 27


class Grid:
    """Welded quad-grid builder for one node (positions welded on creation)."""

    def __init__(self, mb: MB):
        self.mb = mb
        self.v = {}

    def vert(self, p):
        key = (round(p[0] * 1e4), round(p[1] * 1e4), round(p[2] * 1e4))
        v = self.v.get(key)
        if v is None:
            v = self.mb.bm.verts.new(Vector(p))
            self.v[key] = v
        return v

    def quad(self, pts, m, flip=False):
        vs = []
        for p in pts:
            v = self.vert(p)
            if v not in vs:
                vs.append(v)
        if len(vs) < 3:
            return None
        if flip:
            vs.reverse()
        try:
            f = self.mb.bm.faces.new(vs)
        except ValueError:
            return None
        f.material_index = self.mb._mi(m)
        return f


def build_cage(c, st, nodes):
    """Build the outer shell, inner shell, windows, bonnet skin, panel lines and underside strip.

    `nodes` is a dict of MB objects keyed by node name (body, glass, interior, underside, trim, bonnet).
    Returns a dict of useful geometry (stations, rings) for the detail builders.
    """
    cage = Cage(c, st)
    fs = cage.stations()
    rings = [cage.full_ring(f) for f in fs]
    ns = len(fs)
    L = c.L

    def idx_f(f):
        return min(range(ns), key=lambda i: abs(fs[i] - f))

    # ---- hole masks (station i between i and i+1, segment k between k and k+1)
    holes = set()
    side_rng = [(idx_f(a), idx_f(b)) for a, b in st["side_glass"]]
    for (a, b) in side_rng:
        for i in range(a, b):
            for k in (7, 8):
                holes.add((i, k))                   # right
                holes.add((i, 25 - k))              # left mirror
    for key in ("wind", "rear_glass"):
        a, b = idx_f(st[key][0]), idx_f(st[key][1])
        for i in range(min(a, b), max(a, b)):
            for k in range(9, 13):
                holes.add((i, k))
            for k in range(13, 17):
                holes.add((i, k))
    # the segment across the very top (12->13 right, 13->12' left) are both in range above
    # bonnet panel quads
    ba, bb = idx_f(st["bonnet"][0]), idx_f(st["bonnet"][1])
    bonnet_q = set()
    for i in range(min(ba, bb), max(ba, bb)):
        for k in (10, 11, 12, 13, 14, 15):
            bonnet_q.add((i, k))

    body = Grid(nodes["body"])
    trimg = Grid(nodes["trim"])
    under = Grid(nodes["underside"])
    glass = Grid(nodes["glass"])
    inter = Grid(nodes["interior"])
    bon = Grid(nodes["bonnet"])
    pillar_mat = st.get("pillar_mat", "paint")
    pill = Grid(nodes[st.get("pillar_node", "body")])

    def seg_pts(i, k):
        a = rings[i][k]
        b = rings[i][(k + 1) % NR]
        a2 = rings[i + 1][k]
        b2 = rings[i + 1][(k + 1) % NR]
        return a, b, b2, a2

    def jr(k):
        """right-half row index of segment k (0..12 on right, mirrored on left)"""
        if k <= 12:
            return k
        return 25 - k                # left half: segment k connects L(26-k) -> L(25-k)

    orient_flip = None
    for i in range(ns - 1):
        for k in range(NR):
            a, b, b2, a2 = seg_pts(i, k)
            j = jr(k)
            if k == NR - 1:           # closing segment: left 0' -> right 0 along the floor
                under.quad([a, b, b2, a2], "underbody")
                continue
            if (i, k) in holes:
                continue
            if (i, k) in bonnet_q:
                # lowered bay under the bonnet
                lo = Vector((0, -0.04, 0))
                body.quad([a + lo, b + lo, b2 + lo, a2 + lo], "paint")
                bon.quad([a, b, b2, a2], "paint")
                continue
            if j in (1, 2):
                under.quad([a, b, b2, a2], "underbody")
            elif j == 0:
                under.quad([a, b, b2, a2], "underbody")
            elif st.get("pillar_node") and j in (7, 8, 9) and k != 13:
                pill.quad([a, b, b2, a2], pillar_mat)
            else:
                body.quad([a, b, b2, a2], "paint")

    # orientation: make normals point outward. Test the roof-centre quad of a mid station.
    mid = ns // 2
    p0, p1, p2 = rings[mid][12], rings[mid][13], rings[mid + 1][13]
    n = (p1 - p0).cross(p2 - p1)
    flip = n.y < 0
    for g in (body, trimg, under, pill, bon):
        for f in g.mb.bm.faces:
            if flip:
                f.normal_flip()
    # (under faces: floor must face down, wells face inward: recalculated below)

    # ---- inner shell (headliner / door cards): rows 4..13..mirror, same holes
    def inner_pt(p, i):
        ymid = (cage.yb(fs[i]) + cage.T(fs[i])) / 2
        ctr = Vector((0, ymid, p.z))
        d = ctr - p
        l = d.length
        return p + d * (0.05 / l) if l > 0.06 else p
    irings = [[inner_pt(p, i) for p in rings[i]] for i in range(ns)]
    for i in range(ns - 1):
        for k in range(NR - 1):
            j = jr(k)
            if j < 4 or (i, k) in holes or (i, k) in bonnet_q:
                continue
            a, b = irings[i][k], irings[i][k + 1]
            a2, b2 = irings[i + 1][k], irings[i + 1][k + 1]
            m = "doorcard" if j < 7 else "headliner"
            f = inter.quad([a, b, b2, a2], m, flip=not flip)
    # ---- window reveals and glass
    hole_list = sorted(holes)
    hs = set(holes)
    for (i, k) in hole_list:
        a, b, b2, a2 = seg_pts(i, k)
        ia, ib, ib2, ia2 = irings[i][k], irings[i][k + 1], irings[i + 1][k + 1], irings[i + 1][k]
        # glass sheet at mid thickness
        ga, gb, gb2, ga2 = (a + ia) / 2, (b + ib) / 2, (b2 + ib2) / 2, (a2 + ia2) / 2
        glass.quad([ga, gb, gb2, ga2], "glass", flip=flip)
        # reveals on boundary edges
        for (di, dk, e0, e1, ie0, ie1) in (
                (1, 0, b2, a2, ib2, ia2),   # towards next station: edge between a2,b2 at station i+1
                (-1, 0, a, b, ia, ib),
                (0, 1, b, b2, ib, ib2),
                (0, -1, a2, a, ia2, ia)):
            ni, nk = i + di, (k + dk) % NR
            if (ni, nk) in hs:
                continue
            q = trimg.quad([e0, e1, ie1, ie0], "doorcard")
            if q is not None:
                q.normal_update()
                ctrh = (a + b + a2 + b2) / 4
                if q.normal.dot(ctrh - (e0 + e1) / 2) < 0:
                    q.normal_flip()
    # ---- bonnet shell: inner skin and flange
    for (i, k) in sorted(bonnet_q):
        a, b, b2, a2 = seg_pts(i, k)
        dn = Vector((0, -0.035, 0))
        q = bon.quad([a + dn, b + dn, b2 + dn, a2 + dn], "underbody")
        if q is not None:
            q.normal_update()
            if q.normal.y > 0:
                q.normal_flip()
        for (di, dk, e0, e1) in ((1, 0, b2, a2), (-1, 0, a, b), (0, 1, b, b2), (0, -1, a2, a)):
            ni, nk = i + di, (k + dk) % NR
            if (ni, nk) in bonnet_q:
                continue
            f = bon.quad([e0, e1, e1 + dn, e0 + dn], "paint")
            if f is not None:
                f.normal_update()
                mid_ = (a + b + a2 + b2) / 4
                if f.normal.dot((e0 + e1) / 2 - mid_) < 0:
                    f.normal_flip()
    # under faces: orient outward/downward by local test (floor down, others toward the wheel axis)
    for f in under.mb.bm.faces:
        f.normal_update()
    return dict(cage=cage, fs=fs, rings=rings, irings=irings, flip=flip, holes=holes, idx_f=idx_f)


def seam_strip(mb_trim: MB, rings, i, j0, j1, width=0.012, off=0.003, mirror=True):
    """Thin dark panel-line strip across ring i from right-half row j0 to j1 (and mirrored)."""
    g = Grid(mb_trim)
    for sgn in ((1, -1) if mirror else (1,)):
        for k in range(j0, j1):
            a, b = rings[i][k].copy(), rings[i][k + 1].copy()
            if sgn < 0:
                a = rings[i][NR - 1 - k].copy(); b = rings[i][NR - 1 - (k + 1)].copy()
            out = Vector((sgn, 0, 0)) * off
            dz = Vector((0, 0, width / 2))
            f = g.quad([a + out + dz, b + out + dz, b + out - dz, a + out - dz], "trim")
            if f is not None:
                f.normal_update()
                if f.normal.x * sgn < 0:
                    f.normal_flip()
