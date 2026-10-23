# Prompt: build the gun, the character, and the character holding the gun (Blender, bpy)

Paste everything below the line into the AI. In Eclipse: 3D models tab → "Make model", or the Chat with Blender access.
It produces three files: `models/pistol.glb`, `models/character.glb`, `models/character_holding_pistol.glb` (+ preview PNGs).

---

You are an elite Technical Art Director and Blender Python (bpy) expert. Write production-ready, error-free Blender 4.x
Python scripts that run headless:

`blender --background --factory-startup --python-exit-code 1 --python <absolute path to script> -- <args>`

## Rules for every script
- Layout: `import bpy, bmesh, math, mathutils` → `cleanup_scene()` (delete with `bpy.data.objects.remove(o, do_unlink=True)`,
  then purge orphan meshes/materials/armatures; never context-dependent `bpy.ops.object.delete()`) → `generate_*()` →
  material functions → the call at the bottom. No add-ons. Absolute paths only.
- Units are metres, real sizes. Materials: `bpy.data.materials.new` + Principled BSDF; Specular IOR Level 0.1–0.2,
  roughness 0.6–0.9 for polymer/cloth/skin (higher specular makes grey shards); metal = Metallic 1, roughness 0.3–0.45.
- Export each result: `bpy.ops.export_scene.gltf(filepath=..., export_format="GLB", export_extras=True)`.
- After every export render a preview PNG (Eevee, 3-point light, camera framed on the bounding box), look at it,
  name what is wrong, change ONE thing, run again. Never call it done without a render. If a run prints `Traceback`
  or exits non-zero, read the error, fix, run again.
- No real brand names, logos, crests or trademarks anywhere (fully blank). No illegal parts (no auto-sear / "switch" /
  conversion device). Semi-auto only; full-auto is a game setting, never a modelled part.

## 1) The gun — `models/pistol.glb`
A generic polymer-frame 9 mm striker pistol (Glock-17-like proportions, unbranded) with an extended drum magazine.
- Overall length 0.202 m, height 0.139 m (without drum), width 0.032 m, barrel 0.114 m. Drum mag ~0.10 m diameter,
  ~0.05 m thick, under the grip.
- Separate objects, each with its origin on its pivot, all parented to `receiver`:
  `receiver` (frame + grip, polymer, textured grip panels), `slide` (metal, serrations, origin so it slides along the
  barrel axis), `barrel` (metal), `trigger` (origin at its pin, rotates on local X), `magazine` (drum, polymer),
  `sights` (front + rear). Empty `muzzle` at the exact barrel tip, empty `ejection_port` on the right side of the slide,
  empty `grip` at the centre of the grip.
- Hard surface: bmesh/primitives + Bevel modifier (by angle) + Weighted Normal; Boolean DIFFERENCE with hidden cutters
  for the ejection port, serrations and lightening cuts. Apply booleans before export, hide cutters.
- Materials: `Polymer` (near-black, rough 0.75), `Metal` (dark gunmetal), `Mag` (polymer, slightly lighter).
- Custom props: `receiver["item_type"]="pistol"`, `["caliber"]="9mm"`, `["mag_capacity"]=50`.

## 2) The character — `models/character.glb`
A 6 ft (1.829 m) adult, streetwear, game-ready and rigged.
- Clothing: plain light-grey hoodie with the hood up (no print/logo), black sweatpants (matte cotton fleece, no logo),
  plain black leather shoes, black gloves, black knit balaclava with ONE eye opening from just under the eyebrows to
  just above the nose bridge (no mouth hole). The balaclava must sit INSIDE the hood: taper its sides/back so nothing
  pokes through; delete face skin hidden under the mask so cheeks can't clip through. Dark skin, matte (spec 0.25).
- Armature (EDIT mode, strict names): `root`, `hips`, `spine`, `chest`, `neck`, `head`, `shoulder.L/R`,
  `upper_arm.L/R`, `forearm.L/R`, `hand.L/R`, `thigh.L/R`, `shin.L/R`, `foot.L/R`.
- Fingers (this is what makes hands work — do it exactly):
  - Connected bones per phalanx: `index.01.R`, `index.02.R`, `index.03.R` … for thumb/index/middle/ring/pinky, both sides.
  - `edit_bone.align_roll(palm_direction)` so every finger bone's local Z points at the palm → +X rotation ALWAYS curls
    forward. Thumb roll points across the palm toward the pinky.
  - `LIMIT_ROTATION` constraint on each finger bone, LOCAL space, X only: knuckle 0–90°, middle 0–100°, tip 0–75°,
    thumb 0–55°. Fingers can never bend backward.
  - A ball mesh at every finger joint pivot (knuckle balls ~18 % wider) and rounded fingertips, so bent joints never
    open a gap or look broken.
  - Weights: KDTree nearest-bone with a soft blend across joints; palm block 100 % on `hand.*`.
- First-person split: vertex groups / separate objects so the owner client can show ONLY arms + hands (`fp_arms`) and
  hide head/torso/legs; everyone else sees the full body.

## 3) Character holding the gun — `models/character_holding_pistol.glb`
Import 1) and 2), parent the pistol's `grip` empty to `hand.R` and pose.
- Style: an UNTRAINED street shooter, not military: standing upright or leaning slightly back, feet roughly square,
  elbows flared, gun at chest/chin level, arms pushed out.
- Arms: two-bone IK (upper arm + forearm) to wrist targets; pole targets: firing elbow out to the side, support elbow
  down. Right wrist sits just behind and below the grip; left hand cups under the right hand or holds the drum.
- Fingers — contact grip, never clipping:
  1. Start from an open hand. For each finger, curl joint by joint (knuckle first) in 2° steps on local X.
  2. After every step, test the DEFORMED glove vertices of that finger (evaluated mesh) against the gun with
     `mathutils.bvhtree.BVHTree.FromObject` + `find_nearest`: if any vertex is inside (dot with normal < 0) or closer
     than 0.8 mm, undo the step and stop that joint.
  3. Right index finger: straight along the frame above the trigger guard (finger off the trigger) for the idle pose;
     a second pose `fire` with the index curled onto the trigger.
  4. Thumb: curl until contact on the left side of the frame.
- Export the posed result plus two actions on the armature: `idle_hold` and `fire` (slide back 0.03 m on the frame
  after the shot, muzzle rises at most 0.03 m (0.1 ft) up/left/right, then returns to centre within 3 frames at 60 fps).
- Renders to check: side view of the whole body, close-up of each hand on the gun from both sides, first-person view
  from the eyes. Fix anything that clips, floats, or bends the wrong way before finishing.

## Report at the end
List the three files with sizes in metres, triangle counts, bone count, and paste the paths of the preview renders.
