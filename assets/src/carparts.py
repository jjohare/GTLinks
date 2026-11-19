"""Car sub-assemblies: wheels (tread, rims, brake discs), calipers, underside, interior."""
import math
from mathutils import Vector, Matrix
from gtl import MB, make_mat, bx


def car_materials(spec):
    make_mat("paint", spec["paint"], metallic=0.35, rough=0.36)
    make_mat("glass", (0.45, 0.58, 0.66), metallic=0.0, rough=0.04, alpha=0.30)
    make_mat("headlight", (1.0, 0.96, 0.82), rough=0.1, emit=(1.0, 0.93, 0.70), emit_strength=1.0)
    make_mat("taillight", (0.62, 0.04, 0.05), rough=0.25, emit=(0.5, 0.0, 0.0), emit_strength=0.6)
    make_mat("trim", (0.06, 0.065, 0.07), rough=0.75)
    make_mat("chrome", (0.80, 0.82, 0.84), metallic=1.0, rough=0.2)
    make_mat("tyre", (0.045, 0.045, 0.05), rough=0.92)
    make_mat("rim", (0.70, 0.72, 0.75), metallic=0.9, rough=0.30)
    make_mat("rimdark", (0.09, 0.09, 0.10), metallic=0.4, rough=0.6)
    make_mat("plate", (0.9, 0.9, 0.85), rough=0.5)
    make_mat("underbody", (0.035, 0.035, 0.04), rough=0.9)
    make_mat("underplate", (0.16, 0.16, 0.17), metallic=0.3, rough=0.7)
    make_mat("steel", (0.45, 0.46, 0.48), metallic=0.85, rough=0.45)
    make_mat("exhaust", (0.36, 0.34, 0.32), metallic=0.8, rough=0.5)
    make_mat("spring", (0.85, 0.55, 0.08), metallic=0.3, rough=0.5)
    make_mat("disc", (0.52, 0.5, 0.48), metallic=0.9, rough=0.4)
    make_mat("caliper", (0.78, 0.08, 0.06), metallic=0.2, rough=0.45)
    make_mat("rubber", (0.03, 0.03, 0.035), rough=0.95)
    make_mat("seat", (0.17, 0.15, 0.13), rough=0.9)
    make_mat("seat_trim", (0.45, 0.36, 0.26), rough=0.85)
    make_mat("dash", (0.09, 0.09, 0.10), rough=0.8)
    make_mat("doorcard", (0.15, 0.14, 0.13), rough=0.9)
    make_mat("headliner", (0.60, 0.58, 0.54), rough=0.95)
    make_mat("carpet", (0.07, 0.07, 0.075), rough=1.0)
    make_mat("wheel_leather", (0.03, 0.03, 0.035), rough=0.6)


# ----------------------------------------------------------------------------- wheels
def build_wheel(c, sx, sz, style):
    """Wheel node geometry in the game frame, centred at the hub; axle along X, outward = sx."""
    R, ww = c.r, c.ww
    hw = ww / 2
    cx, cy, cz = sx * c.tr / 2, R, sz * c.wb / 2
    rr = R * style.get("rim_frac", 0.62)
    mb = MB()
    ax = (sx, 0, 0)
    O = (cx, cy, cz)
    span = R - rr
    prof = [(rr, -0.80 * hw), (rr + 0.22 * span, -0.96 * hw), (rr + 0.62 * span, -hw), (R - 0.035, -0.92 * hw),
            (R - 0.006, -0.78 * hw),
            (R, -0.70 * hw), (R, -0.40 * hw), (R - 0.013, -0.34 * hw), (R - 0.013, -0.22 * hw), (R, -0.17 * hw),
            (R, 0.17 * hw), (R - 0.013, 0.22 * hw), (R - 0.013, 0.34 * hw), (R, 0.40 * hw), (R, 0.70 * hw),
            (R - 0.006, 0.78 * hw), (R - 0.035, 0.92 * hw), (rr + 0.62 * span, hw), (rr + 0.22 * span, 0.96 * hw),
            (rr, 0.80 * hw)]
    SEG = 36

    def mod(pi, i):
        if 5 <= pi <= 14:
            lane = 0 if pi <= 8 else (1 if pi <= 11 else 2)
            return 1.0 - 0.011 * (((i + lane) // 2) % 2) if pi not in (7, 8, 11, 12) else 1.0
        return 1.0
    mb.lathe(O, ax, prof, SEG, "tyre", closed=True, mod=mod)
    # rim barrel with lips
    mb.lathe(O, ax, [(rr - 0.045, -0.80 * hw), (rr + 0.012, -0.80 * hw), (rr + 0.012, -0.55 * hw),
                     (rr - 0.02, -0.5 * hw), (rr - 0.02, 0.62 * hw), (rr + 0.016, 0.66 * hw), (rr + 0.016, 0.84 * hw),
                     (rr - 0.045, 0.84 * hw)], SEG, "rim", closed=True)
    # dark dish behind the spokes
    mb.lathe(O, ax, [(0, 0.05 * hw), (rr - 0.04, 0.05 * hw), (rr - 0.04, 0.0), (0, 0.0)], 32, "rimdark")
    kind = style["wheel"]
    n = style["spokes"]
    hubr = 0.075
    if kind == "aero":
        mb.lathe(O, ax, [(0, 0.80 * hw), (rr * 0.55, 0.80 * hw), (rr - 0.02, 0.60 * hw), (rr - 0.02, 0.50 * hw),
                         (0, 0.50 * hw)], 32, "rim")
        for i in range(n):
            a = (i + 0.5) * 2 * math.pi / n
            rad = Vector((0, math.sin(a), math.cos(a)))
            mb.box(Vector(O) + Vector((sx * 0.81 * hw, 0, 0)) + rad * rr * 0.62, (0.012, 0.045, rr * 0.30), "rimdark",
                   rot=Matrix.Rotation(-a, 3, 'X'))
    else:
        for i in range(n):
            a = i * 2 * math.pi / n
            for twin in ((-1, 1) if kind == "twin" else (0,)):
                a2 = a + twin * 0.11
                rad = Vector((0, math.sin(a2), math.cos(a2)))
                sw = 0.055 if kind == "spoke6" else 0.034 if kind == "twin" else 0.05
                ctr = Vector(O) + Vector((sx * hw * 0.50, 0, 0)) + rad * rr * 0.54
                rot = Matrix.Rotation(-a2, 3, 'X')
                if kind == "turbine":
                    rot = Matrix.Rotation(-a2, 3, 'X') @ Matrix.Rotation(0.35, 3, 'Z')
                mb.box(ctr, (0.06, sw, rr * 0.92), "rim", bevel=0.012, rot=rot)
        mb.lathe(O, ax, [(0, 0.78 * hw), (hubr, 0.74 * hw), (hubr + 0.02, 0.5 * hw), (0, 0.5 * hw)], 20, "rim")
        for i in range(5):
            a = i * 2 * math.pi / 5 + 0.3
            p = Vector(O) + Vector((sx * 0.79 * hw, 0, 0)) + Vector((0, math.sin(a), math.cos(a))) * 0.045
            mb.lathe(p, ax, [(0.012, -0.01), (0.012, 0.012)], 6, "steel")
    # brake disc (vented look: ring + radial slots), inboard
    dr = rr * 0.80
    mb.lathe(O, ax, [(0.10, -0.50 * hw), (dr, -0.50 * hw), (dr, -0.36 * hw), (0.10, -0.36 * hw)], 40, "disc", closed=True)
    mb.lathe(O, ax, [(0, -0.36 * hw), (0.10, -0.36 * hw), (0.10, -0.62 * hw), (0, -0.62 * hw)], 16, "disc")
    for i in range(18):
        a = i * 2 * math.pi / 18
        rad = Vector((0, math.sin(a), math.cos(a)))
        mb.box(Vector(O) + Vector((sx * -0.43 * hw, 0, 0)) + rad * (dr * 0.78), (0.005, 0.012, dr * 0.34), "trim",
               rot=Matrix.Rotation(-a, 3, 'X'))
    return mb, O


def build_caliper(c, sx, sz, style):
    R, ww = c.r, c.ww
    hw = ww / 2
    cx, cy, cz = sx * c.tr / 2, R, sz * c.wb / 2
    rr = R * style.get("rim_frac", 0.62)
    dr = rr * 0.80
    mb = MB()
    a = math.radians(70)             # rear-upper position
    rad = Vector((0, math.sin(a), -math.cos(a)))
    ctr = Vector((cx + sx * (-0.43 * hw), cy, cz)) + rad * dr * 0.80
    rot = Matrix.Rotation(a + math.pi / 2, 3, 'X')
    mb.box(ctr, (0.115, 0.075, dr * 0.45), "caliper", bevel=0.012, rot=rot)
    mb.box(ctr + Vector((sx * 0.065, 0, 0)), (0.02, 0.05, 0.05), "steel")
    # hub carrier and bearing nose behind the disc
    mb.lathe((cx, cy, cz), (sx, 0, 0), [(0.07, -0.95 * hw), (0.07, -0.60 * hw)], 12, "steel")
    return mb, (cx, cy, cz)


# ----------------------------------------------------------------------------- underside
def helix(mb, centre, r, height, turns, wire, mname, segs_per_turn=10, tilt=(0, 0)):
    n = int(turns * segs_per_turn)
    pts = []
    for i in range(n + 1):
        t = i / n
        a = 2 * math.pi * turns * t
        p = Vector((centre[0] + r * math.cos(a) + tilt[0] * (t - 0.5) * height,
                    centre[1] + (t - 0.5) * height,
                    centre[2] + r * math.sin(a) + tilt[1] * (t - 0.5) * height))
        pts.append(p)
    for a, b in zip(pts[:-1], pts[1:]):
        mb.pipe(a, b, wire, 4, mname)


def build_underside(c, cage, st):
    mb = MB()
    zf, zr = c.wb / 2, -c.wb / 2
    f_mid = 0.5
    yb = cage.yb(f_mid)
    L = c.L
    # tunnel and ribs
    zA, zB = c.zF - 0.55, c.zR + 0.35
    mb.box((0, yb - 0.035, (zA + zB) / 2), (0.34, 0.08, abs(zA - zB)), "underplate", bevel=0.02)
    for x in (-0.62, -0.38, 0.38, 0.62):
        mb.box((x, yb - 0.012, (zA + zB) / 2), (0.05, 0.025, abs(zA - zB) - 0.3), "underplate", bevel=0.008)
    for z in (zf - 0.8, 0.0, zr + 0.6):
        mb.box((0, yb - 0.012, z), (c.bw * 1.5, 0.03, 0.06), "underplate", bevel=0.008)
    # engine bay: radiator, engine block, sump, gearbox
    mb.box((0, 0.74, c.zF - 0.42), (c.bw * 1.2, 0.5, 0.07), "underplate", bevel=0.01)            # radiator
    for k in range(9):
        mb.box((-0.55 + k * 0.1375, 0.74, c.zF - 0.455), (0.012, 0.46, 0.02), "steel")
    mb.box((0, yb + 0.30, zf - 0.30), (0.62, 0.46, 0.78), "underplate", bevel=0.04)             # block
    for k in range(4):
        mb.box((0, yb + 0.58, zf - 0.55 + k * 0.17), (0.50, 0.09, 0.10), "steel", bevel=0.01)   # cam covers
    mb.box((0, yb - 0.10, zf - 0.30), (0.46, 0.11, 0.52), "steel", bevel=0.02)                   # sump
    mb.cyl((0, yb + 0.03, zf - 1.0), (0, 0, 1), 0.17, 0.75, 16, "underplate")                    # gearbox
    mb.cyl((0, yb - 0.02, zf - 1.55), (0, 0, 1), 0.13, 0.45, 14, "steel")                        # transfer case
    # driveshafts
    mb.pipe((0, yb - 0.04, zf - 1.7), (0, yb - 0.04, zr + 0.25), 0.045, 8, "steel")
    mb.pipe((0, yb - 0.01, zf - 0.55), (0, yb - 0.01, zf - 0.05), 0.04, 8, "steel")
    for z in (zf - 1.75, zr + 0.28, zf - 0.55):
        mb.box((0, yb - 0.04, z), (0.09, 0.09, 0.09), "steel", bevel=0.015)
    # axles, diffs, subframes
    ay = c.r - 0.03
    for z in (zf, zr):
        s = 1 if z > 0 else -1
        mb.lathe((0, ay - 0.04, z), (1, 0, 0), [(0.0, -0.14), (0.12, -0.12), (0.145, 0.0), (0.12, 0.12), (0.0, 0.14)], 16, "underplate")
        mb.lathe((0, ay - 0.04, z + s * 0.14), (0, 0, 1), [(0.075, -0.03), (0.075, 0.03)], 12, "steel")
        for sx in (1, -1):
            mb.pipe((sx * 0.12, ay - 0.04, z), (sx * (c.tr / 2 - c.ww / 2 - 0.02), c.r, z), 0.032, 8, "steel")     # half shaft
        # subframe: two rails + two cross members
        for sx in (1, -1):
            mb.box((sx * 0.38, yb - 0.02, z), (0.06, 0.06, 0.86), "underplate", bevel=0.012)
        for dz in (-0.38, 0.38):
            mb.box((0, yb - 0.02, z + dz), (0.82, 0.06, 0.07), "underplate", bevel=0.012)
        # suspension arms, spring, damper, anti-roll bar
        for sx in (1, -1):
            hub = Vector((sx * (c.tr / 2 - c.ww / 2 - 0.045), c.r, z))
            for dz in (-0.30, 0.30):
                mb.pipe(Vector((sx * 0.36, yb - 0.03, z + dz)), hub + Vector((0, -0.09, dz * 0.12)), 0.022, 6, "steel")
            for dz in (-0.2, 0.2):
                mb.pipe(Vector((sx * 0.46, yb + 0.14, z + dz)), hub + Vector((0, 0.16, dz * 0.1)), 0.016, 6, "steel")
            mb.box(hub + Vector((0, 0.03, 0)), (0.05, 0.24, 0.10), "steel", bevel=0.01)                              # knuckle
            sp = Vector((sx * 0.50, yb + 0.12, z + 0.05 * s))
            helix(mb, sp, 0.045, 0.30, 3.5, 0.011, "spring", segs_per_turn=8, tilt=(sx * 0.05, 0))
            mb.pipe(sp + Vector((0, -0.18, 0)), sp + Vector((sx * 0.02, 0.18, 0)), 0.018, 8, "underplate")
            mb.pipe(sp + Vector((0, -0.03, 0)), sp + Vector((sx * 0.02, 0.20, 0)), 0.009, 6, "steel")
            mb.pipe(Vector((sx * 0.33, yb - 0.01, z - 0.42 * s)), hub + Vector((0, 0.01, -0.42 * s)), 0.012, 6, "steel")  # arb link
        mb.pipe(Vector((-0.33, yb - 0.01, z - 0.42 * s)), Vector((0.33, yb - 0.01, z - 0.42 * s)), 0.014, 8, "steel")
    # steering rack and tie rods (front)
    mb.pipe((-0.42, yb - 0.01, zf - 0.20), (0.42, yb - 0.01, zf - 0.20), 0.025, 8, "steel")
    for sx in (1, -1):
        mb.pipe((sx * 0.42, yb - 0.01, zf - 0.20), (sx * (c.tr / 2 - c.ww / 2 - 0.05), c.r - 0.02, zf - 0.12), 0.012, 6, "steel")
    # exhaust (twin) with catalysts, silencers, hangers and tips
    for sx in (1, -1):
        x = sx * 0.27
        pts = [(sx * 0.18, yb + 0.02, zf - 0.75), (x, yb - 0.03, zf - 1.3), (x, yb - 0.075, zf - 2.0)]
        for a, b in zip(pts[:-1], pts[1:]):
            mb.pipe(a, b, 0.032, 8, "exhaust")
        mb.cyl((x, yb - 0.075, zf - 1.75), (0, 0, 1), 0.065, 0.36, 14, "exhaust")                # catalyst
        zs = zr + 0.15
        mb.pipe((x, yb - 0.075, zf - 1.95), (x, yb - 0.075, zr + 1.05), 0.03, 8, "exhaust")
        mb.cyl((x, yb - 0.065, zr + 0.65), (0, 0, 1), 0.085, 0.80, 16, "exhaust", scale=(1.0, 0.82))   # silencer
        mb.pipe((x, yb - 0.075, zr + 0.25), (sx * 0.34, yb - 0.04, c.zR + 0.12), 0.027, 8, "exhaust")
        for z in (zf - 1.5, zr + 1.0, zr + 0.3):
            mb.box((x, yb + 0.0, z), (0.02, 0.07, 0.02), "steel")
        mb.box((x, yb - 0.065, zr + 0.65), (0.30, 0.012, 0.9), "underplate")                      # heat shield
    # fuel tank, straps, lines
    zt = zr + 1.35
    mb.box((0, yb - 0.08, zt), (0.85, 0.17, 0.60), "underplate", bevel=0.03)
    for dz in (-0.2, 0.2):
        mb.box((0, yb - 0.17, zt + dz), (0.88, 0.015, 0.04), "steel")
    mb.pipe((0.45, yb - 0.02, zt), (0.45, yb - 0.02, zf - 1.2), 0.008, 4, "rubber")
    mb.pipe((0.48, yb - 0.02, zt), (0.48, yb - 0.02, zf - 0.8), 0.008, 4, "steel")
    # spare wheel well + spare tyre (lowered under the tail)
    zsw = c.zR + 0.95
    rs = c.r * 0.92
    mb.lathe((0, yb - 0.13, zsw), (0, 1, 0), [(rs * 0.62, -0.11), (rs - 0.04, -0.12), (rs, -0.07), (rs, 0.07), (rs - 0.04, 0.12),
                                                  (rs * 0.62, 0.11)], 36, "tyre", closed=True)
    mb.lathe((0, yb - 0.13, zsw), (0, 1, 0), [(0, -0.10), (rs * 0.60, -0.10), (rs * 0.60, 0.06), (0, 0.06)], 24, "rim")
    mb.lathe((0, yb - 0.04, zsw), (0, 1, 0), [(rs + 0.07, -0.05), (rs + 0.07, 0.04), (rs + 0.02, 0.04), (rs + 0.02, -0.05)], 28, "underplate", closed=True)
    mb.pipe((0, yb - 0.25, zsw), (0, yb - 0.02, zsw), 0.012, 6, "steel")
    # skid plate and tow hooks
    mb.box((0, 0.285, c.zF - 0.80), (0.95, 0.025, 0.55), "steel", bevel=0.01)
    for z, s_ in ((c.zF - 0.12, 1), (c.zR + 0.12, -1)):
        mb.box((0.40, 0.34, z), (0.05, 0.05, 0.12), "steel", bevel=0.01)
    return mb


# ----------------------------------------------------------------------------- interior
def seat(mb, x, z, y0, width=0.52, depth=0.50, back_h=0.66, rear_facing=False, head=True):
    """Front-facing seat; cushion + bolsters + backrest + headrest. y0 = cushion bottom."""
    mb.box((x, y0 + 0.07, z), (width, 0.14, depth), "seat", bevel=0.04)
    for sx in (-1, 1):
        mb.box((x + sx * (width / 2 - 0.03), y0 + 0.14, z), (0.07, 0.07, depth * 0.92), "seat_trim", bevel=0.02)
    a = math.radians(-13)
    mb.box((x, y0 + 0.14 + back_h / 2, z - depth / 2 + 0.02), (width, back_h, 0.14), "seat", bevel=0.045,
           rot=Matrix.Rotation(a, 3, 'X'))
    for sx in (-1, 1):
        mb.box((x + sx * (width / 2 - 0.03), y0 + 0.14 + back_h * 0.5, z - depth / 2 + 0.06), (0.07, back_h * 0.8, 0.1), "seat_trim",
               bevel=0.02, rot=Matrix.Rotation(a, 3, 'X'))
    if head:
        yh = y0 + 0.14 + back_h + 0.06
        mb.box((x, yh, z - depth / 2 - 0.10), (0.27, 0.17, 0.10), "seat", bevel=0.03, rot=Matrix.Rotation(a, 3, 'X'))
        for sx in (-0.07, 0.07):
            mb.pipe((x + sx, yh - 0.1, z - depth / 2 - 0.07), (x + sx, yh - 0.02, z - depth / 2 - 0.09), 0.008, 5, "steel")


def build_interior_parts(c, cage, st, mb):
    """Seats, dashboard, wheel, console; `mb` already holds the inner shell."""
    fs = st["seat_rows"]
    L = c.L
    yb = cage.yb(0.5)
    yfl = yb + 0.10
    zA = c.zF - st["wind"][0] * L
    zC = c.zF - st["rear_glass"][1] * L
    # carpet floor
    x_in = c.bw * 0.93
    mb.box((0, yfl, (zA + zC) / 2 - 0.1), (2 * x_in, 0.03, abs(zA - zC) - 0.4), "carpet", bevel=0.01)
    mb.box((0, yfl + 0.07, (zA + zC) / 2 - 0.1), (0.26, 0.14, abs(zA - zC) - 0.9), "carpet", bevel=0.05)   # tunnel
    for i, f in enumerate(fs):
        z = c.zF - f * L
        ys = yfl + 0.22
        if i == 0:
            for sx in (1, -1):
                seat(mb, sx * 0.40, z, ys)
            # centre console + handbrake
            mb.box((0, ys + 0.18, z + 0.05), (0.20, 0.28, 0.62), "dash", bevel=0.03)
            mb.box((0, ys + 0.34, z + 0.20), (0.07, 0.04, 0.16), "steel", bevel=0.01)
        else:
            for sx in (-0.58, 0, 0.58):
                seat(mb, sx, z, ys + 0.02, width=0.54, depth=0.50, back_h=0.64)
    # dashboard
    zd = zA - 0.30
    yb_ = cage.belt(st["wind"][0]) + 0.02
    mb.box((0, yb_ - 0.05, zd), (2 * x_in - 0.1, 0.22, 0.40), "dash", bevel=0.06)
    mb.box((0, yb_ + 0.10, zd - 0.02), (2 * x_in - 0.14, 0.05, 0.32), "dash", bevel=0.02)
    sx_d = 0.40                                    # driver on the left (+X)
    mb.box((sx_d, yb_ + 0.12, zd - 0.05), (0.52, 0.16, 0.20), "dash", bevel=0.04)       # instrument hood
    for dx in (-0.15, 0.0, 0.15):
        mb.lathe((sx_d + dx, yb_ + 0.07, zd - 0.16), (0, 0.3, -1), [(0.0, 0.0), (0.06, 0.0), (0.06, -0.01), (0.0, -0.01)], 12, "carpet")
    mb.box((0, yb_ - 0.06, zd - 0.12), (0.26, 0.34, 0.14), "dash", bevel=0.03)         # centre stack
    for dx in (-0.55, -0.1, 0.1, 0.55):
        mb.box((dx, yb_ + 0.065, zd - 0.18), (0.12, 0.02, 0.05), "trim")               # vents
    # steering column and wheel (tilted)
    mb.pipe((sx_d, yb_ - 0.02, zd - 0.12), (sx_d, yb_ + 0.12, zd - 0.42), 0.035, 8, "dash")
    ctr = Vector((sx_d, yb_ + 0.14, zd - 0.46))
    mb.lathe(ctr, (0, 0.35, -1), [(0.185, -0.015), (0.185, 0.015), (0.155, 0.015), (0.155, -0.015)], 24, "wheel_leather", closed=True)
    mb.lathe(ctr, (0, 0.35, -1), [(0, -0.03), (0.05, -0.03), (0.05, 0.02), (0, 0.02)], 12, "wheel_leather")
    for ang in (0, 120, 240):
        a = math.radians(ang + 90)
        mb.pipe(ctr, ctr + Vector((0.16 * math.cos(a), 0.16 * math.sin(a) * 0.94, 0.16 * math.sin(a) * 0.34)), 0.011, 5, "wheel_leather")
    # pedals
    for dx in (0.28, 0.40, 0.52):
        mb.box((dx, yfl + 0.18, zd - 0.12), (0.07, 0.015, 0.05), "steel")
    # rear-view mirror
    mb.box((0, cage.T(st["wind"][1]) - 0.30, c.zF - st["wind"][1] * L - 0.06), (0.22, 0.06, 0.04), "dash", bevel=0.01)
    # parcel shelf / cargo floor
    mb.box((0, yfl + 0.22, c.zF - (st["rear_glass"][0]) * L + 0.35), (2 * x_in - 0.1, 0.03, 0.7), "carpet")
