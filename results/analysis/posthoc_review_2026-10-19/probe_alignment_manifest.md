# Probe-alignment manifest (post-hoc, 2026-10-19)

Derived from the frozen probe files `data/probes/EN_tail_facts.jsonl` and `BN_tail_facts.jsonl`.

- EN: 600 probes, 600 distinct (subject, relation, object) triples, 600 distinct subject QIDs, 4 relations, strata: {'HEAD': 200, 'MID': 200, 'TAIL': 200}
- BN: 600 probes, 600 distinct (subject, relation, object) triples, 600 distinct subject QIDs, 4 relations, strata: {'HEAD': 200, 'MID': 200, 'TAIL': 200}

## Cross-language overlap

- Shared (subject, relation, object) triples: 108 (18.0% of EN, 18.0% of BN)
- Shared (subject, relation) pairs: 108 (18.0% of EN, 18.0% of BN)
- Shared subject QIDs: 108 (18.0% of EN, 18.0% of BN)

## Relation x stratum crosstab

### EN

| relation | HEAD | MID | TAIL | total |
|---|---|---|---|---|
| P106 | 85 | 84 | 66 | 235 |
| P17 | 7 | 6 | 4 | 17 |
| P19 | 79 | 91 | 71 | 241 |
| P36 | 29 | 19 | 59 | 107 |

### BN

| relation | HEAD | MID | TAIL | total |
|---|---|---|---|---|
| P106 | 65 | 78 | 81 | 224 |
| P17 | 6 | 4 | 8 | 18 |
| P19 | 62 | 85 | 61 | 208 |
| P36 | 67 | 33 | 50 | 150 |
