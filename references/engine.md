# Engine and game-side knowledge

How HELLDIVERS (2015) is built, where the game's Lua lives, how to find the function to hook, and the traps that crash the game or get a player cut off. Facts come from reading the retail scripts of Steam build 6001293 and from live tests. Statements marked **(inferred)** are conclusions from reading, not confirmed in a running game.

Public references: [Obsidian Mod Manager](https://github.com/Alomare/ObsidianModManager) and [Obsidian API](https://github.com/Alomare/ObsidianAPI) (the `REFERENCE.md` there documents every call).

## Contents

1. [The engine and the scripts](#1-the-engine-and-the-scripts)
2. [How code gets into the game](#2-how-code-gets-into-the-game)
3. [Making your own lift of the scripts](#3-making-your-own-lift-of-the-scripts)
4. [Layout of the scripts](#4-layout-of-the-scripts)
5. [Language and global environment](#5-language-and-global-environment)
6. [Game states and screens](#6-game-states-and-screens)
7. [Entities, components, master and slave](#7-entities-components-master-and-slave)
8. [Settings tables](#8-settings-tables)
9. [Network limits](#9-network-limits)
10. [Protected keys](#10-protected-keys)
11. [How to find what to hook](#11-how-to-find-what-to-hook)
12. [Hooking in practice](#12-hooking-in-practice)
13. [Traps](#13-traps)

---

## 1. The engine and the scripts

| Fact | Detail |
|---|---|
| Engine | Bitsquid, which became Stingray. Resources live in hashed bundles under `contents\`. |
| Script VM | LuaJIT 2.0.3, embedded in the executable. |
| Executable | Not packed. No anti-cheat. |
| Game scripts | 890, all stripped LuaJIT 2.0 bytecode (no local names, no line numbers). Field names and global names survive. |
| Bundle `9e13b2414b41b842` | Gameplay: 725 scripts. |
| Bundle `9cf71054ea26dddf` | Boot and foundation: 165 scripts. Loads first and never unloads. |
| Debug console | Retail ships a dormant `DebugConsole`. Some console commands exist in `StateGame` and work when called from Lua. |

Resource names are hashed with 64-bit MurmurHash (variant 64A, seed 0) over the path string, for example `lua/hud/hud`. A bundle holds entries of (type hash, name hash, data). The type hash is the hash of the type word (`lua`, `unit`, `texture`, `material`, `package`, `level`, `font`, and so on). A Lua resource is an 8-byte header (length, kind) followed by the bytecode. Names are not stored: recover them by hashing path-like strings found inside the bundles and matching. Scripts whose path never appears as a string stay unnamed and show as `#<16 hex digits>`.

## 2. How code gets into the game

The engine probes `<bundle>.patch_0`, `<bundle>.patch_1`, and so on, next to each bundle in `contents\`.

- Probing stops at the first gap. If `patch_0` is missing, `patch_1` is never read.
- The highest patch number wins for a resource that exists in several.
- A patch can add resources that the base bundle never had (for example a new Lua script under `mods/yourname/main`).
- Mods never edit the game's own files. Obsidian writes the patches at deploy and removes them on purge.

A new script is reached by `require("mods/...")` once some existing script has been replaced to call it. The manager replaces a small boot script, which loads the loader, which runs mods. See the Obsidian wiki for the mod format.

Resources other than Lua (textures, fonts, materials) are replaced the same way. Replaced resources load when the game starts, so changing them needs a redeploy. Art for UI goes into the boot bundle because that bundle loads before anything runs and never unloads.

## 3. Making your own lift of the scripts

You cannot read the game's Lua directly, and the decompiled scripts are not distributed. Build a reading copy once per game build. Three steps:

1. **Read the bundles.** Bundles are chunked: a 12-byte header (version `0xF0000004`, total size, unknown), then chunks of up to 0x10000 bytes, each prefixed by a 4-byte length. A chunk whose length equals 0x10000 is stored raw, otherwise it is zlib. After decompression: entry count, a 256-byte property block, a table of (type, name) pairs, then per entry a record with version headers and the data.
2. **Dump the Lua resources** of the two script bundles to `.ljbc` files named by path (use the name table from section 1), unnamed ones by hash.
3. **Lift the bytecode to pseudo-Lua.** Write a LuaJIT 2.0 bytecode reader (dump version 1) and print each prototype as source: registers folded into expressions, `self.f(self, x)` printed as `self:f(x)`, numeric and generic `for` loops rebuilt, other control flow left as labels and `goto`. Also write an index of every named function (`file: function Class.method(args)`) so you can grep it.

What the lifted text looks like, and what it means:

- The output is for reading. It does not recompile.
- Locals and upvalues are anonymous: expect `a0, a1`, `r4`, `L7` labels. Field and method names are real.
- Table constructors print as repeated literals, for example `({ align = "left" }).id = a0`. Read them as one table being filled.
- A lifter can miss patterns (rare opcodes, odd loops). When a function reads wrong, check the raw bytecode listing before trusting it, and mark such facts as medium confidence.

Tools worth writing for yourself:

| Tool | Purpose |
|---|---|
| Bundle reader | Parse and decompress bundles, list entries by type. |
| Name builder | Hash path-like strings from every bundle to name resources. |
| Bytecode dumper and lifter | Steps 2 and 3 above. |
| Bytecode assembler | Emit tiny stripped LuaJIT 2.0 chunks by hand, to test what the engine accepts (for example whether `loadstring` of source works, see section 5). |
| Patch builder | Write a `.patch_N` bundle with a replaced or added Lua resource, to test deploy behaviour. |
| Bundle diff | Compare two builds: list changed, added and removed resources. Run it after each game update to see what a mod may break on. |
| String cross-reference | Find which scripts contain a string or name, and check names against the executable. |

Tag each finding with a confidence: high (read directly), medium (code read, lifter or engine behaviour involved), low (inference). Verify medium and low in the running game before shipping.

## 4. Layout of the scripts

A lift has this shape:

```
lua/
  components/        one file per component (inventory, stratagem, health, ...)
  character_states/  enemy_states/  vehicle_states/
  states/            StateGame, StateMenu, StateMainMenu, StateMissionStart ...
  menu/              menu_screen_*.lua, one class per screen
  hud/               hud.lua and the HUD widgets
  gui/               hd_gui.lua and gui helpers
  managers/          campaign, encounter, mission, spawn, camera, message ...
  settings/          the settings tables (loadout, perk, game, difficulty, ...)
  network/           network_global.lua, network_room.lua
  widgets/           text_chat and other widgets
  generated/         network_messages, game_object_fields_lookup,
                     network_object_types, settings_paths, unit_paths, ...
gameobjects/         one script per replicated game object (airstrike_01, ...)
gameobjects_spec/    level object specs
foundation/lua/      base (class), component, network, util, gui, world ...
#<hash>.lua          scripts whose name could not be recovered
```

Notes:

- Some of the most important classes are unnamed. Examples from build 6001293: InventoryComponent, ExosuitInventoryComponent, EntityAux, ComponentManager, EntityManager, DistributedBaseComponent, StateMachine, GameObject, LuaSettingsManager, `protect()`, the boot script. Find them by class name in the function index, not by file name.
- The boot script defines the globals `init`, `update`, `render` and `shutdown`.
- `lua/generated/*` files are tables generated at build time. They are the fastest way to answer "what can the network carry" and "which fields does this game object have".
- A script keeps the same hash name between builds unless the name changes. After a game update, diff the builds before trusting old notes.

## 5. Language and global environment

| Behaviour | Result |
|---|---|
| `loadstring(bytecode)` | Works. |
| `loadstring(source)` | Silently returns nothing. The source parser is disabled in retail. |
| `loadfile`, `load` | `nil`. |
| `dofile`, `io`, `os` | Work. |
| Language | LuaJIT 2.0, Lua 5.1 semantics. |

Consequence: every script must be stripped LuaJIT 2.0 bytecode. The manager compiles mods at deploy. Do not try to `loadstring` text at runtime.

Strict globals. `foundation_setup` requires `foundation/lua/util/strict` before the build info. `_G` has a metatable: `__newindex` allows new globals only from a main chunk or from C, and `__index` errors on a read of an undeclared global. Use `rawget(_G, "name")` and `rawset(_G, "name", v)` for globals that may not exist yet.

Other facts:

- `_G.ARGUMENTS` is filled from `Application.argv` before build info, so it exists when a loader runs. `Boot.arguments` is built from it later.
- The global `update` is defined by the boot script after the loader runs. To get a per-frame callback, chain `getmetatable(_G).__newindex`: when the key is `"update"`, wrap the function, then `rawset` it. (The Obsidian loader does this; mods use `obsidian.on_frame`.)
- `jit` may not be reachable from `_G` at boot: use `rawget(_G, "jit")` and check **(inferred, unverified live)**.
- Game vectors, quaternions and similar values last one frame. One kept in a variable and read later comes back as NaN. Copy the numbers, or use a box (Obsidian API has `api.game.box`).
- Language: `LocalizationManager.current_language` holds `en`, `fr`, `es`, `bp` (Brazilian Portuguese); other languages fall back to `en`.
- Keys: `Keyboard.button_index(name)` and `Keyboard.pressed(index)`.
- Wrap every call a mod makes into the game with `pcall`. A Lua error inside a game update freezes the game and writes a CRASH file.

## 6. Game states and screens

The state machine is `Boot.state_machine`. `Boot.state_machine:get_current_state()` returns the live state and `get_current_state_name()` returns a name such as `"game"` (a mission) or `"menu"` (the ship).

| State | Role |
|---|---|
| `StateLogos`, intro cutscene | Start up. `Boot.arguments.skip_splash` skips both. |
| `StateMainMenu` | Title and login, network setup (`LOGIN`, `BACKEND`, `CAMPAIGN`, `DONE`). |
| `StateMenu` | The ship: campaign, loadout, armory. Opens screens by name. |
| `StateMissionStart` | Dropship and drop. |
| `StateGame` | The mission. Owns `entity_spawner`, `entity_manager`, `component_manager`, `encounter_manager`, `patrol_manager`, `spawn_manager`. |
| `StateMissionEnd`, season end state | Results. The season end writes the save. |
| `StateTutorial` | Tutorial. |

Frame order in `StateGame.pre_update`: `entity_spawner:pre_update`, `component_manager:pre_update`, on the host `encounter_manager:update`, `patrol_manager:update_host`, `wave_manager:update`, then `spawn_manager:update` on every peer.

Menu screens are classes in `lua/menu/menu_screen_*.lua`: `MenuScreenLoadout`, `MenuScreenArmory`, `MenuScreenArmoryUnlocks`, `MenuScreenCampaignPlanet`, `MenuScreenCampaignMission`, and so on. They share `MenuScreenBase`. Methods named `update`, `draw_*`, `setup_*` and `on_*` are the usual hook points.

HUD: `lua/hud/hud.lua` plus widgets in the same folder. The HUD is built from tables describing containers, images and text (`type = "container"`, `bg_img`, `bg_color`, `size`, `position`, `layout`, `children`) and a CSS-like defaults file (`default_css`).

Gui facts for UI mods:

- A `Gui` is made on a world. Each state has a separate world, so a gui outlives a state change only if it is made on a world that does.
- A gui that lists a material not loaded on this screen can stop the game. For example `menu/menu` is loaded only on the ship.
- Gui coordinates are DPI-virtualized. Lay out in a fixed virtual space (for example 1920x1080) and scale by the window and the player's UI scale. Every state calls `viewport:limit_aspect_ratio(GameSettings.min_aspect_ratio, GameSettings.max_aspect_ratio)`, which letterboxes wide screens.
- The game tests the mouse against where it would have drawn each element. A mod that redraws a screen has to map the positions of the elements it draws to the rectangles the game tests, or clicks land on the wrong thing.
- A mod that replaces what a screen draws should still let the screen's `update` run. The update holds input handling, network sync and writes to the save. Cut only the drawing.

## 7. Entities, components, master and slave

A mission object (player avatar, enemy, crate, stratagem beacon, vehicle) is an entity: a unit plus a set of components. Components live in `lua/components/` (`CharacterComponent`, `HealthComponent`, `InventoryComponent`, `StratagemComponent`, `SupplyCrateComponent`, `FirearmComponent`, `EnemyComponent`, `NavmeshMoverComponent`, and about seventy more).

Every entity has one owner machine. Components therefore have two halves:

| Half | Runs on | Typical functions |
|---|---|---|
| Master | The owner only | `setup_master`, `update_masters`, `command_master`, `remove_master` |
| Slave | Every machine, the owner included | `setup_slave`, `update_slaves`, `command_slave`, `remove_slave` |

Rules that follow:

- AI, damage resolution and ammo run on the master. A change made on a non-owner does nothing to the master.
- State access: `EntityAux.state(unit, component)` is the slave state. `EntityAux.state_master(unit, component)` is the master state, available on the owner only.
- Commands: `EntityAux.queue_command_master(unit, component, command, ...)` asserts if this machine does not own the unit. `EntityAux.queue_command(...)` picks master or slave. A command name that the component's `command_master` does not know stops the game, outside any `pcall`.
- Lists: `entity_manager:get_master_entities(name)` and `get_slave_entities(name)` return unit-to-state maps. `all_masters_iterator(name)` and `all_slaves_iterator(name)` iterate them. There is no `get_entities_with_component`. Check `Unit.alive` before use because the lists can hold units already gone.
- Ownership moves. `BaseComponent.migrated_to_me` runs `setup_master` again on the new owner, with that owner's settings. Enemies are spread across peers (`EncounterManager.get_spawner_peer`), so in co-op the host does not own every enemy and host-only edits miss client-owned ones.
- Replicated fields live on game objects (section 9). Fields marked local, such as `alive_time`, do not replicate.
- Settings are per machine. An edit to a settings table affects that peer only. For stats that must agree in co-op, every player needs the same edit.
- Functions named `rpc_*` on components and states are the receiving side of a network message.

Spawning: `entity_spawner:spawn_entity(path, position, rotation, nil, setup_info)` spawns a replicated game object. `setup_info` is handed to each component's `setup_master`. Pickups, crates and vehicles accept `nil` or `{}`. `entity_spawner:despawn_entity(unit)` only marks the unit, which dies at the next `pre_update` or `post_update`, so despawning inside a loop is safe. For a real stratagem drop, go through `StratagemComponent`, which picks the hellpod and the `setup_info`.

## 8. Settings tables

Gameplay numbers live in tables under `lua/settings/`, `require`d once and shared:

| Table | Holds |
|---|---|
| `LoadoutSettings` | Stratagems (`name`, `combo`, `cooldown_time`, `activation_time`, `num_uses`, `unit`, `upgrades[]`), weapons, perks, slot counts (`nr_of_stratagem_slots` is 8, the first 4 are static). |
| `PerkSettings` | Perk definitions and their setup and remove functions. |
| `GameSettings` | Global caps (`MAX_NUM_ALLOWED_ENEMIES`, aspect ratios). |
| `StatusTemplateSettings` | Status effects (stun, slow). |
| `EncounterSettings*`, `PatrolSettings`, difficulty settings | Waves, patrols and difficulty curves. |
| `weapon_info`, `character_info`, `health_info` | Per-unit values read by components at setup. |
| `LuaSettingsManager` | Loads per-unit settings by unit path. |

Traps:

- Tables are shared across missions and menus. A patch persists and shows in menus. Save the original and restore it.
- `LoadoutSettings.get_upgraded_settings` and the upgrade code clone a definition per upgrade level with overrides. Patching a base value misses a field an upgrade sets for itself (a hellbomb `activation_time` is one). Patch every level.
- A weapon keeps a separate copy of the settings for each upgrade level. A write to the base table does not reach the copies.
- Settings are read at setup. Changing a table after an entity was set up does not change that entity. Patch before the spawn, or edit the live state.
- `setup_master` and `setup_slave` both read the settings, each on the machine that runs it.

## 9. Network limits

`lua/generated/network_messages.lua` lists every rpc and the parameter types of each with bit widths:

```lua
({}).rpc_stratagem_info     = { "unit", "uint4", "uint7", "uint4", "uint10" }
({}).rpc_activate_stratagem = { "position", "uint7", "uint4", "unit" }
```

`lua/generated/game_object_fields_lookup.lua` lists the replicated fields of each game object type, with a fixed index:

```lua
({})["player_menu"] = { avatar_unit = 3, favorite_loadout_index = 7, index = 4, ...,
  stratagem5_index = 11, stratagem6_index = 12, stratagem7_index = 13, stratagem8_index = 14, ... }
```

`lua/settings/network_object_settings.lua` and `lua/generated/network_object_types.lua` bind objects to types.

These are hard limits. A Lua mod cannot change them, because both sides must agree and the widths are fixed in the game's data.

| Limit | Consequence |
|---|---|
| `uint4` slot in `rpc_stratagem_info` | At most 16 values for that field. |
| `uint7` and `uint10` ids | An id above 127 or 1023 does not fit. |
| Lobby `player_menu` has only `stratagem5..8_index` | The lobby syncs four chosen stratagem slots beyond the static four. |
| Unknown rpc name or a wrong parameter list | An error inside the game's network code. |

Design rules:

- Before designing anything that syncs, read the message types and the object fields. If the value does not fit, keep it local (a client mod) or derive it on every machine from data that does sync.
- A custom stratagem is always the base stratagem it was built from on the network. Whatever it calls down has to be a unit that every game has.
- Anything only one machine knows (an edited table, a unit that is not a replicated game object) is invisible to the others. Spawning a unit whose package other peers have not loaded can crash them.
- Vanilla rpcs such as `rpc_spawn_enemy_unit_request` and `rpc_set_hitpoints_request` check ownership but not authority. Do not use them against other players' sessions.
- XP, rank and mission stats reach the shared backend through `CampaignManager` entry points (`upload_mission_stats`, `upload_leaderboard_stats`, `complete_planets`, and others). Obsidian blocks these while session mods run. Do not design a mod that changes them.

## 10. Protected keys

Components register protected keys. `BaseComponent.set_protected` stores a salted hash next to the value, and `check_protected` fires `on_fusk_detected` when the field and the hash disagree. A raw write is caught at the next legitimate update. The result: the game leaves the lobby and stubs the network, and the player stays cut off until they restart.

| Component | Protected keys |
|---|---|
| health | `hitpoints_real`, `armor_min`, `armor_max` |
| mover | `wanted_move_speed` |
| inventory | `num_grenades`, stratagem `cooldown_timer`, `uses_left` |
| firearm, flameweapon | `rounds`, `num_mags`, `reload_time`, `magazine_capacity` |
| throwable weapon | `num_mags` |
| player record | `extra_lives` |
| objectives | `time_elapsed`, `defend_timer`, `enemies_killed`, `enemies_to_kill`, `current_wave` |

Not protected: launcher, beam, arc and melee ammo; shield; `sprint_stamina`; `max_hitpoints`; `slow_*` fields.

Rule: write a protected key only through the game's own command (for example `EntityAux.queue_command_master(unit, "health", "set_hitpoints", n)`, the inventory cooldown commands, `set_extra_lives`) or through `api.game.protected` in Obsidian API. Never assign `state.hitpoints_real = n`.

A timer that the game runs while it is above zero never finishes at 0 (a hellpod `drop_time`). Use 0.01.

## 11. How to find what to hook

A repeatable method. Run it on your own lift.

1. **Start from something the player sees or a name in the game.** Search the lifted scripts for a string: a stratagem name, a button label, an rpc name, a settings key, a message. Use the function index to list a class's methods.
2. **Find the class and the method.** Hooks attach to a class table and a method name (`MenuScreenLoadout.update`, `HealthComponent.do_damage`). Confirm the table is a global or a required module that exists when your mod loads. Functions called through locals (`local function begin_x()`) cannot be hooked: hook the public caller. Example: the `begin_*` upload functions are reached through locals, so hooking them never fires, while the public `CampaignManager.upload_mission_stats` does.
3. **Read both halves.** For a component, read `setup_master`, `update_masters`, `command_master` and the slave counterparts. A change must go where the data is read, on the machine that reads it.
4. **Check who calls it, and on which machine.** Grep for the method name across all scripts. Note whether the caller runs on the owner, the host or every peer. Host-only code (encounters, objectives, mission end) does nothing on a client.
5. **Confirm which table the game reads back, not only which one it writes.** A screen may build a list in one place and read another. `MenuScreenLoadout` builds from `self.parent.players[slot].available_items` but reads `self.option_menus[slot]`, so editing the first changes nothing. Grep for every read of the field you plan to change.
6. **Check the network types** for any value that has to sync (section 9) before you write code.
7. **Look for a guard.** Search the same function for `check_protected`, `set_protected`, asserts and `Unit.alive`. A guard shows which writes the game defends.
8. **Look for an existing path.** The game's tutorial and debug commands often do what you need (the tutorial pauses components and forces a loadout with `loadout_override`). Reusing the game's own call is safer than writing state.
9. **Test in the game.** Static reading gives medium confidence at best. Log from the hook first (`obsidian.log`), watch the call order, then change behaviour.

Search aids:

| Looking for | Search |
|---|---|
| An rpc sender or receiver | The rpc name, and the same name in `generated/network_messages`. |
| A tunable number | The field name in `lua/settings/`, then every file that reads it. |
| A screen | `menu_screen_<name>` and the `setup_*` and `update` methods of the class. |
| A component command | `command_master` in that component's file; the table of names is the full list. |
| A game object's fields | `game_object_fields_lookup` by object name. |
| A unit path | `generated/unit_paths` and `units_with_settings`. |
| What a hash-named script is | The class name in the function index (`Class.method`). |

## 12. Hooking in practice

Obsidian exposes `obsidian.hook(target, method, fn)` and `obsidian.on_require(name, fn)`. Behaviour of the loader's hook, from the loader source:

- `target` is a table or a global name. If the class or method does not exist yet, the hook waits and installs when it does.
- `fn` receives the original function first, then the call arguments. Call the original to keep the game's behaviour.
- If the hook throws before calling the original, the loader calls the original for you. If it throws after the original ran, the loader returns the original's results and does not run it again, so a spawn or a save never happens twice.
- Session mods are gated: while the lobby is not cleared, the hook calls the original untouched. Client mods are not gated.
- `obsidian.on_require(name, fn)` runs `fn(module)` when the game first requires a script, for example `settings/game_settings`. It is the place to patch settings tables once they load.
- Use `obsidian.on_frame` for per-frame work. The loader runs each callback under `pcall`.

Keep hooks on hot functions cheap. Create one closure per hook and not one per call, because a new closure on each call stops the JIT from compiling the path.

Known hook points (build 6001293):

| Goal | Hook |
|---|---|
| Per-frame | Global `update` (the loader wraps it). |
| Skip intro | Set `ARGUMENTS.skip_splash = true` at boot. |
| Skip login, online | In `StateMainMenu`, when the menu shows at network state `LOGIN`: set `wants_exit`, `wanted_state = "menu"`, `exit_timer = 0`, `backend_type = "STEAM"`, then prepare `"menu"`. Setting `ARGUMENTS.autohost` instead picks a LAN backend and the game stays offline. |
| Chat text | `TextChat.update` (capture the instance). `rpc_text_chat` renders `"<name>: <message>"`. |
| Lobby members | The lobby wrapper: `members()`, `member_data(peer, key)`, `set_member_data(key, value)`, `my_id`. |
| Bot input | A hook on `InputComponent.update_masters`, because vectors only live in the frame. |
| Widescreen | Raise `GameSettings.max_aspect_ratio` in `on_require("settings/game_settings", ...)` **(inferred)**. |
| Planet scan skip | After `MenuScreenCampaignPlanet:setup_planets`, mark every planet `is_scanned` and move `planet_scanning_state` to the last step **(inferred)**. |

## 13. Traps

Crashes and freezes:

- **A Lua error in a game update freezes the game** and writes a CRASH file. Wrap your own code in `pcall`.
- **An unknown queued command name stops the game** inside the game's update, where no `pcall` reaches. Add a command to your list only after reading that component's `command_master`.
- **Spawning a unit whose package is not loaded stops the game.** Weapon units are not loaded on the ship: spawning one there kills the process.
- **A wrong type in an input table** (a boolean `fire_button` where a number is expected) errors inside `input_component.lua`. Take field types from `ControllerSettings`.
- **A made-up pad number** crashes the input code. A bare unit with no pad (nil) stands still.
- **A gui that lists an unloaded material** can stop the game (`menu/menu` outside the ship).
- **Sound worlds die with their screen.** Asking a gone world about a sound id took the game down in testing. Keep a sound id only for the screen that made it.
- **A status command on a non-owned unit** can error, because `filter_slave_command` reads an undefined global. Use a zero-damage hit, which is the path weapons use.
- **Camera particles** may be loaded only for their own biome. Spawning an unloaded particle can crash **(inferred)**.
- Fortify objectives call `time_keeper:set_paused` without a check. A fortify mission started with no proving-grounds seed can crash **(inferred)**.

Silent failures and wrong results:

- **Wrong table.** The screen reads a different table from the one it builds (section 11, step 5). Always find the read.
- **Settings patched too late, or at one level.** See section 8.
- **Vectors stored across frames** read as NaN.
- **Strict globals.** A bare read of a global that does not exist raises an error.
- **Perk swaps** skip the old perk's `remove_master` and `remove_slave`, so old effects stay on **(inferred from reading)**.
- **Shared state edited on one peer** desyncs or gets overwritten when ownership migrates.

Save and backend:

- `StateMenu` calls `CampaignManager:upload_mission_stats(queue)` and then `SaveManager:set("mission_stats_to_upload", queue)` with the same table. Emptying the table in a hook drops the queue for good.
- Queues live in the save. A mission finished with a session mod, followed by a crash or an offline exit before the next menu tick, can leave results in the save, and the next run without session mods uploads them.
- A test harness should skip every save call and run as a session mod, so Obsidian holds back Galactic War and leaderboard uploads.
- Paid content stays paid. Items go through the DLC check (`lua/settings/dlc_settings.lua`).

Scope reminder: a mod that only reads game tables and draws locally can be a client mod and works with players who do not have it. A mod that changes shared game state must be a session mod, and only runs while everyone in the lobby has agreed (Obsidian's scopes documentation has the rules).
