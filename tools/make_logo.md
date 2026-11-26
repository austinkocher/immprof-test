# The logo picture

`static/brand/logo.png` is the site's logo as one picture (Austin, November 26, 2026), 1990 by 211 pixels, four times its size on a desktop page.

It was made from the logo as it was first built in type: Source Serif 4 for "ImmigrationProf Blog" and Public Sans for "Since 2005", with a script that placed the year. `tools/logo-source.html` is that version. To draw it again, serve that file beside the stylesheet kept in `archive/2026-11-26_demo-sites/site/static/css/` and the typefaces in `tools/fonts/` (the share card and the logo are the only things that use them, so they are kept with the tools and are not published), take a picture of it in headless Chrome with a clear background (`--default-background-color=00000000`, font size 192 pixels), and crop the picture to its ink.

The stylesheet sizes the picture in em (10.365em wide) from the font size on `.brand-name`, so the three sizes (desktop, tablet, small phone) are set in one place each.
