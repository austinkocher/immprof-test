# ImmigrationProf Blog: the site

The redesigned ImmigrationProf Blog, made with Hugo. This folder is the one version being finalized (Austin, November 26, 2026); the earlier demo versions are in `../archive/2026-11-26_demo-sites/`. It holds every post published on immprof.com from August 25, 2025 to November 26, 2026 (1,833 posts), the About page, the Editors page and the seven Library pages, all at their live addresses, with their pictures, videos and files.

## Running it

```bash
cd ~/Documents/EditorialPipeline/projects/immprof-website-update/site && hugo server --port 4176
```

Then open http://localhost:4176. `bash build.sh` makes the full build into `public/` with the search index; it needs Node as well as Hugo and takes about a second. The server writes its pages into `public/` as well, so run `bash build.sh` with the server stopped before publishing.

## Bringing in posts from Ghost

1. In Ghost, export the site (Settings, then Import and Export). Keep that file outside this project: it holds the editors' email addresses and password hashes.
2. `python3 tools/ghost_export_to_posts.py EXPORT.json` writes `_import/ghost-export-posts.json` with only the posts, tags and author names.
3. `bash tools/prefetch_images.sh` copies the posts' pictures from the live site into `_import/cache/`. The list of addresses is `_import/image-urls.txt`.
4. `python3 tools/import_posts.py _import/ghost-export-posts.json` writes one file per post into `content/posts/`, saves each picture once in `assets/media/`, and gives each post its section from `../analysis/sections-all-2026-11-26.csv`. A post that is not in that list gets a first sort from `tools/section_rules.py`.
5. `bash build.sh`, then the checks in `tools/tests/`.

Videos and files that posts and the Library link to are in `static/content/media/` and `static/content/files/`, at the same addresses as on the live site.

## Contents

* `hugo.toml` holds the settings, the address rules and two switches. `fillParas` keeps the paragraph breaks in the lead story, and `showSources` shows the Sources box under a post and is off. <!-- prose-ok: setting names are code, which the check drops and then reads the rest as fragments -->
* `layouts/home.html` and `_partials/leadstory.html`, `leadparas.html`, `leadpic.html`, `pic.html`, `when.html`: the homepage. A lead story whose opening text fills the space beside the Latest list, the email signup, then the sections in columns, most recently active first.
* `layouts/archive.html`: the Archive. A search of every post with menus for section, author and date and a tag panel, then the link to the 2005 to 2025 archive.
* `layouts/taxonomy.html`: the Editors page (editors only, from the files in `content/authors/`), the Tags page and the Sections page.
* `content/posts/`: one file per post. Imported posts are HTML with the live address written out in `url`.
* `content/sections/` and `data/sections.yaml` hold the sixteen sections, each with a description and the group it opens under on a phone.
* `content/authors/` holds the six editors, and `content/contributors/` the one guest contributor who has a bio. The 20 other guests named on posts have author pages made from their posts, with no bio.
* `content/*.html`: the About page and the Library pages from the live site.
* `static/css/site.css`, `static/fonts/`: the design, in one stylesheet. Noto Serif for headlines and text, Inter for labels.
* `static/brand/logo.png`: the logo as one picture. `tools/make_logo.md` says how it was made.
* `build.sh`, `layouts/search.html`, `static/pagefind/`: search, by Pagefind. The index is made from the finished pages and searched in the reader's browser, with filters for section, author, tag and year. A search can be linked as `/search/?q=word`.
* Pictures: uploads live in `assets/media/` (moved from `static/media/` on November 25, 2026) and are resized when the site is built by `layouts/_partials/img.html`: 1400 pixels wide at most in a post, 400 for homepage thumbnails, 1200 for the share image, saved as WebP when the file is large. Only the pictures a page uses are published. The 156 copied pictures went from 23 MB to 14 MB published, counting all sizes. A picture in a Markdown post is file and description only (`layouts/_markup/render-image.html`); no caption or credit fields, by Austin's choice. A tall picture is capped at 36rem high and never cropped.
* Share cards: a post with no picture of its own gets a card made at build time, 1200 by 630 (`layouts/_partials/sharecard.html`). Design C, chosen by Austin on November 25, 2026: section label in red capitals, title in serif, and along the foot the name with Since 2005 and the address. The fixed pieces (the blank card and one label per section) are drawn by `tools/make_share_assets.sh` into `assets/brand/`; run it again if the logo, colors or sections change. Austin may later switch the title to the bold sans of option A; the eight options are on `../screenshots/first-design/share-card-options.png`, drawn from `tools/share-card-options.html`. A post with a picture, or with "Image for sharing" set, uses that picture. Other pages use `static/brand/share.png`.
* Wide pictures: the post switch `wide: true` ("Wide pictures" in the editor) lets a landscape picture in a Markdown post run the full width of the page column; upright pictures stay in the text column. `hugo server` must be restarted after a new folder is added under `layouts/`.
* Tags: the editors' list is `data/tags.json`, each tag with a one-line description. The descriptions are the editors' notes and are not shown on the site (Austin, November 25, 2026: "remove it from the site"). The Tags field in the editor is open text, so a new tag can appear; `python3 tools/check_tags.py` lists tags that are not on the list, near-duplicates, and posts with no tag or more than four.
* Header and footer: the top row is Home, About, Editors, Library, Archive, Search. The footer has the email signup on every page but the homepage, which shows it under the lead block, then About, Editors, Archive, Library, Tags, Support ImmigrationProf and the two feeds. The repeats are on purpose; RSS left the top row. The support link points to About until a support page exists.
* `static/admin/`: a draft editor setup (Sveltia CMS). The practice copy in `static/admin/test/` is written from it by `tools/make_practice_editor.py` when the site is built. Fields run from what changes on every post to what rarely does (Austin, November 25, 2026): Title, Text, Section, Tags, Byline, Published, Image for sharing, Wide pictures, Guest author, and last Web address (URL). Byline lists only the editors. For a guest post the editor posting it goes in Byline and the guest in Guest author; the site shows the guest as the author, with "Guest contributor", the guest's bio and "Posted by" the editor. Editors are the `authors` list (`content/authors/`), guests the `contributors` list (`content/contributors/`); both have pages under /author/, and an editor's page leaves out guest posts the editor published. To add a guest: a folder in `content/contributors/` with title, bio and link, and the name in the Guest author options in both `config.yml` files. The web address is optional: left empty, it is made from the title when the post is first saved (tried in the practice copy: the title "Practice: A Ruling on Habeas Petitions in the Fifth Circuit" gave `practice-a-ruling-on-habeas-petitions-in-the-fifth-circuit`), and editing the title later does not move the post, because Hugo reads the address from the file name (`:slugorcontentbasename` in `hugo.toml`). `static/admin/test/` is a practice copy with the same fields that keeps posts in the browser only: open http://localhost:4174/admin/test/ and press Work with Test Repository. Tried November 25, 2026: the form opens, and Save refuses a bad address and a missing section or byline. Saving real files needs the site to be the root of its own git repository.
* `tools/read_ghost_pages.py`, `tools/import_posts.py`: read saved live pages and turn them into post files.
* `tools/import_archive.py`: the same for the 2005 to 2025 archive, used in the migration test.
* `tools/check_addresses.py`: checks every address on the live site against the build.
* `_import/`: the data the 200 posts were built from, and the live site's address lists.

## Limits of this build

* Every post was read and given a section on November 26, 2026; about a third are marked as judgment calls in the list. Every post was read a second time for tags and guest authors: each has the tags from the editors' list that fit it, up to four (32 have none), and 30 posts show a guest as the author. The importer reads both from `../analysis/tags-all-2026-11-26.csv`.
* The outlet name beside a title comes from a table of about 60 outlets in `tools/import_posts.py`. It names the outlet on 116 of the 200 posts. 58 link first to an outlet not in the table and 26 link only through newsletter tracking addresses, and those show no outlet.
* The signup form is not connected to a mailing list.
* After adding or changing posts, run `bash build.sh` again so the search index includes them. `hugo server` alone shows the pages and keeps the last index.
* "Today" and "Yesterday" on the homepage follow the clock at the moment of the build, and the reader's own clock once the page is open.
* `tools/tests/README.md` lists the checks. `tools/tests/shots.py` compares pictures of every kind of page before and after a change.

## The public test copy

The test copy is at https://austinkocher.github.io/immprof-test/ and is built by GitHub from the repository `austinkocher/immprof-test`. To update it, run `bash tools/publish_test.sh`, then commit from inside the test repository with EditorialPipeline's `tools/commit_script.py --run --no-changelog`. GitHub rebuilds it in about three minutes. `layouts/_partials/rooted.html` keeps links in post text working when the site sits inside a folder of an address.

