"""Car-only build entry (runs inside Blender via blender-job.js).  Same result as build.py for a car, plus
the patrol car and an optional alternative cars.json (used by the 'models follow the file' check).

  blender-job.js submit cars_job.py -- --src S --cars cars.json --out DIR --what <key,key|cars|all> [--ao 0|1]
"""
import sys, os, json, argparse, time, traceback
argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument('--src', required=True); ap.add_argument('--cars', required=True); ap.add_argument('--out', required=True)
ap.add_argument('--what', default='all'); ap.add_argument('--ao', type=int, default=1)
a = ap.parse_args(argv)
sys.path.insert(0, a.src)
import bpy
import gtl
import cars as carmod

with open(a.cars) as f:
    data = json.load(f)
specs = {c['key']: c for c in data['cars']}
player = list(specs)
if 'patrol' in data:
    specs['patrol'] = data['patrol']
want = []
for w in a.what.split(','):
    want += player if w == 'cars' else list(specs) if w == 'all' else [w]
os.makedirs(os.path.join(a.out, 'cars'), exist_ok=True)
fails = 0
report = {}
for key in want:
    try:
        t0 = time.time()
        gtl.clear_scene()
        root = gtl.empty("car")
        carmod.build_car(key, specs[key], root)
        if a.ao:
            carmod.bake_ao()
        path = os.path.join(a.out, 'cars', key + '.glb')
        size = gtl.export_glb(path)
        per = {}
        for o in bpy.context.scene.objects:
            if o.type == 'MESH':
                o.data.calc_loop_triangles()
                per[o.name] = len(o.data.loop_triangles)
        report[key] = dict(bytes=size, tris=sum(per.values()), per_node=per, seconds=round(time.time() - t0, 1))
        print("BUILT", key, size, sum(per.values()), json.dumps(per, sort_keys=True))
    except Exception:
        fails += 1
        traceback.print_exc()
        print("FAILED", key)
with open(os.path.join(a.out, 'cars_report.json'), 'w') as f:
    json.dump(report, f, indent=1)
sys.exit(1 if fails else 0)
