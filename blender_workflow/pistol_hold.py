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

sc.frame_set(1)
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
sc.render.engine = "BLENDER_EEVEE_NEXT"; sc.render.resolution_x, sc.render.resolution_y = 960, 540
shots = {k: v for k, v in {"over": (eye + V((-0.25, 0.25, 0.25)), gun.location, 0.05), "fps": (eye, eye + V((0, -3, -0.05)), 0.02), "side": (eye + V((1.4, -0.5, 0.1)), eye + V((0, -0.25, -0.2)), 0.1), "gripR": (gun.location + V((-0.35, 0.05, 0.08)), gun.location, 0.02), "gripL": (gun.location + V((0.35, 0.05, 0.08)), gun.location, 0.02), "body": (eye + V((-3.0, -0.9, -0.6)), eye + V((0, -0.3, -0.75)), 0.1), "closeR": (gun.matrix_world.translation + V((-0.42, 0.02, 0.0)), gun.matrix_world.translation + V((0, 0, -0.06)), 0.01), "closeL": (gun.matrix_world.translation + V((0.42, -0.04, 0.0)), gun.matrix_world.translation + V((0, 0, -0.06)), 0.01), "top": (eye + V((0, -0.3, 0.9)), eye + V((-0.05, -0.3, -0.1)), 0.05)}.items() if k in os.environ.get("SHOTS", "over,fps,side")}
for name, (loc, aim, clip) in shots.items():
    bpy.ops.object.camera_add(location=loc); cam = bpy.context.active_object; cam.data.lens = 26 if name == "fps" else 35
    cam.data.clip_start = clip
    a = bpy.data.objects.new("A", None); sc.collection.objects.link(a); a.location = aim
    cam.constraints.new("TRACK_TO").target = a; sc.camera = cam
    sc.render.filepath = os.path.join(OUT, f"hands_{name}.png"); bpy.ops.render.render(write_still=True)
