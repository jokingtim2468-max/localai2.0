# Moto game (Roblox) — code
Rojo project (`default.project.json`). `src/shared` -> ReplicatedStorage.Shared, `src/server` -> ServerScriptService.
- `Bikes.lua`: lineup in power order, prices (500 free -> 1500 R 250k), base stats. Our own names, no brands.
- `Upgrades.lua`: upgrade categories/tiers (prices = half of the reference game). More coming from screenshots.
- `Stats.lua`: final stats from bike + fitted parts (client display + server truth).
- `Economy.server.lua`: server-authoritative cash / owned bikes / fitted parts, DataStore save, RemoteFunctions
  BuyBike, EquipBike, BuyUpgrade, GetGarage. Clients never set cash or stats.
Sync: install Rojo, `rojo serve` here, connect from the Roblox Studio Rojo plugin.
