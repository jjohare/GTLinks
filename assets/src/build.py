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
ap.add_argument('--build-cars', action='store_true')
a = ap.parse_args(argv)
sys.path.insert(0, a.src)

import bpy
import gtl

report = {}

def build_one_car(key, spec):
    gtl.clear_scene()
    root = gtl.empty("car")
    import cars as carmod  # lazy: only imported when cars are actually built (--build-cars)
    carmod.build_car(key, spec, root)
    if os.environ.get('GTL_AO', '1') == '1':
        t0 = time.time(); carmod.bake_ao(); print('AO baked in %.1fs' % (time.time() - t0))
    path = os.path.join(a.out, 'cars', key + '.glb')
    size = gtl.export_glb(path)
    report[key] = dict(file=path, bytes=size, tris=gtl.tri_total(root))
    print("BUILT", key, report[key])

import importlib
PROP_MODULES = ['props', 'props2', 'props3', 'lodge', 'helicopter']

def find_builder(name):
    for mn in PROP_MODULES:
        try:
            mod = importlib.import_module(mn)
        except ImportError:
            continue
        fn = getattr(mod, 'build_' + name, None)
        if fn:
            return fn
    raise KeyError('no builder build_%s in %s' % (name, PROP_MODULES))

def all_prop_names():
    names = []
    for mn in PROP_MODULES:
        try:
            mod = importlib.import_module(mn)
        except ImportError:
            continue
        names += [n[6:] for n in dir(mod) if n.startswith('build_') and callable(getattr(mod, n)) and n[6:] not in names]
    return names

def build_one_prop(name):
    gtl.clear_scene()
    find_builder(name)()
    path = os.path.join(a.out, 'props', name + '.glb')
    size = gtl.export_glb(path)
    report[name] = dict(file=path, bytes=size, tris=gtl.tri_total(None))
    print("BUILT", name, report[name])

specs = gtl.load_cars(a.cars)
with open(a.cars) as _f:            # the patrol car sits beside the player cars in cars.json
    _patrol = json.load(_f).get('patrol')
if _patrol:
    specs[_patrol['key']] = _patrol
PROPS = all_prop_names()
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
if not a.build_cars and any(kd == 'car' for kd, _ in todo):
    print('SKIPPED cars (run.sh with GTL_BUILD_CARS=1 to build car GLBs)')
    todo = [t for t in todo if t[0] != 'car']
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
