-- Where the game is: the state, the lobby, the Helldiver of this player and the enemies near it.
-- python tools/bridge.py -f assets/bridge-scripts/where.lua
local Unit = g("Unit")
print("state", api.game.state_name(), "alone", api.game.alone(), "host", api.game.is_host())
local unit = api.game.my_unit()
if not unit then
	print("no Helldiver right now")
	return
end
local p = Unit.world_position(unit, 0)
print(string.format("Helldiver at %.1f %.1f %.1f", p.x, p.y, p.z))
if api.game.in_mission() then
	print("enemies known", #api.enemies.list(), "within 30 m", #api.enemies.near(30))
	local bug, metres = api.enemies.nearest()
	if bug then print("nearest", api.enemies.info(bug).name, string.format("%.1f m", metres)) end
end
