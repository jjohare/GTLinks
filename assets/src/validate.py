#!/usr/bin/env python3
"""Validate the exported GLBs against CONTRACT.md s3 using only the GLB JSON chunk (no Blender).

  python3 assets/src/validate.py [--out docs/evidence/assets/validation.json]

Checks per car: required node names, triangle budget (<12000), bounding box vs cars.json (3 %),
wheel node positions vs the contract formula (1 cm), +Z forward (front lamps/bumper at +Z, FL at +X,+Z),
glTF validity basics (no Draco/meshopt/KTX/WebP, no images), materials named as required, file size.
Props: required nodes/materials, triangle budgets, bounding boxes, origin conventions.
"""
import json, struct, sys, os, math, argparse

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))


def load_glb(path):
    with open(path, 'rb') as f:
        data = f.read()
    magic, ver, length = struct.unpack('<4sII', data[:12])
    assert magic == b'glTF' and ver == 2 and length == len(data), 'bad GLB header'
    off = 12
    js, bin_ = None, None
    while off < len(data):
        clen, ctype = struct.unpack('<II', data[off:off + 8])
        chunk = data[off + 8: off + 8 + clen]
        if ctype == 0x4E4F534A:
            js = json.loads(chunk)
        elif ctype == 0x004E4942:
            bin_ = chunk
        off += 8 + clen
    return js, bin_, len(data)


def mat4(t=(0, 0, 0), q=(0, 0, 0, 1), s=(1, 1, 1)):
    x, y, z, w = q
    r = [[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
         [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
         [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]]
    return [[r[i][0] * s[0], r[i][1] * s[1], r[i][2] * s[2], t[i]] for i in range(3)] + [[0, 0, 0, 1]]


def mul(a, b):
    return [[sum(a[i][k] * b[k][j] for k in range(4)) for j in range(4)] for i in range(4)]


def local(n):
    if 'matrix' in n:
        m = n['matrix']
        return [[m[c * 4 + r] for c in range(4)] for r in range(4)]
    return mat4(n.get('translation', (0, 0, 0)), n.get('rotation', (0, 0, 0, 1)), n.get('scale', (1, 1, 1)))


def apply(m, p):
    return [sum(m[i][k] * (p[k] if k < 3 else 1) for k in range(4)) for i in range(3)]


def analyse(js):
    nodes = js['nodes']
    parent = {}
    for i, n in enumerate(nodes):
        for c in n.get('children', []):
            parent[c] = i
    world = {}

    def w(i):
        if i not in world:
            m = local(nodes[i])
            world[i] = mul(w(parent[i]), m) if i in parent else m
        return world[i]
    by_name = {}
    for i, n in enumerate(nodes):
        by_name.setdefault(n.get('name', ''), []).append(i)
    tris = 0
    lo, hi = [1e9] * 3, [-1e9] * 3
    per_node = {}
    for i, n in enumerate(nodes):
        if 'mesh' not in n:
            continue
        mesh = js['meshes'][n['mesh']]
        t = 0
        nlo, nhi = [1e9] * 3, [-1e9] * 3
        for p in mesh['primitives']:
            acc = js['accessors'][p['indices']] if 'indices' in p else None
            pos = js['accessors'][p['attributes']['POSITION']]
            t += (acc['count'] if acc else pos['count']) // 3
            mn, mx = pos['min'], pos['max']
            for cx in (mn[0], mx[0]):
                for cy in (mn[1], mx[1]):
                    for cz in (mn[2], mx[2]):
                        q = apply(w(i), (cx, cy, cz))
                        for k in range(3):
                            lo[k] = min(lo[k], q[k]); hi[k] = max(hi[k], q[k])
                            nlo[k] = min(nlo[k], q[k]); nhi[k] = max(nhi[k], q[k])
        tris += t
        per_node[n.get('name', str(i))] = dict(tris=t, min=[round(v, 4) for v in nlo], max=[round(v, 4) for v in nhi])
    pos = {name: [round(v, 5) for v in (w(ids[0])[0][3], w(ids[0])[1][3], w(ids[0])[2][3])] for name, ids in by_name.items()}
    return dict(tris=tris, bbox_min=lo, bbox_max=hi, pos=pos, by_name=by_name, per_node=per_node)


def common_checks(js, binlen):
    issues = []
    ext = set(js.get('extensionsUsed', [])) | set(js.get('extensionsRequired', []))
    bad = {e for e in ext if any(k in e.lower() for k in ('draco', 'meshopt', 'ktx', 'webp', 'basisu'))}
    if bad:
        issues.append('compression/texture extensions used: %s' % sorted(bad))
    if js.get('images') or js.get('textures'):
        issues.append('contains images/textures')
    if js.get('animations'):
        issues.append('contains animations')
    for m in js.get('meshes', []):
        for p in m['primitives']:
            if 'targets' in p:
                issues.append('morph targets present')
    return issues, sorted(ext)


def validate_car(key, spec, path):
    # car checks live in cars_validate.py (reads the vertex data as well as the JSON chunk)
    import cars_validate
    return cars_validate.validate_car(key, spec, path)


def _validate_car_first_pass(key, spec, path):
    js, binchunk, size = load_glb(path)
    res = dict(file=os.path.relpath(path, ROOT), bytes=size, checks={}, ok=True)
    A = analyse(js)
    issues, ext = common_checks(js, len(binchunk or b''))
    res['extensions_used'] = ext
    names = set(A['by_name'])
    need = ['car', 'body', 'glass', 'wheel_fl', 'wheel_fr', 'wheel_rl', 'wheel_rr', 'headlight_l', 'headlight_r',
            'bumper_front', 'bumper_rear', 'bonnet', 'mirror_l', 'mirror_r', 'roof_anchor']
    missing = [n for n in need if n not in names]
    res['checks']['required_nodes'] = dict(ok=not missing, missing=missing)
    # all under root 'car'
    roots = [n.get('name') for i, n in enumerate(js['nodes']) if i in js['scenes'][js.get('scene', 0)]['nodes']]
    res['checks']['single_root_car'] = dict(ok=roots == ['car'], roots=roots)
    # materials
    mnames = {m.get('name') for m in js.get('materials', [])}
    mats_need = ['paint', 'glass', 'headlight']
    res['checks']['materials'] = dict(ok=all(m in mnames for m in mats_need), present=sorted(mnames))
    node_mat = {}
    for i, n in enumerate(js['nodes']):
        if 'mesh' in n:
            node_mat[n['name']] = sorted({js['materials'][p['material']]['name'] for p in js['meshes'][n['mesh']]['primitives'] if 'material' in p})
    res['checks']['node_materials'] = dict(
        ok=(node_mat.get('body') == ['paint'] and node_mat.get('glass') == ['glass'] and
            node_mat.get('headlight_l') == ['headlight'] and node_mat.get('headlight_r') == ['headlight']),
        body=node_mat.get('body'), glass=node_mat.get('glass'), headlight_l=node_mat.get('headlight_l'))
    gl = next((m for m in js['materials'] if m.get('name') == 'glass'), {})
    hl = next((m for m in js['materials'] if m.get('name') == 'headlight'), {})
    res['checks']['glass_blend'] = dict(ok=gl.get('alphaMode') == 'BLEND', alphaMode=gl.get('alphaMode'))
    res['checks']['headlight_emissive'] = dict(ok=any(v > 0 for v in hl.get('emissiveFactor', [0, 0, 0])), emissiveFactor=hl.get('emissiveFactor'))
    res['checks']['no_compression_or_textures'] = dict(ok=not issues, issues=issues)
    # triangles
    res['tris'] = A['tris']
    res['checks']['triangle_budget'] = dict(ok=A['tris'] < 12000, tris=A['tris'], budget=12000)
    # bbox
    ext_ = [A['bbox_max'][k] - A['bbox_min'][k] for k in range(3)]
    meas = dict(width=ext_[0], height=ext_[1], length=ext_[2])
    exp = dict(width=spec['width'], height=spec['height'], length=spec['length'])
    rel = {k: abs(meas[k] - exp[k]) / exp[k] for k in meas}
    res['checks']['bbox_vs_cars_json'] = dict(ok=all(v <= 0.03 for v in rel.values()),
                                              measured={k: round(v, 4) for k, v in meas.items()}, expected=exp,
                                              rel_error_pct={k: round(100 * v, 2) for k, v in rel.items()},
                                              min=[round(v, 4) for v in A['bbox_min']], max=[round(v, 4) for v in A['bbox_max']])
    # wheels
    wexp = {'wheel_fl': (1, 1), 'wheel_fr': (-1, 1), 'wheel_rl': (1, -1), 'wheel_rr': (-1, -1)}
    wres, wok = {}, True
    for n, (sx, sz) in wexp.items():
        e = [sx * spec['track'] / 2, spec['wheel_radius'], sz * spec['wheelbase'] / 2]
        got = A['pos'].get(n)
        err = max(abs(got[k] - e[k]) for k in range(3)) if got else None
        ok = got is not None and err <= 0.01
        wok &= ok
        wres[n] = dict(expected=[round(v, 4) for v in e], got=got, max_abs_err_m=None if err is None else round(err, 5), ok=ok)
    res['checks']['wheel_positions_1cm'] = dict(ok=wok, wheels=wres)
    # wheel tyre extents: radius of the mesh around the node centre
    rad_ok, rads = True, {}
    for n in wexp:
        pn = A['per_node'].get(n)
        if pn:
            ext_y = pn['max'][1] - pn['min'][1]
            rads[n] = round(ext_y / 2, 4)
            rad_ok &= abs(ext_y / 2 - spec['wheel_radius']) < 0.01
    res['checks']['wheel_radius_matches'] = dict(ok=rad_ok, measured_radius=rads, expected=spec['wheel_radius'])
    # ground contact
    res['checks']['ground_at_y0'] = dict(ok=abs(A['bbox_min'][1]) < 0.01, min_y=round(A['bbox_min'][1], 4))
    # forward axis +Z
    P = A['pos']
    fw = []
    try:
        fw.append(P['headlight_l'][2] > 0 and P['headlight_r'][2] > 0)
        fw.append(P['bumper_front'][2] > 0 > P['bumper_rear'][2])
        fw.append(P['wheel_fl'][2] > 0 and P['wheel_fl'][0] > 0)
        fw.append(P['headlight_l'][0] > 0 > P['headlight_r'][0])
        fw.append(P['mirror_l'][0] > 0 > P['mirror_r'][0])
        fw.append(P['bonnet'][2] > 0)
        fw.append(abs(P['car'][0]) < 1e-6 and abs(P['car'][1]) < 1e-6 and abs(P['car'][2]) < 1e-6)
        fw.append(abs(P['roof_anchor'][0]) < 0.01 and abs(P['roof_anchor'][1] - spec['roof_y']) < 0.01)
        zc = (A['bbox_max'][2] + A['bbox_min'][2]) / 2
    except KeyError as e:
        fw.append(False)
    res['checks']['forward_is_plus_z_left_is_plus_x'] = dict(
        ok=all(fw), flags=fw, headlight_l=P.get('headlight_l'), headlight_r=P.get('headlight_r'),
        bumper_front=P.get('bumper_front'), bumper_rear=P.get('bumper_rear'), roof_anchor=P.get('roof_anchor'),
        origin_note='car root at 0,0,0 on ground; wheels positions from formula')
    # lamps centred on own origin
    lamp_ok, lampd = True, {}
    for n in ('headlight_l', 'headlight_r'):
        pn = A['per_node'].get(n)
        if pn:
            ctr = [(pn['min'][k] + pn['max'][k]) / 2 for k in range(3)]
            d = max(abs(ctr[k] - P[n][k]) for k in range(3))
            lampd[n] = round(d, 4)
            lamp_ok &= d < 0.06
    res['checks']['headlight_origin_at_lamp_centre'] = dict(ok=lamp_ok, centre_offset_m=lampd)
    # compare wheel axis extents (axle along X): mesh x-extent should be ~ wheel_width, y/z ~ diameter
    ax_ok, axd = True, {}
    for n in wexp:
        pn = A['per_node'].get(n)
        if pn:
            ex = pn['max'][0] - pn['min'][0]
            ey = pn['max'][1] - pn['min'][1]
            axd[n] = dict(x_extent=round(ex, 3), y_extent=round(ey, 3))
            ax_ok &= abs(ex - spec['wheel_width']) < 0.03 and ey > ex
    res['checks']['wheel_axle_along_x'] = dict(ok=ax_ok, extents=axd)
    res['ok'] = all(c['ok'] for c in res['checks'].values())
    return res


PROP_RULES = {
    'stein': dict(nodes=['stein'], mats=['lager', 'foam'], tris=2000, h=(0.18, 0.22), base0=True),
    'lodge': dict(nodes=['lodge', 'lodge_building', 'lodge_terrace', 'lodge_railings', 'lodge_furniture', 'chairlift_pylon', 'chair_a', 'chair_b'], mats=[], tris=15000),
    'table': dict(nodes=['table'], mats=[], tris=3000, base0=True),
    'tree_pine': dict(nodes=['tree_pine'], mats=[], tris=300, base0=True),
    'tree_broadleaf': dict(nodes=['tree_broadleaf'], mats=[], tris=300, base0=True),
    'spectator': dict(nodes=['spectator'], mats=['shirt'], tris=250, base0=True),
    'flag': dict(nodes=['flag'], mats=[], tris=500, h=(2.1, 2.4), base0=True),
    'tee_marker': dict(nodes=['tee_marker'], mats=[], tris=500),
    'golf_cart': dict(nodes=['golf_cart'], mats=[], tris=4000, base0=True),
    'ramp': dict(nodes=['ramp'], mats=[], tris=200),
    'sign': dict(nodes=['sign'], mats=[], tris=1000, base0=True),
    'rock': dict(nodes=['rock'], mats=[], tris=1000, base0=True),
    'drone': dict(nodes=['drone'], mats=[], tris=2000),
}


def validate_prop(name, path):
    rule = PROP_RULES[name]
    js, b, size = load_glb(path)
    A = analyse(js)
    issues, ext = common_checks(js, 0)
    res = dict(file=os.path.relpath(path, ROOT), bytes=size, tris=A['tris'], checks={}, ok=True)
    miss = [n for n in rule['nodes'] if n not in A['by_name']]
    res['checks']['required_nodes'] = dict(ok=not miss, missing=miss)
    mnames = {m.get('name') for m in js.get('materials', [])}
    mm = [m for m in rule['mats'] if m not in mnames]
    res['checks']['materials'] = dict(ok=not mm, missing=mm, present=sorted(mnames))
    res['checks']['triangle_budget'] = dict(ok=A['tris'] <= rule['tris'], tris=A['tris'], budget=rule['tris'])
    res['checks']['no_compression_or_textures'] = dict(ok=not issues, issues=issues)
    ext_ = [round(A['bbox_max'][k] - A['bbox_min'][k], 3) for k in range(3)]
    res['bbox'] = dict(min=[round(v, 3) for v in A['bbox_min']], max=[round(v, 3) for v in A['bbox_max']], size_xyz=ext_)
    if rule.get('base0'):
        res['checks']['origin_at_base'] = dict(ok=abs(A['bbox_min'][1]) < 0.02, min_y=round(A['bbox_min'][1], 4))
    if 'h' in rule:
        lo, hi = rule['h']
        res['checks']['height'] = dict(ok=lo <= ext_[1] <= hi, height=ext_[1], expected=[lo, hi])
    if name == 'ramp':
        mn, mx = A['bbox_min'], A['bbox_max']
        ok = all(abs(a - e) < 1e-4 for a, e in zip(list(mn) + list(mx), [-0.5, 0, 0, 0.5, 1, 1]))
        res['checks']['unit_wedge_exact'] = dict(ok=ok, min=mn, max=mx, expected_min=[-0.5, 0, 0], expected_max=[0.5, 1, 1])
    if name == 'lodge':
        res['checks']['terrace_origin'] = dict(ok=abs(A['per_node']['lodge_terrace']['max'][1]) < 0.01,
                                              terrace_top_y=A['per_node']['lodge_terrace']['max'][1],
                                              terrace_x=[A['per_node']['lodge_terrace']['min'][0], A['per_node']['lodge_terrace']['max'][0]])
    if name == 'stein':
        ok = res['bbox']['size_xyz'][1] <= 0.22
        res['checks']['stein_height'] = dict(ok=0.18 <= ext_[1] <= 0.22, height=ext_[1])
    res['ok'] = all(c['ok'] for c in res['checks'].values())
    return res


def load_extra_rules():
    """assets/src/rules_*.py may define RULES = {prop_name: {nodes, mats, tris, ...}} (same schema as PROP_RULES)."""
    import glob, importlib.util
    for f in sorted(glob.glob(os.path.join(os.path.dirname(__file__), 'rules_*.py'))):
        spec = importlib.util.spec_from_file_location(os.path.basename(f)[:-3], f)
        m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
        PROP_RULES.update(getattr(m, 'RULES', {}))


def main():
    load_extra_rules()
    ap = argparse.ArgumentParser()
    ap.add_argument('--only', default='', help='comma list of car keys / prop names; skips writing the default output unless --out is given')
    ap.add_argument('--out', default=os.path.join(ROOT, 'docs/evidence/assets/validation.json'))
    a = ap.parse_args()
    only = [x for x in a.only.split(',') if x]
    cars = {c['key']: c for c in json.load(open(os.path.join(ROOT, 'assets/cars.json')))['cars']}
    out = dict(contract='docs/CONTRACT.md s3', cars={}, props={})
    for k, spec in cars.items():
        if only and k not in only:
            continue
        p = os.path.join(ROOT, 'web/public/assets/cars', k + '.glb')
        out['cars'][k] = validate_car(k, spec, p) if os.path.exists(p) else dict(ok=False, error='missing file')
    _pat = json.load(open(os.path.join(ROOT, 'assets/cars.json'))).get('patrol')
    _pp = os.path.join(ROOT, 'web/public/assets/cars/patrol.glb')
    if _pat and os.path.exists(_pp) and (not only or 'patrol' in only):
        out['patrol'] = validate_car('patrol', _pat, _pp)
    for n in PROP_RULES:
        if only and n not in only:
            continue
        p = os.path.join(ROOT, 'web/public/assets/props', n + '.glb')
        out['props'][n] = validate_prop(n, p) if os.path.exists(p) else dict(ok=False, error='missing file')
    out['all_ok'] = all(v['ok'] for v in list(out['cars'].values()) + list(out['props'].values()))
    if only and a.out == os.path.join(ROOT, 'docs/evidence/assets/validation.json'):
        a.out = os.path.join(ROOT, 'docs/evidence/assets/validation_partial_%s.json' % '_'.join(only)[:60])
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    json.dump(out, open(a.out, 'w'), indent=1)
    for grp in ('cars', 'props'):
        for k, v in out[grp].items():
            bad = [c for c, d in v.get('checks', {}).items() if not d['ok']]
            print('%-6s %-18s ok=%s tris=%s bytes=%s %s' % (grp, k, v['ok'], v.get('tris'), v.get('bytes'), ('FAIL: ' + ','.join(bad)) if bad else ''))
    print('ALL OK' if out['all_ok'] else 'SOME FAILED')
    return 0 if out['all_ok'] else 1


if __name__ == '__main__':
    sys.exit(main())
