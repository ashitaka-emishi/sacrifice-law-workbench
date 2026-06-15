/**
 * Founders Online — Washington General Orders batch downloader
 *
 * HOW TO USE:
 *   1. Go to https://founders.archives.gov/ in your browser and let it load fully.
 *   2. Open DevTools → Console.
 *   3. Paste this entire script and press Enter.
 *   4. The script fetches each document in sequence, extracts the plain text,
 *      and downloads it as a .txt file to your Downloads folder.
 *   5. Move the downloaded files into:
 *        cases/am-rev/corpus/raw/am-rev-src-03-washington-general-orders/
 *
 * WHAT IT DOWNLOADS (7 documents):
 *   - washington-orders-1775-07-04-first-independence-day.txt
 *   - washington-orders-1776-02-09-winter-encampment.txt
 *   - washington-orders-1776-07-02-eve-of-declaration.txt
 *   - washington-orders-1776-08-30-after-long-island.txt
 *   - washington-orders-1776-12-25-trenton-eve.txt
 *   - washington-orders-1783-06-08-farewell-circular.txt
 *   - washington-orders-1783-06-17-wars-end.txt
 *
 * NOTE: Founders Online loads documents via internal async calls. This snippet
 * fetches the document page HTML, then extracts the main text content.
 * If a download produces an empty or error file, open that document URL manually
 * and use the single-document snippet at the bottom of this file.
 */

const DOCUMENTS = [
  {
    id: "03-01-02-0004",
    date: "1775-07-04",
    slug: "first-independence-day",
  },
  {
    id: "03-06-02-0138",
    date: "1776-02-09",
    slug: "winter-encampment",
  },
  {
    id: "03-07-02-0355",
    date: "1776-07-02",
    slug: "eve-of-declaration",
  },
  {
    id: "03-09-02-0023",
    date: "1776-08-30",
    slug: "after-long-island",
  },
  {
    id: "03-13-02-0177",
    date: "1776-12-25",
    slug: "trenton-eve",
  },
  {
    id: "03-13-02-0371",
    date: "1783-06-08",
    slug: "farewell-circular",
  },
  {
    id: "03-26-02-0001",
    date: "1783-06-17",
    slug: "wars-end",
  },
];

const PROVENANCE_HEADER = (doc, url) =>
  `SOURCE: Founders Online, National Archives\n` +
  `URL: ${url}\n` +
  `FOUNDERS_ONLINE_ID: ${doc.id}\n` +
  `TITLE: General Orders / Circular Letter\n` +
  `AUTHOR: George Washington\n` +
  `DATE: ${doc.date}\n` +
  `RIGHTS: Public domain (NHPRC transcription)\n` +
  `ACQUISITION_DATE: ${new Date().toISOString().slice(0, 10)}\n` +
  `\n`;

function extractText(html) {
  const parser = new DOMParser();
  const doc = parser.parseFromString(html, "text/html");

  // Founders Online wraps document body in several possible containers.
  // Try each selector in priority order.
  const selectors = [
    ".document-content",
    ".doc-content",
    "#document-content",
    "article.document",
    ".founders-doc",
    "main .content",
    ".field-items",
    "main",
  ];

  for (const sel of selectors) {
    const el = doc.querySelector(sel);
    if (el && el.innerText && el.innerText.trim().length > 200) {
      return el.innerText.trim();
    }
    if (el && el.textContent && el.textContent.trim().length > 200) {
      return el.textContent.trim();
    }
  }

  // Fallback: strip all tags from body
  const body = doc.querySelector("body");
  if (body) {
    return body.textContent.replace(/\s{3,}/g, "\n\n").trim();
  }
  return "";
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

async function fetchDocument(doc) {
  const url = `https://founders.archives.gov/documents/Washington/${doc.id}`;
  const filename = `washington-orders-${doc.date}-${doc.slug}.txt`;

  console.log(`Fetching ${doc.id} (${doc.date})...`);

  let html;
  try {
    // Founders Online returns 202 on first request then processes async.
    // Poll up to 10 times with 2s delay.
    for (let attempt = 0; attempt < 10; attempt++) {
      const resp = await fetch(url, { credentials: "include" });
      if (resp.status === 200) {
        html = await resp.text();
        if (html.length > 1000) break;
      }
      if (attempt < 9) {
        console.log(`  ${doc.id}: got status ${resp.status}, retrying in 2s (attempt ${attempt + 1}/10)...`);
        await new Promise((r) => setTimeout(r, 2000));
      }
    }
  } catch (err) {
    console.error(`  ${doc.id}: fetch error — ${err.message}`);
    return false;
  }

  if (!html || html.length < 500) {
    console.warn(`  ${doc.id}: response too short (${html ? html.length : 0} chars). Try manual download.`);
    console.warn(`  Manual URL: ${url}`);
    return false;
  }

  const bodyText = extractText(html);

  if (bodyText.length < 200) {
    console.warn(`  ${doc.id}: extracted text too short (${bodyText.length} chars). Saving raw for inspection.`);
    download(filename.replace(".txt", "-RAW.html"), html);
    return false;
  }

  const provenance = PROVENANCE_HEADER(doc, url);
  download(filename, provenance + bodyText);
  console.log(`  ✓ Downloaded: ${filename} (${bodyText.length} chars)`);
  return true;
}

async function runAll() {
  console.log("=== Founders Online Washington Orders Downloader ===");
  console.log(`Downloading ${DOCUMENTS.length} documents with 3s delay between requests...`);

  let ok = 0;
  let failed = [];

  for (const doc of DOCUMENTS) {
    const success = await fetchDocument(doc);
    if (success) {
      ok++;
    } else {
      failed.push(doc);
    }
    // Polite delay between requests
    await new Promise((r) => setTimeout(r, 3000));
  }

  console.log(`\n=== Done: ${ok}/${DOCUMENTS.length} succeeded ===`);
  if (failed.length > 0) {
    console.log("Failed documents (open manually):");
    for (const doc of failed) {
      console.log(`  https://founders.archives.gov/documents/Washington/${doc.id}`);
    }
    console.log("\nFor manual download, open the URL, then paste this into the console:");
    console.log("  downloadCurrentDocument()");
  }
}

// --- Single-document helper ---
// If the batch fails for a specific document, navigate to that document's URL
// in the browser, wait for it to fully load, then call this function.
function downloadCurrentDocument() {
  const url = window.location.href;
  const idMatch = url.match(/Washington\/([^/?#]+)/);
  const docId = idMatch ? idMatch[1] : "unknown";
  const filename = `washington-orders-${docId}.txt`;

  const selectors = [
    ".document-content",
    ".doc-content",
    "#document-content",
    "article.document",
    ".founders-doc",
    "main .content",
    ".field-items",
    "main",
  ];

  let text = "";
  for (const sel of selectors) {
    const el = document.querySelector(sel);
    if (el && el.innerText && el.innerText.trim().length > 200) {
      text = el.innerText.trim();
      break;
    }
  }
  if (!text) {
    text = document.body.innerText;
  }

  const provenance =
    `SOURCE: Founders Online, National Archives\n` +
    `URL: ${url}\n` +
    `FOUNDERS_ONLINE_ID: ${docId}\n` +
    `AUTHOR: George Washington\n` +
    `RIGHTS: Public domain (NHPRC transcription)\n` +
    `ACQUISITION_DATE: ${new Date().toISOString().slice(0, 10)}\n\n`;

  const blob = new Blob([provenance + text], { type: "text/plain;charset=utf-8" });
  const a = Object.assign(document.createElement("a"), {
    href: URL.createObjectURL(blob),
    download: filename,
  });
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  console.log(`Downloaded: ${filename}`);
}

// Run
runAll();
