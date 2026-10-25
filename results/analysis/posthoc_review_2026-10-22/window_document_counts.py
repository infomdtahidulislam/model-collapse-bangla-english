"""Post-hoc (2026-10-22): approximate number of sample documents that fill the registered 50,000-word distinct-n window,
from each step's registered mean continuation length (50,000 / mean_length_words). Usage: python window_document_counts.py <T1_metrics.csv> <out_dir>"""
import sys, pathlib, pandas as pd
d = pd.read_csv(sys.argv[1]); out = pathlib.Path(sys.argv[2])
m = d[(d.metric == "mean_length_words") & (d.generation.between(0, 6))].copy()
m["docs_in_window"] = 50000 / m.value
t = m.groupby(["language", "chain_id"]).docs_in_window.agg(["min", "max"]).reset_index()
t.to_csv(out / "window_document_counts.csv", index=False, float_format="%.1f")
print(t.round(1).to_string()); print(m.groupby("language").docs_in_window.agg(["min", "max"]).round(1))
