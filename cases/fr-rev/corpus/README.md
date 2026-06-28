# French Revolution / Jacobin Republic Corpus

Status: draft corpus added for the pre-v1 expansion window.

This case uses French source text from Project Gutenberg ebook 29887. The
committed raw files are extracted sections from the public-domain source volume,
not modern English translations.

Annotation policy:

- annotate the French source text;
- use English glosses only as analytical aids;
- mark translation-sensitive lexical choices, especially `vertu`, `patrie`,
  `peuple`, `terreur`, `salut public`, and `Etre suprême`;
- do not commit modern English translations without a separate rights review.

Regenerate the raw selected speeches with:

```bash
python3 scripts/extract-fr-rev-speeches.py
```
