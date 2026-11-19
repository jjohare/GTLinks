"""Preview renders. Re-imports the exported GLBs (so what you see is what the game loads).

  blender-job.js submit render.py -- --src S --glb DIR --out DIR --what <cars|lodge|props|name,...>
"""
import sys, os, math, argparse
argv = sys.argv[sys.argv.index('--') + 1:]
ap = argparse.ArgumentParser()
ap.add_argument('--src'); ap.add_argument('--glb'); ap.add_argument('--out'); ap.add_argument('--what', default='cars')
ap.add_argument('--samples', type=int, default=48)
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
    nt = w.node_tree
    bg = nt.nodes['Background']
    bg.inputs['Color'].default_value = (0.30, 0.50, 0.82, 1)
    bg.inputs['Strength'].default_value = 0.8
    sc.view_settings.exposure = 0.0
    try:
        sc.view_settings.view_transform = 'Standard'
    except Exception:
        pass
    sun = bpy.data.lights.new('sun', 'SUN'); sun.energy = 3.0; sun.angle = math.radians(3)
    so = bpy.data.objects.new('sun', sun); bpy.context.scene.collection.objects.link(so)
    so.rotation_euler = (math.radians(48), 0, math.radians(30))
    return sc

def ground(size=200, rgb=(0.05, 0.18, 0.03)):
    bpy.ops.mesh.primitive_plane_add(size=size, location=(0, 0, -0.002))
    g = bpy.context.object
    m = bpy.data.materials.new('grass'); m.use_nodes = True
    m.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (*rgb, 1)
    m.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = 0.95
    g.data.materials.append(m)

def cam(loc, target, lens=50):
    c = bpy.data.cameras.new('cam'); c.lens = lens; c.clip_end = 2000
    o = bpy.data.objects.new('cam', c); bpy.context.scene.collection.objects.link(o)
    o.location = loc
    d = Vector(target) - Vector(loc)
    o.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    bpy.context.scene.camera = o
    return o

def render(path):
    bpy.context.scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    print('RENDERED', path)

def load(name):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=os.path.join(a.glb, name + '.glb'))
    return [o for o in bpy.data.objects if o not in before]

def do_car(k):
    setup((1280, 640))
    ground(); load(k)
    cam((6.6, -6.2, 2.4), (0, 0.0, 0.85), 45); render(os.path.join(a.out, f'{k}_front34.png'))
    for o in list(bpy.data.objects):
        if o.type == 'CAMERA': bpy.data.objects.remove(o)
    cam((11.5, 0, 1.0), (0, 0, 0.9), 50); render(os.path.join(a.out, f'{k}_side.png'))
    for o in list(bpy.data.objects):
        if o.type == 'CAMERA': bpy.data.objects.remove(o)
    cam((-6.0, 6.8, 2.4), (0, 0, 0.85), 45); render(os.path.join(a.out, f'{k}_rear34.png'))

def do_lodge():
    setup((1600, 800))
    ground(300)
    load('lodge')
    cam((17, -26, 7.5), (0, 3, 3.5), 28); render(os.path.join(a.out, 'lodge_front.png'))
    for o in list(bpy.data.objects):
        if o.type == 'CAMERA': bpy.data.objects.remove(o)
    cam((-25, -9, 11), (2, 8, 3.5), 28); render(os.path.join(a.out, 'lodge_back.png'))
    for o in list(bpy.data.objects):
        if o.type == 'CAMERA': bpy.data.objects.remove(o)
    cam((6, -9, 2.4), (0, 8, 2.2), 32); render(os.path.join(a.out, 'lodge_terrace.png'))

def do_sheet(names, outname, cols, spacing, cam_pos, target, lens=40, res=(1600, 800)):
    setup(res); ground(120)
    for i, n in enumerate(names):
        objs = load(n)
        roots = [o for o in objs if o.parent is None]
        cx = (i % cols) * spacing - (cols - 1) * spacing / 2
        cy = -(i // cols) * spacing
        for r_ in roots:
            r_.location.x += cx; r_.location.y += cy
    cam(cam_pos, target, lens)
    render(os.path.join(a.out, outname))

os.makedirs(a.out, exist_ok=True)
for w in a.what.split(','):
    if w == 'cars':
        for k in KEYS: do_car(k)
    elif w in KEYS:
        do_car(w)
    elif w == 'lodge':
        do_lodge()
    elif w == 'propsheet':   # large props
        do_sheet(['table', 'tree_pine', 'tree_broadleaf', 'rock', 'sign', 'golf_cart'], 'props_large.png', 3, 7.5,
                 (0, -30, 9), (0, -4.5, 2.2), 38)
    elif w == 'steincloseup':
        do_sheet(['stein'], 'stein_close.png', 1, 1.0, (0.30, -0.42, 0.22), (0.01, 0.0, 0.095), 60, (800, 800))
    elif w == 'propsheet2':  # small props, close camera
        do_sheet(['stein', 'tee_marker', 'flag', 'spectator', 'drone', 'ramp'], 'props_small.png', 6, 1.2,
                 (0.0, -7.0, 1.2), (0.0, 0.0, 0.85), 35, (1600, 500))
