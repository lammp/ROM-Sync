"""The file-name corpus: names a scan meets, and the system each sits in.

Version 1's `clean_title` and `region_of` turn each into a title and a region;
`tools/goldens.py` runs them from the tag and writes their answers to
`tests/golden/data/file_titles.py`. Every title is a published game title or
an invented one; no name comes from anyone's library.

One row per line: system, a tab, the name.
"""

from __future__ import annotations

NAMES = r"""
nes	Legend of Zelda, The (USA).nes
nes	Legend of Zelda, The - A Link to the Past (USA).zip
snes	Super Mario World (USA).sfc
snes	Secret of Mana (Europe) (En,Fr,De).sfc
snes	Chrono Trigger (USA) (Rev 1).sfc
snes	Donkey Kong Country 2 - Diddy's Kong Quest (USA) (Rev 1).sfc
gba	Pokemon - Emerald Version (USA, Europe).gba
gba	Golden Sun - The Lost Age (USA).gba
gb	Tetris (World) (Rev A).gb
psx	Final Fantasy VII (USA) (Disc 1).chd
psx	Moon Saga (Europe)
psx	Final Fantasy IX (USA)
psx	Castlevania - Symphony of the Night (USA).chd
psp	Hover Racer (Europe).iso
psp	Patapon (USA) [Demo].iso
n3ds	Legend of Zelda, The - Majora's Mask 3D (Europe).3ds
md	Sonic the Hedgehog (USA, Europe).md
md	Story of Thor, The (Europe).md
md	Adventures of Batman & Robin, The (USA).md
ps2	Okami (USA).iso
ps2	Grand Theft Auto - San Andreas (USA) (v1.03).iso
n64	Legend of Zelda, The - Ocarina of Time (USA) (Rev 2).z64
n64	Mario Kart 64 (USA).z64
dreamcast	Crazy Taxi (USA).chd
saturn	Panzer Dragoon Saga (USA) (Disc 1).chd
nds	New Super Mario Bros. (USA).nds
nds	Professor Layton and the Curious Village (Europe) (En,Fr,De,Es,It).nds
switch	Hollow Knight [0100633007D48000][v0].nsp
switch	Celeste.xci
wii	Punch-Out!! (USA).rvz
gc	Legend of Zelda, The - The Wind Waker (USA).rvz
nes	Mega Man 2 (USA).nes
nes	Ninja Gaiden II - The Dark Sword of Chaos (USA).nes
snes	Street Fighter II Turbo (USA) (Rev 1).sfc
arcade	sf2.zip
arcade	mslug.zip
arcade	unknownset.zip
fbneo	kof98.zip
fbneo	garou.zip
mame	pacman.zip
neogeo	neogeo.zip
cps2	ssf2t.zip
nes	Star Quest (Europe).zip
nes	Blank Cart (World).nes
snes	Le Mans 24 (Europe).sfc
md	Die Hard Trilogy (Europe).md
psx	Das Boot (Germany).chd
psx	Los Angeles Racer (USA).chd
psx	Les Miserables (France).chd
snes	El Viento (USA).sfc
gba	Mario & Luigi - Superstar Saga (USA).gba
nes	A Boy and His Blob - Trouble on Blobolonia (USA).nes
nes	Boy and His Blob, A - Trouble on Blobolonia (USA).nes
snes	Art of Fighting, An (USA).sfc
psp	Dragon Quest XI S - Echoes of an Elusive Age - Definitive Edition (Japan).iso
pc	No Extension Folder Game
pc	Two.Dots.In.Name (USA).zip
gba	   Spaced   Out   Title   (USA).gba
nes	Bracket [Only].nes
nes	Tags (USA) Then More (Europe).nes
nes	(Leading Tag) Game (USA).nes
"""
