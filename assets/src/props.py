"""Props: stein, lodge, table, trees, spectator, flag, tee marker, golf cart, ramp, sign, rock, drone.

Game frame throughout (+Y up, +Z forward/downhill). Each build_* creates its objects in a clean scene.
"""
import math, random
from mathutils import Vector, Matrix
from gtl import MB, make_mat, empty, bx, B


def _root(name):
    return empty(name)


# ----------------------------------------------------------------------------- stein
def build_stein():
    make_mat("glass", (0.92, 0.96, 1.0), rough=0.04, alpha=0.14)
    make_mat("lager", (0.98, 0.66, 0.05), rough=0.55, emit=(0.95, 0.5, 0.03), emit_strength=0.35)
    make_mat("foam", (0.98, 0.96, 0.90), rough=0.9)
    root = _root("stein")
    g = MB()
    prof = [(0, 0), (0.040, 0), (0.043, 0.012), (0.046, 0.04), (0.0475, 0.07), (0.0485, 0.10), (0.0495, 0.13),
            (0.0505, 0.16), (0.0515, 0.195), (0.0515, 0.2), (0.0465, 0.2), (0.0460, 0.19), (0.0435, 0.035),
            (0.036, 0.024), (0, 0.022)]
    dimple_rows = {3, 4, 5, 6, 7}

    def mod(pi, i):
        return 0.94 if (pi in dimple_rows and (i + pi) % 2 == 0) else 1.0
    g.lathe((0, 0, 0), (0, 1, 0), prof, 16, "glass", mod=mod)
    # handle: square section swept along a half ellipse on +X
    cx, cy, ax, ay = 0.045, 0.108, 0.052, 0.062
    path = [(cx + ax * math.cos(t), cy + ay * math.sin(t)) for t in
            [math.radians(a) for a in (100, 70, 40, 10, -20, -50, -80, -100)]]
    rings = []
    for i, (px, py) in enumerate(path):
        a, b = path[max(i - 1, 0)], path[min(i + 1, len(path) - 1)]
        t = Vector((b[0] - a[0], b[1] - a[1])).normalized()
        n = Vector((t.y, -t.x))
        w, d = 0.0085, 0.0075
        rings.append([Vector((px + n.x * s * w, py + n.y * s * w, z * d)) for s, z in ((1, 1), (1, -1), (-1, -1), (-1, 1))])
    g.loft(rings, "glass")
    g.lathe((0, 0, 0), (0, 1, 0), [(0, 0.025), (0.0365, 0.025), (0.0452, 0.150), (0, 0.150)], 16, "lager")
    g.lathe((0, 0, 0), (0, 1, 0), [(0, 0.150), (0.0453, 0.150), (0.0458, 0.172), (0.0452, 0.188), (0.026, 0.196),
                                    (0, 0.1985)], 16, "foam")
    g.to_object("stein_mesh", parent=root, smooth=60)


# ----------------------------------------------------------------------------- table
def build_table():
    make_mat("wood_top", (0.62, 0.42, 0.22), rough=0.8)
    make_mat("wood_dark", (0.33, 0.20, 0.10), rough=0.85)
    make_mat("cloth", (0.82, 0.12, 0.12), rough=0.95)
    root = _root("table")
    m = MB()
    top_y = 0.92
    for k in range(3):
        z = -0.30 + k * 0.30
        bx(m, -2.1, 2.1, top_y - 0.07, top_y, z - 0.148, z + 0.148, "wood_top", bevel=0.012)
    for sx in (-1, 1):
        x = sx * 1.7
        for sz in (-1, 1):
            bx(m, x - 0.05, x + 0.05, 0, top_y - 0.07, sz * 0.32 - 0.05, sz * 0.32 + 0.05, "wood_dark", bevel=0.01)
        bx(m, x - 0.06, x + 0.06, 0, 0.08, -0.45, 0.45, "wood_dark", bevel=0.01)
        bx(m, x - 0.05, x + 0.05, top_y - 0.17, top_y - 0.07, -0.40, 0.40, "wood_dark", bevel=0.01)
    bx(m, -1.7, 1.7, 0.30, 0.38, -0.025, 0.025, "wood_dark", bevel=0.01)
    # benches
    for sz in (-1, 1):
        zc = sz * 0.82
        bx(m, -2.0, 2.0, 0.46, 0.52, zc - 0.15, zc + 0.15, "wood_top", bevel=0.01)
        for sx in (-1, 1):
            bx(m, sx * 1.6 - 0.04, sx * 1.6 + 0.04, 0, 0.46, zc - 0.10, zc + 0.10, "wood_dark", bevel=0.008)
    m.to_object("table_mesh", parent=root, smooth=None)


# ----------------------------------------------------------------------------- trees
def build_tree_pine():
    make_mat("bark", (0.30, 0.19, 0.11), rough=0.95)
    make_mat("needles", (0.08, 0.30, 0.14), rough=0.9)
    root = _root("tree_pine")
    m = MB()
    m.lathe((0, 0, 0), (0, 1, 0), [(0.24, 0.0), (0.13, 2.4)], 6, "bark")
    tiers = [(2.5, 1.5, 3.4), (2.1, 3.0, 4.9), (1.7, 4.3, 6.2), (1.25, 5.5, 7.4), (0.8, 6.6, 8.4)]
    for i, (r, y0, y1) in enumerate(tiers):
        m.lathe((0.0, 0, 0), (0, 1, 0), [(r, y0), (r * 0.12, y1)], 8, "needles", phase=i * 0.4)
    m.to_object("tree_pine_mesh", parent=root, smooth=None)


def build_tree_broadleaf():
    make_mat("bark", (0.33, 0.22, 0.13), rough=0.95)
    make_mat("leaves", (0.20, 0.50, 0.14), rough=0.9)
    root = _root("tree_broadleaf")
    m = MB()
    m.lathe((0, 0, 0), (0, 1, 0), [(0.28, 0.0), (0.16, 2.9)], 5, "bark")
    m.ico((0, 4.3, 0), 2.3, "leaves", subdiv=2, scale=(1.0, 0.85, 1.0), jitter=0.10, seed=3)
    m.ico((1.1, 3.6, 0.4), 1.5, "leaves", subdiv=2, scale=(1, 0.85, 1), jitter=0.10, seed=5)
    m.ico((-1.0, 3.8, -0.5), 1.45, "leaves", subdiv=2, scale=(1, 0.85, 1), jitter=0.10, seed=9)
    m.to_object("tree_broadleaf_mesh", parent=root, smooth=None)


# ----------------------------------------------------------------------------- spectator
def build_spectator():
    make_mat("shirt", (0.85, 0.85, 0.88), rough=0.9)
    make_mat("trousers", (0.62, 0.55, 0.40), rough=0.9)
    make_mat("skin", (0.88, 0.64, 0.50), rough=0.8)
    make_mat("cap", (0.12, 0.30, 0.55), rough=0.8)
    make_mat("shoes", (0.18, 0.14, 0.11), rough=0.8)
    root = _root("spectator")
    m = MB()
    for sx in (-1, 1):
        bx(m, sx * 0.17 - 0.075, sx * 0.17 + 0.075, 0.08, 0.88, -0.08, 0.08, "trousers")
        bx(m, sx * 0.17 - 0.08, sx * 0.17 + 0.08, 0.0, 0.08, -0.10, 0.14, "shoes")
    m.box((0, 1.14, 0), (0.46, 0.56, 0.24), "shirt", bevel=0.05)
    for sx in (-1, 1):
        bx(m, sx * 0.30 - 0.05, sx * 0.30 + 0.05, 1.12, 1.40, -0.05, 0.05, "shirt")
        bx(m, sx * 0.31 - 0.045, sx * 0.31 + 0.045, 0.88, 1.12, -0.04, 0.05, "skin")
    m.lathe((0, 1.53, 0), (0, 1, 0), [(0, -0.10), (0.085, -0.05), (0.095, 0.03), (0.07, 0.09), (0, 0.11)], 7, "skin")
    m.lathe((0, 1.59, 0), (0, 1, 0), [(0.10, 0.0), (0.098, 0.05), (0.0, 0.075)], 8, "cap")
    bx(m, -0.09, 0.09, 1.585, 1.60, 0.07, 0.20, "cap")
    m.to_object("spectator_mesh", parent=root, smooth=None)


# ----------------------------------------------------------------------------- flag
def build_flag():
    make_mat("pole", (0.96, 0.95, 0.90), rough=0.5)
    make_mat("flag", (0.85, 0.10, 0.10), rough=0.8, double=True)
    root = _root("flag")
    m = MB()
    m.lathe((0, 0, 0), (0, 1, 0), [(0.06, 0.0), (0.06, 0.02), (0.012, 0.02), (0.011, 2.2)], 8, "pole")
    m.ico((0, 2.21, 0), 0.025, "pole", subdiv=1)
    # swallow-free pennant: three wave segments, height tapering to a point, hoisted on the pole
    top, hgt = 2.15, 0.34
    xs = [0.014, 0.19, 0.37, 0.55]
    zs = [0.0, 0.015, -0.015, 0.0]
    hs = [hgt, hgt * 0.68, hgt * 0.36, 0.0]
    for i in range(3):
        m.face([(xs[i], top, zs[i]), (xs[i + 1], top, zs[i + 1]), (xs[i + 1], top - hs[i + 1], zs[i + 1]),
                (xs[i], top - hs[i], zs[i])], "flag", hint=(0, 0, 1))
    m.to_object("flag_mesh", parent=root, smooth=None)


# ----------------------------------------------------------------------------- tee marker
def build_tee_marker():
    make_mat("marker", (0.95, 0.95, 0.95), rough=0.5)
    make_mat("peg", (0.55, 0.38, 0.20), rough=0.8)
    root = _root("tee_marker")
    m = MB()
    m.lathe((0, 0, 0), (0, 1, 0), [(0.0, -0.06), (0.018, 0.04), (0.022, 0.10)], 6, "peg")
    m.ico((0, 0.15, 0), 0.075, "marker", subdiv=2)
    m.to_object("tee_marker_mesh", parent=root, smooth=60)


# ----------------------------------------------------------------------------- ramp
def build_ramp():
    """Unit wedge per CONTRACT s3: 1 m long in +Z, 1 m wide (x in [-0.5, 0.5]), 1 m high at the far end.
    Origin on the ground at the centre of the low edge. The slope carries painted chevrons."""
    make_mat("ramp_plank", (0.66, 0.46, 0.24), rough=0.85)
    make_mat("ramp_chevron", (0.95, 0.78, 0.10), rough=0.7)
    make_mat("ramp_side", (0.36, 0.22, 0.11), rough=0.9)
    root = _root("ramp")
    m = MB()
    for sx in (-0.5, 0.5):
        m.face([(sx, 0, 0), (sx, 0, 1), (sx, 1, 1)], "ramp_side", hint=(sx * 2, 0, 0))
    m.face([(-0.5, 0, 1), (0.5, 0, 1), (0.5, 1, 1), (-0.5, 1, 1)], "ramp_side", hint=(0, 0, 1))
    m.face([(-0.5, 0, 0), (0.5, 0, 0), (0.5, 0, 1), (-0.5, 0, 1)], "ramp_side", hint=(0, -1, 0))
    n, s = 6, 0.22          # bands, chevron depth

    def line(i, ax):        # z of chevron line i at |x| = ax
        return i / n * (1 - s) + s * (1 - 2 * ax)

    def P(x, z):
        return (x, z, z)    # slope plane: y = z
    for sx in (1, -1):
        m.face([P(0, 0), P(sx * 0.5, 0), P(0, s)] if sx > 0 else [P(0, 0), P(0, s), P(-0.5, 0)], "ramp_plank", hint=(0, 1, -1))
        for i in range(n):
            mn = "ramp_chevron" if i % 2 == 0 else "ramp_plank"
            m.face([P(0, line(i, 0)), P(sx * 0.5, line(i, 0.5)), P(sx * 0.5, line(i + 1, 0.5)), P(0, line(i + 1, 0))],
                   mn, hint=(0, 1, -1))
        tm = "ramp_chevron" if n % 2 == 0 else "ramp_plank"
        m.face([P(0, 1), P(sx * 0.5, 1 - s), P(sx * 0.5, 1)], tm, hint=(0, 1, -1))
    m.to_object("ramp_mesh", parent=root, smooth=None)


# ----------------------------------------------------------------------------- sign
def build_sign():
    make_mat("board", (0.96, 0.96, 0.94), rough=0.6)
    make_mat("frame", (0.25, 0.27, 0.30), metallic=0.6, rough=0.5)
    root = _root("sign")
    m = MB()
    for sx in (-1, 1):
        bx(m, sx * 1.35 - 0.05, sx * 1.35 + 0.05, 0, 1.9, -0.05, 0.05, "frame", bevel=0.01)
    bx(m, -1.6, 1.6, 0.85, 1.95, -0.03, 0.03, "frame", bevel=0.015)
    bx(m, -1.52, 1.52, 0.92, 1.88, 0.03, 0.045, "board")
    m.to_object("sign_mesh", parent=root, smooth=None)


# ----------------------------------------------------------------------------- rock
def build_rock():
    make_mat("rock", (0.50, 0.49, 0.47), rough=0.95)
    root = _root("rock")
    m = MB()
    m.ico((0, 0.55, 0), 1.0, "rock", subdiv=3, scale=(1.15, 0.75, 0.9), jitter=0.16, seed=11, ymin=0.0)
    m.to_object("rock_mesh", parent=root, smooth=None)


# ----------------------------------------------------------------------------- golf cart
def build_golf_cart():
    make_mat("cart_body", (0.93, 0.93, 0.90), rough=0.45)
    make_mat("cart_trim", (0.12, 0.13, 0.14), rough=0.7)
    make_mat("seat", (0.80, 0.72, 0.55), rough=0.9)
    make_mat("glass", (0.55, 0.72, 0.82), rough=0.05, alpha=0.4)
    make_mat("tyre", (0.05, 0.05, 0.055), rough=0.92)
    make_mat("rim", (0.72, 0.74, 0.77), metallic=0.9, rough=0.35)
    make_mat("bag", (0.13, 0.30, 0.55), rough=0.85)
    make_mat("club", (0.75, 0.77, 0.80), metallic=0.9, rough=0.3)
    root = _root("golf_cart")
    m = MB()
    # chassis and floor
    bx(m, -0.56, 0.56, 0.16, 0.30, -1.05, 1.15, "cart_trim", bevel=0.03)
    # front cowl and rear body
    m.box((0, 0.52, 0.78), (1.10, 0.46, 0.80), "cart_body", bevel=0.08)
    m.box((0, 0.50, -0.78), (1.10, 0.42, 0.60), "cart_body", bevel=0.08)
    bx(m, -0.56, 0.56, 0.18, 0.40, 1.10, 1.22, "cart_trim", bevel=0.02)
    bx(m, -0.56, 0.56, 0.18, 0.40, -1.12, -1.02, "cart_trim", bevel=0.02)
    # seat bench and back
    bx(m, -0.50, 0.50, 0.42, 0.54, -0.50, 0.12, "seat", bevel=0.03)
    m.box((0, 0.82, -0.52), (1.0, 0.50, 0.10), "seat", bevel=0.03, rot=Matrix.Rotation(math.radians(-8), 3, 'X'))
    # dash, steering wheel
    m.box((0, 0.98, 0.50), (1.0, 0.36, 0.10), "cart_body", bevel=0.04)
    m.lathe((0.25, 1.0, 0.36), (0, 0.5, -0.8), [(0.11, -0.012), (0.11, 0.012), (0.095, 0.012), (0.095, -0.012)], 12, "cart_trim", closed=True)
    m.pipe((0.25, 0.92, 0.46), (0.25, 1.0, 0.36), 0.018, 6, "cart_trim")
    # windscreen frame and glass
    for sx in (-1, 1):
        m.pipe((sx * 0.50, 1.04, 0.46), (sx * 0.50, 1.80, 0.36), 0.022, 6, "cart_trim")
        m.pipe((sx * 0.50, 0.92, -1.0), (sx * 0.50, 1.80, -1.0), 0.022, 6, "cart_trim")
    m.face([(-0.48, 1.08, 0.455), (0.48, 1.08, 0.455), (0.48, 1.78, 0.365), (-0.48, 1.78, 0.365)], "glass", hint=(0, 0.1, 1))
    # roof
    m.box((0, 1.84, -0.30), (1.20, 0.07, 1.90), "cart_body", bevel=0.025)
    # rear bag rack with a golf bag and clubs
    bx(m, -0.50, 0.50, 0.70, 0.76, -1.10, -0.64, "cart_trim")
    m.lathe((0, 1.10, -0.95), (0, 0.2, -1.0), [(0.15, -0.45), (0.17, 0.20), (0.15, 0.45)], 8, "bag")
    for i, ox in enumerate((-0.07, 0.0, 0.07)):
        m.pipe((ox, 1.40, -1.04 + ox * 0.5), (ox * 1.5, 1.72, -1.16), 0.011, 5, "club")
    # wheels
    for sx in (-1, 1):
        for z in (0.78, -0.72):
            x = sx * 0.58
            m.lathe((x, 0.23, z), (sx, 0, 0), [(0.23, -0.085), (0.23, 0.085), (0.18, 0.1), (0.0, 0.09)], 14, "tyre")
            m.lathe((x, 0.23, z), (sx, 0, 0), [(0.0, 0.1), (0.13, 0.095), (0.13, 0.07), (0.0, 0.07)], 10, "rim")
    # headlights (plain, not game-animated)
    for sx in (-1, 1):
        bx(m, sx * 0.38 - 0.08, sx * 0.38 + 0.08, 0.52, 0.62, 1.17, 1.20, "seat")
    m.to_object("golf_cart_mesh", parent=root, smooth=None)


# ----------------------------------------------------------------------------- drone
def build_drone():
    make_mat("drone_body", (0.16, 0.17, 0.19), rough=0.5)
    make_mat("drone_trim", (0.85, 0.85, 0.88), rough=0.5)
    make_mat("rotor", (0.07, 0.07, 0.08), rough=0.6)
    make_mat("lens", (0.10, 0.18, 0.35), metallic=0.5, rough=0.1)
    make_mat("led_green", (0.1, 1.0, 0.2), emit=(0.1, 1.0, 0.2), emit_strength=1.0)
    make_mat("led_red", (1.0, 0.1, 0.1), emit=(1.0, 0.1, 0.1), emit_strength=1.0)
    root = _root("drone")
    m = MB()
    m.box((0, 0, 0), (0.12, 0.05, 0.16), "drone_body", bevel=0.012)
    bx(m, -0.04, 0.04, 0.025, 0.036, -0.05, 0.05, "drone_trim")
    # arms and motors
    hubs = {}
    for name, sx, sz in (("rotor_fl", 1, 1), ("rotor_fr", -1, 1), ("rotor_rl", 1, -1), ("rotor_rr", -1, -1)):
        tip = Vector((sx * 0.17, 0.012, sz * 0.17))
        m.pipe((sx * 0.04, 0.0, sz * 0.04), tip, 0.010, 5, "drone_body")
        m.lathe(tip, (0, 1, 0), [(0.018, -0.012), (0.018, 0.016)], 6, "drone_trim")
        hubs[name] = tip + Vector((0, 0.022, 0))
    # camera gimbal
    m.ico((0, -0.04, 0.085), 0.034, "drone_body", subdiv=1)
    m.lathe((0, -0.04, 0.105), (0, 0, 1), [(0.0, 0.0), (0.022, 0.0), (0.022, 0.02), (0.0, 0.02)], 8, "lens")
    # skids
    for sx in (-1, 1):
        m.pipe((sx * 0.06, -0.025, 0.05), (sx * 0.06, -0.075, 0.07), 0.006, 4, "drone_trim")
        m.pipe((sx * 0.06, -0.075, 0.07), (sx * 0.06, -0.075, -0.07), 0.006, 4, "drone_trim")
        m.pipe((sx * 0.06, -0.075, -0.07), (sx * 0.06, -0.025, -0.05), 0.006, 4, "drone_trim")
    bx(m, -0.012, 0.012, 0.0, 0.012, 0.08, 0.09, "led_green")
    bx(m, -0.012, 0.012, 0.0, 0.012, -0.09, -0.08, "led_red")
    m.to_object("drone_body", parent=root, smooth=None)
    for name, hub in hubs.items():
        r = MB()
        r.box((hub.x, hub.y, hub.z), (0.26, 0.004, 0.022), "rotor")
        r.lathe(hub, (0, 1, 0), [(0.012, -0.004), (0.012, 0.008)], 6, "drone_trim")
        r.to_object(name, origin=tuple(hub), parent=root, smooth=None)


# ----------------------------------------------------------------------------- lodge
def build_lodge():
    from lodge import build as _b
    _b()
