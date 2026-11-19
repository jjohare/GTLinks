"""New props: golfer, golf_bag, golf_club, cow, tree_larch.

Game frame (+X left, +Y up, +Z forward). Each build_* creates its objects in a clean scene; the root
empty is named after the file. Shared helpers live in propkit.py.
"""
import math, random
from mathutils import Vector, Matrix
from gtl import MB, make_mat, empty, bx
from propkit import basis, limb, tube, ring_pts, loft_mat, blob, dome, ik2, club


# ============================================================================ golf club
def build_golf_club():
    """Driver, ~1.12 m. Origin at the grip end; the shaft hangs down -Y, the face looks +Z, the toe is +X."""
    make_mat("shaft", (0.62, 0.64, 0.68), metallic=0.9, rough=0.3)
    make_mat("head", (0.10, 0.11, 0.13), metallic=0.55, rough=0.28)
    make_mat("grip", (0.06, 0.06, 0.065), rough=0.85)
    root = empty("golf_club")
    m = MB()
    club(m, (0, 0, 0), (0, -1, 0), 'driver', (0, 0, 1), length=1.12)
    # face insert and a sole plate, so the head reads as more than one casting
    m.to_object("golf_club_mesh", parent=root, smooth=45)


# ============================================================================ golf bag
def build_golf_bag():
    make_mat("bag_body", (0.10, 0.22, 0.40), rough=0.8)
    make_mat("bag_hood", (0.86, 0.83, 0.74), rough=0.8)
    make_mat("bag_trim", (0.09, 0.09, 0.10), rough=0.85)
    make_mat("bag_accent", (0.75, 0.14, 0.10), rough=0.8)
    make_mat("bag_inner", (0.02, 0.02, 0.025), rough=1.0)
    make_mat("zip", (0.70, 0.72, 0.75), metallic=0.85, rough=0.35)
    make_mat("towel", (0.95, 0.95, 0.92), rough=0.98)
    make_mat("towel_b", (0.12, 0.40, 0.25), rough=0.98)
    make_mat("umbrella", (0.78, 0.72, 0.20), rough=0.7)
    make_mat("shaft", (0.62, 0.64, 0.68), metallic=0.9, rough=0.3)
    make_mat("head", (0.12, 0.12, 0.14), metallic=0.6, rough=0.3)
    make_mat("grip", (0.06, 0.06, 0.065), rough=0.85)
    make_mat("cover", (0.62, 0.10, 0.12), rough=0.95)
    make_mat("cover_b", (0.95, 0.93, 0.85), rough=0.95)
    root = empty("golf_bag")
    m = MB()
    S = (0.92, 1.0)                                       # body is a little narrower left-right than front-back
    # main body and base
    m.lathe((0, 0, 0), (0, 1, 0), [(0, 0), (0.104, 0), (0.118, 0.025), (0.128, 0.30), (0.134, 0.60), (0.138, 0.78), (0, 0.78)],
            14, "bag_body", scale=S)
    m.lathe((0, 0, 0), (0, 1, 0), [(0, 0), (0.110, 0), (0.122, 0.030), (0.122, 0.075), (0, 0.075)], 14, "bag_trim", scale=S)
    # hood with a recessed mouth and a rolled rim
    m.lathe((0, 0, 0), (0, 1, 0), [(0, 0.76), (0.142, 0.76), (0.150, 0.80), (0.150, 0.915), (0.140, 0.940), (0.124, 0.936),
                                     (0.121, 0.90), (0, 0.90)], 14, "bag_hood", scale=S)
    m.lathe((0, 0, 0), (0, 1, 0), [(0, 0.84), (0.150, 0.84), (0.152, 0.855), (0.150, 0.87), (0, 0.87)], 14, "bag_accent", scale=S)
    m.lathe((0, 0, 0), (0, 1, 0), [(0, 0.903), (0.118, 0.903), (0.118, 0.897), (0, 0.897)], 14, "bag_inner", scale=S)
    # club dividers across the mouth
    bx(m, -0.118 * S[0], 0.118 * S[0], 0.905, 0.915, -0.004, 0.004, "bag_trim")
    bx(m, -0.004, 0.004, 0.905, 0.915, -0.118, 0.118, "bag_trim")
    # pockets: big front pocket, ball pocket (+X), apparel pocket (-X)
    m.box((0, 0.34, 0.148), (0.20, 0.40, 0.07), "bag_body", bevel=0.024)
    bx(m, -0.100, 0.100, 0.16, 0.25, 0.181, 0.188, "bag_accent")
    bx(m, -0.100, 0.100, 0.40, 0.43, 0.181, 0.188, "bag_accent")
    bx(m, -0.095, 0.095, 0.455, 0.470, 0.186, 0.194, "zip")
    bx(m, -0.012, 0.012, 0.425, 0.472, 0.190, 0.202, "bag_trim")
    m.box((0.128, 0.46, 0.04), (0.070, 0.22, 0.17), "bag_body", bevel=0.020)
    bx(m, 0.158, 0.164, 0.36, 0.40, -0.03, 0.12, "bag_accent")
    bx(m, 0.164, 0.172, 0.50, 0.53, 0.06, 0.09, "zip")
    m.box((-0.130, 0.54, 0.0), (0.070, 0.24, 0.20), "bag_body", bevel=0.020)
    bx(m, -0.166, -0.160, 0.44, 0.48, -0.08, 0.08, "bag_accent")
    # rear stand: folded legs, hinge block, feet
    bx(m, -0.060, 0.060, 0.560, 0.640, -0.172, -0.140, "bag_trim", bevel=0.01)
    for sx in (-1, 1):
        m.pipe((sx * 0.058, 0.60, -0.158), (sx * 0.072, 0.075, -0.180), 0.0095, 6, "zip")
        bx(m, sx * 0.072 - 0.022, sx * 0.072 + 0.022, 0.0, 0.034, -0.215, -0.150, "bag_trim", bevel=0.008)
    # carry strap: padded loop on the -X side with buckle and D-rings
    strap = [(-0.128, 0.80, -0.020), (-0.190, 0.76, -0.020), (-0.236, 0.62, -0.020), (-0.238, 0.44, -0.020),
             (-0.205, 0.28, -0.020), (-0.140, 0.18, -0.020)]
    tube(m, strap, 0.023, 4, "bag_trim", scale=(0.30, 1.0), phase=math.pi / 4)
    tube(m, [(-0.236, 0.58, -0.020), (-0.238, 0.50, -0.020)], 0.027, 4, "bag_accent", scale=(0.45, 1.0), phase=math.pi / 4)
    bx(m, -0.252, -0.236, 0.40, 0.44, -0.035, -0.005, "zip")
    for y in (0.80, 0.18):
        m.lathe((-0.134, y, -0.02), (0, 0, 1), [(0.020, -0.006), (0.020, 0.006), (0.013, 0.006), (0.013, -0.006)], 8, "zip", closed=True)
    # towel on the +X side: clipped to a ring, with two stripes
    m.lathe((0.152, 0.860, 0.060), (0, 0, 1), [(0.018, -0.008), (0.018, 0.008), (0.012, 0.008), (0.012, -0.008)], 8, "zip", closed=True)
    m.box((0.163, 0.700, 0.060), (0.014, 0.300, 0.110), "towel", bevel=0.004, rot=Matrix.Rotation(math.radians(-3), 3, 'Z'))
    for y in (0.60, 0.64):
        bx(m, 0.168, 0.172, y - 0.012, y + 0.012, 0.006, 0.114, "towel_b")
    # furled umbrella strapped behind: sheath, band, handle crook, metal tip above the hood
    m.pipe((0.060, 0.145, -0.170), (0.074, 0.75, -0.166), 0.026, 8, "umbrella")
    limb(m, (0.074, 0.75, -0.166), (0.082, 0.96, -0.164), 0.026, 0.007, 8, "umbrella")
    limb(m, (0.082, 0.96, -0.164), (0.086, 1.10, -0.163), 0.006, 0.0035, 6, "zip")
    m.ico((0.086, 1.108, -0.163), 0.008, "zip", subdiv=1)
    bx(m, 0.036, 0.098, 0.46, 0.50, -0.196, -0.140, "bag_accent")
    tube(m, [(0.058, 0.145, -0.170), (0.056, 0.080, -0.172), (0.040, 0.050, -0.172), (0.014, 0.060, -0.172)], 0.011, 6, "bag_trim")
    # clubs: heads up, grips inside the mouth
    rnd = random.Random(7)
    clubs = [("driver", -0.052, 0.040, (-0.10, 0.0), 0.34, None),
             ("wood", 0.050, 0.048, (0.07, 0.04), 0.31, ("cover", "cover_b")),
             ("hybrid", -0.078, -0.030, (-0.12, -0.02), 0.28, None),
             ("iron", 0.012, -0.045, (0.0, -0.05), 0.22, None),
             ("iron", 0.085, -0.002, (0.14, 0.0), 0.26, None),
             ("iron", -0.012, 0.075, (-0.02, 0.10), 0.20, None),
             ("wedge", 0.070, -0.060, (0.10, -0.08), 0.18, None),
             ("putter", -0.085, 0.060, (-0.15, 0.10), 0.30, None)]
    for kind, x, z, (tx, tz), vis, cover in clubs:
        d = Vector((tx, 1.0, tz)).normalized()
        a = rnd.uniform(-0.5, 0.5)
        club(m, (x, 0.90, z), d, kind, (math.sin(a), 0.15, math.cos(a)), length=vis, show_grip=False, cover=cover, detail=2)
    m.to_object("golf_bag_mesh", parent=root, smooth=45)


# ============================================================================ larch
def build_tree_larch():
    make_mat("bark", (0.36, 0.25, 0.17), rough=0.95)
    make_mat("needles", (0.40, 0.55, 0.16), rough=0.9)
    make_mat("needles_tip", (0.62, 0.70, 0.24), rough=0.9)
    root = empty("tree_larch")
    m = MB()
    rnd = random.Random(21)

    def tx(y):                                            # trunk centreline: gentle S-bend
        return 0.34 * math.sin(y * 0.52) + 0.012 * y

    def tz(y):
        return 0.18 * math.sin(y * 0.37 + 1.0)
    ys = [0.6, 1.5, 2.6, 3.8, 5.0, 6.2, 7.3, 8.3, 9.0]
    rad = [0.26, 0.21, 0.18, 0.15, 0.12, 0.095, 0.07, 0.04, 0.006]
    tube(m, [(0, 0.0, 0), (0, 0.3, 0)] + [(tx(y), y, tz(y)) for y in ys], [0.36, 0.31] + rad, 6, "bark")
    # whorled branches with a drooping tuft of needles at each tip
    k = 0
    for y, L, nb in ((2.6, 2.0, 3), (3.5, 1.9, 3), (4.4, 1.7, 3), (5.3, 1.45, 2), (6.2, 1.15, 2), (7.1, 0.85, 2), (7.9, 0.55, 1)):
        a0 = rnd.uniform(0, 6.28)
        for q in range(nb):
            a = a0 + q * 6.28 / nb + rnd.uniform(-0.3, 0.3)
            p0 = Vector((tx(y), y, tz(y)))
            p1 = p0 + Vector((math.cos(a) * L * 0.78, 0.18 - 0.10 * k % 0.2, math.sin(a) * L * 0.78))
            limb(m, p0, p1, 0.045, 0.014, 3, "bark")
            c = (p1.x, p1.y - 0.10, p1.z)
            R = 0.50 + 0.22 * L
            dome(m, c, [(0, 0.20), (R, -0.08), (0.5 * R, -0.34), (0, -0.20)], 6,
                 "needles" if k % 2 == 0 else "needles_tip", jit=0.22, seed=300 + k, sag=0.35, phase=k)
            k += 1
    # central tiers hugging the stem
    for i in range(5):
        f = i / 4.0
        y = 3.5 + f * 4.9
        R = 0.95 * (1 - f) + 0.22
        dome(m, (tx(y), y, tz(y)), [(0, 0.35), (R, -0.10), (0.5 * R, -0.34), (0, -0.20)], 6,
             "needles_tip" if i % 2 else "needles", jit=0.2, seed=400 + i, sag=0.3, phase=i * 0.9)
    dome(m, (tx(9.0), 9.0, tz(9.0)), [(0, 0.45), (0.10, 0.1), (0.14, -0.15), (0, -0.30)], 6, "needles_tip", jit=0.1, seed=5)
    m.to_object("tree_larch_mesh", parent=root, smooth=None)


# ============================================================================ cow
def build_cow():
    make_mat("hide", (0.92, 0.89, 0.82), rough=0.92)
    make_mat("patch", (0.40, 0.21, 0.10), rough=0.92)
    make_mat("muzzle", (0.88, 0.62, 0.58), rough=0.7)
    make_mat("horn", (0.88, 0.84, 0.70), rough=0.55)
    make_mat("hoof", (0.14, 0.11, 0.10), rough=0.6)
    make_mat("leather", (0.34, 0.20, 0.10), rough=0.8)
    make_mat("bell", (0.80, 0.60, 0.20), metallic=0.85, rough=0.35)
    make_mat("eye", (0.03, 0.025, 0.02), rough=0.3)
    make_mat("tuft", (0.22, 0.12, 0.07), rough=0.95)
    make_mat("udder", (0.92, 0.70, 0.66), rough=0.8)
    root = empty("cow")
    m = MB()
    # ---- barrel: stations (z, centre y, half-width, half-height)
    st = [(-0.98, 1.02, 0.10, 0.13), (-0.91, 1.04, 0.22, 0.26), (-0.74, 1.05, 0.31, 0.36), (-0.46, 1.00, 0.335, 0.385),
          (-0.16, 0.95, 0.35, 0.395), (0.14, 0.95, 0.35, 0.40), (0.42, 0.98, 0.335, 0.405), (0.66, 1.01, 0.295, 0.385),
          (0.83, 1.04, 0.225, 0.31), (0.94, 1.09, 0.165, 0.235)]
    N = 16
    rings = []
    for z, cy, rx, ry in st:
        rings.append([(rx * math.cos(2 * math.pi * j / N), cy + ry * math.sin(2 * math.pi * j / N), z) for j in range(N)])
    # patches in (z, angle) space; angle 90 deg = spine, 270 = belly
    blobs = [(-0.45, 85, 0.36, 75), (0.16, 25, 0.28, 55), (-0.12, 205, 0.30, 62), (0.64, 125, 0.22, 48),
             (-0.86, 335, 0.18, 60), (0.40, 255, 0.20, 50), (-0.70, 150, 0.20, 40)]
    zc = [(st[i][0] + st[i + 1][0]) / 2 for i in range(len(st) - 1)]

    def mfn(i, j):
        th = (j + 0.5) * 360.0 / N
        z = zc[min(i, len(zc) - 1)]
        for bz, bth, rz, rth in blobs:
            dth = (th - bth + 180.0) % 360.0 - 180.0
            if ((z - bz) / rz) ** 2 + (dth / rth) ** 2 < 1.0:
                return "patch"
        return "hide"
    loft_mat(m, [[Vector(p) for p in r] for r in rings], mfn)
    # haunch and shoulder muscle, hip bones, dewlap
    for sx in (-1, 1):
        blob(m, (sx * 0.25, 0.86, -0.62), (0.15, 0.30, 0.26), "hide", subdiv=2, seed=sx + 3, jitter=0.02)
        blob(m, (sx * 0.25, 0.93, 0.56), (0.12, 0.26, 0.22), "hide", subdiv=2, seed=sx + 5, jitter=0.02)
    blob(m, (0, 0.78, 0.84), (0.10, 0.20, 0.14), "hide", subdiv=2)

    # ---- head: rings in XY planes along +Z
    hs = [(0.88, 1.10, 0.15, 0.20), (0.99, 1.12, 0.135, 0.17), (1.10, 1.07, 0.125, 0.155), (1.23, 0.98, 0.100, 0.130),
          (1.36, 0.91, 0.082, 0.100), (1.47, 0.86, 0.078, 0.082), (1.53, 0.845, 0.060, 0.058)]
    NH = 12
    hr = []
    for z, cy, rx, ry in hs:
        rx, ry = rx * 1.12, ry * 1.12
        hr.append([Vector((rx * math.cos(2 * math.pi * j / NH), cy + ry * math.sin(2 * math.pi * j / NH), z)) for j in range(NH)])

    def hfn(i, j):
        th = (j + 0.5) * 360.0 / NH
        if i >= 4:
            return "muzzle"
        if 45 < th < 135 and i >= 1:
            return "hide"                                  # white blaze down the face
        return "patch"
    loft_mat(m, hr, hfn)
    for sx in (-1, 1):
        m.pipe((sx * 0.04, 0.855, 1.532), (sx * 0.04, 0.855, 1.540), 0.012, 5, "eye")                  # nostrils
        blob(m, (sx * 0.125, 1.15, 1.04), (0.022, 0.024, 0.022), "eye", subdiv=2)                    # eyes
        # ears: flattened leaf shapes angled out and back
        blob(m, (sx * 0.215, 1.17, 0.93), (0.090, 0.020, 0.046), "patch", subdiv=2,
             rot=Matrix.Rotation(sx * math.radians(-18), 3, 'Z') @ Matrix.Rotation(math.radians(-14), 3, 'Y'))
        blob(m, (sx * 0.208, 1.17, 0.945), (0.060, 0.010, 0.030), "udder", subdiv=1,
             rot=Matrix.Rotation(sx * math.radians(-18), 3, 'Z') @ Matrix.Rotation(math.radians(-14), 3, 'Y'))
        # horns: curve out, then up and slightly forward
        hp = [(sx * 0.085, 1.235, 0.97), (sx * 0.150, 1.255, 0.96), (sx * 0.215, 1.315, 0.965), (sx * 0.245, 1.405, 0.985),
              (sx * 0.240, 1.490, 1.015)]
        tube(m, hp, [0.030, 0.026, 0.019, 0.012, 0.003], 6, "horn")
        bx(m, sx * 0.085 - 0.04, sx * 0.085 + 0.04, 1.215, 1.235, 0.93, 1.02, "patch")
    # ---- collar and bell
    cy0, cz0 = 1.04, 0.80
    m.lathe((0, cy0, cz0), (0, 0, 1), [(1.0, -0.032), (1.0, 0.032), (0.96, 0.032), (0.96, -0.032)], 18, "leather", scale=(0.265, 0.335), closed=True)
    bell_c = (0, cy0 - 0.335 - 0.115, cz0)
    m.pipe((0, cy0 - 0.335, cz0), (0, bell_c[1] + 0.085, cz0), 0.020, 6, "leather")
    m.lathe(bell_c, (0, 1, 0), [(0.0, 0.085), (0.042, 0.080), (0.058, 0.040), (0.075, -0.030), (0.092, -0.085), (0.0, -0.085)], 10, "bell",
            scale=(0.80, 1.0))
    m.lathe(bell_c, (0, 1, 0), [(0.0, -0.080), (0.075, -0.080), (0.075, -0.090), (0.0, -0.090)], 10, "eye", scale=(0.78, 1.0))
    m.ico((0, bell_c[1] - 0.092, cz0), 0.018, "bell", subdiv=2)
    # ---- legs
    def leg(sx, pts, rads, hoof_y=0.10):
        for a, b, r0, r1 in zip(pts[:-1], pts[1:], rads[:-1], rads[1:]):
            limb(m, a, b, r0, r1, 7, "hide")
        for p, r in zip(pts[1:-1], rads[1:-1]):
            blob(m, p, (r * 1.06, r * 1.06, r * 1.06), "hide", subdiv=2)
        f = pts[-1]
        limb(m, (f[0], hoof_y, f[2]), (f[0], 0.0, f[2] + 0.015), 0.040, 0.052, 7, "hoof")
        limb(m, (f[0], hoof_y + 0.04, f[2]), (f[0], hoof_y, f[2]), 0.034, 0.040, 7, "hide")
    for sx in (-1, 1):
        leg(sx, [(sx * 0.22, 0.88, 0.58), (sx * 0.205, 0.48, 0.62), (sx * 0.195, 0.14, 0.60)], [0.125, 0.078, 0.052])
        leg(sx, [(sx * 0.23, 0.92, -0.62), (sx * 0.250, 0.62, -0.50), (sx * 0.205, 0.40, -0.80), (sx * 0.200, 0.14, -0.74)],
            [0.145, 0.095, 0.070, 0.052])
    # ---- udder with four teats
    blob(m, (0, 0.60, -0.40), (0.125, 0.105, 0.150), "udder", subdiv=2)
    for tx_ in (-0.048, 0.048):
        for tz_ in (-0.335, -0.455):
            limb(m, (tx_, 0.53, tz_), (tx_, 0.455, tz_), 0.017, 0.012, 5, "udder")
    # ---- tail with switch
    tp = [(0, 1.06, -0.97), (0, 1.00, -1.045), (0, 0.84, -1.075), (0, 0.62, -1.07), (0, 0.42, -1.05)]
    tube(m, tp, [0.030, 0.024, 0.018, 0.014, 0.011], 5, "patch")
    blob(m, (0, 0.31, -1.05), (0.045, 0.13, 0.045), "tuft", subdiv=2, jitter=0.06, seed=2)
    m.to_object("cow_mesh", parent=root, smooth=40)


# ============================================================================ golfer
def build_golfer():
    """Right-handed golfer in the finish of the swing: weight on the lead (+X) foot, rear heel up, chest to the
    target (+Z), both hands high by the lead shoulder, club wrapped behind the neck. Origin between the feet."""
    make_mat("shirt", (0.88, 0.88, 0.90), rough=0.9)
    make_mat("skin", (0.88, 0.64, 0.50), rough=0.8)
    make_mat("trousers", (0.52, 0.55, 0.40), rough=0.9)
    make_mat("cuff", (0.38, 0.41, 0.29), rough=0.9)
    make_mat("belt", (0.15, 0.10, 0.07), rough=0.7)
    make_mat("sock", (0.80, 0.18, 0.16), rough=0.9)
    make_mat("cap", (0.12, 0.28, 0.52), rough=0.8)
    make_mat("shoes", (0.82, 0.80, 0.74), rough=0.7)
    make_mat("sole", (0.22, 0.17, 0.12), rough=0.9)
    make_mat("glove", (0.96, 0.96, 0.96), rough=0.8)
    make_mat("hair", (0.30, 0.20, 0.12), rough=0.95)
    make_mat("eye", (0.05, 0.05, 0.06), rough=0.4)
    make_mat("shaft", (0.62, 0.64, 0.68), metallic=0.9, rough=0.3)
    make_mat("head", (0.10, 0.11, 0.13), metallic=0.55, rough=0.28)
    make_mat("grip", (0.06, 0.06, 0.065), rough=0.85)
    root = empty("golfer")
    m = MB()
    V = Vector

    def Ry(a): return Matrix.Rotation(a, 3, 'Y')
    def Rx(a): return Matrix.Rotation(a, 3, 'X')

    # ---- shoes: local frame has the ball of the foot at the origin, ground at y = 0
    def shoe(ball, yaw, heel):
        R = Ry(yaw) @ Rx(heel)
        T = V((0, 0, 0.105))                               # the toe stays planted; the heel lifts about it
        P = lambda x, y, z: V(ball) + Ry(yaw) @ T + R @ (V((x, y, z)) - T)
        m.box(P(0, 0.011, -0.045), (0.100, 0.022, 0.300), "sole", rot=R)
        m.box(P(0, 0.047, -0.060), (0.090, 0.050, 0.255), "shoes", rot=R)
        return P(0, 0.090, -0.125)                         # ankle
    ankle_l = shoe((0.17, 0, 0.12), 0.45, 0.0)
    ankle_r = shoe((-0.20, 0, -0.14), -0.20, 0.55)

    # ---- legs: plus-fours (baggy to just below the knee), socks, shoes
    def leg(hip, ankle):
        knee = ik2(hip, ankle, 0.445, 0.435, (0.0, 0.1, 1.0))
        limb(m, hip, knee, 0.090, 0.080, 5, "trousers")
        sh = (V(ankle) - knee).normalized()
        cuff_end = knee + sh * 0.17
        limb(m, knee - sh * 0.03, cuff_end, 0.088, 0.074, 5, "trousers")
        limb(m, cuff_end - sh * 0.01, ankle, 0.044, 0.036, 4, "sock")
        return knee
    leg((0.100, 0.935, 0.035), ankle_l)
    leg((-0.075, 0.945, 0.010), ankle_r)

    # ---- torso: stations (y, cx, cz, rx, rz, yaw) lofted, trousers -> belt -> shirt
    ts = [(0.86, 0.02, 0.025, 0.155, 0.105, 0.05), (0.985, 0.02, 0.02, 0.150, 0.100, 0.07),
          (1.04, 0.015, 0.015, 0.150, 0.100, 0.09),
          (1.28, 0.0, -0.025, 0.180, 0.118, 0.14), (1.43, -0.01, -0.04, 0.215, 0.118, 0.16),
          (1.50, -0.01, -0.045, 0.075, 0.075, 0.16)]
    rings = [ring_pts((cx, y, cz), rx, rz, 8, yaw=yw, phase=math.pi / 8) for y, cx, cz, rx, rz, yw in ts]
    loft_mat(m, rings, lambda i, j: "trousers" if i == 0 else ("belt" if i == 1 else "shirt"))
    # neck and polo collar
    limb(m, (-0.010, 1.490, -0.045), (-0.005, 1.625, -0.047), 0.046, 0.040, 5, "skin")
    limb(m, (-0.010, 1.470, -0.045), (-0.008, 1.525, -0.046), 0.066, 0.056, 5, "shirt")

    # ---- head, face blocks, hair, cap
    hc = V((-0.005, 1.690, -0.047))
    bx(m, hc.x - 0.072, hc.x + 0.072, hc.y - 0.050, hc.y + 0.092, hc.z - 0.085, hc.z + 0.082, "skin")
    bx(m, hc.x - 0.058, hc.x + 0.058, hc.y - 0.098, hc.y - 0.040, hc.z - 0.060, hc.z + 0.080, "skin")   # jaw
    bx(m, hc.x - 0.016, hc.x + 0.016, hc.y - 0.050, hc.y + 0.012, hc.z + 0.080, hc.z + 0.108, "skin")   # nose
    for sx in (-1, 1):
        bx(m, hc.x + sx * 0.038 - 0.010, hc.x + sx * 0.038 + 0.010, hc.y + 0.020, hc.y + 0.040, hc.z + 0.081, hc.z + 0.087, "eye")
    bx(m, hc.x - 0.068, hc.x + 0.068, hc.y - 0.020, hc.y + 0.060, hc.z - 0.108, hc.z - 0.070, "hair")     # hair under the cap
    m.lathe((hc.x, hc.y + 0.068, hc.z), (0, 1, 0), [(0.095, 0.0), (0.100, 0.030), (0.080, 0.070), (0, 0.092)], 8, "cap")
    m.box((hc.x, hc.y + 0.074, hc.z + 0.115), (0.150, 0.010, 0.095), "cap", rot=Rx(0.22))               # peak

    # ---- arms: IK from the shoulders to the hands on the grip
    d = V((-0.78, -0.15, -0.60)).normalized()                  # grip -> club head
    hand_l = V((0.20, 1.56, 0.04))
    hand_r = hand_l + d * 0.115
    sh_l, sh_r = V((0.186, 1.410, -0.072)), V((-0.206, 1.410, -0.008))
    HB = basis(V((0, 1, 0)).cross(d), d)

    def arm(sh, hand, pole, glove):
        el = ik2(sh, hand, 0.290, 0.270, pole)
        limb(m, sh, el, 0.056, 0.046, 5, "shirt")
        limb(m, el, hand, 0.040, 0.031, 5, "skin")
        m.box(hand, (0.072, 0.062, 0.100), "glove" if glove else "skin", rot=HB)
    arm(sh_l, hand_l, (0.5, -0.8, 0.5), True)
    arm(sh_r, hand_r, (0.0, -0.5, 1.0), False)

    # ---- the driver, wrapped behind the neck
    G = hand_l - d * 0.075
    club(m, G, d, 'driver', (0.3, 0.8, 0.6), length=1.10, detail=1)
    m.to_object("golfer_mesh", parent=root, smooth=None)
