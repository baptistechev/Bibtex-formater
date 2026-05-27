import sys

# What this program does:
#
# - Change element type to the right category
# - Remove useless fields
# - Inform fields to fill
# - Format authors fields (number and optionally abbreviate first names)
# - Change journal name by its abbreviation
# - Check if journal may be wrong
#

# Elements type
el_type_list = ["article",
                "inproceedings",  # article in conference
                "book",
                "incollection",   # part of a book with its own title
                "unpublished",    # for e-print and others
                "misc"]           # when nothing fit (website...)

# Needed fields:
required_fields = {}
required_fields["article"]       = ["author", "title", "journal", "year", "volume", "number", "pages"]
required_fields["inproceedings"] = ["author", "title", "booktitle", "editor", "publisher", "year", "address", "pages"]
required_fields["book"]          = ["author", "title", "editor", "publisher", "year", "address"]
required_fields["incollection"]  = ["author", "title", "booktitle", "editor", "publisher", "year", "address"]
required_fields["unpublished"]   = ["author", "title", "note", "year"]
required_fields["misc"]          = ["title", "note", "urldate"]

# Optional fields (not mandatory but signaled) for book and proceedings:
optional_fields = ["edition", "volume", "pages"]

# Additional fields (kept as-is):
additional_fields = ["doi", "url", "note"]

# Authors number limit (limit included):
auth_lim = 10

# Whether to abbreviate first names (True = "Baptiste Dupont" -> "B. Dupont")
ABBREVIATE_FIRST_NAMES = True


###############################################################
################   Helper functions   #########################
###############################################################

def abbreviate_name(name):
    """
    Abbreviate first (and middle) names of a single author.
    Handles both "Last, First" and "First Last" formats.
    Preserves BibTeX braces: {Last, First} -> {Last, F.}
    """
    name = name.strip()

    # Strip outer braces for processing, restore later
    braced = name.startswith('{') and name.endswith('}')
    if braced:
        name = name[1:-1].strip()

    if ',' in name:
        # "Last, First Middle" format
        parts = name.split(',', 1)
        last = parts[0].strip()
        firsts = parts[1].strip().split()
        abbrev_firsts = []
        for f in firsts:
            if f.endswith('.'):
                abbrev_firsts.append(f)   # already abbreviated
            elif f.startswith('{') or f.startswith('\\'):
                abbrev_firsts.append(f)   # BibTeX special token, leave as-is
            elif len(f) > 0:
                abbrev_firsts.append(f[0].upper() + '.')
        result = last + ', ' + ' '.join(abbrev_firsts)
    else:
        # "First Middle Last" format — abbreviate everything except the last token
        tokens = name.split()
        if len(tokens) <= 1:
            result = name
        else:
            abbreviated = []
            for t in tokens[:-1]:
                if t.endswith('.'):
                    abbreviated.append(t)
                elif t.startswith('{') or t.startswith('\\'):
                    abbreviated.append(t)
                elif len(t) > 0:
                    abbreviated.append(t[0].upper() + '.')
            result = ' '.join(abbreviated) + ' ' + tokens[-1]

    return '{' + result + '}' if braced else result


def abbreviate_authors(author_field):
    """
    Given the raw BibTeX author field value (including surrounding braces/quotes),
    abbreviate each author's first name.
    """
    # Strip the outer { } or " " wrapper
    value = author_field.strip()
    if (value.startswith('{') and value.endswith('}')) or \
       (value.startswith('"') and value.endswith('"')):
        inner = value[1:-1]
        wrap = (value[0], value[-1])
    else:
        inner = value
        wrap = None

    # Split on " and " (case-insensitive, but BibTeX convention is lowercase)
    import re
    authors = re.split(r'\s+and\s+', inner, flags=re.IGNORECASE)
    abbreviated = [abbreviate_name(a) for a in authors]
    result = ' and '.join(abbreviated)

    if wrap:
        return wrap[0] + result + wrap[1]
    return result


def truncate_authors(author_field, limit):
    """
    If there are more than `limit` authors, keep the first `limit` and append 'and others'.
    Works on the raw BibTeX field value.
    """
    import re
    value = author_field.strip()

    if (value.startswith('{') and value.endswith('}')) or \
       (value.startswith('"') and value.endswith('"')):
        inner = value[1:-1]
        wrap = (value[0], value[-1])
    else:
        inner = value
        wrap = None

    authors = re.split(r'\s+and\s+', inner, flags=re.IGNORECASE)

    if len(authors) > limit:
        kept = [a.strip() for a in authors[:limit]]
        result = ' and '.join(kept) + ' and others'
    else:
        result = inner

    if wrap:
        return wrap[0] + result + wrap[1]
    return result


###############################################################
################   Load journal list  #########################
###############################################################

journal_list = {}          # full_name_lowercase -> abbreviation
journal_abbrevs = set()    # known abbreviations (for fast lookup)
journal_list_file = "journal_abbrev.txt"

try:
    with open(journal_list_file, "r") as f:
        for line in f:
            line = line.rstrip('\n')
            if '|' not in line:
                continue
            abbrev, journal_name = line.split('|', 1)
            journal_list[journal_name.lower()] = abbrev
            journal_abbrevs.add(abbrev)
except FileNotFoundError:
    print(f"Warning: journal abbreviation file '{journal_list_file}' not found.")


###############################################################
################   Read original file #########################
###############################################################

if len(sys.argv) < 2:
    raise SystemExit("Usage: bib_parser.py <file.bib>")

all_items = []

with open(str(sys.argv[1]), "r", encoding="utf-8") as f:
    lines = f.readlines()

i = 0

while i < len(lines):

    # Skip until we find an entry start (@type{...)
    while i < len(lines) and (len(lines[i].strip()) == 0 or lines[i].strip()[0] != '@'):
        i += 1

    if i >= len(lines):
        break

    el = {}
    header = lines[i].strip()
    i += 1

    brace_pos = header.find('{')
    if brace_pos == -1:
        continue  # malformed header, skip

    el["type"] = header[1:brace_pos].strip().lower()
    el["tag"]  = header[brace_pos + 1:].rstrip(',').strip().rstrip('}').strip()

    # Parse fields until the closing brace of the entry
    while i < len(lines):
        line = lines[i].strip()

        # Blank line — skip
        if line == "":
            i += 1
            continue

        # Closing brace of the entry
        if line == '}' or line == '},':
            i += 1
            break

        # Split field = value  (split only on first '=')
        if '=' not in line:
            i += 1
            continue

        eq_pos = line.index('=')
        field = line[:eq_pos].lower().strip()
        value = line[eq_pos + 1:].strip()

        # Accumulate continuation lines until braces are balanced
        # (allow for one extra closing brace which belongs to the entry itself)
        while i + 1 < len(lines):
            opened = value.count('{')
            closed = value.count('}')
            # Balanced value (possibly with trailing comma)
            if opened == closed:
                break
            # One extra closing brace → that brace closes the entry, not the value
            if closed == opened + 1:
                break
            i += 1
            value += '\n' + lines[i].strip()

        # Strip trailing comma and the entry-closing brace if present
        value = value.rstrip()
        opened = value.count('{')
        closed = value.count('}')
        if closed == opened + 1:
            value = value[:value.rfind('}')]  # remove last extra '}'
        if value.endswith(','):
            value = value[:-1]

        el[field] = value.strip()
        i += 1

    all_items.append(el)


###############################################################
####################  Parsing content  ########################
###############################################################

print(f"\n Number of entries found : {len(all_items)} \n")

for item in all_items:

    # Detect arXiv preprints → unpublished
    journal_val   = item.get("journal",   "")
    publisher_val = item.get("publisher", "")
    if "arXiv" in journal_val or "arXiv" in publisher_val:
        item["type"] = "unpublished"

    # For misc: surface URL as note if note is absent
    if item["type"] == "misc" and "url" in item and "note" not in item:
        item["note"] = item["url"]

    # Warn about unknown entry types but still write them out
    if item["type"] not in el_type_list:
        print(f"Unknown type '{item['type']}' for entry [{item.get('tag', '?')}] — kept as-is.")
        continue

    current_required = required_fields[item["type"]]

    # Remove fields that are not required, optional, or additional
    fields_to_remove = [
        f for f in list(item.keys())
        if f not in ("type", "tag")
        and f not in current_required
        and f not in optional_fields
        and f not in additional_fields
    ]
    for f in fields_to_remove:
        del item[f]

    # Format author field
    if "author" in item:
        item["author"] = truncate_authors(item["author"], auth_lim)
        if ABBREVIATE_FIRST_NAMES:
            item["author"] = abbreviate_authors(item["author"])

    # Journal abbreviation / validation
    if item["type"] == "article" and "journal" in item:
        raw = item["journal"].strip()
        # Strip surrounding braces/quotes for lookup
        if (raw.startswith('{') and raw.endswith('}')) or \
           (raw.startswith('"') and raw.endswith('"')):
            inner = raw[1:-1]
        else:
            inner = raw

        if inner.lower() in journal_list:
            item["journal"] = '{' + journal_list[inner.lower()] + '}'
        elif inner not in journal_abbrevs:
            print(f"Journal {raw!r} may be incorrect or missing abbreviation "
                  f"for entry [{item.get('tag', '?')}]")

    # Check for missing required fields
    already_warned_number_pages = False
    for field in current_required:
        if field not in item:
            if item["type"] == "article" and field in ("number", "pages"):
                if not already_warned_number_pages:
                    other = "pages" if field == "number" else "number"
                    if other not in item:
                        print(f"Missing field: NUMBER or PAGES in article [{item.get('tag', '?')}]")
                        already_warned_number_pages = True
            else:
                print(f"Missing field: {field.upper()} for {item['type']} [{item.get('tag', '?')}]")

    # Warn about missing optional fields for book / incollection
    if item["type"] in ("book", "incollection"):
        for field in optional_fields:
            if field not in item:
                print(f"Optional field missing: {field} for {item['type']} [{item.get('tag', '?')}]")


all_items.sort(key=lambda d: d["type"])


###############################################################
####################   Write new file #########################
###############################################################

out_path = str(sys.argv[1])[:-4] + "_parsed.bib"

with open(out_path, "w", encoding="utf-8") as f:

    for item in all_items:

        f.write(f"@{item['type']}{{{item['tag']},\n")

        entry_type = item["type"]

        # Guard against unknown types (no required_fields entry)
        if entry_type not in required_fields:
            for k, v in item.items():
                if k not in ("type", "tag"):
                    f.write(f"{k} = {v},\n")
            f.write("}\n\n")
            continue

        current_required = required_fields[entry_type]

        # Write required fields (except 'note' — handled with additional_fields)
        for field in current_required:
            if field in item and field != "note":
                f.write(f"{field} = {item[field]},\n")

        # Write optional fields for relevant types
        if entry_type in ("inproceedings", "book", "incollection"):
            for field in optional_fields:
                if field in item:
                    f.write(f"{field} = {item[field]},\n")

        # Write additional fields (doi, url, note)
        for field in additional_fields:
            if field in item:
                f.write(f"{field} = {item[field]},\n")

        f.write("}\n\n")

print(f"\nOutput written to: {out_path}")
