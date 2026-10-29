# New direction (2026-10-29): Roblox motorcycle game
The hood shooter is paused. We now build a **Roblox** (not Steam) motorcycle riding game in the style of the
Roblox game "Wide Open": open-world bike riding, wheelies, cutting up through traffic, police chases.
We copy the *genre and game-mode ideas*, not their assets, name, code, logos or UI art.

## Game modes / server settings (per map)
- Chase ON / OFF (police AI or cop players chase you; turbo escapes).
- Points: wheelies only / cutting up only (near-miss weaving through traffic) / both.
- Several maps, each with its own preset of these settings.
- Bikes: superbike classes (1000cc superbike, 600cc supersport, hyperbike, etc.) with modifications
  (exhaust, tune, stance, wheels, colours) and the same kind of mod animations.

## Asset rules (unchanged)
- No real brands or logos in-game (no BMW roundel, no "M" stripes, no model names). Rename bikes.
- Licence check every model: CC0 / CC-BY only for a game that earns Robux. NC (non-commercial) = reference only.
- Roblox limits: a MeshPart max 20,000 triangles; split a bike into parts (frame, fairings, wheels, fork, swingarm,
  handlebars, exhaust) so wheels/fork/suspension can move; textures 1024px.

## Model workflow (use for EVERY new 3D model from now on)
1. Find reference images of the thing from BOTH sides (left + right).
2. From those, make/predict the top, bottom, front and back views (6-view reference sheet).
3. If no images show it, combine the images you have into the 3D model directly.
4. Build the model, then render the same 6 orthographic views (blender_workflow/views6.py) and compare with the
   references; fix, re-render, repeat until they match.
