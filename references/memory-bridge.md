# The Memory Bridge: Lua in the running game

The Memory Bridge of Obsidian API (1.56.0 and later) runs Lua sent from outside the game while the game runs, and writes back what the code printed and returned. Most questions a mod raises can be answered this way without a restart or a test build. What does this function get? Which unit is which? What runs first in a frame? Does this hook do what it should? Any agent that can run a command can drive it.

## Contents

1. Setting it up
2. A first session
3. What code can use
4. Watching over time: frame functions, hooks and the stream
5. Rules for agents
6. Traps
7. How it works, for writing another driver

## 1. Setting it up

1. In Obsidian, open the settings of Obsidian API and switch on **Memory Bridge**. Deploy, then start the game.
2. Play on a Sandbox save in Obsidian. Code sent to the bridge can change anything, and a Sandbox keeps the real save out of reach.
3. Check it answers, from the folder of this skill: `python tools/bridge.py status`. The status file is rewritten every two seconds or so while the game runs frames.

`tools/bridge.py` needs Python 3.8 or later and nothing else. It compiles the code with the LuaJIT 2.0 that Obsidian installs beside itself (the `luajit` folder of the Obsidian install). It finds that compiler from the uninstall entry of Obsidian Launcher. Otherwise, pass `--luajit <path to luajit.exe>` or set `OBSIDIAN_LUAJIT`.

What the option does to the game, by design:

- Code runs only alone or in a lobby that isn't public (by the privacy the host set). In a public lobby a request is refused, and when a lobby turns public, everything the bridge left running is undone.
- Galactic War and leaderboard results of a launch with the option on are never sent, the same as with session mods.

## 2. A first session

```
python tools/bridge.py "api.game.state_name()"          -> = "menu"
python tools/bridge.py "find('^State')"                 -> the game states, by global name
python tools/bridge.py "fields(g('Boot').state_machine)" -> the fields and methods, with types
python tools/bridge.py -f assets/bridge-scripts/where.lua
```

- An expression prints the value. Anything else runs as a chunk: `"print(1) return 2, 3"`.
- `-f file.lua a b` runs a file; `a` and `b` reach it as `...`, as strings.
- Each line `= <value>` is one returned value. Tables print two levels deep: `show(t, 4)` prints deeper.
- Errors come back with the line of the code and a short traceback. Exit codes: 0 ok, 1 the code failed, 2 refused, 3 no answer.

The scripts in `assets/bridge-scripts/` are starting points: `where.lua` (state, Helldiver, enemies near), `trace.lua` (each call to a method for a few seconds), `watch.lua` (each change of a value), `frame_times.lua`, `shot.lua`.

## 3. What code can use

Code runs on the game thread, after the update of the frame, with the globals of the game and these names:

| Name | What it is |
|---|---|
| `api` | Obsidian API, every module, nothing guarded |
| `g(name)` | A global, or nil (strict globals in the game throw on an unknown name; reading through `g` never does) |
| `keep` | A table that lasts from one request to the next |
| `print(...)`, `show(v, depth)` | Lines for the answer |
| `fields(v)` | The keys of a table and of each `__index` table up the metatables, with types: the methods of a game object |
| `find(pattern)` | Global names matching a Lua pattern (lower case) |
| `upvalues(fn)` | The upvalues of a function. Game functions are stripped, so the names are often empty, but the values are there |
| `set(t, k, v)` | `t[k] = v`, kept for `undo()` |
| `every(name, fn)` | `fn(dt, frame)` every frame until it returns true; `every(name, nil)` stops it |
| `hook(class, method, fn)`, `unhook(class, method)` | A hook like `obsidian.hook`, `fn(original, ...)`, that can be replaced or taken off |
| `emit(...)` | A line to the stream, with the frame number |
| `undo()` | Takes back every frame function, hook and `set()` write. `python tools/bridge.py undo` does the same |
| `frame()` | The frame count of the bridge |
| `shot(name)` | A screenshot of the game into the bridge folder: the path, or nil and why not |

A global the code sets stays in that request. Use `keep` for anything a later request needs, and `rawset(_G, ...)` only for a real game global.

## 4. Watching over time: frame functions, hooks and the stream

A request ends at once, so anything over time goes through `every` or `hook`. Their results go to the stream, which `python tools/bridge.py stream` prints (`--follow` keeps printing, `--clear` empties it after).

```lua
-- Each call to a method for two seconds (trace.lua does this with a limit):
keep.until_ = os.clock() + 2
hook("StateMenu", "update", function(original, self, dt, t)
  emit("update", dt)
  return original(self, dt, t)
end)
every("stop", function() if os.clock() > keep.until_ then unhook("StateMenu", "update") return true end end)
```

- One hook per method: hooking the same method again replaces the function.
- A hook that throws an error is taken off, and the error goes to the stream. A frame function that throws an error stops the same way.
- `undo()` at the end of a test, every time.

## 5. Rules for agents

- Ask for small answers: a count, a few fields, `show(t, 1)`. Never print a whole game table. It costs context and says little.
- Read before writing. Write with `set()` where possible, and `undo()` when the test ends.
- Before a call that could stop the game (spawning, an engine call not used before, anything in the "Traps" list), tell the user what it is, and send it alone, in a request by itself.
- One driver at a time: two agents sending requests to one game get the answers late, or in the wrong order.
- Never write the save, the account or campaign progress, unless that is the task and the user agreed.
- Confirm in the game code what the bridge shows. The bridge shows one run, while the game code shows every case.
- When something new is learned (a return value, an order of calls, a trap), write it down where the mod keeps findings, with the date and the game build.

## 6. Traps

- **Engine asserts end the game, and no `pcall` catches them.** Examples: an animation call on a cinematic unit, an unknown command sent to a component, a unit spawned from a package that isn't loaded. If the game closes during a request, the tool says so. The bridge leaves a `running` file with the id of the request, so the cause is known.
- **A unit kept from an earlier frame may be gone.** Check `Unit.alive(unit)` before any other call on a unit kept in `keep`. A world unloads between the ship and a mission.
- **Vectors and quaternions last one frame.** Keep `api.game.box(v)` instead, and `api.game.unbox` it when used.
- **Loading screens hold frames.** No request runs until they end, so a wait of 10 seconds can run out (`--timeout`).
- **Speed.** The retail game loads no new code at runtime: `loadstring` answers nothing for bytecode and for source, and `dofile` looks a name up among the game resources. So the bridge interprets the compiled code itself, about 50 times slower than the code of a mod. The game functions it calls still run at full speed. A hook on a function called hundreds of times a frame costs real frame time. Hook it for a short while, or ship it in a test mod.
- **Error messages don't name variables.** Real Lua says "attempt to index local 't'". The bridge says "attempt to index a nil value" with the line.
- **No FFI cdata constants** (`1LL`, `0x1p4i`) in bridge code.
- **Parts of the API only run with a session mod deployed.** Effects, edits, bots and stratagem changes install their hooks only when a session mod requires Obsidian API (inferred from the API source, `main.lua`). With only client mods deployed, a call can answer true and change nothing. Deploy any session mod, such as Obsidian Trainer, for those.
- **Screenshots** come off the screen: with another window in front of the game, `shot()` refuses (`not_in_front`), and exclusive fullscreen gives `black`. Use borderless.

## 7. How it works, for writing another driver

The folder is `%APPDATA%\Arrowhead\Helldivers\ObsidianLauncher\bridge\`. The driver makes it.

- `request`: written by the driver through a rename, so the game never reads it half written. Text lines, then bytes: `OBSBRIDGE 1`, an id (letters, digits, `_`, `-`), the arguments separated by tabs, the opcode names of the compiler (the `bcnames` string of `jit/vmdef.lua`, six characters a name), then LuaJIT 2.0 bytecode of `return function(...) <code> end`.
- `answer_<id>`: the first line is `ok`, `error` or `refused`, then the id and the time in milliseconds. After it come the printed lines and one `= <value>` line per returned value, or the error, or why it was refused.
- `running`: the id of the request being run. Left behind, the game closed while running it.
- `stream.txt`: `<frame>\t<text>` lines from `emit()`, failing hooks and frame functions.
- `status`: version, frame, time, game state, whether code may run, and counts.

The game reads `request` once a frame. Compile with debug info (`string.dump` of LuaJIT 2.0 keeps it) so errors carry line numbers. Stripped bytecode runs too.
