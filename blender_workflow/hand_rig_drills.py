"""Procedural rigged hand + grip drills (open/close, stick, bumpy stick).
Right hand, palm faces -Z, fingers point +Y, thumb on -X. Every finger joint hinges on its bone's local X;
bone roll points local Z at the palm, so +X rotation always curls toward the palm. Limit Rotation constraints
stop any joint bending backward.  Run: blender --background --python handrig.py -- <out_dir>
"""
import bpy
import bmesh
import math
import mathutils
import os
import sys
from mathutils import Vector as V
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree

OUT = sys.argv[sys.argv.index("--") + 1] if "--" in sys.argv else "/tmp/handrig"
os.makedirs(OUT, exist_ok=True)

# finger name: (base x, base y, base z, direction, phalanx lengths, radius)
FINGERS = {
    "index":  (-0.030, 0.095, 0.0, V((-0.06, 1, 0)), (0.045, 0.027, 0.020), 0.0095),
    "middle": (-0.010, 0.098, 0.0, V((0, 1, 0)), (0.050, 0.031, 0.022), 0.0100),
    "ring":   (0.010, 0.095, 0.0, V((0.05, 1, 0)), (0.046, 0.029, 0.021), 0.0095),
    "pinky":  (0.029, 0.088, 0.0, V((0.12, 1, 0)), (0.036, 0.022, 0.018), 0.0085),
    "thumb":  (-0.038, 0.030, -0.008, V((-0.75, 0.62, -0.25)), (0.040, 0.032, 0.026), 0.0110),
}
LIMITS = (math.radians(90), math.radians(100), math.radians(75))   # knuckle, middle, tip
THUMB_LIMIT = math.radians(55)
FLESH = 0.0095                                                    # approx skin radius around a bone


def cleanup_scene():
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    for coll in (bpy.data.meshes, bpy.data.materials, bpy.data.armatures, bpy.data.textures):
        for d in list(coll):
            if d.users == 0:
                coll.remove(d)


def material(name, rgb, rough=0.6, spec=0.2):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*rgb, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Specular IOR Level"].default_value = spec
    return m


def segments():
    """(bone name, head, tail, radius) for the palm, every phalanx and the thumb."""
    out = [("hand.R", V((0, 0, 0)), V((0, 0.09, 0)), 0.0)]
    for fn, (x, y, z, d, lens, r) in FINGERS.items():
        d = d.normalized()
        p = V((x, y, z)) if fn != "thumb" else V((x, y, z))
        for i, L in enumerate(lens):
            q = p + d * L
            out.append((f"{fn}.0{i + 1}.R", p.copy(), q.copy(), r * (1 - 0.1 * i)))
            p = q
    return out


def build_mesh(segs):
    """Glove-like mesh: a rounded palm block plus one capsule per phalanx, all one object."""
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co = V((v.co.x * 0.082, v.co.y * 0.095 + 0.045, v.co.z * 0.026))
    bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=2, use_grid_fill=True)
    for name, h, t, r in segs[1:]:
        d = (t - h)
        mat = d.to_track_quat("Z", "Y").to_matrix().to_4x4()
        mat.translation = (h + t) / 2
        geo = bmesh.ops.create_cone(bm, cap_ends=False, segments=12, radius1=r, radius2=r * 0.92, depth=d.length)
        bmesh.ops.transform(bm, matrix=mat, verts=geo["verts"])
        # joint ball at the pivot: rotates in place, so a bent joint never opens a gap (knuckles stay whole)
        knuckle = name.endswith(".01.R") and not name.startswith("thumb")
        ball = bmesh.ops.create_uvsphere(bm, u_segments=12, v_segments=8, radius=r * (1.18 if knuckle else 1.02))
        bmesh.ops.translate(bm, vec=h, verts=ball["verts"])
        if name.endswith(".03.R"):                                   # rounded fingertip
            tipb = bmesh.ops.create_uvsphere(bm, u_segments=12, v_segments=8, radius=r * 0.92)
            bmesh.ops.translate(bm, vec=t, verts=tipb["verts"])
    me = bpy.data.meshes.new("HandMesh")
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new("Hand", me)
    bpy.context.scene.collection.objects.link(ob)
    mod = ob.modifiers.new("bevel", "BEVEL")
    mod.width, mod.segments = 0.006, 3
    ob.data.materials.append(material("BlackGlove", (0.015, 0.015, 0.017), 0.7, 0.15))
    return ob


def generate_rigged_hand():
    segs = segments()
    arm_data = bpy.data.armatures.new("HandRig")
    rig = bpy.data.objects.new("HandRig", arm_data)
    bpy.context.scene.collection.objects.link(rig)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode="EDIT")
    ebs = {}
    for name, h, t, r in segs:
        eb = arm_data.edit_bones.new(name)
        eb.head, eb.tail = h, t
        # local Z toward the palm (-Z) -> +X rotation = curl; the thumb curls across the palm toward the pinky side
        eb.align_roll(V((0.9, 0.2, -0.6)) if name.startswith("thumb") else V((0, 0, -1)))
        ebs[name] = eb
    for name in ebs:
        if name == "hand.R":
            continue
        fn, idx = name.split(".")[0], int(name.split(".")[1])
        parent = ebs["hand.R"] if idx == 1 else ebs[f"{fn}.0{idx - 1}.R"]
        ebs[name].parent = parent
        ebs[name].use_connect = idx > 1
    bpy.ops.object.mode_set(mode="OBJECT")

    ob = build_mesh(segs)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.modifier_apply(modifier="bevel")
    # weights: every vertex to its nearest bone segment (KDTree of points sampled along each bone)
    kd_pts = []
    for name, h, t, r in segs:
        for k in range(9):
            kd_pts.append((h.lerp(t, k / 8), name))
    kd = KDTree(len(kd_pts))
    for i, (p, _) in enumerate(kd_pts):
        kd.insert(p, i)
    kd.balance()
    groups = {name: ob.vertex_groups.new(name=name) for name, *_ in segs}
    for v in ob.data.vertices:
        if abs(v.co.x) < 0.043 and -0.005 < v.co.y < 0.091 and abs(v.co.z) < 0.0145:   # palm block stays rigid
            groups["hand.R"].add([v.index], 1.0, "REPLACE")
            continue
        hits = kd.find_n(v.co, 2)
        (p0, i0, d0), (p1, i1, d1) = hits[0], hits[1]
        n0, n1 = kd_pts[i0][1], kd_pts[i1][1]
        if n0 == n1 or d1 > d0 * 1.6:
            groups[n0].add([v.index], 1.0, "REPLACE")
        else:                                        # soft blend across a joint
            w0 = d1 / (d0 + d1)
            groups[n0].add([v.index], w0, "REPLACE")
            groups[n1].add([v.index], 1 - w0, "REPLACE")
    ob.parent = rig
    am = ob.modifiers.new("Armature", "ARMATURE")
    am.object = rig

    # limits: hinge only on local X, forward only
    for pb in rig.pose.bones:
        if pb.name == "hand.R":
            continue
        idx = int(pb.name.split(".")[1]) - 1
        lim = THUMB_LIMIT if pb.name.startswith("thumb") else LIMITS[idx]
        c = pb.constraints.new("LIMIT_ROTATION")
        c.owner_space = "LOCAL"
        c.use_limit_x = c.use_limit_y = c.use_limit_z = True
        c.min_x, c.max_x = 0.0, lim
        c.min_y = c.max_y = c.min_z = c.max_z = 0.0
        pb.rotation_mode = "XYZ"
    return rig, ob


def bone_points(rig, name):
    pb = rig.pose.bones[name]
    h, t = rig.matrix_world @ pb.head, rig.matrix_world @ pb.tail
    return [h.lerp(t, k / 4) for k in range(5)]


MARGIN = 0.0008                                                   # glove surface may touch, never pass through
OWN = {}                                                          # bone -> glove vertex indices it mostly drives


def own_vertices(ob):
    for v in ob.data.vertices:
        if v.groups:
            g = max(v.groups, key=lambda g: g.weight)
            OWN.setdefault(ob.vertex_groups[g.group].name, []).append(v.index)


def touching(rig, names, bvh):
    """True if any glove vertex driven by these bones is inside the object or closer than MARGIN."""
    dg = bpy.context.evaluated_depsgraph_get()
    ev = HAND.evaluated_get(dg); me = ev.data; mw = ev.matrix_world
    for n in names:
        for i in OWN.get(n, ()):
            p = mw @ me.vertices[i].co
            loc, nrm, _, d = bvh.find_nearest(p)
            if loc is not None and ((p - loc).dot(nrm) < 0 or d < MARGIN):
                return True
    return False


def grasp(rig, bvh=None, amount=1.0, step=math.radians(2)):
    """Curl joint by joint (knuckle first). With an object, each joint stops at first contact."""
    for fn in FINGERS:
        chain = [f"{fn}.0{i}.R" for i in (1, 2, 3)]
        for k, name in enumerate(chain):
            pb = rig.pose.bones[name]
            lim = (THUMB_LIMIT if fn == "thumb" else LIMITS[k]) * amount
            while pb.rotation_euler.x + step <= lim:
                pb.rotation_euler.x += step
                bpy.context.view_layer.update()
                if bvh and touching(rig, chain[k:], bvh):
                    pb.rotation_euler.x -= step
                    bpy.context.view_layer.update()
                    break


def open_hand(rig):
    for pb in rig.pose.bones:
        pb.rotation_euler = (0, 0, 0)
    bpy.context.view_layer.update()


def make_stick(bumpy=False, r=0.017, y=0.062):
    bpy.ops.mesh.primitive_cylinder_add(vertices=48, radius=r, depth=0.16, location=(0, y, -(0.013 + r + 0.002)),
                                        rotation=(0, math.radians(90), 0))
    o = bpy.context.active_object
    if bumpy:
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.subdivide(number_cuts=8)
        bpy.ops.object.mode_set(mode="OBJECT")
        tex = bpy.data.textures.new("bumps", "VORONOI")
        tex.noise_scale = 0.012
        d = o.modifiers.new("disp", "DISPLACE")
        d.texture, d.strength, d.mid_level = tex, 0.007, 0.3
        bpy.ops.object.modifier_apply(modifier="disp")
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    o.data.materials.append(material("Stick", (0.2, 0.35, 0.55) if bumpy else (0.55, 0.38, 0.2)))
    return o, BVHTree.FromObject(o, bpy.context.evaluated_depsgraph_get())


def setup_render():
    sc = bpy.context.scene
    w = bpy.data.worlds.new("W")
    sc.world = w
    w.use_nodes = True
    w.node_tree.nodes["Background"].inputs[0].default_value = (0.45, 0.5, 0.58, 1)
    bpy.ops.object.light_add(type="SUN", rotation=(math.radians(40), 0, math.radians(30)))
    bpy.context.active_object.data.energy = 3.5
    sc.render.engine = "BLENDER_EEVEE_NEXT"
    sc.render.resolution_x = sc.render.resolution_y = 480
    cams = {}
    for nm, loc in (("side", (0.32, 0.07, -0.02)), ("below", (0.12, 0.16, -0.28))):
        bpy.ops.object.camera_add(location=loc)
        cam = bpy.context.active_object
        cam.data.lens = 50
        t = bpy.data.objects.new("aim_" + nm, None)
        sc.collection.objects.link(t)
        t.location = (0, 0.07, -0.015)
        cam.constraints.new("TRACK_TO").target = t
        cams[nm] = cam
    return cams


def shot(cams, tag):
    sc = bpy.context.scene
    for nm, cam in cams.items():
        sc.camera = cam
        sc.render.filepath = os.path.join(OUT, f"{tag}_{nm}.png")
        bpy.ops.render.render(write_still=True)


def run_drills():
    cleanup_scene()
    global HAND
    rig, hand = generate_rigged_hand()
    HAND = hand
    own_vertices(hand)
    cams = setup_render()
    for i, a in enumerate((0.0, 0.35, 0.7, 1.0)):            # drill 1: open -> fist
        open_hand(rig)
        grasp(rig, None, amount=a)
        shot(cams, f"d1_fist_{i}")
    for name, bumpy in (("stick", False), ("bumpy", True)):  # drills 2, 3: grip a stick, then a bumpy one
        open_hand(rig)
        o, bvh = make_stick(bumpy)
        shot(cams, f"d_{name}_0open")
        grasp(rig, bvh)
        shot(cams, f"d_{name}_1grip")
        bpy.data.objects.remove(o, do_unlink=True)
    open_hand(rig)
    bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, "hand_rig.glb"), export_format="GLB")


run_drills()
