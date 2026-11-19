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
    ys = [0.6, 1.8, 3.2, 4.8, 6.4, 7.8, 8.7, 9.2]
    rad = [0.26, 0.20, 0.16, 0.125, 0.09, 0.06, 0.03, 0.006]
    tube(m, [(0, 0.0, 0), (0, 0.3, 0)] + [(tx(y), y, tz(y)) for y in ys], [0.36, 0.31] + rad, 5, "bark")
    # whorls of slender branches; each carries drooping fans of needle-cluster cones (conical crown)
    k = 0
    for wi, (y, L, nb) in enumerate(((2.6, 2.4, 4), (3.6, 2.2, 4), (4.6, 1.95, 3), (5.5, 1.65, 3), (6.4, 1.35, 3),
                                     (7.2, 0.95, 2), (7.9, 0.6, 2))):
        a0 = rnd.uniform(0, 6.28)
        for q in range(nb):
            a = a0 + q * 6.28 / nb + rnd.uniform(-0.25, 0.25)
            o = Vector((math.cos(a), 0, math.sin(a)))
            s = Vector((-o.z, 0, o.x))
            p0 = Vector((tx(y), y, tz(y)))
            p1 = p0 + o * L + Vector((0, -0.12 * L, 0))
            limb(m, p0, p1, 0.040, 0.012, 3, "bark")
            for t in (0.45, 0.75, 1.0):
                P = p0 + (p1 - p0) * t
                lc = (0.65 + 0.55 * L / 2.4) * (1.05 - 0.25 * t)
                for sg in (-1, 1):
                    dvec = (o * 0.45 + s * sg * 0.50 + Vector((0, -0.80, 0))).normalized()
                    limb(m, P, P + dvec * lc, 0.16, 0.0, 3, "needles" if (k + sg) % 2 else "needles_tip")
                k += 1
    # leader: a tuft of upright cones
    top = Vector((tx(9.2), 9.2, tz(9.2)))
    for sg in range(3):
        a = sg * 2.09
        limb(m, top - Vector((0, 0.5, 0)), top + Vector((math.cos(a) * 0.12, 0.25, math.sin(a) * 0.12)), 0.10, 0.0, 3, "needles_tip")
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
    # ---- one lofted barrel: pinched at the waist, full at the haunch and at the shoulder, so no separate lumps
    st = [(-1.00, 1.02, 0.09, 0.12), (-0.94, 1.04, 0.20, 0.25), (-0.80, 1.06, 0.30, 0.35), (-0.62, 1.04, 0.345, 0.385),
          (-0.38, 0.99, 0.325, 0.385), (-0.14, 0.95, 0.335, 0.395), (0.10, 0.95, 0.340, 0.405), (0.34, 0.98, 0.350, 0.415),
          (0.56, 1.01, 0.340, 0.405), (0.74, 1.04, 0.285, 0.360), (0.86, 1.07, 0.220, 0.300), (0.95, 1.10, 0.165, 0.235)]
    N = 16
    rings = []
    for z, cy, rx, ry in st:
        rings.append([Vector((rx * math.cos(2 * math.pi * j / N), cy + ry * math.sin(2 * math.pi * j / N), z)) for j in range(N)])
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
    loft_mat(m, rings, mfn)

    # ---- head
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
            return "hide"
        return "patch"
    loft_mat(m, hr, hfn)
    rot_ear = lambda sx: Matrix.Rotation(sx * math.radians(-18), 3, 'Z') @ Matrix.Rotation(math.radians(-14), 3, 'Y')
    for sx in (-1, 1):
        m.pipe((sx * 0.04, 0.855, 1.532), (sx * 0.04, 0.855, 1.540), 0.012, 5, "eye")
        blob(m, (sx * 0.125, 1.15, 1.04), (0.022, 0.024, 0.022), "eye", subdiv=1)
        blob(m, (sx * 0.215, 1.17, 0.93), (0.090, 0.020, 0.046), "patch", subdiv=2, rot=rot_ear(sx))
        blob(m, (sx * 0.208, 1.17, 0.945), (0.060, 0.010, 0.030), "udder", subdiv=1, rot=rot_ear(sx))
        hp = [(sx * 0.085, 1.235, 0.97), (sx * 0.150, 1.255, 0.96), (sx * 0.215, 1.315, 0.965), (sx * 0.245, 1.405, 0.985),
              (sx * 0.240, 1.490, 1.015)]
        tube(m, hp, [0.030, 0.026, 0.019, 0.012, 0.003], 6, "horn")
        bx(m, sx * 0.085 - 0.04, sx * 0.085 + 0.04, 1.215, 1.235, 0.93, 1.02, "patch")
    # ---- collar and bell
    cy0, cz0 = 1.05, 0.80
    m.lathe((0, cy0, cz0), (0, 0, 1), [(1.0, -0.032), (1.0, 0.032), (0.96, 0.032), (0.96, -0.032)], 18, "leather", scale=(0.275, 0.345), closed=True)
    bell_c = (0, cy0 - 0.345 - 0.115, cz0)
    m.pipe((0, cy0 - 0.345, cz0), (0, bell_c[1] + 0.085, cz0), 0.020, 6, "leather")
    m.lathe(bell_c, (0, 1, 0), [(0.0, 0.085), (0.042, 0.080), (0.058, 0.040), (0.075, -0.030), (0.092, -0.085), (0.0, -0.085)], 10, "bell",
            scale=(0.80, 1.0))
    m.lathe(bell_c, (0, 1, 0), [(0.0, -0.080), (0.075, -0.080), (0.075, -0.090), (0.0, -0.090)], 10, "eye", scale=(0.78, 1.0))
    m.ico((0, bell_c[1] - 0.092, cz0), 0.018, "bell", subdiv=2)
    # ---- legs: each one continuous tapered loft, starting well inside the barrel (no visible joints) + a hoof
    def leg(pts, rads):
        tube(m, pts, rads, 8, "hide", up=(1, 0, 0))
        f = pts[-1]
        limb(m, (f[0], 0.105, f[2]), (f[0], 0.0, f[2] + 0.012), 0.052, 0.062, 8, "hoof")
    for sx in (-1, 1):
        leg([(sx * 0.19, 1.00, 0.54), (sx * 0.20, 0.78, 0.57), (sx * 0.205, 0.54, 0.615), (sx * 0.20, 0.44, 0.62),
             (sx * 0.195, 0.28, 0.61), (sx * 0.195, 0.15, 0.60), (sx * 0.195, 0.105, 0.60)],
            [0.12, 0.13, 0.095, 0.066, 0.050, 0.056, 0.056])
        leg([(sx * 0.18, 1.00, -0.66), (sx * 0.23, 0.76, -0.60), (sx * 0.235, 0.56, -0.64), (sx * 0.21, 0.42, -0.78),
             (sx * 0.20, 0.27, -0.77), (sx * 0.20, 0.15, -0.75), (sx * 0.20, 0.105, -0.75)],
            [0.14, 0.15, 0.105, 0.066, 0.050, 0.055, 0.055])
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
    """Right-handed golfer in a high follow-through: weight on the lead (+X) leg, rear heel lifted, chest to the
    target (+Z), both hands on a full-length driver whose shaft rises up and back past the lead shoulder."""
    make_mat("shirt", (0.88, 0.88, 0.90), rough=0.9)
    make_mat("skin", (0.88, 0.64, 0.50), rough=0.8)
    make_mat("trousers", (0.52, 0.55, 0.40), rough=0.9)
    make_mat("belt", (0.15, 0.10, 0.07), rough=0.7)
    make_mat("sock", (0.80, 0.18, 0.16), rough=0.9)
    make_mat("cap", (0.12, 0.28, 0.52), rough=0.8)
    make_mat("shoes", (0.82, 0.80, 0.74), rough=0.7)
    make_mat("sole", (0.22, 0.17, 0.12), rough=0.9)
    make_mat("glove", (0.96, 0.96, 0.96), rough=0.8)
    make_mat("eye", (0.05, 0.05, 0.06), rough=0.4)
    make_mat("shaft", (0.62, 0.64, 0.68), metallic=0.9, rough=0.3)
    make_mat("head", (0.10, 0.11, 0.13), metallic=0.55, rough=0.28)
    make_mat("grip", (0.06, 0.06, 0.065), rough=0.85)
    root = empty("golfer")
    m = MB()
    V = Vector

    def Ry(a): return Matrix.Rotation(a, 3, 'Y')
    def Rx(a): return Matrix.Rotation(a, 3, 'X')

    def shoe(ball, yaw, heel):
        R = Ry(yaw) @ Rx(heel)
        T = V((0, 0, 0.105))
        P = lambda x, y, z: V(ball) + Ry(yaw) @ T + R @ (V((x, y, z)) - T)
        m.box(P(0, 0.011, -0.045), (0.100, 0.022, 0.300), "sole", rot=R)
        m.box(P(0, 0.047, -0.060), (0.090, 0.050, 0.255), "shoes", rot=R)
        return P(0, 0.090, -0.125)
    ankle_l = shoe((0.24, 0, 0.10), 0.35, 0.0)
    ankle_r = shoe((-0.24, 0, -0.16), -0.30, 0.55)

    def leg(hip, ankle):
        hip = V(hip)
        knee = ik2(hip, ankle, 0.445, 0.435, (0.0, 0.0, 1.0))
        sh = (V(ankle) - knee).normalized()
        below = knee + sh * 0.16
        limb(m, hip, knee, 0.094, 0.086, 5, "trousers")                           # plus-fours: thigh, then the baggy knee gather
        limb(m, knee - (knee - hip).normalized() * 0.03, below, 0.092, 0.074, 5, "trousers")
        limb(m, below - sh * 0.01, ankle, 0.045, 0.036, 4, "sock")
    leg((0.095, 0.905, 0.03), ankle_l)
    leg((-0.085, 0.915, 0.0), ankle_r)

    ts = [(0.86, 0.02, 0.025, 0.158, 0.106, 0.05), (1.00, 0.02, 0.02, 0.152, 0.100, 0.08),
          (1.05, 0.015, 0.015, 0.152, 0.100, 0.09), (1.38, -0.005, -0.03, 0.205, 0.118, 0.17),
          (1.50, -0.01, -0.045, 0.075, 0.075, 0.17)]
    rings = [ring_pts((cx, y, cz), rx, rz, 8, yaw=yw, phase=math.pi / 8) for y, cx, cz, rx, rz, yw in ts]
    loft_mat(m, rings, lambda i, j: "trousers" if i == 0 else ("belt" if i == 1 else "shirt"))
    limb(m, (-0.010, 1.490, -0.045), (-0.005, 1.630, -0.047), 0.047, 0.042, 5, "skin")                  # neck

    # ---- round head: ellipsoid, cap with a peak, nose, eyes
    hc = V((-0.005, 1.710, -0.040))
    blob(m, hc, (0.084, 0.104, 0.096), "skin", subdiv=2, rot=Ry(0.12))
    bx(m, hc.x - 0.014, hc.x + 0.014, hc.y - 0.040, hc.y + 0.004, hc.z + 0.088, hc.z + 0.110, "skin")
    bx(m, hc.x - 0.050, hc.x + 0.050, hc.y + 0.012, hc.y + 0.028, hc.z + 0.086, hc.z + 0.092, "eye")            # eye band under the peak
    for sx in ():
        pass
    m.lathe(hc + V((0, 0.020, 0)), (0, 1, 0), [(0.084, 0.0), (0.090, 0.040), (0.074, 0.085), (0, 0.105)], 6, "cap")
    m.box(hc + V((0, 0.040, 0.105)), (0.136, 0.010, 0.085), "cap", rot=Rx(0.20))

    # ---- arms: IK to both hands on the grip
    d = V((0.22, 0.60, -0.77)).normalized()                   # grip -> club head: up and back past the lead shoulder
    hand_l = V((0.13, 1.50, 0.15))
    hand_r = hand_l + d * 0.13
    sh_l, sh_r = V((0.190, 1.415, -0.075)), V((-0.205, 1.415, -0.005))
    HB = basis(V((0, 1, 0)).cross(d), d)

    def arm(sh, hand, pole, glove):
        el = ik2(sh, hand, 0.290, 0.270, pole)
        limb(m, sh, el, 0.058, 0.046, 5, "shirt")
        limb(m, el, hand, 0.042, 0.031, 4, "skin")
        m.box(hand, (0.070, 0.062, 0.095), "glove" if glove else "skin", rot=HB)
    arm(sh_l, hand_l, (0.6, -0.7, 0.2), True)
    arm(sh_r, hand_r, (0.0, -0.6, 1.0), False)

    # ---- full-length driver (1.10 m): grip, shaft, head
    G = hand_l - d * 0.07
    club(m, G, d, 'driver', (0.0, 0.2, 1.0), length=1.10, detail=1)
    m.to_object("golfer_mesh", parent=root, smooth=40)
