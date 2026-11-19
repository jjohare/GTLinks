"""The four SUVs (v2). Dimensions come from assets/cars.json; STYLES only holds design choices.

Fractions: `f` is the distance back from the front-most point divided by the car length;
heights in `top` / `belt` are fractions of roof_y; `floor` is metres above ground_clearance.
Original stylised designs; no badges, lettering or marque cues.
"""
import math
import bpy
from mathutils import Vector, Matrix
from gtl import MB, MATS, empty, B
import carbody
import carparts
from carbody import Cage, build_cage, seam_strip, pchip, clamp

STYLES = {
    # upright, slab-sided, chrome-heavy, flat roof, near-vertical tailgate
    "escapade_2009": dict(
        smooth=36, fo=1.00, roof_frac=0.86, hood_crown=0.025, roof_crown=0.035,
        nose_fe=0.060, nose_p=2.6, tail_fe=0.045, tail_p=2.6, flare=0.035,
        top=[(0, 0.54), (0.03, 0.565), (0.15, 0.585), (0.27, 0.598), (0.285, 0.62), (0.372, 0.95), (0.40, 0.975),
             (0.60, 0.985), (0.90, 0.985), (0.952, 0.975), (0.972, 0.82), (0.99, 0.64), (1.0, 0.60)],
        belt=[(0, 0.60), (1, 0.60)],
        floor=[(0, 0.42), (0.04, 0.28), (0.12, 0.24), (0.88, 0.24), (0.96, 0.28), (1, 0.40)],
        wind=(0.295, 0.372), rear_glass=(0.957, 0.984), side_glass=[(0.388, 0.588), (0.608, 0.914)],
        bonnet=(0.035, 0.272), seams=[0.388, 0.598, 0.932], seat_rows=[0.50, 0.73],
        wheel="spoke6", spokes=6, rim_frac=0.60, hinge_f=0.272,
    ),
    # rounded, smooth, tall arched roof, raked tail with overhang
    "glug_2017": dict(
        smooth=48, fo=0.98, roof_frac=0.78, hood_crown=0.045, roof_crown=0.075,
        nose_fe=0.090, nose_p=2.2, tail_fe=0.075, tail_p=2.2, flare=0.045,
        top=[(0, 0.50), (0.04, 0.54), (0.16, 0.565), (0.28, 0.60), (0.31, 0.625), (0.40, 0.90), (0.48, 0.98),
             (0.62, 0.995), (0.76, 0.97), (0.88, 0.90), (0.95, 0.75), (1.0, 0.56)],
        belt=[(0, 0.56), (1, 0.62)],
        floor=[(0, 0.42), (0.05, 0.28), (0.14, 0.24), (0.86, 0.24), (0.95, 0.30), (1, 0.44)],
        wind=(0.318, 0.462), rear_glass=(0.862, 0.958), side_glass=[(0.478, 0.612), (0.632, 0.84)],
        bonnet=(0.045, 0.300), seams=[0.478, 0.622, 0.846], seat_rows=[0.54, 0.74],
        wheel="twin", spokes=5, rim_frac=0.62, hinge_f=0.300,
    ),
    # sleek, low roof, strongly raked screen and long fastback tail, rising beltline
    "genesips_2021": dict(
        smooth=40, fo=0.93, roof_frac=0.80, hood_crown=0.03, roof_crown=0.05,
        nose_fe=0.080, nose_p=2.3, tail_fe=0.060, tail_p=2.4, flare=0.05,
        top=[(0, 0.56), (0.04, 0.585), (0.15, 0.605), (0.29, 0.635), (0.31, 0.65), (0.43, 0.965), (0.50, 1.0),
             (0.62, 0.985), (0.74, 0.92), (0.86, 0.80), (0.96, 0.67), (1.0, 0.60)],
        belt=[(0, 0.58), (0.5, 0.62), (1, 0.68)],
        floor=[(0, 0.40), (0.05, 0.27), (0.14, 0.24), (0.86, 0.24), (0.95, 0.27), (1, 0.38)],
        wind=(0.322, 0.432), rear_glass=(0.800, 0.936), side_glass=[(0.446, 0.602), (0.622, 0.80)],
        bonnet=(0.04, 0.292), seams=[0.446, 0.612, 0.80], seat_rows=[0.53, 0.70],
        wheel="turbine", spokes=5, rim_frac=0.64, hinge_f=0.292,
    ),
    # clean boxy volume, flush surfaces, blacked-out pillars and a floating roof
    "rangeroller_2026": dict(
        smooth=26, fo=0.95, roof_frac=0.935, hood_crown=0.015, roof_crown=0.02, float_roof=0.07,
        pillar_node="pillars", pillar_mat="trim",
        nose_fe=0.045, nose_p=3.2, tail_fe=0.040, tail_p=3.2, flare=0.02,
        top=[(0, 0.57), (0.03, 0.585), (0.15, 0.605), (0.30, 0.625), (0.315, 0.645), (0.392, 0.94), (0.42, 0.985),
             (0.93, 0.985), (0.965, 0.93), (0.985, 0.74), (1.0, 0.63)],
        belt=[(0, 0.64), (1, 0.64)],
        floor=[(0, 0.46), (0.04, 0.34), (0.12, 0.30), (0.88, 0.30), (0.96, 0.34), (1, 0.46)],
        wind=(0.322, 0.392), rear_glass=(0.950, 0.985), side_glass=[(0.408, 0.603), (0.623, 0.928)],
        bonnet=(0.032, 0.285), seams=[], seat_rows=[0.50, 0.72],
        wheel="aero", spokes=10, rim_frac=0.64, hinge_f=0.285,
    ),
}


class Ctx:
    pass


def make_ctx(key, spec):
    c = Ctx()
    c.key, c.spec = key, spec
    c.L, c.W, c.H, c.wb, c.tr = spec["length"], spec["width"], spec["height"], spec["wheelbase"], spec["track"]
    c.r, c.ww, c.gc, c.roof = spec["wheel_radius"], spec["wheel_width"], spec["ground_clearance"], spec["roof_y"]
    st = dict(STYLES[key])
    c.hw = c.W / 2
    c.bw = c.hw * 0.955
    c.fo = st["fo"]
    c.ro = c.L - c.wb - c.fo
    c.zF = c.wb / 2 + c.fo
    c.zR = -(c.wb / 2 + c.ro)
    st["floor"] = [(f, c.gc + v) for f, v in st["floor"]]
    c.st = st
    return c


# ------------------------------------------------------------------ helpers on the cage
def nose_d(cage, x, rear=False):
    """Distance in from the nose (or tail) tip where the plan-view surface half-width equals x."""
    lo, hi = 0.0, 0.5
    for _ in range(40):
        mid = (lo + hi) / 2
        f = (1 - mid) if rear else mid
        w = cage.c.bw * cage.plan(f)
        if w < x:
            lo = mid
        else:
            hi = mid
    return hi * cage.c.L


def surf_slope(cage, x, rear=False):
    d0, d1 = nose_d(cage, x - 0.02, rear), nose_d(cage, x + 0.02, rear)
    return math.atan2(d1 - d0, 0.04)           # radians; the surface sweeps back with +x


def lamp_parts(c, cage, sx, x, y, w, h, kind="oval", depth=0.07):
    """Recessed housing (trim, chrome) + lens (headlight). Returns (housing MB, lens MB, origin)."""
    d = nose_d(cage, x)
    z = c.zF - d
    a = surf_slope(cage, x)
    fwd = Vector((math.sin(a) * sx, 0, math.cos(a)))
    O = Vector((sx * x, y, z + 0.012))
    hous, lens = MB(), MB()
    if kind == "oval":
        sc = (w / 2, h / 2)
        hous.lathe(O, fwd, [(1.12, -0.03), (1.12, 0.022), (0.99, 0.026), (0.99, -0.03)], 28, "trim", closed=True, scale=sc)
        hous.lathe(O, fwd, [(0.99, -0.02), (0.86, -depth * 0.8), (0.0, -depth)], 28, "trim", scale=sc, solid=False, flip=True)
        hous.lathe(O, fwd, [(0.62, -depth * 0.95), (0.55, -depth * 0.55), (0.30, -depth * 0.45), (0.0, -depth * 0.35)], 24, "chrome", scale=sc)
        lens.lathe(O, fwd, [(0.97, -0.004), (0.94, 0.012), (0.6, 0.026), (0.0, 0.03)], 28, "headlight", scale=sc)
    else:
        r = Matrix.Rotation(a * sx, 3, 'Y')
        t = 0.03
        for (dx, dy, sw_, sh_) in ((0, h / 2 + t / 2, w + 2 * t, t), (0, -h / 2 - t / 2, w + 2 * t, t),
                                   (w / 2 + t / 2, 0, t, h), (-w / 2 - t / 2, 0, t, h)):
            hous.box(O + r @ Vector((dx, dy, 0.004)), (sw_, sh_, 0.04), "trim", bevel=0.008, rot=r)
        hous.box(O + r @ Vector((0, 0, -depth)), (w, h, 0.02), "trim", rot=r)
        hous.box(O + r @ Vector((0, 0, -depth * 0.5)), (w * 0.82, h * 0.7, 0.012), "chrome", rot=r)
        lens.box(O + r @ Vector((0, 0, -0.012)), (w * 0.98, h * 0.98, 0.026), "headlight", bevel=0.008, rot=r)
    return hous, lens, tuple(O)


def mirror_node(c, cage, sx, f_m, y_m, big=1.0):
    """Mirror: arm + housing (paint) + glass face; the outer tip lands exactly on half the car width."""
    ring = cage.ring_half(f_m)
    z = c.zF - f_m * c.L
    x0 = ring[5][0] * 0.99
    mb = MB()
    sz = (0.15 * big, 0.17 * big, 0.23 * big)
    cx = c.hw - sz[0] / 2
    mb.pipe((sx * x0, y_m - 0.02, z), (sx * (cx - 0.04), y_m, z), 0.014, 6, "trim")
    mb.box((sx * (x0 + 0.02), y_m - 0.03, z), (0.07, 0.05, 0.12), "trim", bevel=0.01)
    mb.box((sx * cx, y_m + 0.02, z), (sz[0], sz[1], sz[2]), "paint", bevel=0.045)
    mb.box((sx * cx, y_m + 0.02, z - sz[2] / 2 + 0.003), (sz[0] * 0.8, sz[1] * 0.78, 0.012), "chrome", bevel=0.01)
    mb.box((sx * (cx + 0.035), y_m + 0.055, z + sz[2] / 2 - 0.02), (0.06, 0.035, 0.05), "taillight")
    return mb, (sx * x0, y_m, z)


# ------------------------------------------------------------------ bumpers
def bumper(c, cage, front, style):
    """Wrap-around bumper: ring loft following the plan-view nose/tail, then details."""
    sgn = 1 if front else -1
    depth = style.get("depth", 0.40)
    y0, y1 = style["y"]
    mb = MB()
    stations = 12
    rings = []
    zedge = c.zF if front else c.zR
    for i in range(stations + 1):
        t = i / stations
        d = t * depth
        f = d / c.L if front else 1 - d / c.L
        w = c.bw * cage.plan(f) * 1.012 + 0.012 * t
        zz = zedge - sgn * d
        tuck = style.get("tuck", 0.05) * (1 - t)
        pts = [(0.0, y0 + tuck), (w * 0.6, y0 + tuck * 0.6), (w * 0.93, y0 + 0.03), (w, y0 + 0.10), (w, y1 - 0.10),
               (w * 0.95, y1 - 0.02), (w * 0.6, y1 + 0.005), (0.0, y1 + 0.01)]
        half = [Vector((x, y, zz)) for x, y in pts]
        rings.append(half + [Vector((-p.x, p.y, p.z)) for p in reversed(half[1:-1])])
    mb.loft(rings, style.get("mat", "paint"), caps=True)
    return mb, (0.0, (y0 + y1) / 2, zedge - sgn * depth)


def bumper_details(c, front, style, mb):
    sgn = 1 if front else -1
    zedge = c.zF if front else c.zR
    y0, y1 = style["y"]
    zf = zedge - sgn * 0.02
    w = c.bw * 0.62
    mb.box((0, y0 + 0.10, zf), (w * 1.5, 0.11, 0.05), "trim", bevel=0.02)
    for k in range(4):
        mb.box((0, y0 + 0.075 + k * 0.026, zf + sgn * 0.012), (w * 1.46, 0.007, 0.012), "chrome")
    for sx in (1, -1):
        mb.box((sx * c.bw * 0.78, y0 + 0.11, zf), (0.14, 0.09, 0.05), "trim", bevel=0.02)
        mb.box((sx * c.bw * 0.78, y0 + 0.11, zf + sgn * 0.02), (0.09, 0.05, 0.02), "plate", bevel=0.01)
    plate_y = y1 - 0.13 if front else y1 - 0.11
    mb.box((0, plate_y, zf + sgn * 0.012), (0.52, 0.12, 0.012), "plate", bevel=0.004)      # blank plate
    mb.box((0, plate_y, zf + sgn * 0.003), (0.55, 0.15, 0.01), "trim", bevel=0.01)


# ------------------------------------------------------------------ assembly
def build_car(key, spec, root):
    c = make_ctx(key, spec)
    carparts.car_materials(spec)
    st = c.st
    cage_nodes = {n: MB() for n in ("body", "glass", "interior", "underside", "trim", "bonnet", "pillars")}
    info = build_cage(c, st, cage_nodes)
    cage = info["cage"]
    fs, rings = info["fs"], info["rings"]
    chrome, grille, tail = MB(), MB(), MB()
    ttrim = cage_nodes["trim"]

    for f in st["seams"]:
        i = min(range(len(fs)), key=lambda q: abs(fs[q] - f))
        seam_strip(ttrim, rings, i, 3, 9, width=0.012)
    DET[key](c, cage, ttrim, chrome, grille, tail)
    carparts.build_interior_parts(c, cage, st, cage_nodes["interior"])
    cage_nodes["underside"].merge(carparts.build_underside(c, cage, st))

    P = root
    sm = st["smooth"]
    for name in ("body", "glass", "trim", "interior", "underside", "pillars"):
        mbn = cage_nodes[name]
        if len(mbn.bm.faces) == 0:
            mbn.bm.free()
            continue
        mbn.to_object(name, parent=P, smooth=None if name == "glass" else sm)
    chrome.to_object("chrome", parent=P, smooth=sm)
    grille.to_object("grille", parent=P, smooth=sm)
    tail.to_object("taillights", parent=P, smooth=sm)
    hf = st["hinge_f"]
    ring_h = cage.ring_half(hf)
    cage_nodes["bonnet"].to_object("bonnet", origin=(0, ring_h[13][1], c.zF - hf * c.L), parent=P, smooth=sm)
    for name, sx, sz in (("fl", 1, 1), ("fr", -1, 1), ("rl", 1, -1), ("rr", -1, -1)):
        wm, org = carparts.build_wheel(c, sx, sz, st)
        wm.to_object("wheel_" + name, origin=org, parent=P, smooth=60)
        cm, org = carparts.build_caliper(c, sx, sz, st)
        cm.to_object("caliper_" + name, origin=org, parent=P, smooth=40)
    for name, (hous, lens, org) in c.lamps.items():
        lens.to_object(name, origin=org, parent=P, smooth=40)
    for nm, front in (("bumper_front", True), ("bumper_rear", False)):
        bs = c.bumper_style[nm]
        mb, org = bumper(c, cage, front, bs)
        det = MB()
        bumper_details(c, front, bs, det)
        mb.merge(det)
        mb.to_object(nm, origin=org, parent=P, smooth=sm)
    for nm, sx in (("mirror_l", 1), ("mirror_r", -1)):
        mb, org = mirror_node(c, cage, sx, *c.mirror, big=c.mirror_big)
        mb.to_object(nm, origin=org, parent=P, smooth=sm)
    fa = (st["side_glass"][0][0] + st["side_glass"][-1][1]) / 2
    ra = cage.ring_half(fa)
    empty("roof_anchor", (0, ra[13][1], c.zF - fa * c.L), P)
    return c


# ------------------------------------------------------------------ per-style details
def roof_rails(c, cage, mb, f0, f1, inset=0.82, mat="chrome"):
    for sx in (1, -1):
        pts = []
        n = 10
        for i in range(n + 1):
            f = f0 + (f1 - f0) * i / n
            r = cage.ring_half(f)
            pts.append(Vector((sx * r[10][0] * inset, r[11][1] + 0.014, c.zF - f * c.L)))
        for a, b in zip(pts[:-1], pts[1:]):
            mb.pipe(a, b, 0.016, 6, mat)
        for p in (pts[0], pts[len(pts) // 2], pts[-1]):
            mb.box(Vector((p.x, p.y - 0.014, p.z)), (0.05, 0.03, 0.07), "trim", bevel=0.01)


def door_handles(c, cage, chrome, fs, drop=0.10, sz=(0.03, 0.035, 0.16)):
    for f in fs:
        r = cage.ring_half(f)
        for sx in (1, -1):
            chrome.box((sx * (r[5][0] + 0.004), r[6][1] - drop, c.zF - f * c.L), sz, "chrome", bevel=0.01)


def wipers(c, cage, trim, f):
    r = cage.ring_half(f)
    z = c.zF - f * c.L
    y = r[6][1] + 0.02
    for sx, ln in ((1, 0.55), (-1, 0.5)):
        a = Vector((sx * 0.30, y, z - 0.01))
        e = Vector((a.x - sx * ln * 0.55, a.y + 0.10, a.z - ln * 0.50))
        trim.pipe(a, e, 0.007, 4, "trim")
        trim.pipe(e, e + Vector((-sx * ln * 0.45, 0.07, -ln * 0.45)), 0.009, 4, "rubber")


def tail_lamps(c, cage, tail, trim, kind, x_frac=0.8):
    for sx in (1, -1):
        x = c.bw * x_frac
        d = nose_d(cage, x, rear=True)
        z = c.zR + d
        yaw = surf_slope(cage, x, rear=True)
        rot = Matrix.Rotation(-sx * yaw, 3, 'Y')
        T = cage.T(1 - d / c.L)
        if kind == "tall":
            trim.box((sx * x, T - 0.42, z), (0.17, 0.5, 0.05), "trim", bevel=0.012, rot=rot)
            tail.box((sx * x, T - 0.42, z - 0.012), (0.13, 0.46, 0.03), "taillight", bevel=0.012, rot=rot)
        elif kind == "wrap":
            trim.box((sx * x, T - 0.34, z), (0.30, 0.20, 0.05), "trim", bevel=0.03, rot=rot)
            tail.box((sx * x, T - 0.34, z - 0.012), (0.27, 0.17, 0.03), "taillight", bevel=0.03, rot=rot)
            tail.box((sx * x, T - 0.26, z - 0.012), (0.27, 0.035, 0.03), "headlight", bevel=0.01, rot=rot)
        else:
            tail.box((sx * x * 0.62, T - 0.26, z - 0.01), (0.46, 0.05, 0.03), "taillight", bevel=0.012, rot=rot)
            trim.box((sx * x * 0.62, T - 0.26, z + 0.005), (0.50, 0.075, 0.03), "trim", bevel=0.012, rot=rot)
    if kind == "bar":
        tail.box((0, cage.T(0.985) - 0.26, c.zR + 0.15), (0.6, 0.05, 0.03), "taillight", bevel=0.012)


def exhaust_tips(c, chrome, x=0.34, y=None, dual=True, r=0.042):
    y = y if y is not None else c.gc + 0.30
    for sx in ((1, -1) if dual else (1,)):
        chrome.lathe((sx * x, y, c.zR + 0.04), (0, 0, -1), [(r, 0.0), (r, 0.12), (r * 0.82, 0.12), (r * 0.82, 0.02)], 16, "chrome", closed=True)


def beltline(c, cage, chrome, f0, f1, w=0.012):
    for sx in (1, -1):
        r = cage.ring_half(0.5)
        chrome.box((sx * (r[5][0] + 0.003), r[6][1] - 0.02, c.zF - (f0 + f1) / 2 * c.L), (w, 0.016, (f1 - f0) * c.L), "chrome")


def sills(c, cage, trim, f0, f1, dx=0.012, h=0.12, w=0.05):
    for sx in (1, -1):
        trim.box((sx * (c.bw + dx), cage.yb(0.5) + 0.05, c.zF - (f0 + f1) / 2 * c.L), (w, h, (f1 - f0) * c.L), "trim", bevel=0.02)


def det_escapade(c, cage, trim, chrome, grille, tail):
    zg = c.zF - nose_d(cage, 0.50)
    gy = 0.84
    chrome.box((0, gy, zg + 0.03), (1.06, 0.46, 0.06), "chrome", bevel=0.025)
    grille.box((0, gy, zg + 0.062), (0.94, 0.36, 0.02), "trim")
    for k in range(6):
        chrome.box((0, gy - 0.15 + k * 0.06, zg + 0.07), (0.94, 0.028, 0.03), "chrome", bevel=0.006)
    chrome.box((0, gy, zg + 0.072), (0.04, 0.36, 0.03), "chrome")
    c.lamps = {}
    for nm, sx in (("headlight_l", 1), ("headlight_r", -1)):
        h, l, o = lamp_parts(c, cage, sx, c.bw * 0.78, 0.90, 0.30, 0.26, kind="box", depth=0.06)
        trim.merge(h)
        c.lamps[nm] = (h, l, o)
    roof_rails(c, cage, chrome, 0.43, 0.91)
    door_handles(c, cage, chrome, (0.545, 0.78))
    wipers(c, cage, trim, 0.30)
    for sx in (1, -1):
        zc0, zc1 = c.zF - 0.39 * c.L, c.zF - 0.80 * c.L
        chrome.box((sx * (c.bw + 0.07), cage.yb(0.5) + 0.04, (zc0 + zc1) / 2), (0.012, 0.03, abs(zc0 - zc1)), "chrome")
        for fz in (0.44, 0.60, 0.76):
            trim.box((sx * (c.bw + 0.0), cage.yb(0.5) - 0.02, c.zF - fz * c.L), (0.05, 0.08, 0.05), "trim")
    sills(c, cage, trim, 0.39, 0.80, dx=0.015, w=0.11, h=0.045)
    beltline(c, cage, chrome, 0.30, 0.93)
    tail_lamps(c, cage, tail, trim, "tall", 0.80)
    exhaust_tips(c, chrome, 0.33, c.gc + 0.30, True, 0.045)
    c.mirror = (0.40, 1.28); c.mirror_big = 1.15
    c.bumper_style = {
        "bumper_front": dict(y=(0.30, 0.68), depth=0.44, mat="chrome", tuck=0.06),
        "bumper_rear": dict(y=(0.34, 0.70), depth=0.38, mat="chrome", tuck=0.05)}


def det_glug(c, cage, trim, chrome, grille, tail):
    zg = c.zF - nose_d(cage, 0.42)
    trim.box((0, 0.80, zg + 0.02), (0.86, 0.34, 0.06), "trim", bevel=0.10)
    for k in range(3):
        chrome.box((0, 0.74 + k * 0.065, zg + 0.052), (0.74, 0.03, 0.03), "chrome", bevel=0.008)
    c.lamps = {}
    for nm, sx in (("headlight_l", 1), ("headlight_r", -1)):
        h, l, o = lamp_parts(c, cage, sx, c.bw * 0.70, 0.90, 0.36, 0.22, kind="oval", depth=0.07)
        trim.merge(h)
        c.lamps[nm] = (h, l, o)
    roof_rails(c, cage, chrome, 0.50, 0.80, inset=0.80)
    door_handles(c, cage, chrome, (0.545, 0.74))
    wipers(c, cage, trim, 0.32)
    sills(c, cage, trim, 0.40, 0.82)
    beltline(c, cage, chrome, 0.30, 0.88)
    tail_lamps(c, cage, tail, trim, "wrap", 0.78)
    exhaust_tips(c, chrome, 0.30, c.gc + 0.31, True, 0.04)
    c.mirror = (0.46, 1.22); c.mirror_big = 1.0
    c.bumper_style = {
        "bumper_front": dict(y=(0.32, 0.72), depth=0.42, mat="paint", tuck=0.07),
        "bumper_rear": dict(y=(0.34, 0.74), depth=0.40, mat="paint", tuck=0.06)}


def det_genesips(c, cage, trim, chrome, grille, tail):
    zg = c.zF - nose_d(cage, 0.40)
    gy = 0.70
    wd, ht = 1.30, 0.17
    trim.box((0, gy, zg + 0.02), (wd, ht, 0.06), "trim", bevel=0.07)
    for k in (-1, 0, 1):
        chrome.box((0, gy + k * 0.05, zg + 0.052), (wd * 0.9, 0.016, 0.02), "chrome")
    c.lamps = {}
    for nm, sx in (("headlight_l", 1), ("headlight_r", -1)):
        h, l, o = lamp_parts(c, cage, sx, c.bw * 0.80, 0.86, 0.17, 0.24, kind="oval", depth=0.07)
        trim.merge(h)
        c.lamps[nm] = (h, l, o)
    door_handles(c, cage, chrome, (0.53, 0.70), drop=0.07, sz=(0.02, 0.025, 0.15))
    wipers(c, cage, trim, 0.325)
    sills(c, cage, trim, 0.42, 0.80, dx=0.004, w=0.04)
    beltline(c, cage, chrome, 0.33, 0.86, 0.01)
    rr = cage.ring_half(0.80)
    chrome.box((0, rr[13][1] + 0.025, c.zF - 0.72 * c.L), (0.04, 0.05, 0.16), "trim", bevel=0.012)
    tail_lamps(c, cage, tail, trim, "bar", 0.80)
    exhaust_tips(c, chrome, 0.38, c.gc + 0.29, True, 0.038)
    c.mirror = (0.45, 1.10); c.mirror_big = 0.95
    c.bumper_style = {
        "bumper_front": dict(y=(0.30, 0.66), depth=0.38, mat="paint", tuck=0.06),
        "bumper_rear": dict(y=(0.34, 0.74), depth=0.34, mat="paint", tuck=0.05)}


def det_rangeroller(c, cage, trim, chrome, grille, tail):
    zg = c.zF - nose_d(cage, 0.40)
    trim.box((0, 0.70, zg + 0.018), (0.80, 0.06, 0.04), "trim", bevel=0.015)
    c.lamps = {}
    for nm, sx in (("headlight_l", 1), ("headlight_r", -1)):
        h, l, o = lamp_parts(c, cage, sx, c.bw * 0.66, 0.92, 0.36, 0.085, kind="box", depth=0.05)
        trim.merge(h)
        c.lamps[nm] = (h, l, o)
    sills(c, cage, trim, 0.40, 0.93, dx=0.004, w=0.03, h=0.14)
    for sx in (1, -1):
        for f in (0.58, 0.80):
            rr = cage.ring_half(f)
            trim.box((sx * (rr[5][0] + 0.002), rr[6][1] - 0.06, c.zF - f * c.L), (0.012, 0.03, 0.14), "trim")
    wipers(c, cage, trim, 0.33)
    tail_lamps(c, cage, tail, trim, "bar", 0.80)
    exhaust_tips(c, chrome, 0.30, c.gc + 0.34, False, 0.0001)
    roof_rails(c, cage, trim, 0.46, 0.91, inset=0.85, mat="trim")
    c.mirror = (0.42, 1.30); c.mirror_big = 1.08
    c.bumper_style = {
        "bumper_front": dict(y=(0.36, 0.76), depth=0.36, mat="paint", tuck=0.05),
        "bumper_rear": dict(y=(0.38, 0.78), depth=0.34, mat="paint", tuck=0.05)}


DET = {"escapade_2009": det_escapade, "glug_2017": det_glug, "genesips_2021": det_genesips, "rangeroller_2026": det_rangeroller}


# ------------------------------------------------------------------ ambient occlusion into vertex colours
def bake_ao(skip=("glass", "headlight_l", "headlight_r"), samples=14, maxd=1.1):
    """Per-vertex ambient occlusion (cosine-weighted rays against the whole car plus a ground plane)."""
    from mathutils.bvhtree import BVHTree
    scene = bpy.context.scene
    verts, polys = [], []
    meshes = [o for o in scene.objects if o.type == 'MESH']
    for o in meshes:
        base = len(verts)
        mw = o.matrix_world
        verts += [mw @ v.co for v in o.data.vertices]
        polys += [tuple(base + i for i in p.vertices) for p in o.data.polygons]
    g = len(verts)
    verts += [Vector((-40, -40, -0.001)), Vector((40, -40, -0.001)), Vector((40, 40, -0.001)), Vector((-40, 40, -0.001))]
    polys.append((g, g + 1, g + 2, g + 3))
    bvh = BVHTree.FromPolygons(verts, polys)
    dirs = []
    for i in range(samples):
        u1, u2 = (i + 0.5) / samples, (i * 0.618034) % 1.0
        r = math.sqrt(u1)
        a = 2 * math.pi * u2
        dirs.append(Vector((r * math.cos(a), r * math.sin(a), math.sqrt(max(0.0, 1 - u1)))))
    for o in meshes:
        if o.name in skip:
            continue
        me = o.data
        rot = o.matrix_world.to_3x3()
        mw = o.matrix_world
        col = me.color_attributes.new("Col", 'FLOAT_COLOR', 'POINT')
        for v in me.vertices:
            n = (rot @ v.normal).normalized()
            t = n.cross(Vector((0.0, 0.0, 1.0)) if abs(n.z) < 0.9 else Vector((1.0, 0.0, 0.0))).normalized()
            b = n.cross(t)
            p = mw @ v.co + n * 0.006
            hit = 0.0
            for d in dirs:
                w = t * d.x + b * d.y + n * d.z
                loc, nor, idx, dist = bvh.ray_cast(p, w, maxd)
                if loc is not None:
                    hit += 1.0 - dist / maxd * 0.5
            ao = 1.0 - hit / samples
            val = 0.32 + 0.68 * ao ** 0.8
            col.data[v.index].color = (val, val, val, 1.0)
