---
name: blender-game-assets
description: Build and fix game-ready 3D assets in Blender headless - weapons, characters, first-person arms, firing animations
domain: blender
triggers: [blender, glb, gltf, 3d, model, character, gun, weapon, pistol, rifle, animation, recoil, hands, viewmodel, render, texture, rig]
---
- Work in a loop: run the script, render a preview PNG, LOOK at it, name what is wrong, change one thing, render again. Never call a model done without a render.
- Scripts live in `blender_workflow/` (see its README): inspect_model, extract_textures, preview_model, rebrand_pistol, dress_character, fps_hands, fire_animation.
- Run: `blender --background --factory-startup --python-exit-code 1 --python <abs path>.py -- <args>`; a non-zero exit or "Traceback" means it failed.
- Imported models look grey or show white shards: lower Specular IOR Level to 0.05-0.15, roughness 0.75-0.9. Do not recalculate normals.
- Attached models vanish: remove their Armature modifiers and own armature before fitting.
- Resizing an imported model: un-parent keeping world transform, delete empties, then scale.
- Rigs with unconnected bones (Valve/glTF): solve arm IK on joint head positions yourself.
- No real logos or brands, no illegal weapon parts; check licences (asset.extras) and keep CREDITS.txt.
- Script layout (bpy expert rules): imports (bpy, bmesh, math, mathutils) -> cleanup_scene() that removes objects with bpy.data.objects.remove (no context-dependent ops.delete) and purges orphan meshes/materials -> the generate_*() function -> material functions -> the call at the bottom. Blender 4.x API only, no add-ons.
- Hard-surface (weapons, props): build with bmesh/primitives, Bevel modifier, Boolean DIFFERENCE with hidden cutters, separate materials for metal / polymer / emissive (Principled BSDF via bpy.data.materials.new). Parent moving parts (slide, trigger, mag) to the receiver; put each origin on its pivot.
- Props: origin at bottom centre (Z = 0) so it sits on the ground; custom props like obj["item_type"] export with glTF extras (export_extras=True).
- Maps: grid + Subdivision + Displace (noise) for terrain; Collection Instances for repeats, never thousands of copies; a hidden simplified collision mesh; Sun + sky.
- Real sizes in metres: Glock 17 0.202 m long, AK pistol (Draco) ~0.47-0.52 m, MK18 0.68 m, character 1.829 m (6 ft).
- Hands/rigs: connected bones per phalanx, align_roll so local Z faces the palm (then +X rotation always curls forward), LIMIT_ROTATION X only 0-90/100/75 deg (thumb 55), a ball mesh at every joint so knuckles stay closed, palm weighted 100% to the hand bone. Grip = curl knuckle-first in 2 deg steps and stop when the deformed glove vertices touch the object (BVHTree.find_nearest, 0.8 mm). On Valve/glTF characters use blender_workflow/hands_fix.py (grasp_valve).
- Export: bpy.ops.export_scene.gltf(filepath=..., export_format="GLB", export_extras=True). Then render a preview with blender_workflow/preview_model.py and report what it shows.
