"""Entry script. Run inside Blender (via blender-job.js):

  blender-job.js submit build.py --name gtl-build -- --src <share>/gtl/src --cars <share>/gtl/cars.json \
      --out <share>/gtl/out --what cars|props|all|<key,key,...>

Writes <out>/cars/<key>.glb and <out>/props/<name>.glb and a build_report.json.
"""
import sys, os, json, argparse, time, traceback

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument('--src', required=True)
ap.add_argument('--cars', required=True)
ap.add_argument('--out', required=True)
ap.add_argument('--what', default='all')
a = ap.parse_args(argv)
sys.path.insert(0, a.src)

import bpy
import gtl
import cars as carmod

report = {}

def build_one_car(key, spec):
    gtl.clear_scene()
    root = gtl.empty("car")
    carmod.build_car(key, spec, root)
    path = os.path.join(a.out, 'cars', key + '.glb')
    size = gtl.export_glb(path)
    report[key] = dict(file=path, bytes=size, tris=gtl.tri_total(root))
    print("BUILT", key, report[key])

def build_one_prop(name):
    import props
    gtl.clear_scene()
    getattr(props, 'build_' + name)()
    path = os.path.join(a.out, 'props', name + '.glb')
    size = gtl.export_glb(path)
    report[name] = dict(file=path, bytes=size, tris=gtl.tri_total(None))
    print("BUILT", name, report[name])

specs = gtl.load_cars(a.cars)
PROPS = ['stein', 'lodge', 'table', 'tree_pine', 'tree_broadleaf', 'spectator', 'flag', 'tee_marker',
         'golf_cart', 'ramp', 'sign', 'rock', 'drone']
want = a.what.split(',')
todo = []
for w in want:
    if w == 'all':
        todo += [('car', k) for k in specs] + [('prop', p) for p in PROPS]
    elif w == 'cars':
        todo += [('car', k) for k in specs]
    elif w == 'props':
        todo += [('prop', p) for p in PROPS]
    elif w in specs:
        todo.append(('car', w))
    else:
        todo.append(('prop', w))
fails = 0
for kind, k in todo:
    try:
        if kind == 'car':
            build_one_car(k, specs[k])
        else:
            build_one_prop(k)
    except Exception:
        fails += 1
        traceback.print_exc()
        report[k] = dict(error=traceback.format_exc()[-400:])
with open(os.path.join(a.out, 'build_report_%d.json' % int(time.time())), 'w') as f:
    json.dump(report, f, indent=1)
if fails:
    sys.exit(1)
