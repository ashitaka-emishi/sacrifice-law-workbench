# Browser Snippets

Console snippets for sources that require a browser session (JS-rendered pages,
session cookies, or async document loading). Paste into DevTools → Console.

## Available snippets

### `founders-online-washington-orders.js`

Downloads 7 Washington General Orders from Founders Online (1775–1783).
**Start URL:** <https://founders.archives.gov/>
Saves files to your Downloads folder; move them to:
`cases/am-rev/corpus/raw/am-rev-src-03-washington-general-orders/`

If the batch fetch fails for a specific document (Founders Online uses async
202 responses), navigate to that document's URL directly, wait for it to load,
then call `downloadCurrentDocument()` in the console.

### `gallica-napoleon-early-correspondence.js` ⚠️ DID NOT WORK

**Status: failed — do not use.** Gallica's bot-detection serves an HTML
security challenge page with a 200 OK via the `.texteBrut` API endpoint,
so the script silently saves HTML instead of OCR text.

**Working approach:** On each Gallica volume page, use the download button
and select "Texte (TXT)" to get the full volume as a plain text file.
Save as `tome-N.txt` in the corpus directory; Claude Code extracts the
priority letters from the full-volume text.
See: `cases/napoleon/corpus/raw/napoleon-src-01-early-correspondence/README.md`

### `gallica-napoleon-grande-armee-bulletins.js` ⚠️ DID NOT WORK

**Status: failed — do not use.** Same Gallica bot-detection issue as above.

**Working approach:** Same as above — download "Texte (TXT)" per volume.
See: `cases/napoleon/corpus/raw/napoleon-src-02-grande-armee-bulletins/README.md`

### `umich-lincoln-lyceum-address.js`

Downloads the Lyceum Address from the U Michigan Collected Works (Basler ed.).
**Start URL:** <https://quod.lib.umich.edu/l/lincoln/lincoln1/1:13?rgn=div1;view=fulltext>
Preferred over the Gutenberg/Lapsley version already in corpus — Basler
corrects the date error (Lapsley: 1837, correct: 1838).
Move downloaded file to:
`cases/lincoln/corpus/raw/lincoln-src-01-lyceum-address.txt`
