/**
 * Gallica BnF — Napoleon early correspondence batch downloader
 *
 * HOW TO USE:
 *   1. Go to https://gallica.bnf.fr/ in your browser and let it load fully.
 *      (Being on a Gallica page avoids cross-origin fetch restrictions.)
 *   2. Open DevTools → Console.
 *   3. Paste this entire script and press Enter.
 *   4. The script fetches plain-text OCR for each letter's page range,
 *      and downloads one .txt file per letter to your Downloads folder.
 *   5. Move downloaded files into:
 *        cases/napoleon/corpus/raw/napoleon-src-01-early-correspondence/
 *   6. Record each letter's volume, letter number, date, recipient, and
 *      Gallica ARK in cases/napoleon/metadata/document-manifest.json.
 *
 * WHAT IT DOWNLOADS (priority rise-phase letters, 1784–1797):
 *   Letters are from Correspondance de Napoléon Ier, Plon 1858–1870.
 *   Gallica plain-text endpoint: /ark:/12148/{ARK}/f{PAGE}.texteBrut
 *
 * SELECTION RATIONALE:
 *   Letters selected for explicit sacrifice, gloire, patrie, or army-as-body
 *   language in the rise phase. Pages below are 1-indexed within each volume's
 *   Gallica scan. Verify page ranges against the volume's table of contents
 *   if OCR output is misaligned.
 *
 * NOTE ON TRANSLATION:
 *   Text is French original. Translation methodology must be resolved in
 *   OPEN_DECISIONS.md before annotation begins.
 */

// Gallica volume ARK identifiers — Correspondance de Napoléon Ier (Plon 1858–1870)
// Rise phase covers vols 1–3 (1784–1797)
const GALLICA_VOLUMES = {
  "tome-1": "bpt6k6296221w",  // Tome 1 (1784–1795)
  "tome-2": "bpt6k6295821n",  // Tome 2 (1795–1796)
  "tome-3": "bpt6k6295853m",  // Tome 3 (1796–1797)
};

// Priority letters: {vol, pages, date, recipient, slug, letter_num}
// pages = [start, end] within the Gallica scan (1-indexed).
// These are approximate — the script fetches the range and concatenates pages.
// Adjust pages if OCR output starts mid-letter or cuts off early.
const LETTERS = [
  {
    vol: "tome-1",
    letter_num: "I-1",
    pages: [38, 39],
    date: "1784-xx-xx",
    recipient: "Unknown (early schoolboy letter)",
    slug: "napoleon-corr-1784-schoolboy-early",
    selection_note: "Earliest extant letter; rise-phase baseline for rhetorical register",
  },
  {
    vol: "tome-1",
    letter_num: "I-4",
    pages: [42, 43],
    date: "1786-07-xx",
    recipient: "Father (Carlo Bonaparte)",
    slug: "napoleon-corr-1786-07-father-patrie",
    selection_note: "Explicit patrie and duty language; early expression of national feeling",
  },
  {
    vol: "tome-1",
    letter_num: "I-60",
    pages: [64, 66],
    date: "1793-09-xx",
    recipient: "Convention nationale",
    slug: "napoleon-corr-1793-09-convention-toulon",
    selection_note: "Toulon siege; first battlefield command; sacrifice and glory framing",
  },
  {
    vol: "tome-1",
    letter_num: "I-95",
    pages: [88, 90],
    date: "1794-xx-xx",
    recipient: "Committee of Public Safety",
    slug: "napoleon-corr-1794-committee-public-safety",
    selection_note: "Army-as-body and republican sacrifice language under Jacobin register",
  },
  {
    vol: "tome-2",
    letter_num: "II-1",
    pages: [5, 7],
    date: "1795-08-xx",
    recipient: "War Ministry",
    slug: "napoleon-corr-1795-08-war-ministry",
    selection_note: "Post-Thermidor; transition in sacrificial register from republic to army",
  },
  {
    vol: "tome-2",
    letter_num: "II-100",
    pages: [95, 97],
    date: "1796-03-xx",
    recipient: "Army of Italy",
    slug: "napoleon-corr-1796-03-army-italy-proclamation",
    selection_note: "First Italian campaign proclamation; glory, hunger, honour, soldier-as-body",
  },
  {
    vol: "tome-2",
    letter_num: "II-150",
    pages: [138, 140],
    date: "1796-05-xx",
    recipient: "Directory",
    slug: "napoleon-corr-1796-05-directory-italy",
    selection_note: "Mid-campaign; sacrifice and victory framing; army loyalty rhetoric",
  },
  {
    vol: "tome-3",
    letter_num: "III-1",
    pages: [5, 7],
    date: "1796-08-xx",
    recipient: "Army of Italy / Directory",
    slug: "napoleon-corr-1796-08-castiglione-aftermath",
    selection_note: "Post-Castiglione; battlefield sacrifice and glory economy explicit",
  },
  {
    vol: "tome-3",
    letter_num: "III-80",
    pages: [72, 74],
    date: "1797-01-xx",
    recipient: "Army of Italy",
    slug: "napoleon-corr-1797-01-rivoli-army",
    selection_note: "Post-Rivoli; peak of Italian campaign sacrifice rhetoric",
  },
  {
    vol: "tome-3",
    letter_num: "III-200",
    pages: [186, 188],
    date: "1797-10-xx",
    recipient: "Directory (Campo Formio)",
    slug: "napoleon-corr-1797-10-campo-formio-directory",
    selection_note: "End of Italian campaign; transition from soldier-sacrifice to imperial ambition",
  },
];

// Gallica rate-limits aggressively. These delays keep requests well under the
// threshold. Each page waits 4s; each document waits an additional 8s after
// the last page. On 429 the fetch retries with exponential backoff (max 5×).
const PAGE_DELAY_MS = 4000;
const DOC_DELAY_MS  = 8000;
const MAX_RETRIES   = 5;

function sleep(ms) {
  return new Promise((r) => setTimeout(r, ms));
}

function download(filename, text) {
  const blob = new Blob([text], { type: "text/plain;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

async function fetchPage(ark, pageNum) {
  const url = `https://gallica.bnf.fr/ark:/12148/${ark}/f${pageNum}.texteBrut`;
  let delay = 6000;
  for (let attempt = 0; attempt < MAX_RETRIES; attempt++) {
    const resp = await fetch(url, { credentials: "include" });
    if (resp.status === 429) {
      const retryAfter = resp.headers.get("Retry-After");
      const wait = retryAfter ? parseInt(retryAfter, 10) * 1000 : delay;
      console.warn(`  429 on f${pageNum} — waiting ${wait / 1000}s (attempt ${attempt + 1}/${MAX_RETRIES})...`);
      await sleep(wait);
      delay *= 2;
      continue;
    }
    if (!resp.ok) throw new Error(`HTTP ${resp.status} for page ${pageNum}`);
    const text = await resp.text();
    // Gallica returns its bot-check HTML page (200 OK) instead of OCR text
    // when it doesn't recognise the session. Detect and bail out early.
    if (text.trimStart().startsWith("<!DOCTYPE") || text.trimStart().startsWith("<html")) {
      throw new Error(`Got HTML security page instead of text for page ${pageNum} — reload gallica.bnf.fr and retry`);
    }
    return text;
  }
  throw new Error(`HTTP 429 persisted after ${MAX_RETRIES} retries for page ${pageNum}`);
}

async function fetchLetter(letter) {
  const ark = GALLICA_VOLUMES[letter.vol];
  const filename = `${letter.slug}.txt`;
  const gallicaUrl = `https://gallica.bnf.fr/ark:/12148/${ark}`;

  console.log(`Fetching ${letter.letter_num} (${letter.date}) — pages ${letter.pages[0]}–${letter.pages[1]}...`);

  const pageTexts = [];
  for (let p = letter.pages[0]; p <= letter.pages[1]; p++) {
    try {
      const text = await fetchPage(ark, p);
      pageTexts.push(text.trim());
      await sleep(PAGE_DELAY_MS);
    } catch (err) {
      console.warn(`  Page ${p}: ${err.message}`);
      pageTexts.push(`[PAGE ${p} FETCH ERROR: ${err.message}]`);
      await sleep(PAGE_DELAY_MS);
    }
  }

  const body = pageTexts.join("\n\n");

  if (body.replace(/\[PAGE.*?\]/g, "").trim().length < 50) {
    console.warn(`  ${letter.letter_num}: extracted text too short — check page numbers or try manual download.`);
    console.warn(`  Volume URL: ${gallicaUrl}`);
    return false;
  }

  const provenance =
    `SOURCE: Correspondance de Napoléon Ier, publiée par ordre de l'Empereur Napoléon III\n` +
    `PUBLISHER: Plon, Paris, 1858–1870\n` +
    `VOLUME: ${letter.vol} (Correspondance letter ${letter.letter_num})\n` +
    `GALLICA_ARK: ark:/12148/${ark}\n` +
    `GALLICA_URL: ${gallicaUrl}\n` +
    `SCAN_PAGES: f${letter.pages[0]}–f${letter.pages[1]}\n` +
    `DATE: ${letter.date}\n` +
    `RECIPIENT: ${letter.recipient}\n` +
    `SELECTION_NOTE: ${letter.selection_note}\n` +
    `LANGUAGE: French (original)\n` +
    `RIGHTS: Public domain (Napoleon died 1821; Plon 1858 edition PD)\n` +
    `ACQUISITION_DATE: ${new Date().toISOString().slice(0, 10)}\n` +
    `TRANSLATION_NOTE: French original. English translation required before annotation.\n` +
    `  Key CMT terms to flag: sacrifice, gloire, patrie, honneur, sang, corps, devoir.\n` +
    `  See OPEN_DECISIONS.md — Napoleon translation methodology.\n` +
    `\n`;

  download(filename, provenance + "=" .repeat(72) + "\n\n" + body);
  console.log(`  ✓ Downloaded: ${filename} (${body.length} chars)`);
  return true;
}

async function runAll() {
  console.log("=== Gallica Napoleon Early Correspondence Downloader ===");
  console.log(`Downloading ${LETTERS.length} letters with delays between requests...`);
  console.log("NOTE: Page numbers are approximate. Check OCR output for alignment.\n");

  let ok = 0;
  const failed = [];

  for (const letter of LETTERS) {
    const success = await fetchLetter(letter);
    if (success) {
      ok++;
    } else {
      failed.push(letter);
    }
    await sleep(DOC_DELAY_MS);
  }

  console.log(`\n=== Done: ${ok}/${LETTERS.length} succeeded ===`);
  if (failed.length > 0) {
    console.log("Failed letters (check page numbers or download manually):");
    for (const l of failed) {
      const ark = GALLICA_VOLUMES[l.vol];
      console.log(`  ${l.letter_num} (${l.date}): https://gallica.bnf.fr/ark:/12148/${ark}/f${l.pages[0]}.texteImage`);
    }
  }
  console.log("\nMove downloaded files to:");
  console.log("  cases/napoleon/corpus/raw/napoleon-src-01-early-correspondence/");
}

// --- Single-page helper ---
// If you've navigated to a specific Gallica page in text mode, call this to
// download the current page's plain text.
async function downloadCurrentPage() {
  const url = window.location.href;
  const arkMatch = url.match(/ark:\/12148\/([^/]+)/);
  const pageMatch = url.match(/\/f(\d+)/);
  if (!arkMatch) { console.error("Not on a Gallica document page."); return; }
  const ark = arkMatch[1];
  const page = pageMatch ? pageMatch[1] : "1";
  const textUrl = `https://gallica.bnf.fr/ark:/12148/${ark}/f${page}.texteBrut`;
  const resp = await fetch(textUrl, { credentials: "include" });
  const text = await resp.text();
  const filename = `gallica-${ark}-f${page}.txt`;
  const blob = new Blob([text], { type: "text/plain;charset=utf-8" });
  const a = Object.assign(document.createElement("a"), {
    href: URL.createObjectURL(blob),
    download: filename,
  });
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  console.log(`Downloaded: ${filename} (${text.length} chars)`);
}

runAll();
