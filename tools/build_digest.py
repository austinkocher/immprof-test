"""Build the ImmigrationProf Blog digest emails from the site's posts.

Daily:   python3 tools/build_digest.py daily  --date 2026-11-24 --out ../email
         Every post published on that date (midnight to midnight, US Eastern), grouped by section in the site's section order.
         With no posts on that date it writes nothing and says so, so no empty email is sent.
Weekly:  python3 tools/build_digest.py weekly --end 2026-11-22 --ranking most-read.txt --out ../email
         Ten posts from the seven days ending on that date, in the order given by the ranking file: one post address or slug
         per line, most read first, as exported from the traffic tool. Without --ranking it takes --sample, which picks ten
         posts from the week in a fixed order so the design can be shown before a traffic tool exists. A sample is not a ranking.

Notices: python3 tools/build_digest.py notices --out ../email
         The three short emails around signing up and leaving (confirm your address, welcome, unsubscribed), and a text
         file with the wording of the web pages a reader lands on at each step.

Decisions (Austin, November 26, 2026): about three lines of each post; newest first inside a section; no pictures; the
subject line leads with the top headline; a one-post day still sends; the footer has a Support ImmigrationProf link; the weekly
goes out on Sunday morning. An email cannot adjust times to the reader's zone the way the site does, so times are marked ET.

Each run writes an HTML file and a plain-text file. Addresses for the reader's own links are passed in, so the same
template works with any sending service: --unsubscribe, --manage and --web (the email's page on the web).
--site is the public address of the blog, and --assets is where the two pictures are (the header and the Relevant Research logo).

The summary under each title is the opening of the post's own text, with a repeated headline removed, cut at a word.
The email uses tables and inline styles, which every mail program reads, and typefaces every device has (Georgia and Arial).
"""
import argparse, glob, html, os, random, re, sys
from datetime import datetime, timedelta, date
from zoneinfo import ZoneInfo

import json

try:
    import yaml
except ImportError:      # the builder also runs on a plain Python with nothing installed
    yaml = None

ET = ZoneInfo("America/New_York")
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

INK, ACCENT, META, BAND, BG, TINT = "#241f1a", "#8c1d18", "#62574a", "#f7f1e5", "#fafaf8", "#f1efe9"
HAIR = "rgba(36,31,26,.16)"
SERIF = "Georgia,'Times New Roman',serif"
SANS = "Arial,Helvetica,sans-serif"
NUMBER_WORDS = ["No", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine", "Ten", "Eleven", "Twelve"]


def norm(t):
    return re.sub(r"[^a-z0-9]+", " ", t.lower()).strip()


def summary(title, body, limit=230):
    """The opening of the post: paragraphs and list items, a repeated title removed, cut at a word."""
    body = re.sub(r"\{\{<[^>]*>\}\}", "", body)
    pieces = []
    for m in re.finditer(r"(?s)<(p|li)[^>]*>(.*?)</\1>", body):
        t = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", m.group(2)))).strip()
        t = re.sub(r"\s+([.,;:!?])", r"\1", t)   # removing a link's tags leaves a space before the punctuation after it
        if not t:
            continue
        if not pieces:
            nt, nn = norm(title), norm(t)
            if nn and nn in nt:
                continue
            if nn.startswith(nt) and len(nn) > len(nt):
                words, acc = t.split(" "), ""
                for i, w in enumerate(words[:60]):
                    acc = norm(acc + " " + w)
                    if acc == nt:
                        t = " ".join(words[i + 1:]).strip()
                        break
        if t:
            pieces.append(t)
    if not pieces:
        t = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", body))).strip()
        pieces = [t] if t else []
    text = " ".join(pieces)
    if len(text) <= limit:
        return text, False
    cut = text[:limit].rsplit(" ", 1)[0].rstrip(",;:")
    return cut, True


def front_matter(text):
    """The fields at the top of a post file. Uses PyYAML when it is installed. Otherwise reads the simple form the site's own
    tools write: one "key: value" per line, where the value is a quoted string, a list of quoted strings, true or false."""
    if yaml:
        return yaml.safe_load(text) or {}
    out = {}
    for line in text.splitlines():
        m = re.match(r"^([A-Za-z_]+):\s*(.*)$", line)
        if not m:
            continue
        key, val = m.group(1), m.group(2).strip()
        if not val:
            continue
        try:
            out[key] = json.loads(val)
        except ValueError:
            out[key] = val
    return out


def load_posts(site):
    posts = []
    for f in glob.glob(os.path.join(site, "content", "posts", "*")):
        text = open(f, encoding="utf-8").read()
        _, fm, body = text.split("---\n", 2)
        fm = front_matter(fm)
        when = fm["date"] if isinstance(fm["date"], datetime) else datetime.fromisoformat(str(fm["date"]))
        when = when.astimezone(ET)
        slug = fm.get("slug") or os.path.splitext(os.path.basename(f))[0]
        s, cut = summary(fm["title"], body)
        guest = (fm.get("contributors") or [None])[0]
        posts.append(dict(slug=slug, title=re.sub(r"\s+", " ", fm["title"]).strip(), when=when, section=(fm.get("sections") or [""])[0],
                          author=guest or (fm.get("authors") or [""])[0], guest=bool(guest),
                          summary=s, cut=cut, path=(fm.get("url") or "/%s/" % slug)))
    return sorted(posts, key=lambda p: p["when"], reverse=True)


def section_order(site):
    text = open(os.path.join(site, "data", "sections.yaml"), encoding="utf-8").read()
    return re.findall(r"(?m)^-\s*name:\s*(.+?)\s*$", text)


def esc(t):
    return html.escape(t, quote=True)


def clock(d):
    return d.strftime("%I:%M %p").lstrip("0")


def longdate(d):
    return "%s, %s %d, %d" % (d.strftime("%A"), d.strftime("%B"), d.day, d.year)


def page(kind, dateline, lead, blocks, preheader, a, footer="reader"):
    """The whole email. blocks is the HTML of the rows between the header and the footer.
    footer "reader" has the reader's links (change, unsubscribe, read on the web); "plain" is for the emails sent to
    someone who is not on the list yet or has just left it."""
    links = f"""You are receiving this because you signed up at <a href="{a.site}/" style="color:{META};">immprof.com</a>.<br>
<a href="{a.manage}" style="color:{ACCENT};">Change between daily and weekly</a> &nbsp;&nbsp; <a href="{a.unsubscribe}" style="color:{ACCENT};">Unsubscribe</a> &nbsp;&nbsp; <a href="{a.web}" style="color:{ACCENT};">Read this on the web</a> &nbsp;&nbsp; <a href="{a.support}" style="color:{ACCENT};">Support ImmigrationProf</a>""" if footer == "reader" else f"""ImmigrationProf Blog, <a href="{a.site}/" style="color:{META};">immprof.com</a>. News, policy, law and research on immigration, from law professors, since 2005."""
    dl = f'<span style="font-weight:normal;color:{META};">&nbsp;&nbsp;&nbsp;{esc(dateline)}</span>' if dateline else ""
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light only">
<title>ImmigrationProf Blog, {esc(kind.lower())}</title>
<style>
@media (max-width:620px){{.w{{width:100%!important}}.p{{padding-left:20px!important;padding-right:20px!important}}.t{{font-size:19px!important}}}}
</style>
</head>
<body style="margin:0;padding:0;background:{BG};">
<div style="display:none;max-height:0;overflow:hidden;font-size:1px;line-height:1px;color:{BG};">{esc(preheader)}</div>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" bgcolor="{BG}" style="background:{BG};">
<tr><td align="center" style="padding:0;">
<table role="presentation" class="w" width="600" cellpadding="0" cellspacing="0" border="0" style="width:600px;">
<tr><td bgcolor="{BAND}" style="padding:0;background:{BAND};"><a href="{a.site}/" style="text-decoration:none;"><img src="{a.assets}email-header.png" width="600" alt="ImmigrationProf Blog, since 2005" style="display:block;width:100%;height:auto;border:0;"></a></td></tr>
<tr><td class="p" bgcolor="{BAND}" style="padding:0 32px 20px;background:{BAND};font:bold 14px {SANS};color:{INK};">{esc(kind)}{dl}</td></tr>
{f'<tr><td class="p" style="padding:26px 32px 4px;font:16px/1.5 {SERIF};color:{META};">{esc(lead)}</td></tr>' if lead else ''}
{blocks}
<tr><td class="p" bgcolor="{TINT}" style="padding:24px 32px 8px;background:{TINT};font:13px/1.6 {SANS};color:{META};">
{links}
</td></tr>
<tr><td class="p" bgcolor="{TINT}" align="center" style="padding:18px 32px 30px;background:{TINT};font:13px/1.6 {SANS};color:{META};">
<a href="https://relevant-research.com" style="text-decoration:none;"><img src="{a.assets}rrlogo.png" width="124" alt="Relevant Research" style="display:block;width:124px;height:auto;border:0;margin:0 auto 8px;"></a>
This project is powered by <a href="https://relevant-research.com" style="color:{META};">Relevant Research</a>.
</td></tr>
</table>
</td></tr>
</table>
</body>
</html>
"""


def item(p, a, meta, number=None):
    tail = f'<span style="color:{ACCENT};font-weight:bold;">&hellip;</span> ' if p["cut"] else " "
    url = a.site + p["path"]
    text = f"""<a class="t" href="{url}" style="font:bold 20px/1.25 {SERIF};color:{INK};text-decoration:none;">{esc(p['title'])}</a>
<div style="font:15px/1.5 {SERIF};color:{META};margin-top:6px;">{esc(p['summary'])}{tail}<a href="{url}" style="color:{ACCENT};font-style:italic;">continue reading</a></div>
<div style="font:12px/1.4 {SANS};color:{META};margin-top:7px;">{esc(meta)}</div>"""
    if number is None:
        return f'<tr><td class="p" style="padding:14px 32px 16px;border-top:1px solid {HAIR};">{text}</td></tr>'
    return f"""<tr><td class="p" style="padding:14px 32px 16px;border-top:1px solid {HAIR};">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"><tr>
<td width="40" valign="top" style="width:40px;font:bold 26px/1 {SERIF};color:{ACCENT};">{number}</td>
<td valign="top">{text}</td>
</tr></table></td></tr>"""


def byline(p):
    return p["author"] + (", guest contributor" if p["guest"] else "")


def daily(posts, order, day, a):
    todays = [p for p in posts if p["when"].date() == day]
    if not todays:
        return None
    n = len(todays)
    secs = [s for s in order if any(p["section"] == s for p in todays)]
    count = NUMBER_WORDS[n] if n < len(NUMBER_WORDS) else str(n)
    lead = "%s %s from %s." % (count, "post" if n == 1 else "posts", longdate(day).rsplit(",", 1)[0])
    blocks, text = [], ["ImmigrationProf Blog, daily digest", longdate(day), "", lead, ""]
    for s in secs:
        blocks.append(f'<tr><td class="p" style="padding:24px 32px 8px;font:bold 15px {SANS};color:{INK};">{esc(s)}</td></tr>')
        text += [s.upper(), ""]
        for p in sorted([p for p in todays if p["section"] == s], key=lambda p: p["when"], reverse=True):
            blocks.append(item(p, a, "%s, %s ET" % (byline(p), clock(p["when"]))))
            text += [p["title"], p["summary"] + ("..." if p["cut"] else ""), a.site + p["path"], ""]
    newest = sorted(todays, key=lambda p: p["when"], reverse=True)
    # The subject leads with the day's top headline, which until there is a visit counter is the newest post.
    pre = "; ".join(p["title"] for p in newest[1:4]) or lead
    more = n - 1
    subject = newest[0]["title"] if not more else "%s, and %s more" % (newest[0]["title"], NUMBER_WORDS[more].lower() if more < len(NUMBER_WORDS) else more)
    return subject, page("Daily digest", longdate(day), lead, "\n".join(blocks), pre, a), footer_text(text, a)


def weekly(posts, end, ranked, a):
    start = end - timedelta(days=6)
    week = {p["slug"]: p for p in posts if start <= p["when"].date() <= end}
    top = [week[s] for s in ranked if s in week][:10]
    if not top:
        return None
    span = "%s %d to %s%d, %d" % (start.strftime("%B"), start.day, "" if start.month == end.month else end.strftime("%B") + " ", end.day, end.year)
    lead = "The ten most-read posts of the week." if len(top) == 10 else "The most-read posts of the week."
    blocks, text = [], ["ImmigrationProf Blog, weekly digest", span, "", lead, ""]
    for i, p in enumerate(top, 1):
        blocks.append(item(p, a, "%s, %s, %s %d" % (p["section"], byline(p), p["when"].strftime("%B"), p["when"].day), number=i))
        text += ["%d. %s" % (i, p["title"]), p["summary"] + ("..." if p["cut"] else ""), a.site + p["path"], ""]
    pre = "; ".join(p["title"] for p in top[1:4])
    subject = "%s, and the rest of the week's most read" % top[0]["title"]
    return subject, page("Weekly digest", span, lead, "\n".join(blocks), pre, a), footer_text(text, a)


def footer_text(lines, a):
    lines += ["--", "You are receiving this because you signed up at immprof.com.", "Change between daily and weekly: " + a.manage,
              "Unsubscribe: " + a.unsubscribe, "Support ImmigrationProf: " + a.support, "", "This project is powered by Relevant Research, https://relevant-research.com"]
    return "\n".join(lines) + "\n"


def button(label, url):
    return f"""<tr><td class="p" style="padding:8px 32px 6px;">
<table role="presentation" cellpadding="0" cellspacing="0" border="0"><tr><td bgcolor="{ACCENT}" style="background:{ACCENT};">
<a href="{url}" style="display:inline-block;padding:13px 22px;font:bold 15px {SANS};color:#ffffff;text-decoration:none;">{esc(label)}</a>
</td></tr></table></td></tr>"""


def para(text):
    return f'<tr><td class="p" style="padding:14px 32px 4px;font:17px/1.55 {SERIF};color:{INK};">{text}</td></tr>'


def small(text):
    return f'<tr><td class="p" style="padding:14px 32px 30px;font:14px/1.55 {SERIF};color:{META};">{text}</td></tr>'


# The wording of the three short emails and of the pages a reader lands on. Drafted November 26, 2026, for Austin to approve.
NOTICES = {
    "confirm": dict(
        subject="Confirm your email for ImmigrationProf Blog",
        label="One more step", pre="Confirm your address to start receiving ImmigrationProf Blog by email.",
        body=["Thank you for signing up to receive ImmigrationProf Blog by email.",
              "Please confirm that this is your address. Until you do, we will not send you anything else."],
        button=("Confirm my email address", "confirm"),
        small="If you did not sign up, you can ignore this message. Your address will not be added to the list."),
    "welcome": dict(
        subject="You are subscribed to ImmigrationProf Blog",
        label="Welcome", pre="Your subscription is confirmed. Here is what will arrive and when.",
        body=["Your email address is confirmed, and you are now on the list.",
              "<b>The daily digest</b> arrives each morning with every post from the day before, grouped by section. On a day with no new posts, no email is sent.",
              "<b>The weekly digest</b> arrives on Sunday morning with the ten most-read posts of the week.",
              "You receive whichever of the two you chose when you signed up. You can change between them or unsubscribe at any time, with the links at the bottom of every email."],
        button=("Read today's posts", "site"),
        small="ImmigrationProf Blog has covered immigration news, policy, law and research since 2005. Every post is free to read."),
    "unsubscribed": dict(
        subject="You are unsubscribed from ImmigrationProf Blog",
        label="Unsubscribed", pre="You will not receive any more emails from ImmigrationProf Blog.",
        body=["You have been unsubscribed, and you will not receive any more emails from ImmigrationProf Blog. This message is the last one.",
              "The blog stays free to read at immprof.com, and it has RSS feeds for the whole site and for each section."],
        button=("Subscribe again", "subscribe"),
        small="If you unsubscribed by mistake, the button above takes you back to the signup page."),
}

PAGES = """WORDING FOR THE WEB PAGES A READER LANDS ON
Drafted November 26, 2026, for Austin to approve. Each is a heading and a short text.

AFTER FILLING IN THE SIGNUP FORM
Check your inbox
We have sent a message to the address you gave. Click the link in it to confirm, and your subscription will start. If it does not arrive within a few minutes, look in your spam folder.

AFTER CLICKING THE LINK IN THE CONFIRMATION EMAIL
You are subscribed
Your email address is confirmed. The daily digest arrives each morning with the posts from the day before. The weekly digest arrives on Sunday morning with the ten most-read posts of the week.

WHEN THE ADDRESS IS ALREADY ON THE LIST
You are already subscribed
This address is already on the list. To change between the daily and weekly digests, use the link at the bottom of any email from us.

AFTER CHANGING BETWEEN DAILY AND WEEKLY
Your choice is saved
You will now receive the digests you selected. The change takes effect with the next email.

AFTER CLICKING UNSUBSCRIBE
You are unsubscribed
You will not receive any more emails from ImmigrationProf Blog. The blog stays free to read here, and you can sign up again at any time.

WHEN THE CONFIRMATION LINK IS OLD OR HAS BEEN USED
This link has expired
Confirmation links work once and for a limited time. Fill in the signup form again and we will send a new one.
"""


def notices(a):
    urls = dict(confirm=a.confirm, site=a.site + "/", subscribe=a.site + "/subscribe/")
    out = {}
    for name, n in NOTICES.items():
        rows = "".join(para(t) for t in n["body"]) + button(n["button"][0], urls[n["button"][1]]) + small(n["small"])
        body = page(n["label"], "", "", rows, n["pre"], a, footer="reader" if name == "welcome" else "plain")   # a confirmed reader gets the unsubscribe link from the first email on
        strip = lambda t: re.sub(r"<[^>]+>", "", t)
        text = "\n\n".join([strip(t) for t in n["body"]] + ["%s: %s" % (n["button"][0], urls[n["button"][1]]), n["small"]])
        text += "\n\n--\nImmigrationProf Blog, immprof.com\nThis project is powered by Relevant Research, https://relevant-research.com\n"
        out[name] = (n["subject"], body, text)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("kind", choices=["daily", "weekly", "notices"])
    ap.add_argument("--date"); ap.add_argument("--end"); ap.add_argument("--ranking"); ap.add_argument("--sample", action="store_true")
    ap.add_argument("--site", default="https://immprof.com"); ap.add_argument("--assets", default="https://immprof.com/brand/")
    ap.add_argument("--unsubscribe", default="#"); ap.add_argument("--manage", default="#"); ap.add_argument("--web", default="#")
    ap.add_argument("--support"); ap.add_argument("--confirm", default="#")
    ap.add_argument("--content", default=HERE); ap.add_argument("--out", default=".")
    a = ap.parse_args()
    a.site = a.site.rstrip("/")
    a.support = a.support or a.site + "/about/"
    if a.kind == "notices":
        os.makedirs(a.out, exist_ok=True)
        for name, (subject, body, text) in notices(a).items():
            open(os.path.join(a.out, "notice-%s.html" % name), "w", encoding="utf-8").write(body)
            open(os.path.join(a.out, "notice-%s.txt" % name), "w", encoding="utf-8").write("Subject: %s\n\n%s" % (subject, text))
            print("subject: " + subject)
        open(os.path.join(a.out, "notice-pages.txt"), "w", encoding="utf-8").write(PAGES)
        print("wrote three notices and notice-pages.txt")
        return
    posts = load_posts(a.content)
    if a.kind == "daily":
        day = date.fromisoformat(a.date) if a.date else (datetime.now(ET).date() - timedelta(days=1))
        made, name = daily(posts, section_order(a.content), day, a), "daily-%s" % day.isoformat()
    else:
        end = date.fromisoformat(a.end) if a.end else (datetime.now(ET).date() - timedelta(days=1))
        if a.ranking:
            ranked = [l.strip().strip("/").split("/")[-1] for l in open(a.ranking, encoding="utf-8") if l.strip()]
        elif a.sample:
            start = end - timedelta(days=6)
            pool = sorted(p["slug"] for p in posts if start <= p["when"].date() <= end)
            random.Random(2005).shuffle(pool)
            ranked = pool
        else:
            sys.exit("weekly needs --ranking FILE from the traffic tool, or --sample to show the design")
        made, name = weekly(posts, end, ranked, a), "weekly-%s" % end.isoformat()
    if not made:
        print("no posts in that period: nothing written, nothing to send")
        return
    subject, body, text = made
    os.makedirs(a.out, exist_ok=True)
    open(os.path.join(a.out, name + ".html"), "w", encoding="utf-8").write(body)
    open(os.path.join(a.out, name + ".txt"), "w", encoding="utf-8").write(text)
    print("subject: " + subject)
    print("wrote %s.html and %s.txt" % (name, name))


if __name__ == "__main__":
    main()
