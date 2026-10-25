# CG4 post-hoc GPU run — one command from your terminal

Runs the three remaining audit items on a rented RTX 4090: **#17** cross-decoder
evaluation, **#19** LaBSE dispersion sensitivity, **#18 (full)** nonword/bigram analysis
of the synthetic corpora. Everything is post-hoc and descriptive; no registered number
changes. Expected cost: **under US$2.50** (~$0.40/h for 2–4 hours).

## The one-command way

One-time setup in your terminal (any folder):

    pip install -U vastai
    vastai set api-key <YOUR_VAST_API_KEY>

Then, from inside this `posthoc_gpu_pack` folder:

    python run_from_pc.py

That single command rents the cheapest suitable RTX 4090 on your account, uploads this
folder, downloads the Drive archive on the GPU machine (the share link is baked in),
runs all three diagnostics, pulls the results back into
**`cg4_posthoc_gpu_results/`** inside this folder, and destroys the instance.
It prints a progress line every minute; the whole run is roughly 2–4 hours.

When it says DONE: tell Claude the folder is ready (it is already inside your
`Terminal gaps` folder if you ran from there), and set the Drive file
`cg4_pack_20261016-232223.tar.gz` back to **Restricted** in Google Drive.

If anything fails, the script stops, prints the log tail, and **leaves the instance
running** so the problem can be inspected; paste the output to Claude. Resume with
`python run_from_pc.py --instance <ID>`; stop billing any time with
`vastai destroy instance <ID>`.

## What is in here

| File | Role |
|---|---|
| `run_from_pc.py` | the one command: rent, upload, run, download, destroy |
| `RUN_ALL.sh` | end-to-end driver on the GPU host (deps, fetch, #17, #19, #18, pack) |
| `01_fetch.sh` | Drive download + selective extraction of the 55.7 GB archive |
| `02_cross_decoder.py` | #17: every REPLACE/topp95 checkpoint sampled under both decoders, scored under gen-0 |
| `03_labse_sensitivity.py` | #19: corruption ladder + fluent-only subsets for LaBSE dispersion |
| `04_nonword_bigram.py` | #18 full: OOV and novel-bigram composition of the synthetic corpora |
| `05_pack_results.sh` | re-pack results by hand if ever needed (RUN_ALL does it) |
| `pc_files/human_read/` | copies of the human-read CSVs (used by the optional fluent-only check) |

## Manual route (if you prefer to drive it yourself)

Rent a 4090 with **≥120 GB disk** and fast download, copy this folder to
`/workspace/posthoc_gpu_pack`, then on the host:

    cd /workspace/posthoc_gpu_pack && bash RUN_ALL.sh

and afterwards copy `cg4_posthoc_gpu_results.tar.gz` back and
`vastai destroy instance <ID>`.

## Afterwards (Claude's part)

Claude verifies the outputs against the released tables, writes them up as a dated
post-hoc analysis and adds the decision-log line. Nothing registered changes.

## Update 2026-10-20

The run happened on the VPS (REQ-032; see results/cg4_posthoc_gpu_results/README.md). The three diagnostic scripts here are now the fixed versions as run (top-k disabled at top-p 1.0, registered length caps, fixed crc32 seeds, real training corpora, registered (ix) formula and LaBSE revision); PATCH_NOTES.md and patches.diff document the changes, and the original PC versions are hashed in results/cg4_posthoc_gpu_results/code_as_run/SHA256SUMS_original_from_pc.txt. Results: results/cg4_posthoc_gpu_results/.
