import bpy, sys, os, mathutils
src, out = sys.argv[sys.argv.index("--") + 1:]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=src)
sc = bpy.context.scene
ms = [o for o in sc.objects if o.type == "MESH"]
pts = [o.matrix_world @ mathutils.Vector(c) for o in ms for c in o.bound_box]
lo = mathutils.Vector([min(p[i] for p in pts) for i in range(3)]); hi = mathutils.Vector([max(p[i] for p in pts) for i in range(3)])
mid, size = (lo + hi) / 2, (hi - lo)
print("SIZE", [round(v, 3) for v in size])
w = bpy.data.worlds.new("W"); sc.world = w; w.use_nodes = True
w.node_tree.nodes["Background"].inputs[0].default_value = (0.08, 0.08, 0.09, 1)
t = bpy.data.objects.new("T", None); sc.collection.objects.link(t); t.location = mid
L = max(size)
long_ax = max(range(3), key=lambda i: size[i])
side = [0, 0, 0]; side[(long_ax + 1) % 3 if long_ax != 2 else 0] = -1
for d in ((side, 1.0, 1.6),):
    pass
cam_dir = mathutils.Vector(side) + mathutils.Vector((0.25, 0, 0.25))
bpy.ops.object.camera_add(location=mid + cam_dir.normalized() * L * 1.9); cam = bpy.context.active_object
cam.constraints.new("TRACK_TO").target = t; sc.camera = cam
for off, e in (((1, -1, 1), 2.5), ((-1, 1, 0.6), 1.2)):
    bpy.ops.object.light_add(type="AREA", location=mid + mathutils.Vector(off) * L * 1.5)
    l = bpy.context.active_object; l.data.energy = e * (L * 10) ** 2; l.data.size = L
    l.constraints.new("TRACK_TO").target = t
sc.render.engine = "BLENDER_EEVEE_NEXT"; sc.render.resolution_x, sc.render.resolution_y = 800, 520
sc.render.filepath = out; bpy.ops.render.render(write_still=True)
