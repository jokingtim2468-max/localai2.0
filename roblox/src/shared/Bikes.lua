--!strict
-- Bike lineup, weakest to strongest. Prices in in-game cash. Names are our own (no real brands/models).
-- hp / weightKg / topSpeedMph are base (stock) stats; upgrades add on top (see Upgrades + Stats).
export type Bike = { id: string, name: string, class: string, cc: number, price: number,
	hp: number, weightKg: number, topSpeedMph: number, starter: boolean? }

local Bikes: { Bike } = {
	{ id = "nt500",  name = "500",        class = "Naked Twin",      cc = 500,  price = 0,      hp = 48,  weightKg = 190, topSpeedMph = 110, starter = true },
	{ id = "st700",  name = "700",        class = "Sport Twin",      cc = 700,  price = 15000,  hp = 74,  weightKg = 186, topSpeedMph = 130 },
	{ id = "ss636",  name = "636",        class = "Supersport",      cc = 636,  price = 30000,  hp = 130, weightKg = 193, topSpeedMph = 160 },
	{ id = "ls1000", name = "1000 GX",    class = "Litre Sportbike", cc = 1000, price = 50000,  hp = 200, weightKg = 201, topSpeedMph = 180 },
	{ id = "cp1000", name = "1000 CP",    class = "Crossplane",      cc = 1000, price = 75000,  hp = 200, weightKg = 199, topSpeedMph = 182 },
	{ id = "sb1000", name = "1K RR",      class = "Superbike",       cc = 1000, price = 100000, hp = 207, weightKg = 197, topSpeedMph = 186 },
	{ id = "hm1000", name = "X10R 1000",  class = "Homologation",    cc = 1000, price = 120000, hp = 215, weightKg = 193, topSpeedMph = 188 },
	{ id = "sc1000", name = "1000 SC",    class = "Supercharged",    cc = 1000, price = 150000, hp = 228, weightKg = 216, topSpeedMph = 199 },
	{ id = "hb1340", name = "1340 Turbo", class = "Hyperbike",       cc = 1340, price = 200000, hp = 300, weightKg = 264, topSpeedMph = 220 },
	{ id = "hb1500", name = "1500 R",     class = "Hyperbike 1500",  cc = 1500, price = 250000, hp = 330, weightKg = 270, topSpeedMph = 230 },
}

local byId: { [string]: Bike } = {}
for _, b in Bikes do byId[b.id] = b end

return { list = Bikes, byId = byId, starterId = "nt500" }
