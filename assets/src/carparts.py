"""Car sub-assemblies that hang off the swept body in cars.py: inner structure behind the detachable panels,
lamps, grille, exterior trim, mirrors, underside, interior, wheels and calipers.

Every function takes the car context `c` (dimensions from cars.json, the tagged grids c.tub / c.G / c.R)
and the Shell `sh` whose per-node mesh builders it adds to.  Game frame: x left, y up, z forward.
"""
import math
from mathutils import Vector, Matrix
import carkit as K
from carkit import V, lerp


def mirrored(pts):
    """Left-half polyline (running outboard -> centre) completed across the centreline."""
    out = list(pts)
    for p in reversed(pts[:-1] if abs(pts[-1].x) < 1e-6 else pts):
        out.append(Vector((-p.x, p.y, p.z)))
    return out


def row_line(c, surf, j, i0, i1, frac=0.0):
    """Points and normals along row j (+frac toward j+1) for columns i1..i0 (outboard to centre), mirrored."""
    pts, nrm = [], []
    for i in range(i1, i0 - 1, -1):
        p = surf.P[i][j].lerp(surf.P[i][j + 1], frac) if frac else surf.P[i][j].copy()
        n = surf.N[i][j].copy()
        pts.append(p)
        nrm.append(n)
    full_p = mirrored(pts)
    full_n = list(nrm)
    for n in reversed(nrm[:-1] if abs(pts[-1].x) < 1e-6 else nrm):
        full_n.append(Vector((-n.x, n.y, n.z)))
    return full_p, full_n


# ----------------------------------------------------------------------------- structure behind panels
def structure(c, sh):
    """What is left when a bumper or the bonnet comes off: inner panels, crash bars, radiator, firewall."""
    tub = c.tub
    isbf = lambda t: t is not None and t.startswith('bf')
    isbr = lambda t: t is not None and t.startswith('br')
    K.emit_liner(sh, tub, isbf, 0.10, 'underside', 'trim', outward=True, step=(2, 2))
    K.emit_liner(sh, tub, isbr, 0.05, 'body', 'paint', outward=True)
    un = sh.mb('underside')
    up = Vector((0, 1, 0))
    for (j, i_end, d0, d1) in ((3, c.i_side0 - 1, -0.09, -0.04),):
        pts, nrm = row_line(c, tub, j, 0, i_end)
        K.bar_along(un, pts, nrm, [up] * len(pts), 0.11, d0, d1, 'steel')
    pts, nrm = row_line(c, tub, 3, c.i_rc0 + 2, c.M)
    pts.reverse(); nrm.reverse()
    K.bar_along(un, pts, nrm, [up] * len(pts), 0.10, -0.045, -0.012, 'steel')
    # firewall between the engine bay and the cabin, and the bay floor
    zc = c.cowl[0].z
    yb = c.yfloor
    ytop = c.cowl[-1].y - 0.03
    un.box((0, (yb + ytop) / 2, zc - 0.10), (2 * (c.w - 0.10), ytop - yb, 0.03), 'underplate')


# ----------------------------------------------------------------------------- lamps
def lamps(c, sh):
    """Headlights: an emissive lens in its own node (the front end animates it as an eye) set back inside a
    recess cut into the fascia.  The lens follows the lean and sweep of the opening so it fills it; the dark
    bucket behind it stays with the body."""
    tub, S = c.tub, c.S
    i0, i1, j0, j1 = c.lamp_cells
    P = tub.P
    pts = [P[i][j] for i in range(i0, i1 + 1) for j in range(j0, j1 + 1)]
    x0, x1 = min(p.x for p in pts), max(p.x for p in pts)
    y0, y1 = min(p.y for p in pts), max(p.y for p in pts)
    zc = sum(p.z for p in pts) / len(pts)
    # plane through the opening: slope across (sweep) and up (lean), limited so the lens stays near flat
    sx_ = ((P[i1][j0].z + P[i1][j1].z) - (P[i0][j0].z + P[i0][j1].z)) / 2 / max(1e-6, x1 - x0)
    sy_ = ((P[i0][j1].z + P[i1][j1].z) - (P[i0][j0].z + P[i1][j0].z)) / 2 / max(1e-6, y1 - y0)
    sx_, sy_ = max(-0.35, min(0.0, sx_)), max(-0.35, min(0.0, sy_))
    a, b = (x1 - x0) / 2 + 0.004, (y1 - y0) / 2 + 0.004
    p_ = S['lamp']['p']
    rec = 0.028
    for name, sx in (('headlight_l', 1), ('headlight_r', -1)):
        ctr = Vector((sx * (x0 + x1) / 2, (y0 + y1) / 2, zc - rec - 0.03))
        mb = sh.mb(name)
        n0 = len(mb.bm.verts)
        K.superdome(mb, ctr, a, b, p_, 0.03, 'headlight')
        mb.bm.verts.ensure_lookup_table()
        for v in list(mb.bm.verts)[n0:]:
            v.co.z += sx_ * (v.co.x - ctr.x) * sx + sy_ * (v.co.y - ctr.y)
        c.origins[name] = tuple(ctr)
        zb = min(p.z for p in pts) - 0.10
        sh.mb('trim').box((ctr.x, ctr.y, zb), (2 * a + 0.10, 2 * b + 0.08, 0.03), 'trim')
    c.lamp_box = (x0, x1, y0, y1, zc)


# ----------------------------------------------------------------------------- grille
def grille(c, sh):
    tub, S = c.tub, c.S
    g = S['grille']
    i0, i1, j0, j1 = c.grille_cells
    mb = sh.mb('trim' if S.get('lite') else 'bumper_front')
    kind, m = g['kind'], g['mat']
    up = Vector((0, 1, 0))

    def hbar(j, frac, w, d1=-0.006, mat=m):
        pts, nrm = row_line(c, tub, j, 0, i1, frac)
        K.bar_along(mb, pts, nrm, [up] * len(pts), w, -0.045, d1, mat)

    def vbar(i, sx, w, d1=-0.01, mat=m):
        pts, nrm, ups = [], [], []
        for j in range(j0, j1 + 1):
            p, n = tub.P[i][j].copy(), tub.N[i][j].copy()
            t = (tub.P[min(i + 1, tub.ni - 1)][j] - tub.P[max(i - 1, 0)][j])
            if abs(p.x) < 1e-6:
                t = Vector((1, 0, 0))
            t.normalize()
            if sx < 0:
                p.x, n.x, t = -p.x, -n.x, Vector((t.x, -t.y, -t.z))
            pts.append(p); nrm.append(n); ups.append(t)
        K.bar_along(mb, pts, nrm, ups, w, -0.045, d1, mat)

    rows = [(j, f) for j in range(j0, j1) for f in (0.0, 0.5)][1:]
    if g.get('frame', kind in ('eggcrate', 'bars')):
        hbar(j0, 0.0, 0.035, d1=0.006)
        hbar(j1 - 1, 0.999, 0.035, d1=0.006)
        for sx in (1, -1):
            vbar(i1, sx, 0.035, d1=0.006)
    if kind == 'eggcrate':
        for j, f in rows:
            hbar(j, f, 0.022)
        vbar(0, 1, 0.03, d1=-0.004)
    elif kind == 'bars':
        for j, f in rows[1::2]:
            hbar(j, f, 0.045)
    elif kind == 'slats':
        for j, f in rows:
            hbar(j, f, 0.018, d1=-0.012)
    else:
        hbar(j0, 0.5 * (j1 - j0) if j1 - j0 < 2 else 0.999, 0.012, d1=-0.02)
    # number-plate blank (no text)
    pj = S.get('plate_row', 3)
    p = tub.P[0][pj].lerp(tub.P[0][pj + 1], 0.5)
    mb.box((0, p.y, p.z + 0.008), (0.50, 0.11, 0.014), 'plate', bevel=0.004)
    mb.box((0, p.y, p.z + 0.004), (0.53, 0.14, 0.012), 'trim', bevel=0.004)


# ----------------------------------------------------------------------------- exterior trim
def exterior_details(c, sh):
    tub, G, R, S = c.tub, c.G, c.R, c.S
    side_z = lambda i: c.pts[i][1]
    cols = range(c.i_side0, c.i_rc0 + 1)

    def col_at(z):
        return min(cols, key=lambda i: abs(side_z(i) - z))
    # door handles
    kind = S['handles']
    for z in (c.zn['Bm'] + 0.17, c.zn['C1'] + 0.17):
        i = col_at(z)
        p, n = tub.P[i][7].copy(), tub.N[i][7].copy()
        for sx in (1, -1):
            q = Vector((sx * p.x, p.y, p.z))
            nn = Vector((sx * n.x, n.y, n.z))
            if kind == 'flush':
                sh.mb('trim').box(q + nn * 0.001, (0.008, 0.03, 0.17), 'gloss', bevel=0.003)
            else:
                node, m = ('chrome', 'chrome') if kind == 'chrome' else ('body', 'paint')
                sh.mb('trim').box(q + nn * 0.001, (0.012, 0.062, 0.13), 'trim', bevel=0.004)
                sh.mb(node).box(q + nn * 0.016, (0.026, 0.03, 0.17), m, bevel=0.01)
    # wipers lying along the windscreen base
    gW = c.gh_cols['W']
    pts, nrm, ups = [], [], []
    for g in range(1, max(3, gW - 2)):
        p = G.P[g][1].lerp(G.P[g][2], 0.12)
        u = (G.P[g][2] - G.P[g][1]).normalized()
        pts.append(p); nrm.append(G.N[g][1]); ups.append(u)
    for sx in (1, -1):
        pp = [Vector((sx * p.x, p.y, p.z)) for p in pts]
        nn = [Vector((sx * n.x, n.y, n.z)) for n in nrm]
        uu = [Vector((sx * u.x, u.y, u.z)) for u in ups]
        K.bar_along(sh.mb('trim'), pp, nn, uu, 0.022, 0.006, 0.026, 'trim')
        sh.mb('trim').box(pp[0] + nn[0] * 0.012 - uu[0] * 0.03, (0.05, 0.03, 0.05), 'trim', bevel=0.01)
    # roof rails
    nu, nv = R.ni - 1, R.nj - 1
    iu = nu - 1
    v0, v1 = int(nv * 0.14), int(nv * 0.88)
    node, m = ('chrome', S['rails']) if S['rails'] in ('chrome', 'steel') else ('trim', S['rails'])
    lift = 0.012 if S['rails'] == 'gloss' else 0.034
    for sx in ((1, -1) if S['rails'] else ()):
        pts, nrm, ups = [], [], []
        for iv in range(v0, v1 + 1):
            p, n = R.P[iu][iv], R.N[iu][iv]
            pts.append(Vector((sx * p.x, p.y, p.z)))
            nrm.append(Vector((sx * n.x, n.y, n.z)))
            ups.append(Vector((1, 0, 0)))
        K.bar_along(sh.mb(node), pts, nrm, ups, 0.03, lift - 0.008, lift + 0.01, m)
        for k in (0, len(pts) // 2, len(pts) - 1):
            sh.mb(node).box(pts[k] + nrm[k] * (lift / 2), (0.03, lift + 0.012, 0.09), m, bevel=0.006)
    # aerial fin
    pf = R.P[0][int(nv * 0.9)]
    if not S.get('lite'):
        sh.mb('trim').box((0, pf.y + 0.03, pf.z), (0.035, 0.07, 0.16), 'gloss', bevel=0.014)
    # rear number-plate blank
    M = c.M
    p = tub.P[M][6].lerp(tub.P[M][7], 0.4)
    sh.mb('trim').box((0, p.y, p.z - 0.008), (0.50, 0.11, 0.014), 'plate', bevel=0.004)
    sh.mb('trim').box((0, p.y, p.z - 0.003), (0.56, 0.15, 0.012), 'trim', bevel=0.004)
    # exhaust tips
    tips = S['tips']
    yb = c.yfloor
    for k in range(tips):
        for sx in (1, -1):
            x = sx * (0.34 + 0.11 * k)
            sh.mb('chrome').lathe((x, yb - 0.04, c.zR + 0.16), (0, 0, -1),
                                  [(0.047, -0.08), (0.047, 0.08), (0.036, 0.08), (0.036, -0.08)], 12, 'chrome', closed=True)
    # running boards
    if S.get('boards'):
        za, zb = c.zcF - c.Ra - 0.06, c.zcR + c.Ra + 0.06
        for sx in (1, -1):
            sh.mb('chrome').box((sx * (c.w - 0.03), c.ysb - 0.005, (za + zb) / 2), (0.11, 0.04, za - zb), 'chrome', bevel=0.012)
            sh.mb('trim').box((sx * (c.w - 0.03), c.ysb + 0.017, (za + zb) / 2), (0.085, 0.006, za - zb - 0.06), 'trim')
    # rear spoiler lip over the rear screen
    if S.get('spoiler'):
        gD = c.gh_cols['Dr']
        pts, nrm = row_line(c, G, G.nj - 2, gD + 1, G.ni - 1)
        pts.reverse(); nrm.reverse()
        K.bar_along(sh.mb('trim'), pts, nrm, [Vector((0, 1, 0))] * len(pts), 0.03, 0.0, S['spoiler'], 'gloss')


# ----------------------------------------------------------------------------- mirrors
def mirrors(c, sh):
    """Door mirrors on a short arm at the base of the A pillar; origin at the mount so they can fold or detach."""
    tub = c.tub
    p = tub.P[c.ix['A']][11].copy()
    xlim = c.hw * 1.027
    x_in = p.x - 0.045
    wx = max(0.10, xlim - x_in)
    for name, sx in (('mirror_l', 1), ('mirror_r', -1)):
        mb = sh.mb('body' if c.S.get('lite') else name)
        o = Vector((sx * p.x, p.y, p.z))
        ctr = Vector((sx * (x_in + wx / 2), p.y + 0.085, p.z - 0.01))
        mb.box(o + Vector((0, 0.012, -0.01)), (0.07, 0.03, 0.09), 'trim', bevel=0.01)
        mb.box(ctr, (wx, 0.125, 0.085), 'paint', bevel=0.035)
        mb.box(ctr + Vector((0, -0.003, -0.043)), (wx - 0.035, 0.09, 0.008), 'chrome', bevel=0.003)
        if not c.S.get('lite'):
            c.origins[name] = tuple(o)


# ----------------------------------------------------------------------------- wheels
def build_wheel(c, mb, sx, sz, style):
    """Wheel geometry centred at the hub; axle along X, outer face toward sx."""
    R, ww = c.r, c.ww
    hw = ww / 2
    O = (sx * c.tr / 2, R, sz * c.wb / 2)
    rr = R * style.get("rim_frac", 0.62)
    ax = (sx, 0, 0)
    span = R - rr
    prof = [(rr, -0.80 * hw), (rr + 0.22 * span, -0.96 * hw), (rr + 0.62 * span, -hw), (R - 0.035, -0.92 * hw),
            (R - 0.006, -0.78 * hw),
            (R, -0.70 * hw), (R, -0.40 * hw), (R - 0.013, -0.34 * hw), (R - 0.013, -0.22 * hw), (R, -0.17 * hw),
            (R, 0.17 * hw), (R - 0.013, 0.22 * hw), (R - 0.013, 0.34 * hw), (R, 0.40 * hw), (R, 0.70 * hw),
            (R - 0.006, 0.78 * hw), (R - 0.035, 0.92 * hw), (rr + 0.62 * span, hw), (rr + 0.22 * span, 0.96 * hw),
            (rr, 0.80 * hw)]
    SEG = style.get('seg', 32)

    def mod(pi, i):
        # tread blocks: alternate segments drop, staggered between the three ribs; groove floors stay round
        if 4 <= pi <= 15 and pi not in (7, 8, 11, 12):
            lane = 0 if pi <= 6 else (1 if pi <= 10 else 2)
            return 1.0 - 0.02 * (((i + lane) // 2) % 2)
        return 1.0
    mb.lathe(O, ax, prof, SEG, "tyre", closed=True, mod=mod)
    mb.lathe(O, ax, [(rr - 0.045, -0.80 * hw), (rr + 0.012, -0.80 * hw), (rr + 0.012, -0.55 * hw),
                     (rr - 0.02, -0.5 * hw), (rr - 0.02, 0.62 * hw), (rr + 0.016, 0.66 * hw), (rr + 0.016, 0.84 * hw),
                     (rr - 0.045, 0.84 * hw)], SEG, "rim", closed=True)
    mb.lathe(O, ax, [(0, 0.05 * hw), (rr - 0.04, 0.05 * hw), (rr - 0.04, 0.0), (0, 0.0)], 24, "rimdark")
    kind = style["wheel"]
    n = style["spokes"]
    hubr = 0.075
    Ov = Vector(O)
    if kind == "aero":
        mb.lathe(O, ax, [(0, 0.80 * hw), (rr * 0.55, 0.80 * hw), (rr - 0.02, 0.60 * hw), (rr - 0.02, 0.50 * hw),
                         (0, 0.50 * hw)], 30, "rim")
        for i in range(n):
            a = (i + 0.5) * 2 * math.pi / n
            rad = Vector((0, math.sin(a), math.cos(a)))
            mb.box(Ov + Vector((sx * 0.70 * hw, 0, 0)) + rad * rr * 0.70, (0.03, 0.05, rr * 0.34), "rimdark",
                   rot=Matrix.Rotation(-a, 3, 'X'))
    else:
        for i in range(n):
            a = i * 2 * math.pi / n
            for twin in ((-1, 1) if kind == "twin" else (0,)):
                a2 = a + twin * 0.11
                rad = Vector((0, math.sin(a2), math.cos(a2)))
                sw = 0.06 if kind == "spoke6" else 0.032 if kind == "twin" else 0.036
                ctr = Ov + Vector((sx * hw * 0.50, 0, 0)) + rad * rr * 0.54
                rot = Matrix.Rotation(-a2, 3, 'X')
                if kind == "turbine":
                    rot = Matrix.Rotation(-a2 - 0.22 * sx, 3, 'X')
                    ctr = Ov + Vector((sx * hw * 0.50, 0, 0)) + rad * rr * 0.52
                mb.box(ctr, (0.06, sw, rr * 0.92), "rim", bevel=0.012, rot=rot)
        mb.lathe(O, ax, [(0, 0.78 * hw), (hubr, 0.74 * hw), (hubr + 0.02, 0.5 * hw), (0, 0.5 * hw)], 16, "rim")
    # brake disc with a hat, inboard of the spokes
    dr = rr * 0.80
    mb.lathe(O, ax, [(0.10, -0.50 * hw), (dr, -0.50 * hw), (dr, -0.36 * hw), (0.10, -0.36 * hw)], 32, "steel", closed=True)
    mb.lathe(O, ax, [(0, -0.36 * hw), (0.10, -0.36 * hw), (0.10, -0.62 * hw), (0, -0.62 * hw)], 14, "steel")
    return O


def build_caliper(c, mb, sx, sz, style):
    R, ww = c.r, c.ww
    hw = ww / 2
    cx, cy, cz = sx * c.tr / 2, R, sz * c.wb / 2
    dr = R * style.get("rim_frac", 0.62) * 0.80
    a = math.radians(70)
    rad = Vector((0, math.sin(a), -math.cos(a)))
    ctr = Vector((cx + sx * (-0.43 * hw), cy, cz)) + rad * dr * 0.80
    rot = Matrix.Rotation(a + math.pi / 2, 3, 'X')
    mb.box(ctr, (0.115, 0.075, dr * 0.45), "caliper", bevel=0.012, rot=rot)
    mb.box(ctr + Vector((sx * 0.065, 0, 0)), (0.02, 0.05, 0.05), "steel")
    mb.lathe((cx, cy, cz), (sx, 0, 0), [(0.07, -0.95 * hw), (0.07, -0.60 * hw)], 10, "steel")
    return (cx, cy, cz)


def wheels(c, sh):
    st = c.S['wheel']
    if c.S.get('lite'):
        for name, sx, sz in (("fl", 1, 1), ("fr", -1, 1), ("rl", 1, -1), ("rr", -1, -1)):
            c.origins['wheel_' + name] = build_wheel_lite(c, sh.mb('wheel_' + name), sx, sz, st)
        return
    for name, sx, sz in (("fl", 1, 1), ("fr", -1, 1), ("rl", 1, -1), ("rr", -1, -1)):
        c.origins['wheel_' + name] = build_wheel(c, sh.mb('wheel_' + name), sx, sz, st)
        c.origins['caliper_' + name] = build_caliper(c, sh.mb('caliper_' + name), sx, sz, st)


# ----------------------------------------------------------------------------- underside
def helix(mb, centre, r, height, turns, wire, mname, segs_per_turn=6, tilt=(0, 0)):
    """Coil spring as one square-section tube."""
    n = int(turns * segs_per_turn)
    rings = []
    for i in range(n + 1):
        t = i / n
        a = 2 * math.pi * turns * t
        ctr = Vector((centre[0] + r * math.cos(a) + tilt[0] * (t - 0.5) * height,
                      centre[1] + (t - 0.5) * height,
                      centre[2] + r * math.sin(a) + tilt[1] * (t - 0.5) * height))
        out = Vector((math.cos(a), 0, math.sin(a)))
        upv = Vector((0, 1, 0))
        rings.append([ctr + out * wire, ctr + upv * wire, ctr - out * wire, ctr - upv * wire])
    mb.loft(rings, mname)


def underside(c, sh):
    """Floor pan with ribs and tunnel, engine and gearbox, prop shafts, differentials, subframes, suspension,
    steering rack, exhaust with catalysts and silencers, fuel tank, spare wheel, arch liners.  The car spends
    the finale on its roof, so this is modelled to be looked at."""
    mb = sh.mb('underside')
    zf, zr = c.zcF, c.zcR
    yb = c.yfloor
    w = c.w
    Ra = c.Ra
    xin = c.tr / 2 - c.ww / 2 - 0.13            # clear of the tyres between the wheels
    # floor pan: full width between the arches, narrower between the wheels
    za, zb = zf - Ra - 0.02, zr + Ra + 0.02
    mb.box((0, yb + 0.012, (za + zb) / 2), (2 * (w - 0.075), 0.024, za - zb), 'underplate')
    mb.box((0, yb + 0.012, (c.zF - 0.30 + za) / 2), (2 * xin, 0.024, c.zF - 0.30 - za), 'underplate')
    mb.box((0, yb + 0.012, (c.zR + 0.25 + zb) / 2), (2 * xin, 0.024, zb - c.zR - 0.25), 'underplate')
    zq = zr - Ra - 0.03                          # boot floor behind the rear arches, full width
    if zq - (c.zR + 0.25) > 0.1:
        mb.box((0, yb + 0.014, (zq + c.zR + 0.25) / 2), (2 * (w - 0.09), 0.024, zq - c.zR - 0.25), 'underplate')
    # tunnel, longitudinal ribs, cross-members
    zA, zB = c.zF - 0.55, c.zR + 0.35
    mb.box((0, yb - 0.02, (zA + zB) / 2), (0.34, 0.07, abs(zA - zB)), "underplate", bevel=0.02)
    for x in (-0.66, -0.42, 0.42, 0.66):
        mb.box((x * w, yb - 0.002, (za + zb) / 2), (0.05, 0.03, za - zb - 0.12), "underplate", bevel=0.008)
    for z in (za - 0.12, (za + zb) / 2 + 0.25, (za + zb) / 2 - 0.35, zb + 0.12):
        mb.box((0, yb - 0.004, z), (2 * (w - 0.12), 0.034, 0.07), "underplate", bevel=0.008)
    # sill jacking rails
    for sx in (1, -1):
        mb.box((sx * (w - 0.10), yb - 0.012, (za + zb) / 2), (0.04, 0.045, za - zb - 0.3), "trim", bevel=0.008)
    # engine bay: radiator, block, cam covers, sump, gearbox, transfer case
    yrad = c.S['front']['yb'] * c.hs + 0.36
    mb.box((0, yrad, c.zF - 0.40), (w * 1.15, 0.46, 0.06), "underplate", bevel=0.01)
    for k in range(9):
        mb.box((-0.52 + k * 0.13, yrad, c.zF - 0.365), (0.012, 0.42, 0.02), "steel")
    mb.box((0, yb + 0.30, zf - 0.30), (0.62, 0.46, 0.78), "underplate", bevel=0.04)
    for k in range(4):
        mb.box((0, yb + 0.56, zf - 0.55 + k * 0.17), (0.50, 0.09, 0.10), "steel", bevel=0.01)
    mb.box((0.34, yb + 0.44, zf - 0.62), (0.22, 0.20, 0.30), "trim", bevel=0.02)                    # airbox
    mb.box((-0.50, yb + 0.42, zf - 0.75), (0.26, 0.20, 0.18), "trim", bevel=0.015)                  # battery
    mb.box((0, yb - 0.085, zf - 0.30), (0.46, 0.11, 0.52), "steel", bevel=0.02)                      # sump
    mb.cyl((0, yb + 0.03, zf - 1.0), (0, 0, 1), 0.17, 0.75, 14, "underplate")
    mb.cyl((0, yb - 0.02, zf - 1.55), (0, 0, 1), 0.13, 0.45, 12, "steel")
    # prop shafts and joints
    mb.pipe((0, yb - 0.045, zf - 1.7), (0, yb - 0.045, zr + 0.25), 0.045, 8, "steel")
    mb.pipe((0.11, yb - 0.03, zf - 1.45), (0.07, yb - 0.03, zf + 0.12), 0.032, 8, "steel")
    for z in (zf - 1.75, zr + 0.28):
        mb.box((0, yb - 0.045, z), (0.09, 0.09, 0.09), "steel", bevel=0.015)
    ay = c.r - 0.03
    for z in (zf, zr):
        s = 1 if z > 0 else -1
        # differential with a ribbed cover and pinion nose
        mb.lathe((0, ay - 0.04, z), (1, 0, 0), [(0.0, -0.14), (0.12, -0.12), (0.145, 0.0), (0.12, 0.12), (0.0, 0.14)], 14, "underplate")
        mb.lathe((0, ay - 0.04, z + s * 0.14), (0, 0, 1), [(0.075, -0.03), (0.075, 0.03)], 10, "steel")
        for sx in (1, -1):
            mb.pipe((sx * 0.12, ay - 0.04, z), (sx * (c.tr / 2 - c.ww / 2 - 0.02), c.r, z), 0.032, 8, "steel")
            mb.lathe((sx * 0.20, ay - 0.035, z), (sx, 0.1, 0), [(0.05, -0.05), (0.062, 0), (0.05, 0.05)], 8, "trim")   # CV boot
        for sx in (1, -1):
            mb.box((sx * 0.38, yb - 0.03, z), (0.06, 0.06, 0.86), "underplate", bevel=0.012)
        for dz in (-0.38, 0.38):
            mb.box((0, yb - 0.03, z + dz), (0.82, 0.06, 0.07), "underplate", bevel=0.012)
        for sx in (1, -1):
            hub = Vector((sx * (c.tr / 2 - c.ww / 2 - 0.045), c.r, z))
            for dz in (-0.30, 0.30):
                mb.pipe(Vector((sx * 0.36, yb - 0.04, z + dz)), hub + Vector((0, -0.09, dz * 0.12)), 0.022, 6, "steel")
            for dz in (-0.2, 0.2):
                mb.pipe(Vector((sx * 0.46, yb + 0.16, z + dz)), hub + Vector((0, 0.16, dz * 0.1)), 0.016, 6, "steel")
            mb.box(hub + Vector((0, 0.03, 0)), (0.05, 0.24, 0.10), "steel", bevel=0.01)
            sp = Vector((sx * 0.50, yb + 0.20, z + 0.05 * s))
            helix(mb, sp, 0.05, 0.30, 3.5, 0.012, "spring", tilt=(sx * 0.05, 0))
            mb.pipe(sp + Vector((0, -0.20, 0)), sp + Vector((sx * 0.02, 0.18, 0)), 0.02, 8, "underplate")
            mb.pipe(sp + Vector((0, -0.03, 0)), sp + Vector((sx * 0.02, 0.22, 0)), 0.009, 6, "steel")
            mb.pipe(Vector((sx * 0.33, yb - 0.02, z - 0.42 * s)), hub + Vector((0, 0.01, -0.42 * s)), 0.012, 6, "steel")
        mb.pipe(Vector((-0.33, yb - 0.02, z - 0.42 * s)), Vector((0.33, yb - 0.02, z - 0.42 * s)), 0.014, 8, "steel")
    mb.pipe((-0.42, yb - 0.02, zf - 0.20), (0.42, yb - 0.02, zf - 0.20), 0.025, 8, "steel")       # steering rack
    for sx in (1, -1):
        mb.pipe((sx * 0.42, yb - 0.02, zf - 0.20), (sx * (c.tr / 2 - c.ww / 2 - 0.05), c.r - 0.02, zf - 0.12), 0.012, 6, "steel")
    # exhaust: twin downpipes, catalysts, centre pipes, silencers with heat shields, tailpipes
    for sx in (1, -1):
        x = sx * 0.27
        pts = [(sx * 0.18, yb + 0.02, zf - 0.75), (x, yb - 0.04, zf - 1.3), (x, yb - 0.075, zf - 2.0)]
        for a, b in zip(pts[:-1], pts[1:]):
            mb.pipe(a, b, 0.032, 8, "exhaust")
        mb.cyl((x, yb - 0.075, zf - 1.75), (0, 0, 1), 0.065, 0.36, 12, "exhaust")
        mb.pipe((x, yb - 0.075, zf - 1.95), (x, yb - 0.075, zr + 1.05), 0.03, 8, "exhaust")
        mb.pipe((x, yb - 0.075, zr + 1.05), (sx * 0.42, yb - 0.02, zr + 0.45), 0.03, 8, "exhaust")
        mb.pipe((sx * 0.42, yb - 0.02, zr + 0.45), (sx * 0.42, yb - 0.02, zr - 0.30), 0.03, 8, "exhaust")
        zs = (zr - 0.30 + c.zR + 0.30) / 2 - 0.05
        mb.cyl((sx * 0.42, yb - 0.06, zs), (0, 0, 1), 0.085, 0.50, 14, "exhaust", scale=(1.25, 0.8))
        mb.pipe((sx * 0.42, yb - 0.06, zs - 0.25), (sx * 0.36, yb - 0.04, c.zR + 0.20), 0.027, 8, "exhaust")
        for z in (zf - 1.5, zr + 1.0):
            mb.box((x, yb - 0.02, z), (0.02, 0.07, 0.02), "steel")
        mb.box((x, yb - 0.01, zf - 1.75), (0.22, 0.01, 0.5), "steel")                              # heat shield
    # fuel tank with straps and lines
    zt = zr + 0.95
    mb.box((0.02, yb - 0.075, zt), (0.80, 0.15, 0.56), "trim", bevel=0.035)
    for dz in (-0.18, 0.18):
        mb.box((0.02, yb - 0.155, zt + dz), (0.84, 0.014, 0.04), "steel")
    mb.pipe((0.52, yb - 0.02, zt), (0.52, yb - 0.02, zf - 1.2), 0.008, 4, "trim")
    mb.pipe((0.55, yb - 0.02, zt), (0.55, yb - 0.02, zf - 0.8), 0.008, 4, "steel")
    # spare wheel in its well under the boot floor
    zsw = (zr - Ra + c.zR + 0.30) / 2 - 0.02
    rs = min(c.r * 0.86, (zr - Ra - c.zR - 0.32) / 2, 0.30)
    if rs > 0.2:
        mb.lathe((0, yb - 0.10, zsw), (0, 1, 0), [(rs * 0.62, -0.085), (rs - 0.04, -0.095), (rs, -0.06), (rs, 0.06), (rs - 0.04, 0.095),
                                                    (rs * 0.62, 0.085)], 24, "tyre", closed=True)
        mb.lathe((0, yb - 0.10, zsw), (0, 1, 0), [(0, -0.08), (rs * 0.60, -0.08), (rs * 0.60, 0.06), (0, 0.06)], 16, "rimdark")
        mb.lathe((0, yb - 0.03, zsw), (0, 1, 0), [(rs + 0.06, -0.05), (rs + 0.06, 0.04), (rs + 0.02, 0.04), (rs + 0.02, -0.05)], 24, "underplate", closed=True)
        mb.box((0, yb - 0.19, zsw), (0.05, 0.02, 2 * rs + 0.1), "steel")
    # front skid plate and tow eyes
    mb.box((0, yb - 0.105, c.zF - 0.72), (0.90, 0.022, 0.60), "steel", bevel=0.008)
    for z in (c.zF - 0.34, c.zR + 0.30):
        mb.box((0.40, yb - 0.02, z), (0.05, 0.05, 0.12), "steel", bevel=0.01)
    # arch liners: a tub over each wheel, closed on the inboard side
    rl = Ra * 1.09 + 0.012
    x_out = w - 0.03
    x_inb = c.tr / 2 - c.ww / 2 - 0.10
    for z in (zf, zr):
        for sx in (1, -1):
            xa, xb = sorted((sx * x_inb, sx * x_out))
            mb.sector((0, c.yc, z), rl, rl + 0.014, math.radians(-8), math.radians(188), xa, xb, 14, "trim")
            mb.box((sx * (x_inb - 0.008), (yb + c.yc + rl) / 2, z), (0.016, c.yc + rl - yb, 2 * rl), "trim")


# ----------------------------------------------------------------------------- interior
def seat(mb, x, z, y0, width=0.52, depth=0.50, back_h=0.66, head=True):
    """Front-facing seat: cushion, bolsters, backrest, headrest.  y0 = cushion underside."""
    mb.box((x, y0 + 0.07, z), (width, 0.14, depth), "seat", bevel=0.04)
    for sx in (-1, 1):
        mb.box((x + sx * (width / 2 - 0.03), y0 + 0.14, z), (0.07, 0.07, depth * 0.92), "seat_trim", bevel=0.02)
    a = math.radians(-13)
    rot = Matrix.Rotation(a, 3, 'X')
    mb.box((x, y0 + 0.14 + back_h / 2, z - depth / 2 + 0.02), (width, back_h, 0.14), "seat", bevel=0.045, rot=rot)
    for sx in (-1, 1):
        mb.box((x + sx * (width / 2 - 0.03), y0 + 0.14 + back_h * 0.5, z - depth / 2 + 0.06), (0.07, back_h * 0.8, 0.1), "seat_trim",
               bevel=0.02, rot=rot)
    if head:
        yh = y0 + 0.14 + back_h + 0.06
        mb.box((x, yh, z - depth / 2 - 0.10), (0.27, 0.17, 0.10), "seat", bevel=0.03, rot=rot)
        for dx in (-0.07, 0.07):
            mb.pipe((x + dx, yh - 0.1, z - depth / 2 - 0.07), (x + dx, yh - 0.02, z - depth / 2 - 0.09), 0.008, 5, "steel")


def interior(c, sh):
    """Seats, dashboard, steering wheel, console, carpet.  The cabin lining itself comes from the body grids."""
    mb = sh.mb('interior')
    S = c.S
    yfl = c.yfloor + 0.04
    zA = c.cowl[0].z
    zC = c.zR + 0.40
    x_in = c.w - 0.11
    xn = c.tr / 2 - c.ww / 2 - 0.14
    za, zb = c.zcF - c.Ra - 0.02, c.zcR + c.Ra + 0.02
    mb.box((0, yfl, (zA - 0.1 + zb) / 2), (2 * x_in, 0.03, zA - 0.1 - zb), "cabin")
    mb.box((0, yfl + 0.16, (zb + zC) / 2), (2 * x_in, 0.03, zb - zC), "cabin")                 # boot floor over the axle
    mb.box((0, yfl + 0.08, zb), (2 * x_in, 0.19, 0.03), "cabin")
    mb.box((0, yfl + 0.07, (zA + zb) / 2 - 0.2), (0.26, 0.14, zA - zb - 0.7), "cabin", bevel=0.05)
    for sx in (1, -1):                                                                         # wheel-arch boxes in the boot
        mb.box((sx * (x_in - 0.10), yfl + 0.36, c.zcR), (0.22, 0.42, 2 * c.Ra + 0.1), "cabin", bevel=0.05)
    ys = yfl + 0.20
    z1 = c.zn['B1'] - 0.02
    for sx in (1, -1):
        seat(mb, sx * 0.40, z1, ys)
    mb.box((0, ys + 0.16, z1 + 0.10), (0.20, 0.26, 0.66), "cabin", bevel=0.03)                # console
    mb.box((0, ys + 0.31, z1 + 0.22), (0.07, 0.04, 0.16), "steel", bevel=0.01)
    z2 = c.zn['C1'] + 0.16
    for x in (-0.56, 0, 0.56):
        seat(mb, x, z2, ys + 0.02, width=0.54, depth=0.50, back_h=0.62)
    if S.get('third_row') and c.zcR - c.Ra - 0.25 > c.zR + 0.75:
        z3 = c.zcR - c.Ra + 0.10
        for x in (-0.30, 0.30):
            seat(mb, x, z3, ys + 0.14, width=0.50, depth=0.42, back_h=0.52)
    # dashboard
    zd = zA - 0.32
    yd = c.beltc(c.zA) - 0.03
    mb.box((0, yd - 0.07, zd), (2 * x_in - 0.06, 0.24, 0.42), "cabin", bevel=0.06)
    mb.box((0, yd + 0.06, zd + 0.04), (2 * x_in - 0.10, 0.05, 0.34), "cabin", bevel=0.02)
    xd = 0.40
    mb.box((xd, yd + 0.085, zd - 0.06), (0.50, 0.12, 0.20), "cabin", bevel=0.04)             # instrument hood
    for dx in (-0.12, 0.12):
        mb.lathe((xd + dx, yd + 0.05, zd - 0.17), (0, 0.3, -1), [(0.0, 0.0), (0.06, 0.0), (0.06, -0.01), (0.0, -0.01)], 12, "gloss")
    mb.box((0, yd + 0.04, zd - 0.19), (0.30, 0.19, 0.02), "gloss", bevel=0.006,
           rot=Matrix.Rotation(math.radians(-14), 3, 'X'))                                    # centre screen
    mb.box((0, yd - 0.12, zd - 0.14), (0.26, 0.30, 0.14), "cabin", bevel=0.03)
    for dx in (-0.58, 0.58):
        mb.box((dx, yd + 0.02, zd - 0.215), (0.12, 0.05, 0.02), "trim")
    mb.pipe((xd, yd - 0.04, zd - 0.12), (xd, yd + 0.07, zd - 0.36), 0.035, 8, "cabin")
    ctr = Vector((xd, yd + 0.085, zd - 0.39))
    mb.lathe(ctr, (0, 0.35, -1), [(0.185, -0.015), (0.185, 0.015), (0.155, 0.015), (0.155, -0.015)], 20, "trim", closed=True)
    mb.lathe(ctr, (0, 0.35, -1), [(0, -0.03), (0.05, -0.03), (0.05, 0.02), (0, 0.02)], 10, "trim")
    for ang in (0, 120, 240):
        a = math.radians(ang + 90)
        mb.pipe(ctr, ctr + Vector((0.16 * math.cos(a), 0.16 * math.sin(a) * 0.94, 0.16 * math.sin(a) * 0.34)), 0.011, 5, "trim")
    for dx in (0.28, 0.40, 0.52):
        mb.box((dx, yfl + 0.16, zd - 0.10), (0.07, 0.015, 0.05), "steel")
    # rear-view mirror at the windscreen header
    ph = c.G.P[0][4]
    mb.box((0, ph.y - 0.04, ph.z - 0.07), (0.22, 0.06, 0.03), "trim", bevel=0.01)


# ----------------------------------------------------------------------------- lighter parts (patrol car)
def build_wheel_lite(c, mb, sx, sz, style):
    R, ww = c.r, c.ww
    hw = ww / 2
    O = (sx * c.tr / 2, R, sz * c.wb / 2)
    rr = R * style.get("rim_frac", 0.62)
    ax = (sx, 0, 0)
    span = R - rr
    SEG = 20
    prof = [(rr, -0.80 * hw), (rr + 0.6 * span, -hw), (R - 0.03, -0.92 * hw), (R, -0.72 * hw), (R, -0.2 * hw), (R - 0.012, -0.12 * hw),
            (R - 0.012, 0.12 * hw), (R, 0.2 * hw), (R, 0.72 * hw), (R - 0.03, 0.92 * hw), (rr + 0.6 * span, hw), (rr, 0.80 * hw)]
    mb.lathe(O, ax, prof, SEG, "tyre", closed=True)
    mb.lathe(O, ax, [(rr, -0.8 * hw), (rr - 0.02, -0.5 * hw), (rr - 0.02, 0.62 * hw), (rr + 0.014, 0.82 * hw), (rr - 0.03, 0.82 * hw),
                     (rr - 0.045, 0.3 * hw)], SEG, "rim", solid=False)
    mb.lathe(O, ax, [(0, 0.08 * hw), (rr - 0.04, 0.08 * hw), (rr - 0.04, 0.0), (0, 0.0)], 14, "rimdark")
    Ov = Vector(O)
    for i in range(style["spokes"]):
        a = i * 2 * math.pi / style["spokes"]
        rad = Vector((0, math.sin(a), math.cos(a)))
        mb.box(Ov + Vector((sx * hw * 0.50, 0, 0)) + rad * rr * 0.54, (0.05, 0.06, rr * 0.92), "rim", rot=Matrix.Rotation(-a, 3, 'X'))
    mb.lathe(O, ax, [(0, 0.76 * hw), (0.075, 0.72 * hw), (0.09, 0.5 * hw), (0, 0.5 * hw)], 10, "rim")
    mb.lathe(O, ax, [(0, -0.36 * hw), (rr * 0.8, -0.36 * hw), (rr * 0.8, -0.5 * hw), (0, -0.5 * hw)], 14, "steel")
    return O


def underside_lite(c, sh):
    mb = sh.mb('underside')
    zf, zr, yb, w, Ra = c.zcF, c.zcR, c.yfloor, c.w, c.Ra
    xin = c.tr / 2 - c.ww / 2 - 0.13
    za, zb = zf - Ra - 0.02, zr + Ra + 0.02
    mb.box((0, yb + 0.012, (za + zb) / 2), (2 * (w - 0.075), 0.024, za - zb), 'underplate')
    mb.box((0, yb + 0.012, (c.zF - 0.30 + za) / 2), (2 * xin, 0.024, c.zF - 0.30 - za), 'underplate')
    mb.box((0, yb + 0.012, (c.zR + 0.25 + zb) / 2), (2 * xin, 0.024, zb - c.zR - 0.25), 'underplate')
    zq = zr - Ra - 0.03
    mb.box((0, yb + 0.014, (zq + c.zR + 0.25) / 2), (2 * (w - 0.09), 0.024, zq - c.zR - 0.25), 'underplate')
    mb.box((0, yb - 0.02, (c.zF - 0.55 + c.zR + 0.35) / 2), (0.32, 0.07, c.zF - c.zR - 0.9), "underplate")
    for x in (-0.5, 0.5):
        mb.box((x * w, yb - 0.002, (za + zb) / 2), (0.05, 0.03, za - zb - 0.12), "underplate")
    for z in (za - 0.12, (za + zb) / 2, zb + 0.12):
        mb.box((0, yb - 0.004, z), (2 * (w - 0.12), 0.034, 0.07), "underplate")
    mb.box((0, yb - 0.085, zf - 0.30), (0.46, 0.11, 0.52), "steel")
    mb.box((0, yb - 0.10, c.zF - 0.70), (0.86, 0.02, 0.55), "steel")
    mb.cyl((0, yb + 0.02, zf - 1.0), (0, 0, 1), 0.16, 0.7, 10, "underplate")
    mb.pipe((0, yb - 0.045, zf - 1.4), (0, yb - 0.045, zr + 0.2), 0.04, 6, "steel")
    ay = c.r - 0.03
    for z in (zf, zr):
        mb.lathe((0, ay - 0.04, z), (1, 0, 0), [(0.0, -0.14), (0.13, -0.10), (0.13, 0.10), (0.0, 0.14)], 10, "underplate")
        for sx in (1, -1):
            hub = Vector((sx * (c.tr / 2 - c.ww / 2 - 0.045), c.r, z))
            mb.pipe((sx * 0.12, ay - 0.04, z), (hub.x, c.r, z), 0.03, 6, "steel")
            mb.box((sx * 0.38, yb - 0.03, z), (0.06, 0.06, 0.8), "underplate")
            for dz in (-0.28, 0.28):
                mb.pipe(Vector((sx * 0.36, yb - 0.04, z + dz)), hub + Vector((0, -0.09, dz * 0.12)), 0.02, 4, "steel")
            mb.pipe(Vector((sx * 0.50, yb, z)), Vector((sx * 0.52, yb + 0.40, z)), 0.045, 6, "spring")
    x = 0.27
    mb.pipe((0.18, yb + 0.02, zf - 0.75), (x, yb - 0.06, zf - 1.3), 0.03, 6, "exhaust")
    mb.pipe((x, yb - 0.06, zf - 1.3), (x, yb - 0.06, zr + 0.45), 0.03, 6, "exhaust")
    mb.cyl((x, yb - 0.06, zf - 1.7), (0, 0, 1), 0.065, 0.36, 8, "exhaust")
    mb.pipe((x, yb - 0.06, zr + 0.45), (0.40, yb - 0.02, zr - 0.30), 0.03, 6, "exhaust")
    zs = (zr - 0.30 + c.zR + 0.30) / 2
    mb.cyl((0.0, yb - 0.06, zs), (1, 0, 0), 0.085, 0.70, 10, "exhaust")
    mb.pipe((0.36, yb - 0.06, zs), (0.36, yb - 0.04, c.zR + 0.2), 0.027, 6, "exhaust")
    mb.box((-0.05, yb - 0.075, zr + 0.95), (0.70, 0.15, 0.5), "trim")
    rl = Ra * 1.09 + 0.012
    x_out, x_inb = w - 0.03, c.tr / 2 - c.ww / 2 - 0.10
    for z in (zf, zr):
        for sx in (1, -1):
            xa, xb = sorted((sx * x_inb, sx * x_out))
            mb.sector((0, c.yc, z), rl, rl + 0.014, math.radians(-8), math.radians(188), xa, xb, 8, "trim")
            mb.box((sx * (x_inb - 0.008), (yb + c.yc + rl) / 2, z), (0.016, c.yc + rl - yb, 2 * rl), "trim")


def interior_lite(c, sh):
    mb = sh.mb('interior')
    yfl = c.yfloor + 0.04
    zA = c.cowl[0].z
    x_in = c.w - 0.11
    zb = c.zcR + c.Ra
    mb.box((0, yfl, (zA - 0.1 + c.zR + 0.4) / 2), (2 * x_in, 0.03, zA - 0.1 - c.zR - 0.4), "cabin")
    ys = yfl + 0.20
    rot = Matrix.Rotation(math.radians(-13), 3, 'X')
    for x, z, wd in ((0.40, c.zn['B1'] - 0.02, 0.50), (-0.40, c.zn['B1'] - 0.02, 0.50), (0, c.zn['C1'] + 0.16, 1.5)):
        mb.box((x, ys + 0.07, z), (wd, 0.14, 0.5), "seat", bevel=0.03)
        mb.box((x, ys + 0.45, z - 0.23), (wd, 0.62, 0.13), "seat", bevel=0.03, rot=rot)
        if wd < 1:
            mb.box((x, ys + 0.86, z - 0.33), (0.26, 0.16, 0.10), "seat", rot=rot)
    # partition behind the front seats (a patrol car fitting)
    mb.box((0, ys + 0.50, c.zn['B2'] - 0.12), (2 * x_in - 0.1, 0.75, 0.02), "trim")
    zd = zA - 0.32
    yd = c.beltc(c.zA) - 0.03
    mb.box((0, yd - 0.07, zd), (2 * x_in - 0.06, 0.24, 0.42), "cabin", bevel=0.05)
    ctr = Vector((0.40, yd + 0.085, zd - 0.39))
    mb.lathe(ctr, (0, 0.35, -1), [(0.185, -0.015), (0.185, 0.015), (0.155, 0.015), (0.155, -0.015)], 12, "trim", closed=True)
    mb.pipe((0.40, yd - 0.04, zd - 0.12), ctr, 0.03, 5, "cabin")


def patrol_kit(c, sh):
    """Roof lightbar with separate flashing beacons, push bar on the nose, aerial, rear chevrons."""
    R, tub = c.R, c.tub
    nv = R.nj - 1
    pr = R.P[0][int(nv * 0.30)]
    y0 = pr.y
    lb = sh.mb('lightbar')
    half = c.w * 0.60
    lb.box((0, y0 + 0.02, pr.z), (2 * half + 0.06, 0.035, 0.26), 'trim', bevel=0.01)
    for sx in (1, -1):
        lb.box((sx * half * 0.86, y0 - 0.01, pr.z), (0.06, 0.06, 0.20), 'trim')
    lb.box((0, y0 + 0.075, pr.z), (0.22, 0.085, 0.24), 'steel', bevel=0.02)
    for name, sx, m in (('beacon_l', 1, 'beacon_blue'), ('beacon_r', -1, 'beacon_red')):
        ctr = Vector((sx * (0.13 + half) / 2, y0 + 0.08, pr.z))
        sh.mb(name).box(ctr, (half - 0.13, 0.09, 0.22), m, bevel=0.03)
        c.origins[name] = tuple(ctr)
    c.origins['lightbar'] = (0, y0, pr.z)
    # aerial on the rear of the roof
    pa = R.P[0][int(nv * 0.88)]
    ae = sh.mb('aerial')
    ae.lathe((0.25, pa.y - 0.03, pa.z), (0, 1, 0), [(0.02, 0.0), (0.02, 0.04), (0.004, 0.06), (0.004, 0.55)], 6, 'trim')
    c.origins['aerial'] = (0.25, pa.y, pa.z)
    # push bar: two uprights and two hoops ahead of the fascia
    tr = sh.mb('trim')
    zn = c.zF - 0.03
    ybm = c.S['front']['yb'] * c.hs
    ytop = tub.P[0][8].y + 0.03
    for sx in (1, -1):
        tr.box((sx * 0.30, (ybm + 0.12 + ytop) / 2, zn), (0.05, ytop - ybm - 0.12, 0.06), 'trim', bevel=0.012)
        tr.box((sx * 0.30, ybm + 0.30, zn - 0.06), (0.04, 0.05, 0.10), 'trim')
    for y in (ytop - 0.03, (ybm + ytop) / 2 + 0.03):
        tr.pipe((-0.47, y, zn - 0.01), (0.47, y, zn - 0.01), 0.022, 8, 'trim')
    for sx in (1, -1):
        tr.pipe((sx * 0.47, ytop - 0.03, zn - 0.01), (sx * 0.47, (ybm + ytop) / 2 + 0.03, zn - 0.01), 0.022, 8, 'trim')
    # rear chevrons: slanted bands on the tailgate, rising to the centre (mirrored halves make the V)
    M = c.M
    i0 = c.i_rc0 + 6
    n = M - i0
    bd = sh.mb('body')
    up = Vector((0, 1, 0))
    for k, m in enumerate(('livery_red', 'hiviz', 'livery_red', 'hiviz', 'livery_red')):
        for sx in (1, -1):
            pts, nrm = [], []
            for q, i in enumerate(range(i0, M + 1)):
                f = 5.05 + 0.5 * k + 1.9 * q / n            # row coordinate climbing toward the centre
                if f > 9.9:
                    break
                j = int(f)
                p = tub.P[i][j].lerp(tub.P[i][j + 1], f - j)
                nn = tub.N[i][j]
                pts.append(Vector((sx * p.x, p.y, p.z)))
                nrm.append(Vector((sx * nn.x, nn.y, nn.z)))
            if len(pts) > 1:
                K.bar_along(bd, pts, nrm, [up] * len(pts), 0.085, 0.001, 0.005, m)
