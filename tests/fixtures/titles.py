"""The title corpus.

One row per title: the title, its strict key, its loose key, and the property
the row pins. Every title is a published game title. The keys are version
1's, captured by `ui/parity/titles` running version 1's own twin key
functions from the tag, and `titles.capture.test.ts` proves they still are.

Tab separated. A key may be empty: a title written wholly in a non-Latin
script has no Latin key at all, and version 1 treats it so.
"""

from __future__ import annotations

from typing import NamedTuple


class TitleRow(NamedTuple):
    title: str
    strict: str
    loose: str
    pins: str


ROWS = r"""
Final Fantasy II	finalfantasy2	finalfantasy2	roman numeral
Final Fantasy III	finalfantasy3	finalfantasy3	roman numeral
Final Fantasy IV	finalfantasy4	finalfantasy4	roman numeral
Final Fantasy V	finalfantasy5	finalfantasy5	roman numeral
Final Fantasy VI	finalfantasy6	finalfantasy6	roman numeral
Final Fantasy VII	finalfantasy7	finalfantasy7	roman numeral
Final Fantasy VIII	finalfantasy8	finalfantasy8	roman numeral
Final Fantasy IX	finalfantasy9	finalfantasy9	roman numeral
Final Fantasy X	finalfantasy10	finalfantasy10	roman numeral
Final Fantasy XII	finalfantasyxii	finalfantasyxii	roman numeral
Dragon Quest II	dragonquest2	dragonquest2	roman numeral
Dragon Quest III	dragonquest3	dragonquest3	roman numeral
Dragon Quest IV	dragonquest4	dragonquest4	roman numeral
Dragon Quest V	dragonquest5	dragonquest5	roman numeral
Dragon Quest VI	dragonquest6	dragonquest6	roman numeral
Dragon Quest VII	dragonquest7	dragonquest7	roman numeral
Dragon Quest VIII	dragonquest8	dragonquest8	roman numeral
Dragon Quest IX	dragonquest9	dragonquest9	roman numeral
Grand Theft Auto IV	grandtheftauto4	grandtheftauto4	roman numeral
Grand Theft Auto V	grandtheftauto5	grandtheftauto5	roman numeral
Kingdom Hearts II	kingdomhearts2	kingdomhearts2	roman numeral
Civilization IV	civilization4	civilization4	roman numeral
Street Fighter II	streetfighter2	streetfighter2	roman numeral
Street Fighter III: 3rd Strike	streetfighter33rdstrike	streetfighter33rdstrike	roman numeral
Ultima VII	ultima7	ultima7	roman numeral
Metroid II: Return of Samus	metroid2returnofsamus	metroid2returnofsamus	roman numeral
Zelda II: The Adventure of Link	zelda2adventureoflink	zelda2adventureoflink	roman numeral
Mega Man II	megaman2	megaman2	roman numeral
Castlevania II: Simon's Quest	castlevania2simonsquest	castlevania2simonsquest	roman numeral
Ninja Gaiden II	ninjagaiden2	ninjagaiden2	roman numeral
Mortal Kombat II	mortalkombat2	mortalkombat2	roman numeral
Double Dragon II: The Revenge	doubledragon2revenge	doubledragon2revenge	roman numeral
Phantasy Star IV	phantasystar4	phantasystar4	roman numeral
Wizardry VI	wizardry6	wizardry6	roman numeral
Shining Force II	shiningforce2	shiningforce2	roman numeral
Suikoden II	suikoden2	suikoden2	roman numeral
Jak II	jak2	jak2	roman numeral
Breath of Fire II	breathoffire2	breathoffire2	roman numeral
Lunar II: Eternal Blue	lunar2eternalblue	lunar2eternalblue	roman numeral
Soulcalibur II	soulcalibur2	soulcalibur2	roman numeral
Final Fantasy XI	finalfantasyxi	finalfantasyxi	roman numeral past ten stays a word
Final Fantasy XIII	finalfantasyxiii	finalfantasyxiii	roman numeral past ten stays a word
Final Fantasy XIV	finalfantasyxiv	finalfantasyxiv	roman numeral past ten stays a word
Final Fantasy XV	finalfantasyxv	finalfantasyxv	roman numeral past ten stays a word
Dragon Quest XI	dragonquestxi	dragonquestxi	roman numeral past ten stays a word
Final Fantasy XIII-2	finalfantasyxiii2	finalfantasyxiii2	roman numeral past ten stays a word
Dragon Quest X	dragonquest10	dragonquest10	roman numeral past ten stays a word
Final Fantasy XVI	finalfantasyxvi	finalfantasyxvi	roman numeral past ten stays a word
I Am Setsuna	iamsetsuna	iamsetsuna	a single i is not a numeral
Ice Climber	iceclimber	iceclimber	a single i is not a numeral
Ikaruga	ikaruga	ikaruga	a single i is not a numeral
Ico	ico	ico	a single i is not a numeral
Final Fantasy Tactics	finalfantasytactics	finalfantasytactics	a single i is not a numeral
Mega Man 2	megaman2	megaman2	digits kept as digits
Mega Man 10	megaman10	megaman10	digits kept as digits
Sonic Adventure 2	sonicadventure2	sonicadventure2	digits kept as digits
Super Mario 64	supermario64	supermario64	digits kept as digits
Star Fox 64	starfox64	starfox64	digits kept as digits
Tekken 3	tekken3	tekken3	digits kept as digits
Resident Evil 4	residentevil4	residentevil4	digits kept as digits
Persona 5	persona5	persona5	digits kept as digits
Fallout 3	fallout3	fallout3	digits kept as digits
Half-Life 2	halflife2	halflife2	digits kept as digits
Bomberman 64	bomberman64	bomberman64	digits kept as digits
Mario Kart 8	mariokart8	mariokart8	digits kept as digits
Super Mario Bros. 3	supermariobros3	supermariobros3	digits kept as digits
Gran Turismo 4	granturismo4	granturismo4	digits kept as digits
Crash Bandicoot 2: Cortex Strikes Back	crashbandicoot2cortexstrikesback	crashbandicoot2cortexstrikesback	digits kept as digits
Punch-Out!!	punchoutii	punchoutii	exclamation folded to i
Mario Kart: Double Dash!!	mariokartdoubledashii	mariokartdoubledashii	exclamation folded to i
Yo! Noid	yoinoid	yoinoid	exclamation folded to i
Mike Tyson's Punch-Out!!	miketysonspunchoutii	miketysonspunchoutii	exclamation folded to i
Super Punch-Out!!	superpunchoutii	superpunchoutii	exclamation folded to i
Pokemon Let's Go, Pikachu!	pokemonletsgopikachui	pokemonletsgopikachui	exclamation folded to i
Pokemon Let's Go, Eevee!	pokemonletsgoeeveei	pokemonletsgoeeveei	exclamation folded to i
WarioWare: Touched!	wariowaretouchedi	wariowaretouchedi	exclamation folded to i
Eek! The Cat	eekicat	eekicat	exclamation folded to i
Hey You, Pikachu!	heyyoupikachui	heyyoupikachui	exclamation folded to i
Ratchet & Clank	ratchetandclank	ratchetandclank	ampersand to and
Mario & Luigi: Superstar Saga	marioandluigisuperstarsaga	marioandluigisuperstarsaga	ampersand to and
Sonic & Knuckles	sonicandknuckles	sonicandknuckles	ampersand to and
Mario & Sonic at the Olympic Games	marioandsonicatolympicgames	marioandsonicatolympicgames	ampersand to and
Lilo & Stitch	liloandstitch	liloandstitch	ampersand to and
Kane & Lynch: Dead Men	kaneandlynchdeadmen	kaneandlynchdeadmen	ampersand to and
Brothers: A Tale of Two Sons	brotherstaleoftwosons	brotherstaleoftwosons	ampersand to and
Jak and Daxter: The Precursor Legacy	jakanddaxterprecursorlegacy	jakanddaxterprecursorlegacy	ampersand to and
Ratchet and Clank	ratchetandclank	ratchetandclank	ampersand to and
Sly Cooper and the Thievius Raccoonus	slycooperandthieviusraccoonus	slycooperandthieviusraccoonus	ampersand to and
Snoopy vs. the Red Baron	snoopyvsredbaron	snoopyvsredbaron	ampersand to and
Rock n' Roll Racing	rocknrollracing	rocknrollracing	ampersand to and
Spy vs. Spy	spyvsspy	spyvsspy	ampersand to and
Ben 10	ben10	ben10	ampersand to and
Tom and Jerry	tomandjerry	tomandjerry	ampersand to and
Yoshi's Island	yoshisisland	yoshisisland	apostrophe dropped
Luigi's Mansion	luigismansion	luigismansion	apostrophe dropped
Kirby's Dream Land	kirbysdreamland	kirbysdreamland	apostrophe dropped
Tony Hawk's Pro Skater	tonyhawksproskater	tonyhawksproskater	apostrophe dropped
Assassin's Creed	assassinscreed	assassinscreed	apostrophe dropped
Baldur's Gate	baldursgate	baldursgate	apostrophe dropped
Demon's Souls	demonssouls	demonssouls	apostrophe dropped
Uncharted: Drake's Fortune	uncharteddrakesfortune	uncharteddrakesfortune	apostrophe dropped
Conker's Bad Fur Day	conkersbadfurday	conkersbadfurday	apostrophe dropped
Link's Awakening	linksawakening	linksawakening	apostrophe dropped
Kirby's Adventure	kirbysadventure	kirbysadventure	apostrophe dropped
Yoshi's Story	yoshisstory	yoshisstory	apostrophe dropped
Wario's Woods	warioswoods	warioswoods	apostrophe dropped
Ape Escape	apeescape	apeescape	apostrophe dropped
Luigi's Mansion 3	luigismansion3	luigismansion3	apostrophe dropped
Sid Meier's Pirates!	sidmeierspiratesi	sidmeierspiratesi	apostrophe dropped
Tom Clancy's Splinter Cell	tomclancyssplintercell	tomclancyssplintercell	apostrophe dropped
Kirby's Epic Yarn	kirbysepicyarn	kirbysepicyarn	apostrophe dropped
Mario's Picross	mariospicross	mariospicross	apostrophe dropped
Donkey Kong Country 2: Diddy's Kong Quest	donkeykongcountry2diddyskongquest	donkeykongcountry2diddyskongquest	apostrophe dropped
Yoshi’s Island	yoshisisland	yoshisisland	curly apostrophe is a separator
Luigi’s Mansion	luigismansion	luigismansion	curly apostrophe is a separator
Assassin’s Creed	assassinscreed	assassinscreed	curly apostrophe is a separator
The Legend of Zelda	legendofzelda	legendofzelda	leading article dropped
The Last of Us	lastofus	lastofus	leading article dropped
The Elder Scrolls V: Skyrim	elderscrolls5skyrim	elderscrolls5skyrim	leading article dropped
The Witcher 3: Wild Hunt	witcher3wildhunt	witcher3wildhunt	leading article dropped
The World Ends with You	worldendswithyou	worldendswithyou	leading article dropped
A Boy and His Blob	boyandhisblob	boyandhisblob	leading article dropped
An American Tail: Fievel Goes West	americantailfievelgoeswest	americantailfievelgoeswest	leading article dropped
The Simpsons: Hit & Run	simpsonshitandrun	simpsonshitandrun	leading article dropped
The Ninja Warriors	ninjawarriors	ninjawarriors	leading article dropped
The Adventures of Batman & Robin	adventuresofbatmanandrobin	adventuresofbatmanandrobin	leading article dropped
A Hat in Time	hatintime	hatintime	leading article dropped
A Link to the Past	linktopast	linktopast	leading article dropped
The House of the Dead	houseofdead	houseofdead	leading article dropped
The Bard's Tale	bardstale	bardstale	leading article dropped
The Lost Vikings	lostvikings	lostvikings	leading article dropped
Legend of the Mystical Ninja	legendofmysticalninja	legendofmysticalninja	article inside a title dropped
Shadow of the Colossus	shadowofcolossus	shadowofcolossus	article inside a title dropped
Prince of Persia: The Sands of Time	princeofpersiasandsoftime	princeofpersiasandsoftime	article inside a title dropped
Castlevania: Symphony of the Night	castlevaniasymphonyofnight	castlevaniasymphonyofnight	article inside a title dropped
Kingdom of Paradise	kingdomofparadise	kingdomofparadise	article inside a title dropped
Zone of the Enders	zoneofenders	zoneofenders	article inside a title dropped
Rise of the Tomb Raider	riseoftombraider	riseoftombraider	article inside a title dropped
Valkyrie Profile: Lenneth	valkyrieprofilelenneth	valkyrieprofilelenneth	article inside a title dropped
Super Mario Bros.: The Lost Levels	supermariobroslostlevels	supermariobroslostlevels	article inside a title dropped
Golden Sun: The Lost Age	goldensunlostage	goldensunlostage	article inside a title dropped
The Last of Us Part II	lastofus2	lastofus2	part dropped
Xenosaga Episode I: Der Wille zur Macht	xenosagaepisodeiderwillezurmacht	xenosagaepisodeiderwillezurmacht	part dropped
Final Fantasy VII Remake	finalfantasy7remake	finalfantasy7	part dropped
Kingdom Hearts 358/2 Days	kingdomhearts3582days	kingdomhearts3582days	part dropped
Phantasy Star Online Episode I & II	phantasystaronlineepisodeiand2	phantasystaronlineepisodeiand2	part dropped
Metroid Prime: Hunters	metroidprimehunters	metroidprimehunters	subtitle colon
Castlevania: Aria of Sorrow	castlevaniaariaofsorrow	castlevaniaariaofsorrow	subtitle colon
Tales of Symphonia: Dawn of the New World	talesofsymphoniadawnofnewworld	talesofsymphoniadawnofnewworld	subtitle colon
Fire Emblem: Three Houses	fireemblemthreehouses	fireemblemthreehouses	subtitle colon
Xenoblade Chronicles: Definitive Edition	xenobladechroniclesdefinitiveedition	xenobladechronicles	subtitle colon
Pokemon Mystery Dungeon: Explorers of Sky	pokemonmysterydungeonexplorersofsky	pokemonmysterydungeonexplorersofsky	subtitle colon
Kirby: Planet Robobot	kirbyplanetrobobot	kirbyplanetrobobot	subtitle colon
Phoenix Wright: Ace Attorney - Justice for All	phoenixwrightaceattorneyjusticeforall	phoenixwrightaceattorneyjusticeforall	subtitle colon
Shin Megami Tensei: Nocturne	shinmegamitenseinocturne	shinmegamitenseinocturne	subtitle colon
Metal Gear Solid V: The Phantom Pain	metalgearsolid5phantompain	metalgearsolid5phantompain	subtitle colon
Star Wars: Knights of the Old Republic	starwarsknightsofoldrepublic	starwarsknightsofoldrepublic	subtitle colon
Batman: Arkham Asylum	batmanarkhamasylum	batmanarkhamasylum	subtitle colon
Halo: Combat Evolved	halocombatevolved	halocombatevolved	subtitle colon
Ninja Gaiden: Dragon Sword	ninjagaidendragonsword	ninjagaidendragonsword	subtitle colon
Advance Wars: Dual Strike	advancewarsdualstrike	advancewarsdualstrike	subtitle colon
Okami HD	okamihd	okami	edition word stripped only by the loose key
The Legend of Zelda: Majora's Mask 3D	legendofzeldamajorasmask3d	legendofzeldamajorasmask	edition word stripped only by the loose key
Donkey Kong Country Returns 3D	donkeykongcountryreturns3d	donkeykongcountryreturns	edition word stripped only by the loose key
Link's Awakening DX	linksawakeningdx	linksawakening	edition word stripped only by the loose key
Tetris DX	tetrisdx	tetris	edition word stripped only by the loose key
Dragon Quest XI S: Echoes of an Elusive Age - Definitive Edition	dragonquestxisechoesofelusiveagedefinitiveedition	dragonquestxisechoesofelusiveage	edition word stripped only by the loose key
Tomb Raider: Anniversary	tombraideranniversary	tombraider	edition word stripped only by the loose key
Shadow of the Colossus Remastered	shadowofcolossusremastered	shadowofcolossus	edition word stripped only by the loose key
Final Fantasy X/X-2 HD Remaster	finalfantasy10102hdremaster	finalfantasy10102	edition word stripped only by the loose key
Kirby's Return to Dream Land Deluxe	kirbysreturntodreamlanddeluxe	kirbysreturntodreamland	edition word stripped only by the loose key
Mario Kart 8 Deluxe	mariokart8deluxe	mariokart8	edition word stripped only by the loose key
Resident Evil HD Remaster	residentevilhdremaster	residentevil	edition word stripped only by the loose key
WarioWare, Inc.: Mega Microgame$!	wariowareincmegamicrogamesi	wariowareincmegamicrogamesi	edition word stripped only by the loose key
Metroid: Samus Returns	metroidsamusreturns	metroidsamusreturns	a release form version 1 does not know is kept
Star Fox 64 3D	starfox643d	starfox64	edition word stripped only by the loose key
The Legend of Zelda: Ocarina of Time 3D	legendofzeldaocarinaoftime3d	legendofzeldaocarinaoftime	edition word stripped only by the loose key
Super Mario 3D Land	supermario3dland	supermario3dland	an edition word not at the end is kept
Luigi's Mansion 3D	luigismansion3d	luigismansion	edition word stripped only by the loose key
Kingdom Hearts HD 1.5 Remix	kingdomheartshd15remix	kingdomheartshd15remix	an edition word not at the end is kept
Persona 4 Golden	persona4golden	persona4golden	a release form version 1 does not know is kept
Final Fantasy XII The Zodiac Age	finalfantasyxiizodiacage	finalfantasyxiizodiacage	two edition words stripped in turn
Diablo III: Reaper of Souls - Ultimate Evil Edition	diablo3reaperofsoulsultimateeviledition	diablo3reaperofsoulsultimateevil	two edition words stripped in turn
Nier Replicant ver.1.22474487139 Remaster	nierreplicantver122474487139remaster	nierreplicantver122474487139	two edition words stripped in turn
Grandia HD Remaster	grandiahdremaster	grandia	two edition words stripped in turn
Spyro Reignited Trilogy	spyroreignitedtrilogy	spyroreignitedtrilogy	two edition words stripped in turn
Pokémon Red	pokmonred	pokmonred	accented letter is a separator
Pokémon Blue	pokmonblue	pokmonblue	accented letter is a separator
Pokémon Snap	pokmonsnap	pokmonsnap	accented letter is a separator
Brütal Legend	brtallegend	brtallegend	accented letter is a separator
Ōkami	kami	kami	accented letter is a separator
Pokémon Mystery Dungeon	pokmonmysterydungeon	pokmonmysterydungeon	accented letter is a separator
Pokémon Stadium	pokmonstadium	pokmonstadium	accented letter is a separator
Pokémon Emerald	pokmonemerald	pokmonemerald	accented letter is a separator
Pokémon Yellow	pokmonyellow	pokmonyellow	accented letter is a separator
Pokémon Crystal	pokmoncrystal	pokmoncrystal	accented letter is a separator
F-Zero	fzero	fzero	punctuation to a separator
Banjo-Kazooie	banjokazooie	banjokazooie	punctuation to a separator
Pac-Man	pacman	pacman	punctuation to a separator
Ms. Pac-Man	mspacman	mspacman	punctuation to a separator
Spider-Man 2	spiderman2	spiderman2	punctuation to a separator
R-Type	rtype	rtype	punctuation to a separator
Q*bert	qbert	qbert	punctuation to a separator
Dig Dug	digdug	digdug	punctuation to a separator
X-Men vs. Street Fighter	10menvsstreetfighter	10menvsstreetfighter	punctuation to a separator
Ys I & II	ysiand2	ysiand2	punctuation to a separator
Wave Race 64	waverace64	waverace64	punctuation to a separator
F-Zero GX	fzerogx	fzerogx	punctuation to a separator
Pikmin 2	pikmin2	pikmin2	punctuation to a separator
Teenage Mutant Ninja Turtles II: The Arcade Game	teenagemutantninjaturtles2arcadegame	teenagemutantninjaturtles2arcadegame	punctuation to a separator
Ghosts 'n Goblins	ghostsngoblins	ghostsngoblins	punctuation to a separator
Super Smash Bros. Melee	supersmashbrosmelee	supersmashbrosmelee	punctuation to a separator
Dr. Mario	drmario	drmario	punctuation to a separator
Mr. Driller	mrdriller	mrdriller	punctuation to a separator
Mega Man X	megaman10	megaman10	punctuation to a separator
Wipeout 2097	wipeout2097	wipeout2097	punctuation to a separator
ファイナルファンタジー			non-Latin script
ドラゴンクエスト			non-Latin script
ゼルダの伝説			non-Latin script
スーパーマリオブラザーズ			non-Latin script
ポケットモンスター 赤			non-Latin script
ゼルダの伝説 夢をみる島DX	dx	dx	non-Latin script
ロックマン2	2	2	non-Latin script
星のカービィ			non-Latin script
メトロイド			non-Latin script
ファミコン探偵倶楽部			non-Latin script
信長の野望			non-Latin script
三国志			non-Latin script
大航海時代II	2	2	non-Latin script
魔界村			non-Latin script
ストリートファイターII	2	2	non-Latin script
Metroid Dread	metroiddread	metroiddread	plain title
Hollow Knight	hollowknight	hollowknight	plain title
Celeste	celeste	celeste	plain title
Cuphead	cuphead	cuphead	plain title
Hades	hades	hades	plain title
Stardew Valley	stardewvalley	stardewvalley	plain title
Undertale	undertale	undertale	plain title
Shovel Knight	shovelknight	shovelknight	plain title
Fez	fez	fez	plain title
Braid	braid	braid	plain title
Limbo	limbo	limbo	plain title
Inside	inside	inside	plain title
Journey	journey	journey	plain title
Flower	flower	flower	plain title
Katamari Damacy	katamaridamacy	katamaridamacy	plain title
Rez	rez	rez	plain title
Gitaroo Man	gitarooman	gitarooman	plain title
PaRappa the Rapper	parapparapper	parapparapper	plain title
Vib-Ribbon	vibribbon	vibribbon	plain title
Bloodborne	bloodborne	bloodborne	plain title
Sekiro: Shadows Die Twice	sekiroshadowsdietwice	sekiroshadowsdietwice	plain title
Dark Souls	darksouls	darksouls	plain title
Elden Ring	eldenring	eldenring	plain title
Monster Hunter Rise	monsterhunterrise	monsterhunterrise	plain title
Splatoon 2	splatoon2	splatoon2	plain title
Bayonetta 2	bayonetta2	bayonetta2	plain title
Astral Chain	astralchain	astralchain	plain title
Pikmin 4	pikmin4	pikmin4	plain title
Super Metroid	supermetroid	supermetroid	plain title
Terranigma	terranigma	terranigma	plain title
Illusion of Gaia	illusionofgaia	illusionofgaia	plain title
Soul Blazer	soulblazer	soulblazer	plain title
Ogre Battle 64: Person of Lordly Caliber	ogrebattle64personoflordlycaliber	ogrebattle64personoflordlycaliber	plain title
Tactics Ogre: Let Us Cling Together	tacticsogreletusclingtogether	tacticsogreletusclingtogether	plain title
Vagrant Story	vagrantstory	vagrantstory	plain title
Silent Hill 2	silenthill2	silenthill2	plain title
Fatal Frame	fatalframe	fatalframe	plain title
Devil May Cry 3: Dante's Awakening	devilmaycry3dantesawakening	devilmaycry3dantesawakening	plain title
God of War	godofwar	godofwar	plain title
Sly 2: Band of Thieves	sly2bandofthieves	sly2bandofthieves	plain title
Ratchet & Clank: Going Commando	ratchetandclankgoingcommando	ratchetandclankgoingcommando	plain title
Beyond Good & Evil	beyondgoodandevil	beyondgoodandevil	plain title
Psychonauts	psychonauts	psychonauts	plain title
Grim Fandango	grimfandango	grimfandango	plain title
Day of the Tentacle	dayoftentacle	dayoftentacle	plain title
Monkey Island 2: LeChuck's Revenge	monkeyisland2lechucksrevenge	monkeyisland2lechucksrevenge	plain title
Full Throttle	fullthrottle	fullthrottle	plain title
Myst	myst	myst	plain title
Riven	riven	riven	plain title
Doom	doom	doom	plain title
Quake	quake	quake	plain title
Wolfenstein 3D	wolfenstein3d	wolfenstein	plain title
Duke Nukem 3D	dukenukem3d	dukenukem	plain title
Super Mario 3D World	supermario3dworld	supermario3dworld	plain title
Sonic 3D Blast	sonic3dblast	sonic3dblast	plain title
Castlevania 64	castlevania64	castlevania64	plain title
Mischief Makers	mischiefmakers	mischiefmakers	plain title
Blast Corps	blastcorps	blastcorps	plain title
Jet Force Gemini	jetforcegemini	jetforcegemini	plain title
Diddy Kong Racing	diddykongracing	diddykongracing	plain title
Wild Arms 2	wildarms2	wildarms2	plain title
Pac-Man World 2	pacmanworld2	pacmanworld2	plain title
Bust-A-Move	bustmove	bustmove	plain title
Banjo-Tooie	banjotooie	banjotooie	plain title
Jet Set Radio	jetsetradio	jetsetradio	plain title
Contra (USA)	contrausa	contrausa	region tag
Castlevania (Europe)	castlevaniaeurope	castlevaniaeurope	region tag
Metroid (Japan)	metroidjapan	metroidjapan	region tag
Tetris (World)	tetrisworld	tetrisworld	region tag
Kirby's Adventure (USA, Europe)	kirbysadventureusaeurope	kirbysadventureusaeurope	region tag
Super Metroid (Japan, USA)	supermetroidjapanusa	supermetroidjapanusa	region tag
Chrono Trigger (USA)	chronotriggerusa	chronotriggerusa	region tag
EarthBound (USA)	earthboundusa	earthboundusa	region tag
Golden Sun (Europe) (En,Fr,De)	goldensuneuropeenfrde	goldensuneuropeenfrde	region tag
Advance Wars (USA)	advancewarsusa	advancewarsusa	region tag
Pokemon Gold Version (USA, Europe)	pokemongoldversionusaeurope	pokemongoldversionusaeurope	region tag
Gunstar Heroes (Japan)	gunstarheroesjapan	gunstarheroesjapan	region tag
Streets of Rage 2 (World)	streetsofrage2world	streetsofrage2world	region tag
Phantasy Star (Brazil)	phantasystarbrazil	phantasystarbrazil	region tag
Alex Kidd in Miracle World (Korea)	alexkiddinmiracleworldkorea	alexkiddinmiracleworldkorea	region tag
Final Fantasy VI (Japan)	finalfantasy6japan	finalfantasy6japan	region tag
Mother 3 (Japan)	mother3japan	mother3japan	region tag
Fire Emblem (USA, Australia)	fireemblemusaaustralia	fireemblemusaaustralia	region tag
Star Fox 64 (Europe)	starfox64europe	starfox64europe	region tag
GoldenEye 007 (Europe)	goldeneye007europe	goldeneye007europe	region tag
Super Mario World (USA)	supermarioworldusa	supermarioworldusa	region tag
Sonic the Hedgehog (USA, Europe)	sonichedgehogusaeurope	sonichedgehogusaeurope	region tag
Mega Man X (USA)	megaman10usa	megaman10usa	region tag
Donkey Kong Country (Europe) (Rev 1)	donkeykongcountryeuroperev1	donkeykongcountryeuroperev1	region tag
Kid Icarus (USA, Europe)	kidicarususaeurope	kidicarususaeurope	region tag
Ninja Gaiden (USA)	ninjagaidenusa	ninjagaidenusa	region tag
Final Fantasy Tactics Advance (Europe) (En,Fr,De,Es,It)	finalfantasytacticsadvanceeuropeenfrdeesit	finalfantasytacticsadvanceeuropeenfrdeesit	region tag
Mario Kart DS (Japan)	mariokartdsjapan	mariokartdsjapan	region tag
Animal Crossing (USA)	animalcrossingusa	animalcrossingusa	region tag
Metroid Prime (Europe)	metroidprimeeurope	metroidprimeeurope	region tag
Super Mario Bros. 3 (USA) (Rev 1)	supermariobros3usarev1	supermariobros3usarev1	revision tag
The Legend of Zelda (USA) (Rev 1)	legendofzeldausarev1	legendofzeldausarev1	revision tag
Pokemon Red Version (USA, Europe) (SGB Enhanced)	pokemonredversionusaeuropesgbenhanced	pokemonredversionusaeuropesgbenhanced	revision tag
Super Mario World (USA) (Rev 1)	supermarioworldusarev1	supermarioworldusarev1	revision tag
Street Fighter II Turbo (USA) (Rev 1)	streetfighter2turbousarev1	streetfighter2turbousarev1	revision tag
Sonic the Hedgehog 2 (World) (Rev A)	sonichedgehog2worldrev	sonichedgehog2worldrev	revision tag
Final Fantasy III (USA) (Rev 1)	finalfantasy3usarev1	finalfantasy3usarev1	revision tag
Contra III: The Alien Wars (USA) (Rev 1)	contra3alienwarsusarev1	contra3alienwarsusarev1	revision tag
Kirby Super Star (USA) (v1.1)	kirbysuperstarusav11	kirbysuperstarusav11	revision tag
Tetris (World) (Rev 1)	tetrisworldrev1	tetrisworldrev1	revision tag
F-Zero (USA) (Rev 1)	fzerousarev1	fzerousarev1	revision tag
Metroid Fusion (USA) (Rev 1)	metroidfusionusarev1	metroidfusionusarev1	revision tag
Golden Sun (USA) (v1.1)	goldensunusav11	goldensunusav11	revision tag
Mario Kart 64 (USA) (Rev 1)	mariokart64usarev1	mariokart64usarev1	revision tag
Super Mario 64 (Japan) (Rev 3)	supermario64japanrev3	supermario64japanrev3	revision tag
Perfect Dark (USA) (Rev 1)	perfectdarkusarev1	perfectdarkusarev1	revision tag
Pokemon Crystal Version (USA, Europe) (Rev 1)	pokemoncrystalversionusaeuroperev1	pokemoncrystalversionusaeuroperev1	revision tag
Wario Land 4 (USA, Europe) (v1.1)	warioland4usaeuropev11	warioland4usaeuropev11	revision tag
Mega Man 2 (USA) (Rev 1)	megaman2usarev1	megaman2usarev1	revision tag
Castlevania (USA) (Rev 1)	castlevaniausarev1	castlevaniausarev1	revision tag
Final Fantasy VII (USA) (Disc 1)	finalfantasy7usadisc1	finalfantasy7usadisc1	disc tag
Final Fantasy VII (USA) (Disc 2)	finalfantasy7usadisc2	finalfantasy7usadisc2	disc tag
Final Fantasy VII (USA) (Disc 3)	finalfantasy7usadisc3	finalfantasy7usadisc3	disc tag
Metal Gear Solid (USA) (Disc 1)	metalgearsolidusadisc1	metalgearsolidusadisc1	disc tag
Metal Gear Solid (USA) (Disc 2)	metalgearsolidusadisc2	metalgearsolidusadisc2	disc tag
Final Fantasy VIII (Europe) (Disc 1)	finalfantasy8europedisc1	finalfantasy8europedisc1	disc tag
Final Fantasy IX (USA) (Disc 4)	finalfantasy9usadisc4	finalfantasy9usadisc4	disc tag
Xenogears (USA) (Disc 1)	xenogearsusadisc1	xenogearsusadisc1	disc tag
Chrono Cross (USA) (Disc 2)	chronocrossusadisc2	chronocrossusadisc2	disc tag
Legend of Dragoon, The (USA) (Disc 1)	legendofdragoonusadisc1	legendofdragoonusadisc1	disc tag
Resident Evil 2 (USA) (Disc 1)	residentevil2usadisc1	residentevil2usadisc1	disc tag
Parasite Eve (USA) (Disc 2)	parasiteeveusadisc2	parasiteeveusadisc2	disc tag
Lunar: Silver Star Story Complete (USA) (Disc 1)	lunarsilverstarstorycompleteusadisc1	lunarsilverstarstorycompleteusadisc1	disc tag
Star Ocean: The Second Story (USA) (Disc 1)	staroceansecondstoryusadisc1	staroceansecondstoryusadisc1	disc tag
Valkyrie Profile (USA) (Disc 2)	valkyrieprofileusadisc2	valkyrieprofileusadisc2	disc tag
Grandia (USA) (Disc 1)	grandiausadisc1	grandiausadisc1	disc tag
Shenmue (Europe) (Disc 1)	shenmueeuropedisc1	shenmueeuropedisc1	disc tag
Skies of Arcadia (USA) (Disc 1)	skiesofarcadiausadisc1	skiesofarcadiausadisc1	disc tag
Panzer Dragoon Saga (USA) (Disc 4)	panzerdragoonsagausadisc4	panzerdragoonsagausadisc4	disc tag
Xenosaga Episode I: Der Wille zur Macht (USA) (Disc 2)	xenosagaepisodeiderwillezurmachtusadisc2	xenosagaepisodeiderwillezurmachtusadisc2	disc tag
Legend of Zelda, The - A Link to the Past (USA)	legendofzeldalinktopastusa	legendofzeldalinktopastusa	No-Intro article suffix
Legend of Zelda, The - Ocarina of Time (USA)	legendofzeldaocarinaoftimeusa	legendofzeldaocarinaoftimeusa	No-Intro article suffix
Simpsons, The - Bart vs. the Space Mutants (USA)	simpsonsbartvsspacemutantsusa	simpsonsbartvsspacemutantsusa	No-Intro article suffix
Adventures of Lolo (USA)	adventuresoflolousa	adventuresoflolousa	No-Intro article suffix
Lost Vikings, The (USA)	lostvikingsusa	lostvikingsusa	No-Intro article suffix
Legend of Zelda, The - Link's Awakening DX (USA, Europe)	legendofzeldalinksawakeningdxusaeurope	legendofzeldalinksawakeningdxusaeurope	No-Intro article suffix
Legend of Zelda, The - Majora's Mask (Europe) (En,Fr,De,Es)	legendofzeldamajorasmaskeuropeenfrdees	legendofzeldamajorasmaskeuropeenfrdees	No-Intro article suffix
Ninja Warriors, The (Japan)	ninjawarriorsjapan	ninjawarriorsjapan	No-Intro article suffix
Secret of Mana (USA)	secretofmanausa	secretofmanausa	No-Intro article suffix
Legend of Dragoon, The (USA) (Disc 4)	legendofdragoonusadisc4	legendofdragoonusadisc4	No-Intro article suffix
Okami	okami	okami	same game, different release form
Tomb Raider	tombraider	tombraider	same game, different release form
Kirby's Return to Dream Land	kirbysreturntodreamland	kirbysreturntodreamland	same game, different release form
Resident Evil	residentevil	residentevil	same game, different release form
Grandia	grandia	grandia	same game, different release form
Diablo III	diablo3	diablo3	same game, different release form
The Legend of Zelda: Majora's Mask	legendofzeldamajorasmask	legendofzeldamajorasmask	same game, different release form
Donkey Kong Country Returns	donkeykongcountryreturns	donkeykongcountryreturns	same game, different release form
Tetris	tetris	tetris	same game, different release form
Ocarina of Time	ocarinaoftime	ocarinaoftime	same game, different release form
Persona 4	persona4	persona4	same game, different release form
Wario Land II	warioland2	warioland2	same game, different release form
Nier Replicant	nierreplicant	nierreplicant	same game, different release form
Metroid	metroid	metroid	sequel that must not meet its original
Super Mario Bros.	supermariobros	supermariobros	sequel that must not meet its original
Mario Kart 64	mariokart64	mariokart64	sequel that must not meet its original
Mario Kart DS	mariokartds	mariokartds	sequel that must not meet its original
Final Fantasy	finalfantasy	finalfantasy	sequel that must not meet its original
Dragon Quest	dragonquest	dragonquest	sequel that must not meet its original
Castlevania	castlevania	castlevania	sequel that must not meet its original
Mega Man	megaman	megaman	sequel that must not meet its original
Street Fighter	streetfighter	streetfighter	sequel that must not meet its original
Kingdom Hearts	kingdomhearts	kingdomhearts	sequel that must not meet its original
Earthworm Jim	earthwormjim	earthwormjim	sequel that must not meet its original
Earthworm Jim 2	earthwormjim2	earthwormjim2	sequel that must not meet its original
Earthworm Jim 3D	earthwormjim3d	earthwormjim	sequel that must not meet its original
Halo 2	halo2	halo2	sequel that must not meet its original
Halo 3	halo3	halo3	sequel that must not meet its original
Pikmin	pikmin	pikmin	sequel that must not meet its original
Pikmin 3	pikmin3	pikmin3	sequel that must not meet its original
Golden Sun	goldensun	goldensun	sequel that must not meet its original
Persona 4 Arena	persona4arena	persona4arena	sequel that must not meet its original
Persona 3	persona3	persona3	sequel that must not meet its original
"""


def rows() -> list[TitleRow]:
    """The corpus, parsed."""
    out: list[TitleRow] = []
    for line in ROWS.strip("\n").splitlines():
        title, strict, loose, pins = line.split("\t")
        out.append(TitleRow(title, strict, loose, pins))
    return out
