# Tests for the site

Written November 26, 2026, when Austin asked for the sites to be pressure tested across every post.

* `check_links.py PUBLIC_DIR`: in a built site, every internal link, picture, script and stylesheet address must be a file. Reports pages with no title, pages without exactly one main heading, repeated ids and pictures with no alt attribute.
* `crawl_pages.js`: in a browser, loads every page at 1300, 375 and 340 pixels wide and reports pages wider than the screen, broken pictures, empty pages and pages that fail to load.
* `profile_posts.py`: one row per post with its picture size, text length, lists, embeds and title length. `lead_story_test.py` reads its output.
* `shots.py`: takes a picture of one page of each kind at desktop and phone width, and with `--compare` reports how much two sets of pictures differ. Used to check that a cleanup changed nothing a reader sees.
* `lead_story_test.py`: for the homepage. It builds with `HUGO_PARAMS_LEADTEST=1`, which is what makes the page report its readings; a normal build leaves that code out. Each post takes a turn as the newest. The homepage alone is built with the clock set just after that post, opened in headless Chrome wide and narrow, and the page reports what its script decided. It serves the test builds from its own folder on port 4177, which has to be started first (`python3 -m http.server 4177` in that folder), and it expects `profile.json` beside it.

Results of the first full pass are in `../../../template-survey.md` under "Pressure test".
