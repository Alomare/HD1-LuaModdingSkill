# Stratagems

How stratagems work in HELLDIVERS (2015) and how mods add, hide, carry and sync them. Learned while building More Stratagems and Shared Resupply (github.com/Alomare/HD1-MoreStratagems, github.com/Alomare/HD1-SharedResupply); read their source for working examples.

## Contents

1. Data: LoadoutSettings
2. The Obsidian API calls
3. Menus: Arsenal and Loadout screen
4. Loadouts and the 8-slot limit
5. In mission: inventory, input, HUD
6. Cooldowns
7. Payloads
8. Icons
9. Checklist for a new stratagem

## 1. Data: LoadoutSettings

`lua/settings/loadout_settings.lua` (in a lifted copy) holds every stratagem in `LoadoutSettings.stratagems`, a list. An entry's position in that list is the stratagem id sent over the network.

| Field | Meaning |
| --- | --- |
| `name` | `stratagem_resupply`, `stratagem_tesla_tower`... |
| `stratagem_type` | `supply`, `defensive`, `offensive` or `special`. Menus accept only these four. `special` draws with the yellow gradient (mission stratagems) |
| `cooldown_time`, `activation_time` | seconds; activation is the call-in time |
| `num_uses` | missing means unlimited |
| `unit` | what the hellpod drops, such as `gameobjects/supplycrate_ammunition` |
| `icon` | a sub-material name in the HUD material |
| `combo` | the arrow code |
| upgrades | Mk2 and Mk3 entries named `<name>_mk2`, `<name>_mk3`, each overriding some fields at a cost |

Also in the file:

- `LoadoutSettings.static_stratagems`: the four always carried (metal detector, hellbomb, emergency beacon, reinforce). They are the first four entries of the list.
- `nr_of_stratagem_slots = 8`: 4 static plus 4 picked.
- `default_loadout` and `default_loadouts[i]`: the fallback loadouts. The statics are inserted at the front of these at module load.
- `find_stratagem(combo)`: returns the first entry whose code matches.
- `get_upgraded_settings(unit, level)` and `get_upgraded_stratagem(id, level)`: settings with upgrades applied. The crate's contents come from here.

## 2. The Obsidian API calls

Search the "Stratagems" section of `REFERENCE.md` for exact signatures. The main ones (API 1.40.0):

| Call | Use |
| --- | --- |
| `api.stratagems.define(def)` | A custom stratagem built on a game one (`base`), with a title, code, icon, type, stats, upgrades, unlock rule and `on_activate(ctx)`. Returns `nil, "not_ready"` before the game list exists: retry each frame |
| `hide(name, opts)` / `unhide` | Take a game stratagem out of the Arsenal, Loadout screen, default and saved loadouts and the mission inventory |
| `carry(name, opts)` / `uncarry` | Every player carries it in missions as an extra entry beyond the 8 slots |
| `share_cooldown(name)` / `unshare_cooldown` | One cooldown for the whole squad |
| `edit(name, field, value)` | Change a field of a game entry, undone when the mod stops |
| `give`, `call`, `drop`, `reset_cooldowns`, `refill_uses` | Actions in a mission |

`def.type = "special"` makes a custom stratagem yellow. `unlock = "manual"` keeps it out of the menus until a mod unlocks it. `upgrades = {}` removes Mk levels. When several stratagems share a code, the API makes the one the player holds and can use win, so a replacement can keep the vanilla code.

## 3. Menus: Arsenal and Loadout screen

- **Arsenal:** `MenuScreenArmoryUnlocks.on_enter` builds `self.available_items.stratagems.groups` (supply, defensive, offensive, special, locked; each with `.items`). Filter there.
- **Loadout screen:** `MenuScreenLoadout.setup_loadout(self, slot, ...)` builds the lists, but the screen reads them back from `self.option_menus[slot]`. Filtering `self.parent.players[slot].available_items` does nothing in game. This cost a release cycle: confirm which table a screen reads, not only which it writes.
- Both screens skip statics from the selectable lists.
- **Validation:** if a saved loadout holds a non-static stratagem the screen can't find, the game replaces the whole loadout with a copy of `default_loadout`. A mod that hides a stratagem must rewrite that entry in saved loadouts first, or players lose their loadouts.

## 4. Loadouts and the 8-slot limit

The menu, the lobby and the save all assume 8 slots. The hard limit is the lobby game object: `player_menu` has fields `stratagem5_index` to `stratagem8_index` only. A 5th static slot pushes picks to slot 9, which has no field. Also hardcoded: random loadouts (`for 5, 8`) and the proving grounds.

To give players more than 8, keep the saved and lobby loadout at 4 + 4 and add entries to the mission inventory when the player spawns (`api.stratagems.carry`). Everything in the mission counts entries instead of assuming 8.

## 5. In mission: inventory, input, HUD

- `InventoryComponent.set_loadout(self, unit, ctx, ...)` maps loadout names to ids into `ctx.state.stratagems`. Tutorial and NPC loadouts come through with no context. The "loadout" command calls `broadcast_stratagem_cooldown` right after, which sends every entry to the other machines.
- On respawn the game copies the old list back by index after `set_loadout`. Inserting an entry must keep indexes stable across respawns.
- Other machines build their copy only from `rpc_stratagem_info(unit, index, id, upgrade, cooldown)`, by index, through `command_slave("stratagem_cooldown")`.
- Input: the combo is matched against the whole `LoadoutSettings.stratagems` list, then `CharacterComponent.can_use_stratagem` checks the inventory. HD1 has no radial or d-pad selection, so input doesn't care how many entries there are.
- HUD (`lua/hud/hud.lua`): rows follow the inventory order with `ipairs`. An entry inserted right after the statics draws with the mission stratagems at the bottom of the list. A gap in the list stops `ipairs`.

Network widths that limit designs: slot index `uint4` (15 entries), id `uint7` (127 stratagems in the list), upgrade `uint4`, cooldown `uint10` (1023 seconds max).

## 6. Cooldowns

- `throw_stratagem` sets `cooldown_timer = cooldown_time * multiplier` when the flare is thrown; `InventoryComponent.update_masters` counts it down. Cancelling a flare resets it to 0.
- `cooldown_timer` is a protected key. Set it with the inventory command `set_stratagem_info { id, cooldown_timer }` then `broadcast_stratagem_cooldown`, the way `api.stratagems.reset_cooldowns` does.
- Cooldowns are per player; the game has no squad cooldown. A shared one (`share_cooldown`) watches every player's entry: a remote entry jumping from ready to a long time is a throw, and local players behind the squad are set to the squad's time. A gap of a few seconds before re-setting stops two machines echoing each other.
- Joining mid-mission: a new entry should take the squad's longest remaining time at once, separately from throw detection.

## 7. Payloads

- The hellpod drops `def.unit`. A supply crate lists the contents in `supply_crate_info.content` (the ammunition crate holds two `gameobjects/pickup_ammunitionbox_01` with offsets).
- `SupplyCrateComponent.setup_master` spawns the contents, on the thrower's machine only. Pickups are replicated game objects, so every player sees them.
- To change a payload for one stratagem only, swap the content list while the original `setup_master` runs and restore it after. Editing the shared settings table changes the vanilla stratagem too.
- Extra objects: `self.entity_spawner:spawn_entity(path, position, rotation, nil, setup_info)` on the master machine.

## 8. Icons

- Stratagem icons are sub-materials of `hud/hud` in bundle `95b2365a6369ee36`: 80x80 uncompressed BGRA textures.
- A mod ships a new texture and material as `resources` in `obsidian.json`, in the boot bundle `9cf71054ea26dddf`, and names them in `def.icon` and `def.icon_material`.
- `def.icon` is the name of the sub-material inside the material (the icon name the build script hashes into the material record), not the texture's resource name. A gui asked for a sub-material the material lacks stops the game, with no CRASH file, as soon as a screen draws the icon (the Arsenal, the drop). More Stratagems shipped this mistake once; a test that reads the names out of the build script catches it.
- `tools/build_icon.py` in More Stratagems and Shared Resupply reads the game's icon by name hash, edits the pixels with Pillow and writes the resource files plus a preview PNG. More Stratagems also builds icons from ready-made PNGs. Copy it and change only the drawing step.
- Mission (yellow) colour, sampled from the Hellbomb icon: RGB 187, 151, 75. When recolouring, keep near-white highlights white (the yellow icons keep them), or symbols such as the Resupply "+" disappear into the shapes.
- Always look at the preview next to a vanilla icon before shipping.

## 9. Checklist for a new stratagem

- [ ] Base stratagem chosen; stats and upgrades set on purpose (`upgrades = {}` for none)
- [ ] Code checked against every game code, or shared on purpose with a vanilla one
- [ ] Icon built and compared with vanilla icons
- [ ] Menus: shows where intended, hidden where not (Arsenal, Loadout screen, proving grounds)
- [ ] Saved and default loadouts survive the change
- [ ] Payload changes affect only this stratagem
- [ ] Other players: what they see if they run the mod, and in a lobby that isn't cleared
- [ ] Respawn, joining mid-mission and local co-op tested in game
