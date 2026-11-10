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
| A gui the mod makes on the world of the state | Things that must sit under the game menu gui, such as a 3D character picture behind a panel | Dies with the state. Heroic UI draws the Loadout character this way, because a canvas panel would cover it |
| Calls to the game screen classes | A screen that should look exactly like a game screen | Inside a menu screen the game helpers draw for the mod: `draw_main_panel`, the `selectionbox_01` bar, the `bar_difficulty` bar with `CampaignSettings.difficulty_bar`, `MapWidget(seed)` for a map preview |
| `api.mod_settings` pages | Option rows in the pause menu | See `obsidian-mods.md` section 7 |

Layer order, bottom to top, as Heroic UI uses it: the 3D world, the under gui of the mod, the game menu gui, the canvas.

Inside one drawing kit the guis draw in a fixed order on the same layer: shapes, then the game HUD images (`kit:icon`), then text and art from the mod. Anything drawn on top of a `basicbox_01` box needs a higher layer.

Game HUD images a kit can draw in a mission: `basicbox_01` (the dark gradient box, 24x380 with a 3 pixel black edge), `hud_icon_color_gradient_01` (the fading bar the name bars tint), `wing_01` (the chrome title wings), stratagem icons and rank icons. Perk icons don't draw in a mission: `kit:icon` draws only images the game has loaded on that screen.

## 2. Coordinates and screens

- Lay out in a fixed 1920x1080 space, scaled by the window and the UI scale setting, centred in the window. Every UI mod here does this.
- Every state letterboxes to `GameSettings.max_aspect_ratio`. On a 21:9 screen a 1920x1080 frame is a 16:9 area in the middle; a backdrop meant to fill the screen has to reach past it. Obsidian Patches ships a widescreen fix that removes the bars and moves the objective list, dialogue boxes and galaxy map panels to the real edges.
- The galaxy map gui is a 1280x720 frame, centred like a 1920x1080 kit frame, so a kit draws over a galaxy map panel at 1.5 times the numbers of the panel.
- The game HUD scales from the screen size over the 1280x720 design size (`hd_gui.lua`).
- A world position to pixels: `CameraManager:world_to_screen(position)`, or `api.world.to_screen(position)`.
- Follow the UI scale setting for anything attached to a Helldiver or an enemy, as the bars and rings of Better HUD do.

## 3. Redrawing a game screen

- Let the screen `update` run. It holds input, network sync and save writes. Stop only the drawing (`obsidian.ui.mute` in the loader), then draw over it.
- The game tests the mouse against where it would have drawn each element. When a mod moves an element, map the game hit rectangles to the new places (`obsidian.ui.remap_hits` hands the mod each rectangle). Heroic UI works out which element a rectangle belongs to from the size and place of the rectangle in the 1280x720 columns of the game.
- Some positions are locals of a draw function and can't be read or set from outside. Helldivers Arcade moves a loadout slot by moving the 58x58 pieces of the slot while `draw_menu` runs.
- Texts can be swapped only while a screen draws: `api.ui.with_texts`. A screen may read a text at another moment, such as when Back is pressed, so swap it there too.
- A whole new screen can reuse a game class. Helldivers Arcade registers a second `MenuScreenProvingGroundsMission` in `MenuScreenCampaign.states` and adds a tab to `substate_object.substates` in `MenuScreenCampaignRegion`.
- When a free camera or Photo Mode is active, hide mod drawing: the Obsidian API `photo_mode` effect is on while Photo Mode runs, and Helldivers Arcade draws nothing on the canvas then.

## 4. Images and fonts a mod ships

- Put UI art in the boot bundle `9cf71054ea26dddf`: it loads before anything runs and never unloads, so the art draws in every state.
- A texture resource is a plain DDS followed by four zero bytes. Atlases here are DXT5; backdrops and icon pods are uncompressed RGBA.
- The usual material uses the font material template of the game. The template shader multiplies the texture by the vertex colour, so a white atlas draws in any tint. Heroic UI, Photo Mode (film grain) and Helldivers Arcade (card icons) all ship art this way, built by a Python script (`tools/build_art.py`, `tools/build_grain.py`) that writes the texture, the material and a Lua table of where each image sits.
- Stratagem icons: see `stratagems.md` section 8.
- Replacing a game texture changes every screen that uses it, including screens the mod doesn't draw. Heroic UI replaces 55 stratagem textures, the shared panel texture and the two body fonts.
- Fonts: a font can be replaced as a `font` resource. Heroic UI bakes Barlow as the two body fonts of the game and copies the key glyphs (the controller and keyboard symbols) in from the originals, or prompts lose the key icons.
- Replaced resources load at game start. Changing one needs a full deploy and a restart.
- Art from other sources (a wiki, a concept artist) needs permission before a public release. Keep a NOTICE file.

## 5. Drawing in the world

- `World.create_world_gui(world, Matrix4x4.identity(), 1, 1, "immediate", "material", <a material from the mod>)` makes a gui in the 3D world. Draw with `Gui.bitmap_3d_uv`, with the camera rotation as the transform so the quad faces the camera. The quad lies in the x and z of the transform. Nothing goes over the network.
- A plain unit can be a visual: `World.spawn_unit` with a unit from a loaded package, scaled with `Unit.set_local_scale` (`api.world.prop`). Helldivers Arcade shows XP as the faction research samples this way. A unit from a package that isn't loaded stops the game.

## 6. Text and input

- Text in four languages: `LocalizationManager.current_language` is `en`, `fr`, `es` or `bp` (Brazilian Portuguese). Accented characters draw in the game fonts.
- Keys: `Keyboard.button_index(name)`, `Keyboard.pressed(index)` (one frame per press).
- On the galaxy map, keyboard arrows reach `handle_input` as `up` and `down` for one frame, Q is back, E is select, and Enter opens the text chat.
- A mod that reads several controllers makes a separate input interface (`PadManager:get_inputs`), as the Obsidian in-game menu does. Each local player has a `pad_number`.
- A mod menu with a separate mouse cursor: call `Window.set_cursor("")` for the system arrow. `Window.set_cursor()` with no argument read through a null pointer inside the executable and crashed the game past any `pcall`.
- A click that closes a mod window must wait for the button to come up, or the rest of the click reaches the game screen behind it.
- `Mouse.axis(Mouse.axis_index("cursor"))` is the cursor in pixels from the bottom left, the same origin as `obsidian.ui.canvas`.

The aim cursor, from the game scripts (`cursor_manager.lua`, `input_component.lua`):

- The aim cursor is a hardware cursor. `CursorManager:set_cursor(path)` ends in `Window.set_cursor`, with `_large` added for the large cursor option. Paths: `hud/cursors/game` (aiming), `game_inactive` (between shots), `game_transition_01` to `05` (played 0.035 s apart between those two), `menu`, and `invisible`, which `set_show_cursor(false)` sets.
- `InputComponent.update_masters` picks the cursor each frame, for the keyboard and mouse only. Aiming, firing or throwing shows `game`. Otherwise the cursor is `game_inactive` when the crosshair option in the game settings keeps the crosshair on screen. With that option off, the cursor hides and the game draws `cursor_game` with `Gui.bitmap_uv`, flying back to the weapon as it shrinks.
- A controller has no cursor in the top-down view.
- Custom Crosshair (github.com/Alomare/HD1-CustomCrosshair) hooks `Window.set_cursor` and passes `hud/cursors/invisible` in place of the aim paths, drops the `cursor_game` image by swapping `Gui.bitmap_uv` while `update_masters` runs, and draws a crosshair on a canvas at the cursor **(unproven in game)**.

## 7. Sharing UI with other mods

A mod can export drawing calls from `main.lua` for other mods, which reach them with `obsidian.import(id)`. Better HUD exports `grenade_meter(unit, fraction)`, `flash_health(unit, seconds)`, `status_buildup(unit, kind, fraction, drain, icon)` and `status_effect(unit, kind, seconds, icon)`; an icon is `{ art = material, uv = { u0, v0, u1, v1 } }` for an image from the mod or `{ icon = name }` for a game image. Helldivers Arcade uses them to show upgrade build-ups over enemy bars. Drop entries for units that are gone, and document the calls in the README.

Integrated Third Person exports `active()`, `crosshair()` (where shots go, `{ x, y, aiming, vehicle }` in canvas pixels, or `nil` in the top-down view) and `claim_crosshair(mod_id)`, after which it stops drawing the built-in crosshair. Custom Crosshair claims it and draws in place of it. Better HUD asks `active()` and stops pinning bars to the screen edge while the view is behind the shoulder. A mod that only reads another mod this way doesn't need to list it in `requires`: import on first use, keep the answer, and treat `nil` as "not installed".

## 8. Traps

- A gui that lists a material not loaded on the current screen can stop the game. `menu/menu` is loaded only on the ship.
- A sound world dies with the screen it belongs to. A sound id kept from a screen that closed took the game down.
- Draw calls run every frame: guard them, or one error freezes the game.
- Test at more than one UI scale and aspect ratio. Most findings here came from a 21:9 screen at UI scale 0.8; 16:9, gamepads and other languages each need a separate check.
