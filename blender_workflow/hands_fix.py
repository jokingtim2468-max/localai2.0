"""Contact grip for the character's own (Valve-biped) fingers, using what the hand drills taught us:
- each joint bends on its own hinge = bone direction x palm direction, sign chosen so the fingertip moves
  toward the palm pocket (never backward),
- real joint limits (knuckle 90, middle 100, tip 75 deg; thumb 55),
- joints close knuckle-first in small steps and stop when the deformed GLOVE vertices of that finger touch the gun
  (exact surface test, no phasing).
exec()'d inside the hold/fire scripts after reach()/orient_hand(); uses their arm, rotate_bone, wpos, chain,
finger, tip, BN globals."""
import math
import bpy
import mathutils
from mathutils.bvhtree import BVHTree

V = mathutils.Vector
LIMITS = (90, 100, 75)
THUMB = 55
MARGIN = 0.0008


def _glove():
    return next(o for o in bpy.context.scene.objects if o.type == "MESH" and any(m and "Gloves" in m.name for m in o.data.materials))


def _owned(glove):
    own = {}
    for v in glove.data.vertices:
        if v.groups:
            g = max(v.groups, key=lambda g: g.weight)
            own.setdefault(glove.vertex_groups[g.group].name, []).append(v.index)
    return own


def _trees(objs):
    dg = bpy.context.evaluated_depsgraph_get()
    return [BVHTree.FromObject(o, dg) for o in objs if o.type == "MESH" and len(o.data.polygons)]


def _touch(glove, own, names, trees):
    dg = bpy.context.evaluated_depsgraph_get()
    ev = glove.evaluated_get(dg); me = ev.data; mw = ev.matrix_world
    for n in names:
        for i in own.get(n, ()):
            p = mw @ me.vertices[i].co
            for t in trees:
                loc, nrm, _, d = t.find_nearest(p)
                if loc is not None and ((p - loc).dot(nrm) < 0 or d < MARGIN):
                    return True
    return False


def palm_dir(side):
    """Palm direction from the rest pose: the middle finger's natural curl bends toward the palm."""
    ch = chain(finger(side, 2)); a, b = wpos(ch[0]), wpos(ch[1]); c = tip(ch)
    d1 = (b - a).normalized(); dev = (c - b) - d1 * (c - b).dot(d1)
    return dev.normalized()


def grasp_valve(side, gun_objs, amount=1.0, step=2.0, open_first=True):
    glove = _glove(); own = _owned(glove); trees = _trees(gun_objs)
    W = wpos(BN[side][2]); f = (wpos(finger(side, 2)) - W).normalized()
    pn = palm_dir(side); pn = (pn - f * pn.dot(f)).normalized()
    pocket = W + f * 0.055 + pn * 0.03                      # where a held grip sits in the palm
    for i in range(5):
        ch = chain(finger(side, i))
        for k, b in enumerate(ch):
            nxt = wpos(ch[k + 1]) if k + 1 < len(ch) else tip(ch)
            bd = (nxt - wpos(b)).normalized()
            ax = bd.cross(pn)
            if ax.length < 1e-4:
                continue
            ax.normalize()
            d0 = (tip(ch) - pocket).length                 # pick the bend sign that moves the tip to the pocket
            q = mathutils.Quaternion(ax, math.radians(4)); rotate_bone(b, q, wpos(b))
            sgn = 1 if (tip(ch) - pocket).length < d0 else -1
            rotate_bone(b, q.inverted(), wpos(b))
            lim = (THUMB if i == 0 else LIMITS[min(k, 2)]) * amount
            done = 0.0
            while done + step <= lim:
                q = mathutils.Quaternion(ax, math.radians(sgn * step)); rotate_bone(b, q, wpos(b))
                if trees and _touch(glove, own, ch[k:], trees):
                    rotate_bone(b, q.inverted(), wpos(b)); break
                done += step
    print("GRASP", side, "done")
