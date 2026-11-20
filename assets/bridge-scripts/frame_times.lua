-- Frame times over some seconds: the mean, the slowest frame and how many took more than 25 ms. The
-- result goes to the stream at the end.
-- python tools/bridge.py -f assets/bridge-scripts/frame_times.lua 5
-- python tools/bridge.py stream
local seconds = tonumber((...)) or 5
local n, sum, worst, slow = 0, 0, 0, 0
local stop = os.clock() + seconds
every("frame_times", function(dt)
	n, sum = n + 1, sum + dt
	if dt > worst then worst = dt end
	if dt > 0.025 then slow = slow + 1 end
	if os.clock() < stop then return end
	emit(string.format("frames %d, mean %.2f ms, slowest %.2f ms, over 25 ms %d", n, sum / math.max(n, 1) * 1000, worst * 1000, slow))
	return true
end)
return "measuring for " .. seconds .. " s"
