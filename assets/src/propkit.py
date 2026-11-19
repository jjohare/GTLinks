"""Shared geometry helpers for props.py / props3.py (game frame: +X left, +Y up, +Z forward).

Everything here builds into an `MB` (see gtl.py) and only uses its public primitives plus the
bmesh handle, so the Blender-frame conversion still happens once, in `MB.to_object`.
"""
import math, random
import bmesh
from mathutils import Vector, Matrix


def basis(xa, za):
    """Right-handed rotation whose columns are x = xa, z ~ za (orthogonalised), y = z cross x."""
    x = Vector(xa).normalized()
    z = Vector(za)
    z = (z - x * z.dot(x)).normalized()
    y = z.cross(x)
    return Matrix(((x.x, y.x, z.x), (x.y, y.y, z.y), (x.z, y.z, z.z)))


def limb(m, p0, p1, r0, r1, segs, mat, scale=(1, 1), phase=0.0):
    """Tapered solid segment from p0 (radius r0) to p1 (radius r1)."""
    p0, p1 = Vector(p0), Vector(p1)
    L = (p1 - p0).length
    if L < 1e-5:
        return []
    return m.lathe((p0 + p1) / 2, p1 - p0, [(r0, -L / 2), (r1, L / 2)], segs, mat, scale=scale, phase=phase)


def tube(m, pts, radii, segs, mat, scale=(1.0, 1.0), caps=True, up=(0, 1, 0), phase=0.0):
    """Swept elliptical tube along a polyline. scale = (u, v) stretch of the section in its frame."""
    pts = [Vector(p) for p in pts]
    n = len(pts)
    rings = []
    for i, p in enumerate(pts):
        a, b = pts[max(i - 1, 0)], pts[min(i + 1, n - 1)]
        t = (b - a).normalized()
        ref = Vector(up)
        if abs(t.dot(ref)) > 0.95:
            ref = Vector((1, 0, 0))
        u = (ref - t * ref.dot(t)).normalized()
        v = t.cross(u)
        r = radii[i] if isinstance(radii, (list, tuple)) else radii
        rings.append([p + u * (r * scale[0] * math.cos(phase + 2 * math.pi * k / segs)) +
                      v * (r * scale[1] * math.sin(phase + 2 * math.pi * k / segs)) for k in range(segs)])
    return m.loft(rings, mat, caps=caps)


def ring_pts(c, rx, rz, n, yaw=0.0, phase=0.0, k=None):
    """Horizontal ellipse of n points about centre c, yawed about +Y. k(i) optional radius multiplier."""
    c = Vector(c)
    cs, sn = math.cos(yaw), math.sin(yaw)
    out = []
    for i in range(n):
        a = phase + 2 * math.pi * i / n
        km = k(i) if k else 1.0
        x, z = rx * km * math.cos(a), rz * km * math.sin(a)
        out.append(c + Vector((x * cs + z * sn, 0.0, -x * sn + z * cs)))
    return out


def loft_mat(m, rings, matfn, caps=True, solid=True):
    """Loft whose material is chosen per quad: matfn(i_station, j_around) -> material name."""
    n = len(rings[0])
    vr = [m._verts(r) for r in rings]
    faces = []
    for i in range(len(vr) - 1):
        for j in range(n):
            k = (j + 1) % n
            f = m._face([vr[i][j], vr[i][k], vr[i + 1][k], vr[i + 1][j]], matfn(i, j))
            if f:
                faces.append(f)
    if caps:
        for r, idx in ((vr[0], 0), (vr[-1], len(vr) - 2)):
            f = m._face(list(r), matfn(idx, 0))
            if f:
                faces.append(f)
    if solid:
        m._fix(faces)
    return faces


def blob(m, c, radii, mat, subdiv=1, rot=None, jitter=0.0, seed=0, clip_y=None, squash_y=None):
    """Icosphere ellipsoid centred c with radii (rx, ry, rz) in a local frame rotated by `rot` (Matrix3).
    clip_y flattens local y below the value (sole of a shoe / club head)."""
    rnd = random.Random(seed)
    ret = bmesh.ops.create_icosphere(m.bm, subdivisions=subdiv, radius=1.0)
    c = Vector(c)
    for v in ret["verts"]:
        d = v.co.copy()
        k = 1.0 + (rnd.uniform(-jitter, jitter) if jitter else 0.0)
        p = Vector((d.x * radii[0] * k, d.y * radii[1] * k, d.z * radii[2] * k))
        if clip_y is not None and p.y < clip_y:
            p.y = clip_y
        if rot is not None:
            p = rot @ p
        v.co = c + p
    faces = set()
    for v in ret["verts"]:
        faces.update(v.link_faces)
    for f in faces:
        f.material_index = m._mi(mat)
    m._fix(list(faces))
    return list(faces)


def dome(m, c, prof, n, mat, jit=0.0, seed=0, sag=0.0, phase=0.0, scale=(1.0, 1.0)):
    """Closed lobed solid of revolution about +Y from profile [(rho, h)...]; first/last rho may be 0 (poles).
    jit = per-vertex radial noise, sag = per-lobe downward droop proportional to radius (feathery foliage)."""
    rnd = random.Random(seed)
    cx, cy, cz = c
    rings = []
    for k, (rho, h) in enumerate(prof):
        if rho < 1e-6:
            rings.append(m.bm.verts.new((cx, cy + h, cz)))
            continue
        row = []
        for i in range(n):
            a = phase + 2 * math.pi * i / n
            kk = 1.0 + rnd.uniform(-jit, jit)
            lobe = rnd.uniform(0.0, 1.0) if sag else 0.0
            r = rho * kk
            row.append(m.bm.verts.new((cx + r * scale[0] * math.cos(a), cy + h - sag * rho * lobe,
                                       cz + r * scale[1] * math.sin(a))))
        rings.append(row)
    faces = []
    for a, b in zip(rings[:-1], rings[1:]):
        if isinstance(a, list) and isinstance(b, list):
            for i in range(n):
                j = (i + 1) % n
                f = m._face([a[i], a[j], b[j], b[i]], mat)
                if f: faces.append(f)
        elif isinstance(a, list):
            for i in range(n):
                f = m._face([a[i], a[(i + 1) % n], b], mat)
                if f: faces.append(f)
        elif isinstance(b, list):
            for i in range(n):
                f = m._face([a, b[(i + 1) % n], b[i]], mat)
                if f: faces.append(f)
    for end in (rings[0], rings[-1]):
        if isinstance(end, list):
            f = m._face(list(end), mat)
            if f: faces.append(f)
    m._fix(faces)
    return faces


def ik2(shoulder, hand, l1, l2, pole):
    """Two-bone IK: returns the elbow/knee position. pole = direction the joint bends toward."""
    s, h = Vector(shoulder), Vector(hand)
    d = h - s
    L = d.length
    L = min(max(L, abs(l1 - l2) + 1e-4), l1 + l2 - 1e-4)
    dn = d.normalized()
    a = (l1 * l1 - l2 * l2 + L * L) / (2 * L)
    hh = math.sqrt(max(l1 * l1 - a * a, 0.0))
    pv = Vector(pole)
    pv = pv - dn * pv.dot(dn)
    if pv.length < 1e-6:
        pv = Vector((0, 0, 1)).cross(dn)
    return s + dn * a + pv.normalized() * hh


def club(m, grip, d, kind, face, length=1.1, mats=('shaft', 'head', 'grip'), show_grip=True, cover=None, detail=3):
    """A golf club. grip = grip-end point, d = direction grip->head (unit), face = direction the face looks.
    Origin of the model is the grip end; the head hangs `length` away along d.
    kind: driver | wood | hybrid | iron | wedge | putter"""
    sh, hd, gr = mats
    grip = Vector(grip)
    d = Vector(d).normalized()
    f = Vector(face)
    f = (f - d * f.dot(d)).normalized()
    t = f.cross(d)                       # toe direction (heel at the shaft)
    B = basis(t, f)                      # local x = toe, y = up the shaft, z = face
    up = -d
    tip = grip + d * length              # sole level at the heel
    hosel_h = {'driver': 0.045, 'wood': 0.04, 'hybrid': 0.04, 'iron': 0.05, 'wedge': 0.05, 'putter': 0.04}[kind]
    shaft_end = tip - d * hosel_h
    glen = 0.255 if kind != 'putter' else 0.24
    if show_grip:
        g0 = grip
        g1 = grip + d * glen
        if detail > 1:
            m.lathe((g0 + g1) / 2, d, [(0.0105, -glen / 2), (0.0128, -glen / 2 + 0.03), (0.0122, glen / 2 - 0.02),
                                        (0.0102, glen / 2)], 8, gr)
        else:
            limb(m, g0, g1, 0.0125, 0.0105, 6, gr)
        if detail > 1:
            limb(m, g1, g1 + d * 0.012, 0.0112, 0.0112, 8, sh)   # ferrule
        s0 = g1 + d * 0.012
    else:
        s0 = grip
    limb(m, s0, shaft_end, 0.0072, 0.0052, 6, sh)

    def P(x, y, z):
        return tip + B @ Vector((x, y, z))
    limb(m, shaft_end, P(0.0, 0.012, 0.0), 0.0075, 0.009, 6, hd)   # hosel
    if cover:
        # sock-style head cover: neck sleeve up the shaft, bulb over the head, pom-pom at the toe
        limb(m, shaft_end - d * 0.0, shaft_end + up * 0.13, 0.016, 0.011, 8, cover[0])
        limb(m, shaft_end, P(0.0, 0.0, 0.0), 0.019, 0.022, 8, cover[0])
        ctr = P(0.052, 0.040, 0.0)
        m.lathe(ctr, B @ Vector((1, 0, 0)), [(0.030, -0.070), (0.050, -0.040), (0.060, 0.0), (0.056, 0.040), (0.036, 0.066), (0.0, 0.074)],
                10, cover[0])
        m.lathe(ctr + B @ Vector((-0.060, 0, 0)), B @ Vector((1, 0, 0)), [(0.034, 0.0), (0.034, 0.012)], 10, cover[1])
        blob(m, ctr + B @ Vector((0.080, 0, 0)), (0.020, 0.020, 0.020), cover[1], subdiv=1)
    elif kind == 'driver':
        blob(m, P(0.052, 0.046, 0.0), (0.066, 0.046, 0.058), hd, subdiv=max(detail, 2), rot=B, clip_y=-0.040, seed=1)
    elif kind == 'wood':
        blob(m, P(0.050, 0.036, 0.0), (0.058, 0.036, 0.05), hd, subdiv=detail, rot=B, clip_y=-0.030, seed=2)
    elif kind == 'hybrid':
        blob(m, P(0.045, 0.030, 0.0), (0.052, 0.030, 0.040), hd, subdiv=max(detail - 1, 1), rot=B, clip_y=-0.024, seed=3)
        m.box(P(0.045, 0.012, 0.030), (0.085, 0.032, 0.012), hd, bevel=0.003, rot=B)
    elif kind in ('iron', 'wedge'):
        loft = math.radians(24 if kind == 'iron' else 52)
        R = B @ Matrix.Rotation(-loft, 3, 'X')
        m.box(P(0.052, 0.034, 0.004), (0.098, 0.062, 0.012), hd, bevel=0.003, rot=R)          # blade
        m.box(P(0.055, 0.016, -0.011), (0.085, 0.026, 0.020), hd, bevel=0.004, rot=B)         # cavity back / sole bar
        if detail >= 3:                                                                          # face grooves
            for k in range(5):
                gy = 0.016 + k * 0.0105
                m.box(P(0.054, gy * math.cos(loft) , 0.011 + gy * math.sin(loft)), (0.080, 0.0022, 0.0022), sh, rot=R)
    elif kind == 'putter':
        m.box(P(0.055, 0.032, 0.0), (0.115, 0.050, 0.046), hd, bevel=0.008, rot=B)
        m.box(P(0.015, 0.045, 0.0), (0.016, 0.050, 0.030), hd, bevel=0.003, rot=B)
        if detail >= 3:
            m.box(P(0.055, 0.034, 0.0235), (0.085, 0.006, 0.003), sh, rot=B)                     # alignment line
    return m
