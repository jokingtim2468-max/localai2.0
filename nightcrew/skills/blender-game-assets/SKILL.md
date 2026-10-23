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
