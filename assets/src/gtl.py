"""GTLinks shared Blender helpers.

All geometry is authored in the GAME frame (x = car's left, y = up, z = forward) and
converted to Blender's frame at one point, `to_object`.  Blender (x, y, z) = (gx, -gz, gy),
a proper rotation, so a glTF export (y-up) yields +Z forward, +Y up, +X left.
"""
import math, os, json
import bpy, bmesh
from mathutils import Vector, Matrix, Quaternion

# ----------------------------------------------------------------- materials
MATS = {}

def clear_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    MATS.clear()

def make_mat(name, rgb, metallic=0.0, rough=0.7, alpha=1.0, emit=None, emit_strength=1.0, double=False):
    """Plain PBR factor material. rgb is a 0-1 sRGB-ish triple or '#rrggbb'."""
    if isinstance(rgb, str):
        h = rgb.lstrip('#')
        rgb = tuple(int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4))
    # Blender takes linear values for Base Color; hex above is treated as sRGB
    lin = tuple((c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4) for c in rgb)
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*lin, 1.0)
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = rough
    if alpha < 1.0:
        bsdf.inputs["Alpha"].default_value = alpha
        for attr, val in (("blend_method", "BLEND"), ("surface_render_method", "BLENDED")):
            try:
                setattr(m, attr, val)
            except Exception:
                pass
    if emit is not None:
        e = tuple((c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4) for c in
                  (tuple(int(emit.lstrip('#')[i:i + 2], 16) / 255.0 for i in (0, 2, 4)) if isinstance(emit, str) else emit))
        bsdf.inputs["Emission Color"].default_value = (*e, 1.0)
        bsdf.inputs["Emission Strength"].default_value = emit_strength
    if double:
        m.use_backface_culling = False
    MATS[name] = m
    return m

def mat(name):
    return MATS[name]

# ----------------------------------------------------------------- mesh builder
def B(p):
    """game (x, y, z) -> blender"""
    return Vector((p[0], -p[2], p[1]))

def frame_q(direction):
    d = Vector(direction).normalized()
    return Vector((0, 0, 1)).rotation_difference(d)

class MB:
    """Accumulates primitives in game coordinates, then becomes one Blender object."""

    def __init__(self):
        self.bm = bmesh.new()
        self.slots = []

    # -- plumbing
    def _mi(self, name):
        if name not in self.slots:
            self.slots.append(name)
        return self.slots.index(name)

    def _verts(self, pts):
        return [self.bm.verts.new(Vector(p)) for p in pts]

    def _fix(self, faces):
        bmesh.ops.recalc_face_normals(self.bm, faces=faces)

    def _face(self, vs, m):
        try:
            f = self.bm.faces.new(vs)
        except ValueError:
            return None
        f.material_index = self._mi(m)
        return f

    # -- primitives
    def face(self, pts, m, hint=None, flip=False):
        """Single polygon. hint = outward direction vector (normal is oriented toward it)."""
        vs = self._verts(pts)
        f = self._face(vs, m)
        if f is None:
            return None
        if hint is not None:
            f.normal_update()
            if f.normal.dot(Vector(hint)) < 0:
                f.normal_flip()
        elif flip:
            f.normal_flip()
        return f

    def loft(self, rings, m, caps=True, solid=True, flip=False):
        """Rings: equal-length lists of 3D points. Closed around each ring; caps optional."""
        n = len(rings[0])
        vr = [self._verts(r) for r in rings]
        faces = []
        for i in range(len(vr) - 1):
            for j in range(n):
                k = (j + 1) % n
                f = self._face([vr[i][j], vr[i][k], vr[i + 1][k], vr[i + 1][j]], m)
                if f:
                    faces.append(f)
        if caps:
            for r in (vr[0], vr[-1]):
                f = self._face(list(r), m)
                if f:
                    faces.append(f)
        if solid and caps:
            self._fix(faces)
        elif flip:
            for f in faces:
                f.normal_flip()
        return faces

    def box(self, c, s, m, bevel=0.0, rot=None):
        """Box centred c, size s=(x,y,z); chamfer 'bevel' on all edges; rot = mathutils Matrix3/Quaternion."""
        hx, hy, hz = s[0] / 2, s[1] / 2, s[2] / 2
        b = min(bevel, hx * 0.9, hy * 0.9, hz * 0.9)
        c = Vector(c)

        def oct_ring(x, y, z, cb):
            if cb <= 1e-6:
                pts = [(x, y), (-x, y), (-x, -y), (x, -y)]
            else:
                pts = [(x, y - cb), (x - cb, y), (-(x - cb), y), (-x, y - cb),
                       (-x, -(y - cb)), (-(x - cb), -y), (x - cb, -y), (x, -(y - cb))]
            return [Vector((px, py, z)) for px, py in pts]
        if b <= 1e-6:
            rings = [oct_ring(hx, hy, -hz, 0), oct_ring(hx, hy, hz, 0)]
        else:
            rings = [oct_ring(hx - b, hy - b, -hz, b * 0.6), oct_ring(hx, hy, -hz + b, b),
                     oct_ring(hx, hy, hz - b, b), oct_ring(hx - b, hy - b, hz, b * 0.6)]
        out = []
        for r in rings:
            rr = []
            for p in r:
                if rot is not None:
                    p = rot @ p
                rr.append(c + p)
            out.append(rr)
        return self.loft(out, m)

    def lathe(self, c, axis, profile, segs, m, solid=True, flip=False, scale=(1, 1), phase=0.0, closed=False, mod=None):
        """Revolve profile [(rho, h), ...] about axis through c. rho=0 collapses to a pole.
        scale = (sx, sy) stretches the circle in the local frame (for oval lamps)."""
        q = frame_q(axis)
        c = Vector(c)
        rings, poles = [], []
        verts = []
        for pi_, (rho, h) in enumerate(profile):
            if rho < 1e-7:
                verts.append(self.bm.verts.new(c + q @ Vector((0, 0, h))))
            else:
                ring = []
                for i in range(segs):
                    a = phase + 2 * math.pi * i / segs
                    k_ = mod(pi_, i) if mod else 1.0
                    p = Vector((rho * k_ * math.cos(a) * scale[0], rho * k_ * math.sin(a) * scale[1], h))
                    ring.append(self.bm.verts.new(c + q @ p))
                verts.append(ring)
        faces = []
        pairs = list(zip(verts[:-1], verts[1:]))
        if closed:
            pairs.append((verts[-1], verts[0]))
        for a, b in pairs:
            if isinstance(a, list) and isinstance(b, list):
                for i in range(segs):
                    j = (i + 1) % segs
                    f = self._face([a[i], a[j], b[j], b[i]], m)
                    if f: faces.append(f)
            elif isinstance(a, list):
                for i in range(segs):
                    f = self._face([a[i], a[(i + 1) % segs], b], m)
                    if f: faces.append(f)
            elif isinstance(b, list):
                for i in range(segs):
                    f = self._face([a, b[(i + 1) % segs], b[i]], m)
                    if f: faces.append(f)
        if solid:
            # cap open ends
            for end in ([] if closed else (verts[0], verts[-1])):
                if isinstance(end, list):
                    f = self._face(list(end), m)
                    if f: faces.append(f)
            self._fix(faces)
        elif flip:
            for f in faces:
                f.normal_flip()
        return faces

    def cyl(self, c, axis, r, length, segs, m, scale=(1, 1), phase=0.0):
        return self.lathe(c, axis, [(r, -length / 2), (r, length / 2)], segs, m, scale=scale, phase=phase)

    def pipe(self, p0, p1, r, segs, m):
        p0, p1 = Vector(p0), Vector(p1)
        return self.cyl((p0 + p1) / 2, p1 - p0, r, (p1 - p0).length, segs, m)

    def frustum(self, c, axis, r0, r1, length, segs, m, phase=0.0):
        return self.lathe(c, axis, [(r0, -length / 2), (r1, length / 2)], segs, m, phase=phase)

    def ico(self, c, r, m, subdiv=1, scale=(1, 1, 1), jitter=0.0, seed=0, ymin=None):
        import random
        rnd = random.Random(seed)
        ret = bmesh.ops.create_icosphere(self.bm, subdivisions=subdiv, radius=1.0)
        vs = ret["verts"]
        c = Vector(c)
        for v in vs:
            d = v.co.copy()
            k = 1.0 + (rnd.uniform(-jitter, jitter) if jitter else 0.0)
            v.co = c + Vector((d.x * r * scale[0] * k, d.y * r * scale[1] * k, d.z * r * scale[2] * k))
            if ymin is not None and v.co.y < ymin:
                v.co.y = ymin
        faces = set()
        for v in vs:
            faces.update(v.link_faces)
        for f in faces:
            f.material_index = self._mi(m)
        self._fix(list(faces))
        return list(faces)

    def sector(self, c, ri, ro, a0, a1, x0, x1, segs, m):
        """Annulus sector in the YZ plane about axis X (a=0 -> +Z forward, + toward +Y), thickness x0..x1."""
        c = Vector(c)
        angs = [a0 + (a1 - a0) * i / segs for i in range(segs + 1)]

        def pt(rho, a, x):
            return c + Vector((x, rho * math.cos(a), rho * math.sin(a)))
        # note: y component uses cos, z uses sin -> swap so a measured from +Z
        def pt2(rho, a, x):
            return c + Vector((x, rho * math.sin(a), rho * math.cos(a)))
        rings = []
        for a in angs:
            rings.append([pt2(ro, a, x0), pt2(ro, a, x1), pt2(ri, a, x1), pt2(ri, a, x0)])
        return self.loft(rings, m)

    def from_mesh(self, me, blender_frame=True):
        """Load a Blender mesh (blender frame) into this builder in game frame."""
        names = [m.name for m in me.materials]
        vs = [self.bm.verts.new((v.co.x, v.co.z, -v.co.y)) for v in me.vertices]
        for p in me.polygons:
            f = self._face([vs[i] for i in p.vertices], names[p.material_index] if names else "paint")
        return self

    # -- finishing
    def merge(self, other, remap=None):
        """Absorb another MB (same coordinate frame)."""
        mp = {}
        for v in other.bm.verts:
            mp[v] = self.bm.verts.new(v.co)
        for f in other.bm.faces:
            nf = self.bm.faces.new([mp[v] for v in f.verts])
            nf.material_index = self._mi(other.slots[f.material_index]) if other.slots else 0
            nf.smooth = f.smooth
        for e in other.bm.edges:
            if len(e.link_faces) == 2:
                pass
        return self

    def smooth(self, angle=50.0):
        lim = math.radians(angle)
        for e in self.bm.edges:
            if len(e.link_faces) == 2:
                try:
                    a = e.calc_face_angle()
                except Exception:
                    a = 0.0
                e.smooth = a < lim
            else:
                e.smooth = False
        for f in self.bm.faces:
            f.smooth = True

    def flat(self):
        for e in self.bm.edges:
            e.smooth = False
        for f in self.bm.faces:
            f.smooth = False

    def tri_count(self):
        return sum(len(f.verts) - 2 for f in self.bm.faces)

    def to_object(self, name, origin=(0, 0, 0), parent=None, smooth=50.0):
        if smooth is None:
            self.flat()
        else:
            self.smooth(smooth)
        o = Vector(origin)
        for v in self.bm.verts:
            v.co = B(v.co - o)
        me = bpy.data.meshes.new(name)
        self.bm.to_mesh(me)
        self.bm.free()
        for sname in self.slots:
            me.materials.append(MATS[sname])
        obj = bpy.data.objects.new(name, me)
        bpy.context.scene.collection.objects.link(obj)
        obj.location = B(o)
        if parent is not None:
            obj.parent = parent
        return obj

def empty(name, loc=(0, 0, 0), parent=None):
    e = bpy.data.objects.new(name, None)
    bpy.context.scene.collection.objects.link(e)
    e.location = B(loc)
    if parent is not None:
        e.parent = parent
    return e

# ----------------------------------------------------------------- export / reporting
def tri_total(root):
    t = 0
    for o in bpy.context.scene.objects:
        if o.type == 'MESH':
            me = o.data
            me.calc_loop_triangles()
            t += len(me.loop_triangles)
    return t

def export_glb(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    kw = dict(filepath=path, export_format='GLB', export_apply=True, export_yup=True, export_vertex_color='ACTIVE',
              export_cameras=False, export_lights=False, export_animations=False,
              export_morph=False, export_image_format='NONE',
              export_draco_mesh_compression_enable=False)
    try:
        bpy.ops.export_scene.gltf(**kw)
    except TypeError:
        for k in ('export_vertex_color', 'export_draco_mesh_compression_enable'):
            kw.pop(k, None)
        bpy.ops.export_scene.gltf(**kw)
    return os.path.getsize(path)

def load_cars(path):
    with open(path) as f:
        return {c['key']: c for c in json.load(f)['cars']}


def bx(mb, x0, x1, y0, y1, z0, z1, m, bevel=0.0):
    """Axis-aligned box from min/max extents."""
    return mb.box(((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2), (abs(x1 - x0), abs(y1 - y0), abs(z1 - z0)), m, bevel=bevel)

def make_root(name):
    return empty(name)
