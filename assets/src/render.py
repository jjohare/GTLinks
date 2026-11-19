"""Preview renders (Cycles, neutral studio). Re-imports the exported GLBs, so the picture is what the game loads.

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
    # on its roof: rotate 180 deg about the long (Y) axis, roof on the ground
    root.rotation_mode = 'XYZ'
    root.rotation_euler = (0, math.radians(180), 0)
    bpy.context.view_layer.update()
    lo, hi = bounds(objs)
    root.location = (0, 0, -lo.z)
    bpy.context.view_layer.update()
    cam((3.4, -4.6, 2.3), (0, 0, 0.7), 32); render(os.path.join(a.out, f'{k}_roof.png'))
    cam((0.0, -4.2, 0.55), (0, 0.6, 0.35), 32); render(os.path.join(a.out, f'{k}_roofunder.png'))
    root.rotation_euler = (0, 0, 0); root.location = (0, 0, 0)
    bpy.context.view_layer.update()
    cam((0.0, -3.6, 1.0), (0, 0, 0.9), 40); render(os.path.join(a.out, f'{k}_nose.png'))


def do_lodge():
    setup((1600, 800)); ground(300, (0.28, 0.42, 0.22))
    load('lodge')
    cam((17, -26, 7.5), (0, 3, 3.5), 28); render(os.path.join(a.out, 'lodge_front.png'))
    cam((-25, -9, 11), (2, 8, 3.5), 28); render(os.path.join(a.out, 'lodge_back.png'))
    cam((6, -9, 2.4), (0, 8, 2.2), 32); render(os.path.join(a.out, 'lodge_terrace.png'))
    cam((13, -4, 3.0), (17.5, 0, 6.0), 35); render(os.path.join(a.out, 'lodge_chairlift.png'))
    cam((-4, -3.5, 2.4), (-5, -7, 2.6), 30); render(os.path.join(a.out, 'lodge_closeup.png'))


def do_view(name):
    setup((1100, 750)); ground(300)
    objs = load(name)
    lo, hi = bounds(objs)
    if lo.z < -0.01:      # prop hangs below its origin (e.g. golf_club): lift it clear of the ground plane
        for o in objs:
            if o.parent is None:
                o.location.z += -lo.z
        bpy.context.view_layer.update()
        lo, hi = bounds(objs)
    ctr = (lo + hi) / 2
    size = max((hi - lo).length, 0.05)
    for tag, dirv in (('view1', Vector((0.8, -1.0, 0.55))), ('view2', Vector((-0.8, 1.0, 0.55)))):
        d = dirv.normalized() * size * 1.55
        cam(ctr + d, ctr, 40)
        render(os.path.join(a.out, f'{name}_{tag}.png'))


def do_sheet(names):
    setup((1600, 800)); ground(300)
    x = 0.0
    allobjs = []
    for n in names:
        objs = load(n)
        lo, hi = bounds(objs)
        roots = [o for o in objs if o.parent is None]
        sh = x - lo.x
        for r in roots:
            r.location.x += sh
        x += (hi.x - lo.x) + 0.6
        allobjs += objs
    lo, hi = bounds(allobjs)
    ctr = (lo + hi) / 2
    span = max(hi.x - lo.x, (hi.z - lo.z) * 1.6)
    cam((ctr.x, ctr.y - span * 1.25, ctr.z + span * 0.12), ctr, 40)
    render(os.path.join(a.out, 'sheet_' + '_'.join(names) + '.png'))


os.makedirs(a.out, exist_ok=True)
for w in a.what.split(','):
    if w == 'cars':
        for k in KEYS: do_car(k)
    elif w in KEYS:
        do_car(w)
    elif w == 'lodge':
        do_lodge()
    elif w.startswith('view:'):
        do_view(w[5:])
    elif w.startswith('sheet:'):
        do_sheet(w[6:].split('+'))
    elif w in KEYS:
        pass
    else:
        do_view(w)
