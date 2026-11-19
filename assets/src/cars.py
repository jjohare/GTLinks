"""The four player SUVs and the patrol car.  Every dimension comes from assets/cars.json; the STYLES table
holds design choices only (proportions inside the given envelope, curvature, trim).  Original designs:
no badges, emblems or script anywhere.

Game frame: +Z forward, +Y up, +X left.  Wheel centres: x = +/-track/2, y = r, z = +/-wheelbase/2.

How a car is made (machinery in carkit.py, sub-assemblies in carparts.py):

  tub        one profile swept round a plan outline: nose -> left flank -> tail.  Rows run from the sill
             (or the wheel-arch edge) up to the shoulder, then roll inward to the belt line.  The nose
             columns are the front bumper fascia, the tail columns below the tailgate the rear bumper.
  glasshouse rows lofted from the belt loop to the roof loop; windscreen, side and rear glass and the
             pillars are cell tags on that grid, so pillars have real rake and tumblehome.
  roof       Coons patch inside the roof loop, crowned across the car.
  bonnet     Coons patch inside the shut line that runs round the nose and back to the windscreen base.
"""
import math
import bpy
from mathutils import Vector, Matrix
from gtl import make_mat, MATS, empty, B, MB
import carkit as K
from carkit import Curve, Panel, Surf, Shell, V, lerp, clamp, smooth01, subdiv, corner_pts, plan_normals, coons
import carparts

NL = 9                    # lower tub rows: sill/arch edge .. shoulder
FR = [0, .07, .16, .28, .42, .57, .72, .87, 1.0]
NROLL = 3                 # rows rolling from the shoulder to the belt
TOP = NL - 1 + NROLL      # index of the belt row
NC = 6                    # columns per plan corner
NC1 = 4                   # windscreen-corner columns that are not shared with the tub
GT = [0.0, 0.06, 0.36, 0.66, 0.90]   # glasshouse rows as fractions belt -> roof corner

# ------------------------------------------------------------------ style tables
# Lengths in metres, drawn against the envelope in REF; a changed cars.json rescales the design.
# 'rows' are nine (fraction of height, inset) pairs describing the nose or tail section from its
# bottom edge to its shoulder; a negative inset stands proud of the plan outline.
STYLES = {
    # 2009: upright, slab-shouldered, chrome-heavy, square-jawed
    "escapade_2009": dict(
        fo=0.98, flare=0.024, arch_p=2.5, arch_gap=0.07, flare_w=0.10,
        waist=0.60, tuck=0.06, sh_drop=0.10, sh_in=0.014, sh_e=1.4, roll=0.35, belt_in=0.055, wing_in=0.125,
        belt=[(-9, 1.165), (0.2, 1.165), (1.3, 1.15), (9, 1.115)], sharp_rows=[8], crease=(0.47, 0.012),
        front=dict(ax=0.15, az=0.17, bow=0.05, p=2.6, yb=0.34, sh_drop=0.07, nose_in=0.10,
                   rows=[(0, .11), (.10, .05), (.18, .0), (.29, -.022), (.40, .0), (.46, .04), (.70, .034), (.92, .034), (1, .04)],
                   xbreaks=[0.22, 0.50, 0.56]),
        rear=dict(ax=0.15, az=0.15, bow=0.04, p=2.6, yb=0.40, sh_drop=0.10, tail_in=0.05,
                  rows=[(0, .09), (.10, .03), (.2, 0), (.32, -.018), (.43, 0), (.48, .03), (.68, .026), (.88, .026), (1, .03)],
                  xbreaks=[0.30, 0.62]),
        gh=dict(zA=0.62, cowl=(0.20, 0.16, 0.07), cowl_rise=0.03, zh=0.30, hdr=(0.16, 0.14, 0.05), tum=0.125, tum_r=0.0,
                rear_run=0.17, rhdr=(0.15, 0.12, 0.04), shear_r='D', crown=0.035, rc=0.05,
                roof=[(0.30, 1.835), (-0.25, 1.888), (-1.4, 1.888), (-2.5, 1.86)]),
        zB=(-0.20, -0.34), zC=(-0.93, -1.06), zD=0.44, door_gap=0.10,
        bonnet_arc=0.012, bonnet_dome=0.022, clamshell=False,
        pillars='paint', belt_trim='chrome', sill='chrome', cladding=None, roofpanel=None, rails='chrome', handles='chrome',
        grille=dict(x=0.50, rows=(5, 8), kind='eggcrate', mat='chrome'),
        lamp=dict(x0=0.56, x1=0.83, rows=(5, 8), p=3.2), intake=dict(x=0.50, rows=(0, 2)),
        bumper_chrome=True, tail='pillar', wheel=dict(wheel='spoke6', spokes=6, rim_frac=0.66),
        seat='#b9a888', seat_trim='#8c7a5c', tips=1, boards=True, third_row=True,
    ),
    # 2017: large, rounded and smooth, long glasshouse
    "glug_2017": dict(
        fo=0.93, over=0.012, flare=0.02, arch_p=2.0, arch_gap=0.06, flare_w=0.13,
        waist=0.60, tuck=0.07, sh_drop=0.14, sh_in=0.034, sh_e=2.0, roll=1.0, belt_in=0.06, wing_in=0.12,
        belt=[(-9, 1.13), (-2.2, 1.125), (0.4, 1.085), (1.2, 1.06), (9, 0.97)], sharp_rows=[], crease=None,
        front=dict(ax=0.40, az=0.36, bow=0.10, p=2.0, yb=0.30, sh_drop=0.09, nose_in=0.13,
                   rows=[(0, .12), (.09, .05), (.2, .012), (.32, .0), (.44, .006), (.52, .02), (.72, .03), (.9, .045), (1, .06)],
                   xbreaks=[0.30, 0.40, 0.46]),
        rear=dict(ax=0.34, az=0.30, bow=0.08, p=2.0, yb=0.36, sh_drop=0.12, tail_in=0.07,
                  rows=[(0, .10), (.10, .04), (.2, .008), (.32, 0), (.44, .008), (.5, .03), (.68, .03), (.86, .045), (1, .06)],
                  xbreaks=[0.30, 0.50]),
        gh=dict(zA=0.74, cowl=(0.28, 0.24, 0.12), cowl_rise=0.045, zh=0.20, hdr=(0.26, 0.22, 0.10), tum=0.17, tum_r=0.05,
                rear_run=0.46, rhdr=(0.28, 0.22, 0.08), shear_r='C2', crown=0.05, rc=0.085,
                roof=[(0.20, 1.765), (-0.45, 1.848), (-1.5, 1.83), (-2.3, 1.755)]),
        zB=(-0.20, -0.31), zC=(-1.02, -1.11), zD=0.60, door_gap=0.10,
        bonnet_arc=0.03, bonnet_dome=0.0, clamshell=False,
        pillars='gloss', belt_trim='chrome', sill='paint', cladding=None, roofpanel=(0.12, 0.5), rails='steel', handles='paint',
        grille=dict(x=0.40, rows=(5, 8), kind='bars', mat='chrome'),
        lamp=dict(x0=0.46, x1=0.80, rows=(5, 8), p=2.3), intake=dict(x=0.62, rows=(1, 3)),
        bumper_chrome=False, tail='wrap', wheel=dict(wheel='twin', spokes=5, rim_frac=0.68),
        seat='#2b2d31', seat_trim='#6a6e76', tips=2, boards=False, third_row=True,
    ),
    # 2021: sleeker, falling roofline, wide low grille
    "genesips_2021": dict(
        fo=0.90, flare=0.03, arch_p=2.0, arch_gap=0.055, flare_w=0.12,
        waist=0.58, tuck=0.065, sh_drop=0.11, sh_in=0.03, sh_e=2.0, roll=0.8, belt_in=0.06, wing_in=0.12,
        belt=[(-9, 1.13), (-2.0, 1.115), (-0.3, 1.045), (0.6, 1.025), (1.3, 0.99), (9, 0.92)], sharp_rows=[], crease=(0.52, 0.010),
        front=dict(ax=0.32, az=0.28, bow=0.09, p=2.2, yb=0.28, sh_drop=0.07, nose_in=0.12,
                   rows=[(0, .11), (.10, .04), (.22, .006), (.36, .0), (.50, .004), (.62, .012), (.76, .022), (.9, .04), (1, .055)],
                   xbreaks=[0.44, 0.50, 0.56]),
        rear=dict(ax=0.30, az=0.28, bow=0.08, p=2.1, yb=0.36, sh_drop=0.10, tail_in=0.08,
                  rows=[(0, .10), (.10, .04), (.2, .008), (.32, 0), (.44, .008), (.5, .03), (.68, .03), (.86, .04), (1, .055)],
                  xbreaks=[0.30, 0.52]),
        gh=dict(zA=0.60, cowl=(0.28, 0.24, 0.12), cowl_rise=0.04, zh=0.0, hdr=(0.26, 0.22, 0.10), tum=0.19, tum_r=0.07,
                rear_run=0.80, rhdr=(0.28, 0.22, 0.08), shear_r='C2', crown=0.05, rc=0.08,
                roof=[(0.0, 1.655), (-0.45, 1.718), (-1.2, 1.675), (-1.9, 1.555), (-2.4, 1.49)]),
        zB=(-0.28, -0.39), zC=(-1.02, -1.12), zD=0.78, door_gap=0.10,
        bonnet_arc=0.03, bonnet_dome=0.0, clamshell=False,
        pillars='gloss', belt_trim='chrome', sill='trim', cladding=0.06, roofpanel=(0.10, 0.62), rails='gloss', handles='paint',
        grille=dict(x=0.56, rows=(2, 6), kind='slats', mat='gloss'),
        lamp=dict(x0=0.50, x1=0.84, rows=(6, 8), p=2.4), intake=dict(x=0.30, rows=(0, 1)),
        bumper_chrome=False, tail='bar', wheel=dict(wheel='turbine', spokes=10, rim_frac=0.70),
        seat='#7a3b2e', seat_trim='#2a2222', tips=2, boards=False, third_row=False,
    ),
    # 2026: clean and minimal, flush surfaces, floating roof, clamshell bonnet
    "rangeroller_2026": dict(
        fo=0.88, flare=0.012, arch_p=2.2, arch_gap=0.07, flare_w=0.09,
        waist=0.66, tuck=0.04, sh_drop=0.065, sh_in=0.008, sh_e=1.3, roll=0.9, belt_in=0.05, wing_in=0.05,
        belt=[(-9, 1.175), (0.3, 1.165), (1.3, 1.15), (9, 1.125)], sharp_rows=[], crease=None,
        front=dict(ax=0.24, az=0.22, bow=0.06, p=2.7, yb=0.36, sh_drop=0.065, nose_in=0.05,
                   rows=[(0, .08), (.10, .03), (.22, .006), (.36, 0), (.50, 0), (.64, .004), (.78, .008), (.9, .012), (1, .016)],
                   xbreaks=[0.48, 0.56]),
        rear=dict(ax=0.22, az=0.20, bow=0.05, p=2.7, yb=0.40, sh_drop=0.065, tail_in=0.05,
                  rows=[(0, .08), (.10, .03), (.2, .006), (.32, 0), (.44, 0), (.52, .006), (.7, .008), (.88, .012), (1, .016)],
                  xbreaks=[0.30, 0.60]),
        gh=dict(zA=0.66, cowl=(0.20, 0.18, 0.08), cowl_rise=0.03, zh=0.17, hdr=(0.18, 0.16, 0.06), tum=0.15, tum_r=0.02,
                rear_run=0.34, rhdr=(0.18, 0.16, 0.05), shear_r='D', crown=0.03, rc=0.045,
                roof=[(0.17, 1.83), (-0.4, 1.868), (-1.5, 1.85), (-2.4, 1.80)]),
        zB=(-0.24, -0.33), zC=(-1.02, -1.10), zD=0.50, door_gap=0.10,
        bonnet_arc=0.016, bonnet_dome=0.0, clamshell=True,
        pillars='gloss', belt_trim='gloss', sill='paint', cladding=None, roofpanel=None, rails='gloss', handles='flush',
        grille=dict(x=0.48, rows=(6, 8), kind='slot', mat='gloss'),
        lamp=dict(x0=0.56, x1=0.84, rows=(6, 8), p=3.4), intake=dict(x=0.56, rows=(1, 3)),
        bumper_chrome=False, tail='blade', wheel=dict(wheel='aero', spokes=10, rim_frac=0.72),
        seat='#d8d2c4', seat_trim='#8a8478', tips=0, boards=False, third_row=False,
    ),
}
# envelopes the tables were drawn against: (length, roof height)
REF = {"escapade_2009": (5.14, 1.89), "glug_2017": (5.13, 1.85), "genesips_2021": (4.95, 1.72), "rangeroller_2026": (5.05, 1.87)}


# ------------------------------------------------------------------ materials
def car_materials(spec, S):
    make_mat("paint", spec["paint"], metallic=0.45, rough=0.32)
    make_mat("glass", (0.20, 0.29, 0.35), metallic=0.0, rough=0.04, alpha=0.36)
    make_mat("headlight", (1.0, 0.96, 0.82), rough=0.12, emit=(1.0, 0.93, 0.70), emit_strength=1.0)
    make_mat("taillight", (0.62, 0.03, 0.04), rough=0.22, emit=(0.55, 0.0, 0.0), emit_strength=0.7)
    make_mat("trim", (0.055, 0.058, 0.062), rough=0.72)
    make_mat("gloss", (0.02, 0.022, 0.026), metallic=0.1, rough=0.12)
    make_mat("chrome", (0.86, 0.87, 0.88), metallic=1.0, rough=0.16)
    make_mat("steel", (0.47, 0.48, 0.50), metallic=0.85, rough=0.45)
    make_mat("underplate", (0.15, 0.155, 0.165), metallic=0.3, rough=0.72)
    make_mat("exhaust", (0.38, 0.35, 0.32), metallic=0.8, rough=0.5)
    make_mat("spring", (0.85, 0.55, 0.08), metallic=0.3, rough=0.5)
    make_mat("tyre", (0.04, 0.04, 0.045), rough=0.9)
    make_mat("rim", (0.72, 0.74, 0.77), metallic=0.95, rough=0.26)
    make_mat("rimdark", (0.09, 0.09, 0.10), metallic=0.4, rough=0.6)
    make_mat("caliper", (0.74, 0.07, 0.05), metallic=0.2, rough=0.45)
    make_mat("plate", (0.90, 0.90, 0.86), rough=0.5)
    make_mat("seat", S["seat"], rough=0.7)
    make_mat("seat_trim", S["seat_trim"], rough=0.8)
    make_mat("cabin", (0.08, 0.082, 0.09), rough=0.85)
    make_mat("headliner", (0.55, 0.54, 0.51), rough=0.95)
    make_mat("amber", (0.95, 0.45, 0.05), rough=0.3, emit=(0.6, 0.2, 0.0), emit_strength=0.25)


def panels(S):
    body = dict(gap=0.0045, rim=0.02, rim_node='trim', rim_mat='trim', hole_rim=0.03)
    det = dict(gap=0.0045, rim=0.02, rim_mat='trim')
    pil = S['pillars']
    sill = S['sill']
    P = {
        'shell': Panel('body', 'paint', group='shell', **body),
        'door_f': Panel('body', 'paint', group='door_f', **body),
        'door_r': Panel('body', 'paint', group='door_r', **body),
        'tailgate': Panel('body', 'paint', group='tailgate', **body),
        'flap': Panel('body', 'paint', group='flap', **body),
        'sill': Panel('body', 'paint', group='shell', **body) if sill == 'paint'
        else Panel('chrome' if sill == 'chrome' else 'trim', sill, group='sill', gap=0.0045, rim=0.02, hole_rim=0.03),
        'clad': Panel('trim', 'trim', group='sill', gap=0.0045, rim=0.02, hole_rim=0.03),
        'pillar': Panel('body', 'paint', group='shell', **body) if pil == 'paint' else Panel('trim', 'gloss', group='pillar'),
        'belt': Panel('chrome' if S['belt_trim'] == 'chrome' else 'trim', S['belt_trim'], group='belt'),
        'cowl': Panel('trim', 'trim', group='cowl'),
        'glass_w': Panel('glass', 'glass', off=-0.012, frame=0.045, group='gw'),
        'glass_s': Panel('glass', 'glass', off=-0.012, frame=0.045, group='gs'),
        'glass_q': Panel('glass', 'glass', off=-0.012, frame=0.045, group='gq'),
        'glass_r': Panel('glass', 'glass', off=-0.012, frame=0.045, group='gr'),
        'roofglass': Panel('trim', 'gloss', off=-0.004, frame=0.012, group='roofglass'),
        'tail': Panel('taillights', 'taillight', off=-0.005, frame=0.014, group='tail'),
        'tailbar': Panel('taillights', 'taillight', off=-0.005, frame=0.014, group='tail'),
        'bf': Panel('bumper_front', 'paint', group='bf', hole_rim=0.06, **det),
        'bf_chrome': Panel('bumper_front', 'chrome', group='bf'),
        'bf_trim': Panel('bumper_front', 'trim', group='bf'),
        'bf_grille': Panel('bumper_front', 'trim', off=-0.04, frame=0.05, group='bfg'),
        'bf_intake': Panel('bumper_front', 'trim', off=-0.03, frame=0.04, group='bfi'),
        'br': Panel('bumper_rear', 'paint', group='br', hole_rim=0.04, **det),
        'br_chrome': Panel('bumper_rear', 'chrome', group='br'),
        'br_trim': Panel('bumper_rear', 'trim', group='br'),
        'bonnet': Panel('bonnet', 'paint', group='bonnet', **det),
    }
    return P


# ------------------------------------------------------------------ context
class Ctx:
    pass


def make_ctx(key, spec):
    S = STYLES[key]
    c = Ctx()
    c.key, c.spec, c.S = key, spec, S
    c.L, c.W, c.H = spec["length"], spec["width"], spec["height"]
    c.wb, c.tr, c.r, c.ww, c.gc = spec["wheelbase"], spec["track"], spec["wheel_radius"], spec["wheel_width"], spec["ground_clearance"]
    c.hw = c.W / 2
    # the flare lip must clear the tyre's outer face; S['over'] is the only excess over the cars.json width
    c.xmax = c.hw + S.get('over', 0.0)
    c.w = c.xmax - S['flare']                 # plan outline half-width (door skins)
    refL, refH = REF[key]
    c.ls = c.L / refL                         # longitudinal scale for cabin stations
    c.hs = spec["roof_y"] / refH              # vertical scale for style heights
    c.fo = S['fo'] * c.ls
    c.zF = c.wb / 2 + c.fo
    c.zR = c.zF - c.L
    c.zcF, c.zcR, c.yc = c.wb / 2, -c.wb / 2, c.r
    c.Ra = c.r + S['arch_gap']
    c.ap = S['arch_p']
    c.ysb = c.gc + 0.03
    c.yfloor = c.ysb + 0.03
    c.beltc = Curve([(z * c.ls, y * c.hs) for z, y in S['belt']])
    gh = S['gh']
    top = max(y for _, y in gh['roof'])
    c.roofc = Curve([(z * c.ls, y * spec["roof_y"] / top) for z, y in gh['roof']])
    c.origins = {}
    return c


def pad_to(xs, n):
    xs = list(xs)
    while len(xs) < n:
        k = max(range(len(xs) - 1), key=lambda i: abs(xs[i + 1] - xs[i]))
        xs.insert(k + 1, (xs[k] + xs[k + 1]) / 2)
    return xs


def nearest(vals, v):
    return min(range(len(vals)), key=lambda i: abs(vals[i] - v))


# ------------------------------------------------------------------ arches
def arch_bottom(c, z):
    for zc in (c.zcF, c.zcR):
        t = abs(z - zc) / c.Ra
        if t <= 1.0 + 1e-9:
            return c.yc + c.Ra * max(0.0, 1 - min(1.0, t) ** c.ap) ** (1 / c.ap)
    return None


def arch_dist(c, z, y):
    best = 9.0
    for zc in (c.zcF, c.zcR):
        dz, dy = abs(z - zc), y - c.yc
        if dy < 0:
            d = dz - c.Ra
        else:
            d = c.Ra * (((dz / c.Ra) ** c.ap + (dy / c.Ra) ** c.ap) ** (1 / c.ap) - 1)
        best = min(best, d)
    return best


def arch_stations(c, zc, n=12):
    out = [zc + c.Ra + 0.02]
    for k in range(n + 1):
        cs = math.cos(math.pi * k / n)
        out.append(zc + c.Ra * math.copysign(abs(cs) ** (2 / c.ap), cs))
    out.append(zc - c.Ra - 0.02)
    return out


# ------------------------------------------------------------------ plan path
def cowl_xz(c, th):
    """Windscreen-base corner, th = 0 where it leaves the straight cowl, 90 deg where it meets the flank."""
    ax, az, bow = c.S['gh']['cowl']
    xA = c.w - c.S['belt_in']
    x = (xA - ax) + ax * math.sin(th)
    z = c.zA + bow + az - bow * (x / xA) ** 2 - az * (1 - math.cos(th))
    return x, z


def build_path(c):
    S, w = c.S, c.w
    f, r = S['front'], S['rear']
    c.prot_f = max(0.0, -min(i for _, i in f['rows']))
    c.prot_r = max(0.0, -min(i for _, i in r['rows']))
    zf, zr = c.zF - c.prot_f, c.zR + c.prot_r
    xe_f, xe_r = w - f['ax'], w - r['ax']
    xa = subdiv(sorted(set([0.0] + [x for x in f['xbreaks'] if x < xe_f - 0.03] + [xe_f])), 0.11)
    xr = subdiv(sorted(set([0.0] + [x for x in r['xbreaks'] if x < xe_r - 0.03] + [xe_r])), 0.11)
    n = max(len(xa), len(xr))
    xa, xr = pad_to(xa, n), pad_to(xr, n)
    c.Na = n - 1
    pts = [(x, zf - f['bow'] * (x / w) ** 2) for x in xa]
    for dx, dz in corner_pts(NC, f['ax'], f['az'], f['p'])[1:]:
        x = xe_f + dx
        pts.append((x, zf - f['bow'] * (x / w) ** 2 - dz))
    z_cf = pts[-1][1]
    z_cr = zr + r['bow'] + r['az']
    gh = S['gh']
    c.zA = gh['zA'] * c.ls
    b0 = S['belt_in']
    c.thJ = math.asin(clamp(1 - (S['wing_in'] - b0) / gh['cowl'][0], 0.0, 1.0)) if S['wing_in'] > b0 + 1e-6 else math.radians(50)
    zn = {}
    ths = [c.thJ + (math.pi / 2 - c.thJ) * k / 3 for k in range(4)]
    for name, th in zip(('J', 'J1', 'J2', 'A'), ths):
        zn[name] = cowl_xz(c, th)[1]
    zn['d1'] = c.zcF - c.Ra - 0.02 - S['door_gap']
    zn['B1'], zn['B2'] = (z * c.ls for z in S['zB'])
    zn['Bm'] = (zn['B1'] + zn['B2']) / 2
    zn['C1'], zn['C2'] = (z * c.ls for z in S['zC'])
    zn['D'] = c.zR + S['zD'] * c.ls
    zn['flap0'] = c.zcR - c.Ra - 0.09
    zn['flap1'] = c.zcR - c.Ra - 0.27
    aF, aR = arch_stations(c, c.zcF), arch_stations(c, c.zcR)
    st = set(aF + aR)
    for name, z in zn.items():
        if not any(a[-1] - 0.03 < z < a[0] + 0.03 for a in (aF, aR)):
            st.add(z)
    st = sorted((z for z in st if z_cr + 0.03 < z < z_cf - 0.03), reverse=True)
    full = [z_cf] + st + [z_cr]
    out = [full[0]]
    for z in full[1:]:
        if out[-1] - z < 0.012:
            continue
        if out[-1] - z > 0.115:
            k = int(math.ceil((out[-1] - z) / 0.11))
            a = out[-1]
            for q in range(1, k):
                out.append(a + (z - a) * q / k)
        out.append(z)
    st = out[1:-1]
    c.i_side0 = len(pts) - 1          # last front-corner column (x = w, z = z_cf)
    for z in st:
        pts.append((w, z))
    c.i_rc0 = len(pts)                # first rear-corner column (x = w, z = z_cr)
    cp = corner_pts(NC, r['ax'], r['az'], r['p'])
    for dx, dz in reversed(cp):
        x = xe_r + dx
        pts.append((x, zr + r['bow'] * (x / w) ** 2 + dz))
    for x in reversed(xr[:-1]):
        pts.append((x, zr + r['bow'] * (x / w) ** 2))
    c.pts = pts
    c.nrm = plan_normals(pts)
    c.M = len(pts) - 1
    c.i_fs = c.Na + NC // 2
    c.i_rs = c.i_rc0 + NC // 2
    side_z = [p[1] for p in pts[c.i_side0:c.i_rc0 + 1]]
    c.ix = {name: c.i_side0 + nearest(side_z, z) for name, z in zn.items()}
    c.zn = {name: pts[i][1] for name, i in c.ix.items()}
    c.ix['afF'] = c.i_side0 + nearest(side_z, c.zcF + c.Ra)      # front arch, front vertical edge
    c.ix['afR'] = c.i_side0 + nearest(side_z, c.zcF - c.Ra)
    c.ix['arF'] = c.i_side0 + nearest(side_z, c.zcR + c.Ra)
    c.ix['arR'] = c.i_side0 + nearest(side_z, c.zcR - c.Ra)      # rear arch, rear vertical edge
    # belt-row inset where the wing top sweeps in to the windscreen corner
    c.bin_tab = {}
    for name, th in zip(('J', 'J1', 'J2', 'A'), ths):
        c.bin_tab[c.ix[name]] = w - cowl_xz(c, th)[0]


def side_inset(c, y, ysh):
    S = c.S
    yw = S['waist'] * c.hs
    if y <= yw:
        t = (yw - y) / max(1e-6, yw - c.ysb)
        ins = S['tuck'] * t * t
    else:
        t = clamp((y - yw) / max(1e-6, ysh - yw))
        ins = S['sh_in'] * t ** S['sh_e']
    cr = S.get('crease')
    if cr:                                   # lower character line: the skin steps in below it
        yc_, dep = cr[0] * c.hs, cr[1]
        ins += dep * smooth01((yc_ - y) / 0.05)
    return ins


def tub_column(c, i):
    S = c.S
    f, r = S['front'], S['rear']
    px, pz = c.pts[i]
    nx, nz = c.nrm[i]
    wf = smooth01(nz) if nz > 0 else 0.0
    wr = smooth01(-nz) if nz < 0 else 0.0
    ws = 1.0 - wf - wr
    ybelt = c.beltc(pz)
    ab = arch_bottom(c, pz) if ws > 0.999 else None
    yb_s = ab if ab is not None else c.ysb
    ysh_s = ybelt - S['sh_drop'] * c.hs
    ybF, yshF = f['yb'] * c.hs, ybelt - f['sh_drop'] * c.hs
    ybR, yshR = r['yb'] * c.hs, ybelt - r['sh_drop'] * c.hs
    col = []
    for j in range(NL):
        ys = yb_s + FR[j] * (ysh_s - yb_s)
        ins_s = side_inset(c, ys, ysh_s)
        d = max(0.0, arch_dist(c, pz, ys))
        if d < S['flare_w']:
            ins_s -= S['flare'] * (1 - d / S['flare_w']) ** 2
        y, ins = ws * ys, ws * ins_s
        if wf:
            y += wf * (ybF + f['rows'][j][0] * (yshF - ybF))
            ins += wf * f['rows'][j][1]
        if wr:
            y += wr * (ybR + r['rows'][j][0] * (yshR - ybR))
            ins += wr * r['rows'][j][1]
        col.append((ins, y))
    ins_sh, ysh = col[-1]
    if i in c.bin_tab:
        bs = c.bin_tab[i]
    elif pz > c.zn['J']:
        bs = S['wing_in']
    else:
        bs = S['belt_in']
    bin_ = ws * bs + wf * f['nose_in'] + wr * r['tail_in']
    a = S['roll']
    for k in range(1, NROLL + 1):
        t = k / NROLL
        ty = lerp(t, math.sin(t * math.pi / 2), a)
        tx = lerp(t, 1 - math.cos(t * math.pi / 2), a)
        col.append((ins_sh + (bin_ - ins_sh) * tx, ysh + (ybelt - ysh) * ty))
    return [V(px - nx * ins, y, pz - nz * ins) for ins, y in col]


def build_tub(c):
    P = [tub_column(c, i) for i in range(c.M + 1)]
    for col in (P[0], P[-1]):
        for p in col:
            p.x = 0.0
    return Surf(P, flip=False)


# ------------------------------------------------------------------ glasshouse
def build_glasshouse(c, tub):
    S, w = c.S, c.w
    gh = S['gh']
    b0 = S['belt_in']
    xA = w - b0
    axc, azc, bow_c = gh['cowl']
    iJ, iA = c.ix['J'], c.ix['A']
    g_f = c.i_fs
    c.g_f = g_f
    nca = g_f - NC1
    pJ = tub.P[iJ][TOP]
    ycc = c.beltc(c.zA) + gh['cowl_rise'] * c.hs
    xe = xA - axc
    own = [(xe * k / nca, 0.0) for k in range(nca + 1)]
    for k in range(1, NC1):
        th = c.thJ * k / NC1
        own.append((cowl_xz(c, th)[0], th))
    Bp = []
    for x, th in own:
        z = cowl_xz(c, th)[1] if th > 0 else c.zA + bow_c + azc - bow_c * (x / xA) ** 2
        y = pJ.y + (ycc - pJ.y) * (1 - (x / pJ.x) ** 2)
        Bp.append(V(x, y, z))
    c.cowl = [p.copy() for p in Bp]                # bonnet rear edge (centre -> just before J)
    for i in range(iJ, c.M + 1):
        Bp.append(tub.P[i][TOP].copy())
    ng = len(Bp)
    c.gi = lambda i: i - iJ + g_f
    # roof corner loop Q: the theoretical corner between the glass planes and the roof
    axh, azh, bow_h = gh['hdr']
    axr, azr, bow_r = gh['rhdr']
    zh = gh['zh'] * c.ls
    zrt = c.zR + gh['rear_run'] * c.ls
    xq0 = xA - gh['tum']
    z_At = zh - bow_h - azh
    z_Rt = zrt + bow_r + azr
    zs0 = c.zn['B1']
    zs1 = c.zn[gh['shear_r']]
    z_cr = c.pts[c.i_rc0][1]
    assert z_At > zs0 + 0.05, 'roof front corner must sit ahead of the B pillar'
    assert zs1 > z_Rt + 0.05, 'roof rear corner must sit behind the rear shear start'

    def xq(z):
        return xA - gh['tum'] - gh['tum_r'] * smooth01((zs0 - z) / (zs0 - z_Rt))
    xqr = xq(z_Rt)
    Q = []
    for g in range(nca + 1):
        x = Bp[g].x * (xq0 - axh) / xe
        Q.append((x, zh - bow_h * (x / xq0) ** 2))
    n_arc = NC1 + 3
    for k in range(1, n_arc + 1):
        th = (math.pi / 2) * k / n_arc
        x = (xq0 - axh) + axh * math.sin(th)
        Q.append((x, zh - bow_h * (x / xq0) ** 2 - azh * (1 - math.cos(th))))
    for i in range(iA + 1, c.i_rc0):
        z = c.pts[i][1]
        if z > zs0:
            z2 = zs0 + (z - zs0) * (z_At - zs0) / (c.zn['A'] - zs0)
        elif z < zs1:
            z2 = zs1 - (zs1 - z) * (zs1 - z_Rt) / (zs1 - z_cr)
        else:
            z2 = z
        Q.append((xq(z2), z2))
    xe_r = w - S['rear']['ax']
    for k in range(NC, -1, -1):
        th = (math.pi / 2) * k / NC
        x = (xqr - axr) + axr * math.sin(th)
        Q.append((x, zrt + bow_r * (x / xqr) ** 2 + azr * (1 - math.cos(th))))
    for i in range(c.i_rc0 + NC + 1, c.M + 1):
        x = c.pts[i][0] * (xqr - axr) / xe_r
        Q.append((x, zrt + bow_r * (x / xqr) ** 2))
    assert len(Q) == ng, (len(Q), ng)
    crown = gh['crown']

    def roof_y(x, z):
        return c.roofc(z) - crown * (x / xq0) ** 2
    c.roof_y = roof_y
    qn = plan_normals(Q)
    rc = gh['rc']
    P = []
    gap = 0.006
    for g in range(ng):
        b = Bp[g].copy()
        if g < g_f:
            b.z -= gap * (1 - (g / g_f) ** 4)
        q = V(Q[g][0], roof_y(*Q[g]), Q[g][1])
        tx, tz = Q[g][0] - qn[g][0] * rc, Q[g][1] - qn[g][1] * rc
        if g == 0 or g == ng - 1:
            tx = 0.0
        tx = max(0.0, tx)
        t = V(tx, roof_y(tx, tz), tz)
        col = [b + (q - b) * f for f in GT]
        cpt = col[-1]
        for s_ in (1 / 3, 2 / 3):
            col.append(cpt * (1 - s_) ** 2 + q * (2 * s_ * (1 - s_)) + t * s_ ** 2)
        col.append(t)
        P.append(col)
    for col in (P[0], P[-1]):
        for p in col:
            p.x = 0.0
    s = Surf(P, flip=False)
    s.border['j0'] = (0.02, 0, g_f)
    return s


def build_roof(c, G):
    g_f = c.g_f
    g_rs = c.gi(c.i_rs)
    top = G.nj - 1
    T = [G.P[g][top] for g in range(G.ni)]
    Bm = [T[g].copy() for g in range(0, g_f + 1)]
    R = [T[g].copy() for g in range(g_f, g_rs + 1)]
    Tt = [T[g].copy() for g in range(G.ni - 1, g_rs - 1, -1)]
    assert len(Bm) == len(Tt), (len(Bm), len(Tt))
    L = []
    z0, z1 = R[0].z, R[-1].z
    for p in R:
        s = (p.z - z0) / (z1 - z0)
        z = lerp(Bm[0].z, Tt[0].z, s)
        L.append(V(0.0, c.roof_y(0.0, z), z))
    L[0], L[-1] = Bm[0].copy(), Tt[0].copy()
    return Surf(coons(L, R, Bm, Tt, crown=True), hint=Vector((0, 1, 0)))


def build_bonnet(c, tub):
    S = c.S
    iJ, ifs = c.ix['J'], c.i_fs
    g = 0.0 if S['clamshell'] else 0.006

    def edge(i):
        p = tub.P[i][TOP].copy()
        nx, nz = c.nrm[i]
        p.x -= nx * g
        p.z -= nz * g
        if i == 0:
            p.x = 0.0
        return p
    Bm = [edge(i) for i in range(0, ifs + 1)]
    R = [edge(i) for i in range(ifs, iJ + 1)]
    Tt = [p.copy() for p in c.cowl] + [R[-1].copy()]
    assert len(Bm) == len(Tt), (len(Bm), len(Tt))
    L = []
    z0, z1 = R[0].z, R[-1].z
    for p in R:
        s = (p.z - z0) / (z1 - z0)
        y = lerp(Bm[0].y, Tt[0].y, s) + S['bonnet_arc'] * c.hs * 4 * s * (1 - s)
        L.append(V(0.0, y, lerp(Bm[0].z, Tt[0].z, s)))
    L[0], L[-1] = Bm[0].copy(), Tt[0].copy()
    P = coons(L, R, Bm, Tt, crown=True)
    dome = S['bonnet_dome']
    if dome:
        nu, nv = len(P) - 1, len(P[0]) - 1
        for iu in range(nu + 1):
            for iv in range(nv + 1):
                u, v = iu / nu, iv / nv
                P[iu][iv].y += dome * smooth01((0.50 - u) / 0.16) * smooth01(v / 0.12) * smooth01((1 - v) / 0.08)
    s = Surf(P, hint=Vector((0, 1, 0)))
    s.fill('bonnet')
    hi = 10 ** 6
    s.border['j1'] = (0.02, 0, hi)
    if not S['clamshell']:
        s.border['i1'] = (0.02, 0, hi)
        s.border['j0'] = (0.02, 0, hi)
    return s


# ------------------------------------------------------------------ tagging
def path_index_at_x(c, x, front=True):
    """Column on the nose (or tail) whose plan x is nearest to x."""
    rng = range(0, c.i_side0 + 1) if front else range(c.i_rc0, c.M + 1)
    return min(rng, key=lambda i: abs(c.pts[i][0] - x))


def tag_tub(c, tub):
    S = c.S
    ix = c.ix
    M = c.M
    i_s = ix['afF']                # fascia / wing shut line: front edge of the front arch
    i_b = ix['arR']                # rear bumper starts at the rear edge of the rear arch
    c.i_s, c.i_b = i_s, i_b
    nrow = TOP                     # number of cell rows
    tub.fill('shell')
    tub.set('sill', i_s, i_b, 0, 1)
    tub.set('door_f', ix['d1'], ix['Bm'], 1, nrow)
    tub.set('door_r', ix['Bm'], ix['C1'], 1, nrow)
    tub.set('flap', ix['flap0'], ix['flap1'], 6, 8)          # left side only, see the tagfn in build_car
    # front fascia
    tub.set('bf', 0, i_s, 0, nrow)
    if S['clamshell']:
        tub.set('bonnet', 0, ix['J'], NL - 1, nrow)
    gr = S['grille']
    i_g = path_index_at_x(c, gr['x'])
    tub.set('bf_grille', 0, i_g, gr['rows'][0], gr['rows'][1])
    c.grille_cells = (0, i_g, gr['rows'][0], gr['rows'][1])
    it = S['intake']
    i_i = path_index_at_x(c, it['x'])
    tub.set('bf_intake', 0, i_i, it['rows'][0], it['rows'][1], only='bf')
    c.intake_cells = (0, i_i, it['rows'][0], it['rows'][1])
    lp = S['lamp']
    i_l0, i_l1 = path_index_at_x(c, lp['x0']), path_index_at_x(c, lp['x1'])
    tub.set(None, i_l0, i_l1, lp['rows'][0], lp['rows'][1])
    c.lamp_cells = (i_l0, i_l1, lp['rows'][0], lp['rows'][1])
    if S['bumper_chrome']:
        tub.set('bf_chrome', 0, i_s, 2, 4, only='bf')
    # rear bumper: up to row 5 on the tail, wrapping forward to the rear arch
    tub.set('br', i_b, M, 0, 5)
    if S['bumper_chrome']:
        tub.set('br_chrome', i_b, M, 2, 4)
    else:
        tub.set('br_trim', c.i_rc0 + 2, M, 0, 1)
    i_tg = c.i_rc0 + NC - 1
    tub.set('tailgate', i_tg, M, 5, nrow)
    c.i_tg = i_tg
    kind = S['tail']
    if kind == 'pillar':        # tall lamps on the corners
        tub.set('tail', c.i_rc0 + 2, i_tg, 5, nrow)
    elif kind == 'wrap':        # wide lamps wrapping the corner
        tub.set('tail', c.i_rc0 + 1, i_tg + 3, 7, 10)
    elif kind == 'bar':         # full-width light bar
        tub.set('tailbar', c.i_rc0 + 1, M, 8, 10)
    elif kind == 'blade':       # slim vertical blades
        tub.set('tail', i_tg - 2, i_tg, 5, nrow)
    if S['cladding']:
        for i in range(i_s, i_b):
            for j in range(0, nrow):
                if tub.tag[i][j] in ('shell', 'door_f', 'door_r', 'sill'):
                    pc = (tub.P[i][j] + tub.P[i + 1][j + 1]) / 2
                    if arch_dist(c, pc.z, pc.y) < S['cladding'] or j == 0:
                        tub.tag[i][j] = 'clad'
        tub.set('bf_trim', 0, i_s, 0, 2, only='bf')
        tub.set('br_trim', i_b, M, 0, 2)
    tub.border['j0'] = (0.03, 0, 10 ** 6)
    if not S['clamshell']:
        tub.border['j1'] = (0.02, 0, ix['J'])
    tub.sharp_rows = set(S['sharp_rows'])


def tag_glasshouse(c, G):
    S = c.S
    gi, ix, g_f = c.gi, c.ix, c.g_f
    ng = G.ni - 1
    G.fill('shell')
    # rows: 0 belt strip, 1..3 glass, 4..6 cant rail
    gW = g_f - 1
    gA = gi(ix['A'])
    G.set('cowl', 0, g_f, 0, 1)
    G.set('glass_w', 0, gW, 1, 4)
    G.set('pillar', gW, gA + 1, 0, 4)
    gB1, gB2 = gi(ix['B1']), gi(ix['B2'])
    gC1, gC2 = gi(ix['C1']), gi(ix['C2'])
    gD = gi(ix['D'])
    gDr = gi(c.i_rc0 + NC - 1)
    G.set('belt', gA + 1, gD, 0, 1)
    G.set('glass_s', gA + 1, gB1, 1, 4)
    G.set('pillar', gB1, gB2, 0, 4)
    G.set('glass_s', gB2, gC1, 1, 4)
    G.set('pillar', gC1, gC2, 0, 4)
    G.set('glass_q', gC2, gD, 1, 4)
    G.set('pillar', gD, gDr, 0, 4)
    G.set('tailgate', gDr, ng, 0, 6)
    G.set('glass_r', gDr + 1, ng, 1, 4)
    if S['tail'] == 'pillar':
        G.set('tail', gi(c.i_rc0 + 2), gDr, 0, 3)
    c.gh_cols = dict(W=gW, A=gA, B1=gB1, B2=gB2, C1=gC1, C2=gC2, D=gD, Dr=gDr)


def tag_roof(c, R):
    S = c.S
    R.fill('shell')
    if S['roofpanel']:
        v0, v1 = S['roofpanel']
        nu, nv = R.ni - 1, R.nj - 1
        R.set('roofglass', 0, int(nu * 0.72), int(nv * v0), int(nv * v1))


# ------------------------------------------------------------------ build
def build_car(key, spec, root):
    S = STYLES[key]
    car_materials(spec, S)
    c = make_ctx(key, spec)
    build_path(c)
    tub = build_tub(c)
    tag_tub(c, tub)
    G = build_glasshouse(c, tub)
    tag_glasshouse(c, G)
    R = build_roof(c, G)
    tag_roof(c, R)
    Bn = build_bonnet(c, tub)
    c.tub, c.G, c.R, c.Bn = tub, G, R, Bn

    sh = Shell(panels(S))
    c.sh = sh
    flap = lambda t, sx: ('shell' if (t == 'flap' and sx < 0) else t)
    sh.emit(tub, tagfn=flap)
    sh.emit(G)
    sh.emit(R)
    sh.emit(Bn)
    # inner skins: cabin lining behind every non-glass cell, dark backs for the detachable panels
    K.emit_liner(sh, G, lambda t: t is not None and not t.startswith('glass'), 0.045, 'interior', 'cabin')
    K.emit_liner(sh, R, lambda t: True, 0.045, 'interior', 'headliner', step=(2, 2))
    body_tags = ('shell', 'door_f', 'door_r', 'flap', 'sill', 'clad', 'tail', 'tailgate', 'tailbar')
    K.emit_liner(sh, tub, lambda t: t in body_tags, 0.05, 'interior', 'cabin', step=(1, 2))
    K.emit_liner(sh, tub, lambda t: t is not None and t.startswith('bf'), 0.006, 'bumper_front', 'trim')
    K.emit_liner(sh, tub, lambda t: t is not None and t.startswith('br'), 0.006, 'bumper_rear', 'trim')
    K.emit_liner(sh, Bn, lambda t: True, 0.02, 'bonnet', 'trim', step=(2, 2))
    if S['clamshell']:
        K.emit_liner(sh, tub, lambda t: t == 'bonnet', 0.006, 'bonnet', 'trim')

    carparts.structure(c, sh)
    carparts.lamps(c, sh)
    carparts.grille(c, sh)
    carparts.exterior_details(c, sh)
    carparts.mirrors(c, sh)
    carparts.underside(c, sh)
    carparts.interior(c, sh)
    carparts.wheels(c, sh)

    f = S['front']
    origins = {
        'bumper_front': (0, (f['yb'] + 0.25) * c.hs, c.zF - 0.30),
        'bumper_rear': (0, (S['rear']['yb'] + 0.2) * c.hs, c.zR + 0.30),
        'bonnet': (0, c.cowl[0].y, c.cowl[0].z),
    }
    origins.update(c.origins)
    angle = {'body': 38.0, 'bonnet': 38.0, 'bumper_front': 40.0, 'bumper_rear': 40.0, 'glass': 60.0}
    for name in sorted(sh.nodes):
        mb = sh.nodes[name]
        if not len(mb.bm.faces):
            continue
        mb.to_object(name, origin=origins.get(name, (0, 0, 0)), parent=root, smooth=angle.get(name, 42.0))
    za = (c.R.P[0][0].z + c.R.P[0][-1].z) / 2
    empty("roof_anchor", (0, c.roof_y(0.0, za), za), parent=root)
    return c


# ------------------------------------------------------------------ ambient occlusion into vertex colours
def bake_ao(skip=("glass", "headlight_l", "headlight_r", "taillights", "beacon_l", "beacon_r"), samples=14, maxd=1.1):
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
                wv = t * d.x + b * d.y + n * d.z
                loc, nor, idx, dist = bvh.ray_cast(p, wv, maxd)
                if loc is not None:
                    hit += 1.0 - dist / maxd * 0.5
            ao = 1.0 - hit / samples
            val = 0.32 + 0.68 * ao ** 0.8
            col.data[v.index].color = (val, val, val, 1.0)
