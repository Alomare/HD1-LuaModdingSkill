-- The feature's logic as pure functions, so tests/run.lua can check it without the game.
local M = {}

-- The Obsidian API version this mod needs.
M.API = { 1, 0, 0 }
M.API_TEXT = "1.0.0"

-- Whether an Obsidian API of this version ("1.40.0") has what the mod needs.
function M.api_ok(version)
	local got = {}
	for n in tostring(version or ""):gmatch("%d+") do got[#got + 1] = tonumber(n) end
	if #got == 0 then return false end
	for i, want in ipairs(M.API) do
		local v = got[i] or 0
		if v ~= want then return v > want end
	end
	return true
end

-- Example pure function: scale a value and keep it inside a range.
function M.scale(value, factor, max)
	local out = value * factor
	if max and out > max then return max end
	return out
end

return M
