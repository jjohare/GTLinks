"""carkit: surface-construction kit for the GTLinks cars (car-only helper beside cars.py).

Everything is authored in the GAME frame (x = car's left, y = up, z = forward), like gtl.MB.

The kit builds a car skin from quad grids (`Surf`).  Each grid cell carries a tag; a tag maps to a
`Panel` (node, material, shut-line gap, rim depth, offset).  `Shell.emit` turns the tagged grids of
the left half into welded meshes for both halves:

  * cells of one panel share vertices (welded by position, across grids and across the mirror plane);
  * where two panels meet, each is pulled back by its gap and gets an inward rim, which is what
    makes a door, bonnet or tailgate shut line (a real groove, not a painted line);
  * cells with no tag are openings (lamp buckets, wheel arches); neighbours get a rim around them;
  * a panel offset moves the whole panel along the surface normal (glass sits 12 mm inside its frame).
"""
import math
import bmesh
from mathutils import Vector
from gtl import MB


# ----------------------------------------------------------------- small maths
def lerp(a, b, t):
    return a + (b - a) * t


def clamp(x, lo=0.0, hi=1.0):
    return lo if x < lo else hi if x > hi else x


def smooth01(t):
    t = clamp(t)
    return t * t * (3 - 2 * t)


def V(x, y, z):
    return Vector((x, y, z))


class Curve:
    """Monotone cubic (Fritsch-Carlson) through (x, y) control points; clamps outside the range."""

    def __init__(self, pts):
        pts = sorted(pts)
        self.x = [p[0] for p in pts]
        self.y = [p[1] for p in pts]
        n = len(pts)
        d = [(self.y[i + 1] - self.y[i]) / (self.x[i + 1] - self.x[i]) for i in range(n - 1)]
        m = [0.0] * n
        if n > 1:
            m[0], m[-1] = d[0], d[-1]
        for i in range(1, n - 1):
            m[i] = 0.0 if d[i - 1] * d[i] <= 0 else (d[i - 1] + d[i]) / 2
        for i in range(n - 1):
            if abs(d[i]) < 1e-12:
                m[i] = m[i + 1] = 0.0
            else:
                a, b = m[i] / d[i], m[i + 1] / d[i]
                s = a * a + b * b
                if s > 9:
                    t = 3 / math.sqrt(s)
                    m[i], m[i + 1] = t * a * d[i], t * b * d[i]
        self.m = m

    def __call__(self, x):
        xs, ys, m = self.x, self.y, self.m
        if x <= xs[0]:
            return ys[0]
        if x >= xs[-1]:
            return ys[-1]
        i = 0
        while x > xs[i + 1]:
            i += 1
        h = xs[i + 1] - xs[i]
        t = (x - xs[i]) / h
        t2, t3 = t * t, t * t * t
        return ((2 * t3 - 3 * t2 + 1) * ys[i] + (t3 - 2 * t2 + t) * h * m[i] +
                (-2 * t3 + 3 * t2) * ys[i + 1] + (t3 - t2) * h * m[i + 1])


def subdiv(breaks, maxstep):
    """Values through every break (monotone list), with steps no longer than maxstep."""
    out = [breaks[0]]
    for a, b in zip(breaks[:-1], breaks[1:]):
        n = max(1, int(math.ceil(abs(b - a) / maxstep - 1e-6)))
        for k in range(1, n + 1):
            out.append(a + (b - a) * k / n)
    return out


def corner_pts(n, ax, az, p=2.0):
    """Quarter superellipse as (dx, dz) offsets, k = 0..n: starts tangent to the 'across' direction,
    ends tangent to the 'along' direction.  p = 2 is an ellipse, larger is squarer."""
    e = 2.0 / p
    out = []
    for k in range(n + 1):
        th = (math.pi / 2) * k / n
        out.append((ax * math.sin(th) ** e, az * (1 - max(0.0, math.cos(th)) ** e)))
    return out


def plan_normals(pts):
    """Outward plan normals (nx, nz) for a path of (x, z) running front centre -> left flank -> rear centre."""
    n = len(pts)
    out = []
    for i in range(n):
        a = pts[max(0, i - 1)]
        b = pts[min(n - 1, i + 1)]
        tx, tz = b[0] - a[0], b[1] - a[1]
        if i == 0 or i == n - 1:
            tz = 0.0  # symmetric about the centreline
        l = math.hypot(tx, tz) or 1.0
        out.append((-tz / l, tx / l))
    return out


# ----------------------------------------------------------------- panels and grids
class Panel:
    def __init__(self, node, mat, gap=0.0, rim=0.0, off=0.0, rim_node=None, rim_mat=None, group=None,
                 hole_rim=None, frame=0.0):
        """gap: half shut-line width (applies where both neighbours have a gap); rim: inward rim depth at a
        shut line; hole_rim: rim depth around an opening; frame: rim depth this panel demands of its
        neighbours (glass and recessed panels sit inside a frame); off: offset along the normal."""
        self.node, self.mat, self.gap, self.rim, self.off = node, mat, gap, rim, off
        self.frame = frame
        self.rim_node = rim_node or node
        self.rim_mat = rim_mat or mat
        self.group = group
        self.hole_rim = rim if hole_rim is None else hole_rim   # rim depth where the neighbour is an opening


class Surf:
    """Quad grid P[i][j] with per-cell tags.  Cell (i, j) spans points (i..i+1, j..j+1)."""

    def __init__(self, P, hint=None, flip=None):
        self.P = P
        self.ni, self.nj = len(P), len(P[0])
        self.tag = [[None] * (self.nj - 1) for _ in range(self.ni - 1)]
        self.sharp_rows, self.sharp_cols = set(), set()
        self.border = {}          # 'j0' | 'j1' | 'i0' | 'i1' -> (rim depth, lo, hi) cell range on that grid border
        self.flip = False
        self.N = self._normals()
        if flip is not None:
            self.flip = flip
        elif hint is not None:
            s = sum(n.dot(hint) for row in self.N for n in row)
            self.flip = s < 0
        if self.flip:
            for row in self.N:
                for n in row:
                    n.negate()

    def _normals(self):
        P, ni, nj = self.P, self.ni, self.nj
        N = []
        for i in range(ni):
            row = []
            for j in range(nj):
                du = P[min(ni - 1, i + 1)][j] - P[max(0, i - 1)][j]
                dv = P[i][min(nj - 1, j + 1)] - P[i][max(0, j - 1)]
                n = du.cross(dv)
                if n.length < 1e-10:
                    n = Vector((0, 0, 0))
                else:
                    n.normalize()
                if abs(P[i][j].x) < 1e-7:
                    n.x = 0.0
                    if n.length > 1e-10:
                        n.normalize()
                row.append(n)
            N.append(row)
        # fill degenerate normals from neighbours
        for i in range(ni):
            for j in range(nj):
                if N[i][j].length < 0.5:
                    for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, -1)):
                        a, b = i + di, j + dj
                        if 0 <= a < ni and 0 <= b < nj and N[a][b].length > 0.5:
                            N[i][j] = N[a][b].copy()
                            break
        return N

    def set(self, tag, i0, i1, j0, j1, only=None):
        """Tag cells i0 <= i < i1, j0 <= j < j1 (clipped).  only = tag to replace, else replace anything."""
        for i in range(max(0, i0), min(self.ni - 1, i1)):
            for j in range(max(0, j0), min(self.nj - 1, j1)):
                if only is None or self.tag[i][j] == only:
                    self.tag[i][j] = tag

    def fill(self, tag):
        self.set(tag, 0, self.ni, 0, self.nj)


class CMB(MB):
    """gtl.MB plus explicit sharp edges that survive the angle-based smoothing in to_object."""

    def __init__(self):
        super().__init__()
        self.sharp = set()
        self.keys = {}

    def smooth(self, angle=50.0):
        super().smooth(angle)
        for e in self.bm.edges:
            a, b = e.verts[0], e.verts[1]
            if (a, b) in self.sharp or (b, a) in self.sharp:
                e.smooth = False

    def vert(self, group, p):
        k = (group, round(p.x, 5), round(p.y, 5), round(p.z, 5))
        v = self.keys.get(k)
        if v is None:
            v = self.bm.verts.new(p)
            self.keys[k] = v
        return v

    def quad(self, vs, m):
        u = []
        for v in vs:
            if v not in u:
                u.append(v)
        if len(u) < 3:
            return None
        try:
            f = self.bm.faces.new(u)
        except ValueError:
            return None
        f.material_index = self._mi(m)
        return f


class Shell:
    """Collects the meshes of every node of one car."""

    def __init__(self, panels):
        self.panels = panels
        self.nodes = {}

    def mb(self, node):
        if node not in self.nodes:
            self.nodes[node] = CMB()
        return self.nodes[node]

    def emit(self, surf, mirror=True, tagfn=None):
        sides = (1, -1) if mirror else (1,)
        for sx in sides:
            self._emit_side(surf, sx, tagfn)

    def _emit_side(self, surf, sx, tagfn):
        P, N, ni, nj = surf.P, surf.N, surf.ni, surf.nj
        panels = self.panels

        def tag_at(i, j):
            if 0 <= i < ni - 1 and 0 <= j < nj - 1:
                t = surf.tag[i][j]
                if t is not None and tagfn is not None:
                    t = tagfn(t, sx)
                return t
            return '__out__'

        tags = [[tag_at(i, j) for j in range(nj - 1)] for i in range(ni - 1)]
        # per panel: shrink flags and seam edges
        shift = {}   # (tag, i, j) -> [si, sj]
        seams = []   # (tag, (i,j) a, (i,j) b, depth, border?)
        for i in range(ni - 1):
            for j in range(nj - 1):
                t = tags[i][j]
                if t is None:
                    continue
                pa = panels[t]
                c = [(i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1)]
                # edge k runs c[k] -> c[k+1]; neighbours in the same order
                nb = [(i, j - 1, 'j0'), (i + 1, j, 'i1'), (i, j + 1, 'j1'), (i - 1, j, 'i0')]
                for k, (a, b, side) in enumerate(nb):
                    if 0 <= a < ni - 1 and 0 <= b < nj - 1:
                        o = tags[a][b]
                        if o == t:
                            continue
                        po = panels[o] if o is not None else None
                        depth = 0.0
                        if po is None:
                            depth = pa.hole_rim
                        elif po.frame > 0:
                            depth = po.frame if pa.frame == 0 else 0.0
                        elif pa.gap > 0 and po.gap > 0:
                            depth = pa.rim
                            for v in (c[k], c[(k + 1) % 4]):
                                s = shift.setdefault((t, v[0], v[1]), [0, 0])
                                if side == 'i0':
                                    s[0] = 1
                                elif side == 'i1':
                                    s[0] = -1
                                elif side == 'j0':
                                    s[1] = 1
                                else:
                                    s[1] = -1
                        if depth > 0:
                            seams.append((t, c[k], c[(k + 1) % 4], depth, False))
                    else:
                        spec = surf.border.get(side)
                        if spec:
                            depth, lo, hi = spec
                            along = i if side in ('j0', 'j1') else j
                            if depth > 0 and lo <= along < hi:
                                seams.append((t, c[k], c[(k + 1) % 4], depth, True))

        def pos(t, i, j, inward=0.0):
            pa = panels[t]
            p = P[i][j] + N[i][j] * (pa.off - inward)
            s = shift.get((t, i, j))
            if s:
                g = pa.gap
                if s[0]:
                    d = P[min(ni - 1, i + 1)][j] - P[max(0, i - 1)][j]
                    if d.length > 1e-9:
                        p = p + d.normalized() * (g * s[0])
                if s[1]:
                    d = P[i][min(nj - 1, j + 1)] - P[i][max(0, j - 1)]
                    if d.length > 1e-9:
                        p = p + d.normalized() * (g * s[1])
            if abs(P[i][j].x) < 1e-7:
                p.x = 0.0
            if sx < 0:
                p = Vector((-p.x, p.y, p.z))
            return p

        rev = (sx < 0) != surf.flip
        for i in range(ni - 1):
            for j in range(nj - 1):
                t = tags[i][j]
                if t is None:
                    continue
                pa = panels[t]
                mb = self.mb(pa.node)
                grp = pa.group or t
                vs = [mb.vert(grp, pos(t, a, b)) for a, b in ((i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1))]
                if rev:
                    vs.reverse()
                mb.quad(vs, pa.mat)
                if (j in surf.sharp_rows) and vs[0] is not vs[1]:
                    a, b = mb.vert(grp, pos(t, i, j)), mb.vert(grp, pos(t, i + 1, j))
                    mb.sharp.add((a, b))
                if (j + 1 in surf.sharp_rows):
                    a, b = mb.vert(grp, pos(t, i, j + 1)), mb.vert(grp, pos(t, i + 1, j + 1))
                    mb.sharp.add((a, b))
                if (i in surf.sharp_cols):
                    a, b = mb.vert(grp, pos(t, i, j)), mb.vert(grp, pos(t, i, j + 1))
                    mb.sharp.add((a, b))
                if (i + 1 in surf.sharp_cols):
                    a, b = mb.vert(grp, pos(t, i + 1, j)), mb.vert(grp, pos(t, i + 1, j + 1))
                    mb.sharp.add((a, b))
        for t, a, b, depth, is_border in seams:
            pa = panels[t]
            node = pa.node if is_border else pa.rim_node
            m = pa.mat if is_border else pa.rim_mat
            mb = self.mb(node)
            grp = (pa.group or t) if node == pa.node else ('rim', t)
            va, vb = mb.vert(grp, pos(t, a[0], a[1])), mb.vert(grp, pos(t, b[0], b[1]))
            ra, rb = mb.vert(grp, pos(t, a[0], a[1], depth)), mb.vert(grp, pos(t, b[0], b[1], depth))
            vs = [vb, va, ra, rb]
            if rev:
                vs.reverse()
            mb.quad(vs, m)
            mb.sharp.add((va, vb))


# ----------------------------------------------------------------- patches
def coons(L, R, B, T, crown=True):
    """Coons patch.  L, R: point lists running v = 0..1; B, T: lists running u = 0..1 (L side to R side).
    Corners must agree.  With crown, heights blend with u^2 so the section has zero slope at L
    (L is the centreline, so the mirrored halves meet without a ridge).  Returns P[iu][iv]."""
    nu, nv = len(B) - 1, len(L) - 1
    P = []
    for iu in range(nu + 1):
        u = iu / nu
        uu = u * u if crown else u
        col = []
        for iv in range(nv + 1):
            v = iv / nv
            p = (L[iv] * (1 - u) + R[iv] * u + B[iu] * (1 - v) + T[iu] * v
                 - (L[0] * (1 - u) * (1 - v) + R[0] * u * (1 - v) + L[nv] * (1 - u) * v + R[nv] * u * v))
            y = ((1 - uu) * L[iv].y + uu * R[iv].y
                 + (1 - v) * (B[iu].y - ((1 - uu) * B[0].y + uu * B[nu].y))
                 + v * (T[iu].y - ((1 - uu) * T[0].y + uu * T[nu].y)))
            col.append(Vector((p.x, y, p.z)))
        P.append(col)
    return P


def bar_along(mb, pts, nrm, up, w, d0, d1, m, closed=False):
    """Box-section bar following a polyline.  nrm[i] = outward surface normal, up[i] = in-surface direction
    across the bar.  The bar spans +-w/2 along up and from d0 to d1 along the normal."""
    rings = []
    for p, n, u in zip(pts, nrm, up):
        rings.append([p + u * (w / 2) + n * d1, p - u * (w / 2) + n * d1, p - u * (w / 2) + n * d0, p + u * (w / 2) + n * d0])
    return mb.loft(rings, m)


def superdome(mb, c, a, b, p, depth, m, axis=(0, 0, 1), segs=24, rings=((1.0, 0.0), (0.93, 0.45), (0.72, 0.8), (0.4, 0.96))):
    """Convex lens: superellipse outline (half-axes a along x, b along y) bulging 'depth' along +axis (z)."""
    c = Vector(c)
    e = 2.0 / p
    vr = []
    for s, h in rings:
        ring = []
        for k in range(segs):
            th = 2 * math.pi * k / segs
            cx, sy = math.cos(th), math.sin(th)
            x = a * s * math.copysign(abs(cx) ** e, cx)
            y = b * s * math.copysign(abs(sy) ** e, sy)
            ring.append(mb.bm.verts.new(c + Vector((x, y, depth * h * axis[2]))))
        vr.append(ring)
    top = mb.bm.verts.new(c + Vector((0, 0, depth * axis[2])))
    faces = []
    for r0, r1 in zip(vr[:-1], vr[1:]):
        for k in range(segs):
            k2 = (k + 1) % segs
            f = mb._face([r0[k], r0[k2], r1[k2], r1[k]], m)
            if f:
                faces.append(f)
    for k in range(segs):
        f = mb._face([vr[-1][k], vr[-1][(k + 1) % segs], top], m)
        if f:
            faces.append(f)
    ax = Vector((0, 0, axis[2]))
    for f in faces:
        f.normal_update()
        if f.normal.dot(ax) < -1e-6 or (abs(f.normal.dot(ax)) <= 1e-6 and f.normal.dot(f.calc_center_median() - c) < 0):
            f.normal_flip()
    return faces


def rbox(mb, c, s, m, r=0.02, rot=None):
    """Bevelled box (wrapper keeping call sites short)."""
    return mb.box(c, s, m, bevel=r, rot=rot)


def emit_liner(shell, surf, pred, depth, node, mat, mirror=True, step=(1, 1), outward=False):
    """Inner skin: the cells whose tag passes pred, pushed 'depth' inside and facing inward.
    step = (si, sj) merges blocks of cells (a block is emitted only when every cell in it passes)."""
    mb = shell.mb(node)
    P, N, ni, nj = surf.P, surf.N, surf.ni, surf.nj
    si, sj = step
    ii = list(range(0, ni - 1, si)) + [ni - 1]
    jj = list(range(0, nj - 1, sj)) + [nj - 1]
    for sx in ((1, -1) if mirror else (1,)):
        rev = (sx < 0) != surf.flip
        for a0, a1 in zip(ii[:-1], ii[1:]):
            for b0, b1 in zip(jj[:-1], jj[1:]):
                if not all(pred(surf.tag[i][j]) for i in range(a0, a1) for j in range(b0, b1)):
                    continue
                vs = []
                for a, b in ((a0, b0), (a1, b0), (a1, b1), (a0, b1)):
                    p = P[a][b] - N[a][b] * depth
                    if abs(P[a][b].x) < 1e-7:
                        p.x = 0.0
                    if sx < 0:
                        p = Vector((-p.x, p.y, p.z))
                    vs.append(mb.vert(('liner', node), p))
                if rev == outward:
                    vs.reverse()
                mb.quad(vs, mat)


def super_ring(mb, c, a, b, p, w, m, segs=24, depth=0.0):
    """Flat superellipse annulus facing +z (a lamp bezel): outer half-axes a, b, band width w."""
    c = Vector(c)
    e = 2.0 / p
    faces = []
    outer, inner = [], []
    for k in range(segs):
        th = 2 * math.pi * k / segs
        cx, sy = math.cos(th), math.sin(th)
        ux, uy = math.copysign(abs(cx) ** e, cx), math.copysign(abs(sy) ** e, sy)
        outer.append(mb.bm.verts.new(c + Vector((a * ux, b * uy, 0))))
        inner.append(mb.bm.verts.new(c + Vector(((a - w) * ux, (b - w) * uy, -depth))))
    for k in range(segs):
        k2 = (k + 1) % segs
        f = mb._face([outer[k], outer[k2], inner[k2], inner[k]], m)
        if f:
            f.normal_update()
            if f.normal.z < 0:
                f.normal_flip()
            faces.append(f)
    return faces
