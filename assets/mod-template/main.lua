-- Mod Name: entry script. The loader runs it once when the game boots.
local feature = obsidian.module("src/feature")

local api = obsidian.import("obsidian.api")
local api_info = obsidian.info and obsidian.info("obsidian.api")

-- Version gate: do nothing, and say why, when Obsidian API is missing or too old.
if not api or not feature.api_ok(api_info and api_info.version) then
	obsidian.log("Mod Name needs Obsidian API " .. feature.API_TEXT .. " or later, found " .. tostring(api_info and api_info.version))
	return
end

if obsidian.settings.get("enabled") then
	-- Hooks of a session mod call only the original game code while the lobby isn't cleared.
	obsidian.hook("SomeGameTable", "some_method", function(original, self, ...)
		return original(self, ...)
	end)
end

obsidian.log("Mod Name ready")
