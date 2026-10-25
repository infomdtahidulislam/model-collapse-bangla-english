"""Post-hoc (2026-10-22): actual training exposure per chain and generation from the archived step records (step.json in the
released sidecar bundle): optimizer steps, packed training tokens, target tokens (real, synthetic) and masked prefix tokens.
Usage: python exposure_from_step_records.py <sidecar zip> <out_dir>"""
import json, sys, zipfile, pathlib, re
import pandas as pd
z = zipfile.ZipFile(sys.argv[1]); out = pathlib.Path(sys.argv[2]); rows = []
for n in z.namelist():
    m = re.match(r"cg4_sidecars_bundle/results/chains/([^/]+)/(?:gen_(\d+)/)?step\.json$", n)
    if not m: continue
    s = json.loads(z.read(n)); t = s.get("train") or {}
    rows.append({"chain_id": m.group(1), "generation": int(m.group(2)) if m.group(2) else (0 if m.group(1).startswith("GEN0") else -1),
                 "regime": s.get("regime"), "optimizer_steps": t.get("optimizer_steps"), "train_tokens": t.get("train_tokens"),
                 "target_tokens": t.get("target_tokens"), "real_target_tokens": t.get("real_target_tokens"),
                 "synthetic_target_tokens": t.get("synthetic_target_tokens"), "masked_prefix_tokens": t.get("masked_prefix_tokens")})
d = pd.DataFrame(rows).sort_values(["chain_id", "generation"])
d.to_csv(out / "exposure_from_step_records.csv", index=False)
main = d[d.chain_id.str.match(r"^(EN|BN)-(REPLACE|ACCUMULATE|ACCUMULATE-FILTER|ACCUMULATE-SUBSAMPLE|REAL-REPEAT)$") & d.generation.between(1, 6)]
summ = main.groupby("chain_id").agg(steps_g1=("optimizer_steps", "first"), steps_g6=("optimizer_steps", "last"), steps_total_1_6=("optimizer_steps", "sum"),
                                    target_tokens_total_1_6=("target_tokens", "sum"), real_target_total=("real_target_tokens", "sum"),
                                    synthetic_target_total=("synthetic_target_tokens", "sum"))
summ.to_csv(out / "exposure_summary_g1_6.csv")
print(summ.to_string()); print(d[d.chain_id.str.startswith("GEN0")][["chain_id", "optimizer_steps", "target_tokens"]].to_string())
