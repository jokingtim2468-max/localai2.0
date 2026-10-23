import bpy, sys, os, math, mathutils, bmesh
body, bandana, OUT = sys.argv[sys.argv.index("--") + 1:]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=body)
sc = bpy.context.scene
for o in [o for o in sc.objects if o.name.startswith("Icosphere")]:      # stray helper sphere
    bpy.data.objects.remove(o)
obj = {o.data.materials[0].name: o for o in sc.objects if o.type == "MESH" and o.data.materials}

def bsdf(m):
    return m.node_tree.nodes["Principled BSDF"]

# 1) dark skin: tint the face texture (keeps its shading and detail)
face = obj["ted_facemap"].data.materials[0]; nt = face.node_tree; b = bsdf(face)
src = b.inputs["Base Color"].links[0].from_socket
hsv = nt.nodes.new("ShaderNodeHueSaturation")
hsv.inputs["Saturation"].default_value = 1.15; hsv.inputs["Value"].default_value = 0.2
mul = nt.nodes.new("ShaderNodeMix"); mul.data_type = "RGBA"; mul.blend_type = "MULTIPLY"
mul.inputs["Factor"].default_value = 1.0; mul.inputs[7].default_value = (0.42, 0.26, 0.18, 1)
nt.links.new(src, hsv.inputs["Color"]); nt.links.new(hsv.outputs["Color"], mul.inputs[6]); nt.links.new(mul.outputs[2], b.inputs["Base Color"]); b.inputs["Specular IOR Level"].default_value = 0.25; b.inputs["Roughness"].default_value = 0.6; hsv.inputs["Saturation"].default_value = 0.8

# 2) black gloves: the hands become matte black fabric/leather
g = bpy.data.materials.new("BlackGloves"); g.use_nodes = True; gb = bsdf(g)
gb.inputs["Base Color"].default_value = (0.012, 0.012, 0.013, 1); gb.inputs["Roughness"].default_value = 0.6
gb.inputs["Specular IOR Level"].default_value = 0.15; gb.inputs["Roughness"].default_value = 0.75
nz = g.node_tree.nodes.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 900
bump = g.node_tree.nodes.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = 0.08
g.node_tree.links.new(nz.outputs["Fac"], bump.inputs["Height"]); g.node_tree.links.new(bump.outputs["Normal"], gb.inputs["Normal"])
hands = obj["hands_w"]; hands.data.materials.clear(); hands.data.materials.append(g)

def add_bandana():
    """Cloth ring from the nose to the neck, shrink-wrapped onto the face at low detail so it
    drapes over the lips instead of tracing them; dressed in the bandana model's paisley fabric."""
    bpy.ops.import_scene.gltf(filepath=bandana)
    bmat = next(m for m in bpy.data.materials if m.name.startswith("Material_003"))
    for o in [o for o in sc.objects if o.type == "MESH" and bmat.name in [m.name for m in o.data.materials]]:
        bpy.data.objects.remove(o)
    for o in [o for o in sc.objects if o.name.startswith("Icosphere")]:
        bpy.data.objects.remove(o)
    head = obj["ted_facemap"]
    NOSE, NECK = float(os.environ.get("NOSE", 1.262)), float(os.environ.get("NECK", 1.135))
    pts = [head.matrix_world @ mathutils.Vector(c) for c in head.bound_box]
    cx = sum(p.x for p in pts) / 8; cy = sum(p.y for p in pts) / 8
    bpy.ops.mesh.primitive_cylinder_add(vertices=28, radius=0.11, depth=NOSE - NECK, end_fill_type="NOTHING",
                                        location=(cx, cy, (NOSE + NECK) / 2))
    mask = bpy.context.active_object; mask.name = "BandanaMask"
    bm = bmesh.new(); bm.from_mesh(mask.data)
    vertical = [e for e in bm.edges if abs(e.verts[0].co.z - e.verts[1].co.z) > 1e-4]
    bmesh.ops.subdivide_edges(bm, edges=vertical, cuts=5, use_grid_fill=True)
    bm.to_mesh(mask.data); bm.free()
    sw = mask.modifiers.new("Wrap", "SHRINKWRAP"); sw.target = head; sw.wrap_method = "NEAREST_SURFACEPOINT"
    sw.wrap_mode = "ON_SURFACE"; sw.offset = 0.008
    cs = mask.modifiers.new("Relax", "CORRECTIVE_SMOOTH"); cs.factor = 0.6; cs.iterations = 6
    sol = mask.modifiers.new("Thickness", "SOLIDIFY"); sol.thickness = 0.0015; sol.offset = 1
    sub = mask.modifiers.new("Smooth", "SUBSURF"); sub.levels = 1; sub.render_levels = 2
    mask.data.polygons.foreach_set("use_smooth", [True] * len(mask.data.polygons))
    nt = bmat.node_tree; pb = nt.nodes["Principled BSDF"]
    for name in ("Metallic", "Roughness", "Normal"):                # cotton: no metal, no old bump map
        for l in list(pb.inputs[name].links): nt.links.remove(l)
    pb.inputs["Metallic"].default_value = 0.0; pb.inputs["Roughness"].default_value = 0.85
    pb.inputs["Specular IOR Level"].default_value = 0.2
    col = pb.inputs["Base Color"].links[0].from_node
    col.image = bpy.data.images.load(os.path.join(OUT, "paisley_tile.png"))
    for l in list(col.inputs["Vector"].links): nt.links.remove(l)
    map_ = nt.nodes.new("ShaderNodeMapping"); map_.inputs["Scale"].default_value = (4.5, 0.95, 1)
    uvn = nt.nodes.new("ShaderNodeUVMap")
    nt.links.new(uvn.outputs["UV"], map_.inputs["Vector"]); nt.links.new(map_.outputs["Vector"], col.inputs["Vector"])
    bmat.blend_method = "OPAQUE"
    mask.data.materials.append(bmat)
    arm = next((o for o in sc.objects if o.type == "ARMATURE"), None)
    bone = next((b.name for b in arm.data.bones if "head" in b.name.lower()), None) if arm else None
    if bone:
        mw = mask.matrix_world.copy(); mask.parent = arm; mask.parent_type = "BONE"; mask.parent_bone = bone; mask.matrix_world = mw
    obj["mouth"].hide_render = True

def add_balaclava():
    """Fit the balaclava model to this head and pin it to the head bone."""
    before = set(sc.objects)
    bpy.ops.import_scene.gltf(filepath=os.environ["BALACLAVA"])
    new = [o for o in sc.objects if o not in before]
    for o in [o for o in new if o.name.startswith("Icosphere")]:
        bpy.data.objects.remove(o)
    parts = [o for o in sc.objects if o not in before and o.type == "MESH"]
    for o in parts:
        for m in list(o.modifiers):                 # its own rig would bend it back to where it came from
            o.modifiers.remove(m)
        mw = o.matrix_world.copy(); o.parent = None; o.matrix_world = mw
    for o in [o for o in sc.objects if o not in before and o.type == "ARMATURE"]:
        bpy.data.objects.remove(o)
    for o in [o for o in sc.objects if o not in before and o.type == "EMPTY"]:
        bpy.data.objects.remove(o)
    def box(objs):
        pts = [o.matrix_world @ mathutils.Vector(c) for o in objs for c in o.bound_box]
        lo = mathutils.Vector([min(p[i] for p in pts) for i in range(3)]); hi = mathutils.Vector([max(p[i] for p in pts) for i in range(3)])
        return lo, hi
    hl, hh = box([obj["ted_facemap"]]); bl, bh = box(parts)
    # classic plain black balaclava: matte stretch knit, no logo, no coloured trim
    knit = bpy.data.materials.new("BalaclavaKnit"); knit.use_nodes = True; kb = bsdf(knit)
    kb.inputs["Base Color"].default_value = (0.004, 0.004, 0.0045, 1); kb.inputs["Roughness"].default_value = 0.9
    kb.inputs["Specular IOR Level"].default_value = 0.12
    kb.inputs["Sheen Weight"].default_value = 0.06; kb.inputs["Sheen Tint"].default_value = (0.3, 0.3, 0.32, 1)
    kn = knit.node_tree.nodes.new("ShaderNodeTexNoise"); kn.inputs["Scale"].default_value = 1500
    kbu = knit.node_tree.nodes.new("ShaderNodeBump"); kbu.inputs["Strength"].default_value = 0.05
    knit.node_tree.links.new(kn.outputs["Fac"], kbu.inputs["Height"]); knit.node_tree.links.new(kbu.outputs["Normal"], kb.inputs["Normal"])
    pad = mathutils.Vector(tuple(float(x) for x in os.environ.get("PAD", "1.1,1.08,1.04").split(",")))          # a knitted layer sits a little off the skin
    scale = mathutils.Vector([(hh[i] - hl[i]) * pad[i] / (bh[i] - bl[i]) for i in range(3)])
    hc, bc = (hl + hh) / 2, (bl + bh) / 2
    hc.z += (hh.z - hl.z) * 0.02
    for o in parts:
        o.matrix_world = (mathutils.Matrix.Translation(hc) @ mathutils.Matrix.Diagonal((*scale, 1))
                          @ mathutils.Matrix.Translation(-bc) @ o.matrix_world)
        o.data.materials.clear(); o.data.materials.append(knit)
        for m in []:
            m.blend_method = "OPAQUE"
            b = m.node_tree.nodes.get("Principled BSDF")
            if b:
                for l in list(b.inputs["Alpha"].links): m.node_tree.links.remove(l)
                b.inputs["Alpha"].default_value = 1.0
    # keep the sides and back inside the hood: taper the width from the face (full) to the back (narrower)
    side_k = float(os.environ.get("SIDE_TAPER", "0.16"))
    bpy.context.view_layer.update()
    for o in parts:
        mw = o.matrix_world; mi = mw.inverted()
        P = [mw @ v.co for v in o.data.vertices]
        fy, by = min(p.y for p in P), max(p.y for p in P)
        for v, p in zip(o.data.vertices, P):
            t = min(1.0, max(0.0, (p.y - fy - 0.06) / ((by - fy) * 0.4)))
            v.co = mi @ mathutils.Vector((hc.x + (p.x - hc.x) * (1 - side_k * t), p.y - (p.y - hc.y) * side_k * 0.5 * t if p.y > hc.y else p.y, p.z))
    # eye opening: only from just under the brows to just over the nose bridge
    up_f, down_f = float(os.environ.get("HOLE_UP", "0.2")), float(os.environ.get("HOLE_DOWN", "0.06"))
    for o in parts:
        bpy.context.view_layer.update()
        bm = bmesh.new(); bm.from_mesh(o.data); bm.verts.ensure_lookup_table()
        mw = o.matrix_world; mi = mw.inverted()
        wpos = {v.index: mw @ v.co for v in bm.verts}
        front_y = min(p.y for p in wpos.values())
        rim = [v for v in bm.verts if v.is_boundary and wpos[v.index].y < front_y + 0.06 and wpos[v.index].z > hl.z + (hh.z - hl.z) * 0.35]
        if not rim: bm.free(); continue
        zs = [wpos[v.index].z for v in rim]; lo_z, hi_z = min(zs), max(zs); H = hi_z - lo_z; mid = (lo_z + hi_z) / 2
        print("EYEHOLE rim", len(rim), "height", round(H, 4))
        for v in bm.verts:
            p = wpos[v.index]
            if p.y > front_y + 0.08: continue
            d = min((p - wpos[r.index]).length for r in rim)
            fall = max(0.0, 1 - d / (H * 0.9))
            if fall <= 0: continue
            t = min(1.0, max(0.0, (p.z - lo_z) / H))                 # smooth blend: bottom lifts, top drops, sides in between
            dz = (H * up_f * (1 - t) - H * down_f * t) * fall
            v.co = mi @ (p + mathutils.Vector((0, 0, dz)))
        xs = [wpos[r.index].x for r in rim]
        bm.to_mesh(o.data); bm.free()
        band = (lo_z + H * up_f - 0.012, hi_z - H * down_f + 0.012, front_y, min(xs) + 0.006, max(xs) - 0.006)
    # skin under the mask can never be seen: drop it so the cheeks can't poke through the knit
    fo = obj["ted_facemap"]; bm = bmesh.new(); bm.from_mesh(fo.data); fmw = fo.matrix_world
    kill = [v for v in bm.verts if not (band[0] < (fmw @ v.co).z < band[1] and (fmw @ v.co).y < band[2] + 0.06 and band[3] < (fmw @ v.co).x < band[4])]
    bmesh.ops.delete(bm, geom=kill, context="VERTS"); bm.to_mesh(fo.data); bm.free()
    print("FACE kept band", [round(x, 3) for x in band])
    arm = next((o for o in sc.objects if o.type == "ARMATURE"), None)
    bone = next((b.name for b in arm.data.bones if "head" in b.name.lower()), None) if arm else None
    for o in parts:
        if bone:
            mw = o.matrix_world.copy(); o.parent = arm; o.parent_type = "BONE"; o.parent_bone = bone; o.matrix_world = mw
    obj["mouth"].hide_render = True
    print("BALACLAVA fitted, bone:", bone)

MASK = os.environ.get("MASK", "bandana")
add_bandana() if MASK == "bandana" else add_balaclava()

# hoodie: plain, the printed tree graphic and text removed
hood = obj["ancestor"].data.materials[0]; hb = bsdf(hood)
for l in list(hb.inputs["Base Color"].links): hood.node_tree.links.remove(l)
hb.inputs["Base Color"].default_value = (0.62, 0.63, 0.64, 1); hb.inputs["Specular IOR Level"].default_value = 0.2

# black sweatpants: printed swoosh dropped, matte cotton fleece
pm = obj["pants_6"].data.materials[0]; pb = bsdf(pm)
for l in list(pb.inputs["Base Color"].links): pm.node_tree.links.remove(l)
pb.inputs["Base Color"].default_value = (0.012, 0.012, 0.013, 1); pb.inputs["Roughness"].default_value = 0.95
pb.inputs["Sheen Weight"].default_value = 0.15; pb.inputs["Sheen Tint"].default_value = (0.35, 0.35, 0.37, 1)
pb.inputs["Specular IOR Level"].default_value = 0.15

# shoes: plain black leather (the original texture had a brand swoosh)
sh = bpy.data.materials.new("Leather"); sh.use_nodes = True; shb = sh.node_tree.nodes["Principled BSDF"]
shb.inputs["Base Color"].default_value = (0.015, 0.015, 0.016, 1); shb.inputs["Roughness"].default_value = 0.45
shb.inputs["Specular IOR Level"].default_value = 0.35
shoes = obj["bbshoes_6"]; shoes.data.materials.clear(); shoes.data.materials.append(sh)

# portrait: three-quarter, head and shoulders + a full body shot
w = bpy.data.worlds.new("W"); sc.world = w; w.use_nodes = True
w.node_tree.nodes["Background"].inputs[0].default_value = (0.06, 0.06, 0.07, 1)
for loc, e in (((1.2, -1.6, 2.2), 260), ((-1.6, -0.6, 1.6), 90), ((0.2, 1.8, 2.0), 140)):
    bpy.ops.object.light_add(type="AREA", location=loc); L = bpy.context.active_object
    L.data.energy, L.data.size = e, 1.2
    t = bpy.data.objects.new("T", None); sc.collection.objects.link(t); t.location = (0, 0, 1.1)
    L.constraints.new("TRACK_TO").target = t
sc.render.engine = "BLENDER_EEVEE_NEXT"
for name, cam_loc, aim, lens, res in (("face", (0.35, -0.75, 1.3), (0, 0, 1.24), 60, (900, 900)),
                                       ("body", (1.3, -3.2, 1.25), (0, 0, 0.8), 50, (900, 1200))):
    bpy.ops.object.camera_add(location=cam_loc); cam = bpy.context.active_object; cam.data.lens = lens
    t = bpy.data.objects.new("A", None); sc.collection.objects.link(t); t.location = aim
    cam.constraints.new("TRACK_TO").target = t; sc.camera = cam
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.filepath = os.path.join(OUT, f"char_{MASK}_{name}.png"); bpy.ops.render.render(write_still=True)

# game export: rigged character with the mask attached to the head bone
for o in [o for o in sc.objects if o.type in ("CAMERA", "LIGHT", "EMPTY") and not o.children]:
    bpy.data.objects.remove(o)
sc["credits"] = ("Character: 'i met my wife hood' by photon (that one larry), CC-BY-4.0. "
                 "Bandana: 'Bandana Mask' by Tactical_Gamer, CC-BY-4.0. Balaclava: 'balaclava' by local.yany, CC-BY-4.0. "
                 "Modified: skin tone, gloves, shoes, mask fitting.")
bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, f"character_{MASK}.glb"), export_format="GLB", export_extras=True)
