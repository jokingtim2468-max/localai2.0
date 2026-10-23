import bpy, sys, mathutils
src = sys.argv[sys.argv.index("--") + 1]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=src)
for o in bpy.context.scene.objects:
    if o.type != "MESH":
        continue
    pts = [o.matrix_world @ mathutils.Vector(c) for c in o.bound_box]
    lo = [round(min(p[i] for p in pts), 3) for i in range(3)]; hi = [round(max(p[i] for p in pts), 3) for i in range(3)]
    mats = []
    for s in o.material_slots:
        m = s.material; tex = [n.image.name + f" {n.image.size[0]}x{n.image.size[1]}" for n in m.node_tree.nodes if n.type == "TEX_IMAGE" and n.image] if m and m.use_nodes else []
        mats.append(f"{m.name if m else None}:{tex}")
    print("OBJ", o.name, len(o.data.polygons), "faces", lo, hi, mats)
