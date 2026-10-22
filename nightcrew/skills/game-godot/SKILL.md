---
name: game-godot
description: Godot 4 games in GDScript
domain: godot
triggers: [godot, gdscript, tscn, game, platformer]
---
- Headless check: `godot --headless --check-only --script res://player.gd`; run: `godot --path .`.
- Movement (CharacterBody2D): `velocity.x = Input.get_axis("ui_left","ui_right") * SPEED; velocity.y += gravity * delta; move_and_slide()`.
- Use signals for UI updates; @export for tweakable values; physics in _physics_process.
