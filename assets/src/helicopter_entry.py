"""Local entry script (runs inside Blender via blender-job.js): builds helicopter.glb only.

  blender-job.js submit helicopter_entry.py --name gtl-heli -- --src <share>/gtl_heli/src --out <share>/gtl_heli/out
"""
import sys, os, argparse
argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument('--src', required=True)
ap.add_argument('--out', required=True)
a = ap.parse_args(argv)
sys.path.insert(0, a.src)
import gtl
import helicopter

gtl.clear_scene()
helicopter.build_helicopter()
path = os.path.join(a.out, 'props', 'helicopter.glb')
size = gtl.export_glb(path)
print("BUILT helicopter", path, size, "tris", gtl.tri_total(None))
