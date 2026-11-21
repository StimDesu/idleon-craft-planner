# IdleOn Craft Planner

**Live page: https://stimdesu.github.io/idleon-craft-planner/**

A Legends of Idleon anvil planner. Load your save, pick what you want to craft from the anvil tabs, and the page shows the materials you need, what you have, what is missing, and how much ore to smelt into bars.

The page picks English or Russian from your browser language; the EN/RU switch in the corner overrides it.

## What it does

- **Anvil.** All 7 anvil tabs (72px game icons) with the game's icons, in the game's order. Each item shows its Smithing level and how many you can craft right now. Without a save every recipe is shown. With a save only unlocked recipes are shown; tick “Show locked recipes” to see them all, dimmed, with the game's own unlock hint in the tooltip. The search box looks through every tab. Tabs not opened yet with an “Anvil Tab N” item (`CYAnvilTabsOwned` in the save) are marked ⛔: recipes found there don't count as craftable, and the page offers to plan the Anvil Tab item.
- **Plan.** Click an item to add 1 (Shift+click adds 10) and edit the amounts. The plan warns when a recipe is still locked or needs a higher Smithing level than your best character, and totals the crafts and Smithing EXP.
- **Materials.** Needed, owned and missing for every material, grouped like in the game. With “Craft missing anvil parts too” on, ingredients that are anvil items themselves (helmets, pouches, Log Fries…) are crafted from their own recipes when you don't have enough, and their materials are added.
- **Forge.** Oil picker with icons and your stock, what each forge slot holds right now (ore, oil, bars, Brimstone slots outlined, bars per smelt), and for every missing bar: how many smelts, how much ore (expected and worst case), the ore you have and still miss, and how much oil burns on average.
- **My resources.** Bars, ores, logs, monster drops, materials, fish, bugs, critters, souls and oils you own, counted over storage, character inventories and the forge (both last two can be switched off).

## Smelting

Taken from the game code (`ForgeEtcDetails("BarsMade")` and the forge tick):

- Each smelt eats the ore's fixed amount (2 Copper, 4 Iron, 7 Gold, 16 Platinum, … 20000 Prehistrium) and makes `(1 + Extra Bars%/100) × (1 + oil%/100) × 1.5 if Brimstone slot` bars. The whole part always drops, the fractional part is a chance roll. The planner uses the expected value and also shows the worst case, where every roll fails.
- Double-bar oils: Toxic Sludge +20% (60% chance to burn per smelt), Magma Barrel +40% (50%), Plasma Barrel +60% (30%). The Fossil Fuel Legislation bribe says it cuts that chance to 80%, but the code multiplies it by `1 − 0.2/100`, so it barely changes anything; the planner follows the code.
- Extra Bars level, Brimstone slots and the bribe are read from the save (`ForgeLV[4]`, `GemItemsPurchased[104]`, `BribeStatus[9]`); the oil defaults to the double-bar oil in your forge, or the strongest one you own. A Brimstone slot is a forge slot bought in the gem shop (“Brimstone Forge Slot”): bought slots are the first ones in the forge. All of them can be changed by hand.

## How to get your save

**By username.** Publish your profile on [idleonefficiency.com](https://www.idleonefficiency.com), then type your IdleOn username and press “Load by username”. The page reads `cdn.idleonefficiency.com/profiles/<username>.json`, so it shows your data as of your last publish. A link with the username after `#` opens that profile directly: `https://stimdesu.github.io/idleon-craft-planner/#YourName`.

**By raw data.** Paste or open a raw save export (for example “Raw data” from IdleOn Efficiency). Both a flat export and `{ "data": {...}, "charNames": [...] }` work. The page reads `ChestOrder`/`ChestQuantity`, `InventoryOrder_N`/`ItemQTY_N`, `Lv0_N` (Smithing level), `AnvilCraftStatus` (`-1` = recipe locked), `ForgeItemOrder`/`ForgeItemQty`, `ForgeLV`, `GemItemsPurchased` and `BribeStatus`. A pasted save stays in your browser; nothing is uploaded.

## Data from the game

Every number and icon comes from the Steam game files, not from a wiki:

- `tools/extract.py` opens `resources/app.asar` (or the untouched `app.asar.ru-backup` if the Russian translation is installed), reads the game code `N.js` and the asset pack `default.pak`;
- recipes come from `ItemToCraftNAME`, `ItemToCraftCostTYPE`, `ItemToCraftEXP` and `AnvilRecipeHints`, item names and types from the item definitions, ore amounts and oil effects from the ore and oil items;
- the item icons are packed into `img/items.png`;
- Russian item names and hints come from the IdleOn-Rusificator dictionaries (`translation/`) when that folder sits next to this one.

After a game update:

```
python tools/extract.py --game "D:\Games\SteamLibrary\steamapps\common\Legends of Idleon"
python build.py
```

`index.html` is generated from `src/template.html` and `src/data.json`; edit the template, not the page. Python 3 with Pillow is needed for the extraction, nothing for the page itself.

Legends of Idleon and its art belong to Lavaflame2. This is an unofficial fan tool. Interface idea: [IdleOn Toolbox item planner](https://idleontoolbox.com/tools/item-planner).
