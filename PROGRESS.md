# PROGRESS (resume file)
Redo order if lost:
1. Blender 4.2.3 at /tmp/bl/...; scripts in blender_workflow/ (run: blender --background --factory-startup --python-exit-code 1 --python ABS.py -- args).
2. hood_map.py args: <assets dir with tex/ + props/ (Poly Haven CC0, fetch via api.polyhaven.com w/ User-Agent)> <out dir>. Env SHOTS, NOEXPORT. Outputs map_*.png + chunk_*.glb.
3. Training: nightcrew/training/blender_code.py (bpy code examples), wired in dataset.py + eclipse/src/Training.tsx.
4. Upload every new thing to NexusNotes (notes: Blender workflow, Game design: hood shooter, Hood map, Open tasks).
Next: tracers from real barrel tip; hands w/ character_balaclava.glb; inspect anim; rifle anim (user pick M762 / MK18); CoD viewmodel clips.
Rules: no brands, no switch/auto-sear parts, CC0/CC-BY only, no secrets.
## Update 2026-10-23
- User: DON'T push git or notes yet (notes wiped, user redoing). Plan: Steam first (Unreal later), then Roblox port.
- Gun sound: BigSoundBank CC0 #0437 (Beretta M12 9mm) for pistol, #2853 rifle shot for rifle. URL https://bigsoundbank.com/UPLOAD/mp3/<id>.mp3.
  Mix: ffmpeg one input per shot, adelay=(20+3k)/60 s, atrim 0.35s, amix normalize=0 -> n19b/pistol_shooting_v2_sound.mp4.
- Map render running in background (scratchpad/map/out, log run.log).
- Hands v2: scratchpad/fps/fps2.py (args char_balaclava.glb pistol_drum_blank.glb outdir; env GUNPOS, SHOTS=fps,side,top,over, FULLBODY). Arms-only viewmodel (verts weighted to arm bones), hoodie logo removed (flat grey), trigger finger straight, curl toward palm normal.
  OPEN: left support hand still not wrapping the grip; gun still small in fps view.
- Sound fix: re-encoded pistol_with_sound.mp4 (yuv420p main, AAC 48k, faststart) + pistol_sound_only.mp3.
- Hands v3 OK-ish: run fps_hands.py with GUNPOS=-0.075,-0.43,-0.1 LHT=-0.045,-0.05,-0.062 LF=-0.7,-0.55,-0.1 RHT=0.02,-0.065,-0.025 (ONLY=R|L renders one arm). Fixed one hand at a time; R orient f=(0,-0.7,0.7) t=(0.2,-0.95,0.2).
- iPad: send videos as .webm (VP9+Opus); mp4 audio silent there.
- Rifle: sfx/2853 CC0 -> rifle_shot.mp3, rifle_burst.mp3 (8 rds ~700rpm). M762 glb import breaks mag (needs hierarchy flatten); MK18 ref png ok. User to pick.
- Mask decision: BALACLAVA ONLY (bandana dropped). Classic plain black knit (BalaclavaKnit mat, base 0.004, sheen 0.06), no logo. Hoodie plain grey-white (logo removed). Skin darker, matte.
  Rebuild: MASK=balaclava BALACLAVA=<uploads>/8a168f46-balaclava.glb blender ... char.py -- <hood.glb> <bandana.glb unused> <out>
- Rifle chosen: MK18 (game/assets/rifle_mk18.glb, flat colours, no logo textures). Next: animated fire with hands, rifle_burst sound.
- Balaclava eye hole narrowed: HOLE_UP=0.2 HOLE_DOWN=0.06 (brows to nose bridge), smooth blend by height.
- FINAL pistol clip: blender_workflow/fire_fps_pistol.py (hands env as v3) -> fin/frames; muzzle computed from front-most slide verts; arms parented to gun (rigid recoil). Then mux sound (22 shots, frame 20+3k @60fps) -> webm + baseline mp4.
- Character: black sweatpants (logo dropped), balaclava fits inside hood (PAD 1.1,1.08,1.04 + SIDE_TAPER 0.16 from y+0.06), hidden face skin deleted except eye window.
- Scale: character 6 ft (1.829 m). Pistol = Glock 17 length 0.202 m (GUN_LEN env; model was 0.128!). MK18: 10.3in barrel, OAL ~26.75in collapsed (0.68 m).
- Recoil v2: per-shot random kick <=0.1 ft (3.05 cm) x/up only, returns to centre; tracers aim at crosshair 30 m out. THIRD=1 FULLBODY=1 = side camera.
- TODO queue (user): pistol inspect anim; MK18 shooting (base pose+hands, then mechanics, NO spare mag shown); research real shooting/walk/run reference (YouTube/mocap) for animation.
- Motion reference saved: game/reference/motion_reference.md (vidIQ MCP video_watch works for analysing YouTube).
- STYLE: untrained hood shooters, not pro/military (see motion_reference.md).
- Rifle hold v1: blender_workflow/rifle_hold.py, env RHT=-0.15,-0.35,-0.35 LHT=2.25,0.4,0.3 LF=-0.6,-0.3,0.7 GUNPOS=-0.15,-0.1,-0.33 (THIRD=1 FULLBODY=1 for side). GRIP model (-1.75,0,-0.85), scale to 0.68 m, spare mag/rounds dropped.
- WEAPON SWAP: MK18 dropped -> Draco-style AK pistol (blender_workflow/make_draco.py from M762: stock cut, handguard shortened, new grip; 0.456 m). Hold: draco_hold.py env GUNPOS=-0.06,-0.3,-0.38 LHT=0.1,-0.1,0.04 LF=-0.9,-0.15,-0.2 (left hand cups under grip). Mini ARP = option from MK18 (cut stock/short barrel) later.
- HANDS: procedural rig + contact grip works (blender_workflow/hand_rig_drills.py, docs/hand_rig_lessons.md). Next: re-rig character glove with it, grip guns. Then YouTube research (maps/weapons/chars/cars/brass), then app Models tab (right-click comment to model, left-click edit, drag move).
- APP: new '3D models' tab (eclipse/src/Studio.tsx + nightcrew/studio3d.py): click part=edit props, drag part=move, drag empty=orbit, right-click=comment/Ask model (agent edits via headless Blender), Save writes .glb (+.bak). e2e verified with playwright. vidIQ credits used up.
- Hands v2: joint balls (knuckles), fingertip caps, exact glove-vertex collision (no phasing). Side video done (game/renders/pistol_side*).
- Draco clip: blender_workflow/fire_draco.py env GUNPOS=-0.06,-0.3,-0.33 LHT=0.1,-0.1,0.04 LF=-0.9,-0.15,-0.2 CAMAIM=0,-3,-0.5 -> dfin/frames (190f, 20 rds every 6f from 24). Sound: sfx/2853 per shot at (24+6k-1)/60 s. World-aligned Kick pivot drives recoil.
- Character hands now use hands_fix.py contact grip (Draco). Draco render v2 running -> fps/dfin2 (env GUNPOS=-0.03,-0.3,-0.36 LHT=0.09,-0.085,0.05 LF=-0.9,-0.2,0.1 CAMAIM=0,-3,-0.5).
- APP: 'Make model' in 3D models tab -> /api/model3d/create builds agent prompt (bpy expert layout, real sizes, preview render, auto-fix loop); Blender auto-detect + settings.blender_path; skill blender-game-assets updated with bpy rules + hand lessons.
- INSTALLER: packaging/eclipse.iss (Inno, installs to Desktop\Eclipse + desktop shortcut, optional Ollama via winget) built by .github/workflows/windows-installer.yml (PyInstaller onedir -> EclipseSetup.exe, published as release tag eclipse-latest).
- AUTO-UPDATE: updater.py (desktop.py calls first; compares version.txt sha vs release notes 'build: <sha>', silent reinstall + relaunch). One-line install: irm https://github.com/jokingtim2468-max/localai2.0/releases/download/eclipse-latest/install.ps1 | iex . Fixed Windows path separators in model list.
- Pistol hold (still): blender_workflow/pistol_hold.py env GUNPOS=-0.075,-0.43,-0.1 RHT=0.013,-0.045,-0.012 LHT=-0.03,-0.035,-0.045 LF=-0.7,-0.55,-0.1 (THIRD=1 FULLBODY=1 SHOTS=body,closeR,closeL | SHOTS=fps). Drum x3 (DRUM env), Glock 0.202 m, grasp_valve with straight=(1,) + index laid along frame. Note: hand targets are in gun-local units, so rescaling the gun needs them divided too.
- Pistol fire v4: blender_workflow/fire_pistol2.py = pistol_hold head (2-hand grip, drum x3) + fire_fps tail. Rendering -> fps/pfin/frames (170f). Sound: sfx/0437 at (20+3k-1)/60, 22 shots.
