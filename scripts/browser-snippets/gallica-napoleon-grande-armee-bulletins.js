/**
 * Gallica BnF — Napoleon Grande Armée bulletins batch downloader
 *
 * HOW TO USE:
 *   1. Go to https://gallica.bnf.fr/ in your browser and let it load fully.
 *   2. Open DevTools → Console.
 *   3. Paste this entire script and press Enter.
 *   4. Downloads one .txt file per bulletin to your Downloads folder.
 *   5. Move downloaded files into:
 *        cases/napoleon/corpus/raw/napoleon-src-02-grande-armee-bulletins/
 *   6. Record each bulletin's number, volume, page, date, and Gallica ARK
 *      in cases/napoleon/metadata/document-manifest.json.
 *
 * WHAT IT DOWNLOADS (priority bulletins, 1805–1812):
 *   Bulletins de la Grande Armée from Correspondance de Napoléon Ier,
 *   Plon 1858–1870. Covers Austerlitz, Jena-Auerstedt, Eylau, Wagram,
 *   and Russian campaign phases.
 *
 * SELECTION RATIONALE:
 *   Bulletins selected for peak sacrificial economy, army-as-body,
 *   and glory-as-sacred-object rhetoric. This register is the Napoleon
 *   case's closest analogue to Washington's general orders and Lincoln's
 *   wartime messages — essential for cross-case register comparison.
 *
 * NOTE ON TRANSLATION:
 *   Text is French original. Translation methodology must be resolved in
 *   OPEN_DECISIONS.md before annotation begins.
 *   Key terms to flag: sacrifice, gloire, honneur, sang, patrie, corps,
 *   victoire, mort, devoir, immortel.
 */

// Gallica ARK identifiers — Correspondance de Napoléon Ier (Plon 1858–1870)
// Bulletins fall across vols 10–24 (campaign years 1805–1812)
const GALLICA_VOLUMES = {
  "tome-10":  "bpt6k62954782",  // 1805 (Austerlitz campaign)
  "tome-11":  "bpt6k9666763q",  // 1806 (Jena-Auerstedt)
  "tome-12":  "bpt6k6294040x",  // 1807 (Eylau, Friedland)
  "tome-13":  "bpt6k6328645m",  // 1807–1808
  "tome-14":  "bpt6k6296790v",  // 1808–1809
  "tome-15":  "bpt6k6294033s",  // 1809 (Wagram)
  "tome-17":  "bpt6k96341740",  // 1810
  "tome-18":  "bpt6k63285295",  // 1811
  "tome-20":  "bpt6k6296218d",  // 1811–1812
  "tome-21":  "bpt6k6334241m",  // 1812 (Russian campaign)
  "tome-24":  "bpt6k63342473",  // 1812 (late Russia / retreat)
};

// Priority bulletins: {vol, bulletin_num, pages, date, campaign, slug, selection_note}
// pages = [start, end] within the Gallica scan (1-indexed).
// Bulletin numbers refer to the official sequence in the Correspondance.
const BULLETINS = [
  {
    vol: "tome-10",
    bulletin_num: "34",
    pages: [420, 423],
    date: "1805-12-03",
    campaign: "Austerlitz",
    slug: "napoleon-bulletin-1805-12-03-austerlitz",
    selection_note: "Austerlitz bulletin; peak gloire and sacrifice language; army-as-sacred-body",
  },
  {
    vol: "tome-10",
    bulletin_num: "35",
    pages: [424, 427],
    date: "1805-12-04",
    campaign: "Austerlitz",
    slug: "napoleon-bulletin-1805-12-04-austerlitz-aftermath",
    selection_note: "Day-after Austerlitz; honour of the dead; glory economy explicit",
  },
  {
    vol: "tome-11",
    bulletin_num: "52",
    pages: [390, 393],
    date: "1806-10-14",
    campaign: "Jena-Auerstedt",
    slug: "napoleon-bulletin-1806-10-14-jena",
    selection_note: "Jena-Auerstedt; soldier sacrifice and Prussian enemy rhetoric",
  },
  {
    vol: "tome-11",
    bulletin_num: "55",
    pages: [410, 413],
    date: "1806-10-27",
    campaign: "Jena-Auerstedt",
    slug: "napoleon-bulletin-1806-10-27-berlin",
    selection_note: "Entry into Berlin; conquest as sacred fulfilment; glory-patrie frame",
  },
  {
    vol: "tome-12",
    bulletin_num: "68",
    pages: [120, 124],
    date: "1807-02-09",
    campaign: "Eylau",
    slug: "napoleon-bulletin-1807-02-09-eylau",
    selection_note: "Eylau; bloodiest battle; sacrifice language at maximum density",
  },
  {
    vol: "tome-12",
    bulletin_num: "89",
    pages: [380, 384],
    date: "1807-06-14",
    campaign: "Friedland",
    slug: "napoleon-bulletin-1807-06-14-friedland",
    selection_note: "Friedland victory; divine dispensation and army-glory framing",
  },
  {
    vol: "tome-15",
    bulletin_num: "15",
    pages: [128, 132],
    date: "1809-07-06",
    campaign: "Wagram",
    slug: "napoleon-bulletin-1809-07-06-wagram",
    selection_note: "Wagram; glory and sacrifice at peak of imperial rhetoric",
  },
  {
    vol: "tome-15",
    bulletin_num: "18",
    pages: [155, 158],
    date: "1809-07-11",
    campaign: "Wagram",
    slug: "napoleon-bulletin-1809-07-11-wagram-aftermath",
    selection_note: "Post-Wagram; honouring the dead; sacred duty and immortal glory",
  },
  {
    vol: "tome-21",
    bulletin_num: "16",
    pages: [190, 195],
    date: "1812-09-10",
    campaign: "Russia",
    slug: "napoleon-bulletin-1812-09-10-russia-advance",
    selection_note: "Russian campaign advance; sacrifice-for-patrie at maximum scale",
  },
  {
    vol: "tome-21",
    bulletin_num: "29",
    pages: [320, 326],
    date: "1812-12-03",
    campaign: "Russia",
    slug: "napoleon-bulletin-1812-12-03-russia-29th",
    selection_note: "Famous 29th Bulletin (Moscow retreat); grief, death, and army dissolution; pivotal for sacrificial economy collapse",
  },
  {
    vol: "tome-24",
    bulletin_num: "17",
    pages: [168, 172],
    date: "1813-05-22",
    campaign: "Germany",
    slug: "napoleon-bulletin-1813-05-22-bautzen",
    selection_note: "Post-Bautzen; late-imperial sacrifice framing as losses mount",
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

async function fetchBulletin(bulletin) {
  const ark = GALLICA_VOLUMES[bulletin.vol];
  const filename = `${bulletin.slug}.txt`;
  const gallicaUrl = `https://gallica.bnf.fr/ark:/12148/${ark}`;

  console.log(`Fetching Bulletin ${bulletin.bulletin_num} (${bulletin.date}, ${bulletin.campaign}) — pages ${bulletin.pages[0]}–${bulletin.pages[1]}...`);

  const pageTexts = [];
  for (let p = bulletin.pages[0]; p <= bulletin.pages[1]; p++) {
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
    console.warn(`  Bulletin ${bulletin.bulletin_num}: text too short — check page numbers.`);
    console.warn(`  Volume URL: ${gallicaUrl}/f${bulletin.pages[0]}.texteImage`);
    return false;
  }

  const provenance =
    `SOURCE: Correspondance de Napoléon Ier, publiée par ordre de l'Empereur Napoléon III\n` +
    `PUBLISHER: Plon, Paris, 1858–1870\n` +
    `VOLUME: ${bulletin.vol}\n` +
    `BULLETIN_NUM: ${bulletin.bulletin_num} (Bulletin de la Grande Armée)\n` +
    `GALLICA_ARK: ark:/12148/${ark}\n` +
    `GALLICA_URL: ${gallicaUrl}\n` +
    `SCAN_PAGES: f${bulletin.pages[0]}–f${bulletin.pages[1]}\n` +
    `DATE: ${bulletin.date}\n` +
    `CAMPAIGN: ${bulletin.campaign}\n` +
    `SELECTION_NOTE: ${bulletin.selection_note}\n` +
    `LANGUAGE: French (original)\n` +
    `RIGHTS: Public domain (Napoleon died 1821; Plon 1858 edition PD)\n` +
    `ACQUISITION_DATE: ${new Date().toISOString().slice(0, 10)}\n` +
    `TRANSLATION_NOTE: French original. English translation required before annotation.\n` +
    `  Key CMT terms to flag: sacrifice, gloire, honneur, sang, patrie, corps,\n` +
    `  victoire, mort, devoir, immortel. See OPEN_DECISIONS.md — Napoleon translation.\n` +
    `\n`;

  download(filename, provenance + "=".repeat(72) + "\n\n" + body);
  console.log(`  ✓ Downloaded: ${filename} (${body.length} chars)`);
  return true;
}

async function runAll() {
  console.log("=== Gallica Napoleon Grande Armée Bulletins Downloader ===");
  console.log(`Downloading ${BULLETINS.length} bulletins with delays between requests...`);
  console.log("NOTE: Page numbers are approximate — verify against volume ToC if text is off.\n");

  let ok = 0;
  const failed = [];

  for (const bulletin of BULLETINS) {
    const success = await fetchBulletin(bulletin);
    if (success) {
      ok++;
    } else {
      failed.push(bulletin);
    }
    await sleep(DOC_DELAY_MS);
  }

  console.log(`\n=== Done: ${ok}/${BULLETINS.length} succeeded ===`);
  if (failed.length > 0) {
    console.log("Failed bulletins (adjust page numbers and retry, or download manually):");
    for (const b of failed) {
      const ark = GALLICA_VOLUMES[b.vol];
      console.log(`  Bulletin ${b.bulletin_num} (${b.date}): https://gallica.bnf.fr/ark:/12148/${ark}/f${b.pages[0]}.texteImage`);
    }
    console.log("\nFor manual download: navigate to the URL above, find the bulletin,");
    console.log("then call downloadCurrentPage() from the console to grab the text.");
  }
  console.log("\nMove downloaded files to:");
  console.log("  cases/napoleon/corpus/raw/napoleon-src-02-grande-armee-bulletins/");
}

// --- Single-page helper ---
// Navigate to any Gallica page in text mode (URL ending .texteImage or .texteBrut),
// then call this to download the current page's OCR text.
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
