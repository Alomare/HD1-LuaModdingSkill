# Rendering, shaders and textures

What a mod can change in how HELLDIVERS (2015) draws a frame, from the work on Enhanced Visuals, Upscaled Textures and Photo Mode (github.com/Alomare/HD1-EnhancedVisuals, HD1-UpscaledTextures, HD1-PhotoMode). These mods ship data resources, not only Lua. Facts were seen in game runs (paused frames compared pixel by pixel) unless marked **(inferred)**; build 6001293.

## Contents

1. Live values, no files
2. The render config
3. Shader libraries
4. Textures
5. Lights
6. Limits and risks

## 1. Live values, no files

Try these first. They need no resources and apply at once.

- **Shading environment values** per planet, through `api.world.shading`: `exposure` (planets 0.5 to 1.6), `bloom_threshold_offset` (threshold, knee), `vignette`, `vignette_opacity`, `color_grading_enabled`, fog (`fog_depth_range`, `fog_color`, `fog_sun_blend`), depth of field (`dof_amount`, near and far ranges), sun and ambient. Photo Mode's Look tab drives these.
- **Renderer settings**: `Application.set_renderer_setting(name, value)` flips the render config's dynamic branches at once. Settings the engine reads that no menu sets: `lod_object_multiplier` (model LOD distance; `api.world.detail` drives it), `particles_cast_shadows`. `lod_scatter_density` and `lod_decoration_density` are read by the executable with unknown ranges **(inferred)**. The tessellation settings reach the shaders but no shader reads them.
- The Graphics menu offers only brightness, shadow quality (512, 1024, 2048: `menu_screen_graphics.lua`), FXAA and depth of field.

## 2. The render config

The whole pipeline is one data resource, `core/rendering/renderer` in bundle `1a9c33dcd0301dfd` (28 KB), a compiled data tree. Enhanced Visuals reads and writes it byte for byte with a tree codec.

PC frame order: clear; G-buffer (albedo, normal, mask, all RGBA8, plus depth) and decals; linearized depth (R32F, metres); deferred shading (the sun's shadow map, one cascade per entry of `shadow_slice_depth_ranges`, shadow mask, global lighting, point and spot lights); sky, reflections, fog, water, transparents; tone mapping at the planet's fixed exposure; a four-level bloom pyramid, depth of field, colour grading (two 16x16x16 LUTs per planet); FXAA; world-space transparents and the HUD.

What has been done with it:

- **Unused chains wired in.** The game ships a full SSAO chain (`vo_ssao`, a depth-aware blur, `ssao_upscale`) and never runs it. Enhanced Visuals adds it to the deferred shading generator behind a dynamic branch. Also shipped and unused: an auto exposure chain (`filter:log_luminance`, `luminance_adaption`).
- **Fixed shadow map size** of 4096 or 8192 (the menu stops at 2048), and the point light cube raised from 1024 to 2048. The sun cascade ends at 18 to 21 m in the shading environments; the far end can be rewritten in place in the 220 shading environments.
- **Sky fix.** Past the level the game draws nothing, and old frames smear there under a free camera. Clearing albedo and normal in the clear pass, plus a sky dome, fixes it (found first by the Third Person Camera mod, used by Photo Mode and Enhanced Visuals).
- **Render scale** (scene targets at 1.5x or 2x the back buffer) is possible because every scene target follows `albedo`, but passes that draw into the back buffer need their own depth buffer at the back buffer size, and 33 pixel shaders divide by `back_buffer_size`. A named piece of work, unproven in game at the time of writing.

Material passes versus shader passes: a plain `"shader"` pass gets no shading environment values; the pass's constants stay 0. Run the pass as a `"material"` pass through the planet's shading material of the same name, and the values arrive. This cost Enhanced Visuals a release.

Only one mod can own the render config. Obsidian lets the last mod in the load order win a resource, so a mod that ships it sets `load_after` (Enhanced Visuals loads after Photo Mode and includes the sky fix so both agree).

## 3. Shader libraries

- One `shader_library` resource per shader permutation, named by murmur64 of the lowercase name (`omni_light:shadow_mapping`). It holds a packed header (constant buffers, variables by murmur32 name and offset, textures, render state, samplers), then each stage as a u32 size, a DXBC container and a binding table.
- **A replacement pixel shader that keeps the same bindings and variable offsets loads and runs.** Four replaced entries ran in game. Compile with `D3DCompile` from `d3dcompiler_47.dll` at `ps_4_0` or `vs_4_0`, as most game shaders are; the game also ships shader model 5 stages.
- Entries the PC game never runs, free to borrow for new passes: the `color_blind:*` set, `copy:maintain_aspect_ratio`, `copy:encode_as_rgbm`, `filter:log_luminance`, `tone_mapping:luminance_adaption`, `filter:gaussian_blur_13tap`, the `gbuffer_debug:*` set.
- A `shader_library_group` is `u32 0x35, u32 count, count x u64 name`. Adding a copied entry under a new name to a group should give a fresh slot **(inferred, unproven in game)**.
- New bindings (more textures, camera matrices) mean writing header records, which are only partly decoded. A fullscreen pass hands the `input` list over as `input_texture0..n`, so pick an entry with enough texture slots.
- Run a new shader offline first: Enhanced Visuals runs both the game's and the mod's pixel shaders on WARP over a test scene before any game run.
- A header that doesn't match the bytecode can crash at shader creation; a wrong binding draws garbage. Both show on the first frame.

## 4. Textures

- 13,072 texture entries but only 2,045 distinct textures: level bundles carry copies (median 2, up to 60). **Replace every copy**, or the old texture shows wherever one was left.
- Nothing is streamed. Every texture is whole inside the bundles, so a replacement is a plain resource, and a texture at double size loads with no crash (proven with a probe that striped each replaced texture magenta).
- Formats: DXT5, DXT1, ATI2/BC5 normal maps (two channels; the shader rebuilds the third), uncompressed 32-bit, a few DXT3. A resource is a plain DDS with every mip, then a 4-byte tail.
- Upscaling pipeline lessons from Upscaled Textures: upscale packed mask channels one at a time so maps don't bleed; pad tiling textures by wrapping the opposite edge; resize channel by channel (Pillow weights colour by alpha on RGBA and darkens it); skip cube maps and volume textures; compare each packed texture with the original (format, mip count, PSNR) before shipping. Interface textures gained too little to be worth it.
- A full replacement set is large (hundreds of MB zipped), so ship it as a separate mod or optional download.

## 5. Lights

- Unit lights (flashlights on night armour, stratagem beacons, level lamps) can cast shadows: `Light.set_casts_shadows`, found with `Unit.num_lights` and `Unit.light`. Each shadowed spot light redraws the sun's shadow map, so frame time grows with the count. Enhanced Visuals removed the option before release.
- Photo Mode places lights with `api.world.light(pos, { shadows = true })`, a hidden stratagem beacon with the light taken over. Unseen shapes in levels block those lights.
- Muzzle flashes, explosions and fire are particle lights, out of reach from Lua.

## 6. Limits and risks

- Everything here draws on one machine only. A client mod is enough.
- A bad render config or shader header stops the game at boot or on the first frame. Switching the mod off in Obsidian recovers.
- An engine call with wrong arguments can crash past `pcall`. Probe a new engine call alone before building on it (for example `ShadingEnvironment.set_array_vector2`, whose argument order is unproven).
- Render config and shadow options apply at the next launch; dynamic-branch options apply live.
- Out of reach: TAA (no motion vectors), MSAA (deferred RGBA8 G-buffer), new light types or G-buffer channels (need the executable). Anisotropic filtering works from the GPU driver; the sampler records aren't decoded.
- Judge performance on a mid-range card, not a laptop GPU.
