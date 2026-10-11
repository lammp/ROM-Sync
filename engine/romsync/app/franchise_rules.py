"""The franchise rules (F5-S10): version 1's, as data.

One rule per line: a title pattern, a tab, the franchise it proposes. A
pattern is a case-insensitive regular expression searched in the title. The
names follow the metadata service's franchise names where one exists, so an
accepted proposal merges with the service's own tags. Changing a rule is
changing this text; no code reads a rule any other way.

This is a Python module rather than a TSV file because the repository
publishes only `.py` under `engine/` (law 8); whether to publish data files
there is Matt's call.

One rule differs from version 1: Green Lantern is DC, not Marvel, and is
dropped from the Marvel rule (recorded as an error in ARCHITECTURE.md).
"""

RULES = r"""
^(new )?super mario|^mario (kart|party|golf|tennis|sports|bros|& (luigi|sonic))|^paper mario|^dr\.? mario|^captain toad|^luigi's mansion|^super mario maker|^mario & luigi	Mario
^yoshi|poochy & yoshi	Yoshi
^wario|^warioware	Wario
donkey kong	Donkey Kong
legend of zelda|^hyrule warriors	The Legend of Zelda
^pokemon|^pocket monsters|^(meitantei|detective) pikachu|^super pokemon rumble	Pokémon
^kirby	Kirby
^metroid	Metroid
^fire emblem	Fire Emblem
^star fox|^lylat wars|^starwing|^super star fox	Star Fox
^pilotwings	Pilotwings
^super smash bros	Super Smash Bros.
^animal crossing	Animal Crossing
^punch-out	Punch-Out!!
^ice climber	Ice Climber
^kid icarus	Kid Icarus
^xenoblade	Xenoblade
^tomodachi	Tomodachi
^(more )?brain training|^dr\.? kawashima|brain age	Brain Age
^nintendogs	Nintendogs
^picross	Picross
^rhythm (heaven|paradise|tengoku)	Rhythm Heaven
new style boutique|^style savvy	Style Savvy
art academy	Art Academy
^chibi-robo	Chibi-Robo!
^advance wars|^famicom wars	Wars
^golden sun	Golden Sun
^f-zero	F-Zero
^bayonetta	Bayonetta
^sin & punishment	Sin and Punishment
^ultimate nes remix|^nes remix	NES Remix
^sonic|^mario & sonic|^sonic boom	Sonic the Hedgehog
^super monkey ball	Super Monkey Ball
^golden axe	Golden Axe
^shinobi|^shadow dancer	Shinobi
^after burner	After Burner
^space harrier	Space Harrier
^outrun	OutRun
^crazy taxi	Crazy Taxi
^alex kidd	Alex Kidd
^phantasy star	Phantasy Star
^virtua fighter	Virtua Fighter
^streets of rage	Streets of Rage
^wonder boy	Wonder Boy
^fantasy zone	Fantasy Zone
^mega ?man|^rockman	Mega Man
street fighter	Street Fighter
^resident evil|^biohazard	Resident Evil
^monster hunter	Monster Hunter
^devil may cry	Devil May Cry
^final fight	Final Fight
^ghosts ?'?n ?goblins|^ghouls ?'?n ?ghosts|^gargoyle's quest|^demon's crest	Ghosts 'n Goblins
^marvel vs\.? capcom|^x-men vs|^marvel super heroes vs	Marvel vs. Capcom
^ace attorney|phoenix wright	Ace Attorney
^breath of fire	Breath of Fire
^1942|^1943|^1941|^1944|^19xx	194X
^bionic commando	Bionic Commando
^strider	Strider
^captain commando	Captain Commando
^alien vs\.? predator|^aliens vs\.? predator	Alien vs. Predator
^castlevania|^akumajou	Castlevania
^contra|^super c$|^probotector	Contra
^metal gear	Metal Gear
^gradius|^salamander|^life force|^nemesis	Gradius
^silent hill	Silent Hill
^teenage mutant ninja turtles|^tmnt|nickelodeon teenage mutant	Teenage Mutant Ninja Turtles
^track & field|^international track & field|^hyper sports	Track & Field
^pro evolution soccer|^winning eleven|^pes 	Pro Evolution Soccer
^yu-gi-oh	Yu-Gi-Oh!
^suikoden	Suikoden
^twinbee|^pop'n twinbee	TwinBee
^goemon|^mystical ninja	Ganbare Goemon
^sunset riders	Sunset Riders
^rush'?n attack|^green beret	Rush'n Attack
^blades of steel	Blades of Steel
^frogger	Frogger
^dance dance revolution	Dance Dance Revolution
final fantasy|^theatrhythm|^chocobo	Final Fantasy
^dragon quest|^dragon warrior	Dragon Quest
^kingdom hearts	Kingdom Hearts
^chrono (trigger|cross)	Chrono
^secret of mana|^trials of mana|^seiken densetsu|^legend of mana|^sword of mana	Mana
^bravely	Bravely
^parasite eve|^the 3rd birthday	Parasite Eve
^shin megami tensei|^persona|^devil survivor|^soul hackers|^strange journey|^megami tensei|persona q	Shin Megami Tensei
^etrian	Etrian Odyssey
^radiant historia	Radiant Historia
^star ocean	Star Ocean
^saga |^romancing saga|^saga frontier|^the alliance alive|^the legend of legacy	SaGa
^actraiser	ActRaiser
^ogre battle|^tactics ogre	Ogre Battle
^front mission	Front Mission
^valkyrie profile	Valkyrie Profile
^xenogears|^xenosaga	Xeno
^tales of	Tales
^ys 	Ys
^lufia	Lufia
^gran turismo	Gran Turismo
^god of war	God of War
^ratchet & clank|^ratchet and clank	Ratchet & Clank
^jak (ii|3|x|and daxter)|^daxter	Jak and Daxter
^sly (cooper|2|3)	Sly Cooper
^ape escape|^ape academy	Ape Escape
^twisted metal	Twisted Metal
^wipeout( 64| xl| 2097| fusion| pure| pulse| hd)?$	Wipeout
^crash bandicoot|^crash team racing|^ctr:	Crash Bandicoot
^spyro	Spyro the Dragon
^syphon filter	Syphon Filter
^ico$|^shadow of the colossus	Ico
^dark cloud	Dark Cloud
^killzone	Killzone
^patapon	Patapon
^locoroco	LocoRoco
^hot shots golf|^everybody's golf	Everybody's Golf
^tekken	Tekken
^ridge racer|^r4:	Ridge Racer
^ace combat	Ace Combat
^katamari|^we love katamari	Katamari
^pac-?man|^pac-mania|^ms\.? pac-man|^pacman	Pac-Man
^galaga|^galaxian|^galaga 	Galaga
^dig dug	Dig Dug
^xevious	Xevious
^mappy	Mappy
^dragon spirit|^dragon saber	Dragon Spirit
^dragon buster	Dragon Buster
^sky kid	Sky Kid
^rolling thunder	Rolling Thunder
^splatterhouse	Splatterhouse
tower of druaga|^druaga	The Tower of Druaga
^klonoa	Klonoa
^soul calibur|^soulcalibur|^soul edge	Soulcalibur
^time crisis|^point blank	Time Crisis
^bubble bobble|^puzzle bobble|^bust-a-move|^rainbow islands|^parasol stars	Bubble Bobble
^space invaders	Space Invaders
^arkanoid	Arkanoid
^darius	Darius
^elevator action	Elevator Action
^chase h\.?q|^super chase	Chase H.Q.
^operation wolf|^operation thunderbolt	Operation Wolf
^the newzealand story|^kiwi kraze	The NewZealand Story
^metal slug	Metal Slug
king of fighters	The King of Fighters
^samurai shodown|^samurai spirits	Samurai Shodown
^fatal fury|^garou	Fatal Fury
^art of fighting	Art of Fighting
^ikari	Ikari Warriors
^athena|^psycho soldier	Athena
^r-type	R-Type
^ninja (spirit|gaiden)|^shadow warriors	Ninja Gaiden
^hammerin' harry	Hammerin' Harry
^tecmo (super )?bowl	Tecmo Bowl
^rygar	Rygar
^dead or alive	Dead or Alive
^bad dudes	Bad Dudes
^joe & mac|^caveman ninja	Joe & Mac
^burgertime	BurgerTime
^karnov	Karnov
^double dragon	Double Dragon
^river city|^kunio|^nekketsu|^renegade$|^super dodge ball	Kunio-kun
^centipede|^millipede	Centipede
^asteroids	Asteroids
^missile command	Missile Command
^marble madness	Marble Madness
^gauntlet	Gauntlet
^paperboy	Paperboy
^rampart	Rampart
^mortal kombat|^ultimate mortal kombat	Mortal Kombat
^nba jam	NBA Jam
^smash t\.?v|^super smash t\.?v|^total carnage	Smash TV
^rampage	Rampage
^spy hunter|^super spy hunter	Spy Hunter
^san francisco rush|^rush 2:	San Francisco Rush
^cruis'n	Cruis'n
^hydro thunder	Hydro Thunder
^ready 2 rumble	Ready 2 Rumble Boxing
^joust$	Joust
^defender( ii)?$	Defender
^robotron	Robotron
^q\*bert|^q-bert	Q*bert
^toki	Toki
^snow bros	Snow Bros.
^dodonpachi|^donpachi	DonPachi
^raiden	Raiden
^turrican	Turrican
^lode runner|^championship lode runner	Lode Runner
^boulder dash	Boulder Dash
^pitfall	Pitfall!
^wizards & warriors|^ironsword	Wizards & Warriors
^battletoads	Battletoads
^r\.c\. pro-am	R.C. Pro-Am
^banjo	Banjo-Kazooie
^conker	Conker
^dizzy|^fantastic adventures of dizzy|^treasure island dizzy|^wonderland dizzy|^go! dizzy	Dizzy
^micro machines	Micro Machines
^bomberman|^dynablaster|^super bomberman	Bomberman
^adventure island	Adventure Island
^bonk|^bc kid|^pc kid	Bonk
^bubsy	Bubsy
^clay ?fighter	ClayFighter
^earthworm jim	Earthworm Jim
^aero the acro-bat	Aero the Acro-Bat
^zero the kamikaze	Aero the Acro-Bat
^the lost vikings|^lost vikings	The Lost Vikings
^rock n'? roll racing	Rock n' Roll Racing
^blackthorne	Blackthorne
^ultima(:| [ivx]|$)	Ultima
^wing commander	Wing Commander
^populous	Populous
^syndicate	Syndicate
^theme park	Theme Park
^sid meier's civilization|^civilization	Civilization
^desert strike|^jungle strike|^urban strike|^nuclear strike|^soviet strike	Strike
^road rash	Road Rash
^skate or die|^ski or die	Skate or Die
^snowboard kids	Snowboard Kids
^extreme-g	Extreme-G
^gex	Gex
^star soldier|^starship hector|^hector	Star Soldier
^quake	Quake
^doom( ii| 64|$)	Doom
^hexen|^heretic	Heretic
^starcraft	StarCraft
^vigilante 8	Vigilante 8
^chameleon twist	Chameleon Twist
^fighters destiny|^fighter destiny	Fighters Destiny
^bases loaded|^super bases loaded	Bases Loaded
^r\.b\.i\. baseball|^super r\.b\.i	R.B.I. Baseball
^baseball stars	Baseball Stars
^tetris|^super tetris|^wordtris|^hatris	Tetris
^solomon's key|^fire 'n ice	Solomon's Key
^kid niki	Kid Niki
^ninja jajamaru	Ninja JaJaMaru-kun
^hydlide	Hydlide
^startropics|^zoda's revenge	StarTropics
^power blade	Power Blade
^blaster master|^chou-wakusei	Blaster Master
^fifa	FIFA
^madden	Madden NFL
^nhl 	NHL
^tony hawk	Tony Hawk's
^ssx	SSX
^need for speed	Need for Speed
^burnout	Burnout
^midnight club	Midnight Club
^grand theft auto|^gta 	Grand Theft Auto
^timesplitters	TimeSplitters
^prince of persia	Prince of Persia
^psychonauts	Psychonauts
^armored core	Armored Core
^colin mcrae|^dirt 	Colin McRae
^wrc	WRC
^f1 |^formula (1|one)|^f-1 	Formula One
^army of two	Army of Two
^007|^james bond|^goldeneye	James Bond
^tenchu	Tenchu
^oddworld	Oddworld
^driver	Driver
^tomba	Tomba!
^mega man legends	Mega Man
^dragon ball	Dragon Ball
^naruto	Naruto
^one piece	One Piece
^inazuma eleven	Inazuma Eleven
^yo-kai watch	Yo-kai Watch
^professor layton|^layton's	Professor Layton
^project x zone	Project X Zone
^senran kagura	Senran Kagura
^zero escape	Zero Escape
^corpse party	Corpse Party
^hatsune miku|^project diva|^project mirai	Hatsune Miku
^harvest moon|^story of seasons|^bokujou	Harvest Moon
^rune factory	Rune Factory
^cooking mama|^gardening mama	Cooking Mama
^hello kitty	Hello Kitty
^lego|^la (grande )?lego|^the lego movie	LEGO
star wars	Star Wars
harry potter	Harry Potter
lord of the rings|the hobbit|^lego (der herr|el senor|le seigneur|der hobbit|el hobbit)	The Lord of the Rings
^batman|^lego batman	Batman
spider-man	Spider-Man
^x-men|^wolverine	X-Men
^transformers	Transformers
^power rangers	Power Rangers
^skylanders	Skylanders
^disney infinity	Disney Infinity
spongebob	SpongeBob SquarePants
^scooby-doo	Scooby-Doo
^the simpsons|^simpsons	The Simpsons
^the sims|^sims 	The Sims
^worms	Worms
^lemmings	Lemmings
^rayman|^rabbids	Rayman
splinter cell	Splinter Cell
ghost recon	Ghost Recon
^shrek	Shrek
^madagascar|^penguins of madagascar	Madagascar
^ice age	Ice Age
^kung fu panda	Kung Fu Panda
^how to train your dragon	How to Train Your Dragon
^cars 2|^disney planes|^cars:	Cars
^toy story	Toy Story
^finding nemo	Finding Nemo
^disney frozen|^frozen:	Frozen
^jewel quest	Jewel Quest
^jewel master	Jewel Master
^jewel link	Jewel Link
^mystery case files	Mystery Case Files
^imagine	Imagine
^petz	Petz
^monster high	Monster High
^moshi monsters	Moshi Monsters
^wwe|^wcw|^wwf	WWE
^pinball hall of fame	Pinball Hall of Fame
^puzzler	Puzzler
^farming simulator	Farming Simulator
^rollercoaster tycoon	RollerCoaster Tycoon
^shovel knight	Shovel Knight
^shantae	Shantae
^cave story	Cave Story
^terraria	Terraria
^minecraft	Minecraft
^scribblenauts	Scribblenauts
^no more heroes	No More Heroes
^tiger woods	PGA Tour
^wipeout( 2| 3|: create)	Wipeout (TV)
^the amazing spider-man	Spider-Man
^thor:|^captain america|^iron man	Marvel
^lego marvel	Marvel
"""
