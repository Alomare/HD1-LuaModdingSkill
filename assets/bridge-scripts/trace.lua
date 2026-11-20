-- Traces the calls to a game method for some seconds: each call goes to the stream with the frame and
-- the types of the arguments, then the hook comes off by itself.
-- python tools/bridge.py -f assets/bridge-scripts/trace.lua StateGame update 2
-- python tools/bridge.py stream --clear
local class, method, seconds = ...
assert(class and method, "trace.lua <Class> <method> [seconds]")
seconds = tonumber(seconds) or 3
local target = g(class)
assert(type(target) == "table" and type(target[method]) == "function", class .. "." .. method .. " isn't a function now")
local calls, MAX = 0, 200
hook(class, method, function(original, ...)
	calls = calls + 1
	if calls <= MAX then
		local kinds = {}
		for i = 1, select("#", ...) do kinds[#kinds + 1] = type((select(i, ...))) end
		emit(class .. "." .. method, "call " .. calls, "(" .. table.concat(kinds, ", ") .. ")")
	end
	return original(...)
end)
local stop = os.clock() + seconds
every("trace " .. class .. "." .. method, function()
	if os.clock() < stop then return end
	unhook(class, method)
	emit(class .. "." .. method, "traced " .. calls .. " calls in " .. seconds .. " s" .. (calls > MAX and (", the first " .. MAX .. " streamed") or ""))
	return true
end)
return "tracing " .. class .. "." .. method .. " for " .. seconds .. " s"
