"""(props2 helper) Preview renders (Cycles, neutral studio). Re-imports the exported GLBs, so the picture is what the game loads.

  blender-job.js submit render.py -- --src S --glb DIR --out DIR --what <list>

--what items (comma separated):
  cars                 all four cars: front34, side, rear34, close34 (6 m orbit distance), roof (underside view), roofclose
  <car key>            one car, same views
  lodge                lodge_front / lodge_back / lodge_terrace
  view:<prop>[,...]    any prop (or lodge) auto-framed: <prop>_view1.png (front 3/4) and <prop>_view2.png (back 3/4)
  sheet:<a>+<b>+<c>    several props side by side -> sheet_<a>_<b>....png
"""
import sys, os, math, argparse
argv = sys.argv[sys.argv.index('--') + 1:]
ap = argparse.ArgumentParser()
ap.add_argument('--src'); ap.add_argument('--glb'); ap.add_argument('--out'); ap.add_argument('--what', default='cars')
ap.add_argument('--samples', type=int, default=64)
a = ap.parse_args(argv)
sys.path.insert(0, a.src)
import bpy
from mathutils import Vector

KEYS = ['escapade_2009', 'glug_2017', 'genesips_2021', 'rangeroller_2026']


def setup(res=(1280, 720)):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.samples = a.samples
    sc.cycles.use_denoising = True
    sc.render.resolution_x, sc.render.resolution_y = res
    try:
        prefs = bpy.context.preferences.addons['cycles'].preferences
        for kind in ('OPTIX', 'CUDA'):
            prefs.compute_device_type = kind
            prefs.refresh_devices() if hasattr(prefs, 'refresh_devices') else prefs.get_devices()
            devs = [d for d in prefs.devices if d.type == kind]
            if devs:
                for d in prefs.devices:
                    d.use = d.type == kind
                sc.cycles.device = 'GPU'
                break
    except Exception as e:
        print('gpu setup failed', e)
    w = bpy.data.worlds.new('w'); sc.world = w; w.use_nodes = True
    bg = w.node_tree.nodes['Background']
    bg.inputs['Color'].default_value = (0.62, 0.66, 0.72, 1)
    bg.inputs['Strength'].default_value = 1.1
    try:
        sc.view_settings.view_transform = 'Standard'
    except Exception:
        pass
    # soft key (large angular size) + weak fill from the other side
    for name, en, rot, ang in (('key', 2.2, (math.radians(52), 0, math.radians(35)), 18),
                               ('fill', 0.7, (math.radians(70), 0, math.radians(-140)), 40)):
        l = bpy.data.lights.new(name, 'SUN'); l.energy = en; l.angle = math.radians(ang)
        o = bpy.data.objects.new(name, l); sc.collection.objects.link(o); o.rotation_euler = rot
    return sc


def ground(size=400, rgb=(0.34, 0.35, 0.36)):
    bpy.ops.mesh.primitive_plane_add(size=size, location=(0, 0, -0.002))
    g = bpy.context.object
    m = bpy.data.materials.new('floor'); m.use_nodes = True
    m.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (*rgb, 1)
    m.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = 0.9
    g.data.materials.append(m)


def clear_cams():
    for o in list(bpy.data.objects):
        if o.type == 'CAMERA':
            bpy.data.objects.remove(o)


def cam(loc, target, lens=50):
    clear_cams()
    c = bpy.data.cameras.new('cam'); c.lens = lens; c.clip_end = 2000; c.clip_start = 0.05
    o = bpy.data.objects.new('cam', c); bpy.context.scene.collection.objects.link(o)
    o.location = loc
    o.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    bpy.context.scene.camera = o


def render(path):
    bpy.context.scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    print('RENDERED', path)


def load(name):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=os.path.join(a.glb, name + '.glb'))
    return [o for o in bpy.data.objects if o not in before]


def bounds(objs):
    lo, hi = Vector((1e9,) * 3), Vector((-1e9,) * 3)
    for o in objs:
        if o.type != 'MESH':
            continue
        for c in o.bound_box:
            w = o.matrix_world @ Vector(c)
            lo = Vector(map(min, lo, w)); hi = Vector(map(max, hi, w))
    return lo, hi


def do_car(k):
    setup((1280, 640)); ground()
    objs = load(k)
    root = [o for o in objs if o.parent is None][0]
    # car faces -Y in Blender, left = +X
    cam((6.6, -6.2, 2.4), (0, 0, 0.85), 45); render(os.path.join(a.out, f'{k}_front34.png'))
    cam((11.5, 0, 1.0), (0, 0, 0.9), 50); render(os.path.join(a.out, f'{k}_side.png'))
    cam((-6.0, 6.8, 2.4), (0, 0, 0.85), 45); render(os.path.join(a.out, f'{k}_rear34.png'))
    # drone-orbit distance: ~6 m from the car centre, 35 mm, low-ish
    cam((3.6, -4.9, 1.7), (0, -0.2, 0.8), 30); render(os.path.join(a.out, f'{k}_close34.png'))
    cam((-3.4, 4.9, 1.9), (0, 0.2, 0.8), 30); render(os.path.join(a.out, f'{k}_closerear.png'))

def do_shot(spec):
    # shot:<prop>:<out>:gx,gy,gz:tx,ty,tz:lens  (game frame, metres)
    _, prop, out, c, t, lens = spec.split(':')
    g = lambda s: (lambda v: Vector((v[0], -v[2], v[1])))([float(x) for x in s.split(',')])
    setup((1100, 750)); ground(300)
    load(prop)
    cam(g(c), g(t), float(lens))
    render(os.path.join(a.out, out + '.png'))


os.makedirs(a.out, exist_ok=True)
for w in a.what.split(';'):
    if w.startswith('shot:'):
        do_shot(w)
