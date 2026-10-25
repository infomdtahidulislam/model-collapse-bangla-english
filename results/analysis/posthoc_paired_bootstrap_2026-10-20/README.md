# REQ-034: item-paired bootstrap sensitivity check (2026-10-20)

Post-hoc sensitivity analysis reported in Supplementary Section S5 of the article; decision
record REQ-034 in `signoffs/REQUESTS.md`.

**Inputs.** The per-item sidecar bundle attached to release v1.0.0
(`cg4_sidecars_from_G4b_2026-10-20.zip`, SHA-256
`cd2e94082639dadb01e6acb1b56443af755356409ce64b6b88f1a7755cdc87dc`).

**Run.** Extract the bundle into this folder (so `cg4_sidecars_bundle/results/chains/`
resolves) and run `python3 paired_boot.py` (needs numpy; about 5 s on CPU).
The script first asserts that every registered point estimate (from the released
`H0_anchor.csv`, `H_tests.csv` and `controls.csv`) is reproduced from the per-item
records to below 1e-9, then draws 10,000 item-paired resamples (fixed seed 20261020):
each draw resamples the 2,000 held-out documents / 600 probes once per language and
applies that one resample jointly to every checkpoint and arm.

**Output.** `req034_paired_bootstrap.csv`: per quantity, the point estimate, the
registered 95% CI and bootstrap p, and the item-paired 95% CI and p. Every registered
conclusion is unchanged; every item-paired interval is narrower than its registered
counterpart.
