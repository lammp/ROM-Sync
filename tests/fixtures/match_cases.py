"""The matcher corpus: titles, the system's platform, and what each search returns.

Version 1's `scrape.match` runs over every case from the tag
(`tools/goldens.py`), and its pick and score are written to
`tests/golden/data/matches.py`. A case's `responses` maps one search, written
`text<TAB>platform` (`*` for anywhere), to the candidates it returns, in the
service's raw shape. A search with no entry returns nothing.

The cases are built, not listed: each title meets the same scenarios, so a
scenario's effect is visible across titles. Every candidate is invented.
"""

from __future__ import annotations

from typing import Any

TITLES: tuple[tuple[str, int], ...] = (
    ("Super Mario World", 19),
    ("The Legend of Zelda: A Link to the Past", 19),
    ("Final Fantasy VII", 7),
    ("Pokemon: Emerald Version", 24),
    ("Castlevania: Symphony of the Night", 7),
    ("Street Fighter II: The World Warrior", 52),
    ("Okami", 8),
    ("Metroid Prime", 21),
    ("Chrono Trigger", 19),
    ("Sonic the Hedgehog 2", 29),
    ("Golden Sun: The Lost Age", 24),
    ("Mega Man X", 19),
    ("Tetris", 33),
    ("Donkey Kong Country 2: Diddy's Kong Quest", 19),
    ("Kirby's Adventure", 18),
    ("F-Zero", 19),
    ("Star Fox 64", 4),
    ("Resident Evil 2", 7),
    ("Gran Turismo", 7),
    ("Panzer Dragoon Saga", 32),
)

OTHER = 999


def _cand(
    id_: int, name: str, platforms: list[int], alts: tuple[str, ...] = ()
) -> dict[str, Any]:
    raw: dict[str, Any] = {"id": id_, "name": name, "platforms": platforms}
    if alts:
        raw["alternative_names"] = [{"name": a} for a in alts]
    return raw


def _key(text: str, platform: int | None) -> str:
    return f"{text}\t{platform if platform else '*'}"


def _cases() -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    n = 1000
    for i, (title, plat) in enumerate(TITLES):
        head = title.split(":")[0].strip()
        base = n + i * 100

        def add(
            scenario: str,
            platform: int | None,
            responses: dict[str, list[Any]],
            title: str = title,
        ) -> None:
            cases.append(
                {
                    "name": f"{title} / {scenario}",
                    "title": title,
                    "platform": platform,
                    "responses": responses,
                }
            )

        add(
            "exact on the platform",
            plat,
            {
                _key(title, plat): [
                    _cand(base + 1, title, [plat]),
                    _cand(base + 2, title + " DX", [plat]),
                ],
                _key(title, None): [_cand(base + 3, title, [OTHER])],
            },
        )
        add(
            "near on the platform, exact elsewhere",
            plat,
            {
                _key(title, plat): [_cand(base + 4, title + ": Special Edition", [plat])],
                _key(title, None): [
                    _cand(base + 5, title, [OTHER]),
                    _cand(base + 6, title + " 3D", [OTHER]),
                ],
            },
        )
        add(
            "an alternative name",
            plat,
            {
                _key(title, plat): [
                    _cand(base + 7, "Translated Name", [plat], ("Other Name", title))
                ],
            },
        )
        add(
            "only off the platform",
            plat,
            {
                _key(title, plat): [_cand(base + 8, "Something Else Entirely", [plat])],
                _key(title, None): [_cand(base + 9, title, [OTHER, OTHER + 1])],
            },
        )
        add(
            "no platform known",
            None,
            {
                _key(title, None): [
                    _cand(base + 10, title.upper(), [plat]),
                    _cand(base + 11, head, [plat]),
                ],
            },
        )
        if head != title:
            add(
                "only the head finds it",
                plat,
                {
                    _key(head, plat): [
                        _cand(base + 12, head, [plat]),
                        _cand(base + 13, title, [plat]),
                    ],
                },
            )
        add(
            "nothing close",
            plat,
            {
                _key(title, plat): [_cand(base + 14, "Unrelated Puzzle Game", [plat])],
                _key(title, None): [_cand(base + 15, "Another Thing", [OTHER])],
            },
        )
        add(
            "punctuation and case",
            plat,
            {
                _key(title, plat): [
                    _cand(base + 16, title.lower().replace(" ", "-").replace(":", ""), [plat]),
                    _cand(base + 17, title.replace(":", " -"), [plat]),
                ],
            },
        )
    cases.append({"name": "an empty title", "title": "", "platform": 19, "responses": {}})
    cases.append({"name": "only quotes", "title": '""', "platform": 19, "responses": {}})
    cases.append(
        {
            "name": "a quote inside the title",
            "title": 'Say "Cheese"',
            "platform": 19,
            "responses": {_key("Say Cheese", 19): [_cand(9001, "Say Cheese", [19])]},
        }
    )
    cases.append(
        {
            "name": "the platform not on the candidate",
            "title": "Lonely Game",
            "platform": 19,
            "responses": {_key("Lonely Game", 19): [_cand(9002, "Lonely Game", [])]},
        }
    )
    return cases


CASES: list[dict[str, Any]] = _cases()
