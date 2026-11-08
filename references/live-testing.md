# Testing in the running game

Offline tests settle logic. Hooks, frame order, drawing and engine behaviour need the game. This is the harness pattern used for Heroic UI, Helldivers Arcade, Enhanced Visuals and a backend probe, and the checklist habits that came with it. Build the harness once per project, outside git (an `internal/testing` folder), and keep it out of the release.

## Contents

1. Protect the player's save and library
2. A test mod that takes commands
3. Driving the game
4. Probes
5. Checklists for a person

## 1. Protect the player's save and library

- Before a run: record hashes of the save files (local and Steam Cloud), then purge the player's deployed mods.
- Deploy a throwaway library: the mod under test, Obsidian API, Obsidian Patches (skip intro and login make runs shorter) and the test mod.
- After a run: purge the throwaway library, redeploy the player's, and compare the save hashes. Every run should end with the saves identical.
- **Make the test mod a session mod that skips every save call.** Session scope makes Obsidian hold back Galactic War and leaderboard uploads while it runs, so a test mission sends nothing to the shared war.
- If a test needs the opposite (uploads to a local stub server), redirect the save too: `SaveManager.setup` can be pointed at a separate save name, which the game then writes instead of the real one.

## 2. A test mod that takes commands

The game's Lua can't parse source at runtime (`loadstring` of text returns nothing), so a test can't send code. Instead:

- The test mod reads a command file in the logs folder each frame and runs named commands: open a menu, win, start a mission, set god mode, run a probe.
- The mod is inert unless a config file written by the run script exists, and the script deletes it at the end. A forgotten test mod then does nothing.
- Log lines with fixed prefixes (`STATE`, `MISSION READY`) let the driver wait for a state instead of sleeping.
- A file such as `tour.god` in the logs folder can switch on invulnerability once a mission is ready.

## 3. Driving the game

- A small driver script launches the game, waits for log lines, sends keys and clicks, writes tour commands and takes screenshots. Steps read like `"wait:MISSION READY:90" cmd:win sleep:20 shot:score key:E`.
- Pass a mission seed in the environment to drop straight into a known mission (difficulty, faction and planet type are in the seed; see `game-modes.md` section 2).
- Take mouse coordinates in the 1920x1080 layout space and scale them by the player's UI scale.
- For visual changes, pause the mission and compare frames pixel by pixel ("2.7% of the picture changed by more than 8 levels"). Enhanced Visuals settled why an effect didn't show this way.
- Screenshots: the game has no screenshot call. Copy the window through the OS; exclusive fullscreen can return black, borderless works.
- Ending `helldivers.exe` between steps is fine; deploy needs the game closed.

## 4. Probes

- A probe is a named function shipped inside the test mod and run with a command (`cmd:probe orbs`). It answers one question: spawn candidate units, read a value, call an engine function once.
- Probe a risky engine call alone before building on it. Several probes stopped the game (an unloaded unit, an objective spawned on the wrong biome, an engine call with wrong arguments); finding that in a probe costs one restart.
- Write down what each probe found, with the date and build, and mark it checked. Facts from reading the scripts alone stay **(inferred)** until a probe or a person confirms them.

## 5. Checklists for a person

Scripts can't judge feel, sound, timing with a second player, or how a change looks. Hand those to a person with a short list:

- Most likely failures first.
- One line per check, with what to look for ("a pod with 0.01 still lands").
- Separate solo checks from checks that need a second player or a second controller.
- Ask them to note what was just pressed if the game drops off the network mid-mission: that is the tamper check, and a code path wrote a protected value.
- Record each result under the item (PASS, or what happened), and list what is still untested in the mod's testing doc: gamepads, other aspect ratios, other languages, a lobby.
