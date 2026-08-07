"""Swahili and French skeleton courses — course + A1 level + one unit + one
lesson + a few items, so the UI can list all three languages."""
from __future__ import annotations

from sauti.seed.data_kin import item

COURSE_SWA = {
    "code": "SWA",
    "name": "Kiswahili",
    "levels": [
        {
            "cefr": "A1",
            "title": "Breakthrough",
            "ord": 1,
            "candos": [
                ("speak", "Can greet and respond to greetings at any time of day"),
                ("speak", "Can say their name and ask someone else's"),
            ],
            "units": [
                {
                    "title": "Greetings",
                    "situation_tag": "greetings",
                    "ord": 1,
                    "lessons": [
                        {
                            "title": "Jambo! First greetings",
                            "grammar_md": """## First Swahili greetings

**Hujambo?** (“are you well?” — to one person) is answered **Sijambo** (“I am
well”). To several people: **Hamjambo?** → **Hatujambo**.

The all-purpose opener is **Habari** (“news”): *Habari ya asubuhi?* (“how is
the morning?”), *Habari yako?* (“how are you?”). Reply with **Nzuri** (“good”),
often softened to *Nzuri sana* — “very good”.

Thanks is **asante** (*asante sana* — thank you very much).""",
                            "culture_note": "Utamaduni: Swahili greetings unfold in rounds — "
                            "answer one Habari and another follows. Rushing them is rude on "
                            "the whole Swahili coast, as in Rwanda.",
                            "items": [
                                item("Hujambo?", "How are you? (to one person)", ["greetings"], {2: "R"}),
                                item("Sijambo, asante.", "I am well, thank you.", ["greetings"]),
                                item("Habari ya asubuhi?", "How is the morning?", ["greetings"], {6: "R"}),
                                item("Nzuri sana.", "Very good.", ["greetings"]),
                                item("Jina lako nani?", "What is your name?", ["greetings"], {5: "R"}),
                            ],
                        }
                    ],
                }
            ],
        }
    ],
}

COURSE_FRA = {
    "code": "FRA",
    "name": "Français",
    "levels": [
        {
            "cefr": "A1",
            "title": "Découverte",
            "ord": 1,
            "candos": [
                ("speak", "Can greet, take leave and thank someone"),
                ("speak", "Can introduce themselves with name and origin"),
            ],
            "units": [
                {
                    "title": "Salutations",
                    "situation_tag": "greetings",
                    "ord": 1,
                    "lessons": [
                        {
                            "title": "Bonjour ! — premières salutations",
                            "grammar_md": """## Premières salutations

**Bonjour** covers morning and afternoon; from the evening on, switch to
**bonsoir**. Among friends, **salut** works for both hello and bye.

Asking how someone is: formal **Comment allez-vous ?** / informal **Ça va ?** —
answered *Ça va bien, merci*.

Introduce yourself with **je m'appelle…** (“I call myself…”): *Je m'appelle
Claire.* Ask back with *Et vous ?* (formal) or *Et toi ?* (informal) — French
keeps a two-level politeness system (tu/vous), much as Kinyarwanda uses the
plural for respect.""",
                            "culture_note": "Culture : in Rwanda French is a school and "
                            "office language — greetings often mix: “Bonjour, amakuru?” "
                            "is perfectly normal Kigali speech.",
                            "items": [
                                item("Bonjour !", "Good morning! / Hello!", ["greetings"]),
                                item("Comment ça va ?", "How are you?", ["greetings"], {3: "R"}),
                                item("Ça va bien, merci.", "I'm fine, thank you.", ["greetings"]),
                                item("Je m'appelle Claire.", "My name is Claire.", ["greetings"]),
                                item("Au revoir !", "Goodbye!", ["greetings"]),
                            ],
                        }
                    ],
                }
            ],
        }
    ],
}
