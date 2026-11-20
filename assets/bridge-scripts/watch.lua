-- Watches a value by a path from the globals and streams each change, with the frame it changed in.
-- The path is dot separated; a part that is a number is a list index.
-- python tools/bridge.py -f assets/bridge-scripts/watch.lua MyModState.mode 30
-- python tools/bridge.py stream --follow
local path, seconds = ...
assert(path, "watch.lua <path> [seconds]")
seconds = tonumber(seconds) or 10
local function read()
	local v = nil
	for part in string.gmatch(path, "[^%.]+") do
		if v == nil then v = g(part) else v = v[tonumber(part) or part] end
		if type(v) ~= "table" and type(v) ~= "userdata" then break end
	end
	return v
end
local last = {}
local stop = os.clock() + seconds
every("watch " .. path, function()
	local ok, v = pcall(read)
	local text = ok and tostring(v) or ("error " .. tostring(v))
	if text ~= last.text then
		last.text = text
		emit(path, "=", text)
	end
	return os.clock() > stop
end)
return "watching " .. path .. " for " .. seconds .. " s"
