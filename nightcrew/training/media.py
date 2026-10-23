"""Verified 3D / animation / video examples.

Each task is a (request, script, command, expected output file). verify() RUNS it — Blender
headless or ffmpeg — in a temp folder and keeps it only when it exits 0 and the file exists,
so the model is trained on code that works with YOUR installed versions.
"""
from __future__ import annotations

import os
import random
import shutil
import subprocess
import tempfile

MESHES = {"cube": "primitive_cube_add(size=2", "sphere": "primitive_uv_sphere_add(radius=1, segments=48, ring_count=24",
          "cylinder": "primitive_cylinder_add(radius=1, depth=2, vertices=48", "cone": "primitive_cone_add(radius1=1, depth=2, vertices=48",
          "torus": "primitive_torus_add(major_radius=1, minor_radius=0.3", "monkey head": "primitive_monkey_add(size=2"}
COLORS = {"red": (0.8, 0.05, 0.05), "orange": (1.0, 0.43, 0.0), "blue": (0.05, 0.2, 0.8), "green": (0.1, 0.6, 0.15),
          "gold": (1.0, 0.77, 0.3), "white": (0.9, 0.9, 0.9), "black": (0.02, 0.02, 0.02)}

HEAD = "import bpy, math, os\nbpy.ops.wm.read_factory_settings(use_empty=True)\nOUT = os.getcwd()\n"


def _material(var: str, color, metal: float, rough: float) -> str:
    r, g, b = color
    return (f"mat = bpy.data.materials.new('Mat')\nmat.use_nodes = True\n"
            f"bsdf = mat.node_tree.nodes['Principled BSDF']\n"
            f"bsdf.inputs['Base Color'].default_value = ({r}, {g}, {b}, 1)\n"
            f"bsdf.inputs['Metallic'].default_value = {metal}\nbsdf.inputs['Roughness'].default_value = {rough}\n"
            f"{var}.data.materials.append(mat)\n")


def blender_model(r: random.Random) -> tuple[str, str, str]:
    mesh, op = r.choice(list(MESHES.items()))
    color = r.choice(list(COLORS))
    metal = r.choice([0.0, 0.0, 1.0])
    smooth = r.random() < 0.6
    bevel = mesh == "cube" and r.random() < 0.6
    name = f"{color}_{mesh.replace(' ', '_')}"
    s = HEAD + f"bpy.ops.mesh.{op}, location=(0, 0, 1))\nobj = bpy.context.active_object\nobj.name = '{name}'\n"
    if bevel:
        s += "bev = obj.modifiers.new('Bevel', 'BEVEL')\nbev.width = 0.08\nbev.segments = 4\n"
    if smooth:
        s += "sub = obj.modifiers.new('Subdivision', 'SUBSURF')\nsub.levels = 2\nbpy.ops.object.shade_smooth()\n"
    s += _material("obj", COLORS[color], metal, 0.3 if metal else 0.5)
    s += f"bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, '{name}.blend'))\n"
    ask = f"make {"an" if (not metal and color[0] in "aeiou") else "a"} {'shiny metal ' if metal else ''}{color} {mesh}{' with bevelled edges' if bevel else ''}{', smooth' if smooth else ''} in blender and save it"
    return ask, s, f"{name}.blend"


def blender_animation(r: random.Random) -> tuple[str, str, str]:
    mesh, op = r.choice(list(MESHES.items()))
    kind = r.choice(["spin", "bounce", "slide", "grow"])
    frames = r.choice([48, 60, 96, 120])
    s = HEAD + f"bpy.ops.mesh.{op}, location=(0, 0, 1))\nobj = bpy.context.active_object\n"
    s += f"scene = bpy.context.scene\nscene.frame_start, scene.frame_end = 1, {frames}\n"
    if kind == "spin":
        s += (f"obj.rotation_euler = (0, 0, 0)\nobj.keyframe_insert('rotation_euler', frame=1)\n"
              f"obj.rotation_euler = (0, 0, math.radians(360))\nobj.keyframe_insert('rotation_euler', frame={frames})\n")
    elif kind == "bounce":
        s += (f"for f, z in ((1, 1), ({frames // 2}, 4), ({frames}, 1)):\n"
              f"    obj.location.z = z\n    obj.keyframe_insert('location', index=2, frame=f)\n")
    elif kind == "slide":
        s += (f"obj.location.x = -4\nobj.keyframe_insert('location', index=0, frame=1)\n"
              f"obj.location.x = 4\nobj.keyframe_insert('location', index=0, frame={frames})\n")
    else:
        s += (f"obj.scale = (0.1, 0.1, 0.1)\nobj.keyframe_insert('scale', frame=1)\n"
              f"obj.scale = (1, 1, 1)\nobj.keyframe_insert('scale', frame={frames})\n")
    s += "bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, 'animation.blend'))\n"
    verb = {"spin": "spins a full turn", "bounce": "bounces up and down", "slide": "slides left to right", "grow": "grows from tiny to full size"}[kind]
    return f"animate a {mesh} in blender that {verb} over {frames} frames", s, "animation.blend"


def blender_render(r: random.Random) -> tuple[str, str, str]:
    mesh, op = r.choice(list(MESHES.items()))
    color = r.choice(list(COLORS))
    res = r.choice([(640, 360), (800, 600), (512, 512)])
    s = HEAD + f"bpy.ops.mesh.{op}, location=(0, 0, 1))\nobj = bpy.context.active_object\n"
    s += _material("obj", COLORS[color], 0.0, 0.45)
    s += ("bpy.ops.mesh.primitive_plane_add(size=20)\n"
          "bpy.ops.object.light_add(type='SUN', location=(4, -4, 8))\nbpy.context.active_object.data.energy = 3\n"
          "bpy.ops.object.camera_add(location=(6, -6, 4))\ncam = bpy.context.active_object\n"
          "track = cam.constraints.new('TRACK_TO')\ntrack.target = obj\n"
          "scene = bpy.context.scene\nscene.camera = cam\n"
          "scene.render.engine = 'BLENDER_EEVEE_NEXT' if 'BLENDER_EEVEE_NEXT' in [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties['engine'].enum_items] else 'BLENDER_EEVEE'\n"
          f"scene.render.resolution_x, scene.render.resolution_y = {res[0]}, {res[1]}\n"
          "scene.render.filepath = os.path.join(OUT, 'render.png')\nbpy.ops.render.render(write_still=True)\n")
    return f"render a {color} {mesh} on a floor with a sun light at {res[0]}x{res[1]} in blender", s, "render.png"


def blender_export(r: random.Random) -> tuple[str, str, str]:
    mesh, op = r.choice(list(MESHES.items()))
    fmt = r.choice(["glb", "fbx", "obj", "stl"])
    call = {"glb": "bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, 'model.glb'), export_format='GLB')",
            "fbx": "bpy.ops.export_scene.fbx(filepath=os.path.join(OUT, 'model.fbx'))",
            "obj": "bpy.ops.wm.obj_export(filepath=os.path.join(OUT, 'model.obj'))",
            "stl": "bpy.ops.wm.stl_export(filepath=os.path.join(OUT, 'model.stl'))"}[fmt]
    s = HEAD + f"bpy.ops.mesh.{op}, location=(0, 0, 0))\n{call}\n"
    return f"make a {mesh} in blender and export it as .{fmt} for a game engine", s, f"model.{fmt}"


def blender_scene(r: random.Random) -> tuple[str, str, str]:
    n = r.randint(4, 12)
    seed = r.randint(1, 999)
    s = HEAD + (f"import random\nrandom.seed({seed})\nbpy.ops.mesh.primitive_plane_add(size=30)\n"
                "ground = bpy.context.active_object\n" + _material("ground", COLORS["green"], 0.0, 0.9) +
                f"for i in range({n}):\n"
                "    x, y = random.uniform(-12, 12), random.uniform(-12, 12)\n"
                "    bpy.ops.mesh.primitive_cylinder_add(radius=0.2, depth=1.2, vertices=8, location=(x, y, 0.6))\n"
                "    bpy.ops.mesh.primitive_cone_add(radius1=1, depth=2.4, vertices=8, location=(x, y, 2.3))\n"
                "bpy.ops.object.light_add(type='SUN', location=(0, 0, 10))\n"
                "bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, 'forest.blend'))\n")
    return f"build a low-poly scene in blender: grass ground and {n} simple trees", s, "forest.blend"


# ---- video editing with ffmpeg (input.mp4 is a 6 s 640x360 test clip with audio) ----
FF = [
    ("trim {f} to the part from {a}s to {b}s", "ffmpeg -y -i input.mp4 -ss {a} -to {b} -c:v libx264 -c:a aac trimmed.mp4", "trimmed.mp4"),
    ("scale {f} down to {w} pixels wide", "ffmpeg -y -i input.mp4 -vf scale={w}:-2 -c:a copy small.mp4", "small.mp4"),
    ("crop {f} to a square from the middle", "ffmpeg -y -i input.mp4 -vf \"crop=ih:ih\" -c:a copy square.mp4", "square.mp4"),
    ("make {f} play {s}x faster with the audio sped up too", "ffmpeg -y -i input.mp4 -filter_complex \"[0:v]setpts=PTS/{s}[v];[0:a]atempo={s}[a]\" -map \"[v]\" -map \"[a]\" fast.mp4", "fast.mp4"),
    ("turn the first {b} seconds of {f} into a gif", "ffmpeg -y -t {b} -i input.mp4 -vf \"fps=12,scale=320:-1:flags=lanczos\" clip.gif", "clip.gif"),
    ("pull the audio out of {f} as an mp3", "ffmpeg -y -i input.mp4 -vn -c:a libmp3lame -q:a 2 audio.mp3", "audio.mp3"),
    ("mute {f}", "ffmpeg -y -i input.mp4 -c:v copy -an muted.mp4", "muted.mp4"),
    ("add a 1 second fade in and fade out to {f}", "ffmpeg -y -i input.mp4 -vf \"fade=t=in:st=0:d=1,fade=t=out:st=5:d=1\" -af \"afade=t=in:d=1,afade=t=out:st=5:d=1\" faded.mp4", "faded.mp4"),
    ("change {f} to {fps} fps", "ffmpeg -y -i input.mp4 -r {fps} -c:a copy fps.mp4", "fps.mp4"),
    ("grab a thumbnail from {f} at {a} seconds", "ffmpeg -y -ss {a} -i input.mp4 -frames:v 1 thumb.png", "thumb.png"),
    ("put {f} twice in a row into one video", "ffmpeg -y -i input.mp4 -i input.mp4 -filter_complex \"[0:v][0:a][1:v][1:a]concat=n=2:v=1:a=1[v][a]\" -map \"[v]\" -map \"[a]\" joined.mp4", "joined.mp4"),
    ("put logo.png in the top-right corner of {f}", "ffmpeg -y -i input.mp4 -i logo.png -filter_complex \"overlay=W-w-16:16\" -c:a copy branded.mp4", "branded.mp4"),
]


def ffmpeg_task(r: random.Random) -> tuple[str, str, str]:
    ask, cmd, out = r.choice(FF)
    a = r.choice([0, 1, 2]); b = a + r.choice([2, 3])
    v = {"f": r.choice(["input.mp4", "the video", "my clip"]), "a": a, "b": b,
         "w": r.choice([320, 480, 640]), "s": r.choice([1.5, 2]), "fps": r.choice([24, 30])}
    return ask.format(**v), cmd.format(**v), out


GENERATORS = [("blender", blender_model, 3), ("blender", blender_animation, 2), ("blender", blender_render, 1),
              ("blender", blender_export, 2), ("blender", blender_scene, 1), ("ffmpeg", ffmpeg_task, 4)]


def find(tool: str) -> str | None:
    if shutil.which(tool):
        return shutil.which(tool)
    if tool == "blender" and os.name == "nt":
        base = r"C:\Program Files\Blender Foundation"
        if os.path.isdir(base):
            for d in sorted(os.listdir(base), reverse=True):
                p = os.path.join(base, d, "blender.exe")
                if os.path.isfile(p):
                    return p
    if tool == "blender" and os.path.isfile("/Applications/Blender.app/Contents/MacOS/Blender"):
        return "/Applications/Blender.app/Contents/MacOS/Blender"
    return None


def _fixtures(ffmpeg: str, d: str) -> None:
    run = lambda *a: subprocess.run([ffmpeg, "-y", *a], cwd=d, capture_output=True, timeout=60)
    run("-f", "lavfi", "-i", "testsrc=size=640x360:rate=30:duration=6", "-f", "lavfi", "-i", "sine=frequency=440:duration=6",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", "input.mp4")
    run("-f", "lavfi", "-i", "color=c=orange:s=96x96", "-frames:v", "1", "logo.png")


def verify(kind: str, script: str, out: str, tools: dict, timeout: int = 180) -> bool:
    """Run it for real in a scratch folder. True only if it exits 0 and made `out`."""
    with tempfile.TemporaryDirectory() as d:
        try:
            if kind == "blender":
                with open(os.path.join(d, "task.py"), "w", encoding="utf-8") as f:
                    f.write(script)
                r = subprocess.run([tools["blender"], "--background", "--factory-startup", "--python-exit-code", "1", "--python", os.path.join(d, "task.py")],
                                   cwd=d, capture_output=True, text=True, timeout=timeout)
                ok = r.returncode == 0 and "Traceback" not in (r.stderr + r.stdout)
            else:
                _fixtures(tools["ffmpeg"], d)
                cmd = script.replace("ffmpeg ", f'"{tools["ffmpeg"]}" ', 1)
                ok = subprocess.run(cmd, cwd=d, shell=True, capture_output=True, timeout=timeout).returncode == 0
            return ok and os.path.isfile(os.path.join(d, out)) and os.path.getsize(os.path.join(d, out)) > 0
        except (subprocess.TimeoutExpired, OSError):
            return False


def examples(n: int = 200, seed: int = 5, check: bool = True, log=print) -> list[dict]:
    """n verified examples. check=False skips running them (tests only)."""
    from .dataset import _call, _tool
    tools = {"blender": find("blender"), "ffmpeg": find("ffmpeg")}
    gens = [g for g in GENERATORS if not check or tools[g[0]]]
    if not gens:
        log("media: neither Blender nor ffmpeg is installed - skipping 3D/video examples")
        return []
    r, out, seen, tries = random.Random(seed), [], set(), 0
    pool = [g for g in gens for _ in range(g[2])]
    while len(out) < n and tries < n * 3:
        tries += 1
        kind, gen, _ = r.choice(pool)
        ask, script, file = gen(r)
        if (ask, script) in seen:
            continue
        seen.add((ask, script))
        if check and not verify(kind, script, file, tools):
            continue
        if kind == "blender":
            name = file.rsplit(".", 1)[0] + ".py"
            msgs = [{"role": "user", "content": ask},
                    _call("write_file", path=f"blender/{name}", content=script),
                    _tool("write_file", f"OK: wrote blender/{name} ({len(script)} chars)"),
                    _call("run_command", command=f"blender --background --factory-startup --python-exit-code 1 --python {name}", cwd="blender"),
                    _tool("run_command", "OK\nBlender quit"),
                    {"role": "assistant", "content": f"Done: blender/{name} ran cleanly in Blender and wrote blender/{file}."}]
        else:
            msgs = [{"role": "user", "content": ask}, _call("run_command", command=script),
                    _tool("run_command", "OK"), {"role": "assistant", "content": f"Done: wrote {file}. Command used: `{script}`"}]
        out.append({"messages": msgs, "source": "media"})
        if len(out) % 20 == 0:
            log(f"media: {len(out)}/{n} verified")
    return out
