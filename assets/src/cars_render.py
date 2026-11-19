"""Car preview renders (Cycles, neutral studio, soft light).  Re-imports the exported GLBs, so the picture
is what the game loads.

  blender-job.js submit cars_render.py -- --glb DIR --out DIR --what <key,key,...|lineup> [--views a,b] [--samples N]

Views per car: front34, side, rear34, drone (three-quarter from 6 m at drone height), under (the car on its
roof, seen from a raised three-quarter angle at 6 m, as the wreck camera sees it), underrear, nose.
'lineup' renders every listed player car in side view, orthographic, to compare silhouettes.
"""
import sys, os, math, argparse
argv = sys.argv[sys.argv.index('--') + 1:]
ap = argparse.ArgumentParser()
ap.add_argument('--glb'); ap.add_argument('--out'); ap.add_argument('--what', default='')
ap.add_argument('--views', default='front34,side,rear34,drone,under,underrear,nose')
ap.add_argument('--samples', type=int, default=48); ap.add_argument('--res', default='1280x640')
a = ap.parse_args(argv)
import bpy
from mathutils import Vector

PLAYER = ['escapade_2009', 'glug_2017', 'genesips_2021', 'rangeroller_2026']


def setup(res):
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
            if [d for d in prefs.devices if d.type == kind]:
                for d in prefs.devices:
                    d.use = d.type == kind
                sc.cycles.device = 'GPU'
                break
    except Exception as e:
        print('gpu setup failed', e)
    w = bpy.data.worlds.new('w'); sc.world = w; w.use_nodes = True
    nt = w.node_tree
    bg = nt.nodes['Background']
    # soft studio: vertical gradient so chrome and paint have something to reflect
    tc = nt.nodes.new('ShaderNodeTexCoord'); sep = nt.nodes.new('ShaderNodeSeparateXYZ'); ramp = nt.nodes.new('ShaderNodeValToRGB')
    mp = nt.nodes.new('ShaderNodeMapRange')
    nt.links.new(tc.outputs['Generated'], sep.inputs[0]); nt.links.new(sep.outputs['Z'], mp.inputs['Value'])
    mp.inputs['From Min'].default_value = -0.2; mp.inputs['From Max'].default_value = 1.0
    nt.links.new(mp.outputs[0], ramp.inputs[0])
    ramp.color_ramp.elements[0].color = (0.30, 0.31, 0.33, 1); ramp.color_ramp.elements[1].color = (0.95, 0.97, 1.0, 1)
    nt.links.new(ramp.outputs[0], bg.inputs['Color'])
    bg.inputs['Strength'].default_value = 1.0
    try:
        sc.view_settings.view_transform = 'Standard'
    except Exception:
        pass
    for name, en, rot, ang in (('key', 2.4, (math.radians(50), 0, math.radians(38)), 22),
                               ('fill', 0.8, (math.radians(68), 0, math.radians(-135)), 45)):
        l = bpy.data.lights.new(name, 'SUN'); l.energy = en; l.angle = math.radians(ang)
        o = bpy.data.objects.new(name, l); sc.collection.objects.link(o); o.rotation_euler = rot
    bpy.ops.mesh.primitive_plane_add(size=400, location=(0, 0, -0.002))
    g = bpy.context.object
    m = bpy.data.materials.new('floor'); m.use_nodes = True
    bs = m.node_tree.nodes['Principled BSDF']
    bs.inputs['Base Color'].default_value = (0.36, 0.37, 0.38, 1); bs.inputs['Roughness'].default_value = 0.85
    g.data.materials.append(m)
    return sc


def cam(loc, target, lens=50, ortho=None):
    for o in list(bpy.data.objects):
        if o.type == 'CAMERA':
            bpy.data.objects.remove(o)
    c = bpy.data.cameras.new('cam'); c.lens = lens; c.clip_end = 2000; c.clip_start = 0.05
    if ortho:
        c.type = 'ORTHO'; c.ortho_scale = ortho
    o = bpy.data.objects.new('cam', c); bpy.context.scene.collection.objects.link(o)
    o.location = loc
    o.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    bpy.context.scene.camera = o


def render(name):
    bpy.context.scene.render.filepath = os.path.join(a.out, name)
    bpy.ops.render.render(write_still=True)
    print('RENDERED', name)


def load(name):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=os.path.join(a.glb, name + '.glb'))
    return [o for o in bpy.data.objects if o not in before]


def bounds(objs):
    lo, hi = Vector((1e9,) * 3), Vector((-1e9,) * 3)
    for o in objs:
        if o.type == 'MESH':
            for cc in o.bound_box:
                w = o.matrix_world @ Vector(cc)
                lo = Vector(map(min, lo, w)); hi = Vector(map(max, hi, w))
    return lo, hi


def do_car(k, views, res):
    setup(res)
    objs = load(k)
    root = [o for o in objs if o.parent is None][0]
    # imported car faces -Y in Blender; its left is +X
    if 'front34' in views:
        cam((5.6, -6.6, 2.1), (0, 0, 0.85), 45); render(f'{k}_front34.png')
    if 'side' in views:
        cam((12.0, 0, 1.0), (0, 0, 0.92), 55); render(f'{k}_side.png')
    if 'rear34' in views:
        cam((-5.4, 6.8, 2.2), (0, 0, 0.85), 45); render(f'{k}_rear34.png')
    if 'drone' in views:      # 6 m from the car centre, drone height, wide lens
        cam((3.3, -4.3, 2.6), (0, -0.1, 0.8), 28); render(f'{k}_drone.png')
    if 'nose' in views:
        cam((1.2, -4.4, 1.15), (0, 0, 0.8), 40); render(f'{k}_nose.png')
    if 'under' in views or 'underrear' in views:
        root.rotation_mode = 'XYZ'
        root.rotation_euler = (0, math.radians(180), 0)
        bpy.context.view_layer.update()
        lo, hi = bounds(objs)
        root.location = (0, 0, -lo.z)
        bpy.context.view_layer.update()
        if 'under' in views:
            cam((3.5, -3.9, 3.2), (0, 0, 1.0), 30); render(f'{k}_under.png')
        if 'underrear' in views:
            cam((-3.3, 4.0, 3.3), (0, 0, 1.0), 30); render(f'{k}_underrear.png')


def do_lineup(keys):
    setup((2400, 520))
    y = 0.0
    for k in keys:
        objs = load(k)
        root = [o for o in objs if o.parent is None][0]
        root.location.y = y
        y += 5.9
    mid = (y - 5.9) / 2
    cam((40, mid, 0.95), (0, mid, 0.95), ortho=5.9 * len(keys) + 0.4)
    render('cars_lineup_side.png')


os.makedirs(a.out, exist_ok=True)
res = tuple(int(v) for v in a.res.split('x'))
items = a.what.split(',')
keys = [w for w in items if w and w != 'lineup']
for k in keys:
    do_car(k, a.views.split(','), res)
if 'lineup' in items:
    do_lineup([k for k in PLAYER if os.path.exists(os.path.join(a.glb, k + '.glb'))])
