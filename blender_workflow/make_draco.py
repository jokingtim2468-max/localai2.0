"""AK pistol ("Draco"-style) from the M762 model: drop the stock behind the pistol grip, cut the long handguard
so the gun is ~0.52 m overall (Draco: 20.5 in OAL, 12.25 in barrel). Model units are metres; muzzle is -Y,
height is +X (down), width is Z."""
import bpy, bmesh, sys, os, mathutils
src, out_dir = sys.argv[sys.argv.index("--") + 1:]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=src); sc = bpy.context.scene
CUT_A, CUT_B = float(os.environ.get("CUT_A", "-0.53")), float(os.environ.get("CUT_B", "-0.29"))
SHIFT = CUT_B - CUT_A

def rear_limit(x):                     # slanted line just behind the pistol grip
    row = 250 + 1220 * x
    return (955 + 0.46 * max(0.0, row - 200) - 700) / 1220 - 0.18

for o in [o for o in sc.objects if o.type == "MESH"]:
    mw = o.matrix_world; mi = mw.inverted()
    bm = bmesh.new(); bm.from_mesh(o.data)
    kill = []
    for v in bm.verts:
        p = mw @ v.co
        row, px = 250 + 1220 * p.x, 700 + (p.y + 0.18) * 1220
        if p.y > rear_limit(p.x) or CUT_A < p.y < CUT_B or (row > 185 and px > 868) or (row > 140 and px > 925):
            kill.append(v)
        elif p.y <= CUT_A:
            v.co = mi @ (p + mathutils.Vector((0, SHIFT, 0)))
    bmesh.ops.delete(bm, geom=kill, context="VERTS")
    bm.to_mesh(o.data); bm.free()
    if not o.data.vertices: bpy.data.objects.remove(o)
# new AK pistol grip (the M762's grip was part of its stock): tapered, raked back ~18 deg, black polymer
import math
def M(px, row):  # image coords -> model (y, x)
    return (px - 700) / 1220 - 0.18, (row - 250) / 1220
top_y, top_x = M(888, 170)
bm = bmesh.new()
L, raked = 0.1, math.radians(20)
sec = [(0.0, 0.044, 0.03), (1.0, 0.036, 0.027)]         # along length: depth (y), width (z)
for t, d, w in sec:
    cy = top_y + math.sin(raked) * L * t; cx = top_x + math.cos(raked) * L * t
    for sy, sz in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
        bm.verts.new((cx, cy + sy * d / 2, sz * w / 2))
bm.verts.ensure_lookup_table(); vv = bm.verts
for f in ((0, 1, 2, 3), (7, 6, 5, 4), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)):
    bm.faces.new([vv[i] for i in f])
me = bpy.data.meshes.new("Grip"); bm.to_mesh(me); bm.free()
g = bpy.data.objects.new("AK_Grip", me); sc.collection.objects.link(g)
bev = g.modifiers.new("b", "BEVEL"); bev.width = 0.004; bev.segments = 3
gm = bpy.data.materials.new("GripPolymer"); gm.use_nodes = True; gb = gm.node_tree.nodes["Principled BSDF"]
gb.inputs["Base Color"].default_value = (0.02, 0.02, 0.02, 1); gb.inputs["Roughness"].default_value = 0.7; gb.inputs["Specular IOR Level"].default_value = 0.2
me.materials.append(gm)
bpy.context.view_layer.objects.active = g; g.select_set(True); bpy.ops.object.modifier_apply(modifier="b")
P = [o.matrix_world @ v.co for o in sc.objects if o.type == "MESH" for v in o.data.vertices]
L = max(p.y for p in P) - min(p.y for p in P)
print("DRACO length m", round(L, 3))
sc["credits"] = "Base: 'M762 Assault Rifle' by STALKER (CC-BY-4.0), cut down to an AK pistol shape."
bpy.ops.export_scene.gltf(filepath=os.path.join(out_dir, "draco.glb"), export_format="GLB", export_extras=True)
