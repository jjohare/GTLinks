#!/usr/bin/env python3
"""Car validation: plain Python on the exported GLBs (JSON chunk and binary buffers, no Blender).

  python3 assets/src/cars_validate.py                 validate the four player cars and the patrol car and
                                                      merge the result into docs/evidence/assets/validation.json
  python3 assets/src/cars_validate.py --glb DIR --cars FILE --out FILE [--tag follow_file]
                                                      validate another build (used for the "models follow
                                                      cars.json" check: a build from a modified cars.json)

Checks per car: required nodes; single root `car` with every other node directly under it; standard PBR factor
materials (no textures, no compression or material extensions); triangle budget; bounding box within 3 % of
cars.json; wheel centres within 1 cm of the contract formula with identity rotation and the axle along X;
wheel radius and width; ground contact; forward = +Z and left = +X; headlight origins at the lens centre and
lenses facing +Z; mesh health from the vertex data: no degenerate triangles, and for the painted shell no
edge shared by more than two triangles, consistent winding across every shared edge, and exported vertex
normals that agree with the face winding.
"""
import json, struct, sys, os, math, argparse

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
PLAYER_NODES = ['car', 'body', 'glass', 'wheel_fl', 'wheel_fr', 'wheel_rl', 'wheel_rr', 'headlight_l', 'headlight_r',
                'bumper_front', 'bumper_rear', 'bonnet', 'mirror_l', 'mirror_r', 'roof_anchor', 'underside', 'interior']
PATROL_NODES = ['car', 'body', 'glass', 'wheel_fl', 'wheel_fr', 'wheel_rl', 'wheel_rr', 'headlight_l', 'headlight_r',
                'roof_anchor', 'underside', 'interior', 'lightbar', 'beacon_l', 'beacon_r']
SHELL_NODES = ['body', 'bonnet', 'bumper_front', 'bumper_rear', 'glass']
ROOF_GEAR = ('lightbar', 'beacon_l', 'beacon_r', 'aerial')     # patrol only: sits above the roof line
CTYPE = {5120: 'b', 5121: 'B', 5122: 'h', 5123: 'H', 5125: 'I', 5126: 'f'}
SLIVER = 2e-4
NCOMP = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4}


def load_glb(path):
    with open(path, 'rb') as f:
        data = f.read()
    magic, ver, length = struct.unpack('<4sII', data[:12])
    assert magic == b'glTF' and ver == 2 and length == len(data), 'bad GLB header'
    off, js, bin_ = 12, None, b''
    while off < len(data):
        clen, ctype = struct.unpack('<II', data[off:off + 8])
        chunk = data[off + 8: off + 8 + clen]
        if ctype == 0x4E4F534A:
            js = json.loads(chunk)
        elif ctype == 0x004E4942:
            bin_ = chunk
        off += 8 + clen
    return js, bin_, len(data)


def accessor(js, bin_, idx):
    a = js['accessors'][idx]
    bv = js['bufferViews'][a['bufferView']]
    n = NCOMP[a['type']]
    fmt = CTYPE[a['componentType']]
    size = struct.calcsize(fmt) * n
    stride = bv.get('byteStride', size)
    base = bv.get('byteOffset', 0) + a.get('byteOffset', 0)
    out = []
    for i in range(a['count']):
        v = struct.unpack_from('<%d%s' % (n, fmt), bin_, base + i * stride)
        out.append(v[0] if n == 1 else v)
    return out


def quat_rot(q, v):
    x, y, z, w = q
    ux, uy, uz = v
    cx, cy, cz = y * uz - z * uy, z * ux - x * uz, x * uy - y * ux
    dx, dy, dz = y * cz - z * cy, z * cx - x * cz, x * cy - y * cx
    return (ux + 2 * (w * cx + dx), uy + 2 * (w * cy + dy), uz + 2 * (w * cz + dz))


def node_meshes(js, bin_):
    """Per node: world-space triangles as (positions, normals) index triples.  Hierarchy here is root -> node."""
    nodes = js['nodes']
    parent = {}
    for i, n in enumerate(nodes):
        for ch in n.get('children', []):
            parent[ch] = i

    def world(i, p):
        while i is not None:
            n = nodes[i]
            s = n.get('scale', (1, 1, 1))
            p = (p[0] * s[0], p[1] * s[1], p[2] * s[2])
            p = quat_rot(n.get('rotation', (0, 0, 0, 1)), p)
            t = n.get('translation', (0, 0, 0))
            p = (p[0] + t[0], p[1] + t[1], p[2] + t[2])
            i = parent.get(i)
        return p
    out = {}
    for i, n in enumerate(nodes):
        if 'mesh' not in n:
            continue
        P, N, T = [], [], []
        for prim in js['meshes'][n['mesh']]['primitives']:
            base = len(P)
            pos = accessor(js, bin_, prim['attributes']['POSITION'])
            nor = accessor(js, bin_, prim['attributes']['NORMAL']) if 'NORMAL' in prim['attributes'] else [(0, 0, 0)] * len(pos)
            idx = accessor(js, bin_, prim['indices']) if 'indices' in prim else list(range(len(pos)))
            P += [world(i, p) for p in pos]
            N += nor
            T += [(base + idx[k], base + idx[k + 1], base + idx[k + 2]) for k in range(0, len(idx) - 2, 3)]
        out[n['name']] = (P, N, T)
    return out, parent


def sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def mesh_health(P, N, T):
    """Degenerate triangles, non-manifold edges, winding consistency and normal agreement for one node."""
    key = {}
    ids = []
    for p in P:
        k = (round(p[0], 4), round(p[1], 4), round(p[2], 4))
        ids.append(key.setdefault(k, len(key)))
    degenerate = 0
    edges = {}
    disagree = slivers = 0
    area_total = 0.0
    for (a, b, c) in T:
        fn = cross(sub(P[b], P[a]), sub(P[c], P[a]))
        ar = math.sqrt(dot(fn, fn)) / 2
        wa, wb, wc = ids[a], ids[b], ids[c]
        if ar < 1e-9 or len({wa, wb, wc}) < 3:
            degenerate += 1
            continue
        area_total += ar
        vn = (N[a][0] + N[b][0] + N[c][0], N[a][1] + N[b][1] + N[c][1], N[a][2] + N[b][2] + N[c][2])
        if dot(fn, vn) <= 0:
            if ar < SLIVER:
                slivers += 1         # a sliver under 2 cm2 where panels meet: counted, too small to shade wrongly
            else:
                disagree += 1
        for u, v in ((wa, wb), (wb, wc), (wc, wa)):
            e = edges.setdefault((min(u, v), max(u, v)), [0, 0])
            e[0 if u < v else 1] += 1
    nonmanifold = sum(1 for f, r in edges.values() if f + r > 2)
    flipped = sum(1 for f, r in edges.values() if f + r == 2 and (f == 2 or r == 2))
    boundary = sum(1 for f, r in edges.values() if f + r == 1)
    return dict(triangles=len(T), degenerate=degenerate, nonmanifold_edges=nonmanifold, inconsistent_winding_edges=flipped,
                normal_disagreements=disagree, sliver_disagreements_under_2cm2=slivers, boundary_edges=boundary, area_m2=round(area_total, 3))


def bbox(meshes, skip=()):
    lo, hi = [1e9] * 3, [-1e9] * 3
    for name, (P, N, T) in meshes.items():
        if name in skip:
            continue
        for p in P:
            for k in range(3):
                lo[k] = min(lo[k], p[k]); hi[k] = max(hi[k], p[k])
    return lo, hi


def validate_car(key, spec, path, patrol=None):
    patrol = (key == 'patrol') if patrol is None else patrol
    js, bin_, size = load_glb(path)
    res = dict(file=os.path.relpath(path, ROOT) if path.startswith(ROOT) else path, bytes=size, checks={}, ok=True)
    C = res['checks']
    nodes = js['nodes']
    names = [n.get('name', '') for n in nodes]
    meshes, parent = node_meshes(js, bin_)
    need = PATROL_NODES if patrol else PLAYER_NODES
    missing = [n for n in need if n not in names]
    C['required_nodes'] = dict(ok=not missing, missing=missing, present=sorted(names))
    roots = [names[i] for i in js['scenes'][js.get('scene', 0)]['nodes']]
    car_i = names.index('car') if 'car' in names else -1
    deep = [names[i] for i in range(len(nodes)) if i != car_i and parent.get(i) != car_i]
    dup = sorted({n for n in names if names.count(n) > 1})
    C['flat_hierarchy_under_car'] = dict(ok=roots == ['car'] and not deep and not dup, roots=roots, not_direct_children=deep, duplicate_names=dup)
    # materials
    mats = js.get('materials', [])
    bad = []
    for m in mats:
        pbr = m.get('pbrMetallicRoughness', {})
        if any(k.endswith('Texture') for k in list(m) + list(pbr)) or m.get('extensions'):
            bad.append(m.get('name'))
    ext = sorted(set(js.get('extensionsUsed', [])) | set(js.get('extensionsRequired', [])))
    C['materials_standard_pbr_factors'] = dict(ok=not bad and not ext and not js.get('images') and not js.get('textures')
                                               and not js.get('animations'), offending=bad, extensions=ext,
                                               names=[m.get('name') for m in mats])
    nm = {}
    for i, n in enumerate(nodes):
        if 'mesh' in n:
            nm[n['name']] = sorted({mats[p['material']]['name'] for p in js['meshes'][n['mesh']]['primitives'] if 'material' in p})
    byname = {m.get('name'): m for m in mats}
    hl = byname.get('headlight', {})
    gl = byname.get('glass', {})
    ok = (('paint' in nm.get('body', [])) and nm.get('glass') == ['glass'] and nm.get('headlight_l') == ['headlight']
          and nm.get('headlight_r') == ['headlight'] and gl.get('alphaMode') == 'BLEND' and any(v > 0 for v in hl.get('emissiveFactor', [0])))
    if not patrol:
        ok = ok and nm.get('body') == ['paint']
    else:
        ok = ok and all(any(v > 0 for v in byname.get(nm.get(b, ['?'])[0], {}).get('emissiveFactor', [0])) for b in ('beacon_l', 'beacon_r'))
    C['node_materials'] = dict(ok=ok, body=nm.get('body'), glass=nm.get('glass'), headlight_l=nm.get('headlight_l'),
                               glass_alphaMode=gl.get('alphaMode'), headlight_emissive=hl.get('emissiveFactor'),
                               beacons=[nm.get('beacon_l'), nm.get('beacon_r')] if patrol else None)
    # triangles
    tris = sum(len(T) for (P, N, T) in meshes.values())
    lo_b, hi_b = (12000, 18000) if patrol else (25000, 40000)
    res['tris'] = tris
    res['tris_per_node'] = {k: len(v[2]) for k, v in sorted(meshes.items())}
    C['triangle_budget'] = dict(ok=lo_b <= tris <= hi_b, tris=tris, budget=[lo_b, hi_b])
    # bounding box
    lo, hi = bbox(meshes)
    lo2, hi2 = bbox(meshes, skip=ROOF_GEAR) if patrol else (lo, hi)
    meas = dict(width=hi[0] - lo[0], height=hi2[1] - lo2[1], length=hi[2] - lo[2])
    exp = dict(width=spec['width'], height=spec['height'], length=spec['length'])
    rel = {k: abs(meas[k] - exp[k]) / exp[k] for k in meas}
    lo3, hi3 = bbox(meshes, skip=('mirror_l', 'mirror_r'))
    C['bbox_within_3pct'] = dict(ok=all(v <= 0.03 for v in rel.values()), measured={k: round(v, 4) for k, v in meas.items()},
                                 expected=exp, rel_error_pct={k: round(100 * v, 2) for k, v in rel.items()},
                                 min=[round(v, 4) for v in lo], max=[round(v, 4) for v in hi],
                                 width_without_mirrors=round(hi3[0] - lo3[0], 4),
                                 note=('height excludes the roof lightbar, beacons and aerial; overall top y = %.3f' % hi[1]) if patrol else
                                 'whole model including mirrors and roof rails')
    C['ground_at_y0'] = dict(ok=abs(lo[1]) < 0.01, min_y=round(lo[1], 4))
    C['symmetric_about_x0'] = dict(ok=abs(lo[0] + hi[0]) < 0.02 or patrol, min_x=round(lo[0], 4), max_x=round(hi[0], 4))
    # wheels
    T_ = {names[i]: nodes[i].get('translation', [0, 0, 0]) for i in range(len(nodes))}
    wres, wok = {}, True
    for n, (sx, sz) in {'wheel_fl': (1, 1), 'wheel_fr': (-1, 1), 'wheel_rl': (1, -1), 'wheel_rr': (-1, -1)}.items():
        e = [sx * spec['track'] / 2, spec['wheel_radius'], sz * spec['wheelbase'] / 2]
        got = T_.get(n)
        node = nodes[names.index(n)] if n in names else {}
        ident = node.get('rotation', [0, 0, 0, 1]) == [0, 0, 0, 1] and node.get('scale', [1, 1, 1]) == [1, 1, 1]
        err = max(abs(got[k] - e[k]) for k in range(3)) if got else None
        P = meshes.get(n, ([], [], []))[0]
        rad = max((math.hypot(p[1] - e[1], p[2] - e[2]) for p in P), default=0)
        wid = (max(p[0] for p in P) - min(p[0] for p in P)) if P else 0
        ok = (got is not None and err <= 0.01 and ident and abs(rad - spec['wheel_radius']) < 0.006
              and abs(wid - spec['wheel_width']) < 0.012)
        wok &= ok
        wres[n] = dict(expected=[round(v, 4) for v in e], got=[round(v, 5) for v in got] if got else None,
                       max_abs_err_m=None if err is None else round(err, 6), identity_rotation=ident,
                       tyre_radius=round(rad, 4), tyre_width_along_x=round(wid, 4), ok=ok)
    C['wheels_at_formula_1cm_axle_x'] = dict(ok=wok, expected_radius=spec['wheel_radius'], expected_width=spec['wheel_width'], wheels=wres)
    # clearance between tyre and arch: the tyre must sit inside the body's width
    tyre_out = spec['track'] / 2 + spec['wheel_width'] / 2
    C['tyres_inside_body_width'] = dict(ok=tyre_out <= max(hi3[0], -lo3[0]) + 1e-6, tyre_outer_x=round(tyre_out, 4), body_half_width=round(max(hi3[0], -lo3[0]), 4))
    # orientation
    fw = []
    try:
        fw.append(T_['headlight_l'][2] > 0 and T_['headlight_r'][2] > 0)
        fw.append(T_['headlight_l'][0] > 0 > T_['headlight_r'][0])
        fw.append(T_['wheel_fl'][0] > 0 and T_['wheel_fl'][2] > 0)
        fw.append(all(abs(v) < 1e-6 for v in T_['car']))
        fw.append(abs(T_['roof_anchor'][0]) < 0.01 and abs(T_['roof_anchor'][1] - spec['roof_y']) < 0.02)
        if not patrol:
            fw.append(T_['bumper_front'][2] > 0 > T_['bumper_rear'][2])
            fw.append(T_['mirror_l'][0] > 0 > T_['mirror_r'][0])
            fw.append(T_['bonnet'][2] > 0)
            bz = [p[2] for p in meshes['bonnet'][0]]
            fw.append(max(bz) - T_['bonnet'][2] > 0.5 and T_['bonnet'][2] - min(bz) < 0.3 * (max(bz) - min(bz)))   # hinge at the rear edge
        else:
            fw.append(T_['beacon_l'][0] > 0 > T_['beacon_r'][0])
    except KeyError:
        fw.append(False)
    C['forward_plus_z_left_plus_x'] = dict(ok=all(fw), flags=fw, headlight_l=T_.get('headlight_l'), roof_anchor=T_.get('roof_anchor'),
                                           bonnet_hinge=T_.get('bonnet'), bumper_front=T_.get('bumper_front'), bumper_rear=T_.get('bumper_rear'))
    # headlights: origin at lens centre, lens faces +Z, room for a pupil
    lamp, lok = {}, True
    for n in ('headlight_l', 'headlight_r'):
        P, N, T = meshes.get(n, ([], [], []))
        if not P:
            lok = False
            continue
        ctr = [(min(p[k] for p in P) + max(p[k] for p in P)) / 2 for k in range(3)]
        off = max(abs(ctr[k] - T_[n][k]) for k in range(2))
        w, h = max(p[0] for p in P) - min(p[0] for p in P), max(p[1] for p in P) - min(p[1] for p in P)
        nz = sum(v[2] for v in N) / len(N)
        ok = off < 0.01 and nz > 0.3 and min(w, h) >= 0.15
        lok &= ok
        lamp[n] = dict(centre_offset_xy_m=round(off, 4), lens_width=round(w, 3), lens_height=round(h, 3), mean_normal_z=round(nz, 3),
                       pupil_radius_front_end=round(0.32 * min(w, h), 3), ok=ok)
    C['headlights_as_eyes'] = dict(ok=lok, lamps=lamp)
    # mesh health
    health, hok = {}, True
    for n, (P, N, T) in sorted(meshes.items()):
        h = mesh_health(P, N, T)
        shell = n in SHELL_NODES
        ok = h['degenerate'] == 0 and h['normal_disagreements'] == 0
        if shell:
            ok = ok and h['nonmanifold_edges'] == 0 and h['inconsistent_winding_edges'] == 0
        h['ok'] = ok
        hok &= ok
        health[n] = h
    C['mesh_health'] = dict(ok=hok, rule='all nodes: no degenerate triangles, vertex normals agree with winding; shell nodes '
                            '(%s): no edge shared by more than two triangles, consistent winding across shared edges' % ', '.join(SHELL_NODES),
                            nodes=health)
    # outward-facing shell: share of body area whose normal points away from the car's long axis
    P, N, T = meshes.get('body', ([], [], []))
    out_a = tot_a = 0.0
    for (a, b, c) in T:
        fn = cross(sub(P[b], P[a]), sub(P[c], P[a]))
        ar = math.sqrt(dot(fn, fn)) / 2
        cx, cy = (P[a][0] + P[b][0] + P[c][0]) / 3, (P[a][1] + P[b][1] + P[c][1]) / 3 - 0.9
        tot_a += ar
        if fn[0] * cx + fn[1] * cy > 0 or abs(fn[2]) > 0.8 * 2 * ar:
            out_a += ar
    share = out_a / tot_a if tot_a else 0
    C['body_normals_outward'] = dict(ok=share > 0.85, outward_area_share=round(share, 3),
                                     note='the remainder is arch lips, rims and the panel behind the rear bumper, which face inward or along Z by design')
    res['ok'] = all(c['ok'] for c in C.values())
    return res


def specs_from(path):
    data = json.load(open(path))
    s = {c['key']: c for c in data['cars']}
    if 'patrol' in data:
        s['patrol'] = data['patrol']
    return s


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--glb', default=os.path.join(ROOT, 'web/public/assets/cars'))
    ap.add_argument('--cars', default=os.path.join(ROOT, 'assets/cars.json'))
    ap.add_argument('--out', default=os.path.join(ROOT, 'docs/evidence/assets/validation.json'))
    ap.add_argument('--tag', default='', help='store the result under this key instead of cars/patrol (e.g. follow_file)')
    ap.add_argument('--note', default='')
    a = ap.parse_args()
    specs = specs_from(a.cars)
    results = {}
    for k, spec in specs.items():
        p = os.path.join(a.glb, k + '.glb')
        results[k] = validate_car(k, spec, p) if os.path.exists(p) else dict(ok=False, error='missing file')
    out = json.load(open(a.out)) if os.path.exists(a.out) else dict(contract='docs/CONTRACT.md s3', cars={}, props={})
    if a.tag:
        out[a.tag] = dict(note=a.note, specs={k: {f: specs[k][f] for f in ('length', 'width', 'height', 'wheelbase', 'track', 'wheel_radius',
                                                                            'wheel_width', 'ground_clearance', 'roof_y')} for k in specs},
                          cars=results, all_ok=all(v['ok'] for v in results.values()))
    else:
        out['cars'] = {k: v for k, v in results.items() if k != 'patrol'}
        if 'patrol' in results:
            out['patrol'] = results['patrol']
        out['all_ok'] = all(v.get('ok') for grp in ('cars', 'props') for v in out.get(grp, {}).values()) and out.get('patrol', {}).get('ok', True)
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    json.dump(out, open(a.out, 'w'), indent=1)
    for k, v in results.items():
        bad = [c for c, d in v.get('checks', {}).items() if not d['ok']]
        print('%-18s ok=%s tris=%s bytes=%s %s' % (k, v['ok'], v.get('tris'), v.get('bytes'), ('FAIL: ' + ','.join(bad)) if bad else ''))
    return 0 if all(v['ok'] for v in results.values()) else 1


if __name__ == '__main__':
    sys.exit(main())
