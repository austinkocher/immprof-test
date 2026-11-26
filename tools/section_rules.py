"""A first sort of a post into one of the sixteen sections, from its title and opening text.

It follows the editors' rules in order: kind of post first (job, conference or call, book, scholarship, report or data,
creative work, person), then subject (elections, lawsuits, immigration courts, legislation, international, enforcement,
policy), then News. It is a starting point for posts nobody has read: tools/import_posts.py uses it only for a post
that is not in the hand-sorted list. Score it against that list with:  python3 tools/section_rules.py --score
"""
import csv, json, os, re, sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T = lambda pat: re.compile(pat, re.I)

# (section, pattern on the TITLE, pattern on title + opening text). Either may be None. First match wins.
RULES = [
    ("Books", T(r"from the bookshelves|^\s*new book\b|\bbook (review|talk|launch)\b|\bnew books?\b"), None),
    ("Scholarship", T(r"article of the day|immigration article|law review|\bssrn\b|symposium issue|special (edition|issue) of the journal|\bjournal\b.*(issue|volume)|new (paper|article|scholarship)|working paper"), None),
    ("Jobs", T(r"\b(position|opening|vacanc|hiring|fellowship|job|faculty search|is hiring|positions?) ?(open|announce|available)?\b.*|\bseeks?\b.*(attorney|professor|director|fellow)|\b(attorney|staff attorney|professor|director|fellow|clinical) (position|opening)|teaching fellow|\bhiring\b"), None),
    ("Conferences and Calls", T(r"call for (papers|proposals|submissions|abstracts|nominations|applications)|\bcfp\b|\bconference\b|\bsymposium\b|\bwebinar\b|\bworkshop\b|\blecture\b|save the date|register (now|today)|\bpanel (discussion)?\b|upcoming event|\bcolloquium\b|\bsummit\b|virtual event|book talk"), None),
    ("Creative Works", T(r"at the movies|\bfilm\b|\bdocumentary\b|\bmovie\b|\bphoto(graph)?s?\b|\bart(ist|work)?\b|\bmusic\b|\bsong\b|\balbum\b|\bgrammy\b|\bpoe(m|try)\b|\bnovel\b|\btheat(er|re)\b|\bpodcast\b|\bexhibit"), None),
    ("People", T(r"immigrant of the day|in memoriam|\brip\b|\bobituary\b|remembering\b|passes away|\bdies at\b|congratulations|\bhonou?red\b|\baward(ed|s)?\b|\bnamed (dean|president|director|chair)|\bappointed\b|\bretire(s|ment)\b|\bprofile:"), None),
    ("Research and Data", T(r"\breport\b|\bstudy\b|\bsurvey\b|\bpoll\b|\bdata\b|\bstatistics\b|\btracker\b|\bfact sheet\b|by the numbers|\banalysis\b|\bbrief(ing)?\b:|new research|research (shows|finds)|pew research|migration policy institute|\bmpi\b|\bgao\b|inspector general|\bcato\b|american immigration council"), None),
    ("Elections", T(r"\belection|\bmidterm|\bvoters?\b|\bballot\b|\bcampaign\b|\bprimary\b|\bcandidate|\bpolling\b|blue wave|red wave|\bswing (state|voters?)|\bnoncitizen voting|\bturnout\b"), None),
    ("Immigration Courts", T(r"immigration (judge|court)|\beoir\b|board of immigration appeals|\bbia\b|deportation judges?|court backlog|immigration bench"), None),
    ("Lawsuits", T(r"\bscotus\b|supreme court|\bcircuit\b|district court|\bjudge (blocks|rules|orders|halts|grants|denies)|\blawsuit|\bsues?\b|\bsuing\b|\binjunction|\bruling\b|\brules\b|court (blocks|rules|orders|upholds|strikes|rejects|allows|says)|\bclass action|\bplaintiffs?\b|\bhabeas\b|\bcert(iorari)?\b|oral argument|\bappeals court|\bindict|\bcharged with|\bverdict\b|\bsettlement\b|\btro\b|\bv\.\s"), None),
    ("Legislation", T(r"\bbill\b|\bcongress(ional)?\b|\bsenate\b|\bhouse (passes|votes|republicans|democrats|committee)|\blegislat|\bhearing\b|\bact of 20\d\d|\bdream act\b|\bstate (law|lawmakers|legislature)|\bfilibuster|\breconciliation\b|\bappropriations?\b|\bsenators?\b|\bcaucus\b"), None),
    ("International", T(r"\buk\b|united kingdom|\bbritain|\beurop|\beu\b|\bcanad|\bmexico('s)? (president|government|city)|\baustralia|\bgerman|\bfrance|\bfrench\b|\bitaly|\bspain\b(?!.*heading)|\bgreece|mediterranean|\batlantic\b|\bchannel crossing|\bdjibouti|\blibya|\bsudan|\bbrazil|\bjapan|\bindia('s)?\b|\bchina('s)?\b|\bunhcr\b|\bglobal\b|\bworldwide\b|\bun (refugee|migration)"), None),
    ("Enforcement", T(r"\bice\b|\bcbp\b|border patrol|\barrest|\braid|\bdetain|\bdetention|\bdeport|\bremoval|\bcustody\b|\bagents?\b|\bofficers?\b|\b287\(g\)|\bcheckpoint|\bsweep|\bcrackdown|\bshot\b|\bkilled\b|\bdies in\b|\bdeath(s)? in\b|pepper[- ]spray|\btear gas|national guard|\bmasked\b|\babuse|use of force|\bdetainee"), None),
    ("Policy", T(r"white house|\bdhs\b|\buscis\b|state department|\bdoj\b|justice department|attorney general|\bexecutive order|\bproclamation\b|\bmemo\b|\brule\b|\bregulation|\btps\b|\bdaca\b|\bparole\b|\bvisa|\basylum\b|\brefugee (cap|admissions|ceiling)|\btravel ban|\bh-1b\b|\bgreen card|\bnaturalization|\bcitizenship\b|\bsecretary\b|administration (ends|announces|moves|plans|to)|\btrump (ends|orders|signs|announces|says|plans|to)\b|\bpublic charge"), None),
]
# Text rules, used only when no title rule matched: the opening words decide.
TEXT_RULES = [
    ("Scholarship", T(r"here'?s the abstract|\babstract:|forthcoming in|law review|\bssrn\b")),
    ("Books", T(r"new book|university press|\b(his|her|their) (new|latest) book")),
    ("Research and Data", T(r"(a|the) (new )?report (from|by|finds|shows)|has published a (new )?report|new (data|study|survey|poll)|according to (a|the) (new )?(report|study|data|analysis)")),
    ("Lawsuits", T(r"supreme court|federal (judge|court)|\bcircuit\b|lawsuit|injunction|district court")),
    ("Elections", T(r"\belection|\bvoters?\b|\bmidterm")),
    ("Legislation", T(r"\bcongress\b|\bsenate\b|\bbill\b|lawmakers")),
    ("Enforcement", T(r"\bice\b|immigration (agents|officers|enforcement)|\bdetain|\bdeport|\barrest")),
    ("Policy", T(r"white house|\bdhs\b|administration|\buscis\b|state department")),
]


def section_for(title, text=""):
    for sec, on_title, _ in RULES:
        if on_title and on_title.search(title):
            return sec
    opening = text[:500]
    for sec, pat in TEXT_RULES:
        if pat.search(opening):
            return sec
    return "News"


def main():
    posts = {p["slug"] + ".html": p for p in json.load(open(os.path.join(HERE, "_import", "ghost-export-posts.json")))}
    rows = list(csv.DictReader(open(os.path.join(os.path.dirname(HERE), "analysis", "sections-final-2026-11-26.csv"))))
    strip = lambda h: re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", h))
    ok = sure_ok = sure_n = second = 0
    miss = {}
    for r in rows:
        p = posts.get(r["file"])
        if not p:
            continue
        got = section_for(p["title"], strip(p["body"]))
        hit = got == r["section"]
        ok += hit
        second += (not hit) and got == r["second_choice"]
        if r["sure"] == "yes":
            sure_n += 1; sure_ok += hit
        if not hit:
            miss[(r["section"], got)] = miss.get((r["section"], got), 0) + 1
    print(f"agrees with the hand sort on {ok} of {len(rows)} ({100*ok//len(rows)}%); on the posts the reader was sure of, {sure_ok} of {sure_n} ({100*sure_ok//max(1,sure_n)}%); a further {second} match the reader's second choice")
    for (want, got), n in sorted(miss.items(), key=lambda x: -x[1])[:14]:
        print(f"  {n:3d}  hand: {want:22s} rules: {got}")


if __name__ == "__main__":
    if "--score" in sys.argv:
        main()
