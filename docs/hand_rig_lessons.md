# Hands: how we got a working grip (drills)

Drills (blender_workflow/hand_rig_drills.py): 1) open -> fist, 2) grip a round stick, 3) grip a bumpy stick. Gun grip comes after.

## What was wrong with the Valve-biped character hands
- Bend direction was picked once per finger from a guessed palm side -> some joints bent BACKWARD.
- Finger bones are not connected and have arbitrary roll, so "rotate about the knuckle line" twisted joints (broken knuckles).
- Resetting fingers by world matrix in dict order stacked poses between drills -> use matrix_basis (local) to reset.

## The fix (procedural rig, following the bpy expert rules)
- Build the armature in EDIT mode: connected bones per phalanx (index.01.R ...), palm bone hand.R.
- eb.align_roll(palm_direction) so each bone's local Z points to the palm -> +X rotation ALWAYS curls forward.
  Thumb roll points across the palm toward the pinky side.
- LIMIT_ROTATION constraint (local): X only, 0..90 / 100 / 75 deg (knuckle / middle / tip), thumb 0..55. Cannot hyperextend.
- Weights: KDTree nearest bone segment with soft blend at joints; palm block forced 100% to hand.R (no stretching).
- Contact grip: curl joint by joint (knuckle first) in 2 deg steps; BVHTree.find_nearest on the object; stop the joint
  when a bone sample is inside the object or closer than flesh radius (9.5 mm). Works on smooth and bumpy surfaces.

## Round 2 fixes (user: knuckles broken, fingertips + thumb phased into the stick)
- Knuckles: fingers were plain cylinders butted against a box palm, so a bent joint opened a gap / hard corner.
  Now every joint has a ball mesh centred on the bone pivot (knuckle balls 18% wider) and each finger ends in a
  rounded tip; a ball rotates in place, so bent joints stay closed. Palm block subdivided + bigger bevel.
- Phasing: collision only sampled the bone centre line with one flesh radius, but the glove is thicker than that
  (thumb 11 mm) and the tip cap sticks out past the last bone. Now the test uses the real deformed glove vertices
  each step (each bone's own vertices, via the evaluated mesh) against the object's BVH, 0.8 mm margin.
  Nothing can pass through, whatever the finger thickness.

## Round 3: the character's own hands (user: "hands are still not fixed")
- The drill rig was only a test hand; the character still used the old Valve finger curl.
- blender_workflow/hands_fix.py ports the drill method to the Valve-biped glove (no re-skin needed):
  hinge per joint = bone direction x palm direction (palm side read from the rest curl of the middle finger),
  sign picked so the fingertip moves to the palm pocket, joint limits 90/100/75 (thumb 55),
  knuckle-first 2 deg steps, stop when that finger's deformed glove vertices touch the gun (BVH, 0.8 mm).
- Used by draco_hold.py and fire_draco.py (set OLDCURL=1 for the old behaviour). Support hand moved onto the mag.

## Round 4: two-hand pistol grip from real reference (guns.com / USCCA "5 key elements")
Reference: firing hand high on the backstrap, middle finger against the bottom of the trigger guard, lower three
fingers wrap, index straight on the frame off the trigger; support hand "handshake, rotate forward" fills the empty
left side of the grip, its four fingers wrap OVER the firing hand's knuckles, support thumb points forward along the
frame below the slide; firing thumb rests on the support hand. Avoid the "teacup" (support hand cupped underneath).
- hands_fix.grasp_valve(..., around="R"): the support hand also collides with the firing hand's deformed glove
  (BVH built from only that hand's vertices), so its fingers wrap over the knuckles instead of through them.
- pass_start=True: a finger that already touches at the start may slide until it is free, then stops on new contact
  (otherwise it never moves).
- point_finger(): lay the trigger finger and the support thumb straight along the gun's forward axis.
- Hand targets are in the gun's local units: when the gun is rescaled to real size, divide the targets too.
Settings: GUNPOS=-0.075,-0.43,-0.1 RHT=0.013,-0.045,-0.009 LHT=-0.05,-0.03,-0.008 LF=-0.5,-0.5,-0.7

## Next
- Re-rig the character's glove mesh with this bone layout (same roll + limits), then run the contact grip on the
  pistol grip and the Draco grip/handguard using the gun meshes as the BVH.
