# Obsidian mods: package, loader and API

Everything about the mod package, the Obsidian loader and the way a mod talks to Obsidian API. Sources: the Wiki pages in `app/src/wiki/` of github.com/Alomare/ObsidianLauncher, `loader/src/*.lua` there, and REFERENCE.md of github.com/Alomare/ObsidianAPI. Where a statement is unconfirmed it is marked **(unconfirmed)**.

## Contents

1. [Mod folder and release zip](#1-mod-folder-and-release-zip)
2. [obsidian.json](#2-obsidianjson)
3. [Lua runtime](#3-lua-runtime)
4. [Loader calls](#4-loader-calls)
5. [Session rules](#5-session-rules)
6. [Using Obsidian API](#6-using-obsidian-api)
7. [Options in game](#7-options-in-game)
8. [Offline tests](#8-offline-tests)
9. [Releasing](#9-releasing)
10. [Deploying locally](#10-deploying-locally)

A ready skeleton is in `assets/mod-template/`. Real examples: github.com/Alomare/HD1-MoreStratagems, HD1-SharedResupply, HD1-PhotoMode, HD1-BetterHUD, HD1-EnhancedVisuals, HD1-HelldiversArcade.

## 1. Mod folder and release zip

A mod is a folder with `obsidian.json` at the top plus the files it uses. A script mod needs one Lua file.

```
mod-id/
  obsidian.json        manifest
  main.lua             entry script
  src/*.lua            modules, loaded with obsidian.module
  res/                 game resources (textures, materials, replaced scripts)
  locales/en.json      text the mod shows in game (optional)
  image.png            square picture, up to 4 MB (optional)
  tests/ tools/        offline tests, build scripts (not shipped)
  CHANGELOG.md README.md LICENSE .gitattributes .gitignore
  .github/workflows/release.yml
```

Paths in `obsidian.json` are relative to the mod folder, with forward slashes.

### The release zip

The zip is built by `git archive`, so `.gitattributes` decides what ships. `obsidian.json` must be at the top of the archive, or inside one folder at the top. The release workflow adds the folder `<id>/`.

Ships: `obsidian.json`, `main.lua`, `src/`, `res/`, `locales/`, `image.png`, `LICENSE`.

Left out with `export-ignore`: `.github`, `.gitattributes`, `.gitignore`, `internal`, `README.md`, `CHANGELOG.md`, `CLAUDE.md`, `tests`, `tools`.

```
* text=auto eol=lf
.github export-ignore
tests export-ignore
tools export-ignore
res/* binary
```

Mark `res/*` as `binary` so line-ending conversion never touches a texture.

## 2. obsidian.json

Obsidian checks it on import and names the field that is wrong. Unknown fields are kept and ignored.

### Fields

| Field | Required | Meaning |
|---|---|---|
| `obsidian` | yes | Format version. Always `1`. |
| `id` | yes | Permanent. 1 to 64 of `a-z 0-9 . _ -`, starting with a letter or digit. Use `author.mod-name`. Never change it after release: players would end up with two mods. |
| `version` | yes | Semantic version `1.2.0`. A higher version replaces a lower one on import. |
| `name` | yes | Object by language. `en` required. |
| `description` | no | Object by language. State what changes and whether other players notice. |
| `authors` | no | List of names. |
| `scope` | no | `client`, `session`, `expansion` or `library`. Missing or unknown means unspecified, which runs as a client mod (section 5). |
| `every_player` | no | `true`: runs only when every player in the lobby runs the mod, at the same version and shared option values. Not for client mods or expansions. |
| `entry` | no | Lua script the loader starts. Mods that only replace game files omit it. |
| `modules` | no | Extra `.lua` files, with the extension, loaded through `obsidian.module`. A file not listed cannot be loaded. |
| `requires` | no | Ids of mods this one needs, such as `obsidian.api`. Enabling the mod enables them, and they start first. Deploy stops with a message if one is missing. |
| `resources` | no | Game files to replace or add (below). |
| `options` | no | Settings players change in the app (below). |
| `keybinds` | no | Keys players can rebind. |
| `parts` | no | Pieces of a session mod, each `client` or `session` (below). Obsidian 2.0.0. Not for libraries or expansions. |
| `option_groups` | no | Headings that fold, to sort the options under (below). Obsidian 2.0.0. |
| `option_previews` | no | Pictures of option values drawn from SVG templates (below). Obsidian 2.0.0. |
| `loader_api` | no | Loader API version needed. `1` when left out. A loader with a lower version refuses the mod. |
| `min_obsidian` | no | Oldest Obsidian that works, such as `"1.2.0"`. Older ones refuse the mod. Obsidian before 1.1 ignores it. |
| `load` | no | Load order request: `"first"`, `"last"`, or an object with `position`, `before`, `after`, `before_patches`, `after_patches`. Obsidian 1.3.1 and earlier read only `"last"`. |
| `load_after` | no | Ids to load after. Older form of `load.after`. |
| `image` | no | Square PNG, JPG or WebP in the folder, up to 4 MB. 512 by 512 is enough. |
| `source` | no | Mod address, shown in details. A GitHub repository URL also enables in-app updates (section 9). |

Text shown to players is an object by language: `en`, `pt-BR`, `zh-CN` for the app, and `en`, `fr`, `es`, `pt-BR` for in-game text. English fills in for anything missing. In-game text goes in `locales/<lang>.json` (a flat object of keys and text) and is read with `obsidian.text(key, ...)`.

### scope values

| Value | Meaning |
|---|---|
| `client` | Changes only what this player sees, hears or presses. Runs in any lobby. |
| `session` | Can change the shared game. Runs alone, in friends-only or private lobbies, and in public lobbies only when every other player allows it. |
| `expansion` | Content that stands apart from the normal game (a mode). Client mod until the host starts the content. |
| `library` | Code other mods build on. Becomes session when an enabled session mod requires it, client otherwise. |
| missing | Unspecified. Runs as a client mod. Do not rely on it. |

### options

Each option has `id` (lowercase letters, digits, `_`), `type`, `default`, `label`, and optionally `description`, `visible_when` (object of option ids and required values), `scope`, `group` (an `option_groups` id) and `part` (a `parts` id).

| type | value | extra fields |
|---|---|---|
| `toggle` | `true` or `false` | |
| `number` | number | `min`, `max`, `step` |
| `choice` | one listed id | `choices`: ids, or `{ "id": "...", "label": { ... } }` |
| `key` | key name such as `f8` | |
| `color` | `#rrggbb` | |

`"scope": "client"` on one option marks the value as personal (a color, a camera distance). Option values of a session mod or expansion are compared between players unless marked client.

Obsidian validates values against the declaration, so the mod never sees a value outside the range. Keep option and key ids unchanged between releases: values carry over, except when the type changes.

### keybinds

```json
"keybinds": [ { "id": "toggle", "default": "f8", "label": { "en": "Toggle" } } ]
```

Key names come from the game, in lower case: `f8`, `k`, `insert`. `pad` names a `choice` option holding the controller input for the same action.

### resources

Each entry replaces or adds a game resource. `type` and `name` are the game path.

| Field | Meaning |
|---|---|
| `type` | `lua`, `texture`, `material`, `font`, `timpani_bank`, `bik`, or `#` plus 16 hex digits for an unnamed type |
| `name` | Resource name, such as `lua/settings/perk_settings` or `mymod/icons` |
| `source` | Plain Lua, compiled at deploy (type `lua`) |
| `bytecode` | Already compiled LuaJIT 2.0 bytecode |
| `data` | Raw resource file for any other type |
| `stream` | With `data`: part the game reads from the `.stream` file |
| `variants`, `clips` | Per-language variants, single clips of a sound bank |
| `bundle` | 16 hex digits. Required except with `clips`. |
| `when` | Options that must have these values for the entry to be used. Changing such an option needs a new deploy. |
| `part` | The part the entry belongs to (Obsidian 2.0.0). An entry of a part that is off isn't deployed. |

The boot bundle is `9cf71054ea26dddf`. UI art, fonts and materials a gui draws must be in it: a gui that lists a material that is not loaded can stop the game. The example mods put an icon texture and material there:

```json
"resources": [
  { "type": "texture",  "name": "mymod/icon",  "bundle": "9cf71054ea26dddf", "data": "res/icon.texture" },
  { "type": "material", "name": "mymod/icons", "bundle": "9cf71054ea26dddf", "data": "res/icons.material" }
]
```

Prefer hooks over replacing whole game scripts: a hook changes one function, so two mods can touch the same script. A resource is static and cannot switch off mid-game, so in a session mod use resources for data read at startup and hooks for behaviour. Making textures or materials from scratch needs tools that are not part of the manager; the example mods ship a `tools/build_icon.py` for the icon.

### parts

Obsidian 2.0.0. Splits a session mod into pieces, so the personal pieces keep running in a public lobby where the gameplay pieces switch off (rules in section 5).

```json
"scope": "session",
"parts": [
  { "id": "view", "scope": "client", "name": { "en": "Camera and view" } },
  { "id": "weapon_range", "scope": "session", "option": "max_weapon_range", "name": { "en": "Max weapon range" } }
]
```

- `id` follows the option id rules; `scope` is `client` or `session`; `name` and `description` show in the app and in the in-game notice.
- `option` names a toggle that switches the part. A part that is off runs no code, deploys no file and counts for nothing players compare. Changing that toggle needs a deploy.
- Options, resources and code name the part they belong to. Anything without a part follows the strictest part that is on.
- The top-level `scope` stays the strictest one, `session` when any part is. An older Obsidian reads only that and runs the whole mod as a session mod, so no fallback code is needed.

### option_groups and option_previews

Obsidian 2.0.0. Older versions ignore both and list the options as before.

```json
"option_groups": [
  { "id": "idle", "label": { "en": "Idle" }, "description": { "en": "Between shots." } },
  { "id": "aim", "label": { "en": "Aiming" }, "collapsed": true }
],
"option_previews": [
  { "id": "idle_preview", "group": "idle", "template": "preview/idle.svg", "width": 240, "height": 140,
    "label": { "en": "Preview" } }
]
```

- An option joins a group with `"group": "<id>"`. Options without a group come first, then each group in order. `collapsed` starts a group folded, and the app remembers what the player opened.
- A preview shows at the top of the named group, redrawn while the player edits values. The template is an SVG file in the mod, at most 64 KB, checked on import. `{{expr}}` in an attribute or text becomes the value of the expression; `data-if="expr"` removes an element while the expression is false. Expressions take numbers, `'text'`, option ids, arithmetic, comparisons, `&& || !`, `a ? b : c`, and `min`, `max`, `abs`, `round`, `floor`, `ceil`, `clamp`. Scripts, `foreignObject`, `on...` attributes and outside links are taken out. Full grammar: Wiki page "Options and keys".
- Custom Crosshair builds both templates with a script from the same rectangle table the mod draws from, and a test fills them in the way Obsidian does and compares the result with the game drawing. Rounding then matches pixel for pixel.

### Complete example

```json
{
  "obsidian": 1,
  "id": "author.modname",
  "version": "1.0.0",
  "name": { "en": "Mod Name", "pt-BR": "Nome do Mod" },
  "description": { "en": "What the mod changes, and whether other players notice." },
  "authors": ["Author Name"],
  "image": "image.png",
  "scope": "session",
  "every_player": false,
  "entry": "main.lua",
  "source": "https://github.com/author/HD1-ModName",
  "min_obsidian": "1.2.0",
  "loader_api": 1,
  "modules": ["src/feature.lua"],
  "requires": ["obsidian.api"],
  "resources": [
    { "type": "texture", "name": "mymod/icon", "bundle": "9cf71054ea26dddf", "data": "res/icon.texture" }
  ],
  "options": [
    { "id": "enabled", "type": "toggle", "default": true, "label": { "en": "Enable the feature" } },
    { "id": "power", "type": "number", "default": 2, "min": 1, "max": 10, "step": 1,
      "label": { "en": "Power" }, "visible_when": { "enabled": true } },
    { "id": "tint", "type": "color", "default": "#f0b429", "scope": "client", "label": { "en": "Tint" } }
  ],
  "keybinds": [
    { "id": "toggle", "default": "f8", "label": { "en": "Toggle the feature" } }
  ]
}
```

## 3. Lua runtime

- The game runs LuaJIT 2.0 bytecode and cannot parse Lua source. The manager compiles every mod script (the entry, `modules`, `lua` resources with `source`) at each deploy. A mod ships plain `.lua` text and needs no compiler.
- Write Lua 5.1 syntax plus LuaJIT extensions: no integer division or `//`, no 5.3 bit operators. Use the `bit` library for bit operations. Test with LuaJIT 2.0, the version the game uses.
- Mod scripts see the game globals and the standard libraries: `string`, `table`, `math`, `io`, `os`, `coroutine`, `debug`, `package`, `bit`, `jit`. The loader logs at startup any global a mod adds or replaces.
- Read game globals with `rawget(_G, "Name")`: a global the game has not defined yet is `nil`, and some tables are built after mods start. Use `obsidian.hook` (waits for the global) or `obsidian.on_require` for tables that appear later.
- The loader adds one global, the table `obsidian`. Everything registered through it runs protected: an error is logged and never stops the game.
- The entry script runs once at game boot, in load order. An error at startup switches the mod off for the session and writes `loader.log`. Errors in callbacks are logged at most three times per place. A mod that keeps failing is switched off.
- `obsidian.module(name)`: loads another file of the mod and returns what it returns. `name` is the path without `.lua` (`"src/feature"`), and the file must be listed in `modules`. Results are cached, like `require`.
- `obsidian.import(id)`: what the `entry` script of another running mod returned, or `nil`. List the mod in `requires` so it starts first. A library exports the table other mods use by returning a table from `main.lua`.
- Logs: `%APPDATA%\Arrowhead\Helldivers\ObsidianModManager\logs\`. Each mod writes `<id>.log` (id reduced to letters, digits, `_`, `-`) and the loader writes `loader.log`.
- Game vectors last one frame. Copy numbers, never keep a vector in a variable across frames.

## 4. Loader calls

All calls are on the global `obsidian`. `obsidian.version` is `1`. `obsidian.capabilities` is a read-only table of booleans (`hook`, `wrap`, `on_require`, `on_frame`, `on_session`, `after_startup`, `settings`, `keybind`, `session`, `text`, `log`, `module`, `import`, `caller`, `info`, `menu`, `toast`, `notify`, `storage`, `ui`, `scope`, `guardrails`, `expansion`, `parts`). Test a capability before using a call that came later.

### Hooks and callbacks

| Call | Meaning |
|---|---|
| `obsidian.hook(target, method, fn)` | Wraps a game function. `target` is a table or the name of a global table. `fn(original, self, ...)` gets the original first. Waits if the global is not defined yet. If `fn` errors, the original runs. **Session-gated** (below). |
| `obsidian.wrap(target, method, fn)` | The same, but **always runs**, also in an uncleared lobby and outside expansion content. For the way into an expansion, or a mod with replaced files that cannot be switched off. Anything else uses `hook`. |
| `obsidian.on_require(name, fn)` | Calls `fn(module)` when the game loads the script `name` (`"lua/settings/perk_settings"`). Use it to adjust a settings table right after the game builds it. |
| `obsidian.on_frame(fn, opts)` | Calls `fn` every frame. Return `true` to stop. Session mods: frames run only in a cleared lobby. `opts.always` (Obsidian 2.0.0) runs `fn` in any lobby, for work only this player sees; an older loader ignores it and gates the frame. |
| `obsidian.after_startup(fn)` | Calls `fn` once every mod has started. |
| `obsidian.keybind(id, fn, opts)` | Calls `fn` each time the key goes down. Session mod keys wait for a cleared lobby. `opts.always` leaves the key alone, for keys that act only on the screen of this player. |
| `obsidian.on_session(fn, opts)` | Calls `fn(on)` when the loader switches this mod on or off. Undo lasting changes when `on` is `false`. |

`obsidian.hook`, `on_frame`, `keybind` and `on_session` take `opts.part` (Obsidian 2.0.0) in a mod with parts: the registration belongs to that part (section 5).

```lua
obsidian.hook("Damage", "apply", function(original, target, amount, ...)
  return original(target, amount * 2, ...)
end)
```

### Hook versus wrap

- `hook`: for a session mod the call goes straight to the original while the lobby is not cleared, and the hook runs when it is. For an expansion, only while the content runs. Client mods always run. This is how session mods stay safe without extra code.
- `wrap`: the same safety if `fn` fails, but no gating. Use it only when a gated hook would leave one game half modded.
- Direct assignment (`Table.func = mine`) is never gated, runs in every lobby, and the loader cannot switch it off. Avoid it in session mods.

### Settings, text, state

| Call | Meaning |
|---|---|
| `obsidian.settings.get(id)` | Value of option `id`: the value the player chose, or the default. Changes in the app apply at next game start, with no deploy. |
| `obsidian.text(key, ...)` | Text from `locales/`, in the game language, English fallback. Extra args fill `%s` and `%d`. |
| `obsidian.log(...)` | Writes a line to the mod log. |
| `obsidian.storage.get(key, default)`, `set(key, value)`, `all()` | Strings, numbers and booleans kept between launches. `set(key, nil)` removes. Written at once, so never every frame. |
| `obsidian.toast(text, seconds)` | Short message at the top left. |
| `obsidian.notify(text, seconds)` | Message in the game hint box (default 7 s). Rare, important messages. Up to 3 waiting per mod, then `false, "queue_full"`. |

### Mods and scope

| Call | Meaning |
|---|---|
| `obsidian.module(name)`, `obsidian.import(id)` | See section 3. |
| `obsidian.info(id)` | `{ id, name, version, scope }` for a running mod, `nil` if it is not running. No `id` means the calling mod. Use `info("obsidian.api").version` for version gates. |
| `obsidian.scope()` | How the calling mod runs this deploy: `"client"`, `"session"`, `"hybrid"` (a client part and a session part on, Obsidian 2.0.0) or `"expansion"`. |
| `obsidian.caller()` | Id of the mod that the running code belongs to. |
| `obsidian.session.cleared(part)` | `true` while the calling mod may run. With a part id: always `true` for a client part, `false` for a part that is off. |
| `obsidian.session.guard(t, free)` | A view of table `t` for other mods. Functions named in `free` work normally. All others answer `false, "needs_session"` for client callers and `false, "not_cleared"` when not cleared (for libraries). |
| `obsidian.session.members()` | Other players: `{ peer, obsidian, modset, consent }`. |
| `obsidian.guardrails()` | `{ consent, block_achievements, freeze_progress }` as the player set them. |
| `obsidian.expansion.start()`, `stop()`, `running(id)` | Expansion content control. Host only for start and stop. |

`obsidian.session.forfeit_progress`, `release_progress` and `hold_progress` do nothing and stay only for older mods.

### In-game UI calls

`obsidian.menu` (in-game window, F6, owned by Obsidian API) and `obsidian.ui` (redraw the game menus and HUD with a drawing kit) exist in the loader. New code should use `api.menu`, `api.mod_settings` and `api.ui` from Obsidian API. The full `obsidian.ui` call list (canvas, `on`, `mute`, `data`, `font`, `art`, `frame`, `prompt`) is in the Loader API Wiki page `app/src/wiki/46-loader-api.md`.

### Version gate pattern

```lua
local api = obsidian.import("obsidian.api")
local info = obsidian.info and obsidian.info("obsidian.api")
if not api or not feature.api_ok(info and info.version) then
  obsidian.log("needs a newer Obsidian API, found " .. tostring(info and info.version))
  return
end
if not obsidian.capabilities.on_frame then return end
```

`api_ok` compares version parts numerically; the template has one in `src/feature.lua`.

## 5. Session rules

### Scopes at runtime

- **Client**: runs everywhere. Cannot change the shared game. Calls to Obsidian API that change it answer `false, "needs_session"`.
- **Session**: loader switches the mod on and off. Gated: `hook`, `on_frame`, `keybind` (without `always`), UI handlers, menu pages.
- **Unspecified**: runs as client. If the mod changes the shared game, play only with people who run it too.

### When session mods run

| Situation | Session mods |
|---|---|
| Alone, friends-only or private lobby | Always run, with anyone, vanilla players included |
| Public lobby | Run only if every other player either runs the same set (same versions and option values), or runs Obsidian and does not block session mods of other players |
| Public lobby, a vanilla player present | Off |
| Public lobby, a player who blocks session mods, with a different set | Off |

"Cleared lobby" means the rule passes. Not cleared: hooks call only the original game code, frame functions and keys do not run, menu pages are not listed and close, and the Obsidian API effects and edits are taken off. They come back when the lobby clears. The check re-runs whenever someone joins, leaves, changes setup or the host changes who can join. A mod can undo lasting changes in `obsidian.on_session(function(on) ... end)`.

### Option values compared

For a session mod or expansion, every option value counts when the sets of two players are compared, so a balance slider must match. Mark personal options (`color`, camera distance) with `"scope": "client"` so players can differ and still match.

### every_player

`"every_player": true` makes the mod run only when every other player runs it too, at the same version and shared option values, in any lobby including friends-only. Allowing it is not enough. Obsidian switches it off, with a message, when someone without it joins. The check runs after a player is in the lobby, so leave the game as it was until `obsidian.session.cleared()` is true (for example, keep the vanilla lobby size until then).

### Session content and the Galactic War

Any deployed session content stops Galactic War and leaderboard results being sent, closes Proving Grounds, and limits matchmaking to Obsidian players when the content cannot switch off live (data overrides, resources, older imported mods). Expansion content does this only for missions the content ran in. These rules prevent accidents and are not anti-cheat.

### Mods with parts

Obsidian 2.0.0. A session mod with `parts` (section 2) tags each registration with the part it belongs to:

```lua
local VIEW = { part = "view" }
obsidian.hook("CameraManager", "update", update_camera, VIEW)
obsidian.on_frame(steer, VIEW)
obsidian.keybind("toggle_view", toggle, { part = "view", always = true })
obsidian.hook("FirearmComponent", "update_slaves", longer_range, { part = "weapon_range" })
```

- Code of a client part runs in any lobby; code of a session part only in a cleared one. In a lobby that isn't cleared the game names the session parts that went off and says the rest keeps working.
- A mod with a client part and a session part on is **hybrid**, shown with a diamond half green, half red. While any session part is on, the mod counts as session for the deploy: Galactic War results aren't sent and Proving Grounds is closed. With every session part switched off by the part options, the mod deploys as a client mod.
- Files of a client part are personal: they don't keep vanilla players out of a public lobby. Files without a part count as session content.
- Options of a client part count as `"scope": "client"`, and options of a part that is off don't count at all.
- One Lua state holds every part, so code of a client part can still call session code directly. Only the registrations are gated. Read what a session part changed each time instead of keeping a copy.
- A library the mod requires deploys as session while a session part is on, and the calls the library guards treat the whole mod as session. In a public lobby a client part gets `false, "not_cleared"` from guarded Obsidian API calls (`api.world.prop` is one). Use free calls or engine calls there: Integrated Third Person spawns the sky dome with `World.spawn_unit`.
- Code that runs once (the entry script, `on_require`) isn't tagged and isn't gated.
- What belongs in a client part: what this player sees, hears or presses. A camera is personal. Time scale and gravity aren't, though they run on one machine: the machines drift apart. Information other players don't get isn't personal either: patrol markers, fog taken away, a camera past the map bounds, spectating. Integrated Third Person keeps a longer view and an enemy radar in the client part as the price of the view behind the shoulder, which loses the top-down view of everything behind the player.
- Check `obsidian.capabilities.parts` before telling the player that the personal parts keep running: an older loader gates everything as session code.

### Things to avoid in session mods

- Replacing globals directly, or replacing game scripts with `resources` for gameplay: not switchable live.
- Sending network messages to other players outside the game code.
- Writing guarded values (`hitpoints_real`, `rounds`, `cooldown_timer`, `uses_left`, `num_grenades`, `extra_lives`): trips anti-tamper and cuts the player off the network. Use Obsidian API.
- Changing the progress of this player (XP, unlocks) is allowed, but XP reaches shared leaderboards.

### Libraries and expansions

- A library declares `"scope": "library"`, checks `obsidian.scope()`, registers gameplay hooks only when it is `"session"`, and exports `obsidian.session.guard(M, { "list", "count" })`.
- An expansion (`"scope": "expansion"`, `min_obsidian`, `requires` Obsidian API) enters through `wrap`, the menu or `obsidian.ui`, and the content in `hook`s. The host calls `obsidian.expansion.start()`, which answers `true` or `false, reason` (`players_missing`, `not_host`, `busy`, `not_expansion`). Every game in the lobby then gets `on_session(true)`. Check `obsidian.capabilities.expansion` first and return early if it is missing. Full details: `app/src/wiki/48-session-mods.md`.

## 6. Using Obsidian API

Obsidian API (id `obsidian.api`) is a library mod: game data by name, checked changes, and ready actions. It does nothing alone. Documentation is REFERENCE.md in github.com/Alomare/ObsidianAPI.

```json
"scope": "session",
"entry": "main.lua",
"requires": ["obsidian.api"]
```

```lua
local api = obsidian.import("obsidian.api")
```

Rules:

- A client mod can require it and stays a client mod. It can read data and use `api.ui`, `api.audio`, `api.music`, `api.map`, `api.events` and `api.mod_settings`. Anything that changes the shared game answers `false, "needs_session"`.
- API changes from a session mod run only while the lobby is cleared. Otherwise calls answer `false, "not_cleared"`. Give every effect a `remove`.
- Actions answer `true`, or `false` and a short reason (`needs_session`, `not_cleared`, `not_in_mission`, `host_only`, `no_avatar`, `not_available`, `bad_type`, `out_of_range`, ...). Nothing throws on an ordinary refusal: show or ignore the reason.
- Gate on the API version. Calls added in later releases are missing on older APIs. State the minimum in the README ("Needs Obsidian API 1.40.0 or later") and check it in `main.lua` (section 4).
- If an older API answers `not_ready` for a definition made in the main chunk (before the game has the data), retry on frames until it stops answering that. This is the pattern in HD1-MoreStratagems and HD1-SharedResupply:

```lua
local function define()
  local made, why = api.stratagems.define(def)
  if why == "not_ready" then return false end          -- try again next frame
  if not made and why ~= "taken" then obsidian.log("not added: " .. tostring(why)) end
  return true                                          -- true stops the frame calls
end
if not define() then obsidian.on_frame(define) end
```

- Frames stop while the mod is off (uncleared lobby, or a player without an `every_player` mod). Undo changes in `obsidian.on_session(function(on) if not on then ... end end)` and let the first frame after it clears put them back.

### REFERENCE.md sections

Contents of REFERENCE.md, by section name:

| Section | For |
|---|---|
| Using the API | requires, client versus session, answer reasons |
| The game and the players | `api.game`, `api.lobby`, `api.catalog`, and who is playing |
| Changes and effects | `api.edits` (settings tables, with undo), `api.effects` |
| Events | `api.events`, event names, kill streak example |
| Player and gear | `api.player`, `api.gear`, perks, backpacks, `api.vehicles` |
| Stratagems | cooldowns, calling, hiding, shared stratagems, `api.stratagems.define` |
| Enemies and missions | spawning, `api.enemies`, `api.mission`, `api.combat` |
| World, camera and map | positions, props, camera, photos, look of a mission, `api.map` |
| Sound and music | `api.audio`, `api.music` |
| Menus, messages and the save | `api.menu`, `api.ui`, `api.mod_settings`, `api.progress`, `api.console` |
| Bots | `api.bots` |
| Recipes | small complete mods to copy |
| Rules worth knowing | guarded values, uncatchable errors, ownership, session behaviour |
| Every call | generated list of all calls for the API version |

Where the guide and the generated "Every call" list disagree, the list is right. Read "Rules worth knowing" before touching game tables directly.

## 7. Options in game

Players change `obsidian.json` options in the app. Mods can also show rows in the game pause menu, under **Mods**, through `api.mod_settings`.

```lua
-- Rows bound to options need Obsidian API 1.16 (mod_settings.BINDS).
if api.mod_settings and api.mod_settings.BINDS then
  local page = api.mod_settings.page("Mod Name")
  local on = page:toggle("enabled", {
    option = true,                       -- same id as the manifest option
    default = true,
    label = { en = "Enable the feature", fr = "Activer la fonction" },
    info  = { en = "Turns the feature on or off." },
    on_change = function(v) feature_on = v end,
  })
  page:number("power", { option = true, label = "Power", min = 1, max = 10, step = 1, default = 2 })
end
```

- `page(title)`, then `page:toggle(id, opts)`, `page:choice(id, opts)` (`opts.choices` is `{ { id, label } }`), `page:number(id, opts)` (100 steps at most, `opts.format(value)`), `page:button(label, fn)`, `page:get(id)`, `page:set(id, value)`.
- With `opts.option = true`, the row is the manifest option with the same id. Give it the same choice ids, range and step. The row starts from `obsidian.settings.get(id)`, so build it at load. A change in game applies at once, and Obsidian moves it into the active profile while the game is closed.
- Labels can be strings or tables by language (`en`, `fr`, `es`, `pt-BR`). Shown in capitals.
- Rows without `option = true` are separate in-game settings, kept by Obsidian API.
- The page opens in any lobby. `api.mod_settings.pause_row(id, label, fn, opts)` adds a row to the pause menu itself.
- The in-game window (F6) is `api.menu.add(title, build, opts)` with `page:header`, `toggle`, `number`, `choice`, `action`, `input`, `page`. Session mod pages are not listed in an uncleared lobby.

## 8. Offline tests

Mod logic that needs no game is tested with plain LuaJIT 2.0. From the repository root:

```
luajit tests/run.lua
```

`tests/run.lua` pattern (copy from `assets/mod-template/tests/run.lua`):

- It defines a fake global `obsidian` with `module(name)` that does `dofile(name .. ".lua")` with a cache, so `src/*.lua` load as in game. Add more fake calls as the code needs them.
- It defines the helpers `eq(got, want, what)` and `yes(value, what)`.
- Each test file returns a list of `{ name, fn }`. The runner calls each with `xpcall`, prints failures with a traceback, prints `N passed, M failed`, and exits non-zero on failure.
- A test can return `"skip"` to be counted as skipped.

How to make code testable:

- Keep logic in `src/*.lua` as pure functions of plain values: version checks, level tables, target selection, text. `main.lua` does only wiring (hooks, frames, imports).
- Pass dependencies in (`squad.new(api, { preserve = ..., loadout = ..., log = ... })`) so a test can hand in a fake `api` and fake game tables.
- Write a small fake of the game parts touched (units, components, lobby) in `tests/fake.lua`. One fake is one machine; make two to test sharing between players.
- Useful extra tests: every module loads and is listed in `modules`; names in tools or build scripts match the manifest; texts follow the style rules.

LuaJIT 2.0 for testing comes from the manager repository: `tools/build-luajit.cmd` (Windows) or `sh tools/build-luajit.sh` builds `target/luajit/luajit` **(path per CONTRIBUTING.md)**. Any LuaJIT 2.x on the path works for these tests **(unconfirmed for other builds)**.

Tests prove the logic only. Hooks, frame order and game tables still need a run in the game, with the mod log open.

## 9. Releasing

### Changelog

`CHANGELOG.md` has a section per version, headed exactly `## <version>`. Each change is one line starting `New:`, `Changed:` or `Removed:`, brief and direct.

```
## 1.1.0

New: ...
Changed: ...
Removed: ...
```

The section becomes the release notes. The workflow stops if the section is missing.

### Tag and workflow

1. Raise `version` in `obsidian.json`.
2. Add the changelog section.
3. Commit, then push a tag `v<version>` (for example `v1.1.0`).

`.github/workflows/release.yml` (copy from the template) runs on tags `v*`. It checks that the tag matches `obsidian.json`, that the changelog has the section, then packs `git archive --format=zip --prefix="$id/" -o "$id-$version.zip"` and runs `gh release create` with the section as notes. The zip is named `<id>-<version>.zip`, for example `author.modname-1.0.0.zip`. A tag with a suffix (`v1.1.0-beta.1`) creates a prerelease, which Obsidian does not offer as an update: use it for a hand test.

### Updates

`"source": "https://github.com/author/repo"` lets players update from the app. Obsidian reads the latest release of a public repository, skips drafts and prereleases, and refuses a zip with a different id or a version that is not higher. If a release has several zips, the mod id in the zip name picks the right one.

Versioning: last number for fixes, middle for features and options, first for changes players should know before updating. Keep option and key ids stable.

### Nexus Mods

A second workflow can upload the same zip to Nexus Mods after the GitHub release. Enhanced Visuals (github.com/Alomare/HD1-EnhancedVisuals, `.github/workflows/nexus.yml` and `tools/nexus_release.py`) does it with `Nexus-Mods/upload-action`:

- The repository secret `NEXUS_API_KEY` holds a Nexus Mods API key. Stop the run with a message when the secret is missing, and never run the job with debug logging on: the action writes the key into the debug log, and the logs of a public repository are open to anyone.
- `mod_id` is the Unique Mod ID from the Files tab (Advanced): the game id shifted left 32 bits plus the mod number. HELLDIVERS (2015) is game 3552, so mods/48 is 3552 << 32 | 48 = 15255723835440.
- `file_id` is the File ID under API of the existing file. Each upload becomes a new version of that file, and `archive_existing_version: true` moves the old version to the archive.
- Send no changelog to Nexus: the release notes live on GitHub. Read the current title and description of the file from the Nexus API and send them back unchanged, so text edited on the page stays.
- A page that carries more than one mod, such as the Enhanced Visuals page that also holds Upscaled Textures, should keep `update_mod_version: false`: the version of the page then stays as set by hand.
- Skip prereleases, and allow a run by hand for a tag that's already out.

### Before releasing

1. Import the zip itself (not the folder) to test what players get.
2. Deploy, play a mission, read the mod log.
3. For a session mod, test with a player who does not run it: the mod must switch off.
4. State in the description what changes and whether other players notice.
5. English only in text until translations are added: English is always the fallback.

## 10. Deploying locally

### With the app

Download Obsidian Mod Manager from github.com/Alomare/ObsidianLauncher/releases (Windows 10 or 11, game installed through Steam).

1. Drop the mod folder (or a `.zip`) on the Mods tab, or press **+**.
2. Turn the mod on.
3. Close the game, press **Deploy**, then **Play**.

Importing a folder with the same id replaces the old copy. Raise `version` for shared releases. Deploy replaces all patches each time, so there is no need to purge first. **Purge** deletes everything Obsidian wrote and returns the game to vanilla. Game files are never edited. Saves are backed up before every deploy.

An option change needs only a quick deploy (nothing is rebuilt). A changed `when` option, or any resource, needs a full deploy, shown by the green Deploy button. Hot reload while the game runs is not supported **(unconfirmed)**: close the game before deploy.

### With the command line

`obsidian` is not in the downloads. Build it from the manager repository: `cargo build --release -p obsidian-core`, after running `tools\build-luajit.cmd` once for the LuaJIT 2.0 compiler. Run it with the game closed. `--game <folder>` points at another install.

```
obsidian import <mod folder or .zip>   add a mod to the library
obsidian list                          mods in load order, on or off
obsidian enable <id> / disable <id>
obsidian order <id>...                 put these mods first; later mods win conflicts
obsidian conflicts                     which mods change the same thing
obsidian deploy                        put the enabled mods into the game
obsidian purge                         take them out again
obsidian status                        game build, what is deployed
obsidian set <id> <option> <value>     change a mod option
obsidian key <id> <keybind> <key>      change a mod key
obsidian remove <id>                   delete a mod from the library
obsidian updates | update [<id>...]    check GitHub / install new versions
obsidian profile list|use|new <name>   named sets of mods and settings
obsidian consent on|off                play session mods with other Obsidian users who allow them
```

Typical loop:

```
obsidian import path/to/mod
obsidian enable author.modname
obsidian deploy
```

then start the game, read the logs, edit, and repeat. Problem reports include the output of `obsidian status`, `loader.log` and the list of enabled mods.
