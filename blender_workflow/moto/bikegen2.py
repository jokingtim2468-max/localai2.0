"""Procedural motorcycles v2 — our own geometry, proportions taken from reference measurements (red superbike
outline) and each class's real specs. Every component is its own object so Roblox can stream / LOD / animate it:
Frame, Subframe, Engine, Radiator, ForkTubeL/R, ForkSliderL/R, ForkSpringL/R, TripleClamp, Bars, LeverL/R,
Swingarm, ShockBody, ShockSpring, Linkage, Chain, SprocketF/R, FrontTyre, FrontRim, FrontDiscL/R, CaliperFL/FR,
RearTyre, RearRim, RearDisc, CaliperR, Tank, Seat, Tail, TailLight, FairingL/R, Nose, Screen, Headlight, Belly,
MirrorL/R, Header, Can, PegL/R, PlateHolder (+ Winglets on homologation/supercharged, Headlight+Shroud on naked).

Exports per bike:  <id>.glb (LOD0, full detail)  and  <id>_mobile.glb (LOD1: inner springs/linkage dropped,
small parts merged, wheels/body decimated) for low-end phones.
Axes: +Y forward, +Z up, X across. Metres.   blender --background --python bikegen2.py -- <out> [ids...]
"""
import bpy, bmesh, math, os, sys
from mathutils import Vector as V

OUT = sys.argv[sys.argv.index("--") + 1]
ONLY = sys.argv[sys.argv.index("--") + 2:]

SPECS = {
    "nt500":  dict(name="500",        wb=1.410, rake=25.0, eng=0.80, style="naked", col=(0.02, 0.25, 0.08), acc=(0.04, 0.04, 0.04), rear=160, front=120),
    "st700":  dict(name="700",        wb=1.395, rake=23.7, eng=0.86, style="sport", col=(0.05, 0.12, 0.55), acc=(0.85, 0.85, 0.85), rear=180, front=120),
    "ss636":  dict(name="636",        wb=1.400, rake=23.5, eng=0.88, style="sport", col=(0.15, 0.55, 0.05), acc=(0.03, 0.03, 0.03), rear=180, front=120),
    "ls1000": dict(name="1000 GX",    wb=1.405, rake=23.5, eng=1.00, style="super", col=(0.08, 0.15, 0.6),  acc=(0.85, 0.85, 0.85), rear=190, front=120),
    "cp1000": dict(name="1000 CP",    wb=1.405, rake=24.0, eng=1.00, style="super", col=(0.03, 0.03, 0.04), acc=(0.1, 0.25, 0.7),   rear=190, front=120),
    "sb1000": dict(name="1K RR",      wb=1.441, rake=23.1, eng=1.00, style="super", col=(0.75, 0.05, 0.03), acc=(0.03, 0.03, 0.03), rear=200, front=120),
    "hm1000": dict(name="X10R 1000",  wb=1.450, rake=23.0, eng=1.02, style="super", col=(0.1, 0.45, 0.08),  acc=(0.03, 0.03, 0.03), rear=200, front=120, wings=True),
    "sc1000": dict(name="1000 SC",    wb=1.455, rake=24.5, eng=1.08, style="super", col=(0.2, 0.2, 0.22),   acc=(0.1, 0.5, 0.15),   rear=200, front=120, wings=True),
    "hb1340": dict(name="1340 Turbo", wb=1.480, rake=23.0, eng=1.25, style="hyper", col=(0.55, 0.55, 0.58), acc=(0.05, 0.05, 0.05), rear=190, front=120),
    "hb1500": dict(name="1500 R",     wb=1.510, rake=24.0, eng=1.32, style="hyper", col=(0.04, 0.04, 0.05), acc=(0.75, 0.55, 0.1),  rear=200, front=120),
}

# Upper-body outline measured from the reference superbike (ref y from the rear tip; rear axle at ref y ~0.33).
# (y_ref, top, bottom, half_width) — bodywork only.
TAIL = [(0.10, 0.93, 0.86, 0.04), (0.20, 0.99, 0.84, 0.09), (0.35, 1.00, 0.80, 0.12), (0.52, 0.93, 0.74, 0.135)]
SEAT = [(0.50, 0.86, 0.80, 0.12), (0.68, 0.83, 0.78, 0.135), (0.84, 0.84, 0.79, 0.14)]
TANK = [(0.82, 0.86, 0.72, 0.13), (0.95, 0.97, 0.70, 0.18), (1.10, 1.02, 0.72, 0.19), (1.26, 0.99, 0.80, 0.15)]
FAIR = [(1.10, 0.86, 0.42, 0.20), (1.30, 0.96, 0.38, 0.23), (1.50, 1.02, 0.42, 0.22), (1.70, 0.96, 0.50, 0.17),
        (1.86, 0.84, 0.58, 0.11), (1.97, 0.72, 0.64, 0.05)]
SCREEN = [(1.42, 1.04, 1.00, 0.15), (1.58, 1.15, 1.11, 0.11), (1.66, 1.12, 1.10, 0.07)]
BELLY = [(0.95, 0.42, 0.30, 0.13), (1.30, 0.42, 0.30, 0.15), (1.55, 0.50, 0.40, 0.12)]


def cleanup_scene():
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    for coll in (bpy.data.meshes, bpy.data.materials):
        for d in list(coll):
            if d.users == 0:
                coll.remove(d)


def mat(name, rgb, rough=0.45, metal=0.0, emit=0.0):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True; b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*rgb, 1); b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal; b.inputs["Specular IOR Level"].default_value = 0.4
    if emit:
        b.inputs["Emission Color"].default_value = (*rgb, 1); b.inputs["Emission Strength"].default_value = emit
    return m


PARTS = []


def add(bm, name, material, smooth=True, bevel=0.0):
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    for p in me.polygons: p.use_smooth = smooth
    o = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(o); me.materials.append(material)
    if bevel:
        b = o.modifiers.new("b", "BEVEL"); b.width = bevel; b.segments = 2; b.limit_method = "ANGLE"
    PARTS.append(o)
    return o


def loft(sections, ring=14, power=0.8, side=None, cap=True):
    """sections (y, top, bottom, half_width) -> rounded panel. side=-1/+1 keeps only the left/right half (fairing panels)."""
    bm = bmesh.new(); rings = []
    for (y, top, bot, hw) in sections:
        zc, hh = (top + bot) / 2, max(0.004, (top - bot) / 2); r = []
        for i in range(ring):
            a = 2 * math.pi * i / ring
            c, s = math.cos(a), math.sin(a)
            x = hw * math.copysign(abs(c) ** power, c)
            if side is not None:
                x = side * max(0.004, abs(x)) if side * x >= 0 else side * 0.004
            r.append(bm.verts.new((x, y, zc + hh * math.copysign(abs(s) ** power, s))))
        rings.append(r)
    for a, b in zip(rings, rings[1:]):
        for i in range(ring):
            bm.faces.new((a[i], a[(i + 1) % ring], b[(i + 1) % ring], b[i]))
    if cap:
        bm.faces.new(list(reversed(rings[0]))); bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm


def box(c, s):
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=s, verts=bm.verts); bmesh.ops.translate(bm, vec=c, verts=bm.verts)
    return bm


def tube(a, b, r, seg=10, r2=None):
    bm = bmesh.new(); d = b - a
    bmesh.ops.create_cone(bm, cap_ends=True, segments=seg, radius1=r, radius2=r2 if r2 else r, depth=max(d.length, 1e-4))
    m = d.to_track_quat("Z", "Y").to_matrix().to_4x4(); m.translation = (a + b) / 2
    bmesh.ops.transform(bm, matrix=m, verts=bm.verts)
    return bm


def disc(center, r, thick, seg=28, axis=V((1, 0, 0))):
    return tube(center - axis * thick / 2, center + axis * thick / 2, r, seg)


def coil(a, b, r, wire, turns, seg=8):
    """Helical spring from a to b (shock / fork springs)."""
    bm = bmesh.new(); d = b - a; L = d.length; q = d.to_track_quat("Z", "Y")
    steps = int(turns * 16); prev = None; rings = []
    for i in range(steps + 1):
        t = i / steps; ang = t * turns * 2 * math.pi
        c = V((r * math.cos(ang), r * math.sin(ang), (t - 0.5) * L))
        tang = V((-r * math.sin(ang), r * math.cos(ang), L / (turns * 2 * math.pi))).normalized()
        n1 = tang.orthogonal().normalized(); n2 = tang.cross(n1)
        ring = [bm.verts.new(c + (n1 * math.cos(2 * math.pi * k / seg) + n2 * math.sin(2 * math.pi * k / seg)) * wire) for k in range(seg)]
        rings.append(ring)
    for x, y in zip(rings, rings[1:]):
        for k in range(seg):
            bm.faces.new((x[k], x[(k + 1) % seg], y[(k + 1) % seg], y[k]))
    m = q.to_matrix().to_4x4(); m.translation = (a + b) / 2
    bmesh.ops.transform(bm, matrix=m, verts=bm.verts)
    return bm


def merge(*bms):
    out = bmesh.new(); me = bpy.data.meshes.new("tmp")
    for bm in bms:
        bm.to_mesh(me); out.from_mesh(me); bm.free()
    bpy.data.meshes.remove(me)
    return out


def tyre(center, width_mm, name, m):
    rim_r = 17 * 0.0254 / 2
    side = width_mm / 1000 * (0.70 if width_mm <= 120 else (0.55 if width_mm >= 190 else 0.60))
    R = rim_r + side / 2
    bm = bmesh.new()
    bmesh.ops.create_circle(bm, segments=8, radius=1)
    bm.free()
    bpy.ops.mesh.primitive_torus_add(major_radius=R, minor_radius=side / 2 + 0.006, major_segments=40, minor_segments=10,
                                     location=center, rotation=(0, math.radians(90), 0))
    t = bpy.context.active_object; t.name = name
    sx = (width_mm / 1000 / 2) / (side / 2 + 0.006)
    t.scale = (1, 1, sx)                                   # tyre width from the real size (torus minor axis is along local Z)
    bpy.ops.object.transform_apply(scale=True)
    t.data.materials.append(m["tyre"])
    for p in t.data.polygons: p.use_smooth = True
    PARTS.append(t)
    return R + 0.004, rim_r


def build_bike(bid, s):
    m = {"body": mat(f"{bid}_Body", s["col"], 0.28), "acc": mat(f"{bid}_Accent", s["acc"], 0.35),
         "tyre": mat("Tyre", (0.025, 0.025, 0.025), 0.9), "rim": mat("Rim", (0.05, 0.05, 0.055), 0.35, 0.7),
         "metal": mat("Metal", (0.6, 0.6, 0.62), 0.3, 1.0), "gold": mat("Gold", (0.75, 0.55, 0.15), 0.3, 1.0),
         "black": mat("Black", (0.02, 0.02, 0.022), 0.55), "screen": mat("Screen", (0.03, 0.035, 0.05), 0.05),
         "light": mat("Light", (1, 0.97, 0.9), 0.2, 0, 4), "tail": mat("TailLight", (1, 0.05, 0.03), 0.3, 0, 3),
         "seat": mat("Seat", (0.03, 0.03, 0.03), 0.85), "spring": mat("Spring", (0.85, 0.12, 0.05), 0.35, 0.3),
         "chain": mat("Chain", (0.15, 0.15, 0.15), 0.5, 0.8)}
    wb, e, style = s["wb"], s["eng"], s["style"]
    X = V((1, 0, 0))
    # reference outline is for a 1.441 m wheelbase superbike; stretch it to this bike's wheelbase
    k = wb / 1.441
    def ry(y_ref): return (y_ref - 0.33) * k                 # ref y -> our y (rear axle at 0)
    def sec(lst, zs=1.0, ws=1.0): return [(ry(y), t * zs, b * zs, w * ws) for (y, t, b, w) in lst]
    zs = {"naked": 0.97, "sport": 0.98, "super": 1.0, "hyper": 0.97}[style]
    ws = {"naked": 0.95, "sport": 0.95, "super": 1.0, "hyper": 1.15}[style]

    # ---- wheels: tyre / rim / discs / calipers as separate parts ----
    Rr, rim_r = tyre(V((0, 0, 0)), s["rear"], "RearTyre", m)
    Rf, _ = tyre(V((0, wb, 0)), s["front"], "FrontTyre", m)
    for o in PARTS[-2:]:
        o.location.z = Rr if o.name == "RearTyre" else Rf
    rc, fc = V((0, 0, Rr)), V((0, wb, Rf))
    def rim(c, w, name):
        sp = [tube(c - X * w * 0.35, c + X * w * 0.35, rim_r * 0.99, 36), tube(c - X * 0.065, c + X * 0.065, 0.04, 12)]
        for j in range(5):
            a = 2 * math.pi * j / 5
            for off in (-0.13, 0.13):
                d = V((0, math.cos(a + off), math.sin(a + off)))
                sp.append(tube(c + d * 0.04, c + d * rim_r * 0.96, 0.010, 6, 0.007))
        add(merge(*sp), name, m["rim"])
    rim(rc, s["rear"] / 1000, "RearRim"); rim(fc, s["front"] / 1000, "FrontRim")
    add(disc(fc + X * 0.075, 0.16, 0.005, 32), "FrontDiscR", m["metal"]); add(disc(fc - X * 0.075, 0.16, 0.005, 32), "FrontDiscL", m["metal"])
    add(disc(rc - X * 0.085, 0.11, 0.005, 28), "RearDisc", m["metal"])
    for sx, nm in ((1, "CaliperFR"), (-1, "CaliperFL")):
        add(box(fc + V((sx * 0.085, -0.10, 0.10)), V((0.03, 0.10, 0.06))), nm, m["gold"], bevel=0.006)
    add(box(rc + V((-0.09, 0.0, 0.10)), V((0.03, 0.07, 0.05))), "CaliperR", m["gold"], bevel=0.005)

    # ---- front end: fork tubes, sliders, springs, triple clamp, bars, levers ----
    rake = math.radians(s["rake"]); fl = 0.66
    head = fc + V((0, -math.sin(rake) * fl, math.cos(rake) * fl))
    for sx, sfx in ((-0.09, "L"), (0.09, "R")):
        top = head + V((sx, -0.02, 0.10)); low = fc + V((sx, 0, 0))
        mid = low.lerp(top, 0.48)
        add(tube(mid, top, 0.026 * (1.05 if e >= 1 else 1), 14), f"ForkTube{sfx}", m["gold"] if style != "naked" else m["metal"])
        add(tube(low + V((0, 0, -0.03)), mid + (top - low).normalized() * 0.06, 0.031, 14), f"ForkSlider{sfx}", m["black"])
        add(coil(low.lerp(top, 0.55), low.lerp(top, 0.92), 0.017, 0.0028, 9), f"ForkSpring{sfx}", m["spring"])
    add(merge(box(head + V((0, -0.01, 0.10)), V((0.26, 0.09, 0.03))), box(head + V((0, 0.0, -0.05)), V((0.26, 0.09, 0.035)))),
        "TripleClamp", m["metal"], bevel=0.006)
    if style == "naked":
        add(merge(tube(head + V((-0.37, 0.05, 0.25)), head + V((0.37, 0.05, 0.25)), 0.011, 10),
                  tube(head + V((0, 0, 0.12)), head + V((0, 0.03, 0.24)), 0.016, 8)), "Bars", m["black"])
        lev_y, lev_z = 0.05, 0.25
    else:
        add(merge(tube(head + V((-0.11, -0.02, 0.06)), head + V((-0.34, -0.09, 0.03)), 0.011, 10),
                  tube(head + V((0.11, -0.02, 0.06)), head + V((0.34, -0.09, 0.03)), 0.011, 10)), "Bars", m["black"])
        lev_y, lev_z = -0.06, 0.04
    for sx, sfx in ((-1, "L"), (1, "R")):
        add(tube(head + V((sx * 0.22, lev_y - 0.03, lev_z)), head + V((sx * 0.36, lev_y + 0.03, lev_z - 0.01)), 0.006, 6), f"Lever{sfx}", m["metal"])

    # ---- chassis: frame, subframe, swingarm, shock (body + spring), linkage ----
    pivot = V((0, 0.56 * k, 0.43))
    fr = []
    for sx in (-1, 1):
        fr += [tube(head + V((sx * 0.10, -0.05, -0.03)), pivot + V((sx * 0.135, 0.10, 0.17)), 0.032, 10),
               tube(pivot + V((sx * 0.135, 0.10, 0.17)), pivot + V((sx * 0.135, 0.0, -0.05)), 0.034, 10),
               tube(head + V((sx * 0.08, -0.03, -0.12)), V((sx * 0.12, pivot.y + 0.40 * e, 0.36)), 0.020, 8)]
    add(merge(*fr), "Frame", m["metal"] if style in ("naked", "hyper") else m["black"])
    sub = []
    for sx in (-1, 1):
        sub += [tube(pivot + V((sx * 0.12, 0.08, 0.17)), V((sx * 0.08, ry(0.30), 0.84 * zs)), 0.014, 8),
                tube(pivot + V((sx * 0.12, 0.02, 0.0)), V((sx * 0.08, ry(0.38), 0.82 * zs)), 0.012, 8)]
    add(merge(*sub), "Subframe", m["black"])
    sw = [box(pivot + V((0, 0, 0)), V((0.27, 0.07, 0.07)))]
    for sx in (-1, 1):
        sw.append(tube(rc + V((sx * 0.11, 0, 0)), pivot + V((sx * 0.12, 0, 0)), 0.03, 10, 0.04))
    add(merge(*sw), "Swingarm", m["metal"] if style == "hyper" else m["black"], bevel=0.004)
    shock_lo = pivot + V((0, -0.16, 0.0)); shock_hi = pivot + V((0, 0.02, 0.27))
    add(tube(shock_lo, shock_hi, 0.022, 12), "ShockBody", m["black"])
    add(coil(shock_lo.lerp(shock_hi, 0.12), shock_lo.lerp(shock_hi, 0.78), 0.032, 0.0045, 7), "ShockSpring", m["spring"])
    add(merge(box(shock_lo + V((0, 0.02, -0.03)), V((0.06, 0.08, 0.03)))), "Linkage", m["metal"])

    # ---- drivetrain: engine, radiator, sprockets, chain ----
    eng_c = V((0, pivot.y + 0.21 * k, 0.43 * (1 if style != "hyper" else 0.97)))
    add(merge(box(eng_c, V((0.30 * e ** 0.5, 0.34 * e ** 0.6, 0.27 * e ** 0.5))),
              box(eng_c + V((0, 0.10, 0.19)), V((0.26 * e ** 0.5, 0.18, 0.16))),
              box(eng_c + V((0, -0.05, -0.17)), V((0.22, 0.24, 0.08)))), "Engine", m["black"], bevel=0.008)
    add(box(eng_c + V((0, 0.29 * k, 0.17)), V((0.34 * min(e, 1.1), 0.04, 0.30))), "Radiator", m["black"], bevel=0.004)
    sproc_f = pivot + V((0.10, 0.06, -0.01))
    add(disc(sproc_f, 0.04, 0.008, 16), "SprocketF", m["metal"])
    add(disc(rc + V((0.10, 0, 0)), 0.11, 0.006, 32), "SprocketR", m["gold"])
    ch = []
    for dz in (0.04, -0.04):
        a = sproc_f + V((0, 0, dz)); b = rc + V((0.10, 0, dz * 2.7))
        ch.append(tube(a, b, 0.006, 6))
    add(merge(*ch), "Chain", m["chain"])

    # ---- bodywork (separate panels) ----
    add(loft(sec(TANK, zs, ws)), "Tank", m["body"])
    add(loft(sec(SEAT, zs, ws), power=0.6), "Seat", m["seat"])
    add(loft(sec(TAIL, zs, ws)), "Tail", m["body"] if style != "naked" else m["black"])
    add(box(V((0, ry(0.09), 0.90 * zs)), V((0.07, 0.02, 0.03))), "TailLight", m["tail"], bevel=0.004)
    add(merge(box(V((0, ry(0.05), 0.70 * zs)), V((0.20, 0.02, 0.14)))), "PlateHolder", m["black"])
    if style == "naked":
        hl_c = V((0, head.y + 0.14, head.z + 0.02))
        add(merge(tube(hl_c, hl_c + V((0, 0.06, 0)), 0.085, 20)), "Headlight", m["light"])
        add(loft([(head.y - 0.10, 0.92 * zs, 0.66, 0.17), (head.y - 0.32, 0.84 * zs, 0.56, 0.15)]), "Shroud", m["body"])
    else:
        bulk = {"sport": 0.95, "super": 1.0, "hyper": 1.18}[style]
        fair = [(y, t, b, w * bulk) for (y, t, b, w) in sec(FAIR, zs, 1.0)]
        if style == "hyper":                                  # long rounded nose
            fair[-1] = (fair[-1][0] + 0.08, fair[-1][1] - 0.02, fair[-1][2] - 0.06, 0.09)
        add(loft(fair, side=-1), "FairingL", m["body"]); add(loft(fair, side=1), "FairingR", m["body"])
        add(loft([(y, t, b, w * bulk) for (y, t, b, w) in sec(FAIR[-2:], zs, 1.0)], ring=12), "Nose", m["acc"])
        add(loft([(y, t, b, w * bulk) for (y, t, b, w) in sec(SCREEN, zs, 1.0)], ring=10, power=0.9), "Screen", m["screen"])
        ny = ry(1.93); nz = 0.73 * zs
        add(merge(box(V((-0.07, ny, nz)), V((0.08, 0.04, 0.025))), box(V((0.07, ny, nz)), V((0.08, 0.04, 0.025)))), "Headlight", m["light"])
        add(loft(sec(BELLY, 1.0, ws)), "Belly", m["acc"])
        for sx, sfx in ((-1, "L"), (1, "R")):
            add(box(V((sx * 0.28 * bulk, ry(1.52), 1.08 * zs)), V((0.10, 0.03, 0.055))), f"Mirror{sfx}", m["black"], bevel=0.008)
        if s.get("wings"):
            add(merge(box(V((-0.25, ry(1.62), 0.78 * zs)), V((0.12, 0.10, 0.012))), box(V((0.25, ry(1.62), 0.78 * zs)), V((0.12, 0.10, 0.012)))),
                "Winglets", m["acc"])
    # ---- exhaust: header + can ----
    if style == "hyper":
        add(merge(tube(eng_c + V((0.12, -0.05, -0.12)), V((0.17, pivot.y - 0.05, 0.30)), 0.022, 8),
                  tube(eng_c + V((-0.12, -0.05, -0.12)), V((-0.17, pivot.y - 0.05, 0.30)), 0.022, 8)), "Header", m["metal"])
        add(merge(tube(V((0.17, pivot.y - 0.05, 0.30)), V((0.18, pivot.y - 0.58, 0.44)), 0.058, 16),
                  tube(V((-0.17, pivot.y - 0.05, 0.30)), V((-0.18, pivot.y - 0.58, 0.44)), 0.058, 16)), "Can", m["metal"])
    else:
        add(tube(eng_c + V((0.08, 0.05, -0.15)), V((0.15, pivot.y - 0.02, 0.27)), 0.024, 8), "Header", m["metal"])
        add(tube(V((0.15, pivot.y - 0.02, 0.27)), V((0.17, pivot.y - 0.40, 0.42)), 0.05, 16, 0.045), "Can",
            m["black"] if style in ("super", "sport") else m["metal"])
    for sx, sfx in ((-1, "L"), (1, "R")):
        add(tube(V((sx * 0.12, pivot.y - 0.06, 0.33)), V((sx * 0.21, pivot.y - 0.06, 0.33)), 0.010, 6), f"Peg{sfx}", m["metal"])


def count(objs):
    dg = bpy.context.evaluated_depsgraph_get(); per = {}
    for o in objs:
        me = o.evaluated_get(dg).to_mesh(); per[o.name] = sum(len(p.vertices) - 2 for p in me.polygons); o.evaluated_get(dg).to_mesh_clear()
    return per


def make_mobile():
    """LOD1 for phones: drop hidden/inner detail, decimate round parts, keep the moving parts separate."""
    for o in list(PARTS):
        if o.name.startswith(("ForkSpring", "Linkage", "Lever", "SprocketF")):
            bpy.data.objects.remove(o, do_unlink=True); PARTS.remove(o); continue
        n = len(o.data.polygons)
        if n > 300:
            d = o.modifiers.new("lod", "DECIMATE"); d.ratio = 0.45


def main():
    os.makedirs(OUT, exist_ok=True)
    for bid, s in SPECS.items():
        if ONLY and bid not in ONLY:
            continue
        for mobile in (False, True):
            cleanup_scene(); PARTS.clear()
            build_bike(bid, s)
            if mobile:
                make_mobile()
            root = bpy.data.objects.new(f"Bike_{bid}", None); bpy.context.scene.collection.objects.link(root)
            for o in PARTS: o.parent = root
            root["bike_id"] = bid; root["display_name"] = s["name"]; root["lod"] = 1 if mobile else 0
            per = count(PARTS)
            print("BIKE", bid, "mobile" if mobile else "full", "parts", len(PARTS), "tris", sum(per.values()),
                  "max", max(per.values()), max(per, key=per.get))
            bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, f"{bid}{'_mobile' if mobile else ''}.glb"),
                                      export_format="GLB", export_extras=True, export_apply=True)


main()
