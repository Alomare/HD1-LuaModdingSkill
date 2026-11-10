# HD1 Lua Modding Skill

Instructions and reference for AI coding agents that build Lua mods for HELLDIVERS (2015) with [Obsidian Mod Manager](https://github.com/Alomare/ObsidianLauncher) and the [Obsidian API](https://github.com/Alomare/ObsidianAPI). It works with Claude Code and with any agent that can read Markdown files: Codex, Cursor, Gemini CLI, Copilot, Aider and others.

It covers the mod package and manifest, the game scripts and what to hook, multiplayer and session mods, camera mods, weapons and enemies, stratagems, HUD and menu drawing, graphics and textures, game modes, testing and releasing. Most of it comes from building and shipping real mods, such as [More Stratagems](https://github.com/Alomare/HD1-MoreStratagems) and [Shared Resupply](https://github.com/Alomare/HD1-SharedResupply).

## Contents

| Path | What it holds |
| --- | --- |
| `SKILL.md` | The entry point: workflow, main rules, where to read next |
| `references/obsidian-mods.md` | Mod folder, `obsidian.json`, loader calls, options, tests, releases |
| `references/engine.md` | The game scripts, components, network limits, how to find what to hook |
| `references/multiplayer.md` | Masters and slaves, session mods, sync channels, patterns |
| `references/stratagems.md` | Stratagem data, menus, loadouts, cooldowns, payloads, icons |
| `references/gameplay.md` | The camera frustum in gameplay, third person cameras, weapon range and aim, enemy detection, changes for one call |
| `references/ui.md` | HUD and menu drawing, shipped images and fonts, world-space drawing |
| `references/rendering.md` | Shading values, the render config, shader swaps, textures, lights |
| `references/game-modes.md` | Expansions and modes: mission seeds, maps, campaign safety, lobby sync |
| `references/live-testing.md` | Scripted in-game runs, probes and tester checklists |
| `references/orchestration.md` | Splitting a large mod across several agents |
| `assets/mod-template/` | A mod skeleton to copy, with working offline tests |

## Install

### Claude Code

Put the folder in a skills directory, named after the skill:

```
git clone https://github.com/Alomare/HD1-LuaModdingSkill ~/.claude/skills/hd1-lua-modding
```

Or in one project only: `<project>/.claude/skills/hd1-lua-modding`. Claude loads the skill when a task matches the description in `SKILL.md`.

### Other agents

Clone the folder anywhere, for example next to the mods you work on, then point the agent at `SKILL.md` from the instruction file the agent reads:

| Agent | Instruction file |
| --- | --- |
| Codex, and agents that read `AGENTS.md` | `AGENTS.md` in the mod repository |
| Gemini CLI | `GEMINI.md` |
| Cursor | a rule in `.cursor/rules/` |
| GitHub Copilot | `.github/copilot-instructions.md` |

Text to paste, with the path changed to where you cloned the skill:

```
For HELLDIVERS (2015) mod work, read hd1-lua-modding/SKILL.md first and follow it.
It says which file under hd1-lua-modding/references/ to read for each task.
```

The block at the top of `SKILL.md` between the `---` lines is metadata for Claude; other agents can ignore it.

## What you need

- Obsidian Mod Manager, and the game on Steam.
- LuaJIT 2.0 to run offline tests (the manager repository has a build script).
- A decompiled copy of the game scripts, for reading the game code. `references/engine.md` explains how to make one. Game files aren't redistributed here.

## License

MIT.
