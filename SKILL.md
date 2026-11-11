---
name: hd1-lua-modding
description: Build, fix and release Lua mods for HELLDIVERS (2015, also called Helldivers 1 or HD1) with Obsidian Mod Manager and the Obsidian API. Use this whenever the task touches an HD1 mod or the HD1 game scripts, such as new stratagems, weapons, HUD or menu changes, mission or enemy behaviour, mod options, multiplayer sync between players, obsidian.json manifests, hooks into game classes (InventoryComponent, LoadoutSettings, StateGame, menu screens), patch bundles, or releasing a mod to GitHub, even when the request only names a game feature and never says "mod" or "Lua". Not for HELLDIVERS 2.
---

# HD1 Lua modding

HELLDIVERS (2015) runs on the Bitsquid engine. The whole game logic is Lua, shipped as stripped LuaJIT 2.0 bytecode. Mods are Lua too: Obsidian Mod Manager compiles them, packs them into patch bundles that the engine loads over the game bundles, and the Obsidian Loader runs them in game. The Obsidian API is a library mod with named, checked, undoable calls for most game areas. Prefer an API call over a raw hook whenever one exists, and extend the API when a mod needs something generic.

## Where to read next

Read only what the task needs.

| File | Read it when |
| --- | --- |
| `references/obsidian-mods.md` | Creating a mod, editing `obsidian.json`, options, loader calls (`obsidian.hook`, `on_frame`...), tests, releasing |
| `references/engine.md` | Finding what to hook in the game scripts, components, master and slave, network limits, crashes |
| `references/multiplayer.md` | Anything other players must see, share or agree on; session mods |
| `references/stratagems.md` | Stratagems: new ones, loadouts, cooldowns, payloads, icons, the HUD list |
| `references/gameplay.md` | Camera mods, weapon range and aim, enemy detection and patrols, changing a rule for one call only |
| `references/ui.md` | HUD additions, redrawn menus, images and fonts a mod ships, drawing in the 3D world, the aim cursor, mouse and keys |
| `references/rendering.md` | Graphics: shading values, renderer settings, the render config, shaders, textures, lights |
| `references/game-modes.md` | A mode apart from the campaign: expansions, mission seeds, map generation, keeping the campaign untouched, pausing |
| `references/live-testing.md` | Scripted runs in the game: protecting the save, a command-driven test mod, probes, checklists for a tester |
| `references/orchestration.md` | A large mod where splitting the work across several agents or models pays off |
| `assets/mod-template/` | Starting a new mod: copy it and rename |
| Obsidian API `REFERENCE.md` (github.com/Alomare/ObsidianAPI) | Before writing any hook: search it for the area first. It is long; search, don't read it whole |

## Workflow

1. **Pin down the behaviour.** What players see, what the squad shares, what stays vanilla. Decide the scope early: a `client` mod changes the game for the local player only; a `session` mod changes gameplay and runs only when every player in the lobby runs it. Anything that changes what other players experience is a session mod.

2. **Find the game code.** The game scripts are bytecode; work from a decompiled ("lifted") copy. `references/engine.md` explains how to make one and how to search it. For every function to hook, confirm on which machine it runs (master or slave), who calls it, and which table the game reads back afterwards, not only the one it writes.

3. **Check the API first.** Search `REFERENCE.md` for the area. If the API has a call, use it. If the need is generic (another mod could use it), add it to the API with tests and docs rather than hooking in the mod, so mods stay small and the API grows.

4. **Check the hard limits before designing.** Network message parameters have fixed bit widths and game objects have fixed fields (see `references/engine.md`). A design that needs a 9th lobby loadout field or a value above the field width will not work, however good the Lua is. Find these limits during design, not after a test.

5. **Write testable code.** Put decisions in pure functions (which slot, which code, when to sync) and keep the hooks thin. Test the pure parts offline with LuaJIT 2.0 and fakes of the game tables. Run the API test suite too when the API changed.

6. **Deploy and hand over to an in-game test.** Offline tests can't settle network timing, HUD drawing or engine behaviour. Deploy to the library the player uses, then give the tester a short list of what to look at, most likely failures first. Local co-op (a second controller) tests most multiplayer paths on one machine. For scripted runs and probes, see `references/live-testing.md`.

7. **Release.** Bump the version, add the CHANGELOG section, tag `v<version>`; the release workflow builds the zip. When a mod needs a new API, release the API first and make the mod require that version.

## Rules that save the most time

- Never write protected component keys (such as `cooldown_timer`) directly; go through the game commands, as the API does.
- A custom stratagem (or other custom entry) travels over the network as the vanilla entry it is based on. Other machines can't tell the two apart unless every player runs the mod and the mod tells them.
- Session hooks stop in a lobby that isn't cleared. Global tables a mod replaces directly keep the changes there, so undo them in `obsidian.on_session`. A value changed only while one game call runs, and put back right after, needs no undo (`references/gameplay.md` section 5).
- The camera frustum decides patrol alarms, spawns, the squad leash and more. A camera mod that changes the frustum changes gameplay (`references/gameplay.md` section 1).
- A mod with personal pieces and gameplay pieces can declare parts (Obsidian 2.0.0), so the personal pieces keep running in public lobbies (`references/obsidian-mods.md` section 5).
- A Lua error inside a game update freezes the game. Guard hooks that run every frame.
- Hiding something from a menu has three parts: the list the screen draws, the default data the game falls back to, and the data in the save. Missing one leaves the item reachable.
- Spawning a unit from a package that isn't loaded stops the game, and the engine can't be asked first. Spawn only units known to be loaded where the code runs.
- The `update` of a menu holds input, network sync and save writes. To restyle a screen, stop only the drawing.
- Lobby data outlives the mission. Name the mission and run in every shared value.
- Keep vanilla behaviour as the default and make the change opt-out only when the request says so; players notice lost upgrades and reset loadouts first.

## Writing for players

READMEs, option labels and release notes are plain and serious, describe what the mod does in game terms, and list what every player needs (mod version, API version). No flavour text.
