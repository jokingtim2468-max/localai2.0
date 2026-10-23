# Motion reference (from YouTube via vidIQ video analysis)

## Pistol firing — "Glock Super Slow Mo Firing" (youtube.com/watch?v=ywVsPd6TR9U)
- Muzzle flash: conical orange-white, 10–15 cm forward, horizontal sparks.
- Slide stroke: 3–4 cm back; barrel tilts 3–5° at chamber end as slide opens.
- Brass: ejects up + slightly rearward to the right, 45–60° from vertical, fast tumble.
- Gun moves back into palm 1.5–2 cm; muzzle rise peak 12–15°; front sight up 4–5 cm.
- Slide returns while gun is near peak; wrists drive gun back to aim, <1° overshoot settle.
- Smoke: thin grey wisp from muzzle + port, drifting forward/up.
- GAME RULE (user): kick max 0.1 ft (3.05 cm) left/right/up, return to centre, rounds go to crosshair.

## Rifle stance — Jerry Miculek AR-15 pointers (youtube.com/watch?v=OPzZ5w1o56E)
- Feet shoulder width, lead (left) foot forward, knees soft.
- Torso leaned forward from hips ("nose over toes"), chest square, right shoulder pushed into stock.
- Head down, tight cheek weld on stock.
- Support hand fully forward on handguard, C-clamp (thumb over top rail), left elbow near straight, slightly out.
- Firing hand high on grip, trigger finger straight until firing, right elbow ~45° down (tucked).
- Recoil: rise under 2.5–5 cm, sharp short push into shoulder pocket, near-instant return to aim.

## Locomotion (walk/run with rifle)
- "Carlos Alexandre games" channel: rifle locomotion clips with FBX downloads, free for commercial game use, no resale
  (e.g. youtube.com/watch?v=mfOvPskoMAc). Biped rig → retarget to Valve biped.
- Alternatives: CMU mocap (free incl. commercial), Mixamo (Adobe login, royalty-free).

## STYLE DECISION: untrained street shooters, NOT pro/military
Use the real data above only for the physics (slide, brass, flash). Body/handling must look untrained:
- Stance: upright or leaning BACK, feet square/parallel, knees locked-ish; weight on heels.
- Pistol: loose grip, often one hand or weak support hand (thumbs crossed / cupping), elbows flared, sometimes slight cant.
- Rifle: support hand near magwell or mid-handguard (not C-clamp), stock low on shoulder/bicep, head upright (no cheek weld), firing elbow winged out.
- Recoil: still capped at 0.1 ft (3.05 cm) per shot (user rule), but slower, sloppier recovery with random wander between shots;
  trigger finger may rest inside the guard. No tactical reloads, no textbook ready positions.

## Draco (AK pistol) — youtube.com/watch?v=x_tIGjHMoN0
- Eye level, right arm near straight (165–170°), left hand cups under handguard, elbow 140–150° flared down.
- Recoil: 8–12° muzzle up + slight right per shot, gun punches back 5–7 cm, recovery 0.15–0.25 s.
- Flash: round star-burst fireball 10–20 cm. Brass: up/forward/right (1–2 o'clock).
## Mini AR pistol — youtube.com/watch?v=O16l9V3Wpq4
- Chest/chin level, not shouldered; right elbow 90–110° tucked, left arm forward 130–150°.
- Recoil: sharp 15–25° flip, up-right drift, fast snap down. Big orange fireball (short barrel). Brass 3–4 o'clock.
- GAME: still cap kick at 0.1 ft per user rule; untrained = sloppier return.

# Game research (YouTube via vidIQ)
## Competitor: OFF1700 Chicago (Roblox hood RP) — youtube.com/watch?v=ndGO0Fb-dIk
- Map: brick apartment blocks/projects, auto-repair garages with rollup doors, corner stores, gas station, chain-link lots,
  cracked asphalt, red-painted no-parking curbs, bus stops, trash piles, ATMs. Day/night cycle, neon at night.
- Cars: SUVs, 90s sedans, muscle sedans, city bikes; lock/unlock, trunk storage, P/R/N/D gears, speedo+fuel HUD.
- Guns: Glock, AR, Micro ARP, Draco w/ drum; over-shoulder aim, no fixed crosshair, smoke, brass, punchy audio, fast TTK.
  (WE DO NOT ADD switches/auto-sears — full-auto stays a game setting only.)
- Damage: bleeding + limb damage, bleed-out screen.
- Clothing: puffer vests, hoodies, denim, ski masks/balaclavas, hairstyles, tattoos.
- Economy: player trading, /pay, weight-based grid inventory (item grams), licenses for cars.
- HUD: clock/date/weather, cash/bank, job; health/armor/hunger/thirst/stamina/weight bars.
- Avoid: heads clipping car roofs, clunky gear shifting, floaty melee, cluttered chat feed.
## Tutorial leads
- Buildings: Ian Hubert "Lazy Tutorials" custom buildings (youtu.be/t_c58ryJ-Sw); geometry-nodes procedural buildings (rNXx_C5NqlE).
- Cars: low-poly car guides (ub00akPm7kQ Thomas Potter; 05RTwFttTE0 / OWN6huwRFro full blueprint workflow ~9–10k tris).
- Brass/FX: UE5 casing eject + bounce (W-GZTRWnLZY Infima), muzzle flash without sims (XUlfshL-LXM).
- FPS arms: Blender→engine viewmodel workflow (1cMAOa6UqMY tsitski), Roblox viewmodel in Blender (1AYMuNefJzY).
- Clothes: cloth sim for hoodies/jackets (WxA7kGmLCFI, aNJSb5S0ngw).
