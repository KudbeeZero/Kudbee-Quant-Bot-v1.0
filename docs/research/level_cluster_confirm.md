# Level-cluster confirmation (run 2026-06-22)

```
Loading 10 symbols @ 1h, limit=12000 ...
Baseline: IS -0.0148R (n=1388)  OOS +0.0585R (n=580)

========================================================================
PASS 1 — threshold (K stacked) x tolerance grid, OOS net-of-fees ΔR
========================================================================
    tol   K   OOS_exp        ΔR      n  verdict
   0.15   2   +0.1227   +0.0642    321  +
   0.15   3   +0.1152   +0.0567    125  +
   0.15   4   -0.0727   -0.1312     38  thin
   0.15   5   +0.1226   +0.0641      6  thin
   0.20   2   +0.0871   +0.0286    396  +
   0.20   3   +0.1780   +0.1195    211  +
   0.20   4   +0.3096   +0.2511     85  thin
   0.20   5   +0.0003   -0.0582     21  thin
   0.25   2   +0.0809   +0.0224    451  +
   0.25   3   +0.1336   +0.0751    286  +
   0.25   4   +0.1406   +0.0821    146  +
   0.25   5   +0.1111   +0.0526     49  thin

  Best non-thin OOS cell: tol=0.2 K>=3 -> +0.1780R (ΔR +0.1195, n=211)

========================================================================
PASS 2 — source ablation (tol=0.20, K>=3): drop one group, watch OOS ΔR
========================================================================
     dropped   OOS_exp        ΔR      n  edge kept
      (none)   +0.1780   +0.1195    211       100%
      mlevel   +0.1631   +0.1046    185        87%
       pivot   +0.1873   +0.1288    189       108%
        open   +0.2206   +0.1621    106       136%
       prior   +0.2083   +0.1498    150       125%
       range   +0.1905   +0.1320    200       110%
        vwap   +0.1924   +0.1339    142       112%
       round   +0.1369   +0.0784    173        66%
    prevopen   +0.2056   +0.1471    185       123%

========================================================================
PASS 3 — robustness at tol=0.20, K>=3: per-symbol OOS + bootstrap p
========================================================================
  per-symbol OOS beats baseline: 8/10 symbols
  pooled IS  ΔR +0.0301 (n=559)  bootstrap p=0.3375
  pooled OOS ΔR +0.1195 (n=211)  bootstrap p=0.1815

========================================================================
VERDICT
========================================================================
  🔴 DID NOT CONFIRM on 3x history — the SUGGESTIVE read didn't survive more data. Keep top-10 baseline; do not wire or paper it.
```

## Power test — wider universe (22 liquid symbols, 8000 bars)

```
loaded 22 symbols @ 8000 bars
baseline OOS +0.0654 n=793
cluster  OOS +0.1463 n=315  ΔR +0.0809
baseline IS  -0.0044 n=1992
cluster  IS  +0.0882 n=724  ΔR +0.0926
bootstrap p: IS 0.0707  OOS 0.2210
```

**Read:** more data makes BOTH halves clearly positive (IS ΔR +0.093, OOS ΔR +0.081) and
pulls IS p to 0.07 — but OOS p stays 0.22. The effect is consistent and dose-responsive but
**not statistically luck-proof (p>0.05 OOS)** on any sample tried. Promising near-miss, not a WINNER.
