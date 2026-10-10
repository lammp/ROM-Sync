"""The twin corpus.

One row per pair of games on two systems: each title and system, how version
1 relates them (`exact`, `loose` or `none`), and the property the row pins.
Every title is a published game title. The relation is version 1's, captured
by `ui/parity/pairs` running version 1's own `buildTwins` from the tag, and
`pairs.capture.test.ts` proves it still is.

Tab separated.
"""

from __future__ import annotations

from typing import NamedTuple


class PairRow(NamedTuple):
    a_title: str
    a_system: str
    b_title: str
    b_system: str
    relation: str
    pins: str


ROWS = r"""
Tetris	gb	Tetris	nes	exact	same title, two systems
Street Fighter II	snes	Street Fighter II	md	exact	same title, two systems
Mega Man 2	nes	Mega Man II	gb	exact	roman numeral meets digit
Ratchet & Clank	ps2	Ratchet and Clank	psp	exact	ampersand meets and
Yoshi's Island	snes	Yoshis Island	gba	exact	apostrophe dropped
Pac-Man	arcade	Pac-Man	nes	exact	same title, two systems
Galaga	arcade	Galaga	nes	exact	same title, two systems
Donkey Kong	arcade	Donkey Kong	nes	exact	same title, two systems
Ms. Pac-Man	arcade	Ms. Pac-Man	md	exact	punctuation folded
Final Fantasy VI	snes	Final Fantasy VI	gba	exact	same title, two systems
Final Fantasy IV	snes	Final Fantasy IV	nds	exact	same title, two systems
Chrono Trigger	snes	Chrono Trigger	nds	exact	same title, two systems
Castlevania: Symphony of the Night	psx	Castlevania: Symphony of the Night	xbox360	exact	same title, two systems
Resident Evil 4	gc	Resident Evil 4	ps2	exact	same title, two systems
Okami	ps2	Okami	wii	exact	same title, two systems
Sonic the Hedgehog	md	Sonic the Hedgehog	sms	exact	same title, different games
Prince of Persia: The Sands of Time	ps2	Prince of Persia: The Sands of Time	gc	exact	same title, two systems
Beyond Good & Evil	ps2	Beyond Good and Evil	gc	exact	ampersand meets and
Tony Hawk's Pro Skater	psx	Tony Hawk's Pro Skater	n64	exact	same title, two systems
Super Mario Bros. 3	nes	Super Mario Bros. 3	snes	exact	same title, two systems
Metal Gear Solid	psx	Metal Gear Solid	pc	exact	same title, two systems
Doom	pc	Doom	snes	exact	same title, two systems
Wolfenstein 3D	pc	Wolfenstein 3D	snes	exact	same title, two systems
Mortal Kombat II	snes	Mortal Kombat II	md	exact	same title, two systems
NBA Jam	snes	NBA Jam	md	exact	same title, two systems
Aladdin	snes	Aladdin	md	exact	same title, different games
The Lion King	snes	The Lion King	md	exact	leading article dropped
Earthworm Jim	snes	Earthworm Jim	md	exact	same title, two systems
Rayman	psx	Rayman	saturn	exact	same title, two systems
Bomberman	nes	Bomberman	pce	exact	same title, two systems
Lemmings	snes	Lemmings	md	exact	same title, two systems
Persona 4 Golden	psvita	Persona 4 Golden	pc	exact	same title, two systems
Bayonetta	ps3	Bayonetta	xbox360	exact	same title, two systems
Ys I & II	pce	Ys I and II	pc	exact	ampersand meets and
Ghosts 'n Goblins	arcade	Ghosts 'n Goblins	nes	exact	apostrophe dropped
Dr. Mario	nes	Dr. Mario	gb	exact	punctuation folded
Q*bert	arcade	Q*bert	nes	exact	punctuation folded
Final Fantasy VII	psx	Final Fantasy VII	pc	exact	same title, two systems
SimCity	snes	SimCity	pc	exact	same title, two systems
Paper Mario	n64	Paper Mario	wii	exact	same title, two systems
Super Metroid	snes	Super Metroid	n3ds	exact	same title, two systems
Punch-Out!!	nes	Punch-Out!!	wii	exact	same title, different games
Street Fighter II: The World Warrior	arcade	Street Fighter II: The World Warrior	snes	exact	subtitle kept on both
The Legend of Zelda	nes	Legend of Zelda	gba	exact	leading article dropped
Okami	ps2	Okami HD	ps3	loose	release form stripped, so loose
The Legend of Zelda: Majora's Mask	n64	The Legend of Zelda: Majora's Mask 3D	n3ds	loose	release form stripped, so loose
Donkey Kong Country Returns	wii	Donkey Kong Country Returns 3D	n3ds	loose	release form stripped, so loose
Link's Awakening	gb	Link's Awakening DX	gbc	loose	release form stripped, so loose
Tetris	gb	Tetris DX	gbc	loose	release form stripped, so loose
Resident Evil	gc	Resident Evil HD Remaster	ps3	loose	two release forms stripped, so loose
Tomb Raider	psx	Tomb Raider: Anniversary	ps2	loose	release form stripped, so loose
Mario Kart 8	wiiu	Mario Kart 8 Deluxe	switch	loose	release form stripped, so loose
Kirby's Return to Dream Land	wii	Kirby's Return to Dream Land Deluxe	switch	loose	release form stripped, so loose
Star Fox 64	n64	Star Fox 64 3D	n3ds	loose	release form stripped, so loose
The Legend of Zelda: Ocarina of Time	n64	The Legend of Zelda: Ocarina of Time 3D	n3ds	loose	release form stripped, so loose
Luigi's Mansion	gc	Luigi's Mansion 3D	n3ds	loose	release form stripped, so loose
Grandia	saturn	Grandia HD Remaster	switch	loose	two release forms stripped, so loose
Halo: Combat Evolved	xbox	Halo: Combat Evolved Anniversary	xbox360	loose	release form stripped, so loose
Wolfenstein 3D	pc	Wolfenstein	ps3	loose	a different game, offered only as loose
Earthworm Jim	snes	Earthworm Jim 3D	n64	loose	a different game, offered only as loose
Duke Nukem 3D	pc	Duke Nukem	nes	loose	a different game, offered only as loose
Metroid	nes	Metroid II: Return of Samus	gb	none	sequel
Super Mario Bros.	nes	Super Mario Bros. 3	gba	none	sequel
Mario Kart 64	n64	Mario Kart DS	nds	none	same series, different game
Halo 2	xbox	Halo 3	xbox360	none	sequel
Pikmin	gc	Pikmin 3	wiiu	none	sequel
Persona 3	ps2	Persona 4	psx	none	sequel
Kingdom Hearts	ps2	Kingdom Hearts II	ps3	none	sequel
Earthworm Jim	snes	Earthworm Jim 2	md	none	sequel
Street Fighter II	snes	Street Fighter III: 3rd Strike	dc	none	sequel
Dragon Quest XI: Echoes of an Elusive Age	ps4	Dragon Quest XI S: Echoes of an Elusive Age - Definitive Edition	switch	none	an extra letter keeps a re-release apart
Final Fantasy X	ps2	Final Fantasy X/X-2 HD Remaster	ps3	none	a bundle keeps its own name
Mega Man	nes	Mega Man X	snes	none	same series, different game
Metroid	nes	Metroid: Zero Mission	gba	none	a remake under a new name
The Legend of Zelda: A Link to the Past	snes	The Legend of Zelda: Link's Awakening	gb	none	same series, different game
Mario & Luigi: Superstar Saga	gba	Mario & Luigi: Bowser's Inside Story	nds	none	same series, different game
Pokemon Gold	gbc	Pokemon Silver	gb	none	same series, different game
Tetris	gb	Tetris	gb	none	same title, same system
Final Fantasy	nes	Final Fantasy II	nes	none	sequel on the same system
Super Mario Bros.	nes	Super Mario Bros.	nes	none	same title, same system
ゼルダの伝説	fds	メトロイド	fds	none	no Latin key
ゼルダの伝説	fds	ゼルダの伝説	n64	none	no Latin key, so no twin even when equal
Castlevania	nes	Castlevania: Aria of Sorrow	gba	none	same series, different game
Sonic the Hedgehog	md	Sonic the Hedgehog 2	md	none	sequel on the same system
Sonic the Hedgehog	md	Sonic Adventure	dc	none	same series, different game
Resident Evil	psx	Resident Evil 2	psx	none	sequel on the same system
Resident Evil 4	gc	Resident Evil 5	ps3	none	sequel
Zelda II: The Adventure of Link	nes	The Legend of Zelda	gba	none	sequel
Final Fantasy XI	pc	Final Fantasy 11	ps2	none	a numeral past ten is not folded
Ico	ps2	Ice Climber	nes	none	near spelling
Super Mario 64	n64	Super Mario 64 DS	nds	none	a platform suffix is not a release form
Star Fox	snes	Star Fox 64	n64	none	a number keeps them apart
Diablo III	pc	Diablo III: Reaper of Souls - Ultimate Evil Edition	ps4	none	a subtitle keeps them apart
Ratchet & Clank	ps2	Ratchet & Clank: Going Commando	ps3	none	sequel with a subtitle
Luigi's Mansion	gc	Luigi's Mansion 3	switch	none	a number is not a release form
Okami	ps2	Okamiden	nds	none	a longer word is a different word
Doom	pc	Doom II	n64	none	sequel
Wolfenstein 3D	pc	Return to Castle Wolfenstein	pc	none	same series, different game
Persona 4 Golden	psvita	Persona 4 Arena	ps3	none	same series, different game
Pac-Man	arcade	Ms. Pac-Man	arcade	none	same series, different game
Galaga	arcade	Galaxian	arcade	none	near name
Earthworm Jim 3D	n64	Earthworm Jim 2	snes	none	a release form and a sequel
"""


def rows() -> list[PairRow]:
    """The corpus, parsed."""
    out: list[PairRow] = []
    for line in ROWS.strip("\n").splitlines():
        a_title, a_system, b_title, b_system, relation, pins = line.split("\t")
        out.append(PairRow(a_title, a_system, b_title, b_system, relation, pins))
    return out
