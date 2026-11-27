# ImmigrationProf Blog Archive, 2005 to 2025

This folder is a complete Hugo site of its own: the posts the ImmigrationProf Blog published on TypePad, from 2005 to September 2025, in the look of the blog's new site.
It is separate from the new site on purpose (Austin, November 27, 2026), because the old TypePad categories and names differ from the new sections.
It was built on November 27, 2026 as a test copy, to be published at https://austinkocher.github.io/immprof-test/historical/.
Nothing here has been committed, pushed or published yet.

## Contents

* `hugo.toml` holds the settings. The address the site is built for is set on the build line.
* `content/post/` has one file per post (19,863), in the HTML TypePad stored. Each post is at `/post/<basename>/`, the address it has on archive.immprof.com today, and its old TypePad address `/immigration/YYYY/MM/<basename>.html` is kept as a second address that sends the reader on.
* `content/year/` has one page per year (20 years: 2005, 2006, and 2008 to 2025). A year's page lists its months, each with a count; a month opens to show its posts.
* `content/category/` has one page per TypePad category (14), named exactly as TypePad named them, 100 posts to a page.
* `layouts/` holds the templates, and `static/css/archive.css` the one stylesheet. The fonts and the logo are copies from the new site (`static/fonts/`, `static/brand/`).
* `tools/` holds the download, import and checking scripts.
* `data/import_stats.json` has the counts from the last import, and `data/left_out.json` the records left out.
* `public/`, `resources/` and `static/pagefind/` are made by the build and are not kept in git (`.gitignore`).

The homepage has the search (Pagefind, with menus for year and category), the list of years and the list of categories.
A search can be linked, for example `?q=asylum&year=2014&category=Books`.
The header and footer link to the current blog at https://immprof.com/.

## Building

```bash
cd ~/Documents/immprof-test/archive-site && HUGO_PARAMS_TEST=1 HUGO_BASEURL=https://austinkocher.github.io/immprof-test/historical/ bash build.sh
```

The build needs Hugo (0.170.1 was used) and Node, for Pagefind 1.3.0 through npx.
It runs Hugo, then Pagefind over the finished pages, then Hugo again to copy the search index into `public/`.
It takes about a minute.

`HUGO_PARAMS_TEST=1` puts `<meta name="robots" content="noindex, nofollow">` on every page and makes `robots.txt` refuse every crawler.
`build.sh` turns it on by itself when the line leaves it out. A real, listed copy needs `HUGO_PARAMS_TEST=0`.

Checks after a build:

```bash
cd ~/Documents/immprof-test/archive-site && python3 -I tools/check_build.py /immprof-test/historical/
```

```bash
cd ~/Documents/immprof-test/archive-site && python3 ~/Documents/ClaudePlaybook/tools/css_accent_lint.py static/css/archive.css
```

`check_build.py` reads every built page and confirms that each link, picture, stylesheet and script address inside the site leads to a file, that every page has the noindex line, and that the search index is there.

## Source of the posts

The posts were read on November 27, 2026 from the public data service of the existing archive site, https://archive.immprof.com/api/posts, 100 records at a time with a pause between requests.
The service holds 19,863 records, and all of them were read.
The code of that site is public at github.com/RelevantResearch/immprof_archive.
Earlier findings about the data are in the private project `ClaudeImmProf`, in `MIGRATION.md`, section "The archive, 2005 to 2025".

**The raw download is not in this folder and must never be put in any repository.**
In 896 records the author field holds part of a reader's comment in place of the author: the reader's name, email address, IP number and internet address.
In 915 records the date field holds the date of a reader's comment followed by the comment.
archive.immprof.com's data service still returns those fields to anyone who asks.

## Importing again

```bash
bash ~/Documents/immprof-test/archive-site/tools/fetch_archive.sh /path/outside/every/repository/archive-raw
```

```bash
cd ~/Documents/immprof-test/archive-site && python3 -I tools/join_pages.py /path/outside/every/repository/archive-raw
```

```bash
cd ~/Documents/immprof-test/archive-site && python3 -I tools/import_archive.py /path/outside/every/repository/archive-raw/archive.json
```

```bash
cd ~/Documents/immprof-test/archive-site && python3 -I tools/check_leaks.py /path/outside/every/repository/archive-raw/archive.json
```

The download stops at the first error from the service and can be started again where it stopped.
The import replaces every file in `content/post/`, the year and category pages and the two files in `data/`. It takes about ten seconds.
Adding `--check` reads and counts and writes nothing.
The import refuses to write if an email address, an IP number or a whole author field from a damaged record is in the text it is about to write.
`check_leaks.py` then searches every file in this folder, the built pages and the search index included, for those pieces and prints counts only.
Run `bash build.sh` after an import.

## Repairs made by the import

* **Line breaks.** The export turned every line break in the stored HTML into `<br>`, even inside tags, where it broke picture and link addresses. All 222,385 were turned back into line breaks. A break the editors typed is stored as `<br />` and is kept.
* **Dates.** The 915 records with a damaged date field take their year and month from the old address, and their pages show the month and year only, since the day is not known.
* **Bylines.** Every post is credited as the export credits intact records: "Immigration Prof" on all but one, and "Law Professor Blogs LLC" on one post from 2008. The author field of a damaged record is never used.
* **Dead pictures.** 51,321 `<img>` tags were removed, in 11,539 posts: 40,214 on `i.zemanta.com`, a recommendation service that no longer answers, and 11,107 on `lawprofessors.typepad.com`, TypePad's server for the blog. In 51,097 cases a link that wrapped only that picture went with it. The other 1,843 picture tags are unchanged. No picture was fetched or copied.
* **Links between posts.** 14,385 links to `lawprofessors.typepad.com/immigration/YYYY/MM/name.html` now point to the post's page in this archive. Another 1,735 point to posts that are not in the export (most from 2005 to 2009) and were left as they are.
* **Readers' email addresses printed in posts.** 8 of the email addresses in the damaged author fields are printed in the text of 23 posts as well, because the reader was an editor or a professor whose address the post gave as a contact (calls for papers, conference notices), or because the address sat inside a link. All 31 occurrences were replaced with "[email address removed]", so that no address from a damaged field is anywhere on the site. `--keep-printed-emails` leaves them in.

## Left out

Count: 0.

No record was left out. In every damaged record the reader's comment went into the author and date fields only; the title and the text are the post's own, so each of the 896 was repaired and kept.
A damaged record with no title or no text of its own would be left out and listed in `data/left_out.json`.

## Decisions and changes

Decisions are Austin's, with the date and his words where he gave them.

* **A standalone archive, not merged into the new site** (November 27, 2026). The old categories and names differ from the new sections: "I still think we should have a standalone archive that isn't merged in". It is to be a part of the new website at an address of its own ("let's keep it as a standalone subpage of the new website"). Until then it is published on the earlier test site under `/historical/`.
* **First build** (November 27, 2026). All 19,863 posts, the 14 old categories kept as named, byline "Immigration Prof", the new site's design. He called it "excellent".
* **One central page** (November 27, 2026). "just one central page", then "one landing page and then drill into years on a new page is fine". The front page is the one way in: search, the list of years, the list of categories. The separate list-of-years page (`/year/`) and list-of-categories page (`/category/`) are gone; those two addresses now lead to the front page's lists (`layouts/section.html`), and the "Years" and "Categories" links are out of the top row. Each year and each category still has its own page.
* **Months that open and close on a year's page** (November 27, 2026). "one page per year is fine but maybe collapsable months or something". Each month is a line with its count that opens to show its posts; two buttons open or close every month; a link to `#m03` opens March (`layouts/year.html`, styles in `static/css/archive.css`).
* **Readers' email addresses printed in posts stay removed** (November 27, 2026: "removing email addresses is fine"). Eight addresses in 23 posts read "[email address removed]".
* **Nameplate** (November 27, 2026: "nameplate is fine"). The new site's logo with "Archive, 2005 to 2025" under it.
* **Footer** (November 27, 2026: "footer with RR is fine"). The Relevant Research credit stays.
* **Damaged posts** (November 27, 2026). "we can fix the damaged posts once you get it up and running too". The repairs made so far are under "Repairs made by the import"; the 915 posts with no known day are the ones still to look at.

Open: whether each old category keeps a page of its own or the front page's category list should open a search for that category; whether the second addresses (old TypePad paths) are wanted; about 1,800 picture tags on other hosts, some of them dead.


## Limits

* The export is thin before 2010: 4 posts from 2005, 2 from 2006, none from 2007, 3 from 2008 and 123 from 2009. The blog began in September 2005, so roughly its first four years are missing from the source.
* The export does not say which editor wrote which post.
* Posts keep the HTML TypePad stored, with its own inline styles, embeds and scripts from other sites. Many links to other sites are dead by now.
* "Related articles" boxes that the recommendation service added under posts remain as plain lists of links, without their thumbnails.
* 25 addresses inside post text start at the top of the host (for example `/wiki/...`, pasted from another site). They were dead on TypePad too and are unchanged.
* 24 posts name, in their own title or text, the reader whose comment damaged the record (the reader is the post's author or subject). Those names are part of the posts and are unchanged.
* A year's page holds every post of that year (the largest, 2017, has 1,657), folded into months that open one at a time or all at once. The page's file is still large: 2017 is about 470 KB.
* The second addresses (`/immigration/YYYY/MM/<basename>.html`) are one small page each, which doubles the number of post files. They matter only if the archive is later served at an address where the old TypePad paths can arrive.
