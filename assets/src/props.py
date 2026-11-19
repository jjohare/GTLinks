"""Props: stein, lodge, table, trees, spectator, flag, tee marker, golf cart, ramp, sign, rock, drone.

Game frame throughout (+Y up, +Z forward/downhill). Each build_* creates its objects in a clean scene.
Shared geometry helpers (tapered limbs, swept tubes, lobed foliage, clubs) live in propkit.py.
"""
import math, random
from mathutils import Vector, Matrix
from gtl import MB, make_mat, empty, bx, B
from propkit import basis, limb, tube, ring_pts, loft_mat, blob, dome, ik2, club


def _root(name):
    return empty(name)


# ----------------------------------------------------------------------------- stein
def build_stein():
    make_mat("glass", (0.92, 0.96, 1.0), rough=0.04, alpha=0.14)
    make_mat("lager", (0.98, 0.66, 0.05), rough=0.55, emit=(0.95, 0.5, 0.03), emit_strength=0.35)
    make_mat("foam", (0.98, 0.96, 0.90), rough=0.9)
    root = _root("stein")
    g = MB()
    # thick-bottomed barrel mug: heavy base, pressed rows of dimples, flared rolled lip
    prof = [(0, 0), (0.038, 0), (0.043, 0.006), (0.044, 0.016), (0.0455, 0.040), (0.0475, 0.070), (0.0485, 0.100),
            (0.0495, 0.130), (0.0505, 0.160), (0.0515, 0.190), (0.0525, 0.198), (0.0480, 0.200), (0.0462, 0.190),
            (0.0438, 0.036), (0.036, 0.026), (0, 0.024)]
    dimple_rows = {3, 4, 5, 6, 7, 8}

    def mod(pi, i):
        if pi in dimple_rows:
            return 0.865 if (i + pi) % 2 == 0 else 1.015       # deep dimple, slightly proud boss
        return 1.0
    g.lathe((0, 0, 0), (0, 1, 0), prof, 20, "glass", mod=mod)
    # handle: square section swept along a half ellipse on +X, with a thumb lift on the top attachment
    cx, cy, ax, ay = 0.045, 0.108, 0.054, 0.066
    path = [(cx + ax * math.cos(t), cy + ay * math.sin(t)) for t in
            [math.radians(a) for a in (104, 78, 52, 26, 0, -26, -52, -78, -104)]]
    rings = []
    for i, (px, py) in enumerate(path):
        a, b = path[max(i - 1, 0)], path[min(i + 1, len(path) - 1)]
        t = Vector((b[0] - a[0], b[1] - a[1])).normalized()
        n = Vector((t.y, -t.x))
        w, d = 0.0090, 0.0078
        k = 1.0 + 0.25 * math.sin(math.pi * i / (len(path) - 1))      # bulges at mid handle
        rings.append([Vector((px + n.x * s * w * k, py + n.y * s * w * k, z * d * k)) for s, z in ((1, 1), (1, -1), (-1, -1), (-1, 1))])
    g.loft(rings, "glass")
    bx(g, 0.052, 0.078, 0.178, 0.188, -0.0045, 0.0045, "glass")      # thumb rest
    g.lathe((0, 0, 0), (0, 1, 0), [(0, 0.026), (0.0365, 0.026), (0.0452, 0.150), (0, 0.150)], 20, "lager")
    g.lathe((0, 0, 0), (0, 1, 0), [(0, 0.150), (0.0453, 0.150), (0.0460, 0.168), (0.0456, 0.184), (0.0300, 0.192),
                                    (0, 0.1945)], 20, "foam")
    for k in range(7):                                                  # froth bubbles proud of the head
        a = k * 2.4
        r = 0.010 + 0.016 * (k % 3) / 3.0
        blob(g, (r * math.cos(a), 0.1935, r * math.sin(a)), (0.0085, 0.0055, 0.0085), "foam", subdiv=1)
    g.to_object("stein_mesh", parent=root, smooth=60)


# ----------------------------------------------------------------------------- table
def build_table():
    make_mat("wood_top", (0.62, 0.42, 0.22), rough=0.8)
    make_mat("wood_mid", (0.56, 0.37, 0.19), rough=0.82)
    make_mat("wood_dark", (0.33, 0.20, 0.10), rough=0.85)
    make_mat("cloth", (0.82, 0.12, 0.12), rough=0.95)
    make_mat("bolt", (0.55, 0.56, 0.58), metallic=0.8, rough=0.45)
    root = _root("table")
    m = MB()
    top_y = 0.92
    # 3 planks (4.2 x 0.9 m top), end-grain cleats, two bearers underneath
    for k in range(3):
        z = -0.30 + k * 0.30
        bx(m, -2.1, 2.1, top_y - 0.07, top_y, z - 0.148, z + 0.148, "wood_top" if k % 2 == 0 else "wood_mid", bevel=0.012)
    for sx in (-1, 1):
        bx(m, sx * 1.9 - 0.045, sx * 1.9 + 0.045, top_y - 0.115, top_y - 0.07, -0.44, 0.44, "wood_dark", bevel=0.008)
    for sx in (-1, 1):
        x = sx * 1.7
        # trestle: splayed pair of legs, foot rail, top bearer, tie bar
        for sz in (-1, 1):
            a = Vector((x, top_y - 0.07, sz * 0.26))
            b = Vector((x, 0.04, sz * 0.36))
            m.pipe(a, b, 0.045, 4, "wood_dark")
            m.box((x, 0.03, sz * 0.36), (0.12, 0.06, 0.12), "wood_dark", bevel=0.01)
            m.lathe((x - 0.052, top_y - 0.17, sz * 0.27), (1, 0, 0), [(0.011, 0), (0.011, 0.004), (0.0, 0.004)], 6, "bolt")
        bx(m, x - 0.06, x + 0.06, 0, 0.07, -0.46, 0.46, "wood_dark", bevel=0.01)
        bx(m, x - 0.05, x + 0.05, top_y - 0.17, top_y - 0.07, -0.34, 0.34, "wood_dark", bevel=0.01)
    bx(m, -1.7, 1.7, 0.30, 0.38, -0.025, 0.025, "wood_dark", bevel=0.01)            # tie bar
    # diagonal bracing under the top
    m.pipe((-1.7, 0.34, 0.0), (-1.0, top_y - 0.09, 0.0), 0.022, 4, "wood_dark")
    m.pipe((1.7, 0.34, 0.0), (1.0, top_y - 0.09, 0.0), 0.022, 4, "wood_dark")
    # benches: plank seat, apron, splayed legs, foot rail
    for sz in (-1, 1):
        zc = sz * 0.82
        bx(m, -2.0, 2.0, 0.46, 0.52, zc - 0.15, zc + 0.15, "wood_top", bevel=0.01)
        bx(m, -1.9, 1.9, 0.40, 0.46, zc - 0.03, zc + 0.03, "wood_dark", bevel=0.006)
        for sx in (-1, 1):
            for so in (-1, 1):                                                         # legs splay outwards
                m.pipe((sx * 1.6, 0.46, zc + so * 0.08), (sx * 1.6, 0.0, zc + so * 0.12), 0.04, 4, "wood_dark")
        bx(m, -1.6, 1.6, 0.17, 0.21, zc - 0.015, zc + 0.015, "wood_dark")
    # screw heads in the planks (a line of six per end)
    for sx in (-1, 1):
        for k in range(3):
            z = -0.30 + k * 0.30
            m.lathe((sx * 2.04, top_y, z), (0, 1, 0), [(0.013, 0.0), (0.013, 0.003), (0, 0.003)], 6, "bolt")
    m.to_object("table_mesh", parent=root, smooth=None)


# ----------------------------------------------------------------------------- trees
def build_tree_pine():
    make_mat("bark", (0.30, 0.19, 0.11), rough=0.95)
    make_mat("needles", (0.08, 0.30, 0.14), rough=0.9)
    root = _root("tree_pine")
    m = MB()
    rnd = random.Random(4)
    # slightly leaning, flared trunk
    ys = [0.0, 0.35, 1.6, 3.6, 5.8, 7.4, 8.0]
    tube(m, [(0.05 * y * 0.12, y, 0.03 * y * 0.1) for y in ys], [0.30, 0.22, 0.17, 0.12, 0.08, 0.04, 0.008], 6, "bark")
    # ten drooping skirts of needles, widest low, plus short branch stubs showing between them
    nt = 10
    for i in range(nt):
        f = i / (nt - 1)
        y = 1.5 + f * 5.9
        R = 2.35 * (1 - f) ** 0.92 + 0.30
        h = 1.10 - 0.35 * f
        cx, cz = 0.05 * y * 0.12 + rnd.uniform(-0.05, 0.05), 0.03 * y * 0.1 + rnd.uniform(-0.05, 0.05)
        prof = [(0, y + h), (0.50 * R, y + h * 0.42), (R, y - 0.05), (0.58 * R, y - 0.26), (0, y - 0.12)]
        dome(m, (cx, 0, cz), prof, 8, "needles", jit=0.12, seed=40 + i, sag=0.12, phase=i * 0.55)
    for i in range(6):
        y = 1.8 + i * 0.85
        a = i * 2.4
        p0 = Vector((0.05 * y * 0.12, y, 0.03 * y * 0.1))
        limb(m, p0, p0 + Vector((math.cos(a) * 0.55, 0.10, math.sin(a) * 0.55)), 0.045, 0.015, 4, "bark")
    m.to_object("tree_pine_mesh", parent=root, smooth=None)


def build_tree_broadleaf():
    make_mat("bark", (0.33, 0.22, 0.13), rough=0.95)
    make_mat("leaves", (0.20, 0.50, 0.14), rough=0.9)
    root = _root("tree_broadleaf")
    m = MB()
    # buttressed trunk that forks into three limbs carrying the crown
    tube(m, [(0, 0, 0), (0.02, 0.4, 0.0), (0.0, 1.3, 0.02), (-0.02, 2.2, 0.0), (0.0, 2.9, 0.0)],
         [0.40, 0.29, 0.22, 0.19, 0.16], 6, "bark")
    forks = [(0.95, 3.6, 0.35), (-0.85, 3.8, -0.45), (0.1, 4.6, 0.0)]
    for fx, fy, fz in forks:
        tube(m, [(0.0, 2.7, 0.0), (fx * 0.5, (2.7 + fy) / 2, fz * 0.5), (fx, fy, fz)], [0.13, 0.10, 0.05], 4, "bark")
    # layered crown: skirt of four, mid ring of three, cap
    sk = [(1.35, 3.55, 0.35, 1.45), (-1.25, 3.7, -0.45, 1.40), (0.30, 3.45, -1.40, 1.35), (-0.20, 3.55, 1.50, 1.30)]
    mid = [(0.95, 4.65, -0.60, 1.55), (-0.95, 4.75, 0.35, 1.50), (0.1, 4.55, 1.05, 1.40)]
    cap = [(0.0, 5.75, -0.10, 1.40)]
    for k, (x, y, z, r) in enumerate(sk + mid + cap):
        blob(m, (x, y, z), (r, r * 0.80, r), "leaves", subdiv=2, jitter=0.11, seed=30 + k)
    m.to_object("tree_broadleaf_mesh", parent=root, smooth=None)


# ----------------------------------------------------------------------------- spectator
def build_spectator():
    make_mat("shirt", (0.85, 0.85, 0.88), rough=0.9)
    make_mat("trousers", (0.62, 0.55, 0.40), rough=0.9)
    make_mat("skin", (0.88, 0.64, 0.50), rough=0.8)
    make_mat("cap", (0.12, 0.30, 0.55), rough=0.8)
    make_mat("shoes", (0.18, 0.14, 0.11), rough=0.8)
    make_mat("sole", (0.60, 0.58, 0.54), rough=0.9)
    make_mat("belt", (0.12, 0.08, 0.06), rough=0.7)
    make_mat("hair", (0.28, 0.18, 0.10), rough=0.95)
    make_mat("eye", (0.05, 0.05, 0.06), rough=0.4)
    root = _root("spectator")
    m = MB()
    V = Vector
    # legs: thigh + shin with a knee break, shoe with a separate sole
    for sx in (-1, 1):
        hip, knee, ank = V((sx * 0.095, 0.90, 0.0)), V((sx * 0.105, 0.50, 0.012)), V((sx * 0.105, 0.095, 0.0))
        limb(m, hip, knee, 0.083, 0.068, 5, "trousers")
        limb(m, knee, ank, 0.068, 0.058, 5, "trousers")
        bx(m, sx * 0.105 - 0.052, sx * 0.105 + 0.052, 0.022, 0.095, -0.085, 0.15, "shoes")
        bx(m, sx * 0.105 - 0.056, sx * 0.105 + 0.056, 0.0, 0.022, -0.095, 0.16, "sole")
    # torso: trousers -> belt -> shirt, shoulders -> neck
    ts = [(0.86, 0.0, 0.0, 0.160, 0.105), (0.985, 0.0, 0.0, 0.152, 0.100), (1.035, 0.0, 0.0, 0.152, 0.100),
          (1.30, 0.0, 0.0, 0.195, 0.120), (1.43, 0.0, 0.0, 0.225, 0.120), (1.50, 0.0, 0.0, 0.075, 0.075)]
    rings = [ring_pts((cx, y, cz), rx, rz, 8, phase=math.pi / 8) for y, cx, cz, rx, rz in ts]
    loft_mat(m, rings, lambda i, j: "trousers" if i == 0 else ("belt" if i == 1 else "shirt"))
    bx(m, -0.022, 0.022, 0.99, 1.03, 0.098, 0.108, "sole")                      # buckle
    bx(m, 0.04, 0.12, 1.20, 1.28, 0.118, 0.126, "shirt")                         # chest pocket
    limb(m, (0, 1.49, 0), (0, 1.60, 0.004), 0.045, 0.040, 5, "skin")
    limb(m, (0, 1.47, 0), (0, 1.52, 0.002), 0.068, 0.058, 5, "shirt")           # collar
    # head and face blocks, hair showing under the cap
    hc = V((0, 1.69, 0.004))
    bx(m, -0.074, 0.074, hc.y - 0.050, hc.y + 0.090, hc.z - 0.085, hc.z + 0.080, "skin")
    bx(m, -0.056, 0.056, hc.y - 0.095, hc.y - 0.040, hc.z - 0.055, hc.z + 0.078, "skin")
    bx(m, -0.016, 0.016, hc.y - 0.050, hc.y + 0.012, hc.z + 0.078, hc.z + 0.104, "skin")
    for sx in (-1, 1):
        bx(m, sx * 0.038 - 0.010, sx * 0.038 + 0.010, hc.y + 0.020, hc.y + 0.040, hc.z + 0.079, hc.z + 0.085, "eye")
        bx(m, sx * 0.074, sx * 0.084, hc.y - 0.020, hc.y + 0.030, hc.z - 0.030, hc.z + 0.012, "skin")
    bx(m, -0.070, 0.070, hc.y - 0.020, hc.y + 0.060, hc.z - 0.108, hc.z - 0.070, "hair")
    m.lathe((0, hc.y + 0.068, hc.z), (0, 1, 0), [(0.097, 0.0), (0.102, 0.030), (0.082, 0.070), (0, 0.092)], 8, "cap")
    m.box((0, hc.y + 0.074, hc.z + 0.118), (0.152, 0.010, 0.095), "cap", rot=Matrix.Rotation(0.22, 3, 'X'))
    # folded arms: upper arms hang, forearms cross the chest, hands tucked under the biceps
    for sx, ye in ((1, 1.20), (-1, 1.12)):
        sh = V((sx * 0.222, 1.40, 0.0))
        el = V((sx * 0.245, 1.13, 0.045))
        hd = V((-sx * 0.115, ye, 0.158))
        limb(m, sh, el, 0.060, 0.048, 5, "shirt")
        mid = el + (hd - el) * 0.55
        limb(m, el, mid, 0.048, 0.042, 5, "shirt")
        limb(m, mid, hd, 0.040, 0.034, 5, "skin")
        m.box(hd, (0.07, 0.055, 0.075), "skin")
    m.to_object("spectator_mesh", parent=root, smooth=None)


# ----------------------------------------------------------------------------- flag
def build_flag():
    make_mat("pole", (0.96, 0.95, 0.90), rough=0.5)
    make_mat("band", (0.95, 0.78, 0.10), rough=0.5)
    make_mat("metal", (0.62, 0.64, 0.68), metallic=0.9, rough=0.3)
    make_mat("cup", (0.94, 0.94, 0.92), rough=0.6)
    make_mat("hole", (0.02, 0.02, 0.025), rough=1.0)
    make_mat("flag", (0.85, 0.10, 0.10), rough=0.8, double=True)
    make_mat("flag_stripe", (0.96, 0.95, 0.92), rough=0.8, double=True)
    root = _root("flag")
    m = MB()
    # hole liner: rim ring around a dark well, with the steel ferrule sitting in it
    m.lathe((0, 0, 0), (0, 1, 0), [(0.0, 0.0), (0.060, 0.0), (0.060, 0.010), (0.054, 0.014), (0.054, 0.010), (0.0, 0.010)], 16, "cup")
    m.lathe((0, 0, 0), (0, 1, 0), [(0.0, 0.0), (0.054, 0.0), (0.054, 0.0105), (0.0, 0.0105)], 16, "hole")
    m.lathe((0, 0, 0), (0, 1, 0), [(0.0, 0.0), (0.011, 0.0), (0.0125, 0.012), (0.0125, 0.11), (0.0135, 0.118), (0.0135, 0.15),
                                    (0.0115, 0.16)], 8, "metal")
    # tapered stick with a yellow band at the top and a bright cap
    m.lathe((0, 0, 0), (0, 1, 0), [(0.0115, 0.160), (0.0112, 0.60), (0.0102, 1.40), (0.0095, 2.08), (0.0100, 2.18),
                                    (0.0, 2.19)], 8, "pole")
    m.lathe((0, 0, 0), (0, 1, 0), [(0.0125, 1.98), (0.0125, 2.18), (0.0, 2.18)], 8, "band")
    m.ico((0, 2.205, 0), 0.026, "metal", subdiv=2)
    for y in (2.12, 1.84):                                                                         # cloth grommets
        m.lathe((0.015, y, 0), (0, 0, 1), [(0.011, -0.004), (0.011, 0.004), (0.006, 0.004), (0.006, -0.004)], 8, "metal", closed=True)
    # fluttering pennant: 10 columns x 3 rows, travelling wave that grows toward the fly end, swallow-free taper
    cols, rows = 10, 3
    x0, L, top, H0 = 0.016, 0.62, 2.12, 0.34
    grid = []
    for i in range(cols + 1):
        u = i / cols
        x = x0 + L * u
        h = H0 * (1.0 - 0.45 * u)
        amp = 0.060 * u ** 1.1 + 0.004
        zz = amp * math.sin(u * 7.2) + 0.012 * math.sin(u * 3.1)
        sag = 0.045 * u * u
        col = [(x - 0.03 * u * u, top - sag - h * r / rows, zz + 0.012 * math.sin(u * 5.0 + r * 1.3)) for r in range(rows + 1)]
        grid.append(col)
    for i in range(cols):
        for r in range(rows):
            quad = [grid[i][r], grid[i + 1][r], grid[i + 1][r + 1], grid[i][r + 1]]
            m.face(quad, "flag_stripe" if r == 1 else "flag", hint=(0, 0, 1))
    m.to_object("flag_mesh", parent=root, smooth=None)


# ----------------------------------------------------------------------------- tee marker
def build_tee_marker():
    make_mat("marker", (0.95, 0.95, 0.95), rough=0.5)
    make_mat("marker_band", (0.85, 0.15, 0.12), rough=0.55)
    make_mat("peg", (0.55, 0.38, 0.20), rough=0.8)
    root = _root("tee_marker")
    m = MB()
    # driven stake: tapered, with a flared head and two grip notches, then a seat cup for the ball
    m.lathe((0, 0, 0), (0, 1, 0), [(0.0, -0.08), (0.012, -0.06), (0.022, 0.02), (0.020, 0.040), (0.024, 0.046),
                                    (0.020, 0.052), (0.020, 0.066), (0.026, 0.072), (0.038, 0.074), (0.0, 0.074)], 8, "peg")
    # the marker ball is a faceted sphere with a coloured equatorial band
    m.ico((0, 0.150, 0), 0.075, "marker", subdiv=3)
    m.lathe((0, 0.150, 0), (0, 1, 0), [(0.0780, -0.015), (0.0780, 0.015), (0.0765, 0.015), (0.0765, -0.015)], 16, "marker_band", closed=True)
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
    make_mat("bolt", (0.62, 0.64, 0.68), metallic=0.85, rough=0.35)
    root = _root("sign")
    m = MB()
    for sx in (-1, 1):
        x = sx * 1.35
        bx(m, x - 0.05, x + 0.05, 0.0, 1.9, -0.05, 0.05, "frame", bevel=0.01)
        bx(m, x - 0.075, x + 0.075, 0.0, 0.05, -0.075, 0.075, "frame", bevel=0.01)                    # ground plate
        bx(m, x - 0.06, x + 0.06, 1.90, 1.93, -0.06, 0.06, "frame", bevel=0.01)                      # cap
        # diagonal brace to the rear
        m.pipe((x, 0.20, -0.04), (x, 0.95, -0.30), 0.016, 5, "frame")
        m.pipe((x, 0.95, -0.30), (x, 0.20, -0.52), 0.016, 5, "frame")
        for y in (0.92, 1.78):                                                                       # bolts through the posts
            m.lathe((x, y, 0.055), (0, 0, 1), [(0.016, 0.0), (0.016, 0.008), (0.0, 0.008)], 6, "bolt")
    bx(m, -1.6, 1.6, 0.85, 1.95, -0.03, 0.03, "frame", bevel=0.015)                                   # frame
    bx(m, -1.52, 1.52, 0.92, 1.88, 0.03, 0.045, "board")
    bx(m, -1.54, 1.54, 0.90, 0.92, 0.03, 0.05, "frame")                                              # lip
    bx(m, -1.54, 1.54, 1.88, 1.90, 0.03, 0.05, "frame")
    for sx in (-1, 1):
        bx(m, sx * 1.52 - 0.01, sx * 1.52 + 0.01, 0.92, 1.88, 0.03, 0.05, "frame")
        for y in (0.96, 1.84):
            m.lathe((sx * 1.46, y, 0.045), (0, 0, 1), [(0.013, 0.0), (0.013, 0.006), (0.0, 0.006)], 6, "bolt")
    for sx in (-1, 1):                                                                               # rear cross rails
        bx(m, sx * 1.35 - 0.04, sx * 1.35 + 0.04, 0.90, 0.96, -0.06, -0.03, "frame")
    m.to_object("sign_mesh", parent=root, smooth=None)


# ----------------------------------------------------------------------------- rock
def build_rock():
    make_mat("rock", (0.50, 0.49, 0.47), rough=0.95)
    make_mat("moss", (0.28, 0.40, 0.18), rough=1.0)
    root = _root("rock")
    m = MB()
    m.ico((0, 0.55, 0), 1.0, "rock", subdiv=3, scale=(1.15, 0.75, 0.9), jitter=0.16, seed=11, ymin=0.0)
    m.ico((1.05, 0.30, 0.55), 0.55, "rock", subdiv=3, scale=(1.0, 0.7, 0.9), jitter=0.18, seed=23, ymin=0.0)
    m.ico((-0.95, 0.25, -0.60), 0.48, "rock", subdiv=2, scale=(1.1, 0.65, 1.0), jitter=0.20, seed=31, ymin=0.0)
    m.ico((0.35, 0.18, -1.0), 0.34, "rock", subdiv=2, scale=(1.0, 0.7, 1.1), jitter=0.2, seed=41, ymin=0.0)
    m.ico((-0.1, 1.19, 0.05), 0.46, "moss", subdiv=2, scale=(1.0, 0.24, 0.85), jitter=0.10, seed=5)     # moss cap
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
    make_mat("lamp", (1.0, 0.96, 0.80), rough=0.2, emit=(1.0, 0.92, 0.65), emit_strength=0.6)
    make_mat("taillamp", (0.80, 0.05, 0.05), rough=0.3, emit=(0.9, 0.05, 0.05), emit_strength=0.4)
    make_mat("chrome", (0.80, 0.82, 0.85), metallic=1.0, rough=0.2)
    root = _root("golf_cart")
    m = MB()
    V = Vector

    def rr(z, hw, y0, y1, cb):                 # chamfered-rectangle section in the XY plane
        return [V(p) for p in ((hw, y1 - cb, z), (hw - cb, y1, z), (-(hw - cb), y1, z), (-hw, y1 - cb, z),
                               (-hw, y0 + cb, z), (-(hw - cb), y0, z), (hw - cb, y0, z), (hw, y0 + cb, z))]
    # chassis pan, sills, battery box and motor housing underneath
    bx(m, -0.56, 0.56, 0.16, 0.28, -1.05, 1.15, "cart_trim", bevel=0.03)
    bx(m, -0.45, 0.45, 0.10, 0.18, -0.62, 0.05, "cart_trim", bevel=0.02)
    m.lathe((0, 0.17, -0.74), (1, 0, 0), [(0.07, -0.16), (0.07, 0.16)], 8, "cart_trim")
    # front cowl and rear deck lofted as chamfered sections
    m.loft([rr(1.20, 0.40, 0.25, 0.50, 0.08), rr(1.14, 0.50, 0.22, 0.62, 0.10), rr(0.90, 0.54, 0.22, 0.68, 0.11),
            rr(0.45, 0.55, 0.22, 0.72, 0.10)], "cart_body")
    m.loft([rr(-0.42, 0.55, 0.22, 0.52, 0.08), rr(-0.62, 0.55, 0.22, 0.58, 0.09), rr(-1.08, 0.50, 0.24, 0.56, 0.09),
            rr(-1.18, 0.44, 0.26, 0.50, 0.08)], "cart_body")
    # bumpers
    bx(m, -0.50, 0.50, 0.20, 0.34, 1.19, 1.27, "cart_trim", bevel=0.03)
    bx(m, -0.50, 0.50, 0.20, 0.34, -1.24, -1.16, "cart_trim", bevel=0.03)
    # headlamps and tail lamps
    for sx in (-1, 1):
        m.lathe((sx * 0.33, 0.50, 1.18), (0, 0, 1), [(0.0, -0.02), (0.075, -0.02), (0.075, 0.02), (0.060, 0.03), (0.0, 0.03)], 10, "cart_trim")
        m.lathe((sx * 0.33, 0.50, 1.205), (0, 0, 1), [(0.0, 0.0), (0.060, 0.0), (0.050, 0.014), (0.0, 0.018)], 10, "lamp")
        bx(m, sx * 0.34 - 0.07, sx * 0.34 + 0.07, 0.44, 0.50, -1.205, -1.18, "taillamp", bevel=0.008)
    # mudguards over all four wheels (flared annulus sectors)
    for z in (0.78, -0.72):
        for sx in (-1, 1):
            x0, x1 = (0.46, 0.70) if sx > 0 else (-0.70, -0.46)
            m.sector((0, 0.23, z), 0.255, 0.285, math.radians(8), math.radians(172), x0, x1, 7, "cart_body")
    # seat: base, two cushions, two backrests, centre seam, grab handle
    bx(m, -0.52, 0.52, 0.30, 0.42, -0.52, 0.14, "cart_trim", bevel=0.02)
    for sx in (-1, 1):
        m.box((sx * 0.25, 0.49, -0.20), (0.47, 0.13, 0.62), "seat", bevel=0.04)
        m.box((sx * 0.25, 0.86, -0.54), (0.45, 0.46, 0.10), "seat", bevel=0.045, rot=Matrix.Rotation(math.radians(-8), 3, 'X'))
        bx(m, sx * 0.505, sx * 0.545, 0.54, 0.78, -0.50, -0.10, "cart_trim", bevel=0.01)             # side hip restraint
    bx(m, -0.012, 0.012, 0.50, 0.58, -0.50, 0.10, "cart_trim")
    m.pipe((-0.46, 0.72, -0.62), (0.46, 0.72, -0.62), 0.016, 6, "chrome")
    # dash, glovebox, instrument pod, switch gear
    m.box((0, 0.86, 0.44), (1.08, 0.34, 0.16), "cart_body", bevel=0.05)
    bx(m, -0.50, -0.06, 0.74, 0.96, 0.518, 0.528, "cart_trim", bevel=0.004)                           # glovebox door
    bx(m, -0.30, -0.26, 0.84, 0.88, 0.526, 0.545, "chrome")
    m.box((0.25, 1.07, 0.42), (0.24, 0.09, 0.10), "cart_trim", bevel=0.02)
    m.lathe((0.20, 1.03, 0.37), (0, 0, 1), [(0.020, 0), (0.020, 0.016), (0, 0.016)], 8, "chrome")
    m.box((-0.15, 0.95, 0.52), (0.06, 0.05, 0.04), "cart_trim", bevel=0.008)
    # steering column and wheel (ring + three spokes + hub)
    ax = V((0, 0.5, -0.8)).normalized()
    hubc = V((0.25, 1.0, 0.36))
    m.pipe((0.25, 0.86, 0.50), hubc, 0.020, 6, "cart_trim")
    m.lathe(hubc, ax, [(0.13, -0.012), (0.13, 0.012), (0.105, 0.012), (0.105, -0.012)], 12, "cart_trim", closed=True)
    m.lathe(hubc, ax, [(0.0, -0.02), (0.032, -0.02), (0.032, 0.02), (0.0, 0.02)], 8, "cart_trim")
    uax = V((1, 0, 0))
    vax = ax.cross(uax)
    for k in range(3):
        a = math.radians(90 + k * 120)
        tip = hubc + (uax * math.cos(a) + vax * math.sin(a)) * 0.108
        limb(m, hubc, tip, 0.012, 0.009, 4, "cart_trim")
    # forward/reverse selector and handbrake beside the driver
    m.pipe((0.52, 0.56, -0.10), (0.52, 0.80, -0.04), 0.012, 5, "chrome")
    m.ico((0.52, 0.82, -0.035), 0.022, "cart_trim", subdiv=1)
    # windscreen: glass, frame, two posts
    for sx in (-1, 1):
        m.pipe((sx * 0.50, 1.02, 0.46), (sx * 0.50, 1.80, 0.36), 0.022, 6, "cart_trim")
        m.pipe((sx * 0.50, 0.92, -1.05), (sx * 0.50, 1.80, -1.05), 0.022, 6, "cart_trim")
        m.pipe((sx * 0.50, 0.58, -1.05), (sx * 0.50, 0.92, -1.05), 0.026, 6, "cart_trim")
    m.face([(-0.48, 1.08, 0.455), (0.48, 1.08, 0.455), (0.48, 1.78, 0.365), (-0.48, 1.78, 0.365)], "glass", hint=(0, 0.1, 1))
    m.pipe((-0.50, 1.04, 0.455), (0.50, 1.04, 0.455), 0.018, 6, "cart_trim")
    m.pipe((-0.50, 1.79, 0.365), (0.50, 1.79, 0.365), 0.018, 6, "cart_trim")
    m.pipe((0.0, 1.05, 0.455), (0.0, 1.79, 0.365), 0.012, 5, "cart_trim")
    # roof: skin, rim, front visor lip, four struts
    m.box((0, 1.84, -0.30), (1.20, 0.07, 1.90), "cart_body", bevel=0.025)
    bx(m, -0.55, 0.55, 1.795, 1.815, -1.18, 0.55, "cart_trim", bevel=0.005)
    m.box((0, 1.83, 0.66), (1.12, 0.045, 0.10), "cart_body", bevel=0.015, rot=Matrix.Rotation(math.radians(8), 3, 'X'))
    for sx in (-1, 1):
        m.pipe((sx * 0.50, 1.80, -0.30), (sx * 0.50, 1.80, 0.36), 0.014, 5, "cart_trim")                # roof rails
    # rear bag well: deck plate, cradle hoops, straps; a bag leaning on the rear posts
    bx(m, -0.50, 0.50, 0.56, 0.60, -1.12, -0.74, "cart_trim", bevel=0.01)
    for sx in (-1, 1):
        bx(m, sx * 0.44 - 0.02, sx * 0.44 + 0.02, 0.58, 0.90, -1.10, -0.76, "cart_trim", bevel=0.008)
    m.lathe((0, 0.93, -1.0), (0, 0, 1), [(0.20, -0.016), (0.20, 0.016), (0.18, 0.016), (0.18, -0.016)], 12, "cart_trim", closed=True, scale=(0.95, 1.0))
    bagc = V((0, 1.03, -0.96))
    bagax = V((0, 1.0, -0.14)).normalized()
    m.lathe(bagc, bagax, [(0, -0.45), (0.13, -0.45), (0.152, -0.40), (0.162, 0.0), (0.166, 0.26), (0.172, 0.33),
                          (0.158, 0.37), (0.125, 0.37), (0.125, 0.33), (0, 0.33)], 10, "bag", scale=(1.0, 1.1))
    m.box(bagc + V((0.0, 0.0, 0.17)), (0.22, 0.34, 0.07), "bag", bevel=0.02)
    top = bagc + bagax * 0.31
    for i, (kind, ox, oz, tilt) in enumerate((("driver", -0.06, 0.0, (-0.10, 0.0)), ("wood", 0.05, 0.05, (0.10, 0.05)),
                                              ("iron", 0.0, -0.06, (0.0, -0.12)),
                                              ("putter", -0.08, 0.06, (-0.15, 0.08)))):
        d = V((tilt[0], 1.0, tilt[1] + bagax.z)).normalized()
        club(m, top + V((ox, 0, oz)), d, kind, (math.sin(i), 0.1, math.cos(i)), length=0.26 + 0.015 * i, mats=("club", "club", "cart_trim"),
             show_grip=False, detail=1)
    # wheels: lugged tyre, dished rim, hub cap and four lug nuts; axles and leaf springs between
    def tread(pi, i):
        return 0.965 if (pi in (2, 3, 4, 5) and i % 2 == 0) else 1.0
    for z in (0.78, -0.72):
        m.pipe((-0.58, 0.23, z), (0.58, 0.23, z), 0.032, 8, "cart_trim")
        for sx in (-1, 1):
            x = sx * 0.58
            m.lathe((x, 0.23, z), (sx, 0, 0), [(0.0, -0.09), (0.15, -0.09), (0.205, -0.084), (0.230, -0.055), (0.234, 0.0),
                                                (0.230, 0.055), (0.205, 0.084), (0.15, 0.09), (0.0, 0.09)], 16, "tyre", mod=tread)
            m.lathe((x, 0.23, z), (sx, 0, 0), [(0.0, 0.088), (0.040, 0.100), (0.150, 0.092), (0.150, 0.080), (0.0, 0.080)], 10, "rim")
            m.lathe((x, 0.23, z), (sx, 0, 0), [(0.0, 0.104), (0.034, 0.104), (0.034, 0.100), (0.0, 0.100)], 8, "chrome")
            for k in range(4):
                a = math.radians(45 + 90 * k)
                m.lathe((x + sx * 0.100, 0.23 + 0.075 * math.sin(a), z + 0.075 * math.cos(a)), (sx, 0, 0),
                        [(0.012, 0.0), (0.012, 0.012), (0.0, 0.012)], 4, "chrome")
        for sx in (-1, 1):
            bx(m, sx * 0.34 - 0.04, sx * 0.34 + 0.04, 0.19, 0.215, z - 0.17, z + 0.17, "cart_trim")
    # side mirrors
    for sx in (-1, 1):
        m.pipe((sx * 0.50, 1.50, 0.40), (sx * 0.66, 1.48, 0.30), 0.010, 5, "cart_trim")
        m.box((sx * 0.68, 1.48, 0.29), (0.045, 0.09, 0.012), "chrome", bevel=0.004, rot=Matrix.Rotation(0.3 * sx, 3, 'Y'))
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
    # fuselage: lofted shell, battery tray, top dome with vents, gimbal bracket
    def sec(z, hw, y0, y1):
        cb = min(hw, (y1 - y0) / 2) * 0.55
        return [Vector(p) for p in ((hw, y1 - cb, z), (hw - cb, y1, z), (-(hw - cb), y1, z), (-hw, y1 - cb, z),
                                    (-hw, y0 + cb, z), (-(hw - cb), y0, z), (hw - cb, y0, z), (hw, y0 + cb, z))]
    m.loft([sec(0.095, 0.030, -0.010, 0.020), sec(0.070, 0.056, -0.022, 0.034), sec(-0.050, 0.062, -0.024, 0.036),
            sec(-0.090, 0.040, -0.014, 0.026)], "drone_body")
    bx(m, -0.040, 0.040, 0.034, 0.046, -0.055, 0.050, "drone_trim", bevel=0.004)
    for k in range(4):
        bx(m, -0.030, 0.030, 0.0455, 0.049, -0.040 + k * 0.022, -0.034 + k * 0.022, "drone_body")        # vents
    bx(m, -0.046, 0.046, -0.050, -0.022, -0.060, 0.030, "drone_trim", bevel=0.006)                    # battery
    bx(m, -0.022, 0.022, -0.045, -0.030, -0.062, -0.058, "led_red")
    # arms, motor bells, folding hinges
    hubs = {}
    for name, sx, sz in (("rotor_fl", 1, 1), ("rotor_fr", -1, 1), ("rotor_rl", 1, -1), ("rotor_rr", -1, -1)):
        tip = Vector((sx * 0.175, 0.014, sz * 0.175))
        limb(m, (sx * 0.045, 0.008, sz * 0.045), tip, 0.012, 0.0085, 6, "drone_body")
        m.lathe((sx * 0.060, 0.012, sz * 0.060), (0, 1, 0), [(0.016, -0.010), (0.016, 0.010)], 8, "drone_trim")          # hinge
        m.lathe(tip, (0, 1, 0), [(0.015, -0.010), (0.016, 0.0), (0.014, 0.012), (0.009, 0.016)], 8, "drone_trim")         # motor bell
        m.lathe(tip + Vector((0, -0.012, 0)), (0, 1, 0), [(0.011, -0.012), (0.011, 0.0)], 6, "drone_body")
        hubs[name] = tip + Vector((0, 0.024, 0))
        bx(m, tip.x - 0.004, tip.x + 0.004, -0.012, 0.0, tip.z - 0.004, tip.z + 0.004, "drone_body")
        # landing leg under each motor
        foot = Vector((sx * 0.185, -0.085, sz * 0.185))
        limb(m, (sx * 0.15, 0.0, sz * 0.15), foot, 0.0065, 0.005, 4, "drone_trim")
        m.box(foot + Vector((0, -0.004, 0)), (0.026, 0.008, 0.026), "drone_body", bevel=0.002)
    # camera gimbal with a three-axis yoke and a lens barrel
    m.ico((0, -0.050, 0.092), 0.030, "drone_body", subdiv=2)
    m.lathe((0, -0.050, 0.110), (0, 0, 1), [(0.0, 0.0), (0.021, 0.0), (0.021, 0.014), (0.016, 0.020), (0.0, 0.020)], 10, "lens")
    m.lathe((0, -0.050, 0.108), (0, 0, 1), [(0.025, 0.0), (0.025, 0.006), (0.021, 0.006), (0.021, 0.0)], 10, "drone_trim", closed=True)
    for sx in (-1, 1):
        limb(m, (sx * 0.032, -0.018, 0.078), (sx * 0.032, -0.056, 0.092), 0.005, 0.005, 4, "drone_trim")
    # status LEDs and a short whip antenna
    bx(m, 0.036, 0.048, 0.004, 0.012, 0.094, 0.104, "led_green")
    bx(m, -0.048, -0.036, 0.004, 0.012, 0.094, 0.104, "led_green")
    bx(m, 0.040, 0.052, 0.004, 0.012, -0.100, -0.088, "led_red")
    bx(m, -0.052, -0.040, 0.004, 0.012, -0.100, -0.088, "led_red")
    limb(m, (0.0, 0.034, -0.084), (0.0, 0.080, -0.100), 0.0035, 0.002, 4, "drone_body")
    m.to_object("drone_body", parent=root, smooth=None)
    # rotors: separate nodes, origin at the hub, two pitched blades each
    for name, hub in hubs.items():
        r = MB()
        for sgn in (-1, 1):
            rings = []
            for u, ch in ((0.012, 0.020), (0.060, 0.024), (0.128, 0.013)):
                p = 0.30 - 1.2 * (u - 0.012)
                rings.append([Vector((hub.x + sgn * u, hub.y + zz * math.sin(p) + t, hub.z + zz * math.cos(p)))
                              for zz, t in ((ch / 2, 0.0016), (-ch / 2, 0.0016), (-ch / 2, -0.0016), (ch / 2, -0.0016))])
            r.loft(rings, "rotor")
        r.lathe(hub, (0, 1, 0), [(0.012, -0.004), (0.012, 0.007), (0.006, 0.010), (0.0, 0.010)], 8, "drone_trim")
        r.to_object(name, origin=tuple(hub), parent=root, smooth=None)


# ----------------------------------------------------------------------------- lodge
def build_lodge():
    from lodge import build as _b
    _b()
