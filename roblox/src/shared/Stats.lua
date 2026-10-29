--!strict
-- Final bike stats from the base bike + fitted upgrade tiers. Same code runs on client (display) and server (truth).
local Bikes = require(script.Parent.Bikes)
local Upgrades = require(script.Parent.Upgrades)

local Stats = {}

function Stats.compute(bikeId: string, fitted: { [string]: string })
	local b = Bikes.byId[bikeId]
	assert(b, "unknown bike " .. tostring(bikeId))
	local hp, weight, top, nitrous = b.hp, b.weightKg, b.topSpeedMph, 0
	local mul, topMul = 1, 1
	for catId, tierId in fitted do
		local cat = Upgrades.byId[catId]
		if cat then
			for _, t in cat.tiers do
				if t.id == tierId then
					mul *= t.hpMul or 1
					hp += t.hpAdd or 0
					weight += t.weightAdd or 0
					topMul *= t.topSpeedMul or 1
					nitrous = math.max(nitrous, t.nitrousShot or 0)
				end
			end
		end
	end
	hp *= mul
	return { hp = math.floor(hp + 0.5), weightKg = weight, topSpeedMph = math.floor(top * topMul * (hp / b.hp) ^ (1 / 3) + 0.5),
		nitrousShot = nitrous, powerToWeight = hp / weight }
end

return Stats
