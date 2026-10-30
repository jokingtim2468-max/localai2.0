"""Measure a reference bike's outline: for slices along its length, top/bottom height and half-width of the
bodywork (above the axle line). Output JSON in metres, bike scaled to a target length. Proportions only."""
import bpy, sys, json, mathutils
src, out, L = sys.argv[sys.argv.index("--") + 1:]
L = float(L); V = mathutils.Vector
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=src)
ms = [o for o in bpy.context.scene.objects if o.type == "MESH"]
P = [o.matrix_world @ v.co for o in ms for v in o.data.vertices]
lo = V([min(p[i] for p in P) for i in range(3)]); hi = V([max(p[i] for p in P) for i in range(3)])
size = hi - lo; ax = max(range(3), key=lambda i: size[i])                 # length axis
up = 2 if ax != 2 and size[2] >= min(size[0], size[1]) * 0.9 and 2 != ax else 1
side = [i for i in range(3) if i not in (ax, up)][0]
k = L / size[ax]
pts = [((p[ax] - lo[ax]) * k, (p[up] - lo[up]) * k, (p[side] - (lo[side] + hi[side]) / 2) * k) for p in P]
N = 40; sl = []
for i in range(N):
    y0, y1 = L * i / N, L * (i + 1) / N
    s = [q for q in pts if y0 <= q[0] < y1 and q[1] > 0.33]                # above the axle line = bodywork
    if s:
        sl.append({"y": round((y0 + y1) / 2, 3), "top": round(max(q[1] for q in s), 3), "bot": round(min(q[1] for q in s), 3),
                   "hw": round(max(abs(q[2]) for q in s), 3)})
json.dump({"length": L, "height": round(size[up] * k, 3), "width": round(size[side] * k, 3), "slices": sl}, open(out, "w"), indent=1)
print("SIL", len(sl), "height", round(size[up] * k, 3), "width", round(size[side] * k, 3), "axes", ax, up, side)
