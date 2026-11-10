# Working on this repository

This repository is a skill: instructions other agents read while modding HELLDIVERS (2015). These rules are for editing the skill itself. To use the skill on a mod, start at `SKILL.md`.

- Keep `SKILL.md` short: workflow, the rules that save the most time, and a table pointing into `references/`. Detail goes in the reference files.
- Write for any agent: plain Markdown, no tool names specific to one agent ("search the scripts", not the name of a particular tool).
- The repository is public. No local absolute paths, user names, or files from the game itself. Refer to public repositories and relative paths.
- Only write facts confirmed in game or in the game code. Mark anything inferred as inferred, and say which API version a fact needs.
- Tone: plain and serious. No flavour text. Don't write the word "its"; rephrase. No possessive forms in prose ("the game scripts", "the save of the player"). No em dashes.
- When a mod teaches something new (a trap, a limit, a pattern), add it to the reference file for that area, with the mod as the example.
- `assets/mod-template/` must keep passing the offline tests: run `luajit tests/run.lua` in that folder.
