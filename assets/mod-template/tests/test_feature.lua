local feature = obsidian.module("src/feature")

local T = {}
local function test(name, fn) T[#T + 1] = { name, fn } end

test("scale multiplies and caps", function()
	eq(feature.scale(10, 2), 20)
	eq(feature.scale(10, 2, 15), 15)
	eq(feature.scale(10, 0.5, 15), 5)
end)

test("api_ok compares versions part by part", function()
	eq(feature.api_ok("1.0.0"), true)
	eq(feature.api_ok("1.40.0"), true)
	eq(feature.api_ok("2.0"), true)
	eq(feature.api_ok(nil), false, "no version")
	eq(feature.api_ok("0.9.9"), false)
end)

test("the manifest lists every module", function()
	local f = assert(io.open("obsidian.json", "r"))
	local manifest = f:read("*a")
	f:close()
	yes(manifest:find('"src/feature.lua"', 1, true), "src/feature.lua in the manifest")
end)

return T
