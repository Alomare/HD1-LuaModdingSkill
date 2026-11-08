# UI, HUD and menus

How mods draw in HELLDIVERS (2015): HUD additions, redrawn menus, images a mod ships, text in the 3D world. Learned while building Heroic UI, Better HUD, Photo Mode and Helldivers Arcade (github.com/Alomare/HD1-BetterHUD, HD1-PhotoMode, HD1-HelldiversArcade). Facts are from Steam build 6001293 and were seen in the running game unless marked **(inferred)**.

## Contents

1. Where to draw
2. Coordinates and screens
3. Redrawing a game screen
4. Images and fonts a mod ships
5. Drawing in the world
6. Text and input
7. Sharing UI with other mods
8. Traps

## 1. Where to draw

| Surface | Use | Notes |
| --- | --- | --- |
| Obsidian API `api.ui` canvas (loader `obsidian.ui`) | Most mod UI: HUD additions, panels, redrawn menus | On a world that outlives state changes. Search REFERENCE.md "Menus, messages and the save" |
| A gui the mod makes on the state's world | Things that must sit under the game's menu gui, such as a 3D character picture behind a panel | Dies with the state. Heroic UI draws the Loadout character this way, because a canvas panel would cover it |
| Calls of the game's own screen classes | A screen that should look exactly like the game's | Inside a menu screen the game's helpers draw for the mod: `draw_main_panel`, the `selectionbox_01` bar, the `bar_difficulty` bar with `CampaignSettings.difficulty_bar`, `MapWidget(seed)` for a map preview |
| `api.mod_settings` pages | Option rows in the pause menu | See `obsidian-mods.md` section 7 |

Layer order, bottom to top, as Heroic UI uses it: the 3D world, the mod's under gui, the game's menu gui, the canvas.

Inside one drawing kit the guis draw in a fixed order on the same layer: shapes, then the game's HUD images (`kit:icon`), then text and the mod's own art. Anything drawn on top of a `basicbox_01` box needs a higher layer.

Game HUD images a kit can draw in a mission: `basicbox_01` (the dark gradient box, 24x380 with a 3 pixel black edge), `hud_icon_color_gradient_01` (the fading bar the name bars tint), `wing_01` (the chrome title wings), stratagem icons and rank icons. Perk icons don't draw in a mission: `kit:icon` draws only images the game has loaded on that screen.

## 2. Coordinates and screens

- Lay out in a fixed 1920x1080 space, scaled by the window and the player's UI scale, centred in the window. Every UI mod here does this.
- Every state letterboxes to `GameSettings.max_aspect_ratio`. On a 21:9 screen a 1920x1080 frame is a 16:9 area in the middle; a backdrop meant to fill the screen has to reach past it. Obsidian Patches ships a widescreen fix that removes the bars and moves the objective list, dialogue boxes and galaxy map panels to the real edges.
- The galaxy map's gui is a 1280x720 frame, centred like a 1920x1080 kit frame, so a kit draws over a galaxy map panel at 1.5 times the panel's numbers.
- The game's HUD scales from the screen size over the 1280x720 design size (`hd_gui.lua`).
- A world position to pixels: `CameraManager:world_to_screen(position)`, or `api.world.to_screen(position)`.
- Follow the player's UI scale setting for anything attached to a Helldiver or an enemy. Better HUD's bars and rings do.

## 3. Redrawing a game screen

- Let the screen's `update` run. It holds input, network sync and save writes. Stop only the drawing (`obsidian.ui.mute` in the loader), then draw over it.
- The game tests the mouse against where it would have drawn each element. When a mod moves an element, map the game's hit rectangles to the new places (`obsidian.ui.remap_hits` hands the mod each rectangle). Heroic UI works out which element a rectangle belongs to from the rectangle's size and place in the game's 1280x720 columns.
- Some positions are locals of a draw function and can't be read or set from outside. Helldivers Arcade moves a loadout slot by moving the slot's 58x58 pieces while `draw_menu` runs.
- Texts can be swapped only while a screen draws: `api.ui.with_texts`. A screen may read a text at another moment, such as when Back is pressed, so swap it there too.
- A whole new screen can reuse a game class. Helldivers Arcade registers a second `MenuScreenProvingGroundsMission` in `MenuScreenCampaign.states` and adds a tab to `MenuScreenCampaignRegion`'s `substate_object.substates`.
- When a free camera or Photo Mode is active, hide mod drawing: Obsidian API's `photo_mode` effect is on while Photo Mode runs, and Helldivers Arcade draws nothing on the canvas then.

## 4. Images and fonts a mod ships

- Put UI art in the boot bundle `9cf71054ea26dddf`: it loads before anything runs and never unloads, so the art draws in every state.
- A texture resource is a plain DDS followed by four zero bytes. Atlases here are DXT5; backdrops and icon pods are uncompressed RGBA.
- The usual material uses the game's font material template, whose shader multiplies the texture by the vertex colour. A white atlas therefore draws in any tint. Heroic UI, Photo Mode (film grain) and Helldivers Arcade (card icons) all ship art this way, built by a Python script (`tools/build_art.py`, `tools/build_grain.py`) that writes the texture, the material and a Lua table of where each image sits.
- Stratagem icons: see `stratagems.md` section 8.
- Replacing a game texture changes every screen that uses it, including screens the mod doesn't draw. Heroic UI replaces 55 stratagem textures, the shared panel texture and the two body fonts.
- Fonts: a font can be replaced as a `font` resource. Heroic UI bakes Barlow as the game's two body fonts and copies the key glyphs (the controller and keyboard symbols) in from the originals, or prompts lose their key icons.
- Replaced resources load at game start. Changing one needs a full deploy and a restart.
- Art from other sources (a wiki, a concept artist) needs permission before a public release. Keep a NOTICE file.

## 5. Drawing in the world

- `World.create_world_gui(world, Matrix4x4.identity(), 1, 1, "immediate", "material", <the mod's material>)` makes a gui in the 3D world. Draw with `Gui.bitmap_3d_uv`, with the camera's rotation as the transform so the quad faces the camera. The quad lies in the transform's x and z. Nothing goes over the network.
- A plain unit can be a visual: `World.spawn_unit` with a unit whose package is loaded, scaled with `Unit.set_local_scale` (`api.world.prop`). Helldivers Arcade shows XP as the faction research samples this way. A unit whose package isn't loaded stops the game.

## 6. Text and input

- Text in four languages: `LocalizationManager.current_language` is `en`, `fr`, `es` or `bp` (Brazilian Portuguese). Accented characters draw in the game fonts.
- Keys: `Keyboard.button_index(name)`, `Keyboard.pressed(index)` (one frame per press).
- On the galaxy map, keyboard arrows reach `handle_input` as `up` and `down` for one frame, Q is back, E is select, and Enter opens the text chat.
- A mod that reads several controllers makes a separate input interface (`PadManager:get_inputs`), as Obsidian's in-game menu does. Each local player has a `pad_number`.
- A mod menu with a separate mouse cursor: call `Window.set_cursor("")` for the system arrow. `Window.set_cursor()` with no argument read through a null pointer inside the executable and crashed the game past any `pcall`.
- A click that closes a mod window must wait for the button to come up, or the rest of the click reaches the game's screen behind it.

## 7. Sharing UI with other mods

A mod can export drawing calls from `main.lua` for other mods, which reach them with `obsidian.import(id)`. Better HUD exports `grenade_meter(unit, fraction)`, `flash_health(unit, seconds)`, `status_buildup(unit, kind, fraction, drain, icon)` and `status_effect(unit, kind, seconds, icon)`; an icon is `{ art = material, uv = { u0, v0, u1, v1 } }` for a mod's own image or `{ icon = name }` for a game image. Helldivers Arcade uses them to show upgrade build-ups over enemy bars. Drop entries whose unit is gone, and document the calls in the README.

## 8. Traps

- A gui that lists a material not loaded on the current screen can stop the game. `menu/menu` is loaded only on the ship.
- Sound worlds die with their screen. A sound id kept from a screen that closed took the game down.
- Draw calls run every frame: guard them, or one error freezes the game.
- Test at more than one UI scale and aspect ratio. Most findings here came from a 21:9 screen at UI scale 0.8; 16:9, gamepads and other languages need their own look.
