# Washington General Orders — Manual Re-Acquisition Needed

**STATUS: All 7 files contain wrong documents. Re-download required.**

The browser snippet (`founders-online-washington-orders.js`) ran but all 7
files contain wrong content. Founders Online's async document loading caused
the script to capture whatever document was already in the DOM cache instead
of the intended document. Files currently contain:

| Filename | Should be | Actually contains |
|----------|-----------|-------------------|
| 1775-07-04-first-independence-day | General Orders, 4 Jul 1775 | Commission from Continental Congress, 19 Jun 1775 |
| 1776-02-09-winter-encampment | General Orders, 9 Feb 1776 | GW to Maj. Gen. Heath, 30 Aug 1776 |
| 1776-07-02-eve-of-declaration | General Orders, 2 Jul 1776 | GW to Hancock, 27 Dec 1776 |
| 1776-08-30-after-long-island | General Orders, 30 Aug 1776 | General Orders, 30 Mar 1777 |
| 1776-12-25-trenton-eve | General Orders, 25 Dec 1776 | GW to Benjamin Rush, 12 Jan 1778 |
| 1783-06-08-farewell-circular | Circular to States, 8 Jun 1783 | Knox to GW, 4 Feb 1778 |
| 1783-06-17-wars-end | General Orders, 17 Jun 1783 | General Orders, 13 May 1780 |

## Re-download instructions (manual, per document)

For each document:
1. Open the Founders Online URL in your browser
2. Wait for the page to fully load (document text visible on screen)
3. Select all document body text, copy, paste into a new .txt file
4. Prepend the provenance header and save with the expected filename

Provenance header format:
```
SOURCE: Founders Online, National Archives
URL: https://founders.archives.gov/documents/Washington/{FOUNDERS_ID}
FOUNDERS_ONLINE_ID: {FOUNDERS_ID}
TITLE: {title}
AUTHOR: George Washington
DATE: {YYYY-MM-DD}
RIGHTS: Public domain (NHPRC transcription)
ACQUISITION_DATE: {YYYY-MM-DD}
```

## Priority documents with Founders Online URLs

1. General Orders, 4 Jul 1775 → `washington-orders-1775-07-04-first-independence-day.txt`
   https://founders.archives.gov/documents/Washington/03-01-02-0004

2. General Orders, 9 Feb 1776 → `washington-orders-1776-02-09-winter-encampment.txt`
   https://founders.archives.gov/documents/Washington/03-06-02-0138

3. General Orders, 2 Jul 1776 → `washington-orders-1776-07-02-eve-of-declaration.txt`
   https://founders.archives.gov/documents/Washington/03-07-02-0355

4. General Orders, 30 Aug 1776 → `washington-orders-1776-08-30-after-long-island.txt`
   https://founders.archives.gov/documents/Washington/03-09-02-0023

5. General Orders, 25 Dec 1776 → `washington-orders-1776-12-25-trenton-eve.txt`
   https://founders.archives.gov/documents/Washington/03-13-02-0177

6. Circular to the States, 8 Jun 1783 → `washington-orders-1783-06-08-farewell-circular.txt`
   https://founders.archives.gov/documents/Washington/99-01-02-11404

7. General Orders, 17 Jun 1783 → `washington-orders-1783-06-17-wars-end.txt`
   https://founders.archives.gov/documents/Washington/03-26-02-0001

## Notes

All texts are public domain (Founders Online NHPRC transcriptions).
Per source-registry: `git_tracking = committed`.
