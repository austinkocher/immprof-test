"""Restore email addresses that Cloudflare hid when the posts were read from the live site.

Cloudflare replaces an address in a page with a link to /cdn-cgi/l/email-protection and the text "[email protected]",
keeping the real address in a scrambled form. On a copy of the page the link leads nowhere and the address is lost.
This turns each one back into an ordinary mailto link. import_posts.py calls restore() on every post it writes.

Usage:  python3 tools/fix_cf_email.py content/posts/*.html      (prints how many it restored; changes the files in place)
"""
import re, sys


def _decode(code):
    key = int(code[:2], 16)
    return "".join(chr(int(code[i:i + 2], 16) ^ key) for i in range(2, len(code), 2))


LINK = re.compile(r'<a[^>]*href="/cdn-cgi/l/email-protection#([0-9a-f]+)"[^>]*>.*?</a>', re.S)
SPAN = re.compile(r'<span class="__cf_email__" data-cfemail="([0-9a-f]+)">.*?</span>', re.S)


def restore(html):
    """Returns (html with addresses restored, how many were restored)."""
    count = 0

    def link(m):
        nonlocal count
        count += 1
        a = _decode(m.group(1))
        return '<a href="mailto:%s">%s</a>' % (a, a)

    def span(m):
        nonlocal count
        count += 1
        return _decode(m.group(1))

    html = LINK.sub(link, html)
    html = SPAN.sub(span, html)
    return html, count


if __name__ == "__main__":
    total = 0
    for path in sys.argv[1:]:
        text = open(path, encoding="utf-8").read()
        new, n = restore(text)
        if n:
            open(path, "w", encoding="utf-8").write(new)
            total += n
            print("%s: %d" % (path.split("/")[-1], n))
    print("restored %d" % total)
