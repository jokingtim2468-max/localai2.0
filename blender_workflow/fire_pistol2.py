import bpy, sys, os, math, mathutils
CHAR, GUN, OUT = sys.argv[sys.argv.index("--") + 1:]
V = mathutils.Vector
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
bpy.ops.import_scene.gltf(filepath=CHAR)
arm = next(o for o in sc.objects if o.type == "ARMATURE")
meshes = [o for o in sc.objects if o.type == "MESH"]
top = max((o.matrix_world @ V(c)).z for o in meshes for c in o.bound_box)
s = 1.829 / top                                       # 6 ft                                       # real height
root = arm
while root.parent: root = root.parent
root.scale = [v * s for v in root.scale]
bpy.context.view_layer.update()
# first person: hide everything above the shoulders and the legs
for o in meshes:
    mats = [m.name for m in o.data.materials if m]
    if os.environ.get("THIRD"):
        if "mouth" in "".join(mats): o.hide_render = True
        continue
    if any(k in "".join(mats) for k in ("ted_facemap", "mouth", "eyeball", "Material_003", "bbshoes", "pants", "Leather")) or o.name == "BandanaMask":
        o.hide_render = True
ARMB = ("UpperArm", "Forearm", "Hand", "Ulna", "Wrist", "Finger", "Bicep", "Elbow")
import bmesh
for o in meshes:
    if o.hide_render: continue
    mats = "".join(m.name for m in o.data.materials if m)
    if "Gloves" in mats: continue
    if "ancestor" in mats:                       # hoodie: drop the printed logo, plain cloth colour
        for m in o.data.materials:
            bsdf = m.node_tree.nodes.get("Principled BSDF")
            for l in list(bsdf.inputs["Base Color"].links): m.node_tree.links.remove(l)
            bsdf.inputs["Base Color"].default_value = (0.5, 0.52, 0.53, 1)
            bsdf.inputs["Specular IOR Level"].default_value = 0.2
    if os.environ.get("FULLBODY"): continue
    only = os.environ.get("ONLY", "")
    keep = {g.index for g in o.vertex_groups if any(k in g.name for k in ARMB) and (not only or f"_{only}_" in g.name)}
    if not keep: o.hide_render = True; continue
    bm = bmesh.new(); bm.from_mesh(o.data); dl = bm.verts.layers.deform.active
    kill = [v for v in bm.verts if not dl or sum(w for gi, w in v[dl].items() if gi in keep) < 0.5]
    bmesh.ops.delete(bm, geom=kill, context="VERTS"); bm.to_mesh(o.data); bm.free()

def bone_world(name, tail=False):
    b = arm.pose.bones[name]
    return arm.matrix_world @ (b.tail if tail else b.head)

eye = (bone_world("ValveBiped.Bip01_Head1_1") + V((0, -0.09 * s, 0.03 * s)))
# gun: our pistol points +Y, the character looks -Y, so turn it round
bpy.ops.import_scene.gltf(filepath=GUN)
gun_parts = [o for o in sc.objects if o.type == "MESH" and o not in meshes]
# drum magazine x3 (DRUM env): grow only the drum below the grip, anchored at the mag well
import bmesh as _bm
DRUM = float(os.environ.get("DRUM", "3"))
for o in gun_parts:
    if o.name == "Object_14" and DRUM != 1:
        mw = o.matrix_world; mi = mw.inverted(); anchor = V((0.0, -0.04, -0.005))
        for v in o.data.vertices:
            p = mw @ v.co
            if p.z < -0.005:
                q = anchor + (p - anchor) * DRUM
                q.z = min(q.z, -0.005)
                v.co = mi @ q
        o.data.update()
gun = bpy.data.objects.new("Gun", None); sc.collection.objects.link(gun)
GRIP = V((0.0, -0.035, 0.018))                       # grip centre in the pistol's own coordinates
for o in gun_parts:
    mw = o.matrix_world.copy(); o.parent = gun; o.matrix_world = mathutils.Matrix.Translation(-GRIP) @ mw
gun.rotation_euler = (0, 0, math.pi)
_ys = [(o.matrix_world @ V(c)).y for o in gun_parts if o.name != 'Object_14' for c in o.bound_box]
gun.scale = [0.202 / (max(_ys) - min(_ys))] * 3                     # Glock 17: 202 mm
gun.location = eye + V(tuple(float(x) for x in os.environ.get("GUNPOS", "-0.1,-0.33,-0.11").split(",")))     # character right = -X         # right of centre, out in front, below the eye
bpy.context.view_layer.update()

def target(name, parent, loc):
    e = bpy.data.objects.new(name, None); sc.collection.objects.link(e)
    e.parent = parent; e.location = loc; return e

rh_t = target("RH_target", gun, V(tuple(float(x) for x in os.environ.get("RHT", "0.02,-0.07,-0.06").split(","))))             # right palm on the grip
lh_t = target("LH_target", gun, V(tuple(float(x) for x in os.environ.get("LHT", "-0.045,-0.05,-0.075").split(","))))             # left hand cups from the support side
r_pole = target("R_pole", None, eye + V((0.35, 0.1, -0.45)))
l_pole = target("L_pole", None, eye + V((-0.35, 0.1, -0.45)))
BN = {"R": ("ValveBiped.Bip01_R_UpperArm_26", "ValveBiped.Bip01_R_Forearm_22", "ValveBiped.Bip01_R_Hand_19"),
      "L": ("ValveBiped.Bip01_L_UpperArm_52", "ValveBiped.Bip01_L_Forearm_48", "ValveBiped.Bip01_L_Hand_45")}
r_pole.location = eye + V((-0.35, 0.15, -0.5)); l_pole.location = eye + V((0.35, 0.15, -0.5))

def wpos(name):
    return arm.matrix_world @ arm.pose.bones[name].head

def rotate_bone(name, q, pivot):
    pb = arm.pose.bones[name]
    M = mathutils.Matrix.Translation(pivot) @ q.to_matrix().to_4x4() @ mathutils.Matrix.Translation(-pivot)
    pb.matrix = arm.matrix_world.inverted() @ (M @ (arm.matrix_world @ pb.matrix))
    bpy.context.view_layer.update()

def reach(side, target, pole):
    """Two-bone IK on joint positions (this rig's bones are not connected, so Blender IK can't)."""
    up, fo, ha = BN[side]
    S_, E_, W_ = wpos(up), wpos(fo), wpos(ha)
    L1, L2 = (E_ - S_).length, (W_ - E_).length
    T = target.matrix_world.translation
    d = min((T - S_).length, L1 + L2 - 1e-4); dr = (T - S_).normalized()
    ca = max(-1, min(1, (L1 * L1 + d * d - L2 * L2) / (2 * L1 * d)))
    p = pole.matrix_world.translation - S_; perp = (p - dr * p.dot(dr)).normalized()
    E2 = S_ + dr * (L1 * ca) + perp * (L1 * math.sqrt(1 - ca * ca))
    rotate_bone(up, (E_ - S_).rotation_difference(E2 - S_), S_)
    E_, W_ = wpos(fo), wpos(ha)
    rotate_bone(fo, (W_ - E_).rotation_difference(T - E_), E_)
    print("REACH", side, "miss", round((wpos(ha) - T).length, 3), "arm length", round(L1 + L2, 3), "needed", round((T - S_).length, 3))

bpy.context.view_layer.update()
reach("R", rh_t, r_pole); reach("L", lh_t, l_pole)

def basis(f, t):
    x = f.normalized(); z = x.cross(t).normalized(); y = z.cross(x)
    return mathutils.Matrix((x, y, z)).transposed()

FING = {s_: [b.name for b in arm.data.bones if b.name.startswith(f"ValveBiped.Bip01_{s_}_Finger") and b.parent and "Hand" in b.parent.name] for s_ in "RL"}

def finger(side, i):
    return next(n for n in FING[side] if f"_Finger{i}_" in n)

def orient_hand(side, f_t, t_t):
    """Turn the hand so knuckles point along f_t and the thumb along t_t (world space)."""
    ha = BN[side][2]; W_ = wpos(ha)
    f = wpos(finger(side, 2)) - W_; t = wpos(finger(side, 0)) - W_
    R = basis(V(f_t), V(t_t)) @ basis(f, t).inverted()
    q = R.to_quaternion()
    rotate_bone(ha, q, W_)
    wrist = next(b.name for b in arm.data.bones if b.name.startswith(f"ValveBiped.Bip01_{side}_Wrist"))
    ulna = next(b.name for b in arm.data.bones if b.name.startswith(f"ValveBiped.Bip01_{side}_Ulna"))
    rotate_bone(wrist, q, W_)                                   # wrist helper carries the back of the hand
    rotate_bone(ulna, mathutils.Quaternion().slerp(q, 0.5), wpos(ulna))   # forearm twist takes half

def chain(name):
    out = [name]
    while True:
        kids = arm.data.bones[out[-1]].children
        if not kids: return out
        out.append(kids[0].name)

def palm_normal(side):
    W_ = wpos(BN[side][2])
    f = (wpos(finger(side, 2)) - W_).normalized()
    lat = (wpos(finger(side, 4)) - wpos(finger(side, 1))).normalized()     # index -> pinky across the knuckles
    n = f.cross(lat).normalized()
    th = wpos(finger(side, 0)) - W_
    return n if n.dot(th - f * th.dot(f)) > 0 else -n                     # palm is on the thumb side

def tip(b_chain):
    last = b_chain[-1]
    return arm.matrix_world @ arm.pose.bones[last].head + (arm.matrix_world @ arm.pose.bones[last].head - arm.matrix_world @ arm.pose.bones[b_chain[-2]].head) * 0.8

def curl(side, palm_n, deg, thumb_deg):
    """Bend each finger joint; of the two directions keep the one that closes on the grip."""
    grip = gun.matrix_world.translation if side == "R" else wpos(BN["R"][2]) + (gun.matrix_world.translation - wpos(BN["R"][2])) * 0.5
    W_ = wpos(BN[side][2]); f = (wpos(finger(side, 2)) - W_).normalized()
    lat = (wpos(finger(side, 4)) - wpos(finger(side, 1))).normalized()
    pn = palm_normal(side)
    for i in range(0, 5):
        ch = chain(finger(side, i))
        for k, b in enumerate(ch):
            a = math.radians(thumb_deg if i == 0 else (8 if side == "R" and i == 1 else deg[min(k, 2)]))
            ax = lat if i else f                       # fingers hinge across the knuckles, thumb swings over the palm
            before = tip(ch).copy()
            rotate_bone(b, mathutils.Quaternion(ax, a), wpos(b))
            if (tip(ch) - before).dot(pn) < 0:              # must close towards the palm
                rotate_bone(b, mathutils.Quaternion(ax, -2 * a), wpos(b))

# right hand: hand upright on the grip, palm facing the gun's left side (+X), fingers wrap round the front
orient_hand("R", (0.0, -0.7, 0.7), (0.2, -0.95, 0.2))
exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "hands_fix.py")).read())
None if os.environ.get("NOCURL") else grasp_valve("R", gun_parts, straight=(1,), pass_start=True)
if not os.environ.get("NOCURL"):
    # real two-hand pistol grip (USCCA / guns.com): firing hand high on the backstrap, middle finger under the
    # trigger guard, index straight along the frame; support hand fills the left side of the grip, its four
    # fingers wrap OVER the firing hand's knuckles, support thumb points forward along the frame under the slide,
    # firing thumb rests forward on top of the support hand.
    _fwd = gun.matrix_world.to_3x3() @ V((0, 1, 0))
    point_finger("R", 1, _fwd)
# left hand: support hand on the left side of the grip
orient_hand("L", tuple(float(x) for x in os.environ.get("LF", "-0.6,-0.55,-0.5").split(",")), (-0.1, -0.95, 0.25))
None if os.environ.get("NOCURL") else grasp_valve("L", gun_parts, straight=(0,), around="R", pass_start=True)
if not os.environ.get("NOCURL"):
    _down = gun.matrix_world.to_3x3() @ V((0, 0, -1))
    point_finger("L", 0, _fwd - _down * 0.22)            # support thumb forward along the frame
    pass                                                 # firing thumb: left to the contact curl (wraps the backstrap)
print("FINGERS", FING["R"], [chain(finger("R", i)) for i in range(5)][:2])

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


# ---------------- final pistol clip: posed arms ride the gun, gun drives everything ----------------
import mathutils as _m
root.parent = None
mw = root.matrix_world.copy(); root.parent = None if os.environ.get("THIRD") else gun; root.matrix_world = mw     # arms follow recoil rigidly
for e in (r_pole, l_pole):
    e.parent = gun
rig = gun
# real muzzle: centre of the front-most vertices of the slide/barrel, in the gun's own coordinates
fr = [(gun.matrix_world.inverted() @ (o.matrix_world @ v.co)) for o in gun_parts for v in o.data.vertices]
top = max(p.z for p in fr)
ymax = max(p.y for p in fr if p.z > top - 0.035)
tip = [p for p in fr if p.y > ymax - 0.003 and p.z > top - 0.035]
MUZ = sum(tip, _m.Vector()) / len(tip)
print("MUZZLE local", tuple(round(c, 4) for c in MUZ), "from", len(tip), "verts")
slide = [o for o in gun_parts if o.name in ("Object_8", "Object_12")]
import random
rng = random.Random(19)
FPS, START, END = 60, 1, 170
sc.render.fps = FPS; sc.frame_start, sc.frame_end = START, END
SHOTS = list(range(20, 20 + 3 * 22, 3))           # 22 rounds, one every 3 frames at 60 fps (~1,200/min)
local_muzzle = MUZ + mathutils.Vector((0, 0.004, 0))
local_port = mathutils.Vector((0.016, 0.035, 0.07)) - GRIP     # ejection port, right side of the slide

def key(obj, path, frame, value, interp=None):
    setattr(obj, path, value); obj.keyframe_insert(path, frame=frame)
    if interp and obj.animation_data and obj.animation_data.action:
        for fc in obj.animation_data.action.fcurves:
            if fc.data_path == path:
                for kp in fc.keyframe_points:
                    if int(kp.co.x) == frame: kp.interpolation = interp

# ---- recoil: each shot kicks the gun at most 0.1 ft (3.05 cm) left/right/up from where it fired, then it
#      settles back on the centre so every round goes to the crosshair ----
LIM = 0.03048
base_loc = rig.location.copy(); base_rot = rig.rotation_euler.copy()
key(rig, "location", START, base_loc); key(rig, "rotation_euler", START, base_rot)
for f in SHOTS:
    dx, dz = rng.uniform(-1, 1) * LIM, rng.uniform(0.35, 1) * LIM
    key(rig, "location", f, base_loc, "LINEAR"); key(rig, "rotation_euler", f, base_rot, "LINEAR")
    key(rig, "location", f + 1, base_loc + mathutils.Vector((dx, 0, dz)), "BEZIER")
    key(rig, "rotation_euler", f + 1, (base_rot.x + dz * 1.6, 0, base_rot.z + dx * 1.2), "BEZIER")
end = SHOTS[-1] + 3
key(rig, "location", end, base_loc, "BEZIER"); key(rig, "rotation_euler", end, base_rot, "BEZIER")

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
    d = ((eye + V((0, -3, -0.05)) * 1 + V((0, -3, -0.05)) * 9) - mz).normalized()   # to the crosshair, 30 m out
    if i == 0: print("TRACERDIR", tuple(round(c, 3) for c in d), "muzzle", tuple(round(c, 3) for c in mz), "gunrot", tuple(round(c, 3) for c in rig.rotation_euler))
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
w = bpy.data.worlds.new("Sky"); sc.world = w; w.use_nodes = True
w.node_tree.nodes["Background"].inputs[0].default_value = (0.42, 0.55, 0.72, 1)
w.node_tree.nodes["Background"].inputs[1].default_value = 0.6
bpy.ops.object.light_add(type="SUN", rotation=(math.radians(50), math.radians(10), math.radians(150)))
bpy.context.active_object.data.energy = 3.5
bpy.ops.mesh.primitive_plane_add(size=40)
bp = bpy.context.active_object; m = bpy.data.materials.new("Base"); m.use_nodes = True
ck = m.node_tree.nodes.new("ShaderNodeTexChecker"); ck.inputs["Scale"].default_value = 40
ck.inputs["Color1"].default_value = (0.32, 0.32, 0.33, 1); ck.inputs["Color2"].default_value = (0.27, 0.27, 0.28, 1)
m.node_tree.links.new(ck.outputs["Color"], m.node_tree.nodes["Principled BSDF"].inputs["Base Color"]); bp.data.materials.append(m)
THIRD = bool(os.environ.get("THIRD"))
bpy.ops.object.camera_add(location=eye + V((-3.6, -0.5, -0.65)) if THIRD else eye); cam = bpy.context.active_object; cam.data.lens = 35 if THIRD else 26; cam.data.clip_start = 0.02
aim = bpy.data.objects.new("Aim", None); sc.collection.objects.link(aim); aim.location = eye + V((0, -0.35, -0.72)) if THIRD else eye + V((0, -3, -0.05))
cam.constraints.new("TRACK_TO").target = aim; sc.camera = cam
home_aim = aim.location.copy(); aim.keyframe_insert("location", frame=START)
for f in ([] if THIRD else SHOTS):
    aim.location = home_aim + V((rng.uniform(-0.02, 0.02), 0, rng.uniform(0.005, 0.025))); aim.keyframe_insert("location", frame=f + 1)
    aim.location = home_aim; aim.keyframe_insert("location", frame=f + 3)
sc.render.engine = "BLENDER_EEVEE_NEXT"; sc.eevee.taa_render_samples = 16
sc.render.use_motion_blur = True; sc.render.motion_blur_shutter = 0.5
sc.render.resolution_x, sc.render.resolution_y = 960, 540
sc.render.image_settings.file_format = "PNG"
if os.environ.get("ONE"):
    sc.frame_set(int(os.environ["ONE"])); sc.render.filepath = os.path.join(OUT, "probe.png"); bpy.ops.render.render(write_still=True)
else:
    sc.frame_start = int(os.environ.get("FSTART", sc.frame_start)); sc.render.filepath = os.path.join(OUT, "frames", "f_"); bpy.ops.render.render(animation=True)
