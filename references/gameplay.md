# Weapons, enemies and the camera

Gameplay rules that camera mods and balance mods run into. The facts come from the game scripts (Steam build 6001293). The examples come from Integrated Third Person (github.com/Alomare/HD1-IntegratedThirdPerson), a third person camera built from hooks alone, with no game script replaced. Approaches marked **(unproven in game)** come from that mod and haven't run in the game yet.

## Contents

1. The camera frustum is gameplay
2. A third person camera
3. Weapon range and aim
4. Enemy detection and patrols
5. A change for one call only

## 1. The camera frustum is gameplay

`CameraManager:is_position_inside_frustum(position)` asks whether a point is on the screen of the top-down camera. Gameplay code asks it in many places:

- Patrol alarms: `EnemyUtility.check_alert` raises the alarm only while the enemy is inside the frustum (section 4).
- Patrol spawn and the despawn of patrols off screen (`patrol_manager`). Enemy spawns placed off screen (`spawn_manager`, with `get_closest_position_outside_frustum`).
- Escort NPCs left off screen die (`npc_escort_component`).
- The squad leash and `mover_state.is_inside_screen` (`mover_component`). The timer that kills a downed player off screen reads that flag (`character_component`), and so does getting up after being downed.
- The respawn wait (`state_game`), several enemy states, and the HUD markers (`Hud.draw_plugins` in `hud.lua`).

A mod that moves the drawn camera moves all of these with it, unless the frustum keeps answering for the top-down view. Integrated Third Person lets `CameraManager.update` run every frame, so `CameraManager.position`, `.rotation` and `.fov` keep the top-down pose, and sets the shoulder view on the drawn camera after that update. The frustum calls, `ViewportProxy.world_to_viewport` and `ViewportProxy.screen_to_world` then answer for the top-down pose, worked out in Lua from those three fields. Only `Hud.draw_plugins` gets the drawn view, so markers follow what the player sees **(unproven in game)**.

Code that reads `CameraManager.position` keeps working the same way: `get_position` (respawn, spawn info) and `get_ground_position` (NPCs, the UAV drone).

## 2. A third person camera

- Set the drawn camera after `CameraManager.update`: `Camera.set_local_position`, `Camera.set_local_rotation`, `Camera.set_vertical_fov`, and `Camera.set_near_range` (0.05 for a close shoulder view), then `World.update_unit` on the camera unit. Move the scatter observer (`ScatterSystem.move_observer`) and the sound listener (`TimpaniWorld.set_listener` with `Matrix4x4.from_quaternion_position`) along with it.
- `CameraManager.follow_spin` turns the movement input of the top-down view. Obsidian API bots and the squad leash read it in the same update, so leave the value alone and turn the input of the local player instead: `mover`/`set_movement` and `character`/`input` in `InputComponent.queue_command_master`. Vehicles read movement back through `follow_spin` (`vehicle_component`), so give the value the view direction only while `VehicleComponent.update_masters` runs, and only when the vehicle of the local player is the only vehicle master on this machine.
- `CameraManager:world_to_screen` projects a point behind the camera onto the screen, mirrored. Answer an off-screen position for a point at depth 0 or less, or names and markers show in front.
- The game adds camera shake to the top-down pose only.
- `Mouse.axis(Mouse.axis_index("mouse"))` is the mouse movement in the frame. Photo Mode steers a free camera with it.
- A longer view: `Camera.set_far_range`, the fog of the planet pushed out with `api.world.shading("fog_depth_range", "vector2", ...)`, and model detail through `api.world.detail` (`rendering.md` section 1). Past the level the game draws nothing; the sky fix is in `rendering.md` section 2.
- Step aside when another camera takes over: `api.world.camera.taken()` (Photo Mode, the Trainer), a camera state other than `follow` or `follow_menu`, a dead player (the game then shows the squad from above), or a second local player on a controller, who shares the screen.

## 3. Weapon range and aim

- Weapon components copy `weapon_info.range` into `state.range` at setup. Firearms take 20 when the settings have none. A write to the settings after setup doesn't reach a weapon already set up.
- **Firearms cast a fixed 100 m ray for every shot.** `state.range` only sets a dip: `WeaponUtility.get_random_spread` takes muzzle height / (range x `range_multiplier`) off the z of the shot direction, so a shot from the muzzle meets the ground at the range. The dip doesn't show from above. From behind the shoulder, shots at a target past the range fall short.
- Firearms take the commands `set_range_multiplier` and `reset_range_multiplier` (`FirearmComponent.command_master`).
- Beams cast a ray exactly `state.range` long. Launchers copy `range` and `z_direction` from the settings at setup and dip like firearms. A laser sight draws to `state.range`, lowered by 1.5 / range. Flame and arc weapons have separate reach settings.
- Weapon direction: the weapon updates ask `Quaternion.forward(Unit.world_rotation(wielder, attach_node))`. Integrated Third Person swaps `Quaternion.forward` with `rawset` while the weapon update of the local player runs, and answers the crosshair direction for that one rotation, matched by value **(unproven in game)**.
- Throws: the grenade and stratagem throw states measure the charge from `CameraManager:screen_to_world` at the cursor (distance squared x 0.015, full at about 8 m). Answer the aim point there and throws land at the crosshair **(unproven in game)**.

## 4. Enemy detection and patrols

- `EnemyComponent.update_target` keeps the players inside `enemy_info.aggro_range` in the aggro table: 80 m for most enemies, 90 m for a few. An enemy that isn't on patrol chases the strongest target there.
- A patrol looks only within `enemy_info.patrol_range`: 10 to 16 m, mostly 12 or 13, and half of that while the target dodges. `EnemyUtility.check_alert` raises the alarm, which calls reinforcements, when the closest player is inside that range, in sight, and the patrol is inside the camera frustum. Otherwise it casts the sight ray `state.can_see_closest_target_raycast` as long as `patrol_range` and sets `state.waiting_for_see_closest_target_raycast` until the answer comes.
- `EnemyUtility.wander` walks a patrol toward `state.closest_target_unit` while `state.can_see_closest_target` is set.
- A longer sight ray cast before `wander` therefore makes a patrol walk toward a player farther away, while the alarm still needs the player inside `patrol_range`. Integrated Third Person casts the same ray out to 80 m, at most every 0.25 s per patrol **(unproven in game)**.

## 5. A change for one call only

A value changed only while one game call runs, and put back right after, leaves nothing behind: the game never keeps the changed value, and when the hook of a session mod stops, nothing needs undoing in `obsidian.on_session`.

```lua
local function with_range(state, fn, ...)
  local range = state.range
  state.range = 100
  local results = { pcall(fn, ...) }
  state.range = range
  if not results[1] then error(results[2], 0) end
  return unpack(results, 2, table.maxn(results))
end

obsidian.hook("LauncherComponent", "do_fire", function(original, self, unit, state, ...)
  return with_range(state, original, self, unit, state, ...)
end)
```

- Put the value back when the call fails too, then raise the error again. The loader sees that the original already ran and doesn't run the original a second time.
- A settings table shared by every enemy of a type can't change for one enemy. Hand the call a shadow table instead: `setmetatable({ enemy_info = setmetatable({ aggro_range = 150 }, { __index = info }) }, { __index = settings })`, set in `context.settings` for the call and taken out after. Keep one shadow per settings table in a weak-keyed cache, so a frame makes no new tables.
- Engine functions can be swapped the same way, with `rawset` on the table for the length of the call: `Quaternion.forward` for aim (section 3), `Gui.bitmap_uv` to drop one image the game draws (`ui.md` section 6).
- `stratagems.md` section 7 uses the same pattern for payloads.
