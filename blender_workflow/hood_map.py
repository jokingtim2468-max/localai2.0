"""Procedural 'projects' block: streets, brick towers, courtyard + court, parking, corner store,
street furniture. Materials and props are CC0 from Poly Haven. Each block is its own collection
and exports as its own .glb chunk (stream/cull per chunk in-game)."""
import bpy, bmesh, math, os, random, sys, mathutils
ASSETS, OUT = sys.argv[sys.argv.index("--") + 1:]
V = mathutils.Vector; rng = random.Random(7)
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene

def coll(name):
    c = bpy.data.collections.new(name); sc.collection.children.link(c); return c

def put(o, c):
    for old in list(o.users_collection): old.objects.unlink(o)
    c.objects.link(o)

def pbr(name, key, tile=1.0, tint=None):
    """Image-texture PBR material from the downloaded CC0 maps (UV based, survives glTF export)."""
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; b = nt.nodes["Principled BSDF"]
    def img(slot, non_color=False):
        p = os.path.join(ASSETS, "tex", f"{key}_{slot}.jpg")
        if not os.path.exists(p): return None
        n = nt.nodes.new("ShaderNodeTexImage"); n.image = bpy.data.images.load(p)
        if non_color: n.image.colorspace_settings.name = "Non-Color"
        return n
    d, r, nm = img("diff"), img("rough", True), img("nor", True)
    if d:
        if tint:
            mx = nt.nodes.new("ShaderNodeMix"); mx.data_type = "RGBA"; mx.blend_type = "MULTIPLY"; mx.inputs["Factor"].default_value = 1
            mx.inputs[7].default_value = (*tint, 1); nt.links.new(d.outputs["Color"], mx.inputs[6]); nt.links.new(mx.outputs[2], b.inputs["Base Color"])
        else:
            nt.links.new(d.outputs["Color"], b.inputs["Base Color"])
    if r: nt.links.new(r.outputs["Color"], b.inputs["Roughness"])
    if nm:
        nmap = nt.nodes.new("ShaderNodeNormalMap"); nt.links.new(nm.outputs["Color"], nmap.inputs["Color"]); nt.links.new(nmap.outputs["Normal"], b.inputs["Normal"])
    b.inputs["Specular IOR Level"].default_value = 0.3
    m["tile"] = tile
    return m

def flat(name, rgb, rough=0.5, metal=0.0, emit=0.0):
    m = bpy.data.materials.new(name); m.use_nodes = True; b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*rgb, 1); b.inputs["Roughness"].default_value = rough; b.inputs["Metallic"].default_value = metal
    if emit: b.inputs["Emission Color"].default_value = (*rgb, 1); b.inputs["Emission Strength"].default_value = emit
    return m

BRICK = pbr("Brick", "brick", 3.0); ROAD = pbr("Asphalt", "asph" if os.path.exists(os.path.join(ASSETS, "tex", "asph_diff.jpg")) else "road", 6.0); WALK = pbr("Sidewalk", "walk", 3.0)
GRASS = pbr("Grass", "grass", 4.0); CONC = pbr("ConcreteBlock", "concrete", 3.0); RUST = pbr("Corrugated", "rust", 2.0)
GLASS = flat("WindowGlass", (0.05, 0.06, 0.07), 0.08, 0.0); FRAME = flat("WindowFrame", (0.55, 0.55, 0.53), 0.6)
LIT = flat("LitWindow", (1.0, 0.78, 0.45), 0.4, 0, 2.0); COURT = flat("CourtConcrete", (0.16, 0.2, 0.26), 0.85)
PAINT = flat("CourtLines", (0.9, 0.9, 0.88), 0.7); STEEL = flat("Steel", (0.4, 0.4, 0.42), 0.4, 1.0)
TRIM = flat("ParapetConcrete", (0.24, 0.23, 0.22), 0.9)
TAR = flat("RoofTar", (0.07, 0.07, 0.075), 0.9)
BRICK2 = pbr("BrickB", "brick2", 3.0)

def box(name, c, loc, size, mat, uv=True):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    o = bpy.context.active_object; o.name = name; o.scale = size
    bpy.ops.object.transform_apply(scale=True)
    o.data.materials.append(mat)
    if uv:                                   # world-size cube UVs so textures keep real scale
        bpy.ops.object.mode_set(mode="EDIT"); bpy.ops.mesh.select_all(action="SELECT")
        bpy.ops.uv.cube_project(cube_size=mat.get("tile", 2.0), correct_aspect=True, scale_to_bounds=False)
        bpy.ops.object.mode_set(mode="OBJECT")
    put(o, c); return o

FLOOR_H, WIN_GAP = 3.0, 2.6

def window_row(name, c, origin, axis, count, floors, out):
    """One facade: frame + dark glass, arrayed along `axis` and up the floors (cheap: 1 object)."""
    bm = bmesh.new()
    for (sx, sy, sz, oy, mat_i) in ((1.3, 0.12, 1.6, 0.0, 0), (1.1, 0.12, 1.4, 0.03, 1)):
        geom = bmesh.ops.create_cube(bm, size=1.0)
        for v in geom["verts"]:
            v.co = V((v.co.x * sx, v.co.y * sy + oy, v.co.z * sz))
        for f in {f for v in geom["verts"] for f in v.link_faces}:
            f.material_index = mat_i
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); c.objects.link(o)
    o.data.materials.append(FRAME); o.data.materials.append(GLASS)
    o.location = origin; o.rotation_euler = (0, 0, math.atan2(out[0], -out[1]))     # local -Y faces outward
    a1 = o.modifiers.new("Across", "ARRAY"); a1.count = count; a1.use_relative_offset = False
    a1.use_constant_offset = True; a1.constant_offset_displace = (WIN_GAP, 0, 0)
    a2 = o.modifiers.new("Up", "ARRAY"); a2.count = floors; a2.use_relative_offset = False
    a2.use_constant_offset = True; a2.constant_offset_displace = (0, 0, FLOOR_H)
    return o

def tower(name, c, center, w, d, floors):
    h = floors * FLOOR_H
    box(name, c, (center[0], center[1], h / 2), (w, d, h), BRICK)
    box(name + "_Parapet", c, (center[0], center[1], h + 0.45), (w + 0.3, d + 0.3, 0.9), TRIM)
    box(name + "_Roof", c, (center[0], center[1], h + 0.05), (w - 0.2, d - 0.2, 0.2), TAR)
    for i in range(floors - 1):                                      # concrete floor bands, typical of projects
        box(f"{name}_Band{i}", c, (center[0], center[1], (i + 1) * FLOOR_H), (w + 0.12, d + 0.12, 0.22), TRIM, uv=False)
    nx, ny = int((w - 2) // WIN_GAP), int((d - 2) // WIN_GAP)
    x0 = center[0] - (nx - 1) * WIN_GAP / 2; y0 = center[1] - (ny - 1) * WIN_GAP / 2
    z0 = FLOOR_H * 0.55 + FLOOR_H                                   # ground floor has the entrance instead
    window_row(name + "_WinS", c, (x0, center[1] - d / 2 - 0.02, z0), "x", nx, floors - 1, (0, -1))
    window_row(name + "_WinN", c, (x0 + (nx - 1) * WIN_GAP, center[1] + d / 2 + 0.02, z0), "x", nx, floors - 1, (0, 1))
    window_row(name + "_WinW", c, (center[0] - w / 2 - 0.02, y0 + (ny - 1) * WIN_GAP, z0), "y", ny, floors - 1, (-1, 0))
    window_row(name + "_WinE", c, (center[0] + w / 2 + 0.02, y0, z0), "y", ny, floors - 1, (1, 0))
    for _ in range(rng.randint(6, 12)):                               # a few lights on behind windows
        f = rng.randint(1, floors - 1); k = rng.randint(0, nx - 1)
        box(f"{name}_Lit{_}", c, (x0 + k * WIN_GAP, center[1] - d / 2 - 0.055, f * FLOOR_H + FLOOR_H * 0.55), (1.08, 0.02, 1.38), LIT, uv=False)
    box(name + "_Entrance", c, (center[0], center[1] - d / 2 - 0.6, 1.6), (3.2, 1.2, 0.2), TRIM, uv=False)   # canopy
    box(name + "_Door", c, (center[0], center[1] - d / 2 - 0.03, 1.15), (1.8, 0.06, 2.3), STEEL, uv=False)
    for k in range(rng.randint(1, 3)):                                 # roof units
        box(f"{name}_RoofUnit{k}", c, (center[0] + rng.uniform(-w / 3, w / 3), center[1] + rng.uniform(-d / 4, d / 4), h + 0.8), (2.2, 1.6, 1.4), RUST)

def prop(name, c, loc, rot=0.0, scale=1.0):
    """Import a CC0 Poly Haven prop (cached per name, then linked copies)."""
    if name not in PROPS:
        before = set(bpy.data.objects)
        bpy.ops.import_scene.gltf(filepath=os.path.join(ASSETS, "props", name, f"{name}.gltf"))
        new = [o for o in bpy.data.objects if o not in before]
        holder = bpy.data.collections.new("src_" + name)
        for o in new:
            for cc in list(o.users_collection): cc.objects.unlink(o)
            holder.objects.link(o)
        PROPS[name] = holder
    inst = bpy.data.objects.new(name, None); inst.instance_type = "COLLECTION"; inst.instance_collection = PROPS[name]
    inst.location = loc; inst.rotation_euler = (0, 0, rot); inst.scale = (scale,) * 3
    c.objects.link(inst); return inst
PROPS = {}

# ---------------- layout (metres). Streets cross at the origin ----------------
HALF, ROAD_W, WALK_W = 70, 11, 3.5
streets = coll("Streets")
for axis in ("x", "y"):
    size = (HALF * 2, ROAD_W, 0.2) if axis == "x" else (ROAD_W, HALF * 2, 0.2)
    box("Road_" + axis, streets, (0, 0, -0.1), size, ROAD)
for sx in (-1, 1):
    for sy in (-1, 1):                                            # sidewalk slab under each block corner
        cx, cy = sx * (ROAD_W / 2 + (HALF - ROAD_W / 2) / 2), sy * (ROAD_W / 2 + (HALF - ROAD_W / 2) / 2)
        box(f"Sidewalk_{sx}_{sy}", streets, (cx, cy, 0.075), (HALF - ROAD_W / 2, HALF - ROAD_W / 2, 0.15), WALK)
for i in range(-3, 4):                                            # lamps + poles along the curbs
    t = i * 20
    for side in (-1, 1):
        prop("street_lamp_01", streets, (t, side * (ROAD_W / 2 + 0.8), 0.15), math.pi / 2 * (1 - side))
        prop("street_lamp_01", streets, (side * (ROAD_W / 2 + 0.8), t + 10, 0.15), math.pi / 2 * side)
    prop("modular_electricity_poles", streets, (t + 8, ROAD_W / 2 + 2.6, 0.15))
for p_ in ((ROAD_W / 2 + 1.2, ROAD_W / 2 + 1.2), (-ROAD_W / 2 - 1.2, -ROAD_W / 2 - 1.2), (30, -ROAD_W / 2 - 1.0)):
    prop("fire_hydrant", streets, (p_[0], p_[1], 0.15))

def court(c, center):
    cx, cy = center
    box("Court", c, (cx, cy, 0.17), (28, 15, 0.06), COURT, uv=False)
    for (lx, ly, sx_, sy_) in ((0, 7.4, 28, 0.08), (0, -7.4, 28, 0.08), (13.9, 0, 0.08, 15), (-13.9, 0, 0.08, 15), (0, 0, 0.08, 15)):
        box("CourtLine", c, (cx + lx, cy + ly, 0.205), (sx_, sy_, 0.01), PAINT, uv=False)
    for s in (-1, 1):
        box("HoopPole", c, (cx + s * 14.6, cy, 1.7), (0.12, 0.12, 3.4), STEEL, uv=False)
        box("Backboard", c, (cx + s * 14.2, cy, 3.3), (0.05, 1.8, 1.05), flat("Board", (0.85, 0.85, 0.85), 0.4), uv=False)
        bpy.ops.mesh.primitive_torus_add(major_radius=0.23, minor_radius=0.012, location=(cx + s * 13.9, cy, 3.05))
        rim = bpy.context.active_object; rim.data.materials.append(flat("Rim", (0.85, 0.25, 0.05), 0.4, 1.0)); put(rim, c)

def fence_line(c, a, b, step=3.0):
    a, b = V((*a, 0.15)), V((*b, 0.15)); n = max(1, int((b - a).length // step))
    ang = math.atan2((b - a).y, (b - a).x)
    for i in range(n):
        prop("modular_chainlink_fence", c, a + (b - a) * ((i + 0.5) / n), ang)

def projects(name, sx, sy, floors):
    c = coll(name)
    tower(name + "_TowerA", c, (sx * 30, sy * 22), 28, 12, floors)
    tower(name + "_TowerB", c, (sx * 54, sy * 46), 12, 26, floors - 2)
    yard = (sx * 32, sy * 50)
    box(name + "_Yard", c, (yard[0], yard[1], 0.16), (30, 30, 0.02), GRASS)
    court(c, (sx * 30, sy * 52))
    fence_line(c, (sx * 15, sy * 36), (sx * 45, sy * 36)); fence_line(c, (sx * 15, sy * 36), (sx * 15, sy * 66))
    for k in range(3):
        prop("painted_wooden_bench" if False else "metal_trash_can", c, (sx * (18 + k * 9), sy * 33, 0.15))
    prop("barrel_stove", c, (sx * 20, sy * 40, 0.15))
    for k in range(4):
        prop("trashbag", c, (sx * (44 + rng.uniform(-1, 1)), sy * (14 + rng.uniform(-1, 1)), 0.15), rng.uniform(0, 6))
    return c

projects("Projects_NE", 1, 1, 10)
projects("Projects_SW", -1, -1, 9)

park = coll("Parking_NW")
box("ParkingLot", park, (-38, 38, 0.16), (52, 52, 0.02), ROAD)
for row in range(3):
    for k in range(5):
        if rng.random() < 0.75:
            prop("covered_car", park, (-20 - k * 6.5, 22 + row * 14, 0.17), math.pi / 2 + rng.uniform(-0.06, 0.06))
    for k in range(6):
        box("ParkingLine", park, (-17 - k * 6.5, 22 + row * 14, 0.175), (0.12, 5.2, 0.01), PAINT, uv=False)
for k in range(8):
    prop("concrete_road_barrier", park, (-14 - k * 4.2, 12.5, 0.17), 0)

store = coll("CornerStore_SE")
box("Store", store, (30, -19, 3.2), (24, 14, 6.4), CONC)
box("StoreRoofTrim", store, (30, -19, 6.6), (24.4, 14.4, 0.4), TRIM, uv=False)
box("StoreRoof", store, (30, -19, 6.45), (23.8, 13.8, 0.1), TAR, uv=False)
for k in range(3):
    prop("rollershutter_door", store, (22 + k * 8, -12.05, 0.15), math.pi)
for k in range(6):
    prop(rng.choice(["wooden_crate_01", "cardboard_box_01", "trashbag"]), store, (44 + rng.uniform(-1.5, 1.5), -14 - k * 1.3, 0.15), rng.uniform(0, 6))
prop("metal_trash_can", store, (17.5, -12, 0.15)); prop("barrel_stove", store, (45, -24, 0.15))

def rowhouses(c, start, direction, count, face):
    """3-storey brick rowhouses along a street: alternating brick, stoop, windows on the street face."""
    for k in range(count):
        p = V(start) + V(direction) * (k * 9.5)
        h = rng.choice([3, 3, 4]) * FLOOR_H
        mat = BRICK if k % 2 else BRICK2
        box(f"Row_{c.name}_{k}", c, (p.x, p.y, h / 2), (9, 9, h) if True else None, mat)
        box(f"RowRoof_{c.name}_{k}", c, (p.x, p.y, h + 0.25), (9.3, 9.3, 0.5), TAR, uv=False)
        for f in range(1, int(h // FLOOR_H)):
            for j in (-2.4, 0, 2.4):
                off = V(direction) * j
                box("RowWin", c, (p.x + off.x + face[0] * 4.52, p.y + off.y + face[1] * 4.52, f * FLOOR_H + 1.5), (1.0 if face[0] == 0 else 0.06, 0.06 if face[0] == 0 else 1.0, 1.4), GLASS, uv=False)
        box("Stoop", c, (p.x + face[0] * 5.0, p.y + face[1] * 5.0, 0.35), (2.0 if face[0] == 0 else 1.0, 1.0 if face[0] == 0 else 2.0, 0.4), TRIM, uv=False)

fill = coll("Rowhouses")
rowhouses(fill, (-14, -62), (0, 1), 4, (1, 0))       # SW block, along the north-south street
rowhouses(fill, (62, -14), (0, -1), 0, (-1, 0))
rowhouses(fill, (14, -40), (1, 0), 6, (0, 1))         # SE block behind the store
rowhouses(fill, (16, 62), (1, 0), 0, (0, -1))
rowhouses(fill, (-62, 14), (0, 1), 0, (1, 0))
box("EmptyLot_SE", fill, (40, -58, 0.16), (50, 18, 0.02), GRASS)

# ---------------- light, cameras, renders ----------------
w = bpy.data.worlds.new("Sky"); sc.world = w; w.use_nodes = True
sky = w.node_tree.nodes.new("ShaderNodeTexSky"); sky.sun_elevation = math.radians(22); sky.sun_rotation = math.radians(210)
w.node_tree.links.new(sky.outputs["Color"], w.node_tree.nodes["Background"].inputs["Color"])
w.node_tree.nodes["Background"].inputs["Strength"].default_value = 1.3
bpy.ops.object.light_add(type="SUN", rotation=(math.radians(68), 0, math.radians(210)))
sun = bpy.context.active_object; sun.data.energy = 2.2; sun.data.color = (1.0, 0.86, 0.7); sun.data.angle = math.radians(1.5)
sc.render.engine = "BLENDER_EEVEE_NEXT"; sc.eevee.taa_render_samples = 32
sc.view_settings.look = "AgX - Medium High Contrast" if "AgX - Medium High Contrast" in [l for l in bpy.types.ColorManagedViewSettings.bl_rna.properties["look"].enum_items.keys()] else sc.view_settings.look
shots = {"aerial": ((95, -95, 75), (5, 5, 0), 30), "street": ((-4, -60, 1.7), (2, 10, 6), 24),
         "courtyard": ((10, 30, 1.7), (40, 52, 3), 22), "parking": ((-6, 10, 1.7), (-35, 35, 1), 24)}
only = os.environ.get("SHOTS")
for name, (loc, aim, lens) in shots.items():
    if only and name not in only.split(","): continue
    bpy.ops.object.camera_add(location=loc); cam = bpy.context.active_object; cam.data.lens = lens; cam.data.clip_end = 600
    t = bpy.data.objects.new("Aim_" + name, None); sc.collection.objects.link(t); t.location = aim
    cam.constraints.new("TRACK_TO").target = t; sc.camera = cam
    sc.render.resolution_x, sc.render.resolution_y = 1280, 720
    sc.render.filepath = os.path.join(OUT, f"map_{name}.png"); bpy.ops.render.render(write_still=True)

# ---------------- export: one .glb per chunk, instances made real ----------------
if not os.environ.get("NOEXPORT"):
    for c in [c for c in sc.collection.children]:
        bpy.ops.object.select_all(action="DESELECT")
        for o in [o for o in c.objects if o.instance_type == "COLLECTION"]:
            o.select_set(True)
        if bpy.context.selected_objects:
            bpy.context.view_layer.objects.active = bpy.context.selected_objects[0]
            bpy.ops.object.duplicates_make_real(use_base_parent=False, use_hierarchy=False)
            for o in [o for o in c.objects if o.instance_type == "COLLECTION"]:
                bpy.data.objects.remove(o)
        bpy.ops.object.select_all(action="DESELECT")
        for o in c.all_objects:
            o.select_set(True)
        bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, f"chunk_{c.name}.glb"), export_format="GLB",
                                  use_selection=True, export_apply=True)
        print("CHUNK", c.name, len(c.all_objects))
