# Game modes and expansions

How to build a mode that stands apart from the campaign, from Helldivers Arcade (github.com/Alomare/HD1-HelldiversArcade), a survivors-style mode shipped as an Obsidian expansion. "Checked" means seen in the running game, Steam build 6001293. Read `obsidian-mods.md` (scopes, `wrap` versus `hook`) and `multiplayer.md` first.

## Contents

1. The expansion shape
2. Starting a mission of the mode
3. The map
4. Keeping the campaign untouched
5. Pausing, time and freezing
6. Lobby sync for a mode
7. What the game allows

## 1. The expansion shape

- `"scope": "expansion"`, `min_obsidian` 1.2.0, `requires` Obsidian API. Outside the content the mod counts as a client mod: normal matchmaking, Galactic War results and Proving Grounds.
- **The way in uses `obsidian.wrap`**: menu tabs, the mode screen, loadout changes, map previews. Hooks and guarded API calls stay off until the content starts.
- **The content uses `obsidian.hook`**: everything a mission of the mode changes.
- Guarded API calls (such as `api.ui.with_texts`) refuse before the content starts, so the way in needs a private copy of anything it calls there.
- The host calls `obsidian.expansion.start()` before leaving the mode screen. It refuses when a player lacks the mod at the same version (and shows the names), when the caller isn't host, or when another expansion runs. Keep the screen open on a refusal and say why.
- Call `obsidian.expansion.stop()` when the host picks a campaign mission or a Proving Grounds trial, or reaches the main menu. A stop at the main menu comes after the game left the lobby; Obsidian hands the content to the next host, as when a host leaves mid-mission.
- Every machine hears start and stop through `obsidian.on_session(on)`. On `false`, put back every change and clear effects with `api.effects.clear()`, because `effects.set` is refused by then.
- Test it offline: Helldivers Arcade starts `main.lua` against a fake loader and fake API, and fails on a guarded call before the content or a function moved between the wrap and hook lists.

## 2. Starting a mission of the mode

- Every machine builds the map from one number, the mission seed (`DifficultySettings.get_mission_params`), which the host sends. The low seven digits pick time of day, light, planet type, variant, faction, mission type and difficulty.
- **The digits above the seventh are free.** A seed of `97 * 10^7 + params` reads as the normal mission it describes, and every machine knows it is an Arcade mission without any message. Checked.
- The game reads five digits of the seed modulo a count, so another spelling of the same digits gives the same mission on a different map (about a thousand per parameter set).
- On the ship, `StateMenu.get_mission_seed` on the host decides what the hellpods start. Answer it with the mode seed, and the normal game launch does the rest, lobby included. Checked.
- The hellpods open only with a planet (or a trial) in the save (`StateMenu.update` / `update_host`). See section 4 for lending one.
- `StateMenu` calls `MenuSpaceManager.planet_changed` only when the planet name changes. To move the ship to the mode planet, call it after the galaxy map closes.
- A new galaxy map tab: add it to `substate_object.substates` in `MenuScreenCampaignRegion` and register a screen in `MenuScreenCampaign.states`. Obsidian closes Proving Grounds by state name only, so a second Proving Grounds screen under another name stays open in sessions.

## 3. The map

`GeneratedLevel` lays out the map from the seed.

| Change | Result |
| --- | --- |
| Skip `GeneratedLevel.generate_mission` | No objectives; set pieces, samples and extraction stay. The HUD lists only Extract. Checked |
| Filter the candidates of `generate_mission` | Keeps the normal count of objectives but only chosen kinds. Checked |
| Skip `generate_extract` | Black screen before the drop. Keep extraction; block the shuttle instead (`ExtractBeaconComponent`: `can_interact` for the player, `should_draw_ui`). Checked |
| Load `resource_packages/race_<faction>` in `GeneratedLevel.load_resources` | Two or three factions on one map, on every machine, before the drop. Checked |
| Spawn an objective entity mid-mission | Joins the list of the mission, but the unit must be in a loaded package. `gameobject_flag_01` stopped the game on a bugs desert. Not safe |
| Map size and shape | `GeneratedLevelSettings.get_level_settings` per planet type **(inferred, not tried)** |

The engine has no `Application.can_get`, so a mod can't ask whether the package of a unit is loaded. Use units known to be on every map (`gameobjects/pickup_ammunitionbox_01` was on every map tried), or read the package contents offline. Boss units live in the larger `race_<faction>_boss` packages.

`api.mission.restart_objectives` brings back terminals and assassinations; destroyed nests stay destroyed.

## 4. Keeping the campaign untouched

The vanilla mission end does campaign work from the current planet in the save (`StateMissionEnd.on_enter` and `save_stats`, on the first host only): it marks the selected mission done, finishes the planet after the last mission, completes defend and attack events, and adds the numbers of the mission to the planet.

- Lend the hellpods a planet only while `StateMenu.update_host` runs, and put the original planet of the player (or none) back right after.
- Hide the planet from the mission end, so none of that campaign work runs for a mode mission.
- Copy the campaign keys before and restore them after, in case anything else changes them.
- Leaving the galaxy map with a mode mission must save no planet (`set_current_planet_on_exit` off).
- `available_planets` holds raw planets: no region, fronts counted from 1. The planet screen builds the real table (`setup_planets`). A current planet with no region stops the ship in any game, modded or not; if an old version saved one, repair it at load.
- Test it offline against a copy of the vanilla mission end, failing on any mod line that writes a campaign key.
- The Obsidian loader keeps war reports and `CampaignManager` uploads out of every mission that runs expansion content.

## 5. Pausing, time and freezing

- `_G.TIME_SCALE` scales `GAME_DT` for the scripts only. Engine animation and movement keep the normal pace, so it doesn't slow the game. Checked.
- A real pause on every machine: `api.world.time_scale(0, { lobby = true })` (Obsidian API 1.33.1), each machine pausing itself as the pause menu does. Older APIs: `freeze` the enemies instead.
- A paused component keeps the commands queued for it, and some of the command data sits in `TempTableFactory` tables the game takes back at the end of the frame. Damage while frozen crashed on resume until Obsidian API 1.5.1 copied them.

## 6. Lobby sync for a mode

Helldivers Arcade shares state through lobby member data (`api.lobby.share`). Rules that kept machines in agreement:

- **Count whole values.** A machine that counted the fractions it collected reached a level the others didn't and waited for them forever.
- **Name the mission and the run in every shared value.** Lobby data outlives the mission, so a machine still loading would otherwise read the last run. Clear the value when a run ends.
- A machine that leaves stays in the sum, and nobody waits for a choice from that machine. Back in the same run, the value from that machine takes over.
- **The host shares a clock**, and a machine more than 3 seconds off takes it. Drift grows a little at every pause.
- A machine that becomes host mid-run picks the host-only logic (the enemy director) up at the shared clock, instead of starting over.
- Things every machine sees happen (an enemy dying) can be acted on locally on every machine with the same result: each machine drops the same orb, collects only what the local players touch, and shares the total.
- One roll, one result: let the host roll for random drops so a box comes once for the lobby.

## 7. What the game allows

More findings, all checked unless marked:

- `EncounterManager.start_encounter(position)` on the host sounds the alarm. `EncounterManager.spawn_group(position, group)` spawns where a mod wants (`api.enemies.spawn`).
- The Proving Grounds planet has 12 mission markers: 4 for Proving Grounds, 7 for campaign missions, and 1 for the boss.
- Stratagems outside the loadout drop fine (flamethrower, exosuit), so a mode can offer any of them.
- `LoadoutSettings.nr_of_stratagem_slots` set to static plus 1 leaves one choice; the screen and the drop both read it.
- The `activation_time` of a flare starts from that of the stratagem and counts down, so changing it as the flare appears changes that one call-in.
- The Orbital Laser burns about 15 metres around the target; an upgrade that aimed it at the nearest enemy killed the player who picked it.
- An explosion sends hits from a physics overlap answered on a later step, after the call returned. Filter hits where the answer arrives, not around the call.
- The state of a weapon points at settings shared by the weapon type plus copies of some of them, and the hit test keeps the settings it was made with: a private copy needs `remake_raycast` (`api.gear.tune` does this).
- `InventoryComponent` starts the backpack shield with `set_shield_info` and stops it with `set_shield_activated false`. Other states stop it too, so only a changed `inv.backpack` says the backpack went.
- A Cyborg Hound takedown is the `regular_knockdown` status, the same `CharacterStateKnockedDown` as a blast. A dive is `CharacterStateDodge` for every character; getting up runs in it or in `CharacterStateCrawl` when a direction is held.
- A drone needs the station from the pack it came with to dock and reload; a mod can spawn the station on the player outside the backpack slot, as `set_backpack` does.
- `type()` of a game vector is `"vector3"`, not `"userdata"`.
