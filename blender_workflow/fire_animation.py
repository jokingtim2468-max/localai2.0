import bpy, sys, math, mathutils, os
src, OUT = sys.argv[sys.argv.index("--") + 1:]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=src)
sc = bpy.context.scene
parts = [o for o in sc.objects if o.type == "MESH"]
for m in bpy.data.materials:                     # keep the glTF materials opaque
    m.blend_method = "OPAQUE"

# rig: everything under one pivot at the grip so recoil rotates the whole gun
rig = bpy.data.objects.new("Rig", None); sc.collection.objects.link(rig)
rig.location = (0, -0.03, 0.02)
for o in parts:
    mw = o.matrix_world.copy(); o.parent = rig; o.matrix_world = mw
slide = [o for o in parts if o.name in ("Object_8", "Object_12") or o.name.startswith("Text")]
MUZZLE = mathutils.Vector((0.002, 0.07, 0.064))
rig.location = (0, -0.03, 1.2); rig.rotation_euler = (0, 0, 0)

def emit(name, rgb, strength, alpha=1.0):
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree
    for n in list(nt.nodes): nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial"); e = nt.nodes.new("ShaderNodeEmission")
    e.inputs["Color"].default_value = (*rgb, 1); e.inputs["Strength"].default_value = strength
    if alpha < 1:
        t = nt.nodes.new("ShaderNodeBsdfTransparent"); mix = nt.nodes.new("ShaderNodeMixShader")
        mix.inputs["Fac"].default_value = alpha
        nt.links.new(t.outputs[0], mix.inputs[1]); nt.links.new(e.outputs[0], mix.inputs[2])
        nt.links.new(mix.outputs[0], out.inputs[0]); m.blend_method = "BLEND"; m.surface_render_method = "BLENDED"
    else:
        nt.links.new(e.outputs[0], out.inputs[0])
    return m

# baseplate: grey studded-grid floor like a game baseplate
bpy.ops.mesh.primitive_plane_add(size=40, location=(0, 0, 0))
bp = bpy.context.active_object
m = bpy.data.materials.new("Baseplate"); m.use_nodes = True; nt = m.node_tree; b = nt.nodes["Principled BSDF"]
tc = nt.nodes.new("ShaderNodeTexCoord"); ck = nt.nodes.new("ShaderNodeTexChecker")
ck.inputs["Scale"].default_value = 40; ck.inputs["Color1"].default_value = (0.32, 0.32, 0.33, 1); ck.inputs["Color2"].default_value = (0.27, 0.27, 0.28, 1)
nt.links.new(tc.outputs["UV"], ck.inputs["Vector"]); nt.links.new(ck.outputs["Color"], b.inputs["Base Color"])
b.inputs["Roughness"].default_value = 0.8; bp.data.materials.append(m)

import random
rng = random.Random(19)
FPS, START, END = 60, 1, 170
sc.render.fps = FPS; sc.frame_start, sc.frame_end = START, END
SHOTS = list(range(20, 20 + 3 * 22, 3))           # 22 rounds, one every 3 frames at 60 fps (~1,200/min)
pivot0 = mathutils.Vector((0, -0.03, 0.02))
local_muzzle = MUZZLE - pivot0
local_port = mathutils.Vector((0.016, 0.035, 0.07)) - pivot0     # ejection port, right side of the slide

def key(obj, path, frame, value, interp=None):
    setattr(obj, path, value); obj.keyframe_insert(path, frame=frame)
    if interp and obj.animation_data and obj.animation_data.action:
        for fc in obj.animation_data.action.fcurves:
            if fc.data_path == path:
                for kp in fc.keyframe_points:
                    if int(kp.co.x) == frame: kp.interpolation = interp

# ---- recoil: snap up + back on each shot, climb that builds over the burst, sideways drift ----
base_loc = rig.location.copy()
key(rig, "location", START, base_loc); key(rig, "rotation_euler", START, (0, 0, 0))
climb, drift = 0.0, 0.0
for i, f in enumerate(SHOTS):
    climb = min(climb + math.radians(0.45), math.radians(6))          # muzzle rise accumulates
    drift = max(-0.05, min(0.05, drift + math.radians(rng.uniform(-0.5, 0.5))))
    kick = math.radians(rng.uniform(2.5, 3.6))
    key(rig, "rotation_euler", f, (climb, 0, drift), "LINEAR")
    key(rig, "location", f, base_loc + mathutils.Vector((0, -0.003, climb * 0.02)), "LINEAR")
    key(rig, "rotation_euler", f + 1, (climb + kick, rng.uniform(-0.008, 0.008), drift), "BEZIER")
    key(rig, "location", f + 1, base_loc + mathutils.Vector((rng.uniform(-0.0015, 0.0015), -0.014, 0.004 + climb * 0.02)), "BEZIER")
end = SHOTS[-1] + 3
key(rig, "rotation_euler", end, (climb * 0.8, 0, drift), "BEZIER")
key(rig, "rotation_euler", end + 30, (0, 0, 0), "BEZIER")           # the shooter brings it back down
key(rig, "location", end + 30, base_loc, "BEZIER")

# ---- slide: fully back on frame +1, home on frame +3 ----
for o in slide:
    home = o.location.copy()
    key(o, "location", START, home)
    for f in SHOTS:
        key(o, "location", f, home, "LINEAR")
        key(o, "location", f + 1, home + mathutils.Vector((0, -0.024, 0)), "LINEAR")
        key(o, "location", f + 3, home, "LINEAR")

# ---- muzzle flash: random size/spin each shot + a real light that lights the gun and floor ----
bpy.ops.mesh.primitive_cone_add(radius1=0.026, depth=0.075, vertices=7, rotation=(math.radians(-90), 0, 0))
flash = bpy.context.active_object; flash.data.materials.append(emit("Flash", (1.0, 0.62, 0.22), 45))
flash.parent = rig; flash.location = local_muzzle + mathutils.Vector((0, 0.035, 0))
bpy.ops.mesh.primitive_ico_sphere_add(radius=0.018, subdivisions=1)
core = bpy.context.active_object; core.data.materials.append(emit("FlashCore", (1.0, 0.9, 0.7), 80))
core.parent = rig; core.location = local_muzzle + mathutils.Vector((0, 0.012, 0))
bpy.ops.object.light_add(type="POINT"); fl = bpy.context.active_object
fl.data.color = (1.0, 0.7, 0.35); fl.data.shadow_soft_size = 0.05; fl.parent = rig; fl.location = local_muzzle + mathutils.Vector((0, 0.04, 0.01))
for o in (flash, core):
    key(o, "scale", START, (0, 0, 0), "CONSTANT")
fl.data.energy = 0; fl.data.keyframe_insert("energy", frame=START)
for f in SHOTS:
    s = rng.uniform(0.7, 1.35)
    key(flash, "scale", f - 1, (0, 0, 0), "CONSTANT"); key(core, "scale", f - 1, (0, 0, 0), "CONSTANT")
    key(flash, "scale", f, (s, s * rng.uniform(0.8, 1.6), s), "CONSTANT")
    key(flash, "rotation_euler", f, (math.radians(-90), rng.uniform(0, 6.28), 0), "CONSTANT")
    key(core, "scale", f, (s, s, s), "CONSTANT")
    key(flash, "scale", f + 1, (0, 0, 0), "CONSTANT"); key(core, "scale", f + 1, (0, 0, 0), "CONSTANT")
    for fr, e in ((f - 1, 0), (f, rng.uniform(25, 40)), (f + 1, 0)):
        fl.data.energy = e; fl.data.keyframe_insert("energy", frame=fr)
for fc in fl.data.animation_data.action.fcurves:
    for kp in fc.keyframe_points: kp.interpolation = "CONSTANT"

# ---- tracers: red 50% transparent, leave from the muzzle along where the gun points that frame ----
tracer_mat = emit("Tracer", (1.0, 0.05, 0.05), 10, alpha=0.5)
for i, f in enumerate(SHOTS):
    sc.frame_set(f + 1)
    mz = rig.matrix_world @ local_muzzle
    d = (rig.matrix_world.to_3x3() @ mathutils.Vector((0, 1, 0))).normalized()
    bpy.ops.mesh.primitive_cylinder_add(radius=0.005, depth=0.9, vertices=8, location=mz)
    t = bpy.context.active_object; t.data.materials.append(tracer_mat)
    t.rotation_euler = d.to_track_quat("Z", "Y").to_euler()
    key(t, "scale", START, (0, 0, 0), "CONSTANT"); key(t, "scale", f, (0, 0, 0), "CONSTANT")
    for k in range(0, 9):
        key(t, "location", f + 1 + k, mz + d * (0.46 + 1.4 * k), "LINEAR")
        key(t, "scale", f + 1 + k, (1, 1, 1), "CONSTANT")
    key(t, "scale", f + 10, (0, 0, 0), "CONSTANT")

# ---- brass: thrown out the right side, spinning, falling and bouncing on the floor ----
brass = bpy.data.materials.new("Brass"); brass.use_nodes = True
bb = brass.node_tree.nodes["Principled BSDF"]
bb.inputs["Base Color"].default_value = (0.78, 0.55, 0.22, 1); bb.inputs["Metallic"].default_value = 1.0; bb.inputs["Roughness"].default_value = 0.3
G, dt = -9.81, 1.0 / FPS
for i, f in enumerate(SHOTS):
    sc.frame_set(f + 1)
    p = rig.matrix_world @ local_port
    m3 = rig.matrix_world.to_3x3()
    v = m3 @ mathutils.Vector((rng.uniform(2.2, 3.0), rng.uniform(-0.6, 0.2), rng.uniform(1.6, 2.4)))
    spin = mathutils.Vector((rng.uniform(25, 45), rng.uniform(-10, 10), rng.uniform(20, 40)))
    bpy.ops.mesh.primitive_cylinder_add(radius=0.0048, depth=0.019, vertices=12, location=p)
    c = bpy.context.active_object; c.data.materials.append(brass)
    key(c, "scale", START, (0, 0, 0), "CONSTANT"); key(c, "scale", f, (0, 0, 0), "CONSTANT")
    rot = mathutils.Vector((0, 0, 0)); bounced = 0
    for k in range(0, END - f):
        fr = f + 1 + k
        if fr > END: break
        key(c, "location", fr, p, "LINEAR"); key(c, "rotation_euler", fr, rot, "LINEAR")
        if k == 0: key(c, "scale", fr, (1, 1, 1), "CONSTANT")
        v.z += G * dt; p = p + v * dt; rot = rot + spin * dt
        if p.z < 0.005:                                # hit the baseplate: bounce, lose energy
            p.z = 0.005; v.z = -v.z * 0.35; v.x *= 0.6; v.y *= 0.6; spin *= 0.5; bounced += 1
            if bounced > 3: v = mathutils.Vector((0, 0, 0)); spin = mathutils.Vector((0, 0, 0))

# ---- smoke: soft grey puffs that grow, rise and fade after each shot ----
smoke = bpy.data.materials.new("Smoke"); smoke.use_nodes = True; snt = smoke.node_tree
for n in list(snt.nodes): snt.nodes.remove(n)
so = snt.nodes.new("ShaderNodeOutputMaterial"); sd = snt.nodes.new("ShaderNodeBsdfDiffuse"); st = snt.nodes.new("ShaderNodeBsdfTransparent")
sm = snt.nodes.new("ShaderNodeMixShader"); sd.inputs["Color"].default_value = (0.6, 0.6, 0.62, 1)
snt.links.new(st.outputs[0], sm.inputs[1]); snt.links.new(sd.outputs[0], sm.inputs[2]); snt.links.new(sm.outputs[0], so.inputs[0])
smoke.blend_method = "BLEND"; smoke.surface_render_method = "BLENDED"; smoke.use_backface_culling = True
for i, f in enumerate(SHOTS[::2]):
    sc.frame_set(f + 1)
    mz = rig.matrix_world @ local_muzzle
    bpy.ops.mesh.primitive_ico_sphere_add(radius=0.02, subdivisions=3, location=mz)
    puff = bpy.context.active_object; m = smoke.copy(); puff.data.materials.append(m)
    mix = m.node_tree.nodes["Mix Shader"]
    key(puff, "scale", START, (0, 0, 0), "CONSTANT"); key(puff, "scale", f, (0, 0, 0), "CONSTANT")
    for k, (sz, a) in enumerate(((0.6, 0.12), (1.5, 0.07), (2.6, 0.03), (3.4, 0.0))):
        fr = f + 1 + k * 10
        key(puff, "scale", fr, (sz, sz, sz), "LINEAR")
        key(puff, "location", fr, mz + mathutils.Vector((rng.uniform(-0.03, 0.03), 0.04 * k, 0.05 * k)), "LINEAR")
        mix.inputs["Fac"].default_value = a; mix.inputs["Fac"].keyframe_insert("default_value", frame=fr)
sc.frame_set(START)
# light + camera
w = bpy.data.worlds.new("Sky"); sc.world = w; w.use_nodes = True
w.node_tree.nodes["Background"].inputs[0].default_value = (0.42, 0.55, 0.72, 1)
w.node_tree.nodes["Background"].inputs[1].default_value = 0.6
bpy.ops.object.light_add(type="SUN", location=(0, 0, 10), rotation=(math.radians(50), math.radians(10), math.radians(-30)))
bpy.context.active_object.data.energy = 3.5
bpy.ops.object.light_add(type="AREA", location=(0.3, -0.4, 1.5)); fill = bpy.context.active_object
fill.data.energy, fill.data.size = 6, 0.6
fill.constraints.new("TRACK_TO").target = rig
bpy.ops.object.camera_add(location=(-0.07, -0.34, 1.33)); cam = bpy.context.active_object; cam.data.lens = 30
aim = bpy.data.objects.new("Aim", None); sc.collection.objects.link(aim); aim.location = (-0.07, 3.0, 1.2)
cam.constraints.new("TRACK_TO").target = aim; sc.camera = cam
# camera shake: a small jolt on every shot, the aim point jumps a little and settles
home_aim = aim.location.copy()
aim.keyframe_insert("location", frame=START)
for f in SHOTS:
    aim.location = home_aim + mathutils.Vector((rng.uniform(-0.03, 0.03), 0, rng.uniform(0.01, 0.04)))
    aim.keyframe_insert("location", frame=f + 1)
    aim.location = home_aim; aim.keyframe_insert("location", frame=f + 3)
sc.render.use_motion_blur = True; sc.render.motion_blur_shutter = 0.5
sc.eevee.taa_render_samples = 24
sc.render.engine = "BLENDER_EEVEE_NEXT"
sc.eevee.use_bloom = True if hasattr(sc.eevee, "use_bloom") else None
sc.render.resolution_x, sc.render.resolution_y = 960, 540
sc.render.image_settings.file_format = "PNG"
sc.render.filepath = os.path.join(OUT, "frames2", "f_")
if os.environ.get("ONE"):
    sc.frame_set(int(os.environ["ONE"])); sc.render.filepath = os.path.join(OUT, "probe.png"); bpy.ops.render.render(write_still=True)
else:
    bpy.ops.render.render(animation=True)
