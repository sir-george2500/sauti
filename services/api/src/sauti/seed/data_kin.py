"""Kinyarwanda course content — A1 and A2 fully seeded.

Structure: COURSE -> levels -> units -> lessons -> items.
Item syllables are auto-split (Kinyarwanda is strongly CV); tone hints are
sparse manual overrides (H = high / R = rise / F = fall) — orthography does not
mark tone, and flat tone is the #1 foreign tell.
"""
from __future__ import annotations

import re

_SYL = re.compile(r"[^aeiouAEIOU\W]*[aeiouAEIOU]+|[^aeiouAEIOU\W]+", re.UNICODE)


def syl(phrase: str, tones: dict[int, str] | None = None) -> dict:
    """Syllabify a (Kinyarwanda) phrase into CV chunks with tone hints.

    tones maps syllable index -> H/R/F (default L). Only the leading phrase up
    to a punctuation break is used — that is what the pronunciation screen drills.
    """
    head = re.split(r"[,.!?…]", phrase)[0]
    syllables: list[dict] = []
    for word in head.split():
        word = word.strip("'’\"“”")
        for part in word.replace("’", "'").split("'"):
            if not part:
                continue
            for chunk in _SYL.findall(part):
                syllables.append({"syl": chunk.lower(), "tone": "L"})
    for idx, tone in (tones or {}).items():
        if 0 <= idx < len(syllables):
            syllables[idx]["tone"] = tone
    return {"syllables": syllables}


def item(sentence: str, gloss: str, tags: list[str], tones: dict[int, str] | None = None) -> dict:
    return {"sentence": sentence, "gloss": gloss, "tags": tags, "phoneme_ref": syl(sentence, tones)}


def q(
    kind: str,
    question: str,
    correct: str,
    wrong: list[str],
    explain: str,
    item: str | None = None,
) -> dict:
    """One quiz question. kind: grammar | vocab | usage | culture.

    `item` is the sentence of a lesson item the question drills (resolved to an
    item_id at serialization time, so attempts feed that item's SRS state).
    Options are authored correct-first; the API shuffles them deterministically.
    """
    assert kind in ("grammar", "vocab", "usage", "culture"), kind
    assert len(wrong) == 3, f"need exactly 3 distractors: {question}"
    return {
        "kind": kind,
        "question": question,
        "options": [{"text": correct, "correct": True}]
        + [{"text": w, "correct": False} for w in wrong],
        "explanation": explain,
        "item": item,
    }


# ---------------------------------------------------------------------------
# A1 — Unit 1 · Greetings & people
# ---------------------------------------------------------------------------

A1_U1_L1 = {
    "title": "Greetings around the clock",
    "grammar_md": """## Greetings by time of day

Kinyarwanda greetings change with the clock, and almost all of them are built on
the **mu-** prefix — “you (plural)” — used even for one person as a mark of respect.

| Greeting | When | Literal sense |
|---|---|---|
| **Mwaramutse** | morning | “you (pl.) made it through the night” (from *kuramuka*) |
| **Mwiriwe** | afternoon / evening | “you (pl.) have spent the day” (from *kwirirwa*) |
| **Muraho** | any time, esp. after a long absence | “you are (still) there” (*-ho* = there) |
| **Ijoro ryiza** | parting at night | “good night” (*ijoro* = night, *ryiza* agrees with it) |
| **Murabeho** | goodbye (for a while) | “may you keep being there” |

To ONE close friend or a child you may drop to the singular: **Waramutse**,
**Wiriwe**, **Uraho**. When unsure, keep **mwa-/mu-** — the plural of respect is
never wrong.

**Urakoze** (“thank you”, to one person) becomes **Murakoze** to several people
or to an elder — the same singular/plural respect switch.""",
    "culture_note": "Umuco: the plural is respect. Addressing one elder with the plural "
    "mwa-/mu- forms (Mwaramutse, Murakoze) honours them; the singular to an elder "
    "sounds abrupt. Rwandans also greet with the right hand — often gripping their "
    "own right forearm with the left hand, a gesture that says “my hand is open and unarmed.”",
    "items": [
        item("Mwaramutse!", "Good morning!", ["greetings"]),
        item("Mwiriwe neza.", "Good afternoon.", ["greetings"]),
        item("Muraho!", "Hello!", ["greetings"], {2: "H"}),
        item("Ijoro ryiza.", "Good night.", ["greetings"]),
        item("Murabeho.", "Goodbye.", ["greetings"]),
        item("Urakoze cyane.", "Thank you very much.", ["greetings"], {2: "H"}),
        item("Murakaza neza!", "Welcome!", ["greetings"]),
    ],
    "quiz": [
        q(
            "usage",
            "It is 8 in the morning and you meet your neighbour. The natural greeting is…",
            "Mwaramutse!",
            ["Mwiriwe neza.", "Ijoro ryiza.", "Murabeho."],
            "Mwaramutse — “you made it through the night” — is the morning greeting; "
            "Mwiriwe belongs to the afternoon and evening.",
            item="Mwaramutse!",
        ),
        q(
            "grammar",
            "You want to thank ONE close friend. The right form is…",
            "Urakoze",
            ["Murakoze", "Mwaramutse", "Murabeho"],
            "Urakoze is the singular “thank you”; Murakoze is the plural — used for "
            "several people or as respect to an elder.",
            item="Urakoze cyane.",
        ),
        q(
            "grammar",
            "To one close friend in the morning you may drop to the singular:",
            "Waramutse",
            ["Mwaramutse", "Mwiriwe", "Muraho"],
            "The singular strips the mwa-/mu- plural prefix: Mwaramutse → Waramutse "
            "— but when unsure, the plural of respect is never wrong.",
        ),
        q(
            "vocab",
            "Which phrase means “Welcome!”?",
            "Murakaza neza!",
            ["Murabeho.", "Ijoro ryiza.", "Mwiriwe neza."],
            "Murakaza neza literally wishes that you arrive well — the greeting for "
            "someone reaching your home or town.",
            item="Murakaza neza!",
        ),
        q(
            "vocab",
            "“Ijoro ryiza” means…",
            "Good night.",
            ["Good morning.", "Goodbye.", "Thank you very much."],
            "Ijoro is “night” and ryiza (“good”) agrees with it — the parting phrase "
            "at the end of the evening.",
            item="Ijoro ryiza.",
        ),
        q(
            "culture",
            "Why do Rwandans greet one elder with plural forms like Mwaramutse?",
            "The plural is the mark of respect.",
            [
                "Elders are assumed to be accompanied.",
                "The singular forms are archaic.",
                "The plural is easier to pronounce.",
            ],
            "Addressing one elder with mwa-/mu- honours them; the singular to an "
            "elder sounds abrupt.",
        ),
    ],
}

A1_U1_L2 = {
    "title": "Amakuru? — asking how someone is",
    "grammar_md": """## Amakuru — “the news”

**Amakuru** literally means “news” (noun class 6, the *ama-* class). Asking
*Amakuru?* is asking “(what is) the news?” — the everyday “how are you?”.

| Phrase | Meaning |
|---|---|
| **Amakuru?** | How are you? |
| **Amakuru yawe?** | How are YOU? (*yawe* = “your”, agreeing with *ama-*) |
| **Ni meza.** | (The news) is good. — *meza* agrees with class 6 |
| **Umeze ute?** | How are you doing? (*kumera* = to be/feel) |
| **Meze neza.** | I'm doing well. |
| **Bite se?** | What's up? (informal, among friends) |
| **Ni byiza.** | All good. (informal reply) |

Notice the **agreement**: *amakuru* is in the **ma-** class, so “good” is
**meza** (ma- + -iza), and “your” is **yawe**. Adjectives and possessives in
Kinyarwanda always take a prefix that matches the noun's class — you will meet
this again with every noun class.

A rise in pitch on the final syllable is what makes *Amakuru?* a question —
there is no word for “?”.""",
    "culture_note": "Umuco: Amakuru? is not small talk to rush past. The full exchange — "
    "news of family, health, the harvest — matters, especially in rural Rwanda. "
    "Answering just “ni meza” and walking on can read as cold with elders.",
    "items": [
        item("Amakuru?", "How are you? (What's the news?)", ["greetings"], {2: "H", 3: "R"}),
        item("Amakuru yawe?", "How are you? (Your news?)", ["greetings"], {2: "H"}),
        item("Ni meza, urakoze.", "It's good, thank you.", ["greetings"]),
        item("Umeze ute?", "How are you doing?", ["greetings"], {3: "R"}),
        item("Meze neza.", "I'm doing well.", ["greetings"]),
        item("Bite se?", "What's up? (informal)", ["greetings"], {1: "R"}),
        item("Ni byiza.", "All good.", ["greetings"]),
    ],
    "quiz": [
        q(
            "usage",
            "A colleague asks “Amakuru?”. The natural reply is…",
            "Ni meza, urakoze.",
            ["Murakaza neza!", "Ni angahe?", "Ijoro ryiza."],
            "Amakuru (“the news”) takes the class-6 reply ni meza — “(the news) is "
            "good” — usually rounded off with thanks.",
            item="Ni meza, urakoze.",
        ),
        q(
            "grammar",
            "Amakuru is class 6 (ama-). Which agreement is correct?",
            "Amakuru ni meza.",
            ["Amakuru ni byiza.", "Amakuru ni nziza.", "Amakuru ni mwiza."],
            "Adjectives take the owning noun's class prefix: ma- + -iza gives meza; "
            "byiza and nziza belong to other classes.",
        ),
        q(
            "grammar",
            "“How is YOUR news?” — the correct possessive is…",
            "Amakuru yawe?",
            ["Amakuru wawe?", "Amakuru byawe?", "Amakuru zawe?"],
            "Possessives also agree: class 6 takes the ya- connector, so “your” "
            "after amakuru is yawe.",
            item="Amakuru yawe?",
        ),
        q(
            "vocab",
            "The informal “What's up?” between friends is…",
            "Bite se?",
            ["Umeze ute?", "Amakuru yawe?", "Murabeho."],
            "Bite se is the casual opener among friends, typically answered ni byiza "
            "— keep Amakuru for elders and new acquaintances.",
            item="Bite se?",
        ),
        q(
            "grammar",
            "What turns “Amakuru” into a question in speech?",
            "A rise in pitch on the final syllable",
            [
                "The particle “se” is required",
                "The verb moves to the end",
                "The prefix changes to aya-",
            ],
            "Kinyarwanda has no question word for “?” — a final rising pitch alone "
            "marks the question.",
            item="Amakuru?",
        ),
        q(
            "culture",
            "With an elder, answering just “ni meza” and walking on reads as…",
            "Cold — the full exchange about family and health matters.",
            [
                "Polite — it keeps the greeting efficient.",
                "Expected — elders dislike small talk.",
                "Rude only in Kigali.",
            ],
            "Amakuru? is not small talk to rush past: news of family, health and "
            "the harvest matters, especially with elders.",
        ),
    ],
}

A1_U1_L3 = {
    "title": "Introducing yourself",
    "grammar_md": """## Nitwa… — saying who you are

Three verbs carry every first introduction:

| Verb | Meaning | I | you | he/she |
|---|---|---|---|---|
| **kwitwa** | to be called | **n**itwa | **w**itwa | **y**itwa |
| **gukomoka** | to come from | **n**komoka | **u**komoka | **a**komoka |
| **gutura** | to live (somewhere) | **n**tuye | **u**tuye | **a**tuye |

The bold letters are **subject prefixes** — Kinyarwanda marks the subject on
the verb itself: **n-** (I), **u-/w-** (you), **a-/y-** (he/she). Before a vowel,
*u-* becomes *w-* and *a-* becomes *y-*: ku-**itwa** → w**itwa**, y**itwa**.

Place names take the little locative word **i**: *Ntuye **i** Kigali* (“I live
in Kigali”), *Nkomoka **i** Huye*. Country names built on *u Rwanda* take **mu**:
*Nkomoka **mu** Rwanda*.

Ask a name with **nde** (“who”): *Witwa nde?* — “What (lit. who) are you called?”""",
    "culture_note": "Umuco: many Rwandan given names are meaningful sentences — Keza "
    "(“beautiful”), Ishimwe (“gratitude”), Mugisha (“blessing”). Asking what a name "
    "means is a compliment, not an intrusion.",
    "items": [
        item("Nitwa Ange.", "My name is Ange.", ["greetings", "grammar"]),
        item("Witwa nde?", "What is your name?", ["greetings"], {3: "R"}),
        item("Nkomoka mu Rwanda.", "I come from Rwanda.", ["greetings"]),
        item("Ntuye i Kigali.", "I live in Kigali.", ["greetings"]),
        item("Uva he?", "Where are you from?", ["greetings"], {2: "R"}),
        item("Nishimiye kukumenya.", "I am pleased to meet you.", ["greetings"]),
        item("Uyu ni inshuti yanjye.", "This is my friend.", ["greetings"]),
    ],
    "quiz": [
        q(
            "grammar",
            "“I am called…” takes which subject prefix on -itwa?",
            "Nitwa",
            ["Witwa", "Yitwa", "Twitwa"],
            "The subject lives on the verb: n- = I, w- = you, y- = he/she — so “my "
            "name is…” is Nitwa.",
            item="Nitwa Ange.",
        ),
        q(
            "grammar",
            "“HE is called Eric” is…",
            "Yitwa Eric.",
            ["Witwa Eric.", "Nitwa Eric.", "Bitwa Eric."],
            "Before the vowel stem -itwa, the he/she prefix a- becomes y-: yitwa.",
        ),
        q(
            "grammar",
            "“I live in Kigali” is…",
            "Ntuye i Kigali.",
            ["Ntuye mu Kigali.", "Ntuye ku Kigali.", "Ntuye Kigali."],
            "Place names take the little locative i (Ntuye i Kigali); mu is for "
            "countries like mu Rwanda.",
            item="Ntuye i Kigali.",
        ),
        q(
            "vocab",
            "To ask someone's name you say…",
            "Witwa nde?",
            ["Uva he?", "Umeze ute?", "Ni saa ngahe?"],
            "Witwa nde? is literally “you are called who?” — nde asks “who”, he asks "
            "“where”, ute asks “how”.",
            item="Witwa nde?",
        ),
        q(
            "usage",
            "You have just been introduced to someone. You say…",
            "Nishimiye kukumenya.",
            ["Ndazimiye.", "Murabeho.", "Ni byose, urakoze."],
            "Nishimiye kukumenya — “I am pleased to meet you” — is the warm close of "
            "an introduction; ndazimiye means “I'm lost”.",
            item="Nishimiye kukumenya.",
        ),
        q(
            "culture",
            "You like the name Keza. Asking what it means is…",
            "A compliment — many Rwandan names are meaningful words.",
            [
                "An intrusion into family matters.",
                "Acceptable only between close friends.",
                "Odd — names have no meanings.",
            ],
            "Rwandan given names often carry meanings — Keza (“beautiful”), Ishimwe "
            "(“gratitude”), Mugisha (“blessing”) — and asking about them honours the name.",
        ),
    ],
}

A1_U1_L4 = {
    "title": "People: umu- and aba- (classes 1–2)",
    "grammar_md": """## The first noun classes: umu- / aba-

Every Kinyarwanda noun belongs to a **class**, shown by its prefix. People live
in class 1 (singular, **umu-**) and class 2 (plural, **aba-**):

| Singular | Plural | Meaning |
|---|---|---|
| umu**ntu** | aba**ntu** | person / people |
| umu**gabo** | aba**gabo** | man / men |
| umu**gore** | aba**gore** | woman / women |
| **umwana** | **abana** | child / children |
| umw**arimu** | ab**arimu** | teacher(s) |
| umu**nyeshuri** | aba**nyeshuri** | student(s) |

*umwana / abana*: before the vowel stem *-ana*, **umu-** contracts to **umw-**
and **aba-** drops its *a* — sound changes you will see across the language.

**The verb agrees**: class 1 subjects take **a-**, class 2 take **ba-**:
*Umwana **a**rasinziriye* (“the child is sleeping”) → *Abana **ba**rasinziriye*.

**The present -ra-**: when the verb ends the sentence, insert **-ra-** —
*Umugore a**ra**vuga* (“the woman is speaking”). When something follows the verb,
-ra- is dropped: *Abana biga ku ishuri* (“the children study at school”).""",
    "culture_note": "Umuco: abantu — people — anchor the proverb “Umuntu ni abantu”: "
    "a person is people; we are who we are through others. The plural class isn't "
    "just grammar, it's a worldview.",
    "items": [
        item("Umwana arasinziriye.", "The child is sleeping.", ["greetings", "grammar"]),
        item("Abana biga ku ishuri.", "The children study at school.", ["greetings", "grammar"]),
        item("Umugore aravuga.", "The woman is speaking.", ["greetings", "grammar"]),
        item("Umugabo arakora.", "The man is working.", ["greetings", "grammar"]),
        item("Abantu benshi baraza.", "Many people are coming.", ["greetings", "grammar"]),
        item("Umwarimu yigisha Ikinyarwanda.", "The teacher teaches Kinyarwanda.", ["greetings", "grammar"]),
        item("Umwana umwe, abana babiri.", "One child, two children.", ["greetings", "grammar"]),
    ],
    "quiz": [
        q(
            "grammar",
            "One child is umwana; several children are…",
            "abana",
            ["abaana", "ubwana", "abantu"],
            "Before the vowel stem -ana, aba- drops its final a: abana — ubwana "
            "means “childhood” and abantu means “people”.",
            item="Umwana umwe, abana babiri.",
        ),
        q(
            "grammar",
            "“The woman is speaking” — which is correct?",
            "Umugore aravuga.",
            ["Umugore baravuga.", "Umugore iravuga.", "Umugore uravuga."],
            "Class 1 subjects (umu-) take the verb prefix a-: umugore a-ra-vuga; "
            "ba- is the class 2 (plural) prefix.",
            item="Umugore aravuga.",
        ),
        q(
            "grammar",
            "Which sentence uses the present -ra- correctly?",
            "Abana biga ku ishuri.",
            ["Abana bariga ku ishuri.", "Umugore vuga.", "Umwana sinziriye."],
            "-ra- appears only when the verb ends the sentence; with “ku ishuri” "
            "following, it drops: biga, not bariga.",
            item="Abana biga ku ishuri.",
        ),
        q(
            "vocab",
            "“Teacher” in Kinyarwanda is…",
            "umwarimu",
            ["umunyeshuri", "umugabo", "umuntu"],
            "Umwarimu is the teacher; umunyeshuri is the student, umugabo a man, "
            "umuntu a person.",
            item="Umwarimu yigisha Ikinyarwanda.",
        ),
        q(
            "vocab",
            "“Abantu benshi baraza.” means…",
            "Many people are coming.",
            [
                "The people have arrived.",
                "A few people are coming.",
                "Many children are coming.",
            ],
            "Abantu = people, benshi = many (agreeing with aba-), baraza = they are "
            "coming — present, not past.",
            item="Abantu benshi baraza.",
        ),
        q(
            "culture",
            "The proverb “Umuntu ni abantu” expresses that…",
            "A person is a person through other people.",
            [
                "One person can stand in for many.",
                "People are hard to predict.",
                "A person must earn adulthood.",
            ],
            "“A person is people”: we are who we are through others — the aba- "
            "plural as a worldview, not just grammar.",
        ),
    ],
}

# ---------------------------------------------------------------------------
# A1 — Unit 2 · Family & home
# ---------------------------------------------------------------------------

A1_U2_L1 = {
    "title": "Meet the family",
    "grammar_md": """## The family — umuryango

| Kinyarwanda | Meaning |
|---|---|
| **mama** | my mother |
| **data** | my father |
| **umubyeyi / ababyeyi** | parent / parents |
| **umuvandimwe / abavandimwe** | sibling / siblings |
| **umuhungu** | boy, son |
| **umukobwa** | girl, daughter |
| **nyogokuru** | my grandmother |
| **sogokuru** | my grandfather |

Kinship words are special: **mama** and **data** already mean “**my** mother/
father” — no possessive needed. “Your mother” is *mama wawe*, “his father” is
*se* — kinship has its own short forms that you will absorb gradually.

To point someone out, use **uyu ni…** (“this is…”): *Uyu ni mama.* To say what
you have, use **-fite**: *Mfite abavandimwe babiri* — “I have two siblings”
(note *babiri* agreeing with the aba- class).""",
    "culture_note": "Umuco: umuryango means both “family” and “extended lineage” — "
    "aunts are often “mothers” (mama wacu) and cousins are simply siblings. "
    "Family questions are warm openers in Rwandan conversation, not prying.",
    "items": [
        item("Uyu ni mama.", "This is my mother.", ["family"]),
        item("Uyu ni data.", "This is my father.", ["family"]),
        item("Mfite abavandimwe babiri.", "I have two siblings.", ["family"]),
        item("Umukobwa wanjye yitwa Keza.", "My daughter is called Keza.", ["family"]),
        item("Umuhungu we ni muto.", "Her son is young.", ["family"]),
        item("Nyogokuru atuye mu cyaro.", "My grandmother lives in the countryside.", ["family"]),
        item("Turi umuryango munini.", "We are a big family.", ["family"]),
    ],
    "quiz": [
        q(
            "grammar",
            "The kinship words mama and data already mean…",
            "my mother / my father",
            [
                "mother / father in general",
                "any older woman / man",
                "grandmother / grandfather",
            ],
            "Kinship words carry a built-in “my”: mama = my mother; “your mother” "
            "needs the possessive — mama wawe.",
        ),
        q(
            "vocab",
            "“My grandmother” is…",
            "nyogokuru",
            ["sogokuru", "umubyeyi", "umukobwa"],
            "Nyogokuru is my grandmother; sogokuru my grandfather, umubyeyi a "
            "parent, umukobwa a girl or daughter.",
            item="Nyogokuru atuye mu cyaro.",
        ),
        q(
            "grammar",
            "“I have two siblings” is…",
            "Mfite abavandimwe babiri.",
            [
                "Mfite abavandimwe kabiri.",
                "Mfite umuvandimwe babiri.",
                "Mfite abavandimwe bibiri.",
            ],
            "Numbers agree with the noun's class: aba- takes babiri; kabiri is the "
            "bare counting form and bibiri belongs to the ibi- class.",
            item="Mfite abavandimwe babiri.",
        ),
        q(
            "vocab",
            "“Umukobwa” means…",
            "girl, daughter",
            ["boy, son", "sibling", "parent"],
            "Umukobwa is a girl or daughter; the boy or son is umuhungu.",
            item="Umukobwa wanjye yitwa Keza.",
        ),
        q(
            "usage",
            "To introduce your mother you say…",
            "Uyu ni mama.",
            ["Uyu ni data.", "Ni meza.", "Nitwa mama."],
            "Uyu ni… (“this is…”) points someone out — and mama already means “my "
            "mother”, no possessive needed.",
            item="Uyu ni mama.",
        ),
        q(
            "culture",
            "In a Rwandan umuryango, your aunt may well be called…",
            "mama wacu — “our mother”",
            ["nyogokuru", "umukobwa", "inshuti"],
            "Umuryango means both family and extended lineage: aunts are often "
            "“mothers” and cousins simply siblings.",
        ),
    ],
}

A1_U2_L2 = {
    "title": "Mine and yours — possessives",
    "grammar_md": """## Possessives agree with the noun's class

The possessive stems are fixed:

| my | your (sg) | his/her | our | your (pl) | their |
|---|---|---|---|---|---|
| -anjye | -awe | -e | -acu | -anyu | -abo |

…but their **prefix comes from the noun being owned**:

| Class | Connector | Example |
|---|---|---|
| 1 (umu-) | **wa-** | umwana **wanjye** — my child |
| 2 (aba-) | **ba-** | abana **banjye** — my children |
| 7 (iki-) | **cya-** | igitabo **cyawe** — your book |
| 9 (in-) | **ya-** | inzu **yanjye** — my house |
| 3 (umu-, things) | **wa-** | umuryango **wacu** — our family |

So “my” is not one word in Kinyarwanda — it is *wanjye, banjye, cyanjye,
yanjye…* depending on what is owned. Learn possessives **inside phrases**
(*umwana wanjye*, *inzu yanjye*), never as bare lists.""",
    "culture_note": "Umuco: “our” beats “my”. Rwandans habitually say urugo rwacu, "
    "umuryango wacu — our home, our family — even about their own household. "
    "Claiming things with -anjye where -acu fits can sound oddly individualistic.",
    "items": [
        item("Umwana wanjye", "my child", ["family", "grammar"]),
        item("Abana banjye", "my children", ["family", "grammar"]),
        item("Inzu yanjye ni nto.", "My house is small.", ["family", "grammar"]),
        item("Igitabo cyawe", "your book", ["family", "grammar"]),
        item("Umuryango wacu", "our family", ["family", "grammar"]),
        item("Mama wawe ameze ute?", "How is your mother?", ["family"], {5: "R"}),
        item("Abavandimwe be batuye i Huye.", "His siblings live in Huye.", ["family"]),
    ],
    "quiz": [
        q(
            "grammar",
            "“My house” is…",
            "inzu yanjye",
            ["inzu wanjye", "inzu cyanjye", "inzu banjye"],
            "The possessive's prefix comes from the owned noun: class 9 (in-) takes "
            "ya-, so inzu yanjye.",
            item="Inzu yanjye ni nto.",
        ),
        q(
            "grammar",
            "“Your book” is…",
            "igitabo cyawe",
            ["igitabo wawe", "igitabo yawe", "igitabo bawe"],
            "Igitabo is class 7 (iki-), whose connector is cya-: igitabo cyawe.",
            item="Igitabo cyawe",
        ),
        q(
            "grammar",
            "“My children” is…",
            "abana banjye",
            ["abana wanjye", "abana yanjye", "abana cyanjye"],
            "Class 2 (aba-) takes the ba- connector: abana banjye — “my” is a "
            "different word for every class.",
            item="Abana banjye",
        ),
        q(
            "vocab",
            "“Umuryango wacu” means…",
            "our family",
            ["my family", "your family", "their family"],
            "The stem -acu is “our”; -anjye my, -awe your, -abo their.",
            item="Umuryango wacu",
        ),
        q(
            "usage",
            "You meet a friend and ask after his mother:",
            "Mama wawe ameze ute?",
            ["Mama wanjye ameze ute?", "Data wawe ni nde?", "Mama wawe ni angahe?"],
            "Mama wawe = “your mother”, ameze ute = “how is she doing” — wanjye "
            "would ask about your own mother.",
            item="Mama wawe ameze ute?",
        ),
        q(
            "culture",
            "Rwandans habitually say “urugo rwacu” rather than “urugo rwanjye” because…",
            "“Our” reflects the shared household — -anjye can sound individualistic.",
            [
                "rwanjye is grammatically wrong.",
                "rwacu is easier to pronounce.",
                "-anjye is reserved for objects.",
            ],
            "“Our” beats “my”: Rwandans say umuryango wacu, urugo rwacu even about "
            "their own household.",
        ),
    ],
}

A1_U2_L3 = {
    "title": "The home: inzu n'urugo",
    "grammar_md": """## Around the house

| Kinyarwanda | Class | Meaning |
|---|---|---|
| **inzu** | 9 (in-) | house (the building) |
| **urugo** | 11 (uru-) | home, homestead, compound |
| **icyumba / ibyumba** | 7/8 | room / rooms |
| **igikoni** | 7 | kitchen |
| **umuryango** | 3 | doorway (same word as “family”!) |

Two little location words do most of the work:

- **mu** = inside: *mu nzu* (in the house), *mu gikoni* (in the kitchen)
- **ku** = at/on: *ku rugo* (at the homestead), *ku meza* (on the table)

After **mu** and **ku** the noun **drops its initial vowel**: i-nzu → mu **nzu**,
u-rugo → ku **rugo**, i-gikoni → mu **gikoni**. Hearing that clipped form is a
sure sign a location phrase is coming.

“To be somewhere” is **-ri**: *Ndi mu gikoni* (I am in the kitchen), *Mama ari
mu nzu* (Mother is in the house).""",
    "culture_note": "Umuco: urugo is more than a building — traditionally a fenced "
    "compound holding the house, kraal and yard; a married adult “has an urugo”, "
    "meaning a household. Inzu is the structure; urugo is the life in it.",
    "items": [
        item("Inzu yacu ifite ibyumba bitatu.", "Our house has three rooms.", ["family"]),
        item("Ndi mu gikoni.", "I am in the kitchen.", ["family"]),
        item("Mama ari mu nzu.", "Mother is in the house.", ["family"]),
        item("Abana bakinira ku rugo.", "The children are playing in the yard.", ["family"]),
        item("Icyumba cyanjye ni gito.", "My room is small.", ["family"]),
        item("Urugo rwacu ruri hafi y'isoko.", "Our home is near the market.", ["family"]),
    ],
    "quiz": [
        q(
            "grammar",
            "“In the kitchen” — igikoni after mu becomes…",
            "mu gikoni",
            ["mu igikoni", "i gikoni", "ku igikoni"],
            "After mu and ku the noun drops its initial vowel: i-gikoni → mu "
            "gikoni; the locative i is for place names.",
            item="Ndi mu gikoni.",
        ),
        q(
            "grammar",
            "“I am in the kitchen” is…",
            "Ndi mu gikoni.",
            ["Ni mu gikoni.", "Nitwa mu gikoni.", "Mfite mu gikoni."],
            "Being somewhere uses -ri with a subject prefix: n-di (“I am”); bare ni "
            "only identifies (“it is”).",
            item="Ndi mu gikoni.",
        ),
        q(
            "vocab",
            "“Icyumba” means…",
            "room",
            ["kitchen", "house", "doorway"],
            "Icyumba (plural ibyumba) is a room; the kitchen is igikoni and the "
            "house inzu.",
            item="Icyumba cyanjye ni gito.",
        ),
        q(
            "vocab",
            "Which word means both “doorway” and “family”?",
            "umuryango",
            ["urugo", "inzu", "igikoni"],
            "Umuryango is the doorway you pass through and the family/lineage — the "
            "same word for both thresholds of belonging.",
        ),
        q(
            "usage",
            "“Where is Mother?” — “She is in the house”:",
            "Mama ari mu nzu.",
            ["Mama ni mu nzu.", "Mama iri mu nzu.", "Mama ari ku nzu."],
            "Class-1 mama takes a- + -ri (ari), and mu means inside: mu nzu, with "
            "inzu's initial vowel dropped.",
            item="Mama ari mu nzu.",
        ),
        q(
            "culture",
            "The difference between inzu and urugo:",
            "Inzu is the building; urugo is the homestead and the life in it.",
            [
                "They are exact synonyms.",
                "Urugo is a modern word for apartment.",
                "Inzu means compound, urugo means house.",
            ],
            "Traditionally urugo is the fenced compound — a married adult “has an "
            "urugo”, meaning a household — while inzu is just the structure.",
        ),
    ],
}

A1_U2_L4 = {
    "title": "To have and to be",
    "grammar_md": """## -fite (have) and the three ways to “be”

**Having — -fite** (no -ra- ever):

| | -fite |
|---|---|
| I | **m**fite |
| you | **u**fite |
| he/she | **a**fite |
| we | **du**fite |
| you (pl) | **mu**fite |
| they | **ba**fite |

*Mfite imyaka makumyabiri* — “I am twenty” is literally “I **have** twenty years”.

**Being** splits three ways:

1. **ni** — identification, no subject prefix: *Ni umwarimu.* (“She is a teacher.”)
2. **-ri** — location/state: *Ndi mu rugo. Turi mu nzu.* (I am at home / we are inside.)
3. **kuba** — to be habitually / to live: *Mba i Kigali.* (“I live in Kigali.”)

**The present -ra- again**: verb-final sentences take it — *Ndakora* (“I'm
working”); add a complement and it drops — *Nkora ku isoko* (“I work at the
market”). This conjoint/disjoint switch is the heartbeat of Kinyarwanda rhythm.""",
    "culture_note": "Umuco: age is worn proudly — asking “Ufite imyaka ingahe?” "
    "is normal between adults, and elders expect their years to earn the plural "
    "forms of respect you met in the greetings lesson.",
    "items": [
        item("Mfite imyaka makumyabiri.", "I am twenty years old.", ["family", "grammar"]),
        item("Ufite abana bangahe?", "How many children do you have?", ["family"], {6: "R"}),
        item("Afite inzu i Kigali.", "He has a house in Kigali.", ["family"]),
        item("Ndi umunyeshuri.", "I am a student.", ["family", "grammar"]),
        item("Turi mu rugo.", "We are at home.", ["family", "grammar"]),
        item("Ni umwarimu.", "She is a teacher.", ["family", "grammar"]),
        item("Ndakora.", "I am working.", ["family", "grammar"]),
    ],
    "quiz": [
        q(
            "grammar",
            "“I am twenty” is said with “have”:",
            "Mfite imyaka makumyabiri.",
            [
                "Ndi imyaka makumyabiri.",
                "Ni imyaka makumyabiri.",
                "Mba imyaka makumyabiri.",
            ],
            "Age is possessed in Kinyarwanda — literally “I have twenty years”, "
            "with -fite, never with “to be”.",
            item="Mfite imyaka makumyabiri.",
        ),
        q(
            "grammar",
            "“THEY have” is…",
            "bafite",
            ["dufite", "mufite", "afite"],
            "-fite takes the plain subject prefixes: ba- they, du- we, mu- you "
            "(pl.), a- he/she.",
        ),
        q(
            "grammar",
            "“She is a teacher” — identification uses…",
            "Ni umwarimu.",
            ["Ari umwarimu.", "Aba umwarimu.", "Afite umwarimu."],
            "Bare ni identifies with no subject prefix; -ri is for location and "
            "kuba for living/being habitually.",
            item="Ni umwarimu.",
        ),
        q(
            "grammar",
            "“I work at the market” — with a complement after the verb:",
            "Nkora ku isoko.",
            ["Ndakora ku isoko.", "Kora ku isoko.", "Nakora ku isoko."],
            "The present -ra- drops when something follows the verb: Ndakora alone, "
            "but Nkora ku isoko.",
            item="Ndakora.",
        ),
        q(
            "usage",
            "To ask an adult how many children they have:",
            "Ufite abana bangahe?",
            ["Mfite abana bangahe?", "Ufite abana angahe?", "Ufite bana bangahe?"],
            "u- addresses “you”, and -ngahe agrees with aba-: bangahe — mfite would "
            "ask about yourself.",
            item="Ufite abana bangahe?",
        ),
        q(
            "culture",
            "Asking an adult “Ufite imyaka ingahe?” (how old are you?) is…",
            "Normal — age is worn proudly and earns respect.",
            [
                "Taboo outside the family.",
                "Acceptable only from elders.",
                "An insult unless clearly joking.",
            ],
            "Years earn the plural forms of respect, so age is asked and told "
            "openly between adults.",
        ),
    ],
}

# ---------------------------------------------------------------------------
# A1 — Unit 3 · Numbers & time
# ---------------------------------------------------------------------------

A1_U3_L1 = {
    "title": "Counting 1–10",
    "grammar_md": """## Imibare — the first ten

Counting out loud (no noun attached):

| 1 | 2 | 3 | 4 | 5 |
|---|---|---|---|---|
| rimwe | kabiri | gatatu | kane | gatanu |

| 6 | 7 | 8 | 9 | 10 |
|---|---|---|---|---|
| gatandatu | karindwi | umunani | icyenda | icumi |

**Numbers agree too.** Attached to a noun, 1–7 take the noun's class prefix:

- *umwana **umwe*** — one child; *abana **babiri*** — two children
- *igitabo **kimwe*** — one book; *ibitabo **bibiri*** — two books
- *inzu **imwe*** — one house; *inzu **ebyiri*** — two houses (class 10 is irregular: ebyiri, eshatu, enye, eshanu)

8, 9 and 10 (*umunani, icyenda, icumi*) never change. Ask “how many?” with
**-ngahe**, which also agrees: *abana **bangahe**?*, *inzu **zingahe**?*""",
    "culture_note": "Umuco: counting on fingers starts from the index finger, and "
    "market totals are often tapped out on the palm. Watch a vendor count change — "
    "numbers live in the hands as much as the mouth.",
    "items": [
        item("Rimwe, kabiri, gatatu.", "One, two, three.", ["numbers"]),
        item("Mfite abana batatu.", "I have three children.", ["numbers"]),
        item("Ibitabo bine biri ku meza.", "Four books are on the table.", ["numbers"]),
        item("Inzu ebyiri", "two houses", ["numbers"]),
        item("Abantu icumi baraza.", "Ten people are coming.", ["numbers"]),
        item("Gatanu na gatanu ni icumi.", "Five and five is ten.", ["numbers"]),
    ],
    "quiz": [
        q(
            "vocab",
            "“Seven”, counting aloud, is…",
            "karindwi",
            ["gatandatu", "umunani", "icyenda"],
            "Karindwi is seven; gatandatu six, umunani eight, icyenda nine.",
        ),
        q(
            "grammar",
            "“Two books” is…",
            "ibitabo bibiri",
            ["ibitabo kabiri", "ibitabo babiri", "ibitabo ebyiri"],
            "Attached to a noun, 1–7 take its class prefix: ibi- gives bibiri; "
            "kabiri is only for counting aloud.",
            item="Ibitabo bine biri ku meza.",
        ),
        q(
            "grammar",
            "Which numbers never change form, whatever the noun?",
            "umunani, icyenda, icumi (8, 9, 10)",
            [
                "rimwe, kabiri, gatatu (1, 2, 3)",
                "everything from 1 to 7",
                "all numbers agree with the noun",
            ],
            "Only 1–7 take class prefixes; umunani, icyenda and icumi stay fixed.",
        ),
        q(
            "grammar",
            "“How many houses?” is…",
            "inzu zingahe?",
            ["inzu bangahe?", "inzu cyangahe?", "inzu ingahe?"],
            "-ngahe agrees like a number: class 10 takes zi- (zingahe); bangahe "
            "belongs to people (aba-).",
        ),
        q(
            "usage",
            "A friend asks how many children you have; you have three:",
            "Mfite abana batatu.",
            ["Mfite abana gatatu.", "Mfite batatu abana.", "Mfite abana bane."],
            "The number follows the noun and agrees with aba-: batatu — bane would "
            "be four.",
            item="Mfite abana batatu.",
        ),
        q(
            "culture",
            "Counting on fingers in Rwanda typically starts from…",
            "the index finger",
            ["the thumb", "the little finger", "the left palm"],
            "Fingers count from the index finger, and market totals are often "
            "tapped out on the palm — numbers live in the hands.",
        ),
    ],
}

A1_U3_L2 = {
    "title": "Eleven to one hundred",
    "grammar_md": """## Building bigger numbers

Kinyarwanda numbers are transparent — you assemble them with **na** (“and”):

| Number | Kinyarwanda | Built from |
|---|---|---|
| 11 | icumi **na** rimwe | ten and one |
| 15 | icumi na gatanu | ten and five |
| 20 | **makumyabiri** | (special word) |
| 25 | makumyabiri na gatanu | twenty and five |
| 30 | **mirongo itatu** | “three tens” |
| 40 | mirongo ine | four tens |
| 50 | mirongo itanu | five tens |
| 99 | mirongo icyenda n'icyenda | nine tens and nine |
| 100 | **ijana** | hundred |

From 30 upward, tens are *mirongo* + an agreeing number (“tens that are three”).
Twenty alone keeps its own old word, **makumyabiri**.

Your age uses -fite + *imyaka*: *Mfite imyaka mirongo itatu* — “I'm thirty.”""",
    "culture_note": "Umuco: prices are usually round hundreds, and vendors quote them "
    "fast — magana atanu! Recognising the tens and hundreds by ear before you can "
    "produce them is a survival skill for Unit “Market & money”.",
    "items": [
        item("Icumi na rimwe", "eleven", ["numbers"]),
        item("Makumyabiri", "twenty", ["numbers"]),
        item("Mirongo itatu na gatanu", "thirty-five", ["numbers"]),
        item("Mirongo itanu", "fifty", ["numbers"]),
        item("Ijana", "one hundred", ["numbers"]),
        item("Mfite imyaka mirongo itatu.", "I am thirty years old.", ["numbers"]),
    ],
    "quiz": [
        q(
            "vocab",
            "“Twenty” is…",
            "makumyabiri",
            ["mirongo ibiri", "icumi na kabiri", "magana abiri"],
            "Twenty keeps its own old word makumyabiri; the mirongo tens start at "
            "30, and magana abiri is 200.",
            item="Makumyabiri",
        ),
        q(
            "grammar",
            "“Thirty” is built as “three tens”:",
            "mirongo itatu",
            ["mirongo gatatu", "makumyatatu", "ijana itatu"],
            "From 30 upward, tens are mirongo plus an agreeing number — itatu, not "
            "the counting form gatatu.",
            item="Mirongo itanu",
        ),
        q(
            "vocab",
            "“Icumi na rimwe” is…",
            "eleven",
            ["ten", "twelve", "twenty-one"],
            "Numbers assemble with na (“and”): ten and one — eleven.",
            item="Icumi na rimwe",
        ),
        q(
            "usage",
            "“I am thirty years old”:",
            "Mfite imyaka mirongo itatu.",
            [
                "Ndi imyaka mirongo itatu.",
                "Mfite imyaka gatatu.",
                "Mfite mirongo itatu imyaka.",
            ],
            "Age uses -fite + imyaka, with the number after the noun — imyaka "
            "gatatu would make you three.",
            item="Mfite imyaka mirongo itatu.",
        ),
        q(
            "vocab",
            "“One hundred” is…",
            "ijana",
            ["igihumbi", "mirongo icyenda", "magana"],
            "Ijana is 100; igihumbi is 1 000, mirongo icyenda 90, and magana the "
            "plural “hundreds”.",
            item="Ijana",
        ),
        q(
            "culture",
            "A vendor calls out “magana atanu!” — she means…",
            "500 francs",
            ["50 francs", "5 000 francs", "five items"],
            "Prices come fast in round hundreds: magana atanu = five hundreds — "
            "catching tens and hundreds by ear is market survival.",
        ),
    ],
}

A1_U3_L3 = {
    "title": "What time is it? — Ni saa ngahe?",
    "grammar_md": """## East African time

Rwanda tells time the East African way: the day starts at **sunrise (6:00)**, so
**saa moya** — “hour one” — is **7:00**, not one o'clock. The hour names came in
through Swahili and stayed:

| Clock | Kinyarwanda | Count |
|---|---|---|
| 7:00 | saa moya | hour 1 |
| 8:00 | saa mbiri | hour 2 |
| 9:00 | saa tatu | hour 3 |
| 12:00 (noon) | saa sita | hour 6 |
| 15:00 | saa cyenda | hour 9 |
| 18:00 | saa kumi n'ebyiri | hour 12 |

Ask with **Ni saa ngahe?** (“what hour is it?”). Disambiguate with the part of
day: **za mu gitondo** (in the morning), **za ku manywa** (in the daytime),
**za nimugoroba** (in the evening), **za mu ijoro** (at night).

*Ni saa moya za mu gitondo* = 7 a.m. — count SIX hours forward from the number
you hear and you have Western time.""",
    "culture_note": "Umuco: “saa moya” meaning 7:00 trips up every visitor once. If a "
    "Rwandan friend says to meet at saa mbiri, they mean 8:00 — the day is counted "
    "from sunrise, when life actually starts.",
    "items": [
        item("Ni saa ngahe?", "What time is it?", ["numbers"], {3: "R"}),
        item("Ni saa moya za mu gitondo.", "It is seven in the morning.", ["numbers"]),
        item("Ni saa sita.", "It is noon.", ["numbers"]),
        item("Ni saa cyenda.", "It is three in the afternoon.", ["numbers"]),
        item("Tuzahura nimugoroba.", "We will meet in the evening.", ["numbers"]),
        item("Mbyuka kare mu gitondo.", "I wake up early in the morning.", ["numbers"]),
    ],
    "quiz": [
        q(
            "vocab",
            "On the East African clock, “saa moya” is…",
            "7:00",
            ["1:00", "6:00", "12:00"],
            "The day starts at sunrise (6:00), so “hour one” lands at 7:00 — count "
            "six hours forward from the number you hear.",
            item="Ni saa moya za mu gitondo.",
        ),
        q(
            "usage",
            "A friend says to meet at “saa mbiri za mu gitondo”. You arrive at…",
            "8:00 in the morning",
            [
                "2:00 in the morning",
                "7:00 in the morning",
                "2:00 in the afternoon",
            ],
            "Saa mbiri is “hour two” = 8:00, and za mu gitondo pins it to the "
            "morning.",
        ),
        q(
            "vocab",
            "“Noon” is…",
            "saa sita",
            ["saa moya", "saa kumi n'ebyiri", "saa cyenda"],
            "Saa sita — “hour six” — is noon; saa kumi n'ebyiri (hour twelve) is "
            "18:00 and saa cyenda 15:00.",
            item="Ni saa sita.",
        ),
        q(
            "vocab",
            "To ask the time you say…",
            "Ni saa ngahe?",
            ["Ni angahe?", "Ni ryari?", "Ni he?"],
            "Saa ngahe asks the hour; angahe alone asks a price, ryari “when” and "
            "he “where”.",
            item="Ni saa ngahe?",
        ),
        q(
            "usage",
            "“za nimugoroba” pins an hour to…",
            "the evening",
            ["the morning", "midday", "deep night"],
            "Disambiguate hours with the part of day: mu gitondo morning, ku manywa "
            "daytime, nimugoroba evening, mu ijoro night.",
            item="Tuzahura nimugoroba.",
        ),
        q(
            "culture",
            "Why does saa moya mean 7:00 in Rwanda?",
            "Hours are counted from sunrise at 6:00, when the day's life starts.",
            [
                "Hours are counted from midnight.",
                "Hours are counted from noon.",
                "It follows a French colonial convention.",
            ],
            "“Saa moya = 7:00” trips up every visitor once — if a friend says saa "
            "mbiri, they mean 8:00.",
        ),
    ],
}

A1_U3_L4 = {
    "title": "Days of the week — and the two faces of “ejo”",
    "grammar_md": """## Iminsi y'icyumweru

Days are ordinals built on **ku wa** (“on the …th”):

| Day | Kinyarwanda |
|---|---|
| Monday | **ku wa mbere** (the first) |
| Tuesday | ku wa kabiri |
| Wednesday | ku wa gatatu |
| Thursday | ku wa kane |
| Friday | ku wa gatanu |
| Saturday | ku wa gatandatu |
| Sunday | **ku cyumweru** (“the week day”) |

**Ejo means BOTH yesterday and tomorrow** — context or a helper decides:

- **ejo hashize** — “ejo that passed” = yesterday
- **ejo hazaza** — “ejo that comes” = tomorrow
- **uyu munsi** — today

*Ejo* pairs naturally with the past and future tenses you'll meet at A2:
*Ejo hashize **nagiye**…* (yesterday I went), *Ejo hazaza **nzajya**…*
(tomorrow I will go).""",
    "culture_note": "Umuco: the last Saturday of every month is Umuganda — nationwide "
    "community work, roads quiet until noon. Plan around it; better, join your "
    "neighbours. It is the fastest way to belong on your street.",
    "items": [
        item("Uyu munsi ni ku wa kabiri.", "Today is Tuesday.", ["numbers"]),
        item("Ejo hazaza tuzajya ku isoko.", "Tomorrow we will go to the market.", ["numbers"]),
        item("Ejo hashize nagiye ku ishuri.", "Yesterday I went to school.", ["numbers"]),
        item("Ku cyumweru turuhuka.", "On Sunday we rest.", ["numbers"]),
        item("Icyumweru gifite iminsi irindwi.", "A week has seven days.", ["numbers"]),
        item("Tuzahura ku wa gatanu.", "We will meet on Friday.", ["numbers"]),
    ],
    "quiz": [
        q(
            "vocab",
            "“Monday” is…",
            "ku wa mbere",
            ["ku cyumweru", "ku wa kabiri", "ku wa gatanu"],
            "Days are ordinals on ku wa: Monday is “the first” — ku wa kabiri is "
            "Tuesday and ku wa gatanu Friday.",
            item="Uyu munsi ni ku wa kabiri.",
        ),
        q(
            "grammar",
            "Ejo means both yesterday and tomorrow. “Yesterday” specifically is…",
            "ejo hashize",
            ["ejo hazaza", "uyu munsi", "buri munsi"],
            "Hashize (“that passed”) points ejo backwards; hazaza (“that comes”) "
            "points it forward.",
            item="Ejo hashize nagiye ku ishuri.",
        ),
        q(
            "grammar",
            "Which pairing of ejo and tense is correct?",
            "Ejo hazaza nzajya — tomorrow I will go",
            [
                "Ejo hazaza nagiye — tomorrow I went",
                "Ejo hashize nzajya — yesterday I will go",
                "Ejo hashize tuzajya — yesterday we will go",
            ],
            "Ejo hazaza pairs with the future -za-; ejo hashize pairs with the "
            "past -a- … -ye forms.",
            item="Ejo hazaza tuzajya ku isoko.",
        ),
        q(
            "vocab",
            "“Sunday” is…",
            "ku cyumweru",
            ["ku wa gatandatu", "ku wa karindwi", "ku wa mbere"],
            "Sunday is “the week day” — ku cyumweru; there is no ku wa karindwi, "
            "and ku wa gatandatu is Saturday.",
            item="Ku cyumweru turuhuka.",
        ),
        q(
            "usage",
            "It is Thursday and a friend proposes meeting “ejo hazaza”. That means…",
            "Friday",
            ["Wednesday", "Thursday next week", "Sunday"],
            "Ejo hazaza is the ejo that comes — the very next day.",
        ),
        q(
            "culture",
            "On the last Saturday morning of each month, streets are quiet because of…",
            "Umuganda — nationwide community work",
            ["a national lie-in", "the biggest market day", "a driving ban for taxis"],
            "Umuganda pauses the country until noon — and joining your neighbours "
            "is the fastest way to belong on your street.",
        ),
    ],
}

# ---------------------------------------------------------------------------
# A2 — Unit 1 · Getting around
# ---------------------------------------------------------------------------

A2_U1_L1 = {
    "title": "Taking a moto",
    "grammar_md": """## Moto! — commands and let's-go forms

Getting around Kigali means motos, and motos run on two verb moods:

**The imperative** — the bare stem, for direct instructions:

| Command | Meaning |
|---|---|
| **Genda!** | Go! |
| **Hagarara hano.** | Stop here. |
| **Ngwino.** | Come. (irregular) |
| **Genda buhoro.** | Go slowly. |

**The subjunctive** — final -a becomes **-e**, for suggestions and “let's”:

- *Tujye mu mujyi.* — “Let's go to town.” (kujya → tu-jy-**e**)
- *Tugende.* — “Let's get going.” (kugenda → tu-gend-**e**)

Destination phrases reuse the locatives: **mu mujyi** (into town), **ku isoko**
(to the market), **i Kimironko** (to Kimironko — place names take *i*).

Ask the fare before you ride: *Ni angahe kugera ku isoko?* — “how much to reach
the market?” (**kugera** = to reach).""",
    "culture_note": "Umuco: agree the moto fare BEFORE the helmet goes on — "
    "negotiating at the destination is bad form on both sides. Helmets are law; a "
    "driver without a passenger helmet is not your driver.",
    "items": [
        item("Moto! Tujye mu mujyi.", "Moto! Let's go to town.", ["transport"]),
        item("Ni angahe kugera ku isoko?", "How much to get to the market?", ["transport"], {2: "H"}),
        item("Ndashaka kujya i Kimironko.", "I want to go to Kimironko.", ["transport"]),
        item("Genda buhoro.", "Go slowly.", ["transport"]),
        item("Hagarara hano.", "Stop here.", ["transport"]),
        item("Ingofero iri he?", "Where is the helmet?", ["transport"], {5: "R"}),
        item("Ngwino, tugende.", "Come, let's go.", ["transport"]),
    ],
    "quiz": [
        q(
            "grammar",
            "“Let's get going” uses the subjunctive final -e:",
            "Tugende.",
            ["Tugenda.", "Genda.", "Tuzagenda."],
            "For suggestions the final -a becomes -e: tu-gend-e; Genda! is a direct "
            "command and tuzagenda is the future “we will go”.",
            item="Ngwino, tugende.",
        ),
        q(
            "grammar",
            "A direct instruction to the driver — “Stop here”:",
            "Hagarara hano.",
            ["Hagarare hano.", "Uhagarara hano.", "Guhagarara hano."],
            "The imperative is the bare stem: Hagarara — no subject prefix, no "
            "infinitive gu-.",
            item="Hagarara hano.",
        ),
        q(
            "usage",
            "Before the helmet goes on, you ask…",
            "Ni angahe kugera ku isoko?",
            ["Ni saa ngahe?", "Amakuru yawe?", "Uva he?"],
            "Agree the fare first: “how much to reach the market?” — kugera means "
            "“to reach”.",
            item="Ni angahe kugera ku isoko?",
        ),
        q(
            "vocab",
            "“Slowly”, as in “go slowly”, is…",
            "buhoro",
            ["vuba", "cyane", "kare"],
            "Genda buhoro — go slowly; vuba is fast, cyane very, kare early.",
            item="Genda buhoro.",
        ),
        q(
            "grammar",
            "“To Kimironko” — neighbourhood and place names take…",
            "i Kimironko",
            ["mu Kimironko", "ku Kimironko", "za Kimironko"],
            "Place names take the locative i (i Kimironko, i Kigali); mu is for "
            "countries and enclosed spaces.",
            item="Ndashaka kujya i Kimironko.",
        ),
        q(
            "culture",
            "The right moment to agree the moto fare is…",
            "before the ride begins",
            [
                "at the destination",
                "halfway, at a red light",
                "only if the driver raises it",
            ],
            "Negotiating at the destination is bad form on both sides — and a "
            "driver without a passenger helmet is not your driver.",
        ),
    ],
}

A2_U1_L2 = {
    "title": "Directions",
    "grammar_md": """## Which way? — iburyo, ibumoso

| Kinyarwanda | Meaning |
|---|---|
| **iburyo** | right |
| **ibumoso** | left |
| **imbere** | ahead / in front |
| **inyuma** | behind |
| **hafi (ya…)** | near (to) |
| **kure (ya…)** | far (from) |
| **iruhande rwa…** | beside, next to |

The verb for turning is **gukata**: *Kata iburyo* — “turn right”; keep going
with **komeza**: *Komeza imbere* — “continue straight”.

**Here and there** come in three distances — *hano* (here), *aho* (there,
known), *hariya* (over there, visible far off).

Asking politely uses the conditional **wa-…**: *Wamfasha?* — “could you help
me?” — softer than the bare imperative *mfasha* (“help me”). *Ndazimiye* (“I'm
lost”, from *kuzimira*) plus *Wamfasha?* will get you anywhere in Rwanda.""",
    "culture_note": "Umuco: Rwandans often point with the whole hand or a nod of the "
    "chin — a single pointed finger at a person is rude. If someone walks you part "
    "of the way instead of explaining, that's normal hospitality; accept it.",
    "items": [
        item("Kata iburyo.", "Turn right.", ["transport"]),
        item("Kata ibumoso.", "Turn left.", ["transport"]),
        item("Komeza imbere.", "Keep going straight.", ["transport"]),
        item("Isoko riri hafi.", "The market is near.", ["transport"]),
        item("Ni kure cyane?", "Is it very far?", ["transport"], {3: "R"}),
        item("Banki iri iruhande rw'ivuriro.", "The bank is next to the clinic.", ["transport"]),
        item("Ndazimiye. Wamfasha?", "I'm lost. Could you help me?", ["transport"]),
    ],
    "quiz": [
        q(
            "vocab",
            "“Turn right” is…",
            "Kata iburyo.",
            ["Kata ibumoso.", "Komeza imbere.", "Hagarara hano."],
            "Gukata is to turn: iburyo right, ibumoso left; komeza imbere keeps "
            "you going straight.",
            item="Kata iburyo.",
        ),
        q(
            "vocab",
            "“Komeza imbere” means…",
            "Keep going straight.",
            ["Turn back.", "Stop ahead.", "Wait behind."],
            "Komeza = continue, imbere = ahead/in front — the straight-on "
            "instruction.",
            item="Komeza imbere.",
        ),
        q(
            "grammar",
            "“Could you help me?” — the polite conditional is…",
            "Wamfasha?",
            ["Mfasha!", "Uramfasha?", "Kumfasha?"],
            "The wa- conditional softens a request; bare Mfasha! is a blunt "
            "command.",
            item="Ndazimiye. Wamfasha?",
        ),
        q(
            "vocab",
            "“Over there, visible far off” is…",
            "hariya",
            ["hano", "aho", "hafi"],
            "Distance comes in three steps: hano here, aho there (known), hariya "
            "over there in sight.",
        ),
        q(
            "usage",
            "You are lost in a new neighbourhood. You say…",
            "Ndazimiye. Wamfasha?",
            ["Ndahaze, urakoze.", "Ni angahe?", "Nitwa Ange."],
            "Ndazimiye (“I'm lost”) plus the soft Wamfasha? will get you anywhere "
            "in Rwanda.",
            item="Ndazimiye. Wamfasha?",
        ),
        q(
            "culture",
            "Instead of explaining the route, a stranger walks you part of the way. This is…",
            "normal hospitality — accept it",
            [
                "a request for payment",
                "unusual — politely refuse",
                "a sign you offended them",
            ],
            "Walking you along is ordinary kindness; remember too that pointing at "
            "a person with one finger is rude — use the whole hand.",
        ),
    ],
}

A2_U1_L3 = {
    "title": "The bus and places in town",
    "grammar_md": """## Mu mujyi — around town

| Place | Class | Meaning |
|---|---|---|
| **isoko** | 5 (i-/ri-) | market |
| **ishuri** | 5 | school |
| **ivuriro** | 5 | clinic, health centre |
| **banki** | 9 | bank |
| **bisi** | 9 | bus |
| **umujyi** | 3 | town, city |

Class 5 nouns (isoko, ishuri, ivuriro) take **ri-** agreement: *isoko **ri**ri
hafi* — “the market is near”. Class 9 (banki, bisi) takes **i-**: *bisi **i**ri
he?*

Frequency with **buri**: *buri munsi* (every day), *buri cyumweru* (every week):
*Njya ku ishuri buri munsi* — “I go to school every day” (habitual: no -ra-).

Useful bus verbs: **gutegereza** (wait for), **kumanuka** (get off/descend),
**itike** (ticket): *Ndifuza kumanuka hano* — “I'd like to get off here”
(**kwifuza** = polite want).""",
    "culture_note": "Umuco: Kigali buses fill seat by seat and leave when full — "
    "timetables are aspirations. The conductor calls the destination out the "
    "window; answer with a hand signal and he will stop for you.",
    "items": [
        item("Bisi ijya mu mujyi iri he?", "Where is the bus going to town?", ["transport"], {8: "R"}),
        item("Njya ku ishuri buri munsi.", "I go to school every day.", ["transport"]),
        item("Tegereza bisi hano.", "Wait for the bus here.", ["transport"]),
        item("Itike ni amafaranga magana abiri.", "The ticket is two hundred francs.", ["transport"]),
        item("Ndifuza kumanuka hano.", "I'd like to get off here.", ["transport"]),
        item("Umujyi uri kure y'urugo rwanjye.", "Town is far from my home.", ["transport"]),
    ],
    "quiz": [
        q(
            "grammar",
            "Class 5 isoko/ishuri agree with ri-. “The school is near” is…",
            "Ishuri riri hafi.",
            ["Ishuri iri hafi.", "Ishuri ziri hafi.", "Ishuri biri hafi."],
            "Class 5 (i-/ri-) takes ri-: ishuri riri hafi — class 9 words like "
            "banki and bisi take i- instead.",
        ),
        q(
            "grammar",
            "“I go to school every day” — a habit, so…",
            "Njya ku ishuri buri munsi.",
            [
                "Ndajya ku ishuri buri munsi.",
                "Njye ku ishuri buri munsi.",
                "Nzajya ku ishuri ejo.",
            ],
            "Habitual actions drop -ra-: njya, with buri munsi (“every day”) — "
            "ndajya would be “I am going (now)”.",
            item="Njya ku ishuri buri munsi.",
        ),
        q(
            "vocab",
            "“To wait for” is…",
            "gutegereza",
            ["kumanuka", "kugera", "gutura"],
            "Gutegereza is to wait for (Tegereza bisi hano); kumanuka is to get "
            "off, kugera to reach, gutura to live somewhere.",
            item="Tegereza bisi hano.",
        ),
        q(
            "usage",
            "You want to get off the bus politely:",
            "Ndifuza kumanuka hano.",
            ["Hagarara!", "Genda buhoro.", "Ndashaka itike."],
            "Kwifuza is the polite “would like”: ndifuza kumanuka hano — “I'd like "
            "to get off here”.",
            item="Ndifuza kumanuka hano.",
        ),
        q(
            "vocab",
            "“Itike ni amafaranga magana abiri.” — the ticket costs…",
            "200 francs",
            ["2 000 francs", "20 francs", "100 francs"],
            "Magana abiri is “hundreds that are two” — 200; igihumbi would be a "
            "thousand.",
            item="Itike ni amafaranga magana abiri.",
        ),
        q(
            "culture",
            "Kigali buses leave…",
            "when the seats are full",
            [
                "on a strict published timetable",
                "every hour on the hour",
                "only when police wave them off",
            ],
            "Buses fill seat by seat and go when full — the conductor calls the "
            "destination out the window; answer with a hand signal.",
        ),
    ],
}

A2_U1_L4 = {
    "title": "Yesterday and tomorrow — past and future",
    "grammar_md": """## Moving through time: -a- and -za-

**The near future — -za-** slots between subject prefix and stem:

| | kujya (go) | kugaruka (return) |
|---|---|---|
| I | n**za**jya | n**za**garuka |
| you | u**za**jya | u**za**garuka |
| she | a**za**jya | a**za**garuka |
| we | tu**za**jya | tu**za**garuka |

*Nzajya i Kigali ejo.* — “I will go to Kigali tomorrow.”

**The recent past — -a- … -ye**: past marker **-a-** plus a changed ending
(usually **-ye**):

- kujya → **nagiye** (n-a-gi-ye) — I went
- kuza → **naje**, *twaje* — I/we came
- kugura → **naguze** — I bought

The ending change (-ze, -ye, -shye…) follows sound rules you will absorb verb
by verb — learn each past form inside a sentence.

Question word **ryari?** (“when?”): *Uzagaruka ryari?* — “when will you come
back?”""",
    "culture_note": "Umuco: “Buhoro buhoro ni rwo rugendo” — slowly, slowly is the "
    "journey. Rwanda's favourite proverb about progress: steady beats fast, in "
    "travel as in language learning. Say it when someone apologises for slow "
    "progress and watch faces light up.",
    "items": [
        item("Nzajya i Kigali ejo.", "I will go to Kigali tomorrow.", ["transport", "grammar"]),
        item("Nagiye ku isoko ejo hashize.", "I went to the market yesterday.", ["transport", "grammar"]),
        item("Uzagaruka ryari?", "When will you come back?", ["transport"], {4: "R"}),
        item("Twaje kare.", "We came early.", ["transport", "grammar"]),
        item("Azaza nimugoroba.", "She will come in the evening.", ["transport", "grammar"]),
        item("Buhoro buhoro ni rwo rugendo.", "Slowly, slowly is indeed the journey. (proverb)", ["transport", "proverb"]),
    ],
    "quiz": [
        q(
            "grammar",
            "“She will come in the evening” — the future -za-:",
            "Azaza nimugoroba.",
            ["Araza nimugoroba.", "Yaje nimugoroba.", "Azaje nimugoroba."],
            "-za- slots between the subject prefix and stem: a-za-za; araza is "
            "present and yaje is the past “she came”.",
            item="Azaza nimugoroba.",
        ),
        q(
            "grammar",
            "The past of kujya (“to go”) for “I went” is…",
            "nagiye",
            ["nzajya", "ndajya", "najyaga"],
            "The recent past is -a- plus a changed ending: n-a-gi-ye; nzajya is “I "
            "will go” and ndajya “I am going”.",
            item="Nagiye ku isoko ejo hashize.",
        ),
        q(
            "grammar",
            "“We came early” is…",
            "Twaje kare.",
            ["Tuzaza kare.", "Turaza kare.", "Twaza kare."],
            "Kuza in the past: tw-a-je — the -ye/-je ending marks the past, while "
            "tuzaza is future and turaza present.",
            item="Twaje kare.",
        ),
        q(
            "vocab",
            "“When?” is…",
            "ryari",
            ["he", "nde", "iki"],
            "Ryari asks when (Uzagaruka ryari?); he asks where, nde who, iki what.",
            item="Uzagaruka ryari?",
        ),
        q(
            "usage",
            "“Uzagaruka ryari?” asks…",
            "When will you come back?",
            [
                "Where are you going?",
                "When did you come back?",
                "Will you come back soon?",
            ],
            "U-za-garuka is the future “you will return”, so ryari asks for the "
            "future time, not the past.",
            item="Uzagaruka ryari?",
        ),
        q(
            "culture",
            "Someone apologises for their slow progress. The proverb to offer is…",
            "Buhoro buhoro ni rwo rugendo.",
            ["Genda buhoro.", "Umuntu ni abantu.", "Murakaza neza!"],
            "“Slowly, slowly is the journey” — Rwanda's favourite word on progress: "
            "steady beats fast, in travel as in learning.",
            item="Buhoro buhoro ni rwo rugendo.",
        ),
    ],
}

# ---------------------------------------------------------------------------
# A2 — Unit 2 · Market & money
# ---------------------------------------------------------------------------

A2_U2_L1 = {
    "title": "Asking prices",
    "grammar_md": """## Ni angahe? — how much?

The one question that runs every market: **Ni angahe?** — “how much is it?”
(*angahe* agrees with *amafaranga*, “francs”, class 6). Point at something and
ask *Iki ni angahe?* — “how much is THIS?” (*iki* = this thing, class 7).

Money answers come back in hundreds:

| Price | Kinyarwanda |
|---|---|
| 200 RWF | amafaranga **magana abiri** |
| 500 RWF | amafaranga **magana atanu** |
| 1000 RWF | amafaranga **igihumbi** |

Reacting to a price:

- *Birahenze!* — “that's expensive!” (from **guhenda**)
- *Ni bihendutse.* — “it's cheap” (from **guhenduka**)

Quantities use **ikilo**: *Ikilo ry'inyanya ni angahe?* — “how much is a kilo
of tomatoes?” — note the class-5 connector **ry'** before a vowel.""",
    "culture_note": "Umuco: never open with the price. Greet first — Mwaramutse! "
    "Amakuru? — then browse, then ask. A price asked without a greeting starts "
    "high and stays high.",
    "items": [
        item("Ni angahe?", "How much is it?", ["market"], {1: "H", 3: "R"}),
        item("Iki ni angahe?", "How much is this?", ["market"], {2: "H"}),
        item("Ikilo ry'inyanya ni angahe?", "How much is a kilo of tomatoes?", ["market"]),
        item("Ni amafaranga magana atanu.", "It is five hundred francs.", ["market"]),
        item("Birahenze!", "That's expensive!", ["market"], {2: "H"}),
        item("Ni bihendutse.", "It's cheap.", ["market"]),
        item("Mfite amafaranga igihumbi.", "I have one thousand francs.", ["market"]),
    ],
    "quiz": [
        q(
            "vocab",
            "You point at something on the stall and ask “how much is THIS?”:",
            "Iki ni angahe?",
            ["Iki ni iki?", "Ni saa ngahe?", "Iki ni nde?"],
            "Iki is “this thing” (class 7) and ni angahe asks the price; iki ni iki "
            "would ask what it is.",
            item="Iki ni angahe?",
        ),
        q(
            "grammar",
            "“How much is a kilo of tomatoes?” — the class-5 connector:",
            "Ikilo ry'inyanya ni angahe?",
            [
                "Ikilo cy'inyanya ni angahe?",
                "Ikilo by'inyanya ni angahe?",
                "Ikilo z'inyanya ni angahe?",
            ],
            "Ikilo is class 5, so its connector is rya-, contracting to ry' before "
            "the vowel of inyanya.",
            item="Ikilo ry'inyanya ni angahe?",
        ),
        q(
            "vocab",
            "“Birahenze!” means…",
            "That's expensive!",
            ["It's cheap.", "It's delicious.", "That's enough."],
            "From guhenda: birahenze — expensive; the happy opposite is ni "
            "bihendutse, “it's cheap”.",
            item="Birahenze!",
        ),
        q(
            "vocab",
            "500 francs is “amafaranga…”",
            "magana atanu",
            ["magana abiri", "igihumbi", "mirongo itanu"],
            "Magana atanu is five hundreds; magana abiri is 200, igihumbi 1 000 "
            "and mirongo itanu just 50.",
            item="Ni amafaranga magana atanu.",
        ),
        q(
            "usage",
            "The vendor's price is too high. You react:",
            "Birahenze cyane!",
            ["Ni bihendutse.", "Ni byiza cyane.", "Ndabyemeye."],
            "Birahenze cyane (“much too expensive”) opens the bargain; ndabyemeye "
            "would accept the price as-is.",
            item="Birahenze!",
        ),
        q(
            "culture",
            "Before asking a price at the market, you should…",
            "greet the vendor first",
            [
                "name your maximum straight away",
                "inspect the goods in silence",
                "ask another customer what they paid",
            ],
            "Never open with the price: a price asked without a greeting starts "
            "high and stays high.",
        ),
    ],
}

A2_U2_L2 = {
    "title": "Bargaining like a local",
    "grammar_md": """## Kugabanya — bringing the price down

Bargaining is a friendly ritual with its own verbs:

| Verb | Meaning | In action |
|---|---|---|
| **kugabanya** | to reduce | *Gabanya gato.* — lower it a little |
| **kugabanyaho** | to knock some off | *Gabanyaho.* — come down a bit |
| **kongeraho** | to add on | *Ongeraho gato.* — add a little (the vendor's counter) |
| **guha** | to give | *Mpa igiciro cyiza.* — give me a good price |
| **kwemera** | to accept | *Ndabyemeye.* — I accept |

**Mpa** (“give me”) is *m-* (me) + *ha* — the object sits INSIDE the verb.
You'll also hear **Nguhe … ?** — “shall I give you …?” — the subjunctive making
an offer: *Nguhe magana ane?* — “shall I give you four hundred?”

Close warmly: *Ni sawa, ndabyemeye* (“okay, I accept” — *sawa* is a Swahili
loan every Rwandan uses) and promise return custom: *Nzagaruka* — “I'll be
back.” That promise is worth more than the last hundred francs.""",
    "culture_note": "Umuco: bargaining is conversation, not combat. Smile, use the "
    "vendor's greetings, concede something (“sawa, magana atanu”) — and once you "
    "agree, pay without re-opening. Walking away smiling is allowed; scowling is not.",
    "items": [
        item("Gabanya gato.", "Lower it a little.", ["market"]),
        item("Mpa igiciro cyiza.", "Give me a good price.", ["market"]),
        item("Birahenze cyane, gabanyaho.", "It's too expensive, come down a bit.", ["market"]),
        item("Nguhe magana ane?", "Shall I give you four hundred?", ["market"], {4: "R"}),
        item("Ongeraho gato.", "Add a little more.", ["market"]),
        item("Ni sawa, ndabyemeye.", "Okay, I accept.", ["market"]),
        item("Urakoze, nzagaruka.", "Thank you, I will come back.", ["market"]),
    ],
    "quiz": [
        q(
            "grammar",
            "“Mpa” (“give me”) is built from…",
            "m- (me) + ha (give) — the object sits inside the verb",
            [
                "a shortening of the noun impano",
                "mu- (you pl.) + ha (give)",
                "the imperative of gufata",
            ],
            "Kinyarwanda slots object pronouns into the verb: m-pa = give-me, just "
            "as -du- (“us”) hides in mwaduha.",
            item="Mpa igiciro cyiza.",
        ),
        q(
            "vocab",
            "“Gabanya gato” means…",
            "Lower it a little.",
            ["Add a little.", "Wrap it up.", "Weigh it again."],
            "Kugabanya is to reduce — the buyer's opening move; gato softens it to "
            "“a little”.",
            item="Gabanya gato.",
        ),
        q(
            "vocab",
            "The vendor's counter-move “Ongeraho gato” means…",
            "Add a little more.",
            ["Take a little off.", "Come back tomorrow.", "Choose another one."],
            "Kongeraho is to add on — the vendor asks you to come up as you ask "
            "her to come down.",
            item="Ongeraho gato.",
        ),
        q(
            "grammar",
            "“Shall I give you four hundred?” — the subjunctive offer:",
            "Nguhe magana ane?",
            [
                "Mpa magana ane?",
                "Uzampa magana ane?",
                "Ndaguha magana ane.",
            ],
            "The -e subjunctive makes an offer: n-gu-he “shall I give you”; Mpa "
            "asks THEM to give, and ndaguha just states it.",
            item="Nguhe magana ane?",
        ),
        q(
            "usage",
            "You have agreed on a price. You close warmly with…",
            "Ni sawa, ndabyemeye.",
            ["Birahenze cyane.", "Ntacyo nshaka.", "Gabanyaho."],
            "Ni sawa (a Swahili loan every Rwandan uses) plus ndabyemeye — “okay, I "
            "accept” — seals the deal in good spirit.",
            item="Ni sawa, ndabyemeye.",
        ),
        q(
            "culture",
            "Once a market price is agreed, re-opening the bargain is…",
            "bad form — pay, and promise return custom instead",
            [
                "expected exactly once more",
                "fine as long as you smile",
                "required for large amounts",
            ],
            "Bargaining is conversation, not combat — and “Nzagaruka” (I'll be "
            "back) is worth more than the last hundred francs.",
            item="Urakoze, nzagaruka.",
        ),
    ],
}

A2_U2_L3 = {
    "title": "Buying vegetables — imboga",
    "grammar_md": """## At the vegetable stall

| Kinyarwanda | Class | Meaning |
|---|---|---|
| **imboga** | 10 | vegetables |
| **inyanya** | 9/10 | tomato(es) |
| **ibirayi** | 8 | potatoes |
| **ibitoki** | 8 | plantains |
| **amashu** | 6 | cabbage |
| **karoti** | 9/10 | carrots |

Class matters at the stall: *inyanya **zi**ri he?* (“where are the tomatoes?” —
class 10 **zi-**), *ibitoki **bi**rahenze* (“plantains are expensive” — class 8
**bi-**).

Ordering combines what you know:

- *Mpa ibiro bibiri by'ibirayi.* — “give me two kilos of potatoes”
  (**ibiro** = kilos; **by'** connects class 8 to what follows)
- *Ongeramo inyanya eshatu.* — “add in three tomatoes” (-mo = into it)
- *Ni byose, urakoze.* — “that's all, thanks” (**byose** = everything, class 8)""",
    "culture_note": "Umuco: vendors expect you to inspect — squeeze the tomatoes, "
    "lift the plantain hand. A vendor may add an extra tomato after you pay: "
    "that's inyongera, the little bonus for a pleasant customer. Say urakoze.",
    "items": [
        item("Ndashaka imboga.", "I want vegetables.", ["market", "food"]),
        item("Mpa ibiro bibiri by'ibirayi.", "Give me two kilos of potatoes.", ["market"]),
        item("Inyanya ziri he?", "Where are the tomatoes?", ["market"], {5: "R"}),
        item("Ibitoki birahenze uyu munsi.", "Plantains are expensive today.", ["market"]),
        item("Mfite karoti nziza.", "I have nice carrots.", ["market"]),
        item("Ongeramo inyanya eshatu.", "Add in three tomatoes.", ["market"]),
        item("Ni byose, urakoze.", "That's all, thank you.", ["market"]),
    ],
    "quiz": [
        q(
            "vocab",
            "“Tomatoes” are…",
            "inyanya",
            ["ibirayi", "amashu", "ibitoki"],
            "Inyanya are tomatoes; ibirayi potatoes, amashu cabbage, ibitoki "
            "plantains.",
            item="Inyanya ziri he?",
        ),
        q(
            "grammar",
            "“Where are the tomatoes?” — class 10 takes zi-:",
            "Inyanya ziri he?",
            ["Inyanya biri he?", "Inyanya riri he?", "Inyanya bari he?"],
            "Plural inyanya is class 10, whose subject prefix is zi-: inyanya "
            "zi-ri he.",
            item="Inyanya ziri he?",
        ),
        q(
            "grammar",
            "“Give me two kilos of potatoes”:",
            "Mpa ibiro bibiri by'ibirayi.",
            [
                "Mpa ibiro kabiri by'ibirayi.",
                "Mpa ibiro bibiri cy'ibirayi.",
                "Mpa biro bibiri by'ibirayi.",
            ],
            "Ibiro (class 8) takes bibiri and the connector by' — kabiri is only "
            "for counting aloud.",
            item="Mpa ibiro bibiri by'ibirayi.",
        ),
        q(
            "vocab",
            "“Ibitoki birahenze uyu munsi.” means…",
            "Plantains are expensive today.",
            [
                "Plantains are cheap today.",
                "Potatoes are expensive today.",
                "Plantains are fresh today.",
            ],
            "Ibitoki (plantains, class 8) takes bi-: birahenze — “are expensive” — "
            "with uyu munsi, “today”.",
            item="Ibitoki birahenze uyu munsi.",
        ),
        q(
            "usage",
            "You have everything you need and want to finish up:",
            "Ni byose, urakoze.",
            ["Ongeramo inyanya eshatu.", "Mpa igiciro cyiza.", "Ndashaka imboga."],
            "Ni byose — “that's everything” (byose agreeing with class 8) — closes "
            "the purchase; the others keep it going.",
            item="Ni byose, urakoze.",
        ),
        q(
            "culture",
            "The vendor drops an extra tomato in your bag after you pay. That is…",
            "inyongera — the little bonus for a pleasant customer",
            [
                "a mistake you should point out",
                "an invitation to bargain again",
                "a sample you pay for next time",
            ],
            "Inyongera rewards a friendly sale — say urakoze; and do squeeze the "
            "tomatoes first, vendors expect you to inspect.",
        ),
    ],
}

A2_U2_L4 = {
    "title": "Money and big numbers",
    "grammar_md": """## Amafaranga — hundreds and thousands

**Amafaranga** (francs/money) is class 6, so numbers agree with **ma-**:

| Amount | Kinyarwanda |
|---|---|
| 100 | ijana |
| 200 | **magana abiri** (hundreds that are two) |
| 500 | magana atanu |
| 1 000 | **igihumbi** |
| 2 000 | **ibihumbi bibiri** |
| 2 500 | ibihumbi bibiri na magana atanu |

*Ijana* pluralises to **magana**; *igihumbi* (class 7) to **ibihumbi** (class
8) — the noun-class system reaching into arithmetic.

**Having none — nta**: *Nta mafaranga mfite* — “I have no money.” **Nta**
swallows the initial vowel of the next noun (nta **ma**faranga, never nta
amafaranga) and the verb comes without -ra-.

“A little” is **make** for class 6: *Mfite amafaranga make* — “I have little
money” — a bargaining sentence worth its weight in francs.""",
    "culture_note": "Umuco: mobile money (momo) is everywhere — even tiny stalls "
    "take it, and the agent's yellow booth is a village landmark. Cash still "
    "rules the market itself, in well-worn hundred-franc coins.",
    "items": [
        item("Magana abiri", "two hundred", ["market", "numbers"]),
        item("Magana atanu", "five hundred", ["market", "numbers"]),
        item("Igihumbi kimwe", "one thousand", ["market", "numbers"]),
        item("Ibihumbi bibiri na magana atanu", "two thousand five hundred", ["market", "numbers"]),
        item("Nta mafaranga mfite.", "I have no money.", ["market", "grammar"]),
        item("Mfite amafaranga make.", "I have little money.", ["market"]),
        item("Amafaranga y'u Rwanda", "Rwandan francs", ["market"]),
    ],
    "quiz": [
        q(
            "grammar",
            "“2 000” is…",
            "ibihumbi bibiri",
            ["igihumbi bibiri", "ibihumbi kabiri", "magana abiri"],
            "Igihumbi (class 7) pluralises to ibihumbi (class 8), and the number "
            "agrees: bibiri — noun classes reach into arithmetic.",
            item="Ibihumbi bibiri na magana atanu",
        ),
        q(
            "vocab",
            "“Ibihumbi bibiri na magana atanu” is…",
            "2 500 francs",
            ["2 050 francs", "250 francs", "5 200 francs"],
            "Two thousands and five hundreds, joined by na: 2 500.",
            item="Ibihumbi bibiri na magana atanu",
        ),
        q(
            "grammar",
            "“I have no money” — nta swallows the initial vowel:",
            "Nta mafaranga mfite.",
            [
                "Nta amafaranga mfite.",
                "Nta mafaranga ndafite.",
                "Ntabwo amafaranga mfite.",
            ],
            "Nta + noun drops the noun's initial vowel (nta mafaranga) and the "
            "verb follows without -ra-.",
            item="Nta mafaranga mfite.",
        ),
        q(
            "vocab",
            "“Magana atanu” is…",
            "five hundred",
            ["fifty", "five thousand", "four hundred"],
            "Magana are hundreds: atanu makes five of them — 500.",
            item="Magana atanu",
        ),
        q(
            "grammar",
            "“A little money” — “little” agreeing with class 6 ama-:",
            "amafaranga make",
            ["amafaranga gake", "amafaranga bake", "amafaranga hake"],
            "Class 6 takes ma-: make — a bargaining sentence worth its weight in "
            "francs (Mfite amafaranga make).",
            item="Mfite amafaranga make.",
        ),
        q(
            "culture",
            "Mobile money (momo) in Rwanda is…",
            "everywhere — even tiny stalls take it",
            [
                "accepted only in banks",
                "banned inside markets",
                "used only by foreigners",
            ],
            "The agent's yellow booth is a village landmark — though the market "
            "itself still runs on well-worn hundred-franc coins.",
        ),
    ],
}

# ---------------------------------------------------------------------------
# A2 — Unit 3 · Food & eating
# ---------------------------------------------------------------------------

A2_U3_L1 = {
    "title": "Everyday foods",
    "grammar_md": """## Ibiryo — what's on the plate

| Kinyarwanda | Meaning |
|---|---|
| **ibiryo** | food (class 8) |
| **umuceri** | rice |
| **ibishyimbo** | beans — the national staple |
| **ubugari** | cassava/maize paste, eaten by hand |
| **isombe** | pounded cassava leaves |
| **amata** | milk |
| **amazi** | water |
| **ifunguro** | a meal |

Class agreement keeps working at the table: *ibiryo **bi**raryoshye* (“the food
is delicious” — **kuryoha**, to be tasty), *amata ni **meza*** (“milk is good”).

Joining foods uses **na** (“and/with”), which contracts before vowels:
*ubugari **n'**isombe* — ubugari with isombe.

Purpose with **-o ku-**: *amazi **yo kunywa*** — “water for drinking”. Ask what
someone eats with **iki** (“what”): *Urya iki mu gitondo?* — “what do you eat in
the morning?”""",
    "culture_note": "Umuco: ibishyimbo n'ubugari fuel the nation — beans appear at "
    "nearly every meal. Milk has deep cultural prestige from Rwanda's cattle "
    "heritage: offering a guest milk is an honour, and the milk bar (akabari "
    "k'amata) is a Kigali institution.",
    "items": [
        item("Ibishyimbo n'umuceri ni ibiryo byiza.", "Beans and rice are good food.", ["food"]),
        item("Ndya ubugari n'isombe.", "I eat ubugari with isombe.", ["food"]),
        item("Amata ni meza ku bana.", "Milk is good for children.", ["food"]),
        item("Ndashaka amazi yo kunywa.", "I want water to drink.", ["food"]),
        item("Ibiryo biraryoshye.", "The food is delicious.", ["food"]),
        item("Urya iki mu gitondo?", "What do you eat in the morning?", ["food"], {4: "R"}),
    ],
    "quiz": [
        q(
            "vocab",
            "The national staple, beans, is…",
            "ibishyimbo",
            ["ibirayi", "umuceri", "isombe"],
            "Ibishyimbo appear at nearly every meal; ibirayi are potatoes, umuceri "
            "rice and isombe pounded cassava leaves.",
            item="Ibishyimbo n'umuceri ni ibiryo byiza.",
        ),
        q(
            "grammar",
            "“Amazi yo kunywa” means…",
            "water for drinking",
            ["milk for drinking", "water for washing", "cold water"],
            "The -o ku- construction marks purpose: amazi yo kunywa — water "
            "that is for drinking.",
            item="Ndashaka amazi yo kunywa.",
        ),
        q(
            "grammar",
            "“The food is delicious” — class 8 agreement:",
            "Ibiryo biraryoshye.",
            ["Ibiryo riraryoshye.", "Ibiryo araryoshye.", "Ibiryo ziraryoshye."],
            "Ibiryo (class 8) takes bi-: bi-ra-ryoshye, from kuryoha, “to be "
            "tasty”.",
            item="Ibiryo biraryoshye.",
        ),
        q(
            "grammar",
            "“Ubugari with isombe” — na contracts before a vowel:",
            "ubugari n'isombe",
            ["ubugari na isombe", "ubugari ni isombe", "ubugari no isombe"],
            "Na (“and/with”) becomes n' before a vowel: n'isombe — ni would say "
            "“is”, and no is the contraction before infinitives.",
            item="Ndya ubugari n'isombe.",
        ),
        q(
            "usage",
            "To ask what someone eats in the morning:",
            "Urya iki mu gitondo?",
            ["Urya nde mu gitondo?", "Unywa he mu gitondo?", "Urya ryari?"],
            "Iki asks “what”; nde would ask WHO you eat — a mix-up worth avoiding "
            "at breakfast.",
            item="Urya iki mu gitondo?",
        ),
        q(
            "culture",
            "Offering a guest milk in Rwanda is…",
            "an honour rooted in the country's cattle heritage",
            [
                "an everyday afterthought",
                "reserved for children",
                "a hint that the visit is over",
            ],
            "Milk carries deep prestige — the milk bar (akabari k'amata) is a "
            "Kigali institution.",
            item="Amata ni meza ku bana.",
        ),
    ],
}

A2_U3_L2 = {
    "title": "Eating and drinking — kurya no kunywa",
    "grammar_md": """## Two short, mighty verbs

**kurya** (to eat) and **kunywa** (to drink) are short-stem verbs:

| | kurya | kunywa |
|---|---|---|
| I | **ndya** | **nywa** / ndanywa |
| you | urya | unywa |
| he/she | arya | anywa |
| we | turya | tunywa |
| they | barya | banywa |

With -ra- (verb-final): *Ndarya.* — “I'm eating.” *Ndanywa icyayi* keeps -ra-
before a short object in everyday speech: “I'm drinking tea.”

**Wanting + infinitive**: *ndashaka* (I want) or the politer *ndifuza* (I'd
like) + **ku-** verb:

- *Ndashaka **kurya**.* — I want to eat.
- *Urashaka **kunywa** iki?* — what would you like to drink?

Habits drop -ra- and love **buri**: *Arya umuceri buri munsi* — “he eats rice
every day”; times slot in directly: *Turya saa sita* — “we eat at noon.”""",
    "culture_note": "Umuco: meals are shared — arriving during one gets you a plate, "
    "and refusing everything can wound. Wash hands before ubugari (it's eaten by "
    "hand), and try a little of everything offered.",
    "items": [
        item("Ndashaka kurya.", "I want to eat.", ["food"]),
        item("Urashaka kunywa iki?", "What would you like to drink?", ["food"], {6: "R"}),
        item("Ndanywa icyayi.", "I am drinking tea.", ["food"]),
        item("Turya saa sita.", "We eat at noon.", ["food"]),
        item("Arya umuceri buri munsi.", "He eats rice every day.", ["food"]),
        item("Mfite inzara.", "I am hungry.", ["food"]),
        item("Mfite inyota.", "I am thirsty.", ["food"]),
    ],
    "quiz": [
        q(
            "grammar",
            "“I am eating” — the verb ends the sentence, so…",
            "Ndarya.",
            ["Ndya.", "Ndarye.", "Kurya."],
            "Verb-final present takes -ra-: nda-rya “I am eating”; plain ndya is "
            "the habitual/linked form.",
        ),
        q(
            "grammar",
            "“He eats rice every day” — a habit drops -ra-:",
            "Arya umuceri buri munsi.",
            [
                "Ararya umuceri buri munsi.",
                "Arye umuceri buri munsi.",
                "Azarya umuceri buri munsi.",
            ],
            "Habits take the plain form with buri munsi: arya — ararya is “he is "
            "eating right now” and azarya the future.",
            item="Arya umuceri buri munsi.",
        ),
        q(
            "vocab",
            "“I am thirsty” is…",
            "Mfite inyota.",
            ["Mfite inzara.", "Mfite inyoni.", "Mfite amazi."],
            "Thirst is possessed: mfite inyota; mfite inzara is “I'm hungry” and "
            "inyoni is a bird.",
            item="Mfite inyota.",
        ),
        q(
            "usage",
            "Your host asks “Urashaka kunywa iki?”. They want to know…",
            "what you would like to drink",
            [
                "whether you are hungry",
                "what you would like to eat",
                "when you will drink",
            ],
            "Kunywa is to drink and iki asks what — kurya would make it about "
            "food.",
            item="Urashaka kunywa iki?",
        ),
        q(
            "grammar",
            "“I want to eat” — want + infinitive:",
            "Ndashaka kurya.",
            ["Ndashaka ndya.", "Ndashaka rya.", "Ndashaka kurye."],
            "After ndashaka comes the full ku- infinitive: kurya — not a "
            "conjugated or subjunctive form.",
            item="Ndashaka kurya.",
        ),
        q(
            "culture",
            "You arrive at a Rwandan home during a meal. Expect…",
            "a plate — meals are shared",
            [
                "to wait outside until it ends",
                "to be asked to come back later",
                "to be served only a drink",
            ],
            "Arriving during a meal gets you a plate; wash hands before ubugari — "
            "it is eaten by hand — and try a little of everything.",
        ),
    ],
}

A2_U3_L3 = {
    "title": "At the restaurant",
    "grammar_md": """## Kwishyura — ordering and paying

Restaurant Kinyarwanda runs on polite requests. The conditional **wa-/mwa-**
softens an imperative into “could you…”:

- *Mwaduha urutonde rw'ibiryo?* — “could you give us the menu?”
  (mu-a-du-ha: you(pl)-would-us-give — the object **-du-** sits inside the verb)
- *Tuzanire amazi.* — “bring us water” (**kuzanira** = bring for)

Stating your order politely uses **ndifuza**: *Ndifuza inyama n'ibirayi* — “I'd
like meat and potatoes.”

The bill: **kwishyura** (to pay) — *Ndifuza kwishyura* — and the total question
you already own from the market: *Ni angahe byose?* — “how much is everything?”
(**byose** = all of it, class 8 agreeing with *ibiryo*).

A buffet is a **melange** (from French) — pile the plate once, pay one price.""",
    "culture_note": "Umuco: lunchtime melange is Rwanda's working meal — one plate, "
    "one pass, no hurry. Water arrives in a shared bottle; drinks are often "
    "ordered by brand. Tipping is appreciated, not expected — rounding up is plenty.",
    "items": [
        item("Mwaduha urutonde rw'ibiryo?", "Could you give us the menu?", ["food"], {8: "R"}),
        item("Ndifuza inyama n'ibirayi.", "I'd like meat and potatoes.", ["food"]),
        item("Tuzanire amazi.", "Bring us water, please.", ["food"]),
        item("Ni angahe byose?", "How much is everything?", ["food", "market"], {5: "R"}),
        item("Ndifuza kwishyura.", "I would like to pay.", ["food"]),
        item("Ifunguro ryari ryiza cyane.", "The meal was very good.", ["food"]),
    ],
    "quiz": [
        q(
            "grammar",
            "“Could you (pl.) give us the menu?” — the polite conditional:",
            "Mwaduha urutonde rw'ibiryo?",
            [
                "Muduha urutonde rw'ibiryo.",
                "Duha urutonde rw'ibiryo.",
                "Mwaduhe urutonde rw'ibiryo!",
            ],
            "Mwa- is “you (pl.) would” and the object -du- (“us”) sits inside the "
            "verb: mu-a-du-ha.",
            item="Mwaduha urutonde rw'ibiryo?",
        ),
        q(
            "vocab",
            "“To pay” is…",
            "kwishyura",
            ["kwifuza", "kuzanira", "kugura"],
            "Kwishyura settles the bill (Ndifuza kwishyura); kwifuza is to wish, "
            "kuzanira to bring for, kugura to buy.",
            item="Ndifuza kwishyura.",
        ),
        q(
            "usage",
            "Stating your order politely:",
            "Ndifuza inyama n'ibirayi.",
            ["Mpa inyama!", "Inyama, vuba!", "Ndashaka kwishyura."],
            "Ndifuza (“I'd like”) is the polite want — a bare Mpa! belongs to the "
            "market bargain, not the table.",
            item="Ndifuza inyama n'ibirayi.",
        ),
        q(
            "usage",
            "Asking for the total at the end of the meal:",
            "Ni angahe byose?",
            ["Ni byose, urakoze.", "Ni saa ngahe?", "Mwaduha byose?"],
            "Byose (“all of it”, class 8) turns the market question into “how much "
            "is everything?”.",
            item="Ni angahe byose?",
        ),
        q(
            "grammar",
            "“Bring us water” — kuzanira (“bring for”) with -us- inside:",
            "Tuzanire amazi.",
            ["Tuzanira amazi.", "Zanire amazi.", "Tuzana amazi."],
            "Tu- (“us”) slots into the verb and the final -e marks the polite "
            "command: tu-zanir-e.",
            item="Tuzanire amazi.",
        ),
        q(
            "culture",
            "A lunchtime “melange” is…",
            "one plate piled once at the buffet, for one price",
            [
                "a mixed fruit drink",
                "the restaurant's daily soup",
                "a shared platter for the table",
            ],
            "The melange is Rwanda's working meal — one pass, one price, no hurry; "
            "tipping is appreciated but rounding up is plenty.",
        ),
    ],
}

A2_U3_L4 = {
    "title": "Likes, dislikes and saying no",
    "grammar_md": """## Gukunda and the art of negation

**Liking — gukunda**: *Nkunda ibitoki* — “I like plantains”; compare with
**kuruta**: *Nkunda icyayi **kuruta** ikawa* — “I like tea MORE THAN coffee.”

**Negation** has two shapes:

1. **First person singular: si-** — *Nkunda → **Si**nkunda* (“I don't like”),
   *nywa → **si**nywa* (“I don't drink”).
2. **Everything else: nti-** before the subject prefix — *urya → **nti**wurya?*
   *barya → **nti**barya* (“they don't eat”).

The heavier **ntabwo** + verb is an emphatic, very common alternative:
*Ntabwo ndya inyama.* — “I don't eat meat.”

**Refusing food politely** pairs a negative with thanks: *Ntacyo nshaka,
urakoze* — “I don't want anything, thank you” (**ntacyo** = “no thing”). Add
*ndahaze* — “I'm full” — and no host is offended.""",
    "culture_note": "Umuco: a flat “no” to offered food is harsh; Rwandans refuse "
    "with softeners — urakoze, ndahaze (thank you, I'm full) — or accept a "
    "symbolic taste. Vegetarianism is understood best as “simfite umuco wo kurya "
    "inyama” — framing it as your custom, which everyone respects.",
    "items": [
        item("Nkunda ibitoki.", "I like plantains.", ["food"]),
        item("Sinkunda urusenda.", "I don't like hot pepper.", ["food", "grammar"]),
        item("Ukunda kurya iki?", "What do you like to eat?", ["food"], {5: "R"}),
        item("Ntabwo ndya inyama.", "I don't eat meat.", ["food", "grammar"]),
        item("Nkunda icyayi kuruta ikawa.", "I like tea more than coffee.", ["food"]),
        item("Ntacyo nshaka, urakoze.", "I don't want anything, thank you.", ["food"]),
    ],
    "quiz": [
        q(
            "grammar",
            "“I don't like” — the first-person negative si-:",
            "Sinkunda",
            ["Ntinkunda", "Sikunda", "Ntikunda"],
            "First person singular negates with si- and keeps its n-: si-n-kunda; "
            "nti- belongs to every other person.",
            item="Sinkunda urusenda.",
        ),
        q(
            "grammar",
            "“They don't eat” is…",
            "ntibarya",
            ["sibarya", "ntibarye", "ntabarya"],
            "Other persons negate with nti- before the subject prefix: nti-ba-rya; "
            "-rye would be the subjunctive ending.",
            item="Ntabwo ndya inyama.",
        ),
        q(
            "vocab",
            "“Nkunda icyayi kuruta ikawa.” means…",
            "I like tea more than coffee.",
            [
                "I like coffee more than tea.",
                "I drink tea instead of coffee.",
                "I like tea and coffee equally.",
            ],
            "Kuruta makes the comparison “more than”, ranking what comes before it "
            "(icyayi) above what follows (ikawa).",
            item="Nkunda icyayi kuruta ikawa.",
        ),
        q(
            "usage",
            "To refuse more food without offending your host:",
            "Urakoze, ndahaze.",
            ["Ntabwo ndya.", "Sinkunda ibiryo byawe.", "Genda, ndahaze."],
            "Pair thanks with “I'm full” — urakoze, ndahaze — and no host is "
            "offended; a flat refusal wounds.",
            item="Ntacyo nshaka, urakoze.",
        ),
        q(
            "vocab",
            "“Ntacyo nshaka” means…",
            "I don't want anything",
            ["I want everything", "I don't like this one", "I can't find it"],
            "Ntacyo is “no thing”: ntacyo nshaka — softened with urakoze when "
            "declining an offer.",
            item="Ntacyo nshaka, urakoze.",
        ),
        q(
            "culture",
            "The best-understood way to explain being vegetarian:",
            "“Simfite umuco wo kurya inyama” — framing it as your custom",
            [
                "declaring meat unhealthy",
                "refusing dishes silently",
                "accepting meat and leaving it",
            ],
            "Framing it as your umuco (custom) is respected by everyone — customs "
            "are understood where preferences may puzzle.",
        ),
    ],
}

# ---------------------------------------------------------------------------
# Can-do statements
# ---------------------------------------------------------------------------

A1_CANDOS = [
    ("speak", "Can greet and take leave at any time of day, with the right respect forms"),
    ("speak", "Can introduce themselves: name, where they live and where they come from"),
    ("speak", "Can ask and answer “how are you?” and keep the exchange going"),
    ("speak", "Can present their family and say how many siblings or children they have"),
    ("speak", "Can count to one hundred and say their age"),
    ("speak", "Can say the day of the week and place events today, yesterday and tomorrow"),
    ("listen", "Can understand slow, clear greetings and simple personal questions"),
    ("listen", "Can catch clock times and parts of the day in slow speech"),
    ("read", "Can read short familiar phrases about people, family and home"),
    ("write", "Can write their name, origin and simple sentences about their family"),
]

A2_CANDOS = [
    ("speak", "Can ask prices and bargain simply at a market"),
    ("speak", "Can hail a moto, state a destination and agree a fare"),
    ("speak", "Can ask for and give simple directions in the street"),
    ("speak", "Can order food and drink and settle the bill in a simple restaurant"),
    ("speak", "Can express likes, dislikes and polite refusals"),
    ("speak", "Can talk about past and future journeys in simple sentences"),
    ("listen", "Can understand prices, quantities and simple directions"),
    ("listen", "Can follow a short, clear market exchange between two speakers"),
    ("read", "Can read simple signs, menus and price labels"),
    ("write", "Can write short messages about plans and errands"),
]

# ---------------------------------------------------------------------------
# Course assembly
# ---------------------------------------------------------------------------

COURSE_KIN = {
    "code": "KIN",
    "name": "Ikinyarwanda",
    "levels": [
        {
            "cefr": "A1",
            "title": "Breakthrough — first words that work",
            "ord": 1,
            "candos": A1_CANDOS,
            "units": [
                {
                    "title": "Greetings & people",
                    "situation_tag": "greetings",
                    "ord": 1,
                    "lessons": [A1_U1_L1, A1_U1_L2, A1_U1_L3, A1_U1_L4],
                },
                {
                    "title": "Family & home",
                    "situation_tag": "family",
                    "ord": 2,
                    "lessons": [A1_U2_L1, A1_U2_L2, A1_U2_L3, A1_U2_L4],
                },
                {
                    "title": "Numbers & time",
                    "situation_tag": "numbers",
                    "ord": 3,
                    "lessons": [A1_U3_L1, A1_U3_L2, A1_U3_L3, A1_U3_L4],
                },
            ],
        },
        {
            "cefr": "A2",
            "title": "Waystage — out in the city",
            "ord": 2,
            "candos": A2_CANDOS,
            "units": [
                {
                    "title": "Getting around",
                    "situation_tag": "transport",
                    "ord": 1,
                    "lessons": [A2_U1_L1, A2_U1_L2, A2_U1_L3, A2_U1_L4],
                },
                {
                    "title": "Market & money",
                    "situation_tag": "market",
                    "ord": 2,
                    "lessons": [A2_U2_L1, A2_U2_L2, A2_U2_L3, A2_U2_L4],
                },
                {
                    "title": "Food & eating",
                    "situation_tag": "food",
                    "ord": 3,
                    "lessons": [A2_U3_L1, A2_U3_L2, A2_U3_L3, A2_U3_L4],
                },
            ],
        },
    ],
}

# ---------------------------------------------------------------------------
# Quiz index — (cefr, unit ord, lesson ord) -> authored quiz questions.
# Quizzes are curriculum content that lives here (not in a DB column); the
# roadmap service joins them to DB lessons by position at serialization time.
# ---------------------------------------------------------------------------


def _quiz_index() -> dict[tuple[str, int, int], list[dict]]:
    idx: dict[tuple[str, int, int], list[dict]] = {}
    for level in COURSE_KIN["levels"]:
        for unit in level["units"]:
            for lesson_ord, lesson in enumerate(unit["lessons"], start=1):
                quiz = lesson.get("quiz")
                if quiz:
                    idx[(level["cefr"], unit["ord"], lesson_ord)] = quiz
    return idx


KIN_QUIZZES = _quiz_index()
