--!strict
-- Server-authoritative garage: cash, owned bikes, fitted upgrades. Clients only ASK; the server checks price and
-- ownership and saves to DataStore. (Anti-cheat: never trust client cash or stats.)
local Players = game:GetService("Players")
local DataStoreService = game:GetService("DataStoreService")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Shared = ReplicatedStorage:WaitForChild("Shared")
local Bikes = require(Shared.Bikes)
local Upgrades = require(Shared.Upgrades)

local store = DataStoreService:GetDataStore("Garage_v1")
local remotes = Instance.new("Folder"); remotes.Name = "GarageRemotes"; remotes.Parent = ReplicatedStorage
local function remote(name: string) local r = Instance.new("RemoteFunction"); r.Name = name; r.Parent = remotes; return r end
local buyBike, equipBike, buyUpgrade, getGarage = remote("BuyBike"), remote("EquipBike"), remote("BuyUpgrade"), remote("GetGarage")

type Garage = { cash: number, owned: { [string]: boolean }, equipped: string, fitted: { [string]: { [string]: string } },
	ownedParts: { [string]: { [string]: boolean } } }
local data: { [Player]: Garage } = {}

local function fresh(): Garage
	return { cash = 0, owned = { [Bikes.starterId] = true }, equipped = Bikes.starterId, fitted = {}, ownedParts = {} }
end

Players.PlayerAdded:Connect(function(p)
	local ok, saved = pcall(function() return store:GetAsync("u" .. p.UserId) end)
	data[p] = (ok and saved) or fresh()
	local ls = Instance.new("Folder"); ls.Name = "leaderstats"; ls.Parent = p
	local cash = Instance.new("IntValue"); cash.Name = "Cash"; cash.Value = data[p].cash; cash.Parent = ls
end)

local function save(p: Player)
	local g = data[p]; if not g then return end
	pcall(function() store:SetAsync("u" .. p.UserId, g) end)
end
Players.PlayerRemoving:Connect(function(p) save(p); data[p] = nil end)
game:BindToClose(function() for p in data do save(p) end end)

local function setCash(p: Player, v: number)
	data[p].cash = v
	local ls = p:FindFirstChild("leaderstats"); local c = ls and ls:FindFirstChild("Cash") :: IntValue?
	if c then c.Value = v end
end

buyBike.OnServerInvoke = function(p, bikeId: string)
	local g, b = data[p], Bikes.byId[bikeId]
	if not g or not b then return false, "unknown bike" end
	if g.owned[bikeId] then return false, "already owned" end
	if g.cash < b.price then return false, "not enough cash" end
	setCash(p, g.cash - b.price); g.owned[bikeId] = true
	return true
end

equipBike.OnServerInvoke = function(p, bikeId: string)
	local g = data[p]
	if not g or not g.owned[bikeId] then return false, "not owned" end
	g.equipped = bikeId
	return true
end

buyUpgrade.OnServerInvoke = function(p, catId: string, tierId: string)
	local g, cat = data[p], Upgrades.byId[catId]
	if not g or not cat then return false, "unknown part" end
	local tier
	for _, t in cat.tiers do if t.id == tierId then tier = t end end
	if not tier then return false, "unknown tier" end
	local bike = g.equipped
	g.ownedParts[bike] = g.ownedParts[bike] or {}
	local key = catId .. ":" .. tierId
	if not g.ownedParts[bike][key] then
		if g.cash < tier.price then return false, "not enough cash" end
		setCash(p, g.cash - tier.price); g.ownedParts[bike][key] = true
	end
	g.fitted[bike] = g.fitted[bike] or {}; g.fitted[bike][catId] = tierId
	return true
end

getGarage.OnServerInvoke = function(p) return data[p] end
