"""Import a bike (usdz/usd/gltf), report size/licence metadata, export GLB, render front/back/left/right/top/bottom."""
import bpy, sys, os, math, mathutils
src, out, tag = sys.argv[sys.argv.index("--") + 1:]
V = mathutils.Vector
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
ext = os.path.splitext(src)[1].lower()
if ext in (".usdz", ".usd", ".usdc", ".usda"):
    bpy.ops.wm.usd_import(filepath=src)
else:
    bpy.ops.import_scene.gltf(filepath=src)
meshes = [o for o in sc.objects if o.type == "MESH"]
bpy.context.view_layer.update()
pts = [o.matrix_world @ V(c) for o in meshes for c in o.bound_box]
lo = V([min(p[i] for p in pts) for i in range(3)]); hi = V([max(p[i] for p in pts) for i in range(3)])
size = hi - lo
tris = sum(len(p.vertices) - 2 for o in meshes for p in o.data.polygons)
print("INFO", tag, "objects", len(meshes), "tris", tris, "size", [round(x, 3) for x in size])
for k, v in sc.items() if hasattr(sc, "items") else []:
    print("META", k, str(v)[:200])
bpy.ops.export_scene.gltf(filepath=os.path.join(out, tag + ".glb"), export_format="GLB")
c = (lo + hi) / 2; R = max(size) * 1.6
w = bpy.data.worlds.new("W"); sc.world = w; w.use_nodes = True
w.node_tree.nodes["Background"].inputs[0].default_value = (0.5, 0.52, 0.56, 1); w.node_tree.nodes["Background"].inputs[1].default_value = 1.0
bpy.ops.object.light_add(type="SUN", rotation=(math.radians(50), 0, math.radians(30))); bpy.context.active_object.data.energy = 3
sc.render.engine = "BLENDER_EEVEE_NEXT"; sc.render.resolution_x = sc.render.resolution_y = 512
up = 2 if size.z <= max(size.x, size.y) else 1                      # usd may be Y-up; pick the short axis as up
long_ax = 0 if size.x >= size.y else 1
views = {}
dirs = {"left": V((0, 0, 0)), }
fwd = V((1, 0, 0)) if long_ax == 0 else V((0, 1, 0)); side = V((0, 1, 0)) if long_ax == 0 else V((1, 0, 0)); upv = V((0, 0, 1))
for name, d in (("front", fwd), ("back", -fwd), ("left", side), ("right", -side), ("top", upv), ("bottom", -upv)):
    bpy.ops.object.camera_add(location=c + d * R); cam = bpy.context.active_object
    cam.data.type = "ORTHO"; cam.data.ortho_scale = max(size) * 1.15
    t = bpy.data.objects.new("t", None); sc.collection.objects.link(t); t.location = c
    tr = cam.constraints.new("TRACK_TO"); tr.target = t; tr.up_axis = "UP_Y" if name not in ("top", "bottom") else "UP_Y"
    if name in ("top", "bottom"): cam.location = c + d * R + fwd * 0.001
    sc.camera = cam; sc.render.filepath = os.path.join(out, f"{tag}_{name}.png"); bpy.ops.render.render(write_still=True)
