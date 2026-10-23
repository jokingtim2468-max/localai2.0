import bpy, sys, os, math, mathutils
src, OUT = sys.argv[sys.argv.index("--") + 1:]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=src)
obj = {o.name: o for o in bpy.context.scene.objects if o.type == "MESH"}

def textured(name, rgb, metal, rough, var, bump, scale):
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; b = nt.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*rgb, 1); b.inputs["Metallic"].default_value = metal
    tc = nt.nodes.new("ShaderNodeTexCoord"); nz = nt.nodes.new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = scale; nz.inputs["Detail"].default_value = 8
    nt.links.new(tc.outputs["Object"], nz.inputs["Vector"])
    mr = nt.nodes.new("ShaderNodeMapRange"); mr.inputs["To Min"].default_value = rough - var; mr.inputs["To Max"].default_value = rough + var
    nt.links.new(nz.outputs["Fac"], mr.inputs["Value"]); nt.links.new(mr.outputs["Result"], b.inputs["Roughness"])
    bm = nt.nodes.new("ShaderNodeBump"); bm.inputs["Strength"].default_value = bump; bm.inputs["Distance"].default_value = 0.0005
    nt.links.new(nz.outputs["Fac"], bm.inputs["Height"]); nt.links.new(bm.outputs["Normal"], b.inputs["Normal"])
    return m

def swap(o, m):
    o.data.materials.clear(); o.data.materials.append(m)

for m in bpy.data.materials:              # inside faces of the low-poly mesh showed as white shards
    m.blend_method = "OPAQUE"
    if m.use_nodes and "Principled BSDF" in m.node_tree.nodes:
        a = m.node_tree.nodes["Principled BSDF"].inputs["Alpha"]
        for l in list(a.links): m.node_tree.links.remove(l)
        a.default_value = 1.0
def outward(o):                          # sleeve faces pointed inward -> lit from behind = grey
    bpy.context.view_layer.objects.active = o; o.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT"); bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.normals_make_consistent(inside=False); bpy.ops.object.mode_set(mode="OBJECT"); o.select_set(False)
def clamp_texture(m, top=0.22):          # bright padding pixels in the baked maps = white shards
    nt = m.node_tree; b = nt.nodes["Principled BSDF"]; link = b.inputs["Base Color"].links
    if not link: return
    src = link[0].from_socket; mx = nt.nodes.new("ShaderNodeMix"); mx.data_type = "RGBA"; mx.blend_type = "DARKEN"
    mx.inputs["Factor"].default_value = 1.0; mx.inputs[7].default_value = (top, top, top, 1)
    nt.links.new(src, mx.inputs[6]); nt.links.new(mx.outputs[2], b.inputs["Base Color"])
def matte(m, spec=0.08, rough=0.85):       # rubber / polymer: weak, wide reflections
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Specular IOR Level"].default_value = spec
    for l in list(b.inputs["Roughness"].links): m.node_tree.links.remove(l)
    for l in list(b.inputs["Metallic"].links): m.node_tree.links.remove(l)
    b.inputs["Roughness"].default_value = rough; b.inputs["Metallic"].default_value = 0.0
for name in ("Object_10", "Object_14"):
    matte(obj[name].material_slots[0].material, 0.15, 0.75)
for name in ("Object_10", "Object_14"):
    clamp_texture(obj[name].material_slots[0].material)
m6 = textured("GripSleeve", (0.012, 0.012, 0.013), 0.0, 0.62, 0.06, 0.04, 150); matte(m6, 0.05, 0.9); swap(obj["Object_6"], m6)   # was crest + camo
swap(obj["Object_8"], textured("SlideNitride", (0.02, 0.02, 0.023), 0.8, 0.4, 0.05, 0.03, 400))  # was camo
for n in obj["Object_12"].material_slots[0].material.node_tree.nodes:                              # was a real logo
    if n.type == "TEX_IMAGE":
        n.image = bpy.data.images.load(os.path.join(OUT, "nocta_logo.png"))

ENGRAVE = bpy.data.materials.new("Engraving"); ENGRAVE.use_nodes = True
eb = ENGRAVE.node_tree.nodes["Principled BSDF"]; eb.inputs["Base Color"].default_value = (0.5, 0.5, 0.52, 1)
eb.inputs["Metallic"].default_value = 0.7; eb.inputs["Roughness"].default_value = 0.5

def engrave(body, y, z, size, x=0.0995, side=-1):
    rot = (math.radians(90), 0, math.radians(-90 if side < 0 else 90))
    bpy.ops.object.text_add(location=(x, y, z), rotation=rot)
    t = bpy.context.active_object; t.data.body = body; t.data.size = size; t.data.extrude = 0.002
    t.data.align_x = t.data.align_y = "CENTER"; t.data.materials.append(ENGRAVE)
    bpy.ops.object.convert(target="MESH")


sc = bpy.context.scene
ms = [o for o in sc.objects if o.type == "MESH"]
pts = [o.matrix_world @ mathutils.Vector(c) for o in ms for c in o.bound_box]
lo = mathutils.Vector([min(p[i] for p in pts) for i in range(3)]); hi = mathutils.Vector([max(p[i] for p in pts) for i in range(3)])
mid, L = (lo + hi) / 2, max(hi - lo)
w = bpy.data.worlds.new("W"); sc.world = w; w.use_nodes = True
w.node_tree.nodes["Background"].inputs[0].default_value = (0.045, 0.045, 0.05, 1)
t = bpy.data.objects.new("T", None); sc.collection.objects.link(t); t.location = mid
for off, e in (((-1, -0.6, 1), 2.5), ((-0.8, 1, 0.4), 1.2), ((1, 0, 0.5), 0.8)):
    bpy.ops.object.light_add(type="AREA", location=mid + mathutils.Vector(off) * L * 1.4)
    l = bpy.context.active_object; l.data.energy = e * 60 * L ** 2; l.data.size = L * 1.2
    l.constraints.new("TRACK_TO").target = t
sc.render.engine = "BLENDER_EEVEE_NEXT"; sc.render.resolution_x, sc.render.resolution_y = 1100, 800
for name, d in (("side", (-1, 0, 0.05)), ("three_quarter", (-0.8, 0.55, 0.35)), ("rear", (-0.7, -0.75, 0.3))):
    bpy.ops.object.camera_add(location=mid + mathutils.Vector(d).normalized() * L * 2.1)
    cam = bpy.context.active_object; cam.constraints.new("TRACK_TO").target = t; sc.camera = cam
    sc.render.filepath = os.path.join(OUT, f"blank_{name}.png"); bpy.ops.render.render(write_still=True)

# game export: real size (~19 cm long), credits kept in the file
for o in [o for o in sc.objects if o.type in ("CAMERA", "LIGHT", "EMPTY")]:
    bpy.data.objects.remove(o)
# flatten the Sketchfab node tree first (scaling only the roots pulled the parts apart)
meshes = [o for o in sc.objects if o.type == "MESH"]
for o in meshes:
    mw = o.matrix_world.copy(); o.parent = None; o.matrix_world = mw
for o in [o for o in sc.objects if o.type == "EMPTY"]:
    bpy.data.objects.remove(o)
s = 0.19 / L
for o in meshes:
    o.matrix_world = mathutils.Matrix.Translation(-mid * s) @ mathutils.Matrix.Scale(s, 4) @ o.matrix_world
bpy.ops.object.select_all(action="DESELECT")
for o in meshes: o.select_set(True)
bpy.context.view_layer.objects.active = meshes[0]
bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
sc["credits"] = "Base model: 'Glock 9mm Flamengo' by Japonês (sketchfab.com/Japones_), CC-BY-4.0. Modified: all logos and branding removed, new finishes."
bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, "pistol_drum_blank.glb"), export_format="GLB", export_extras=True)
