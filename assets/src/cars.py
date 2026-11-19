"""The four SUVs. Every number that matters comes from assets/cars.json; the STYLE tables
below only hold design choices (station profiles, overhang split, detail options).

Station tables measure `d` = distance in metres back from the front-most point of the car.
Game frame: +Z forward, +Y up, +X left. Wheel centres: x = +/-track/2, y = r, z = +/-wb/2.
"""
import math
import bpy
from mathutils import Vector, Matrix
from gtl import MB, MATS, make_mat, mat, empty, B

# ------------------------------------------------------------------ style tables
# tub station: (d, yb, yt or 'h' (hood-derived), width fraction, top inset, shoulder chamfer, crown)
# hood station: (d, top y, width fraction)
# cabin station: (d, roof y at station, bottom width frac, top width frac)
STYLES = {
    "escapade_2009": dict(smooth=22,
        fo=1.00, belt=1.14, rail=0.04, sill=0.0, hinge_d=1.42,
        tub=[(0.23, .40, 'h', .93, .05, .04, 0), (0.33, .30, 'h', .99, .04, .05, 0),
             (1.42, .27, 'h', 1.0, .03, .05, 0), (1.52, .25, 1.14, 1.0, .03, .08, 0),
             (-0.29, .27, 1.14, 1.0, .03, .08, 0), (-0.23, .38, 1.14, .96, .05, .07, 0)],
        hood=[(0.23, 1.04, .93), (0.33, 1.09, .99), (1.42, 1.15, 1.0)],
        cab=[(1.50, 1.20, .97, .95), (1.98, 0.0, .97, .90), (3.05, 0.0, .97, .90), (3.20, 0.0, .97, .90),
             (-0.52, 0.0, .97, .90), (-0.34, 0.0, .97, .90), (-0.23, 1.32, .97, .90)],
        side_glass=[(1, 2), (3, 4)], front_glass=(0, 1), rear_glass=(5, 6),
        crown_cab=0.0, wheel="spoke6", spokes=6, flare=0.13, seams=[1.98, 3.12, -0.52],
    ),
    "glug_2017": dict(smooth=42, round=True,
        fo=0.98, belt=1.10, rail=0.03, sill=0.0, hinge_d=1.50,
        tub=[(0.24, .40, 'h', .91, .10, .04, .03), (0.36, .30, 'h', .98, .10, .05, .04),
             (1.50, .28, 'h', 1.0, .10, .05, .04), (1.62, .26, 1.10, 1.0, .11, .12, .03),
             (-0.38, .28, 1.10, 1.0, .11, .12, .03), (-0.24, .38, 1.10, .95, .12, .12, .03)],
        hood=[(0.24, .98, .91), (0.36, 1.03, .98), (1.50, 1.10, 1.0)],
        cab=[(1.72, 1.15, .97, .92), (2.32, -0.03, .97, .84), (3.00, -0.03, .97, .84), (3.12, -0.03, .97, .84),
             (-1.08, -0.05, .97, .82), (-0.73, -0.15, .97, .80), (-0.24, 1.20, .95, .74)],
        side_glass=[(1, 2), (3, 4)], front_glass=(0, 1), rear_glass=(5, 6),
        crown_cab=0.03, wheel="spoke5", spokes=5, flare=0.10, seams=[2.15, 3.06, -0.73],
    ),
    "genesips_2021": dict(smooth=30,
        fo=0.93, belt=1.06, rail=0.0, sill=0.0, hinge_d=1.38,
        tub=[(0.20, .38, 'h', .92, .08, .04, .02), (0.30, .30, 'h', .98, .08, .05, .03),
             (1.38, .26, 'h', 1.0, .07, .05, .03), (1.50, .24, 1.06, 1.0, .08, .10, .02),
             (-0.33, .26, 1.06, 1.0, .08, .10, .02), (-0.2, .36, 1.00, .96, .08, .10, .02)],
        hood=[(0.20, .92, .92), (0.30, .98, .98), (1.38, 1.06, 1.0)],
        cab=[(1.46, 1.10, .97, .93), (2.06, 0.0, .97, .90), (2.95, 0.0, .97, .90), (3.07, 0.0, .97, .90),
             (-1.0, -0.02, .97, .88), (-0.21, 1.18, .96, .84)],
        side_glass=[(1, 2), (3, 5)], front_glass=(0, 1), rear_glass=(4, 5),
        crown_cab=0.02, wheel="spoke5", spokes=5, flare=0.10, seams=[2.06, 3.01],
    ),
    "rangeroller_2026": dict(smooth=18,
        fo=0.95, belt=1.15, rail=0.0, sill=0.0, hinge_d=1.48,
        tub=[(0.20, .46, 'h', .94, .04, .03, 0), (0.30, .36, 'h', .99, .03, .03, 0),
             (1.48, .34, 'h', 1.0, .03, .03, 0), (1.58, .32, 1.15, 1.0, .03, .04, 0),
             (-0.21, .34, 1.15, 1.0, .03, .04, 0), (-0.1, .46, 1.15, .97, .04, .04, 0)],
        hood=[(0.20, 1.06, .94), (0.30, 1.12, .99), (1.48, 1.17, 1.0)],
        cab=[(1.58, 1.20, .96, .94), (2.10, -0.09, .96, .92), (2.85, -0.09, .96, .92), (2.97, -0.09, .96, .92),
             (-0.43, -0.09, .96, .92), (-0.31, -0.09, .96, .92), (-0.1, 1.30, .96, .92)],
        side_glass=[(1, 2), (3, 4)], front_glass=(0, 1), rear_glass=(5, 6),
        crown_cab=0.0, wheel="aero", spokes=0, flare=0.09, seams=[],
    ),
}


# ------------------------------------------------------------------ materials
def car_materials(spec, key):
    make_mat("paint", spec["paint"], metallic=0.35, rough=0.38)
    make_mat("glass", (0.20, 0.30, 0.38), metallic=0.0, rough=0.05, alpha=0.55)
    make_mat("headlight", (1.0, 0.96, 0.82), rough=0.1, emit=(1.0, 0.93, 0.70), emit_strength=1.0)
    make_mat("taillight", (0.62, 0.04, 0.05), rough=0.25, emit=(0.5, 0.0, 0.0), emit_strength=0.6)
    make_mat("trim", (0.07, 0.075, 0.08), rough=0.75)
    make_mat("chrome", (0.80, 0.82, 0.84), metallic=1.0, rough=0.22)
    make_mat("tyre", (0.05, 0.05, 0.055), rough=0.92)
    make_mat("rim", (0.72, 0.74, 0.77), metallic=0.9, rough=0.32)
    make_mat("rimdark", (0.10, 0.10, 0.11), metallic=0.4, rough=0.6)
    make_mat("plate", (0.9, 0.9, 0.85), rough=0.5)


# ------------------------------------------------------------------ context
class Ctx:
    pass


def _d(c, d):
    return c.L + d if d < 0 else d


def make_ctx(key, spec, st):
    c = Ctx()
    c.key, c.spec = key, spec
    c.L, c.W, c.H, c.wb, c.tr = spec["length"], spec["width"], spec["height"], spec["wheelbase"], spec["track"]
    c.r, c.ww, c.gc, c.roof = spec["wheel_radius"], spec["wheel_width"], spec["ground_clearance"], spec["roof_y"]
    c.hw = c.W / 2
    c.bw = c.hw * 0.965
    c.fo = st["fo"]
    c.ro = c.L - c.wb - c.fo
    c.zF = c.wb / 2 + c.fo
    c.zR = -(c.wb / 2 + c.ro)
    c.belt = st["belt"]
    # resolve relative notation: d < 0 -> metres in from the rear end; cab roof y <= 0 -> offset from roof_y
    st = dict(st)
    st["tub"] = [(_d(c, t[0]),) + tuple(t[1:]) for t in st["tub"]]
    st["hood"] = [(_d(c, t[0]),) + tuple(t[1:]) for t in st["hood"]]
    st["cab"] = [(_d(c, t[0]), (c.roof + t[1]) if t[1] <= 0 else t[1]) + tuple(t[2:]) for t in st["cab"]]
    st["seams"] = [_d(c, x) for x in st["seams"]]
    c.st = st
    c.Z = lambda d: c.zF - d
    c.Zr = lambda k: c.zR + k      # k metres forward of the rear-most point
    return c


def hood_y(c, d):
    h = c.st["hood"]
    if d <= h[0][0]:
        return h[0][1]
    for a, b in zip(h[:-1], h[1:]):
        if a[0] <= d <= b[0]:
            t = (d - a[0]) / (b[0] - a[0])
            return a[1] + t * (b[1] - a[1])
    return h[-1][1]


def hood_w(c, d):
    h = c.st["hood"]
    for a, b in zip(h[:-1], h[1:]):
        if a[0] <= d <= b[0]:
            t = (d - a[0]) / (b[0] - a[0])
            return a[2] + t * (b[2] - a[2])
    return h[-1][2]


# ------------------------------------------------------------------ body shell
def tub_ring(c, d, yb, yt, wf, topin, cs, crown):
    w = c.bw * wf
    z = c.Z(d)
    if c.st.get("round"):
        half = [(0.6 * w, yb), (0.92 * w, yb), (w, yb + 0.08), (w, yt - cs), (w - topin * 0.34, yt - cs * 0.34 * 0.5),
                (w - topin * 0.72, yt - cs * 0.07), (w - topin, yt)]
    else:
        half = [(0.6 * w, yb), (0.92 * w, yb), (w, yb + 0.08), (w, yt - cs), (w - topin, yt)]
    right = [Vector((x, y, z)) for x, y in half]
    left = [Vector((-x, y, z)) for x, y in reversed(half)]
    return right + [Vector((0, yt + crown, z))] + left


def build_tub(c):
    rings = []
    for (d, yb, yt, wf, ti, cs, cr) in c.st["tub"]:
        if yt == 'h':
            yt = hood_y(c, d) - 0.07
        rings.append(tub_ring(c, d, yb, yt, wf, ti, cs, cr))
    mb = MB()
    mb.loft(rings, "paint")
    return mb


def arch_cutters(c):
    out = []
    for sx in (1, -1):
        for sz in (1, -1):
            m = MB()
            m.cyl((sx * (c.bw - 0.12), c.r, sz * c.wb / 2), (1, 0, 0), c.r + 0.06, 0.70, 28, "paint")
            out.append(m)
    return out


def boolean_cut(tub, cutters):
    tub_o = tub.to_object("tub_tmp", smooth=None)
    cut_objs = [m.to_object("cut_tmp%d" % i, smooth=None) for i, m in enumerate(cutters)]
    for co in cut_objs:
        md = tub_o.modifiers.new("b", 'BOOLEAN')
        md.operation = 'DIFFERENCE'
        md.object = co
        md.solver = 'EXACT'
    dg = bpy.context.evaluated_depsgraph_get()
    ev = tub_o.evaluated_get(dg)
    me = bpy.data.meshes.new_from_object(ev)
    res = MB()
    res.from_mesh(me)
    bpy.data.meshes.remove(me)
    for o in [tub_o] + cut_objs:
        d = o.data
        bpy.data.objects.remove(o)
        bpy.data.meshes.remove(d)
    return res


def cab_ring(c, d, yt, wbf, wtf, crown):
    st = c.st
    ybot = c.belt - 0.05
    z = c.Z(d)
    wb_, wt_ = c.bw * wbf, c.bw * wtf
    rc = min(0.11, max(0.02, (yt - ybot) * 0.35))
    c0 = (wb_, ybot)
    c1 = (wt_ + 0.05, yt - rc)
    c2 = (wt_, yt)
    right = [Vector((x, y, z)) for x, y in (c0, c1, c2)]
    left = [Vector((-x, y, z)) for x, y in (c2, c1, c0)]
    return right + [Vector((0, yt + crown, z))] + left


def cab_rings(c):
    st = c.st
    out = []
    for (d, yt, wbf, wtf) in st["cab"]:
        if d == st["cab"][0][0] or True:
            yt = min(yt, c.roof - st["rail"] - st["crown_cab"])
        out.append(cab_ring(c, d, yt, wbf, wtf, st["crown_cab"]))
    return out


def lerp(a, b, t):
    return a + (b - a) * t


def glass_quad(mb, pts, hint, off=0.007):
    a, b, cc, d = [Vector(p) for p in pts]
    n = (b - a).cross(d - a)
    if n.length < 1e-9:
        n = (cc - a).cross(d - a)
    n.normalize()
    if n.dot(Vector(hint)) < 0:
        n = -n
    mb.face([p + n * off for p in (a, b, cc, d)], "glass", hint=n)


def build_glass(c, rings):
    st = c.st
    g = MB()
    # side windows
    s0, s1 = (0.14, 0.90)
    for (i0, i1) in st["side_glass"]:
        for sgn in (1, -1):
            for i in range(i0, i1):
                A, Bn = rings[i], rings[i + 1]
                def pt(R, s):
                    p = R[0] + (R[1] - R[0]) * s
                    return Vector((sgn * p.x, p.y, p.z))
                quad = [pt(A, s0), pt(Bn, s0), pt(Bn, s1), pt(A, s1)]
                glass_quad(g, quad, (sgn, 0, 0))
    # front and rear glass: use the roof-edge corners of the two stations
    for key, hint in (("front_glass", (0, 0.5, 1)), ("rear_glass", (0, 0.5, -1))):
        i, j = st[key]
        A, Bn = rings[i], rings[j]
        t0, t1 = (0.10, 0.92)
        def corner(R, sgn):
            p = R[1] if sgn > 0 else R[5]
            return p
        pts = []
        for t, sgn in ((t0, 1), (t0, -1), (t1, -1), (t1, 1)):
            p = corner(A, sgn) + (corner(Bn, sgn) - corner(A, sgn)) * t
            p.x *= 0.96
            pts.append(p)
        glass_quad(g, pts, hint)
    return g


def build_cabin(c, rings, mname="paint"):
    mb = MB()
    mb.loft(rings, mname)
    return mb


# ------------------------------------------------------------------ parts
def build_bonnet(c):
    st = c.st
    hs = [h for h in st["hood"]]
    crown = [t[6] for t in st["tub"] if t[2] == 'h'][0]
    rings = []
    for (d, yt, wf) in hs:
        w = c.bw * wf
        z = c.Z(d)
        pts = [(w, yt - 0.07), (w, yt - 0.03), (w - 0.06, yt), (0, yt + crown), (-(w - 0.06), yt),
               (-w, yt - 0.03), (-w, yt - 0.07)]
        rings.append([Vector((x, y, z)) for x, y in pts])
    mb = MB()
    mb.loft(rings, "paint")
    return mb


def build_wheel(c, sx, sz, rim_style, spokes):
    r, ww = c.r, c.ww
    hw = ww / 2
    cx, cy, cz = sx * c.tr / 2, r, sz * c.wb / 2
    rr = r * 0.62
    mb = MB()
    ax = (sx, 0, 0)
    prof = [(rr, -hw * 0.9), (r * 0.80, -hw), (r - 0.035, -hw * 0.96), (r, -hw * 0.55),
            (r, hw * 0.55), (r - 0.035, hw * 0.96), (r * 0.80, hw), (rr, hw * 0.9)]
    mb.lathe((cx, cy, cz), ax, prof, 22, "tyre", closed=True)
    mb.lathe((cx, cy, cz), ax, [(rr - 0.03, -hw * 0.9), (rr + 0.006, -hw * 0.9), (rr + 0.006, hw * 0.9),
                                (rr - 0.03, hw * 0.9)], 22, "rim", closed=True)
    # dish plate behind the spokes
    mb.lathe((cx, cy, cz), ax, [(0, hw * 0.35), (rr - 0.02, hw * 0.35), (rr - 0.02, hw * 0.1), (0, hw * 0.1)], 22, "rimdark")
    if rim_style == "aero":
        mb.lathe((cx, cy, cz), ax, [(0, hw * 0.72), (rr * 0.62, hw * 0.72), (rr - 0.015, hw * 0.52),
                                    (rr - 0.015, hw * 0.35), (0, hw * 0.35)], 22, "rim")
        for i in range(6):
            a = i * math.pi / 3 + 0.2
            rad = Vector((0, math.sin(a), math.cos(a)))
            mb.box(Vector((cx + sx * hw * 0.74, cy, cz)) + rad * rr * 0.58, (0.015, 0.05, rr * 0.42), "rimdark",
                   rot=Matrix.Rotation(-a, 3, 'X'))
    else:
        for i in range(spokes):
            a = i * 2 * math.pi / spokes
            rad = Vector((0, math.sin(a), math.cos(a)))
            ctr = Vector((cx + sx * hw * 0.55, cy, cz)) + rad * rr * 0.52
            mb.box(ctr, (0.06, 0.07 if rim_style == "spoke6" else 0.06, rr * 0.9), "rim", bevel=0.01,
                   rot=Matrix.Rotation(-a, 3, 'X'))
        mb.lathe((cx, cy, cz), ax, [(0, hw * 0.82), (0.085, hw * 0.78), (0.095, hw * 0.4), (0, hw * 0.4)], 16, "rim")
    return mb, (cx, cy, cz)


def build_mirror(c, sx, d_m, y_m, size=(0.20, 0.17, 0.13), arm=0.1):
    z = c.Z(d_m)
    x0 = sx * c.bw * 0.97
    mb = MB()
    tip = sx * c.hw
    hx = size[0]
    # arm + housing; housing outer tip exactly at hw
    mb.box((x0 + sx * 0.01, y_m, z), (0.05, 0.06, 0.10), "trim")
    mb.box((tip - sx * hx / 2, y_m + 0.04, z - 0.01), size, "paint", bevel=0.03)
    mb.box((tip - sx * hx / 2, y_m + 0.04, z + size[2] / 2 - 0.0), (size[0] * 0.8, size[1] * 0.78, 0.012), "chrome")
    return mb, (x0, y_m, z)


def lamp_box(c, sx, y, d, sz, kind):
    y = y if kind != 'box' else 0.88
    z = c.Z(d)
    mb = MB()
    if kind == "oval":
        mb.lathe((sx * c.bw * 0.70, y, z), (0, 0, 1), [(0.0, 0.0), (0.12, 0.0), (0.12, 0.04), (0.0, 0.05)], 14,
                 "headlight", scale=(1.0, 0.75))
    else:
        mb.box((sx * c.bw * sz[3], y, z), sz[:3], "headlight", bevel=0.02)
    return mb


# ------------------------------------------------------------------ the build
def build_car(key, spec, root):
    c = make_ctx(key, spec, STYLES[key])
    st = c.st
    car_materials(spec, key)
    P = root

    # ---- shell
    tub = boolean_cut(build_tub(c), arch_cutters(c))
    crings = cab_rings(c)
    body = MB()
    body.merge(tub)
    trim = MB()
    chrome = MB()
    grille = MB()
    tail = MB()
    floating = key == "rangeroller_2026"
    if floating:
        trim.merge(build_cabin(c, crings, "trim"))
    else:
        body.merge(build_cabin(c, crings))
    glass = build_glass(c, crings)

    # arch liners / flares
    for sx in (1, -1):
        for sz in (1, -1):
            x0, x1 = sorted((sx * (c.bw - 0.45), sx * (c.bw + st["flare"] * 0.3)))
            trim.sector((0, c.r, sz * c.wb / 2), c.r + 0.04, c.r + 0.07 + st["flare"] * 0.6, 0.02, math.pi - 0.02,
                        x0, x1, 14, "trim")
    # sill cladding
    zc0, zc1 = c.Z(1.75), c.zR + 0.62
    for sx in (1, -1):
        trim.box((sx * (c.bw + 0.004), 0.40 + st["sill"], (zc0 + zc1) / 2), (0.05, 0.16, abs(zc0 - zc1)), "trim", bevel=0.015)

    # door seams
    for sx in (1, -1):
        for d in st["seams"]:
            trim.box((sx * (c.bw + 0.001), (c.belt + 0.45) / 2 + 0.05, c.Z(d)), (0.012, c.belt - 0.5, 0.014), "trim")

    parts = {}
    DET[key](c, body, trim, chrome, grille, tail, parts)

    # ---- roof anchor
    z_roof = (c.Z(st["cab"][1][0]) + c.Z(st["cab"][-3][0])) / 2
    anchor = empty("roof_anchor", (0, c.roof, z_roof), P)

    # ---- nodes
    objs = {}
    objs["body"] = body.to_object("body", parent=P, smooth=st['smooth'])
    objs["glass"] = glass.to_object("glass", parent=P, smooth=None)
    objs["trim"] = trim.to_object("trim", parent=P, smooth=st['smooth'])
    objs["chrome"] = chrome.to_object("chrome", parent=P, smooth=st['smooth'])
    objs["grille"] = grille.to_object("grille", parent=P)
    objs["taillights"] = tail.to_object("taillights", parent=P)
    if floating:
        pass
    # wheels
    for name, sx, sz in (("wheel_fl", 1, 1), ("wheel_fr", -1, 1), ("wheel_rl", 1, -1), ("wheel_rr", -1, -1)):
        wm, org = build_wheel(c, sx, sz, st["wheel"], st["spokes"])
        wm.to_object(name, origin=org, parent=P)
    # headlights
    for name, sx in (("headlight_l", 1), ("headlight_r", -1)):
        mb, org = parts["lamp"](sx)
        mb.to_object(name, origin=org, parent=P)
    # detachables
    bon = build_bonnet(c)
    bon.to_object("bonnet", origin=(0, hood_y(c, st["hinge_d"]), c.Z(st["hinge_d"])), parent=P, smooth=st['smooth'])
    for nm in ("bumper_front", "bumper_rear"):
        mb, org = parts[nm]
        mb.to_object(nm, origin=org, parent=P, smooth=st['smooth'])
    for nm, sx in (("mirror_l", 1), ("mirror_r", -1)):
        mb, org = build_mirror(c, sx, *parts["mirror"])
        mb.to_object(nm, origin=org, parent=P, smooth=st['smooth'])
    return c


# ------------------------------------------------------------------ per-style details
def bumper(c, front, upper, lower, w, hu, hl, depth, yu, yl, up_mat="paint", low_mat="trim", extra=None):
    """Bumper node: origin on the centreline at the mounting face (the body end face)."""
    sgn = 1 if front else -1
    zface = c.Z(0.23 if front else c.L - 0.23) if False else (c.zF - 0.23 if front else c.zR + 0.23)
    zc = zface + sgn * depth / 2 - sgn * 0.05
    mb = MB()
    mb.box((0, yu, zc), (w, hu, depth), up_mat, bevel=0.05)
    mb.box((0, yl, zc - sgn * 0.03), (w * 0.94, hl, depth * 0.92), low_mat, bevel=0.03)
    if extra:
        extra(mb, sgn, zface, zc)
    return mb, (0, yu, zface)


def det_escapade(c, body, trim, chrome, grille, tail, parts):
    st = c.st
    zn = c.zF - 0.23
    # grille: chrome frame, dark recess, slats
    gy = 0.84
    chrome.box((0, gy, zn + 0.05), (1.02, 0.50, 0.10), "chrome", bevel=0.025)
    grille.box((0, gy, zn + 0.10), (0.92, 0.40, 0.04), "trim")
    for k in range(5):
        chrome.box((0, gy - 0.16 + k * 0.08, zn + 0.125), (0.92, 0.035, 0.03), "chrome")
    chrome.box((0, gy, zn + 0.125), (0.04, 0.40, 0.03), "chrome")
    # lamp bezels
    for sx in (1, -1):
        chrome.box((sx * 0.74, 0.92, zn + 0.035), (0.40, 0.36, 0.07), "chrome", bevel=0.02)
    # roof rails, running boards, handles
    for sx in (1, -1):
        zr0, zr1 = c.Z(2.05), c.Zr(0.44)
        chrome.box((sx * 0.74, c.roof - 0.035, (zr0 + zr1) / 2), (0.06, 0.05, abs(zr1 - zr0)), "chrome", bevel=0.012)
        for dz in (2.3, 3.5, 4.4):
            chrome.box((sx * 0.74, c.roof - 0.07, c.Z(dz)), (0.05, 0.03, 0.06), "chrome")
        chrome.box((sx * c.bw, 0.34, (c.Z(1.9) + c.Zr(0.64)) / 2), (0.07, 0.045, abs(c.Z(1.9) - c.Zr(0.64))), "chrome", bevel=0.01)
        for d in (2.85, 4.35):
            chrome.box((sx * (c.bw + 0.012), c.belt - 0.08, c.Z(d)), (0.03, 0.04, 0.18), "chrome", bevel=0.008)
        chrome.box((sx * (c.bw + 0.004), 0.70, (c.Z(0.9) + c.Zr(0.14)) / 2), (0.018, 0.022, abs(c.Z(0.9) - c.Zr(0.14))), "chrome")
    # tail lamps: tall vertical units
    for sx in (1, -1):
        tail.box((sx * (c.bw - 0.24), 0.98, c.zR + 0.27), (0.30, 0.20, 0.05), "taillight", bevel=0.02)
    chrome.box((0, 0.98, c.zR + 0.245), (0.86, 0.04, 0.03), "chrome")
    chrome.box((0, 1.12, c.zR + 0.245), (0.50, 0.28, 0.02), "plate")

    def front_ex(mb, sgn, zface, zc):
        for sx in (1, -1):
            mb.box((sx * 0.68, 0.38, zface + 0.20), (0.26, 0.10, 0.06), "trim")
    parts["bumper_front"] = bumper(c, True, "chrome", "trim", 2 * c.bw * 1.0, 0.32, 0.20, 0.34, 0.54, 0.34,
                                   up_mat="chrome", extra=front_ex)
    parts["bumper_rear"] = bumper(c, False, "chrome", "trim", 2 * c.bw * 1.0, 0.30, 0.20, 0.32, 0.56, 0.36, up_mat="chrome")
    parts["mirror"] = (1.98, 1.26)

    def lamp(sx):
        return lamp_box(c, sx, 0.92, 0.23 - 0.075, (0.31, 0.27, 0.05, 0.77), "box"), (sx * c.bw * 0.77, 0.88, c.zF - 0.23 + 0.075)
    parts["lamp"] = lamp


def det_glug(c, body, trim, chrome, grille, tail, parts):
    zn = c.zF - 0.24
    gy = 0.80
    # pill-shaped grille: frame + three silver slats
    trim.box((0, gy, zn + 0.03), (0.86, 0.38, 0.07), "trim", bevel=0.05)
    for k in range(3):
        chrome.box((0, gy - 0.10 + k * 0.10, zn + 0.07), (0.78, 0.045, 0.03), "chrome", bevel=0.01)
    # lamp surrounds
    for sx in (1, -1):
        trim.box((sx * 0.70, 0.92, zn + 0.02), (0.44, 0.26, 0.05), "trim", bevel=0.05)
    for sx in (1, -1):
        zr0, zr1 = c.Z(2.2), c.Zr(1.13)
        chrome.box((sx * 0.72, c.roof - 0.015, (zr0 + zr1) / 2), (0.045, 0.03, abs(zr1 - zr0)), "chrome", bevel=0.01)
        trim.box((sx * (c.bw + 0.02), 0.36, (c.Z(1.9) + c.Zr(0.63)) / 2), (0.04, 0.10, abs(c.Z(1.9) - c.Zr(0.63))), "trim", bevel=0.015)
        for d in (2.65, 3.75):
            chrome.box((sx * (c.bw + 0.006), c.belt - 0.06, c.Z(d)), (0.025, 0.035, 0.20), "chrome", bevel=0.008)
        chrome.box((sx * (c.bw + 0.004), 0.82, (c.Z(1.0) + c.Zr(0.23)) / 2), (0.014, 0.02, abs(c.Z(1.0) - c.Zr(0.23))), "chrome")
        tail.box((sx * (c.bw - 0.14), 0.98, c.zR + 0.22), (0.26, 0.20, 0.06), "taillight", bevel=0.04)
        tail.box((sx * (c.bw - 0.04), 0.98, c.zR + 0.30), (0.08, 0.20, 0.10), "taillight", bevel=0.03)
    chrome.box((0, 0.98, c.zR + 0.215), (0.48, 0.016, 0.02), "chrome")
    chrome.box((0, 1.00, c.zR + 0.215), (0.46, 0.14, 0.02), "plate")

    def front_ex(mb, sgn, zface, zc):
        mb.box((0, 0.36, zface + 0.25), (0.9, 0.05, 0.05), "chrome", bevel=0.01)
    parts["bumper_front"] = bumper(c, True, "paint", "trim", 2 * c.bw * 0.995, 0.36, 0.22, 0.34, 0.52, 0.31, extra=front_ex)
    parts["bumper_rear"] = bumper(c, False, "paint", "trim", 2 * c.bw * 0.995, 0.36, 0.22, 0.32, 0.54, 0.33)
    parts["mirror"] = (2.1, 1.24)

    def lamp(sx):
        return lamp_box(c, sx, 0.86, 0.20, None, "oval"), (sx * c.bw * 0.70, 0.86, c.zF - 0.175)
    parts["lamp"] = lamp


def det_genesips(c, body, trim, chrome, grille, tail, parts):
    zn = c.zF - 0.20
    gy = 0.745
    # wide, low, rounded slot grille (own design) with three horizontal bars
    wd, ht, rr_ = 1.30, 0.17, 0.05
    def slot(z, k):
        w2, h2 = wd / 2 * k, ht / 2 * k
        pts = [(w2 - rr_, h2), (-(w2 - rr_), h2), (-w2, h2 - rr_), (-w2, -(h2 - rr_)), (-(w2 - rr_), -h2), (w2 - rr_, -h2),
               (w2, -(h2 - rr_)), (w2, h2 - rr_)]
        return [Vector((x, gy + y, z)) for x, y in pts]
    trim.loft([slot(zn, 1.0), slot(zn + 0.07, 0.96)], "trim")
    for k in (-1, 0, 1):
        chrome.box((0, gy + k * 0.05, zn + 0.075), (1.22, 0.018, 0.02), "chrome")
    for sx in (1, -1):
        tail.box((sx * (c.bw - 0.34), 1.06, c.zR + 0.30), (0.34, 0.06, 0.05), "taillight", bevel=0.015)
        trim.box((sx * (c.bw + 0.003), 0.38, (c.Z(1.9) + c.Zr(0.65)) / 2), (0.04, 0.12, abs(c.Z(1.9) - c.Zr(0.65))), "trim", bevel=0.015)
        for d in (2.7, 3.7):
            chrome.box((sx * (c.bw + 0.003), c.belt - 0.04, c.Z(d)), (0.02, 0.025, 0.16), "chrome")
        chrome.box((sx * (c.bw + 0.003), 0.74, (c.Z(1.0) + c.Zr(0.25)) / 2), (0.012, 0.016, abs(c.Z(1.0) - c.Zr(0.25))), "chrome")
        trim.box((sx * 0.80, 0.76, zn + 0.0), (0.22, 0.28, 0.03), "trim", bevel=0.03)  # lamp surround
    tail.box((0, 1.06, c.zR + 0.30 - 0.0), (0.18, 0.06, 0.05), "taillight")
    chrome.box((0, 0.90, c.zR + 0.30), (0.46, 0.13, 0.02), "plate")

    def front_ex(mb, sgn, zface, zc):
        for sx in (1, -1):
            mb.box((sx * 0.78, 0.38, zface + 0.20), (0.22, 0.07, 0.05), "trim", bevel=0.01)
    parts["bumper_front"] = bumper(c, True, "paint", "trim", 2 * c.bw * 0.995, 0.30, 0.20, 0.30, 0.50, 0.30, extra=front_ex)
    parts["bumper_rear"] = bumper(c, False, "paint", "trim", 2 * c.bw * 0.995, 0.32, 0.22, 0.30, 0.52, 0.31)
    parts["mirror"] = (2.04, 1.12)

    def lamp(sx):
        mb = MB()
        mb.box((sx * 0.80, 0.76, c.zF - 0.20 + 0.025), (0.15, 0.22, 0.05), "headlight", bevel=0.02)
        return mb, (sx * 0.80, 0.76, c.zF - 0.20 + 0.025)
    parts["lamp"] = lamp


def det_rangeroller(c, body, trim, chrome, grille, tail, parts):
    zn = c.zF - 0.20
    # floating roof plate in body colour (cabin is blacked out)
    plate = MB()
    ys = c.roof
    rings = []
    for z, wf in ((c.Z(1.96), 0.90), (c.Z(2.10), 0.97), (c.Zr(0.25), 0.97), (c.Zr(0.15), 0.92)):
        w = c.bw * wf
        pts = [(w, ys - 0.07), (w, ys - 0.03), (w - 0.05, ys), (-(w - 0.05), ys), (-w, ys - 0.03), (-w, ys - 0.07)]
        rings.append([Vector((x, y, z)) for x, y in pts])
    body.loft(rings, "paint")
    # fascia: blank panel, light strip, slim lower intake
    trim.box((0, 0.64, zn + 0.02), (0.90, 0.07, 0.05), "trim", bevel=0.02)
    for sx in (1, -1):
        trim.box((sx * (c.bw + 0.003), 0.44, (c.Z(1.9) + c.Zr(0.35)) / 2), (0.03, 0.14, abs(c.Z(1.9) - c.Zr(0.35))), "trim", bevel=0.01)
        trim.box((sx * 0.66, 0.92, zn + 0.0), (0.46, 0.14, 0.03), "trim", bevel=0.03)
        tail.box((sx * (c.bw - 0.24), 1.10, c.zR + 0.27), (0.30, 0.05, 0.04), "taillight")
        tail.box((sx * (c.bw - 0.04), 1.10, c.zR + 0.26), (0.05, 0.40, 0.04), "taillight")
    tail.box((0, 1.10, c.zR + 0.27), (0.60, 0.05, 0.04), "taillight")
    trim.box((0, 0.78, c.zR + 0.26), (0.78, 0.05, 0.03), "trim")
    chrome.box((0, 0.90, c.zR + 0.26), (0.44, 0.12, 0.015), "plate")

    def front_ex(mb, sgn, zface, zc):
        mb.box((0, 0.30, zface + 0.20), (1.1, 0.07, 0.06), "chrome", bevel=0.015)
    parts["bumper_front"] = bumper(c, True, "paint", "trim", 2 * c.bw * 0.995, 0.34, 0.22, 0.30, 0.56, 0.37, extra=front_ex)
    parts["bumper_rear"] = bumper(c, False, "paint", "trim", 2 * c.bw * 0.995, 0.34, 0.22, 0.30, 0.58, 0.39)
    parts["mirror"] = (2.12, 1.28)

    def lamp(sx):
        mb = MB()
        mb.box((sx * 0.66, 0.92, c.zF - 0.20 + 0.025), (0.36, 0.085, 0.045), "headlight", bevel=0.02)
        return mb, (sx * 0.66, 0.92, c.zF - 0.20 + 0.025)
    parts["lamp"] = lamp


DET = {"escapade_2009": det_escapade, "glug_2017": det_glug, "genesips_2021": det_genesips, "rangeroller_2026": det_rangeroller}
