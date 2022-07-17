import asyncio
import wizwalker
from typing import Optional, Tuple, Union, List
from wizwalker.combat import CombatHandler, CombatCard, CombatMember
from wizwalker import utils, Client, Keycode
from wizwalker.memory import Window, DynamicWindow
from wizwalker.memory.memory_objects.enums import DuelPhase, SpellEffects, EffectTarget
# from wizwalker.memory.memory_object import MemoryObject
from loguru import logger
import asyncio
import math
from src.utils import is_visible_by_path, get_window_from_path
from src.paths import willcast_path


# Enchants
HIT_ENCHANTS = frozenset(['Strong', 'Giant', 'Monstrous', 'Gargantuan', 'Colossal', 'Epic', 'Keen Eyes', 'Accurate', 'Sniper', 'Unstoppable', 'Extraordinary', 'Solar Surge', 'Extract Undead', 'Extract Gobbler', 'Extract Mander', 'Extract Spider', 'Extract Colossus', 'Extract Cyclops', 'Extract Golems', 'Extract Draconians', 'Extract Treant', 'Extract Imp', 'Extract Pig', 'Extract Elephant', 'Extract Wyrm', 'Extract Wyrm', 'Extract Dinos', 'Extract Parrot', 'Extract Insects', "Extract Polar Bear"])
HEAL_ENCHANTS = frozenset(['Primordial', 'Radical'])
BLADE_ENCHANTS = frozenset(['Sharpened Blade'])
TRAP_ENCHANTS = frozenset(['Potent Trap'])
WARD_ENCHANTS = frozenset(['Bolstered Ward'])
GOLEM_ENCHANT = frozenset(['Golem: Taunt'])

# Auras
HIT_AURAS = frozenset(['Virulence', 'Frenzy', 'Berserk', 'Flawless', 'Infallible', 'Amplify', 'Magnify', 'Vengeance', 'Chastisement', 'Devotion', 'Furnace', 'Galvanic Field', 'Punishment', 'Reliquary', 'Sleet Storm', 'Reinforce', 'Eruption', 'Acrimony', 'Outpouring', 'Apologue', 'Rage', 'Intensify', 'Icewind', 'Recompense', 'Upheaval', 'Quicken'])
DEFENSE_AURAS = frozenset(['Fortify', 'Brace', 'Bulwark', 'Conviction'])
HEAL_AURAS = frozenset(['Cycle of Life', 'Mend', 'Renew', 'Empowerment', 'Adapt'])

# Shields
SELECT_SHIELDS = frozenset(['Bracing Frost', 'Bracing Wind',  'Bracing Breeze', 'Borrowed Time', 'Ancient Wraps', 'Aegis of Artemis', 'Frozen Armor', 'Tower Shield', 'Death Shield', 'Life Shield', 'Myth Shield', 'Fire Shield', 'Ice Shield', 'Storm Shield', 'Dream Shield', 'Legend Shield', 'Elemental Shield', 'Spirit Shield', 'Shadow Shield', 'Glacial Shield', 'Volcanic Shield', 'Ether Shield', 'Thermic Shield'])
AOE_SHIELDS = frozenset(['Armory of Artemis I', 'Armory of Artemis', 'Legion Shield', 'Mass Tower Shield'])
STUN_SHIELDS = frozenset(['Stun Block'])

# Blades
SELECT_BLADES = frozenset(['Catalyze', 'Fireblade', 'Deathblade', 'Iceblade', 'Stormblade', 'Lifeblade', 'Mythblade', 'Balanceblade', 'Precision', 'Dark Pact', 'Shadowblade', 'Elemental Blade', 'Spirit Blade', 'Aegis Deathblade', 'Aegis Mythblade', 'Aegis Lifeblade', 'Aegis Stormblade', 'Aegis Fireblade', 'Aegis Iceblade', 'Aegis Balanceblade'])
AOE_BLADES = frozenset(['Blind Strike', 'Bladestorm', 'Dragonlance', 'Blade Dance', 'Ion Wind', 'Chromatic Blast'])
SELF_BLADES = frozenset(['Supercharge'])
SELECT_PIERCE = frozenset(['Deathspear', 'Lifespear', 'Mythspear', 'Firespear', 'Icespear', 'Stormspear', 'Spirit Spear', 'Elemental Spear', 'Balancespear'])
AOE_HEAL_BLADES = frozenset(['Guidance', 'Brilliant Light'])
SELECT_HEAL_BLADES = frozenset(['Guiding Light', 'Precision', 'Guiding Armor'])

# Traps
SELECT_TRAPS = frozenset(["Elemental Trap",'Hex', 'Disarming Trap', 'Curse', 'Spirit Trap', 'Death Trap', 'Life Trap', 'Myth Trap', 'Storm Trap', 'Fire Trap', 'Backdraft', 'Feint', 'Ice Trap'])
AOE_TRAPS = frozenset(['Bewilder', 'Beastmoon Curse', 'Debilitate', 'Ambush', 'Mass Death Trap', 'Mass Life Trap', 'Mass Feint', 'Mass Myth Trap', 'Mass Fire Trap', 'Mass Ice Trap', 'Mass Storm Trap', 'Mass Hex', 'Malediction'])

# Globals
GLOBALS = frozenset(['Age of Reckoning', 'Astraphobia', 'Balance of Power', 'Balefrost', 'Circle of Thorns', 'Combustion', 'Counterforce', 'Darkwind', 'Deadzone', 'Doom and Gloom', 'Elemental Surge', 'Katabatic Wind', 'Namaste', 'Power Play', 'Saga of Heroes', 'Sanctuary', 'Spiritual Attunement', 'Time of Legend', 'Tide of Battle', 'Wyldfire', 'Elemental Surge', 'Dampen Magic'])

# Hits
SELECT_DOTS = frozenset(['Creeping Death', 'Cindertooth', 'Broiler', 'Bennu Alight', 'Befouling Brew', 'Link', 'Power Link', 'Inferno Salamander', 'Burning Rampage', 'Heck Hound', 'Wrath of Hades', 'Storm Hound', 'Frost Hound', 'Thunderstorm', 'Avenging Fossil', 'Frostbite', 'Spinysaur', 'Lightning Elf', 'Basilisk', 'Poison', 'Skeletal Dragon'])
SELECT_HITS = frozenset(['Firezilla', 'Earthwalker', 'Blight Hound', 'Gearhead Destroyer', 'Stone Colossus', 'Cyclonic Swarm', 'Doggone Frog', 'Disarming Spirit', 'Deadly Sting', 'Consume Life', 'Cripping Blow', 'Crystal Shard', 'Curse-Eater', 'Cursed Kitty', 'Contamination', 'Chill Bug', 'Conflagaration', 'Clever Imp', 'Chill Wind', 'Chilling Touch', 'Cheapshot', 'Chaotic Currents', 'Butcher Bat', 'Bull Rush', 'Blue Moon Bird', 'Bluster Blast', 'Bombardier Beetle', 'Blizzard Wind', 'Blitz Beast', 'Blood Boil', 'Bitter Chill', 'Bio-Gnomes', 'Blistering Bolt', 'Blazing Construct', 'Basic Bruiser', 'Bargain of Brass', 'Ballistic Bat', 'Backdrafter', 'Avenging Marid', 'Angelic Vigor', 'Death Scarab', 'Immolate', 'Efreet', 'King Artorius', 'Scion of Fire', "S'more Machine", 'Fire from Above', 'Sun Serpent', 'Brimstone Revenant', 'Hephaestus', 'Krampus', 'Nautilus Unleashed', 'Fire Cat', 'Fire Elf', 'Sunbird', 'Phoenix', 'Naphtha Scarab', 'Elemental Golem', 'Spirit Golem', 'Dream Golem', 'Ether Golem', 'Legend Golem', 'Volcanic Golem', 'Thermic Golem', 'Glacial Golem', 'Helephant', 'Frost Beetle', 'Snow Serpent', 'Evil Snowman', 'Ice Wyvern', 'Thieving Dragon', 'Colossus', 'Angry Snowpig', 'Handsome Fomori', 'Winter Moon', 'Woolly Mammoth', 'Lord of Winter', 'Abominable Weaver', 'Scion of Ice', 'Shatterhorn', 'Frostfeather', 'Imp', 'Leprechaun', 'Seraph', 'Sacred Charge', 'Centaur', 'Infestation', "Nature's Wrath", 'Goat Monk', 'Luminous Weaver', 'Gnomes!', 'Hungry Caterpillar', 'Grrnadier', 'Thunder Snake', 'Lightning Bats', 'Storm Shark', 'Kraken', 'Stormzilla', 'Stormwing', 'Triton', 'Catalan', 'Queen Calypso', 'Catch of the Day', 'Hammer of Thor', 'Wild Bolt', 'Insane Bolt', 'Leviathan', 'Storm Owl', 'Scion of Storm', "Rusalka's Wrath", 'Thunderman', 'Blood Bat', 'Troll', 'Cyclops', 'Minotaur', 'Vermin Virtuoso', 'Gobbler', 'Athena Battle Sight', 'Keeper of the Flame', 'Ninja Pigs', 'Splashsquatch', 'Medusa', 'Celestial Calendar', 'Scion of Myth', "Witch's House Call", 'Tatzlewurm Terror', 'Dark Sprite', 'Ghoul', 'Banshee', 'Vampire', 'Skeletal Pirate', 'Crimson Phantom', 'Wraith', 'Monster Mash', 'Headless Horseman', 'Lord of Night', "Dr. Von's Monster", 'Winged Sorrow', 'Scion of Death', 'Snack Attack', 'Scarab', 'Scorpion', 'Locust Swarm', 'Spectral Blast', 'Hydra', 'Loremaster', 'Ninja Piglets', 'Samoorai', 'Savage Paw', 'Spiritual Tribunal', 'Judgement', 'Vengeful Seraph', 'Chimera', 'Supernova', 'Mana Burn', 'Sabertooth', 'Gaze of Fate', 'Scion of Balance', 'Mockenspiel', 'Beary Surprise', 'Camp Bandit', 'Obsidian Colossus', 'Grim Reader', 'Dark & Stormy', "Barbarian's Saga", 'Quartermane', 'The Bantam', 'The Shadoe', 'Mandar', 'Dog Tracy', 'Buck Gordon', 'Duck Savage', 'Hunting Wyrm', 'Shift Piscean', 'Shift Grendel', 'Shift Rattlebones', 'Shift Greenoak', 'Shift Thornpaw', 'Shift Ogre', 'Shift Dread Paladin', 'Shift Sugar Glider', 'Shift Fire Dwarf', 'Van Der Borst', 'Shift Bunferatu', 'Shift Ghulture', 'Frost Minotaur', 'Deadly Minotaur', 'Lively Minotaur', 'Natural Attack', 'Storm Sweep', 'Cat Scratch', 'Colossal Uppercut', 'Colossus Crunch', 'Cursed Flame', 'Ignite', 'Flame Strike', 'Firestorm', 'Storm Strike', 'Maelstrom', 'Taco Toss', 'Stinky Salute', 'Ice Breaker', 'Ritual Blade', 'Mander Blast', 'Death Ninja Pig', 'Ninja Slice', 'Ninja Slam', 'Thunder Spike', 'Stomp', 'Swipe', 'Wrath of Aquila', 'Wrath of Cronus', 'Wrath of Apollo', 'Wrath of Zeus', 'Wrath of Poseidon', 'Wrath of Ares'])
AOE_DOTS = frozenset(["Death's Champion", "Champion's Blight", 'Scald', 'Wings of Fate', 'Rain of Fire', 'Fire Dragon', 'Reindeer Knight', 'Snow Angel', 'Deer Knight', 'Iron Curse'])
AOE_HITS = frozenset(['Confounding Fiend', 'Desperate Daimyo', 'Cursed Medusa', 'Cursed Medusa I', 'Cursed Medusa II', 'Confounding Fiend I', 'Colossal Scorpion', 'Cold Harvest', 'Bloodletter', 'Arctic Blast', 'Colossafrog', 'Raging Bull', 'Meteor Strike', 'Blizzard', 'Snowball Barrage', 'Frost Giant', "Ratatoskr's Spin", 'Forest Lord', 'Tempest', 'Storm Lord', 'Sirens', 'Glowbug Squall', 'Sound of Musicology', 'Humongofrog', 'Earthquake', 'Orthrus', 'Mystic Colossus', 'Ship of Fools', 'Scarecrow', 'Call of Khrulhu', 'Leafstorm', 'Sandstorm', 'Power Nova', 'Ra', 'Nested Fury', 'Squall Wyvern', "Morganthe's Will", 'Steel Giant', 'Lycian Chimera', 'Lernaean Hydra', 'Lord of Atonement', "Morganthe's Venom", 'Eirkur Axebreaker', 'Wildfire Treant', 'Lava Giant', 'Fiery Giant', 'Lava Lord', 'Lord of Blazes', 'Snowball Strike', "Morganthe's Gaze", 'Tundra Lord', "Morganthe's Angst", 'Squall Wyvern', 'Lord of the Squall', "Morganthe's Ardor", 'Enraged Forest Lord', "Morganthe's Requiem", 'Death Seraph', 'Ominous Scarecrow', 'Bonetree Lord', 'Fable Lord', 'Lord Humongofrog', 'Noble Humongofrog', "Morganthe's Deceit", 'Lord of the Jungle', 'Freeze Ray', "Old One's Endgame", 'Blast Off!', 'Lava Giant', 'Lava Lord', 'Snowball Strike'])
SELECT_SHADOW_HITS = frozenset(['Ultra Shadowstrike', 'Dark Nova', 'Shadowplume'])
AOE_SHADOW_HITS = frozenset(['Dark Fiend', 'Dark Shepherd'])
DIVIDE_HITS = frozenset(["Qismah's Curse", 'Iron Sultan', 'Sand Wurm', 'Snake Charmer', 'Climcaclysm', 'Scorching Scimitars', 'Lamassu'])
SELECT_WAND_HITS = frozenset(['Agony', 'Arctic Sting', 'Assail', 'Blaze', 'Blitz', 'Burst', 'Clash', 'Cold Slash', 'Conniption', 'Crusade', 'Crush', 'Cyclone', 'Dark Blow', 'Death Blow', 'Death Charge', 'Death Chill', 'Death Touch', 'Dread', 'Fire Scorch', 'Fire Slash', 'Fireball', 'Flare', 'Flash', 'Flux', 'Frostblight', 'Heroic Hit', 'Ice Blast', 'Ice Shard', 'Ice Slash', 'Impact', 'Inferno', 'Jolt', 'Justice Slash', 'Life Fury', 'Life Ire', 'Major Agony', 'Major Arctic Sting', 'Major Assail', 'Major Balance Burst', 'Major Blaze', 'Major Blitz', 'Major Burst', 'Major Chill', 'Major Clash', 'Major Conniption', 'Major Crusade', 'Major Crush', 'Major Cyclone', 'Major Dread', 'Major Fire Scorch', 'Major Fireball', 'Major Flare', 'Major Flash', 'Major Flux', 'Major Frostblight', 'Major Heroic Hit', 'Major Ice Blast', 'Major Ice Shard', 'Major Impact', 'Major Inferno', 'Major Jolt', 'Major Life Fury', 'Major Life Ire', 'Major Nova', 'Major Rage', 'Major Revile', 'Major Scorch', 'Major Scourge', 'Major Shadowplume', 'Major Shadowstrike', 'Major Shock', 'Major Snowburst', 'Major Spark', 'Major Strike', 'Major Surge', 'Major Torment', 'Major Vibrato', 'Major Wrath', 'Mana Burn', 'Mega Agony', 'Mega Arctic Sting', 'Mega Assail', 'Mega Blaze', 'Mega Blitz', 'Mega Burst', 'Mega Conniption', 'Mega Cyclone', 'Mega Dark Blow', 'Mega Frostblight', 'Mega Impact', 'Mega Inferno', 'Mega Jolt', 'Mega Nova', 'Mega Rage', 'Mega Shadowstrike', 'Mega Torment', 'Mighty Rage', 'Minor Chill', 'Minor Clash', 'Minor Cold Slash', 'Minor Crusade', 'Minor Crush', 'Minor Dark Blow', 'Minor Death Tap', 'Minor Fire Flare', 'Minor Fire Scorch', 'Minor Fireball', 'Minor Flash', 'Minor Heroic Hit', 'Minor Ice Blast', 'Minor Ice Shard', 'Minor Ice Slash', 'Minor Life Fury', 'Minor Life Ire', 'Minor Nova', 'Minor Shock', 'Minor Spark', 'Minor Strike', 'Minor Surge', 'Minor Wrath', 'Moon Beam', 'Mystic Slash', 'Rage', 'Revile', 'Rolling Thunder Bolt', 'Scorch', 'Shadow Slash', 'Shadowblast', 'Shadowplume', 'Shadowstrike', 'Shock', 'Sky Slash', 'Snowburst', 'Spark', 'Spirit Slash', 'Strike', 'Super Agony', 'Super Arctic Sting', 'Super Assail', 'Super Blaze', 'Super Blitz', 'Super Burst', 'Super Chill', 'Super Clash', 'Super Conniption', 'Super Crusade', 'Super Crush', 'Super Cyclone', 'Super Dark Blow', 'Super Death Tap', 'Super Dread', 'Super Fire Scorch', 'Super Fireball', 'Super Flare', 'Super Flash', 'Super Flux', 'Super Frostblight', 'Super Heroic Hit', 'Super Ice Blast', 'Super Ice Shard', 'Super Impact', 'Super Inferno', 'Super Jolt', 'Super Life Fury', 'Super Life Ire', 'Super Nova', 'Super Rage', 'Super Revile', 'Super Scorch', 'Super Shadowplume', 'Super Shadowstrike', 'Super Shock', 'Super Snowburst', 'Super Spark', 'Super Strike', 'Super Surge', 'Super Torment', 'Super Vibrato', 'Super Wrath', 'Surge', 'Torment', 'Ultra Agony', 'Ultra Arctic Sting', 'Ultra Assail', 'Ultra Blaze', 'Ultra Blitz', 'Ultra Burst', 'Ultra Conniption', 'Ultra Cyclone', 'Ultra Dark', 'Ultra Frostblight', 'Ultra Impact', 'Ultra Inferno', 'Ultra Jolt', 'Ultra Rage', 'Ultra Shadowstrike', 'Ultra Torment', 'Vibrato', 'Waves of Wrath', 'Wrath'])

# Minions
MINIONS = frozenset(['Call of the Pack', 'Test Dummy', 'Mander Minion', 'Nerys', 'Spectral Minion', 'Animate', 'Malduit', 'Fire Elemental', 'Sir Lamorak', 'Ice Guardian', 'Freddo', 'Sprite Guardian', 'Sir Bedevere', 'Troll Minion', 'Cyclops Minion', 'Minotaur Minion', 'Talos', 'Vassanji', 'Water Elemental', 'Mokompo'])
AOE_GOLEM_MINION = frozenset(['Golem Minion'])

# Shadow Creatures
OFFENSE_SHADOW = frozenset(['Shadow Shrike', 'Shadow Trickster'])
DEFENSE_SHADOW = frozenset(['Dark Protector', 'Shadow Sentinel'])
HEAL_SHADOW = frozenset(['Shadow Seraph'])

# Dispels
DISPELS = frozenset(['Quench', 'Melt', 'Dissipate', 'Vaporize', 'Entangle', 'Strangle', 'Unbalance', 'Spirit Defuse', 'Elemental Defuse'])

# Heals
SELECT_HEALS = frozenset(['Charming Pixie', 'Divine Intervention', 'Divine Spark', 'Dryad of Artemis', 'Cauterize', 'Beastmoon Brownie', 'Fairy', 'Dryad', 'Satyr', 'Guardian Spirit', 'Regenerate', 'Scion of Life', 'Minor Blessing', 'Healing Current', 'Sacrifice', 'Helping Hands', 'Availing Hands', "Grendel's Amends", 'Blessing', 'Cleansing Current', 'Gobble'])
AOE_HEALS = frozenset(['Pixie', 'Unicorn', 'Sprite Swarm', 'Pigsie', 'Rebirth', 'Hamadryad', 'Kiss of Death', 'Helping Hands', 'Availing Hands', 'Cat Nap', 'Restoring Hands'])

# Stuns
SELECT_STUNS = frozenset(['Freeze', 'Stun', 'Decelerate'])
AOE_STUNS = frozenset(['Petrify', 'Choke', 'Blinding Light', 'Blinding Freeze', 'Wall of Smoke', 'Shockwave'])

# Detonates
SELECT_DETONATES = frozenset(['Detonate', 'Solomon Crane', 'Dive-Bomber Beetle'])
AOE_DETONATES = frozenset(['Incindiate'])

# Prisms
SELECT_PRISMS = frozenset(['Elemental Prism', 'Spirit Prism', 'Death Prism', 'Life Prism', 'Myth Prism', 'Ice Prism', 'Fire Prism', 'Storm Prism'])
AOE_PRISMS = frozenset(['Mass Elemental Prism', 'Mass Spirit Prism', 'Mass Fire Prism', 'Mass Ice Prism', 'Mass Storm Prism', 'Mass Death Prism', 'Mass Life Prism', 'Mass Myth Prism'])

# Charm Debuffs
AOE_DEBUFFS = frozenset(['Plague', 'Virulent Plague', 'Smokescreen', 'Malediction', 'Mass Infection', 'Muzzle'])
SELECT_DEBUFFS = frozenset(['Weakness', 'Black Mantle', 'Bad Juju', 'Infection', 'Threefold Fever', 'Atrophy', 'Corruption', 'Diversion'])

# Minion Utilities
SELECT_MINION_UTILITIES = frozenset(['Shield Minion', 'Buff Minion', 'Siphon Health', 'Mend Minion', 'Draw Power', 'Dimension Shift', 'Steal Health', 'Sap Health', 'Take Power', 'Draw Health', 'Drain Health', 'Sap Power', 'Benevolent Bat', 'Cast-Iron Aegis', "Charalatan's Deceit", 'Charmed Scales', 'Cinderbird', 'Demoralize'])
SELECT_PACIFIES = frozenset(['Mega Pacify', 'Mega Distract', 'Mega Subdue', 'Mega Soothe', 'Mega Tranquilize', 'Mega Calm'])
AOE_PACIFIES = frozenset(['Pacify', 'Distract', 'Calm', 'Subdue', 'Soothe', 'Tranquilize'])
AOE_TAUNTS = frozenset(['Taunt', 'Mega Taunt', 'Provoke'])

# Polymorphs (based)
AOE_POLYMORPHS = frozenset(['Polymorph Jaguar', 'Polymorph Gobbler', 'Polymorph Beet', 'Polymorph Carrot', 'Polymorph Cat Bandit', 'Polymorph Colossus', 'Polymorph Disparagus', 'Polymorph Draconian', 'Polymorph Elemental', 'Polymorph Icehorn', 'Polymorph Mander', 'Polymorph Hound', 'Polymorph Ninja', 'Polymorph Peas', 'Polymorph Ptera', 'Polymorph Treant', 'Hatch'])

# Spell Type Utilities
SELECT_ENEMY_WARD_UTILITY = frozenset(['Shatter', 'Pierce'])
SELECT_ENEMY_BLADE_UTILITY = frozenset(['Steal Charm, Double Steal Charm', 'Enfeeble', 'Disarm', 'Backstab'])
SELECT_ENEMY_HOT_UTILITY = frozenset(['Snowdrift'])
SELECT_SELF_DOT_UTILITY = frozenset(['Triage', 'Shift'])
AOE_SELF_DOT_UTILITY = frozenset(['Mass Triage', 'Cooldown'])
SELECT_SELF_WEAKNESS_UTILITY = frozenset(['Cleanse Charm', 'Double Cleanse Charm'])
SELECT_SELF_TRAP_UTILITY = frozenset(['Cleanse Ward', 'Double Cleanse Ward'])
AOE_SELF_WEAKNESS_UTILITY = frozenset(['Empower'])
SELECT_ENEMY_MORE_PIPS_UTILITY = frozenset(['Steal Pip', 'Mana Burn'])
SELECT_RESHUFFLE = frozenset(["Reshuffle"]) 

# Roshambo Utilities
ENEMY_WARD_ROSHAMBO = frozenset(['Betrayal', 'Meltdown', "Oni's Forge", "Jinn's Defense"])
ENEMY_BLADE_ROSHAMBO = frozenset(['Wall of Blades', "Oni's Destruction", 'Putrefaction', "Jinn's Larceny"])
ENEMY_HOT_ROSHAMBO = frozenset(['Energy Transfer', "Jinn's Restoration", 'Contagion', "Oni's Morbidity", "Jinn's Fortune"])
SELF_TRAP_ROSHAMBO = frozenset(['Backfire', "Jinn's Reversal", 'Tranquility', "Oni's Naturalism", 'Righting the Scales'])
SELF_WEAKNESS_ROSHAMBO = frozenset(['Glacial Fortress', "Jinn's Vexation", 'Delusion', "Oni's Projection", 'Eye of Vigilance'])
SELF_DOT_ROSHAMBO = frozenset(['Reap the Whirlwind', "Oni's Attrition", 'Meditation', "Jinn's Affliction", "Jinn's Fortune"])
ONI_SHADOW_ROSHAMBO = frozenset(["Oni's Shadow"])

# Gambit Hits
SELF_WARD_ROSHAMBO_GAMBIT = frozenset(['Scion of Ice', 'Doom Oni', 'Phantastic Jinn'])
SELF_BLADE_ROSHAMBO_GAMBIT = frozenset(['Scion of Storm', 'Macabre Jinn', 'Primal Oni'])
ENEMY_TRAP_ROSHAMBO_GAMBIT = frozenset(['Caldera Jinn', 'Everwinter Oni', 'Scion of Myth'])
ENEMY_WEAKNESS_ROSHAMBO_GAMBIT = frozenset(['Iceburn Jinn', 'Turmoil Oni', 'Scion of Death'])
ENEMY_DOT_ROSHAMBO_GAMBIT = frozenset(['Scion of Fire', 'Verdurous Jinn', 'Trickster Oni', 'Duststorm Jinn'])
SELF_HOT_ROSHAMBO_GAMBIT = frozenset(['Infernal Oni', 'Thundering Jinn', 'Scion of Life'])
ENEMY_2_SHADS_ROSHAMBO_GAMBIT = frozenset(['Tribunal Oni'])
ENEMY_11_PIPS_ROSHAMBO_GAMBIT = frozenset(['Scion of Balance'])


# For spells with different spell logics in pvp
pvp_casting_logic_dict = {
	'Scion of Balance': 'Enemy Select Enemy 11 Pips Roshambo Hit',
	"Scion of Fire": 'Enemy Select Enemy DOT Roshambo Hit',
	"Scion of Death": 'Enemy Select Enemy Weakness Roshambo Hit',
	"Scion of Life": 'Enemy Select Self HOT Roshambo Hit',
	"Scion of Myth": 'Enemy Select Enemy Trap Roshambo Hit',
	"Scion of Ice": 'Enemy Select Self Ward Roshambo Hit',
	"Scion of Storm": 'Enemy Select Self Blade Roshambo Hit'
}

# For spells that cannot be enchanted only in pvp
pvp_no_enchant_logic_list = [
	"Abominable Weaver",
	"Barbarian's Saga",
	"Blast Off!",
	"Call of Khrulhu",
	"Climaclysm",
	"Dark & Stormy",
	"Fire from Above",
	"Freeze Ray",
	"Gaze of Fate",
	"Glowbug Squall",
	"Grim Reader",
	"Grrnadier",
	"Hungry Caterpillar",
	"Iron Sultan",
	"Lamassu",
	"Lord of the Jungle",
	"Mockenspiel",
	"Mystic Colossus",
	"Nested Fury",
	"Old One's Endgame",
	"Qismah's Curse",
	"Raging Bull",
	"Rusalka's Wrath",
	"S'more Machine",
	"Sand Wurm",
	"Scorching Scimitars",
	"Shatterhorn",
	"Snack Attack",
	"Snake Charmer",
	"Snowball Barrage",
	"Sound of Musicology",
	"Tatzlewurm Terror",
	"Winged Sorrow",
	"Wings of Fate",
	"Witch's House Call"
]

# Assigns a casting logic to a spell's origin set
casting_logic_dict = {
	SELECT_RESHUFFLE: 'Ally Select Reshuffle',
	HIT_ENCHANTS: 'Hit Enchant',
	HEAL_ENCHANTS: 'Heal Enchant',
	BLADE_ENCHANTS: 'Blade Enchant',
	TRAP_ENCHANTS: 'Trap Enchant',
	WARD_ENCHANTS: 'Ward Enchant',
	HIT_AURAS: 'AOE Hit Aura',
	DEFENSE_AURAS: 'AOE Defense Aura',
	HEAL_AURAS: 'AOE Heal Aura',
	SELECT_SHIELDS: 'Ally Select Shield',
	AOE_SHIELDS: 'AOE Shield',
	SELECT_BLADES: 'Ally Select Blade',
	AOE_BLADES: 'AOE Blade',
	SELECT_PIERCE: 'Ally Select Pierce',
	SELECT_TRAPS: 'Enemy Select Trap',
	AOE_TRAPS: 'AOE Trap',
	GLOBALS: 'AOE Global',
	SELECT_DOTS: 'Enemy Select DOT',
	SELECT_HITS: 'Enemy Select Hit',
	AOE_DOTS: 'AOE DOT',
	AOE_HITS: 'AOE Hit',
	MINIONS: 'AOE Minion',
	OFFENSE_SHADOW: 'AOE Offensive Shadow Creature',
	DEFENSE_SHADOW: 'AOE Defensive Shadow Creature',
	HEAL_SHADOW: 'AOE Heal Shadow Creature',
	DISPELS: 'Enemy Select Dispel',
	SELECT_HEALS: 'Ally Select Heal',
	AOE_HEALS: 'AOE Heal',
	SELECT_STUNS: 'Enemy Select Stun',
	AOE_STUNS: 'AOE Stun',
	SELECT_DETONATES: 'Enemy Select Detonate',
	SELECT_PRISMS: 'Enemy Select Prism',
	AOE_PRISMS: 'AOE Prism',
	DIVIDE_HITS: 'Enemy Select Hit Divide',
	AOE_DEBUFFS: 'AOE Debuff',
	SELECT_DEBUFFS: 'Enemy Select Debuff',
	AOE_SHADOW_HITS: 'AOE Hit Shadow',
	SELECT_SHADOW_HITS: 'Enemy Select Hit Shadow',
	SELECT_MINION_UTILITIES: 'Ally Select Minion Utility',
	SELECT_PACIFIES: 'Ally Select Pacify',
	AOE_PACIFIES: 'AOE Pacify',
	AOE_TAUNTS: 'AOE Taunt',
	AOE_DETONATES: 'AOE Detonate',
	AOE_POLYMORPHS: 'AOE Polymorphs',
	AOE_HEAL_BLADES: 'AOE Heal Blade',
	SELECT_HEAL_BLADES: 'Ally Select Heal Blade',
	SELF_BLADES: 'AOE Self Blade',
	GOLEM_ENCHANT: 'Golem Enchant',
	AOE_GOLEM_MINION: 'AOE Golem Minion',
	SELECT_WAND_HITS: 'Enemy Select Wand Hit',
	SELECT_SELF_WEAKNESS_UTILITY: 'Ally Select Weakness Counter Utility',
	AOE_SELF_WEAKNESS_UTILITY: 'AOE Weakness Counter Utility',
	SELECT_SELF_TRAP_UTILITY: 'Ally Select Trap Counter Utility',
	SELECT_ENEMY_WARD_UTILITY: 'Enemy Select Ward Counter Utility',
	SELECT_ENEMY_BLADE_UTILITY: 'Enemy Select Blade Counter Utility',
	SELECT_ENEMY_HOT_UTILITY: 'Enemy Select HOT Counter Utility',
	SELECT_SELF_DOT_UTILITY: 'Ally Select DOT Counter Utility',
	AOE_SELF_DOT_UTILITY: 'AOE DOT Counter Utility',
	SELECT_ENEMY_MORE_PIPS_UTILITY: 'Enemy Select More Pips Counter Utilty',
	SELF_WEAKNESS_ROSHAMBO: 'Enemy Select Weakness Roshambo',
	ENEMY_WARD_ROSHAMBO: 'Enemy Select Ward Roshambo',
	ENEMY_BLADE_ROSHAMBO: 'Enemy Select Blade Roshambo',
	SELF_TRAP_ROSHAMBO: 'Enemy Select Trap Roshambo',
	ENEMY_HOT_ROSHAMBO: 'Enemy Select HOT Roshambo',
	SELF_DOT_ROSHAMBO: 'Enemy Select DOT Roshambo',
	SELF_WARD_ROSHAMBO_GAMBIT: 'Enemy Select Self Ward Roshambo Hit',
	SELF_BLADE_ROSHAMBO_GAMBIT: 'Enemy Select Self Blade Roshambo Hit',
	ENEMY_TRAP_ROSHAMBO_GAMBIT: 'Enemy Select Enemy Trap Roshambo Hit',
	ENEMY_WEAKNESS_ROSHAMBO_GAMBIT: 'Enemy Select Enemy Weakness Roshambo Hit',
	ENEMY_DOT_ROSHAMBO_GAMBIT: 'Enemy Select Enemy DOT Roshambo Hit',
	SELF_HOT_ROSHAMBO_GAMBIT: 'Enemy Select Self HOT Roshambo Hit',
	ENEMY_2_SHADS_ROSHAMBO_GAMBIT: 'Enemy Select Enemy 2 Shads Roshambo Hit',
	ENEMY_11_PIPS_ROSHAMBO_GAMBIT: 'Enemy Select Enemy 11 Pips Roshambo Hit',
	ONI_SHADOW_ROSHAMBO: 'Enemy Select Oni Shadow Roshambo',
	STUN_SHIELDS: 'Ally Select Stun Block'
}

# Assigns enchanting logic to enchantable spells based on their origin set
enchant_logic_dict = {
	DIVIDE_HITS: str(casting_logic_dict[HIT_ENCHANTS]),
	SELECT_DOTS: str(casting_logic_dict[HIT_ENCHANTS]),
	SELECT_HITS: str(casting_logic_dict[HIT_ENCHANTS]),
	AOE_DOTS: str(casting_logic_dict[HIT_ENCHANTS]),
	AOE_HITS: str(casting_logic_dict[HIT_ENCHANTS]),
	SELECT_HEALS: str(casting_logic_dict[HEAL_ENCHANTS]),
	AOE_HEALS: str(casting_logic_dict[HEAL_ENCHANTS]),
	SELECT_BLADES: str(casting_logic_dict[BLADE_ENCHANTS]),
	SELF_BLADES: str(casting_logic_dict[BLADE_ENCHANTS]),
	AOE_BLADES: str(casting_logic_dict[BLADE_ENCHANTS]),
	SELECT_TRAPS: str(casting_logic_dict[TRAP_ENCHANTS]),
	AOE_TRAPS: str(casting_logic_dict[TRAP_ENCHANTS]),
	SELF_WARD_ROSHAMBO_GAMBIT: str(casting_logic_dict[HIT_ENCHANTS]),
	SELF_BLADE_ROSHAMBO_GAMBIT: str(casting_logic_dict[HIT_ENCHANTS]),
	ENEMY_TRAP_ROSHAMBO_GAMBIT: str(casting_logic_dict[HIT_ENCHANTS]),
	ENEMY_WEAKNESS_ROSHAMBO_GAMBIT: str(casting_logic_dict[HIT_ENCHANTS]),
	ENEMY_DOT_ROSHAMBO_GAMBIT: str(casting_logic_dict[HIT_ENCHANTS]),
	SELF_HOT_ROSHAMBO_GAMBIT: str(casting_logic_dict[HIT_ENCHANTS]),
	ENEMY_2_SHADS_ROSHAMBO_GAMBIT: str(casting_logic_dict[HIT_ENCHANTS]),
	ENEMY_11_PIPS_ROSHAMBO_GAMBIT: str(casting_logic_dict[HIT_ENCHANTS]),
	AOE_GOLEM_MINION: str(casting_logic_dict[GOLEM_ENCHANT]),
	SELECT_SHIELDS: str(casting_logic_dict[WARD_ENCHANTS]),
	AOE_SHIELDS: str(casting_logic_dict[WARD_ENCHANTS])
}

# List of all valid spell names
master_list = list(casting_logic_dict.keys())

# For converting stat indices to school IDs and vice versa
school_ids = {0: 2343174, 1: 72777, 2: 83375795, 3: 2448141, 4: 2330892, 5: 78318724, 6: 1027491821, 7: 2625203, 8: 78483, 9: 2504141, 10: 663550619, 11: 1429009101, 12: 1488274711, 13: 1760873841, 14: 806477568, 15: 931528087}
school_list_ids = {index: i for i, index in school_ids.items()}
school_id_list = list(school_ids.values())

DAMAGE_TYPE_SCHOOLS = [
	"Fire",
	"Ice",
	"Storm",
	"Myth",
	"Life",
	"Death",
	"Balance",
	"Star",
	"Sun",
	"Moon",
	"Gardening",
	"Shadow"
]

# define the master hitting strategy
master_strategy = ['AOE Golem Minion', 'Ally Select Blade', 'Enemy Select Trap', 'AOE Minion', 'AOE Global', 'AOE Blade', 'AOE Trap', 'AOE Hit Aura','AOE Golem Minion', 'Ally Select Blade', 'Enemy Select Trap', 'AOE Minion', 'AOE Global', 'AOE Blade', 'AOE Trap', 'AOE Hit Aura', 'AOE Offensive Shadow Creature', 'AOE DOT', 'AOE Hit', 'Enemy Select DOT', 'Enemy Select Hit', 'Enemy Select Hit Divide', 'AOE Polymorph']
mob_strategy = ['AOE DOT', 'AOE Hit', 'Enemy Select DOT', 'Enemy Select Hit', 'Enemy Select Hit Divide', 'AOE Hit Aura', 'AOE Trap', 'AOE Global', 'AOE Blade','AOE Golem Minion' ,'AOE Minion', 'AOE Offensive Shadow Creature', 'AOE Polymorph']
pvp_strategy = ['Ally Select Stun Block', 'AOE Global', 'AOE Defense Aura', 'AOE Offensive Shadow Creature', 'AOE DOT', 'AOE Hit', 'Enemy Select DOT', 'Enemy Select Hit', 'Enemy Select Hit Divide']

# Basic types
hit_types = ['AOE DOT', 'AOE Hit', 'Enemy Select DOT', 'Enemy Select Hit', 'Enemy Select Hit Divide']
heal_types = ['AOE Heal Blade', 'Ally Select Heal Blade', 'AOE Heal Shadow Creature', 'AOE Heal', 'Ally Select Heal']
reshuffle_types = ['Ally Select Reshuffle']
defensive_types = ['AOE Defense Aura', 'AOE Defensive Shadow Creature', 'AOE Shield', 'Enemy Select Debuff', 'AOE Debuff', 'AOE Stun', 'Enemy Select Stun', 'Ally Select Shield']
prism_types = ['AOE Prism', 'Enemy Select Prism']
minion_types = ['AOE Minion', 'AOE Golem Minion']
minion_utility_types = ['Ally Select Minion Utility', 'Ally Select Pacify', 'AOE Pacify', 'AOE Taunt']
global_types = ['AOE Global']
buff_types = ['Ally Select Blade', 'Enemy Select Trap', 'AOE Minion', 'AOE Global', 'AOE Blade', 'AOE Trap', 'AOE Hit Aura', 'AOE Offensive Shadow Creature']

# Utilities for negative types
weakness_counter_types = ['Ally Select Weakness Counter Utility', 'AOE Weakness Counter Utility', 'Enemy Select Wand Hit']
weakness_roshambo_types = ['Enemy Select Weakness Roshambo']
weakness_roshambo_gambit_types = ['Enemy Select Enemy Weakness Roshambo Hit']
trap_counter_types = ['Ally Select Trap Counter Utility']
trap_roshambo_types = ['Enemy Select Trap Roshambo']
trap_roshambo_gambit_types = ['Enemy Select Enemy Trap Roshambo Hit']
dot_counter_types = ['Ally Select DOT Counter Utility', 'AOE DOT Counter Utility']
dot_roshambo_types = ['Enemy Select DOT Roshambo']
dot_roshambo_gambit_types = ['Enemy Select Enemy DOT Roshambo Hit']

# Utilities for positive types
blade_counter_types = ['Enemy Select Blade Counter Utility']
blade_roshambo_types = ['Enemy Select Blade Roshambo']
blade_roshambo_gambit_types = ['Enemy Select Self Blade Roshambo Hit']
ward_counter_types = ['Enemy Select Ward Counter Utility']
ward_roshambo_types = ['Enemy Select Ward Roshambo']
ward_roshambo_gambit_types = ['Enemy Select Self Ward Roshambo Hit']
hot_counter_types = ['Enemy Select HOT Counter Utility']
hot_roshambo_types = ['Enemy Select HOT Roshambo']
hot_roshambo_gambit_types = ['Enemy Select Self HOT Roshambo Hit']

# Utilities for pip conditions (most of this will take a while to implement)
more_pips_counter_types = ['Enemy Select More Pips Counter Utilty']
two_shad_roshambo_gambit_types = ['Enemy Select Enemy 2 Shads Roshambo Hit']
eleven_pips_roshambo_gambit_types = ['Enemy Select Enemy 11 Pips Roshambo Hit']
oni_shadow_roshambo_types = ['Enemy Select Oni Shadow Roshambo']


# Spell Types each school has no utility counter for
cannot_counter_school_types = {
	2343174: ['HOT', 'Enemy Select Debuff', 'AOE Debuff', 'Enemy Select DOT', 'AOE DOT'],
	72777: ['Enemy Select DOT', 'AOE DOT', 'Enemy Select Trap', 'AOE Trap'],
	83375795: ['Ally Select Shield', 'AOE Shield', 'Enemy Select Trap', 'AOE Trap'],
	78318724: ['Ally Select Shield', 'AOE Shield', 'Enemy Select Trap', 'AOE Trap', 'Enemy Select DOT', 'AOE DOT'],
	2330892: ['Ally Select Shield', 'AOE Shield', 'Ally Select Blade', 'AOE Blade', 'Enemy Select Debuff', 'AOE Debuff'],
	2448141: ['Ally Select Blade', 'AOE Blade'],
	1027491821: []
}

# Spell Types each school's gambits buff off of, excluding types that are bad to spam in pvp
gambit_school_types = {
	2343174: ['Enemy Select Trap', 'AOE Trap', 'Enemy Select DOT', 'AOE DOT'],
	72777: ['Enemy Select Trap', 'AOE Trap', 'Ally Select Shield', 'AOE Shield', 'Enemy Select Debuff', 'AOE Debuff'],
	83375795: ['Enemy Select Debuff', 'AOE Debuff', 'Ally Select Blade', 'AOE Blade'],
	78318724: ['Enemy Select Debuff', 'AOE Debuff', 'Ally Select Blade', 'AOE Blade', 'Ally Select Shield', 'AOE Shield'],
	2330892: ['Enemy Select DOT', 'AOE DOT', 'Ally Select Blade', 'AOE Blade'],
	2448141: ['Enemy Select Trap', 'AOE Trap', 'Ally Select Shield', 'AOE Shield', 'Enemy Select DOT', 'AOE DOT'],
	1027491821: []
}


# Lists of SpellEffects that align to a specific spell type
# Types that are interpreted as charms
charm_effect_types = [
	SpellEffects.modify_outgoing_damage,
	SpellEffects.modify_outgoing_damage_flat,
	SpellEffects.modify_outgoing_heal,
	SpellEffects.modify_outgoing_heal_flat,
	SpellEffects.modify_outgoing_damage_type,
	SpellEffects.modify_outgoing_armor_piercing
	]

# Types that are interpreted as wards
ward_effect_types = [
	SpellEffects.modify_incoming_damage,
	SpellEffects.modify_incoming_damage_flat,
	SpellEffects.maximum_incoming_damage,
	SpellEffects.modify_incoming_heal,
	SpellEffects.modify_incoming_heal_flat,
	SpellEffects.modify_incoming_damage_type,
	SpellEffects.modify_incoming_armor_piercing
	]

DAMAGE_EFFECTS = [
	SpellEffects.damage,
	SpellEffects.damage_no_crit,
	SpellEffects.damage_over_time,
	SpellEffects.damage_per_total_pip_power,
	SpellEffects.max_health_damage,
	SpellEffects.steal_health,
	SpellEffects.divide_damage,
	SpellEffects.deferred_damage
]

DAMAGE_ENCHANT_EFFECTS = [
	SpellEffects.modify_card_damage,
	SpellEffects.modify_card_accuracy,
	SpellEffects.modify_card_armor_piercing,
	SpellEffects.modify_card_damage_by_rank
]

STRICT_DAMAGE_ENCHANT_EFFECTS = [
	SpellEffects.modify_card_damage,
	SpellEffects.modify_card_damage_by_rank
]

DAMAGE_TARGETS = [
	EffectTarget.enemy_team_all_at_once,
	EffectTarget.enemy_single,
	EffectTarget.enemy_team
]

TEMPLATE_SCHOOLS = [
	"MagicSchools/FireSchool.xml",
	"MagicSchools/IceSchool.xml",
	"MagicSchools/StormSchool.xml",
	"MagicSchools/MythSchool.xml",
	"MagicSchools/LifeSchool.xml",
	"MagicSchools/DeathSchool.xml",
	"MagicSchools/StarSchool.xml",
	"MagicSchools/SunSchool.xml",
	"MagicSchools/MoonSchool.xml",
	"MagicSchools/GardeningSchool.xml",
	"MagicSchools/ShadowSchool.xml"
]

school_name_to_id = {'Ice': 72777, 'Sun': 78483, 'Life': 2330892, 'Fire': 2343174, 'Star': 2625203, 'Myth': 2448141, 'Moon': 2504141, 'Death': 78318724, 'Storm': 83375795, 'Gardening': 663550619, 'CastleMagic': 806477568, 'WhirlyBurly': 931528087, 'Balance': 1027491821, 'Shadow': 1429009101, 'Fishing': 1488274711, 'Cantrips': 1760873841}
school_id_to_name = {v: k for k, v in school_name_to_id.items()}

opposite_school_ids = {72777: 2343174, 2330892: 78318724, 2343174: 72777, 2448141: 83375795, 78318724: 2330892, 83375795: 2448141}



class Fighter(CombatHandler):
	def __init__(self, client: Client, clients: list[Client]):
		self.client = client
		self.clients = clients


	async def get_cards(self) -> List[CombatCard]:  # extended to sort by enchanted # Olaf's fix for coro graphical spell error
			async def _inner() -> List[CombatCard]:
				cards = await super(Fighter, self).get_cards()
				rese, res = [], []
				for card in cards:
					if await card.is_enchanted():
						rese.append(card)
					else:
						res.append(card)
				return rese + res
			try:
				return await wizwalker.utils.maybe_wait_for_any_value_with_timeout(_inner, sleep_time=0.2, timeout=2.0)
			except wizwalker.errors.ExceptionalTimeout:
				return []


	@logger.catch()
	async def new_cast(
			self,
			target: Union["CombatCard", "wizwalker.combat.CombatMember", None],
			*,
			sleep_time: Optional[float] = 1.0,
			debug_paint: bool = True,
		):
			"""
			Cast this Card on another Card; a Member or with no target
			Args:
				target: Card, Member, or None if there is no target
				sleep_time: How long to sleep after enchants and between multicasts or None for no sleep
				debug_paint: If the card should be highlighted before clicking
			"""
			if isinstance(target, CombatCard):
				cards_len_before = len(await self.combat_handler.get_cards())

				await self.combat_handler.client.mouse_handler.click_window(
					self._spell_window
				)

				await asyncio.sleep(sleep_time)

				await self.combat_handler.client.mouse_handler.set_mouse_position_to_window(
					target._spell_window
				)

				await asyncio.sleep(sleep_time)

				if debug_paint:
					await target._spell_window.debug_paint()

				await self.combat_handler.client.mouse_handler.click_window(
					target._spell_window
				)

				# wait until card number goes down
				while len(await self.combat_handler.get_cards()) > cards_len_before:
					await asyncio.sleep(0.1)

				# wiz can't keep up with how fast we can cast
				if sleep_time is not None:
					await asyncio.sleep(sleep_time)

			elif target is None:
				await self.combat_handler.client.mouse_handler.click_window(
					self._spell_window
				)
				# we don't need to sleep because nothing will be casted after

			else:
				await self.combat_handler.client.mouse_handler.click_window(
					self._spell_window
				)

				# see above
				if sleep_time is not None:
					await asyncio.sleep(sleep_time)

				await self.combat_handler.client.mouse_handler.click_window(
					await target.get_name_text_window())

	CombatCard.cast = new_cast


	@logger.catch()
	async def is_fighting(self):
		'''New accurate check for if we're in combat, using spellbook visibility'''
		spellbook_path = ['WorldView', 'windowHUD', 'btnSpellbook']
		check = await is_visible_by_path(self.client, spellbook_path)
		return (not check and await self.client.in_battle())


	@logger.catch()
	async def wait_for_next_round(self, current_round: int, sleep_time: float = 0.5):
		"""
		Wait for the round number to change
		"""
		# can't use wait_for_value bc of the special in_combat condition
		# so we don't get stuck waiting if combat ends
		while await self.is_fighting() and self.client.combat_status:
			new_round_number = await self.round_number()
			if new_round_number > current_round:
				return
			await asyncio.sleep(sleep_time)


	@logger.catch()
	async def wait_for_combat(self, sleep_time: float = 0.5):
		"""
		Wait until in combat
		"""
		await utils.wait_for_value(self.is_fighting, True, sleep_time)
		await self.handle_combat()
		await self.client.send_key(Keycode.D, 0.1)


	async def member_from_id(self, id: int, members: List[CombatMember] = None) -> CombatMember:
		if not members:
			members = await self.get_members()

		for member in members:
			if await member.owner_id() == id:
				return member

		raise ValueError


	@logger.catch()
	async def handle_combat(self):
		"""Handles an entire combat interaction"""
		self.tc = True
		self.cards = []
		self.card_exclusions = []
		self.card_names = {}
		self.spell_logic = {}
		self.enchant_logic = {}
		self._spell_check_boxes = None
		self.prev_hit_types = []
		self.passed = False
		self.fizzled = False
		self.can_kill = False
		self.cur_card_count = 0
		self.prev_card_count = 0
		self.real_round = 0
		self.bypass_strategy_to_kill= []
		self.selected_enemy = None
		self.selected_ally = None
		self.selected_ally_id = None
		while await self.is_fighting() and self.client.combat_status:
			await self.wait_for_planning_phase()
			self.real_round = await self.round_number()
			# TODO: handle this taking longer than planning timer time
			if not self.client.mouseless_status:
				try:
					await self.client.mouse_handler.activate_mouseless()
				except:
					pass
				self.client.mouseless_status = True

			# start = time.perf_counter()
			await self.assign_stats()
			self.card_exclusions = await self.get_valid_cards(None)
			for c in self.cards:
				c: CombatCard
				type = await c.type_name()
				g_spell = await c.get_graphical_spell()
				effects = await g_spell.spell_effects()
				# print(await c.display_name())
				# print(await c.spell_id())
				# for e in effects:
				# 	name = await e.effect_type()
				# 	print(name)
				# print(type)
				# print('-------------------------------------')
			self.fizzled = await self.fizzle_detection()
			if self.cards:
				await self.assign_card_names()
				await self.assign_pip_values()
				await self.discard_unsupported()
				await self.assign_spell_logic()
				await self.effect_enchant_ID(self.client_member)
				await self.enchant_all()
				await self.discard_useless()
				await self.get_tc()
				await self.handle_round()
			else: 
				logger.debug(f"Client {self.client.title} - Passing")
				await self.pass_button()
				self.passed = True
			# end = time.perf_counter()
			# logger.debug(f'Turn logic took {end - start} seconds')
			if self.client.mouseless_status:
				try:
					await self.client.mouse_handler.deactivate_mouseless()
				except:
					pass
				self.client.mouseless_status = False
			await self.wait_for_next_round(self.real_round)


	@logger.catch()
	async def get_valid_cards(self, exclusions):
		await asyncio.sleep(0.45)
		self.cards = await self.get_cards()
		await asyncio.sleep(0)
		# await asyncio.sleep(0.2)
		# if len(self.cards) > 7:
		# 	self.cards = self.cards.copy()[1:]
		if exclusions:
			self.cards = [c for c in self.cards.copy() if c not in exclusions]
		else:
			exclusions = []
			for c in self.cards.copy():
				c_graphical_spell = await c.wait_for_graphical_spell()
				c_spell_template = await c_graphical_spell.spell_template()
				if await c_spell_template.no_discard():
					self.cards.remove(c)
					exclusions.append(c)
		return exclusions


	@logger.catch()
	async def enchant_logic_stacking(self, spell, enchant, selected) -> bool:
		"""Checks if enchanted version of the card is already in play"""
		graphical_spell = await spell.wait_for_graphical_spell()
		graphical_enchant = await enchant.wait_for_graphical_spell()
		card_enchant_ID = (await graphical_enchant.template_id(), await graphical_spell.template_id()) # combines spell ID & enchant ID in a list to make a hypothetical enchanted version of the card
		await self.effect_enchant_ID(selected)
		if card_enchant_ID in self.current_hand_IDs: # checks if already enchanted version of the card in hand
			return False
		for effects in self.hanging_effect_IDs: 
			if card_enchant_ID[0] == effects[0] and card_enchant_ID[1] == effects[1]: # checks if already enchanted version of the card in hanging effects
				return False
		return True # will return true if hypothetical enchanted version hasn't been casted


	@logger.catch()
	async def is_spell_in_hanging_effect(self, spell):
		graphical_spell = await spell.wait_for_graphical_spell()
		card_atr = (await graphical_spell.template_id(), await graphical_spell.enchantment())
		for i in self.hanging_effect_IDs:
			if i[0] == card_atr[0] and i[1] == card_atr[1]:
				return True
		return False


	@logger.catch()
	async def discard_spell_in_hanging_effect(self, spell):
		graphical_spell = await spell.wait_for_graphical_spell()
		card_atr = (await graphical_spell.template_id(), await graphical_spell.enchantment())
		await self.effect_enchant_ID(self.client_member)
		for i in self.hanging_effect_IDs:
			if i[0] == card_atr[0] and i[1] == card_atr[1]:
				logger.debug(f"Client {self.client.title} - Discarding {self.card_names[spell]}")
				await spell.discard(sleep_time = 0.25)
				break


	@logger.catch()
	async def effect_enchant_ID(self, selected):
		"""Reads casted & in hand enchanted cards for enchanting logic"""
		#TODO selected ally/enemy for enchanting stacking logic
		#player_members = [a for a in self.allies if await a.is_player() == True] #hardcoded ally
		self.current_hand_IDs = []
		self.hanging_effect_IDs = []
		self.mob_hanging_effect_IDs = []
		if not selected:
			selected = self.client_member
		# print(f'hanging effects dict{self.member_hanging_effects}')
		# print(f'selected ally {selected}')
		# print(f'client member ID {self.client_member}')
		#makes lists of card ID's with enchant ID to compare with later on 
		if selected in self.member_hanging_effects:
			for effect in self.member_hanging_effects[selected]: 
				hanging_atr = (await effect.spell_template_id(), await effect.enchantment_spell_template_id(), await effect.effect_param(), await effect.string_damage_type(), await effect.effect_type())
				self.hanging_effect_IDs.append(hanging_atr)
		for card in self.cards:
			graphical_spell = await card.wait_for_graphical_spell()
			card_atr = (await graphical_spell.template_id(), await graphical_spell.enchantment())
			self.current_hand_IDs.append(card_atr)


	@logger.catch()
	async def get_card_counts(self) -> Tuple[int, int]: #Olaf's reads UI of card counts
		"""Reads UI for card count and returns values"""
		window = None
		while window is None:
			window, *_ = await self.client.root_window.get_windows_with_name("CountText")
		text: str = await window.maybe_text()
		_, count_text = text.splitlines()
		count_text = count_text[8:-9]
		count_text = count_text.replace("of", "").strip()  # I know this sucks
		res1, res2 = count_text.split()
		return int(res1), int(res2)


	@logger.catch()
	async def fizzle_detection(self) -> bool:
		"""Compares prev card count to current card count to detect fizzling"""
		self.cur_card_count = len(await self.get_cards()) + (await self.get_card_counts())[0] # checks the current amount of cards in hand at start of round 
		if self.real_round > 1 : #checks if round is greater than 1 because you can't fizzle on round 1
			if self.cur_card_count >= self.prev_card_count and not self.passed: # checks if the current card count equals previous card count without passing, if it's true it means you fizzled.
				logger.debug(f"Client {self.client.title} - Fizzled")
				return True
		return False


	@logger.catch()
	async def assign_card_names(self):
		"""Assigns the name for each card in a dict to avoid over reading"""
		self.card_names = {}
		for c in self.cards:
			if c not in self.card_names:
				# try:
				self.card_names[c] = await c.display_name()
				# except wizwalker.errors.ExceptionalTimeout:
				# 	await self.assign_card_names()


	@logger.catch()
	async def discard_unsupported(self):
		"""Discards all spells not in the master spell list"""
		discarded = True
		while discarded:
			discarded = False
			for c in self.cards.copy():
				if all([self.card_names[c] not in s for s in master_list]):
					logger.debug(f"Client {self.client.title} - Discarding {self.card_names[c]}")
					await c.discard(sleep_time=0.25)
					_ = await self.get_valid_cards(self.card_exclusions)
					await self.assign_card_names()
					await self.assign_pip_values()
					discarded = True
					break


	@logger.catch()
	async def assign_spell_logic(self):
		"""Assigns spell logic string and enchanting logic strings to all spells """
		self.spell_logic = {}
		self.enchant_logic = {}
		for c in self.cards:
			for s in master_list:
				if self.card_names[c] in s:
					self.spell_logic[c] = casting_logic_dict[s]
					if s in enchant_logic_dict:
						self.enchant_logic[c] = enchant_logic_dict[s]


	@logger.catch()
	async def assign_pip_values(self):
		'''Assigns a calculated pip value to every spell in the hand. Shadow pips are worth 4 regular pips.'''
		self.pip_values = {}
		for s in self.cards:
			await s.wait_for_graphical_spell()
			g_spell = await s.get_graphical_spell()
			regular_rank = await g_spell.read_value_from_offset(176 + 72, "unsigned char")
			shadow_rank = await g_spell.read_value_from_offset(176 + 73, "unsigned char")
			card_rank = regular_rank + (4 * shadow_rank)
			self.pip_values[s] = card_rank


	@logger.catch()
	async def enchant_all(self):
		"""Enchants all compatible cards with any compatible enchants"""
		enchanted = True
		while enchanted:
			enchanted = False
			enchants = []
			enchantable_cards = []
			selected = None
			for c in self.cards:
				if c in self.spell_logic:
					if 'Enchant' in self.spell_logic[c]:
						enchants.append(c)
					else:
						if c not in self.enchant_logic or await c.is_enchanted() or await c.is_item_card() or await c.is_treasure_card():
							pass
						else:
							enchantable_cards.append(c)

			for e in enchants.copy():
				sorted_enchantable_cards = []
				enchantable_cards_pip_values = {e: p for e, p in self.pip_values.items() if e in enchantable_cards.copy()}
				for i in range(len(enchantable_cards_pip_values)):
					max_enchantable_card = max(enchantable_cards_pip_values, key= lambda s: enchantable_cards_pip_values[s])
					sorted_enchantable_cards.append(max_enchantable_card)
					del enchantable_cards_pip_values[max_enchantable_card]
				for c in sorted_enchantable_cards:
					if e in self.spell_logic and c in self.enchant_logic:
						if self.spell_logic[e] == self.enchant_logic[c]:
							if 'Enemy' in self.spell_logic[e]:
								selected = self.selected_enemy
							else:
								selected = self.client_member
							if await self.enchant_logic_stacking(e, c, selected):
								logger.debug(f"Client {self.client.title} - Enchanting {self.card_names[c]} with {self.card_names[e]}")
								await e.cast(c, sleep_time=0)
								# await self.checked_cast(card=c, enchant=e)
								_ = await self.get_valid_cards(self.card_exclusions)
								await self.assign_card_names()
								await self.assign_spell_logic()
								await self.assign_pip_values()
								await self.effect_enchant_ID(self.client_member)
								enchanted = True
								break
				if enchanted:
					break


	@logger.catch()
	async def discard_duplicate_types(self, iterations: int = 1):
		"""Discards duplicate spell types in hand"""
		#TODO make a version that discards based on spell name
		for i in range(iterations):
			discarded = True
			prev_checked_logics = []
			while discarded:
				discarded = False
				card_list = self.cards.copy()
				card_list_pip_values = self.pip_values.copy()
				sorted_card_list = []
				for i in range(len(card_list)):
					max_card = min(card_list_pip_values, key= lambda s: card_list_pip_values[s])
					sorted_card_list.append(max_card)
					del card_list_pip_values[max_card]
				for c in sorted_card_list:
					if self.spell_logic[c] not in prev_checked_logics:
						prev_checked_logics.append(self.spell_logic[c])
						if len([s for s in list(self.spell_logic.values()) if s == self.spell_logic[c]]) > 1 and (('Hit' not in self.spell_logic[c] and 'DOT' not in self.spell_logic[c]) or 'Wand' in self.spell_logic[c]):
							logger.debug(f"Client {self.client.title} - Discarding {self.card_names[c]}")
							await c.discard(sleep_time=0.25)
							_ = await self.get_valid_cards(self.card_exclusions)
							await self.assign_card_names()
							await self.assign_spell_logic()
							await self.assign_pip_values()
							await self.enchant_all()
							discarded = True
							break


	async def is_control_grayed(self, win: Window): # if button is not gray it will return false
		return await win.read_value_from_offset(688, "bool")

	@logger.catch()
	async def get_tc(self):
		if self.tc:
			'''Draws TC equivalent to half the available free spaces in the hand. Example: 3/7 cards in hand = drawing twice'''
			draw_path = ["WorldView", "PlanningPhase", "Alignment", "PlanningPhaseSubWindow", "SpellSelection", "ActionButtons", "Draw"]
			num_cards = int((7 - len(self.cards)) / 2)
			if num_cards >= 0:
				draw_button = await get_window_from_path(self.client.root_window,draw_path)
				if await self.is_control_grayed(draw_button) == False: 
					for i in range(num_cards):
						await self.client.mouse_handler.click_window(draw_button)
					await asyncio.sleep(0.3)
					_ = await self.get_valid_cards(self.card_exclusions)
					await self.assign_card_names()
					await self.assign_spell_logic()
					self.cards = [c for c in self.cards.copy() if c in self.spell_logic]
					await self.assign_pip_values()
					await self.enchant_all()
				else:
					self.tc = False


	async def get_index_from_list(self, name, list):
			for i, x in enumerate(list):
				if name == x:
					return i

	@logger.catch()
	async def discard_useless(self, strategy: list[str] = None):
		'''Discards spells that would be detrimental to cast. Example: Will discard minions in hand if a minion is already up'''
		discarded = True
		minions = [a for a in self.allies if await a.is_minion()]
		self.combat_resolver = await self.client.duel.combat_resolver()
		while discarded:
			discarded = False
			to_discard = []

			# Add discarding conditionals here
			if minions:
				to_discard += [c for c in self.cards if self.spell_logic[c] in minion_types]

			if self.combat_resolver is not None:
				global_effect = await self.combat_resolver.global_effect() #reads the global effects on the field
				if global_effect:
					global_effect_type = await global_effect.effect_type() #reads just like hanging effects
					global_damage_type = await global_effect.string_damage_type()
					# print(F"Effect Type: {global_effect_type.name} [{global_damage_type}]")
					global_effect_school_num = await self.get_index_from_list(global_damage_type, DAMAGE_TYPE_SCHOOLS) #gets globals school
					if global_effect_school_num:
						global_effect_school = school_ids[global_effect_school_num]
						if (SpellEffects.modify_outgoing_damage == global_effect_type) and ((self.client_school_id == global_effect_school) or (global_damage_type == "All")): #checks if global school matches our school
							to_discard += [c for c in self.cards if self.spell_logic[c] in global_types] # finds spells in out hand that are global and discards them

			if strategy:
				if any([await m.is_player() for m in self.mobs]):
					not_in_strategy = [c for c in self.cards if self.spell_logic[c] not in strategy]
					not_in_strategy.reverse()
					# TODO: make this logic somehow not shit
					to_discard += [c for c in self.cards if self.spell_logic[c] not in strategy][int(len(not_in_strategy) / 2):]

			if to_discard:
				for i in to_discard:
					logger.debug(f"Client {self.client.title} - Discarding {self.card_names[i]}")
					await i.discard(sleep_time=0.25)
				_ = await self.get_valid_cards(self.card_exclusions)
				await self.assign_card_names()
				await self.assign_spell_logic()
				await self.assign_pip_values()
				await self.enchant_all()
				discarded = True




	@logger.catch()
	async def assign_stats(self):
		'''Assign client-specific stats and member/participant objects and stats'''
		self.members = await self.get_members()
		self.client_member = None
		self.member_participants = {}
		for m in self.members:
			if await m.is_client():
				self.client_member = m
			self.member_participants[m] = await m.get_participant()
		self.client_participant = await self.client_member.get_participant()
		self.client_school_id = await self.client_participant.primary_magic_school_id()
		self.client_team_id = await self.client_participant.team_id()

		# Assign lists of ally members and enemy members
		self.allies = []
		self.mobs = []
		for member in self.members:
			member_id = await self.member_participants[member].team_id()
			if member_id == self.client_team_id:
				self.allies.append(member)
			else:
				self.mobs.append(member)

		# assign combat member stat dictionaries and such
		self.member_stats = {}
		self.member_resistances = {}
		self.member_flat_resistances = {}
		self.member_damages = {}
		self.member_flat_damages = {}
		self.member_hanging_effects = {}
		self.member_school_ids = {}
		self.member_pierce = {}
		self.member_aura_effects = {}
		self.member_shadow_effects = {}
		self.member_pips = {}
		self.member_power_pips = {}
		self.member_shadow_pips = {}
		self.member_critical_ratings = {}
		self.member_block_ratings = {}
		for m in self.members:
			self.member_school_ids[m] = await self.member_participants[m].primary_magic_school_id()
			self.member_stats[m] = await m.get_stats()
			# calculate actual resistances/damages/pierces/criticals/blocks for this combat member
			m_pierce = await self.member_stats[m].ap_bonus_percent()
			m_damages = await self.member_stats[m].dmg_bonus_percent()
			m_flat_damages = await self.member_stats[m].dmg_bonus_flat()
			m_universal_pierce = float(await self.member_stats[m].ap_bonus_percent_all())
			m_universal_damage = float(await self.member_stats[m].dmg_bonus_percent_all())
			m_universal_flat_damage = float(await self.member_stats[m].dmg_bonus_flat_all())
			self.member_pierce[m] = [r + m_universal_pierce for r in m_pierce]
			self.member_damages[m] = [r + m_universal_damage for r in m_damages]
			self.member_flat_damages[m] = [r + m_universal_flat_damage for r in m_flat_damages]
			m_resistances = await self.member_stats[m].dmg_reduce_percent()
			m_universal_resistance = float(await self.member_stats[m].dmg_reduce_percent_all())
			self.member_resistances[m] = [r + m_universal_resistance for r in m_resistances]
			m_flat_resistances = await self.member_stats[m].dmg_reduce_flat()
			m_universal_flat_resistance = float(await self.member_stats[m].dmg_reduce_flat_all())
			self.member_flat_resistances[m] = [r + m_universal_flat_resistance for r in m_flat_resistances]
			m_critical_ratings = await self.member_stats[m].critical_hit_rating_by_school()
			m_universal_critical = await self.member_stats[m].critical_hit_rating_all()
			self.member_critical_ratings[m] = [r + m_universal_critical for r in m_critical_ratings]
			m_block_ratings = await self.member_stats[m].block_rating_by_school()
			m_universal_block = await self.member_stats[m].block_rating_all()
			self.member_block_ratings[m] = [r + m_universal_block for r in m_block_ratings]
			# get hanging effects for this combat member
			self.member_hanging_effects[m] = await self.member_participants[m].hanging_effects()
			self.member_aura_effects[m] = await self.member_participants[m].aura_effects()
			self.member_shadow_effects[m] = await self.member_participants[m].shadow_spell_effects()
			self.member_pips[m] = await m.normal_pips()
			self.member_power_pips[m] = await m.power_pips()
			self.member_shadow_pips[m] = await m.shadow_pips()


		# assigns mobs health values in a dictionary & selects highest health mob as target. 
		self.mob_healths = {}
		self.damage_potential_to_self = {}
		self.selected_enemy = None
		for m in self.mobs:
			self.mob_healths[m] = await m.health()
		self.selected_enemy = max(self.mob_healths, key = lambda h: self.mob_healths[h])


	@logger.catch()
	async def handle_round(self):
		"""Uses strategy lists and conditional strategies to decide on the best spell to cast, then casts it."""

		# get a list of bosses, and assigns a strategy
		# TODO: PVP detection, possibly beastmoon detection. Right now this only does boss and mob only fights.
		self.selected_ally = None
		in_pvp = False
		try:
			bosses = [m for m in self.mobs if await m.is_boss()]
		except:
			bosses = []
		strategy = None
		if bosses:
			strategy = master_strategy.copy()
		elif all([await m.is_monster() for m in self.mobs]):
			strategy = mob_strategy.copy()
		else:
			in_pvp = True
			strategy = pvp_strategy.copy()
		clean_strategy = strategy.copy()

		# If you fizzled remove the last value in previous hit types
		if self.fizzled:
			if self.prev_hit_types:
				self.prev_hit_types.pop()
		# de-prioritize any spell types that were previously casted, avoids spamming the same spell type. Playstyle modifications bypass this.
		for p in self.prev_hit_types:
			if p in strategy:
				strategy.remove(p)
			strategy.append(p)


		# assign pvp-only spell logic modifications, and delete enchant logic from spells that cannot be enchanted in only pvp
		if in_pvp:
			for c in self.cards:
				if self.card_names[c] in pvp_casting_logic_dict:
					self.spell_logic[c] = pvp_casting_logic_dict[self.card_names[c]]
				if self.card_names[c] in pvp_no_enchant_logic_list:
					if c in self.enchant_logic:
						del self.enchant_logic[c]


		# Conditional playstyle modifications. Allows for changing playstyle based on conditions like healing, enemy schools, and hanging effects (not implemented)
		# Priority types is the list of spell types it inserts at the front of the list, the selected ally is the ally that these spells will be used on.
		priority_types = []
		selected_ally = None


		# Healing logic
		player_members = [a for a in self.allies if await a.is_player() == True]
		health_percentages = {}
		for a in player_members:
			health_percentages[a] = float(await a.health()) / float(await a.max_health())
		# chooses ally with lowest health percent
		highest_priority_ally = min(health_percentages, key= lambda a: health_percentages[a])
		# only prioritizes healing if below the threshold float (0.51 by default)
		if health_percentages[highest_priority_ally] < 0.51:
			selected_ally = highest_priority_ally
			priority_types += heal_types
		if len([c for c in self.cards if self.card_names[c] == "Reshuffle"]) > len([c for c in self.cards if not self.card_names[c] == "Reshuffle" and not await c.is_treasure_card()]) and len([self.cards]) < 6 :
			selected_ally = self.client_member
			priority_types += reshuffle_types


		# Preemptive Defensive Spells Logic
		# assigns the damage potentials for each mob, against the player.
		for m in self.mobs:
			self.damage_potential_to_self[m] = await self.member_damage_potential(m, self.client_member)
		most_powerful_mob = max(self.damage_potential_to_self, key= lambda m: self.damage_potential_to_self[m])
		if (await self.client_member.health() - self.damage_potential_to_self[most_powerful_mob]) / await self.client_member.max_health() < 0.35:
			priority_types += defensive_types

		# Self - Charm (Positive/Negative) counter/roshambo logic
		self_charms = [e for e in self.member_hanging_effects[self.client_member] if await e.effect_type() in charm_effect_types]
		if self_charms and (selected_ally == self.client_member or not selected_ally):
			self_weaknesses = [c for c in self_charms if await c.effect_param() <= 0]
			self_blades = [c for c in self_charms if c not in self_weaknesses]
			if self_weaknesses:
				priority_types += weakness_counter_types
				if len(self_weaknesses) >= 2:
					priority_types += weakness_roshambo_types
			if len(self_blades) >= 4:
				priority_types += blade_roshambo_gambit_types


		# Self - Ward (Positive/Negative) counter/roshambo logic
		self_wards = [e for e in self.member_hanging_effects[self.client_member] if await e.effect_type() in ward_effect_types]
		if self_wards and (selected_ally == self.client_member or not selected_ally):
			self_traps = [c for c in self_wards if await c.effect_param() > 0]
			self_shields = [c for c in self_wards if c not in self_traps]
			if self_traps:
				priority_types += trap_counter_types
				if len(self_traps) >= 2:
					priority_types += trap_roshambo_types
			if len(self_shields) >= 4:
				priority_types += ward_roshambo_gambit_types


		# Self - DOT counter/roshambo logic
		self_dots = [e for e in self.member_hanging_effects[self.client_member] if await e.effect_type() == SpellEffects.damage_over_time]
		if self_dots:
			priority_types += dot_roshambo_types
			priority_types += dot_counter_types


		# Self - HOT roshambo gambit logic
		self_hots = [e for e in self.member_hanging_effects[self.client_member] if await e.effect_type() == SpellEffects.heal_over_time]
		if len(self_hots) >= 2:
			priority_types += hot_roshambo_gambit_types


		# # Defensive logic, works same as healing but with diff spells and diff threshold (DEPRECATED)
		# if health_percentages[highest_priority_ally] < 0.61 and not in_pvp:
		# 	selected_ally = highest_priority_ally
		# 	priority_types += defensive_types


		# # Enemy Selection, if not done via playstyle mods already (DEPRECATED, I THINK)
		# if not selected_enemy:
		# 	selected_enemy = self.selected_enemy


		# Get selected enemy's masteries
		selected_enemy_masteries = []
		selected_enemy_school_id = await self.member_participants[self.selected_enemy].primary_magic_school_id()
		selected_enemy_masteries.append(selected_enemy_school_id)
		if await self.member_stats[self.selected_enemy].fire_mastery():
			selected_enemy_masteries.append(2343174)
		elif await self.member_stats[self.selected_enemy].ice_mastery():
			selected_enemy_masteries.append(72777)
		elif await self.member_stats[self.selected_enemy].storm_mastery():
			selected_enemy_masteries.append(83375795)
		elif await self.member_stats[self.selected_enemy].death_mastery():
			selected_enemy_masteries.append(78318724)
		elif await self.member_stats[self.selected_enemy].life_mastery():
			selected_enemy_masteries.append(2330892)
		elif await self.member_stats[self.selected_enemy].myth_mastery():
			selected_enemy_masteries.append(2448141)
		elif await self.member_stats[self.selected_enemy].balance_mastery():
			selected_enemy_masteries.append(1027491821)


		# PVP Spelltype spam logic
		if in_pvp:
			self_gambit_types = gambit_school_types[self.client_school_id]
			school_non_counter_types = cannot_counter_school_types[selected_enemy_school_id]
			mastery_non_counter_types = cannot_counter_school_types[selected_enemy_masteries[0]]
			enemy_non_counter_types = [s for s in school_non_counter_types if s in mastery_non_counter_types]
			spammable_types = [s for s in self_gambit_types if s in enemy_non_counter_types]


		# Prism logic
		if not [e for e in self.member_hanging_effects[self.selected_enemy] if await e.effect_type() == SpellEffects.modify_incoming_damage_type]:
			if [e for e in self.member_hanging_effects[self.selected_enemy] if await e.damage_type() == self.client_school_id and await e.effect_type() == SpellEffects.modify_incoming_damage]:
				priority_types += prism_types
			else:
				selected_enemy_resistances = self.member_resistances[self.selected_enemy]
				max_enemy_resistance = max(selected_enemy_resistances)
				selected_enemy_resistances_ids = {i: r for i, r in zip(school_id_list, selected_enemy_resistances)}
				if max_enemy_resistance > 0.35:
					if max_enemy_resistance - selected_enemy_resistances_ids[self.client_school_id] < 0.1:
						priority_types += prism_types


		# Enemy - Charm (Positive/Negative) counter/roshambo logic
		enemy_charms = [e for e in self.member_hanging_effects[self.selected_enemy] if await e.effect_type() in charm_effect_types]
		if enemy_charms:
			enemy_weaknesses = [c for c in enemy_charms if await c.effect_param() <= 0]
			enemy_blades = [c for c in enemy_charms if c not in enemy_weaknesses]
			if enemy_blades:
				priority_types += blade_counter_types
				if len(enemy_blades) >= 2:
					priority_types += blade_roshambo_types
			if len(enemy_weaknesses) >= 4:
				priority_types += weakness_roshambo_gambit_types


		# Enemy - Ward (Positive/Negative) counter/roshambo logic
		enemy_wards = [e for e in self.member_hanging_effects[self.selected_enemy] if await e.effect_type() in ward_effect_types]
		if enemy_wards:
			enemy_traps = [c for c in enemy_wards if await c.effect_param() >= 0]
			enemy_shields = [c for c in enemy_wards if c not in enemy_traps]
			if enemy_shields:
				priority_types += ward_counter_types
				if len(enemy_shields) >= 2:
					priority_types += ward_roshambo_types
			if len(enemy_traps) >= 4:
				priority_types += trap_roshambo_gambit_types


		# Enemy - DOT roshambo gambit logic
		self_dots = [e for e in self.member_hanging_effects[self.selected_enemy] if await e.effect_type() == SpellEffects.damage_over_time]
		if len(self_dots) >= 2:
			priority_types += dot_roshambo_gambit_types


		# Enemy - Hot counter/roshambo logic
		self_hots = [e for e in self.member_hanging_effects[self.selected_enemy] if await e.effect_type() == SpellEffects.heal_over_time]
		if self_hots:
			priority_types += hot_roshambo_types
			priority_types += hot_counter_types


		# Assign pips/shadow pips for self and selected enemy
		self_pips = (self.member_power_pips[self.client_member] * 2) + self.member_pips[self.client_member]
		self_shadow_pips = self.member_shadow_pips[self.client_member]
		enemy_pips = (self.member_power_pips[self.selected_enemy] * 2) + self.member_pips[self.selected_enemy]
		enemy_shadow_pips = self.member_shadow_pips[self.selected_enemy]


		# Enemy - More pips counter/roshambo logic
		if enemy_pips >= self_pips:
			priority_types += more_pips_counter_types


		# Enemy - 11 pips roshambo gambit logic
		if enemy_pips >= 11:
			priority_types += eleven_pips_roshambo_gambit_types


		# Enemy - 2 shadow pips roshambo gambit logic
		if enemy_shadow_pips >= 2:
			priority_types += two_shad_roshambo_gambit_types


		# Enemy - Oni's shadow roshambo logic
		if enemy_shadow_pips >= 2 or (enemy_shadow_pips == 1 and enemy_pips < self_pips):
			priority_types += oni_shadow_roshambo_types

		# Minion Utility logic
		minion = [a for a in self.allies if await a.is_minion()]
		if minion and not selected_ally:
			selected_ally = minion[0]
			priority_types += minion_utility_types
		
		# Preemptive Buffing logic, only buffs if we cannot kill the selected enemy
		final_card_damages = {}
		hits = [c for c in self.cards if self.spell_logic[c] in hit_types and await c.is_castable()]
		for card in hits:
			card_damage =  await self.calculate_damage(self.selected_enemy, card)
			if card_damage >= self.mob_healths[self.selected_enemy]:
				break
			else:
				final_card_damages[card] = card_damage
		else:
			if not in_pvp:
				priority_types += buff_types
			else:
				priority_types += spammable_types


		# Prioritize priority spells by placing them front of the priority list
		# print(priority_types)
		priority_types.reverse()
		for t in priority_types:
			strategy.insert(0, t)

		if in_pvp:
			await self.discard_useless(strategy)

		await self.effect_enchant_ID(self.selected_enemy)
		for card in self.cards:
			await self.discard_spell_in_hanging_effect(card)
		_ = await self.get_valid_cards(self.card_exclusions)
		await self.assign_card_names()
		await self.assign_spell_logic()
		await self.assign_pip_values()

	
		if self.selected_ally_id:
			for i in self.members:
				if await i.owner_id() == self.selected_ally_id:
					self.selected_ally = i 

		if not self.selected_ally:
			self.selected_ally = self.client_member

		# print(f"no selected_ally {self.selected_ally}")

		# print(f"current ally : {self.selected_ally}")
		await self.effect_enchant_ID(self.selected_ally)
		for card in self.cards:
			await self.discard_spell_in_hanging_effect(card)

		_ = await self.get_valid_cards(self.card_exclusions)
		await self.assign_card_names()
		await self.assign_spell_logic()
		await self.assign_pip_values()


		# Spell Selection Logic
		self.selected_spell = None
		spell_matches = []
		castable_cards = [c for c in self.cards if await c.is_castable()]
		#selected_ally = None
		# search cards for matching spell type, finds all matches and then breaks.
		#print(f"strategy : {strategy}")
		if castable_cards:
			for t in strategy:
				for c in castable_cards:
					if c in self.spell_logic:
						c_spell_logic = self.spell_logic[c]
						if c_spell_logic == t:
							spell_matches.append(c)
							#print(self.card_names[c])
				if spell_matches:
					# print(spell_matches)
					spell_matches_ranks = {}
					spell_pip_value_in_order = []
					spell_pip_value = []
					if "HIT" in strategy:
						for s in spell_matches:
							pip_value = self.pip_values[s]
							spell_pip_value.append((pip_value, s))
						spell_pip_value.sort(reverse=True, key=lambda pip: pip[0]) # Selects the highest pip value among the matched cards, prevents smaller hits being preferred. Shads are counted as 4 regular pips, as they are less pip heavy overall and should be preferred.
					else:
						for s in spell_matches:
							pip_value = self.pip_values[s]
							spell_pip_value.append((pip_value, s))
						spell_pip_value.sort(key=lambda pip: pip[0])

					for i in spell_pip_value:
						spell_pip_value_in_order.append(i[1])
					for selected_spell in spell_pip_value_in_order: 
						selected_spell_logic = self.spell_logic[selected_spell]
						# Ally Selection, if not done via playstyle mods already
						if not selected_ally :
							spiritblade = [2330892, 78318724, 2448141, 1027491821]#list of schools [life, death, myth, balance]
							elementalblade = [83375795, 2343174, 72777, 102749182]#list of schools [storm, fire, ice, balance]
							non_balance_uni_blade_names = ['Dark Pact']
							selected_graphical_spell =  await selected_spell.get_graphical_spell()
							selected_spell_school = await selected_graphical_spell.magic_school_id()
							allies_to_compare = [a for a in self.allies if await a.is_player() == True if await self.member_participants[a].primary_magic_school_id() == selected_spell_school or self.card_names[selected_spell] == "Spirit Blade" and await self.member_participants[a].primary_magic_school_id() in spiritblade or self.card_names[selected_spell] == "Elemental Blade" and await self.member_participants[a].primary_magic_school_id() in elementalblade or selected_spell_school == 1027491821 or self.card_names[selected_spell] in non_balance_uni_blade_names]
							if allies_to_compare:
								max_ally_damages = {}
								for a in allies_to_compare:
									max_ally_damages[a] = max(self.member_damages[a])
								# return the ally with the max damage, school matched
								selected_ally = max(max_ally_damages, key = lambda a: max_ally_damages[a])
								await self.effect_enchant_ID(selected_ally)
								if await self.is_spell_in_hanging_effect(selected_spell) == False:
									self.selected_spell = selected_spell
									self.selected_ally_id = await selected_ally.owner_id()
									self.selected_ally = selected_ally
									break
									
					if self.selected_spell:
						break
					else:
						for spell in spell_pip_value_in_order:
							if not await self.is_spell_in_hanging_effect(spell):
								self.selected_spell = spell
								break
						break
				
		# print("icecream")
		# print(self.removed_spells)
		#cards = []
		#cards = [ele for ele in self.cards if ele not in self.removed_spells]

		self.bypass_strategy_to_kill, self.can_kill = await self.damage_calc_handle_round(self.cards)
		# print(self.can_kill)
		self.prev_card_count = len(await self.get_cards()) + (await self.get_card_counts())[0] # gets card amount after enchants and discards
		# update previously used spell types, and those that aren't purely done by conditionals
		if self.selected_spell:
			if self.spell_logic[self.selected_spell] in clean_strategy:
				self.prev_hit_types.append(self.spell_logic[self.selected_spell])
		
		#overiding logic
		if self.can_kill:
			if self.selected_spell:
				if not self.selected_spell == self.bypass_strategy_to_kill:
					logger.debug(f"Client {self.client.title} - Overriding {self.card_names[self.selected_spell]} to {self.card_names[self.bypass_strategy_to_kill]}")
					self.selected_spell = self.bypass_strategy_to_kill
			else:
				logger.debug(f"Client {self.client.title} - Overriding {self.card_names[self.bypass_strategy_to_kill]}")
				self.selected_spell = self.bypass_strategy_to_kill

		if not self.selected_spell:
			for card in self.cards:
				if card in self.spell_logic:
					if self.spell_logic[card] in defensive_types:
						self.selected_spell = card
						break

		if not self.selected_ally:
			self.selected_ally = self.client_member

		# Casting logic
		while True:
			if self.selected_spell:
				selected_spell_logic = self.spell_logic[self.selected_spell]
				if 'AOE' in selected_spell_logic:
					logger.debug(f"Client {self.client.title} - Casting {self.card_names[self.selected_spell]}")
					await self.selected_spell.cast(None, sleep_time=0)
					# await self.checked_cast(selected_spell)
				elif 'Enemy Select' in selected_spell_logic:
					logger.debug(f"Client {self.client.title} - Casting {self.card_names[self.selected_spell]} on {await self.selected_enemy.name()}")
					await self.selected_spell.cast(self.selected_enemy, sleep_time=0)
					# await self.checked_cast(selected_spell, target=self.selected_enemy)
				elif 'Ally Select' in selected_spell_logic:
					logger.debug(f"Client {self.client.title} - Casting {self.card_names[self.selected_spell]} on {await self.selected_ally.name()}")
					await self.selected_spell.cast(self.selected_ally, sleep_time=0)
					# await self.checked_cast(selected_spell, target=self.selected_ally)
				if 'Divide' in selected_spell_logic:
					await asyncio.sleep(0.2)
					try:
						await self.client.mouse_handler.click_window_with_name(name='ConfirmTargetsConfirm')
					except:
						await asyncio.sleep(0.1)
				self.passed = False
			else:
				logger.debug(f"Client {self.client.title} - Passing")
				await self.pass_button()
				self.passed = True

			# detect failed cast, only if the client is soloing and is not in pvp as to avoid issues
			await asyncio.sleep(1)
			if len(self.clients) == len(self.allies) and not in_pvp:  # bad check to see if it's only your char's in battle.
				if await self.client.duel.duel_phase() == DuelPhase.planning:
					await asyncio.sleep(0.5)
					pass
				else:
					break
			else:
				break

#big thanks to major for doing most of the work, & click for helping
	#TODO not overread
	async def get_school_template_name(self, member: CombatMember):
		part = await member.get_participant()
		school_id = await part.primary_magic_school_id()
		return await self.client.cache_handler.get_template_name(school_id)

	async def read_target_effect(self, card):
		card_targets = []

		for effect in await card.get_spell_effects():
			type_name = await effect.maybe_read_type_name()

			if "random" in type_name.lower() or "variable" in type_name.lower():
				subeffects = await effect.maybe_effect_list()
				card_targets.append(await subeffects[0].effect_target())

			else:
				card_targets.append(await effect.effect_target())

		return card_targets

	async def read_spell_effect(self, card):
		spell_effects = []

		for effect in await card.get_spell_effects():
			type_name = await effect.maybe_read_type_name()

			if "random" in type_name.lower() or "variable" in type_name.lower():
				subeffects = await effect.maybe_effect_list()
				spell_effects.append(await subeffects[0].effect_type())

			else:
				spell_effects.append(await effect.effect_type())

		return spell_effects

	async def read_damage_type(self, card):
		spell_effects = []

		for effect in await card.get_spell_effects():
			type_name = await effect.maybe_read_type_name()

			if "random" in type_name.lower() or "variable" in type_name.lower():
				subeffects = await effect.maybe_effect_list()
				spell_effects.append(await subeffects[0].string_damage_type())

			else:
				spell_effects.append(await effect.string_damage_type())

		return spell_effects


	async def read_damage_type_id(self, card : CombatCard) -> list[int]:
		spell_effects = []

		for effect in await card.get_spell_effects():
			type_name = await effect.maybe_read_type_name()

			if "random" in type_name.lower() or "variable" in type_name.lower():
				subeffects = await effect.maybe_effect_list()
				spell_effects.append(await subeffects[0].damage_type())

			else:
				spell_effects.append(await effect.damage_type())
		return spell_effects

	async def average_effect_param(self, card: CombatCard, compared_effects : list[SpellEffects] = DAMAGE_EFFECTS):
		subeffect_params = []
		effect_params = []
		client_pips = (self.member_power_pips[self.client_member] * 2) + self.member_pips[self.client_member]
		

		for effect in await card.get_spell_effects():
			type_name = await effect.maybe_read_type_name()

			if "random" in type_name.lower() or "variable" in type_name.lower():
				subeffects = await effect.maybe_effect_list()

				for i, subeffect in enumerate(subeffects):
					subeffect_type = await subeffect.effect_type()

					if subeffect_type in compared_effects:
						if len(subeffects) == 14:
							if i == (client_pips - 1):
								subeffect_params.append(await subeffect.effect_param())
						else:
							subeffect_params.append(await subeffect.effect_param())

				if subeffect_params:
					total = 0
					for effect_param in subeffect_params:
						total += effect_param

					return (total / len(subeffect_params))

			else:

				effect_type = await effect.effect_type()

				if effect_type in compared_effects:
					effect_params.append(await effect.effect_param())

		total_param = 0
		for effect_param in effect_params:
			total_param += effect_param

		return total_param

	async def highest_damage_card(self, cards: list):
		highest_damage = 0
		damagest_card = None
		for card in cards:

			card_effects = await self.read_spell_effect(card)
			card_targets = await self.read_target_effect(card)

			if (any([effects in card_effects for effects in DAMAGE_EFFECTS])) and (any([effects in card_targets for effects in DAMAGE_TARGETS])):
				if await self.average_effect_param(card) > highest_damage:
					highest_damage = await self.average_effect_param(card)

					damagest_card = card

		return damagest_card

	async def get_index_from_list(self, name, list):
		for i, x in enumerate(list):
			if name == x:
				return i


	# Calculates damage from given base damage value, and is the basis for both exact and damage potential calculation.
	async def calculate_damage_from_base(self, caster: CombatMember, target: CombatMember, damage: float, card: CombatCard = None) -> float:
		"""
		Calculates damage from a given base damage, from a specific caster onto a specific target combat member.

		Args:
			caster: Combat member of the desired caster
			target: Combat member of the desired caster
			damage: The spell's base damage (enchant added)
			card: Optional card input for exact calculation
		"""
		caster_level = await self.member_stats[caster].reference_level()

		caster_damages = self.member_damages[caster]
		caster_flat_damages = self.member_flat_damages[caster]

		caster_hanging_effects = self.member_hanging_effects[caster]
		caster_hanging_effects += self.member_aura_effects[caster]
		caster_hanging_effects += self.member_shadow_effects[caster]
		if self.combat_resolver:  # Globals
			global_effect = await self.combat_resolver.global_effect()
			if global_effect is not None:
				caster_hanging_effects.append(global_effect)

		if card:
			card_graphical_spell = await card.get_graphical_spell()
			card_school = await card_graphical_spell.magic_school_id()
		else:
			card_school = self.member_school_ids[caster]

		target_resistances = self.member_resistances[target]
		target_flat_resistances = self.member_flat_resistances[target]

		target_hanging_effects = self.member_hanging_effects[target]
		target_hanging_effects += self.member_aura_effects[target]
		target_hanging_effects += self.member_shadow_effects[target]

		caster_pierce_values = self.member_pierce[caster]

		caster_crit_ratings = self.member_critical_ratings[caster]
		caster_crit_rating = caster_crit_ratings[school_list_ids[card_school]]

		target_block_ratings = self.member_critical_ratings[target]
		target_block_rating = target_block_ratings[school_list_ids[card_school]]


		# assign params and types and such for every hanging effect so we only have to read these values once per turn
		total_hanging_effects = caster_hanging_effects + target_hanging_effects
		effect_params = {}
		effect_types = {}
		effect_schools = {}
		effect_templates = {}
		effect_enchant_templates = {}
		effect_atrs = {}
		if total_hanging_effects:
			for effect in total_hanging_effects:
				effect_params[effect] = await effect.effect_param()
				effect_types[effect] = await effect.effect_type()
				effect_schools[effect] = await effect.damage_type()
				effect_templates[effect] = await effect.spell_template_id()
				effect_enchant_templates[effect] = await effect.enchantment_spell_template_id()
				effect_atrs[effect] = (effect_templates[effect], effect_enchant_templates[effect], effect_schools[effect], effect_types[effect])


		# remove duplicate effects from caster hanging effects list
		if caster_hanging_effects:
			checked_effect_atrs = []
			for effect in caster_hanging_effects.copy():
				if not effect_atrs[effect] in checked_effect_atrs:
					checked_effect_atrs.append(effect_atrs[effect])
				else:
					caster_hanging_effects.reverse()
					caster_hanging_effects.remove(effect)
					caster_hanging_effects.reverse()


		# remove duplicate effects from target hanging effects list
		if target_hanging_effects:
			checked_effect_atrs = []
			for effect in target_hanging_effects.copy():
				if not effect_atrs[effect] in checked_effect_atrs:
					checked_effect_atrs.append(effect_atrs[effect])
				else:
					target_hanging_effects.reverse()
					target_hanging_effects.remove(effect)
					target_hanging_effects.reverse()


		# redo the total effects list
		total_hanging_effects = target_hanging_effects + caster_hanging_effects


		# get relevant damage %, with damage limit
		caster_damage = caster_damages[school_list_ids[card_school]]
		caster_damage_percent = caster_damage * 100
		if caster_damage > 1.50:
			limit = float(await self.client.duel.damage_limit()) * 100
			caster_damage_percent = float(limit - 536.43 * (math.e ** (-0.0158 * caster_damage_percent)))
			caster_damage = (caster_damage_percent / 100) + 1
		else:
			caster_damage += 1


		# get relevant flat damage
		caster_flat_damage = caster_flat_damages[school_list_ids[card_school]]

		# get relevant pierce value
		caster_pierce = caster_pierce_values[school_list_ids[card_school]]

		# apply percentage damage
		damage *= caster_damage

		# apply flat damage
		damage += caster_flat_damage

		# calculates critical multiplier and chance
		if caster_crit_rating > 0:
			if caster_level > 100:
				caster_level = 100
			crit_damage_multiplier = (2 - ((target_block_rating)/((caster_crit_rating / 3) + target_block_rating)))
			client_school_critical = (0.03 * caster_level * caster_crit_rating)
			mob_block = (3 * caster_crit_rating + target_block_rating)
			crit_chance = client_school_critical / mob_block
			# applying the crit multiplier if the chance is above a certain threshold
			if crit_chance >= 0.85:
				damage *= crit_damage_multiplier

		# outgoing hanging effects (caster)
		if caster_hanging_effects:
			for effect in caster_hanging_effects:
				# only consider effects that matches the school or are universal
				if effect_schools[effect] == card_school or effect_schools[effect] == 80289:
					match effect_types[effect]:
						case SpellEffects.modify_outgoing_damage:
							damage *= (effect_params[effect] / 100) + 1

						case SpellEffects.modify_outgoing_damage_flat:
							damage += effect_params[effect]

						case SpellEffects.modify_outgoing_armor_piercing:
							caster_pierce += effect_params[effect]

						case SpellEffects.modify_outgoing_damage_type:
							if card_school in opposite_school_ids:
								card_school = opposite_school_ids[effect_schools[effect]]

						case _:
							pass

		# incoming hanging effects (target)
		if target_hanging_effects:
			for effect in target_hanging_effects:
				if effect_schools[effect] == card_school or effect_schools[effect] == 80289:
					match effect_types[effect]:
						# traps/shields, and pierce handling
						case SpellEffects.modify_incoming_damage:
							ward_param = effect_params[effect]
							if ward_param < 0:
								ward_param += caster_pierce
								caster_pierce += effect_params[effect]
								if ward_param > 0:
									ward_param = 0
								if caster_pierce < 0:
									caster_pierce = 0
							damage *= (ward_param / 100) + 1

						case SpellEffects.intercept:
							damage *= (effect_params[effect] / 100) + 1

						case SpellEffects.modify_incoming_damage_flat:
							damage += effect_params[effect]

						case SpellEffects.absorb_damage:
							damage += effect_params[effect]

						case SpellEffects.modify_incoming_armor_piercing:
							caster_pierce += effect_params[effect]
						# prism handling
						case SpellEffects.modify_incoming_damage_type:
							if card_school in opposite_school_ids:
								card_school = opposite_school_ids[effect_schools[effect]]

						case _:
							pass

		# get school relevant target resist
		target_resist = target_resistances[school_list_ids[card_school]]

		# get school relevant target flat resist
		target_flat_resist = target_flat_resistances[school_list_ids[card_school]]

		# apply flat resist
		damage -= target_flat_resist

		# apply resist, accounting for pierce and potential boost
		if target_resist > 0:
			target_resist -= caster_pierce
			if target_resist <= 0:
				target_resist = 1
			else:
				target_resist = 1 - target_resist
		else:
			target_resist = abs(target_resist) + 1

		damage *= target_resist

		return damage


	# Damage potential calculation, uses DPP to estimate max possible spell damage
	async def member_damage_potential(self, caster: CombatMember, target: CombatMember) -> float:
		"""
		Calculates the estimated maximum damage potential a combat member could do against another, if they were to hit now.

		Args:
			caster: CombatMember that would be hitting the target
			target: CombatMember that is the target of the hit
		"""

		# Get relevant stats and hanging effects from dictionaries for the two combat members
		caster_normal_pips = self.member_pips[caster]
		caster_shadow_pips = self.member_shadow_pips[caster]
		caster_power_pips = self.member_power_pips[caster]

		# Damage per pip averages, these are the fire ones as it should provide a good estimate for damage output for all schools, even astral/shadow
		damage_estimate = 100

		if caster_shadow_pips:
			damage_estimate += 20

		# calculate total normal pips, including value of shadow pips
		caster_total_pips = (caster_power_pips * 2) + (caster_shadow_pips * 3.6) + (caster_normal_pips)

		# calculate estimated base damage, based on dpp and total pips
		damage_estimate *= caster_total_pips

		return await self.calculate_damage_from_base(caster, target, damage_estimate)


	# Exact damage calculation, does not round anything so may be ~5 off with higher buffed spells
	async def calculate_damage(self, target: CombatMember, card: CombatCard, enchant: CombatCard = None) -> float:
		"""
		Calculates damage from a given card, on a specific target combat member.

		Args:
			target: The combat member of the target
			card: a damage card
			enchant_card: a damage enchant
		"""

		damage = await self.average_effect_param(card)

		if enchant:
			damage += await self.average_effect_param(enchant)

		final_damage = await self.calculate_damage_from_base(self.client_member, target, damage, card=card)

		return final_damage


	async def will_kill(self, card: CombatCard, enchant: CombatCard = None) -> bool:
		kill_counter = 0
		for target in self.mobs:
			target_health = self.mob_healths[target]
			damage = await self.calculate_damage(target, card, enchant)
			if damage >= target_health:
				kill_counter = kill_counter + 1
		if kill_counter / len(self.mobs) >= 0.5:
			return True
		# Accept smaller hit percentages in PVP
		if any([await m.is_player() for m in self.mobs]):
			if target_health > 3000:
				return damage >= target_health / 3.5
			else:
				return damage >= target_health
		if self.client.sigil_status:
			# TODO: Disable this if more than one client
			return damage >= (target_health / len(self.allies))


	async def damage_calc_handle_round(self, cards):
		await asyncio.sleep(0.5)

		
		# Sorting Enchants and Normals
		enchants = []
		normals = []
		for card in cards:
			if await card.is_castable():
				enchant_target = await self.read_target_effect(card)
				if EffectTarget.spell in enchant_target:
					enchants.append(card)
				else:
					normals.append(card)

		# Sorting enchants
		damage_enchants = []
		strict_damage_enchants = []
		for enchant in enchants:
			enchant_types = await self.read_spell_effect(enchant)

			if any([effects in enchant_types for effects in DAMAGE_ENCHANT_EFFECTS]):
				damage_enchants.append(enchant)
			if any([effects in enchant_types for effects in STRICT_DAMAGE_ENCHANT_EFFECTS]):
				strict_damage_enchants.append(enchant)

		# Finding Highest Damage card
		damagest_card = await self.highest_damage_card(normals)

		if strict_damage_enchants:
			enchant_damage = strict_damage_enchants[0]
		else:
			enchant_damage = None
		
		if damagest_card:
			
			if result := await self.will_kill(damagest_card, enchant_damage):
				return damagest_card, result
		# print("Ready to cast")
		return None, False