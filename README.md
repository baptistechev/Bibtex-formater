# bib_parser.py

A BibTeX bibliography cleaner and formatter. It normalises `.bib` files by correcting entry types, pruning unnecessary fields, abbreviating author names, replacing journal names with their standard abbreviations, and flagging missing or suspicious data.

---

## Features

- **Entry-type correction** — detects arXiv preprints and reclassifies them as `unpublished`
- **Field pruning** — removes fields that are not required, optional, or explicitly kept for a given entry type
- **Author formatting** — truncates long author lists (configurable limit) and optionally abbreviates first names (`Baptiste Dupont` → `B. Dupont`)
- **Journal abbreviation** — replaces full journal names with their standard abbreviations via a lookup file; warns when a name is unrecognised
- **Validation warnings** — prints a report of missing required fields, missing optional fields (for books and proceedings), and potentially wrong journal names
- **Sorted output** — entries in the output file are sorted by entry type

---

## Requirements

- Python 3.6+
- No third-party dependencies

---

## Usage

```bash
python bib_parser.py <file.bib>
```

The cleaned file is written next to the input file with the suffix `_parsed.bib`:

```
references.bib  →  references_parsed.bib
```

---

## Journal abbreviation file

The script looks for `journal_abbrev.txt` in the **current working directory**. Each line has the format:

```
ABBREVIATION|Full Journal Name
```

Example:
```
Phys. Rev. Lett.|Physical Review Letters
J. Fluid Mech.|Journal of Fluid Mechanics
```

If the file is not found, a warning is printed and journal replacement is skipped.

---

## Configuration

At the top of `bib_parser.py` there are two user-facing constants:

| Constant | Default | Description |
|---|---|---|
| `auth_lim` | `10` | Maximum number of authors before the list is truncated with `and others` |
| `ABBREVIATE_FIRST_NAMES` | `True` | When `True`, first and middle names are reduced to initials |

---

## Supported entry types

| Type | Description |
|---|---|
| `article` | Journal article |
| `inproceedings` | Paper in conference proceedings |
| `book` | Full book |
| `incollection` | Titled part of a book |
| `unpublished` | Preprints and other unpublished work |
| `misc` | Anything else (websites, software, …) |

Entries with a type not in this list are kept as-is with a warning.

---

## Validation output

While processing, the script prints:

- `Missing field: FIELD for type [tag]` — a required field is absent
- `Optional field missing: field for type [tag]` — an optional field (edition, volume, pages) is absent for a book or incollection
- `Journal 'name' may be incorrect or missing abbreviation for entry [tag]` — the journal name was not found in either the full-name lookup or the known-abbreviations set
- `Unknown type 'type' for entry [tag]` — unrecognised entry type

---

## Example

```bash
$ python bib_parser.py refs.bib

 Number of entries found : 42

Journal 'Nature' may be incorrect or missing abbreviation for entry [smith2023]
Missing field: VOLUME for article [doe2021]

Output written to: refs_parsed.bib
```
