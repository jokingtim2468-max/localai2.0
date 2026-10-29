--!strict
-- Upgrade shop. Every tier price is half of the reference game's. Stat effects are multipliers/adders applied
-- by Stats.lua. Categories and tiers will grow as more screenshots of the upgrade menus come in.
export type Tier = { id: string, name: string, price: number, hpMul: number?, hpAdd: number?, weightAdd: number?,
	topSpeedMul: number?, nitrousShot: number?, gripMul: number? }
export type Category = { id: string, name: string, group: string, tiers: { Tier } }

local C: { Category } = {
	{ id = "turbo", name = "Turbo & Gearing", group = "Engine", tiers = {
		{ id = "none",   name = "No Turbo",    price = 0 },
		{ id = "street", name = "Street Turbo", price = 37500, hpMul = 1.15 },
		{ id = "sport",  name = "Sport Turbo",  price = 55000, hpMul = 1.25 },
		{ id = "race",   name = "Race Turbo",   price = 75000, hpMul = 1.40 },
	} },
	{ id = "nitrous", name = "Nitrous", group = "Engine", tiers = {
		{ id = "none",   name = "No Nitrous",          price = 0 },
		{ id = "street", name = "Street 35 Shot",      price = 12500, nitrousShot = 35 },
		{ id = "strip",  name = "Strip 50 Shot",       price = 20000, nitrousShot = 50 },
		{ id = "race",   name = "Race 75 Shot + Heater", price = 30000, nitrousShot = 75 },
	} },
	{ id = "intake", name = "Intake", group = "Engine", tiers = {
		{ id = "stock", name = "Stock Airbox", price = 0 },
		{ id = "race",  name = "Race Velocity Stacks", price = 7500, hpAdd = 6 },
	} },
	{ id = "exhaust", name = "Exhaust", group = "Engine", tiers = {
		{ id = "stock", name = "Stock Exhaust", price = 0 },
		{ id = "slip",  name = "Slip-on", price = 5000, hpAdd = 3, weightAdd = -2 },
		{ id = "full",  name = "Heat-Treated Full System", price = 12500, hpAdd = 8, weightAdd = -5 },
	} },
	{ id = "ecu", name = "ECU & Fuelling", group = "Engine", tiers = {
		{ id = "stock", name = "Stock ECU", price = 0 },
		{ id = "flash", name = "ECU Flash", price = 7500, hpAdd = 5 },
		{ id = "race",  name = "Race Kit Loom", price = 15000, hpAdd = 10, topSpeedMul = 1.02 },
	} },
}

local byId: { [string]: Category } = {}
for _, c in C do byId[c.id] = c end

-- Menu groups (same layout as the reference garage); empty ones get their parts later.
local groups = { "Engine", "Drivetrain", "Chassis", "Brakes", "Wheels & Tyres", "Bodywork", "Stunt", "Headlights",
	"Paint & Finish", "Tuning & Colours", "Number Plate", "Keychain", "360 Camera" }

return { list = C, byId = byId, groups = groups }
