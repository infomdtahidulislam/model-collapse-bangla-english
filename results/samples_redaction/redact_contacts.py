"""Release redaction (2026-10-22): replace e-mail addresses and phone-number-formatted strings in the model-written
continuations ("text" field) of the released 50-sample files with [EMAIL] / [PHONE]. The real 12-word prefixes are scanned
too (none matched). Writes redacted copies, a per-file count log, and the SHA-256 of every original and redacted file.
Usage: python redact_contacts.py <samples_dir> <out_dir>"""
import hashlib, json, re, sys, pathlib, csv
src, out = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
# phone formats: separated digit groups such as 555-123-4567, (555) 123-4567, +1 555 123 4567, 01711.234.567
PHONE_FMT = re.compile(r"(?<![\w.])(?:\+\d{1,3}[\s.-]?)?\(?\d{2,5}\)?[\s.-]\d{3,4}[\s.-]\d{3,4}(?:[\s.-]\d{2,4})?(?![\w])")
# unformatted digit runs (7 to 15 digits) only when a phone keyword precedes them within 25 characters
KEYWORD = re.compile(r"(phone|tel\b|telephone|call|fax|mobile|whatsapp|contact|ফোন|মোবাইল|যোগাযোগ|টেলিফোন)", re.I)
DIGITS = re.compile(r"(?<!\d)\+?\d{7,15}(?!\d)")
def redact(t):
    """Return (redacted text, e-mails, formatted phones, keyword-preceded digit runs)."""
    n_e = len(EMAIL.findall(t)); t = EMAIL.sub("[EMAIL]", t)
    n_p = len(PHONE_FMT.findall(t)); t = PHONE_FMT.sub("[PHONE]", t)
    hits = []
    def kw(m):
        if KEYWORD.search(t[max(0, m.start() - 25):m.start()]):
            hits.append(1); return "[PHONE]"
        return m.group(0)
    t = DIGITS.sub(kw, t)
    return t, n_e, n_p, len(hits)
out.mkdir(parents=True, exist_ok=True)
log = []
for f in sorted(src.glob("*.jsonl")):
    rows_out, ne, np_, nk, npre = [], 0, 0, 0, 0
    for line in f.read_text(encoding="utf-8").splitlines():
        r = json.loads(line)
        npre += len(EMAIL.findall(r["prefix"])) + len(PHONE_FMT.findall(r["prefix"]))
        t, e, p, k = redact(r["text"])
        r["text"] = t; ne += e; np_ += p; nk += k
        rows_out.append(json.dumps(r, ensure_ascii=False))
    data = ("\n".join(rows_out) + "\n").encode("utf-8")
    (out / f.name).write_bytes(data)
    log.append({"file": f.name, "emails": ne, "phones_formatted": np_, "phones_keyword": nk, "prefix_matches": npre,
                "sha256_original": hashlib.sha256(f.read_bytes()).hexdigest(), "sha256_redacted": hashlib.sha256(data).hexdigest()})
with open(out.parent / "redaction_log.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=list(log[0])); w.writeheader(); w.writerows(log)
tot = {k: sum(r[k] for r in log) for k in ("emails", "phones_formatted", "phones_keyword", "prefix_matches")}
print(len(log), "files;", tot, "; files changed:", sum(1 for r in log if r["sha256_original"] != r["sha256_redacted"]))
