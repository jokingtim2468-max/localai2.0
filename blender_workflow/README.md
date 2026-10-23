# Blender game-asset workflow

The loop that produced the pistol, character, hands and firing videos:
**render → look → name what's wrong → change one thing → render again.**
Every script runs headless:

```
blender --background --factory-startup --python-exit-code 1 --python <script>.py -- <args>
```

| Script | Args | Does |
|---|---|---|
| `inspect_model.py` | `model.glb` | Lists every mesh: faces, world bounds, materials and textures |
| `extract_textures.py` | `model.glb out_dir` | Saves every texture as PNG, to find logos/camo/trademarks |
| `preview_model.py` | `model.glb out.png` | Auto-framed studio render of any model |
| `rebrand_pistol.py` | `source.glb out_dir` | Strips logos/camo, realistic finishes, real-scale export with credits |
| `dress_character.py` | `character.glb bandana.glb out_dir` (env `MASK=bandana|balaclava`, `BALACLAVA=...glb`) | Skin tone, gloves, shoes, mask fitted to the head bone, export |
| `fps_hands.py` | `character.glb gun.glb out_dir` | First-person arms on the gun: own two-bone IK, hand orientation, finger curl |
| `fire_animation.py` | `gun.glb out_dir` | 60 fps burst: recoil climb, slide, flash + light, tracers, brass, smoke, camera shake |

## Lessons (each cost an iteration)
- **Grey surfaces / white shards** on imported game models = specular far too high. Set Specular IOR Level 0.05-0.15 and roughness 0.75-0.9 on polymer/rubber. Do not recalculate normals on low-poly models.
- **Attachment invisible** although its bounds look right = it still has an Armature modifier pointing at its own rig. Remove modifiers and its armature before fitting.
- **Resize on export pulls parts apart** = Sketchfab files nest nodes. Un-parent keeping world transform, delete empties, then scale.
- **Blender IK does nothing** on Valve/glTF rigs: bones are not connected. Solve two-bone IK on joint positions (shoulder, elbow, wrist heads).
- **Finger curl splays**: try both bend directions per joint and keep the one that brings the fingertip closer to the grip.
- **Hand skin stretches**: the rig has helper bones (Wrist, Ulna); rotate them with the hand.
- **Texture on a new mesh shows solid colour**: write ONE UV map and make it active for render; replace only the Base Color image, not metal/roughness/normal maps.
- **`--python task.py` not found**: Blender resolves relative script paths from `$PWD`. Pass absolute paths.
- **Saturated colours look pink / everything washed out**: lights too strong for AgX; light energy ~ 60 × size².

## Rules
- No real brand names or logos. No illegal weapon parts. Full-auto is a game setting only.
- Check every asset licence (Sketchfab files store it in `asset.extras`). CC0 / CC-BY only for a sold game; keep `CREDITS.txt`.
