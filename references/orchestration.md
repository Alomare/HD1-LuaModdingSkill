# Splitting a mod across agents

A mod with several independent parts (research, icon, manifest, API calls, gameplay) can be built by one lead agent handing parts to helper agents, each on a model and effort level matched to the part. This kept the lead's context small when building Shared Resupply. It applies to any agent setup that can start helpers; with none, do the parts in the same order yourself.

## How the lead works

- The lead writes the briefs, decides between steps, checks every result and assembles. It doesn't redo the helpers' reading.
- Every helper starts with no context. A brief names exact paths, what was already found (so it isn't researched again), the files the helper owns, what it must not touch, and what to return with a word limit. The return is the only thing the lead sees.
- Tell helpers not to commit, bump versions or edit changelogs; the lead does those once, at the end.
- Give parallel helpers separate files. Two helpers editing one file at the same time lose work.
- For follow-up fixes, send them back to the helper that wrote the code. That helper keeps the context and doesn't need to read everything again.

## Order for a typical mod

| Step | Model and effort | Why |
| --- | --- | --- |
| 1. Research: where the feature lives in the game scripts and the API, known limits | mid model, medium | Lots of reading, only conclusions needed |
| 2. Feasibility study for anything risky (slot counts, network fields, sync) | strongest model, high | A wrong design costs the most; find hard limits before building |
| 3. In parallel: mod skeleton; icon or asset; small API calls | small model for skeleton and assets, mid model for API calls | Mechanical, or contained |
| 4. Core gameplay plus the API calls it needs, together | strongest model, high | The API shape and the gameplay code inform each other |
| 5. Release prep: README, changelog, workflow | small model, low | Mirrors other mods |

The lead runs both test suites itself before committing, looks at any image output itself, and hands the in-game test to a person.

## What to check in helper output

- Tests pass when the lead runs them, not only in the report.
- Images: compare with the game's own (a recolour can wash out a symbol).
- Conflicts between helpers' designs: two helpers may each assume something the other changed (for example, one hides an entry and shifts the index the other relies on).
- Rules the helper broke while trying to help, such as shipping a file the other mods leave out of the zip.
- Generated files committed by accident (`__pycache__`, previews).

## Cost

Helpers on the strongest model cost the most; most of a mod's tokens go to the core build. Small-model helpers handle skeletons, recolours and release files well. The saving comes from the lead never loading the files the helpers read.
