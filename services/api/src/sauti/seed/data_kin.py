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
