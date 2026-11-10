# Multiplayer

HELLDIVERS (2015) is played in squads of up to four, online, in local co-op on one machine, or both. A mod that changes gameplay must work out what every machine sees. Read this before designing anything other players share.

## Contents

1. Machines, masters and slaves
2. Session mods and the guardrails
3. Channels for sending data
4. Patterns that worked
5. What to test

## 1. Machines, masters and slaves

- Each entity (a player, a crate, a turret) belongs to one machine, the master. Other machines hold a slave copy.
- Component code is split: `setup_master` and `update_masters` run on the owner; slave paths (`command_slave`, slave updates) on the others. A hook on a master path runs on one machine only. That is usually what you want for spawning things (spawn once, the game replicates it), and wrong for display changes that every machine needs.
- Local co-op: one machine is master of several players. Code that assumes one local player breaks for the second controller. Loop over every local player.
- Several data flows are display copies only. For example, other machines learn the stratagem cooldowns of a player from `rpc_stratagem_info` to draw HUD cards; changing the slave copy changes nothing on the owner.

## 2. Session mods and the guardrails

Details are in `obsidian-mods.md`. In short:

- `client` scope: runs alone; must not change gameplay. The Obsidian API refuses gameplay calls to client mods.
- `session` scope: runs only in a cleared lobby, where every player runs the same session mods (or opted in). In a lobby that isn't cleared, hooks and `on_frame` stop and custom content falls back to the vanilla content it is based on. Design for that: nothing may error, and players without the mod must see a normal game.
- `every_player: true`: the mod runs only if every player runs it, at the same version and with the same shared option values. Use it when partial support would confuse players.
- Option values of a session mod are compared between players unless the option is marked client scope.
- `parts` (Obsidian 1.5.0): a session mod can keep personal pieces, such as a camera, running in a lobby that isn't cleared, while the gameplay pieces switch off (`obsidian-mods.md` section 5).
- A change made only while one game call runs leaves nothing to undo when the mod switches off (`gameplay.md` section 5).

## 3. Channels for sending data

Lua mods can't add network messages or game object fields; those are fixed in the game network config. Available channels:

| Channel | Latency | Fits |
| --- | --- | --- |
| Game rpcs and game objects the game already sends | game speed | Riding existing data, such as watching the cooldown of another player in the slave copy |
| Replicated entities (`entity_spawner:spawn_entity` on the master) | game speed | Things everyone must see: pickups, props |
| `api.lobby.share(name, text)` / `api.lobby.shared(name)` | about 1 s (Steam lobby member data) | Small mod state, up to 200 characters per mod and name; persists for late joiners |
| `NetworkLobby:set_data` | host only | Lobby-wide flags |

Check the bit widths in `network_messages.lua` before reusing a message: a value that doesn't fit is truncated silently or errors.

## 4. Patterns that worked

**Identify custom content on other machines by context, not by id.** A custom stratagem travels as the base id, so another machine sees a vanilla Resupply. Shared Resupply finds the entry by position (the first base-id entry after the statics); with the vanilla one also present, the vanilla one sits later in the list.

**Spawn once, on the master.** Extra boxes in a supply crate are spawned in `SupplyCrateComponent.setup_master`, which runs only on the machine of the thrower, and replicate to all.

**Squad state by watching slaves.** Shared cooldown: every machine watches the entries of all players. A remote entry going from ready to a long time is a throw; local players behind the squad are set to the remaining time of the squad with the built-in game command and broadcast. Guards:
- Treat a jump as a throw only after the entry has been watched for a few seconds; a respawn copies old values back.
- Only correct local players more than about 2 seconds behind, so corrections don't echo between machines.
- A new entry (a player joining, a local controller added) takes the longest remaining time in the squad at once, without waiting to detect a throw.

**Shared values that outlive a mission.** Lobby member data stays after a mission ends. Put the mission and run in every shared value, count whole numbers only, let the host share a clock, and keep the contribution of a leaving player in sums. The full rules from Helldivers Arcade are in `game-modes.md` section 6.

**Signal with data every machine already has.** A mission seed has free digits above the seventh: a mode can mark the missions it starts there, and every machine knows without a message (`game-modes.md` section 2). Events every machine sees (an enemy dying) can drive the same local result on each machine.

**Undo on session change.** `obsidian.on_session(fn)` fires when the lobby clears or stops being cleared. Take back global edits, hidden items and carried entries there.

## 5. What to test

Offline tests can check decisions; only the game settles timing. Ask the tester, most likely failures first:

1. Local co-op: add a second controller mid-mission; both players see the same state.
2. Online with a second player who runs the mod: HUD of the other player, sync speed, objects both see.
3. Respawn, and joining mid-mission.
4. A lobby that isn't cleared (a player without the mod): no errors, vanilla behaviour.
5. Host leaving (host migration), if the mod keeps state on the host.
