/**
 * University of Michigan Lincoln Studies — Lyceum Address downloader
 *
 * HOW TO USE:
 *   1. Go to https://quod.lib.umich.edu/l/lincoln/ in your browser.
 *      The Lyceum Address is at:
 *      https://quod.lib.umich.edu/l/lincoln/lincoln1/1:13?rgn=div1;view=fulltext
 *   2. Wait for the page to fully load.
 *   3. Open DevTools → Console.
 *   4. Paste this entire script and press Enter.
 *   5. A file named lincoln-lyceum-address-umich.txt will download.
 *   6. Move it to:
 *        cases/lincoln/corpus/raw/lincoln-src-01-lyceum-address.txt
 *      (overwriting the Gutenberg version if you prefer this source)
 *
 * WHY: The U Michigan Collected Works (Basler ed.) is the standard scholarly
 * edition and corrects the date error present in the Gutenberg/Lapsley text
 * (Lapsley prints "January 27, 1837"; Basler corrects to 1838).
 * The Gutenberg version already in the corpus notes this error.
 * Use this snippet if you want the Basler text directly.
 */

function extractUMichText() {
  // U Michigan Lincoln Studies wraps text in #content or .TextSection
  const selectors = [
    "#content",
    ".TextSection",
    ".text",
    "div[id^='div']",
    "main",
  ];

  for (const sel of selectors) {
    const el = document.querySelector(sel);
    if (el && el.innerText && el.innerText.trim().length > 1000) {
      return el.innerText.trim();
    }
  }

  // Fallback: full body text minus nav
  const nav = document.querySelector("nav, #navbar, .navbar, header");
  if (nav) nav.remove();
  return document.body.innerText.trim();
}

function downloadLyceumAddress() {
  const url = window.location.href;
  const text = extractUMichText();

  if (text.length < 500) {
    console.warn("Extracted text looks too short — page may not have loaded fully.");
    console.warn("Wait for the page to load completely and try again.");
    return;
  }

  const provenance =
    `SOURCE: University of Michigan Lincoln Studies Center — Collected Works of Abraham Lincoln\n` +
    `URL: ${url}\n` +
    `TITLE: The Perpetuation of Our Political Institutions (Lyceum Address)\n` +
    `AUTHOR: Abraham Lincoln\n` +
    `DATE: 1838-01-27\n` +
    `EDITION: Collected Works of Abraham Lincoln, vol. 1, ed. Roy P. Basler (Rutgers UP, 1953)\n` +
    `RIGHTS: Public domain (speech text); Basler editorial apparatus may carry separate copyright\n` +
    `ACQUISITION_DATE: ${new Date().toISOString().slice(0, 10)}\n` +
    `NOTE: Preferred over Gutenberg/Lapsley text — Basler corrects date to 1838.\n\n`;

  const blob = new Blob([provenance + text], { type: "text/plain;charset=utf-8" });
  const a = Object.assign(document.createElement("a"), {
    href: URL.createObjectURL(blob),
    download: "lincoln-lyceum-address-umich.txt",
  });
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  console.log(`Downloaded: lincoln-lyceum-address-umich.txt (${text.length} chars)`);
}

downloadLyceumAddress();
