# Exit-geometry sweep — 5m (read-only study)

> Offline replay over resolved **5m** bracket trades. Sweeps the **stop width** (a multiple of today's stop) against the **break-even trigger**, target held at **3R** of the scaled stop. R is normalised to the risk taken at each width (1 NEW-R = w x original stop), so widths compare directly. Intrabar resolved **adverse-first** (reused `sim_policy`). **No engine / journal / workflow / live change.**

- 5m resolved bracket trades: **182** (usable path: **182**)
- Axes: stop_widths [0.5, 1.0, 1.5, 2.0] x BE_triggers ['no_BE', 'first_green', '+0.10R', '+0.25R', '+0.50R', '+1.00R'], target=3R

## Best combo (by expectancy net of **real** fees)

**stop_width = 2.0x, BE_trigger = first_green, target = 3R** -> **-0.243 R/trade** net-real (-0.476 harsh), win 3%, n=182, BE saved 120 / cut 44.

## Full sweep (net-of-real / net-of-harsh expectancy in R)

| stop_width | BE_trigger | n | win% | net_real | net_harsh | BE_save | BE_cut |
|---:|---|---:|---:|---:|---:|---:|---:|
| 2.0x | first_green | 182 | 3% | -0.243 | -0.476 | 120 | 44 |
| 1.5x | first_green | 182 | 3% | -0.301 | -0.612 | 122 | 39 |
| 2.0x | +0.10R | 182 | 4% | -0.334 | -0.567 | 101 | 41 |
| 1.5x | +0.10R | 182 | 3% | -0.350 | -0.661 | 113 | 39 |
| 2.0x | +0.25R | 182 | 4% | -0.408 | -0.641 | 87 | 41 |
| 2.0x | +0.50R | 182 | 12% | -0.428 | -0.661 | 56 | 26 |
| 1.5x | +0.25R | 182 | 5% | -0.431 | -0.742 | 93 | 36 |
| 2.0x | +1.00R | 182 | 18% | -0.442 | -0.675 | 24 | 12 |
| 1.5x | +1.00R | 182 | 16% | -0.488 | -0.799 | 29 | 13 |
| 1.0x | first_green | 182 | 3% | -0.502 | -0.969 | 128 | 23 |
| 2.0x | no_BE | 182 | 24% | -0.504 | -0.737 | 0 | 0 |
| 1.5x | +0.50R | 182 | 7% | -0.519 | -0.830 | 65 | 31 |
| 1.5x | no_BE | 182 | 23% | -0.539 | -0.850 | 0 | 0 |
| 1.0x | +0.10R | 182 | 3% | -0.541 | -1.007 | 121 | 23 |
| 1.0x | +0.25R | 182 | 4% | -0.629 | -1.095 | 102 | 22 |
| 1.0x | +0.50R | 182 | 4% | -0.711 | -1.178 | 87 | 22 |
| 1.0x | +1.00R | 182 | 10% | -0.739 | -1.205 | 49 | 11 |
| 1.0x | no_BE | 182 | 16% | -0.841 | -1.307 | 0 | 0 |
| 0.5x | first_green | 182 | 10% | -0.956 | -1.888 | 86 | 15 |
| 0.5x | +0.10R | 182 | 10% | -0.972 | -1.905 | 83 | 15 |
| 0.5x | +0.25R | 182 | 10% | -0.972 | -1.905 | 83 | 15 |
| 0.5x | +0.50R | 182 | 10% | -1.060 | -1.993 | 67 | 15 |
| 0.5x | +1.00R | 182 | 12% | -1.076 | -2.009 | 58 | 13 |
| 0.5x | no_BE | 182 | 19% | -1.181 | -2.113 | 0 | 0 |

## Condition breakdown at the best combo (net-real R)

> `*` marks cells under ~20 trades — **hypothesis seeds, confirm out-of-sample before trusting.**

### by direction

| cell | n | net_real R |
|---|---:|---:|
| long | 122 | -0.250 |
| short | 60 | -0.229 |

### by band

| cell | n | net_real R |
|---|---:|---:|
| 50pct | 99 | -0.188 |
| 60pct | 64 | -0.290 |
| 70pct * | 15 | -0.340 |
| 80pct * | 4 | -0.480 |

### by session

| cell | n | net_real R |
|---|---:|---:|
| ny_13-21 | 80 | -0.283 |
| asia_00-08 | 42 | -0.185 |
| late_21-24 | 32 | -0.204 |
| london_08-13 | 28 | -0.259 |

### by symbol

| cell | n | net_real R |
|---|---:|---:|
| SOLUSDT * | 11 | -0.202 |
| BNBUSDT * | 10 | +0.148 |
| BTCUSDT * | 7 | -0.310 |
| XRPUSDT * | 7 | -0.207 |
| AVAXUSDT * | 7 | -0.243 |
| DOTUSDT * | 6 | -0.357 |
| ADAUSDT * | 6 | -0.162 |
| LINKUSDT * | 5 | -0.291 |
| SNXUSDT * | 4 | -0.491 |
| ATOMUSDT * | 4 | -0.246 |
| DYDXUSDT * | 4 | -0.372 |
| ETHUSDT * | 3 | -0.282 |
| FILUSDT * | 3 | -0.164 |
| OPUSDT * | 3 | -0.245 |
| AAVEUSDT * | 3 | -0.113 |
| PEOPLEUSDT * | 3 | -0.231 |
| UNIUSDT * | 3 | +0.892 |
| ENJUSDT * | 3 | +0.545 |
| TIAUSDT * | 3 | -0.082 |
| NEARUSDT * | 2 | -0.099 |
| EGLDUSDT * | 2 | -0.746 |
| CELOUSDT * | 2 | -0.246 |
| NMRUSDT * | 2 | -0.959 |
| ENSUSDT * | 2 | -0.134 |
| CRVUSDT * | 2 | -0.158 |
| WLDUSDT * | 2 | -0.076 |
| TONUSDT * | 2 | -0.172 |
| SEIUSDT * | 2 | -0.169 |
| ACHUSDT * | 2 | -0.210 |
| APTUSDT * | 2 | -0.184 |
| BATUSDT * | 2 | -0.245 |
| ORDIUSDT * | 2 | -0.089 |
| DODOUSDT * | 2 | -0.598 |
| JASMYUSDT * | 2 | -0.263 |
| MAGICUSDT * | 2 | -0.214 |
| MANAUSDT * | 2 | -0.220 |
| JUPUSDT * | 2 | -0.117 |
| FETUSDT * | 2 | -0.125 |
| MASKUSDT * | 2 | -0.302 |
| SHIBUSDT * | 2 | -0.157 |
| LDOUSDT * | 2 | -0.131 |
| ALGOUSDT * | 2 | -0.139 |
| KAVAUSDT * | 2 | -0.295 |
| DOGEUSDT * | 1 | -0.395 |
| ETCUSDT * | 1 | -0.109 |
| HBARUSDT * | 1 | -0.169 |
| VETUSDT * | 1 | -0.088 |
| INJUSDT * | 1 | -0.073 |
| FLOWUSDT * | 1 | -0.281 |
| XTZUSDT * | 1 | -0.305 |
| GMXUSDT * | 1 | -0.224 |
| ZECUSDT * | 1 | -0.100 |
| KNCUSDT * | 1 | -2.790 |
| STORJUSDT * | 1 | -1.270 |
| CVCUSDT * | 1 | -1.512 |
| BNTUSDT * | 1 | -0.536 |
| BCHUSDT * | 1 | -0.161 |
| LTCUSDT * | 1 | -0.242 |
| TRXUSDT * | 1 | -1.059 |
| ANKRUSDT * | 1 | -0.253 |
| GRTUSDT * | 1 | -0.215 |
| QNTUSDT * | 1 | -0.158 |
| STXUSDT * | 1 | -0.350 |
| SANDUSDT * | 1 | -0.236 |
| DASHUSDT * | 1 | -0.185 |
| OGNUSDT * | 1 | -0.328 |
| SKLUSDT * | 1 | -0.152 |
| AXSUSDT * | 1 | -0.215 |
| ROSEUSDT * | 1 | -0.094 |
| ARPAUSDT * | 1 | -0.342 |
| NEOUSDT * | 1 | -1.318 |
| SUIUSDT * | 1 | -0.212 |
| THETAUSDT * | 1 | -0.257 |
| KSMUSDT * | 1 | -0.168 |
| PYTHUSDT * | 1 | -0.157 |
| IOTAUSDT * | 1 | -0.176 |
| HIGHUSDT * | 1 | -0.013 |
| IMXUSDT * | 1 | -0.233 |
| CHZUSDT * | 1 | -0.174 |
| RLCUSDT * | 1 | -1.679 |
| RUNEUSDT * | 1 | -0.391 |
| BANDUSDT * | 1 | -1.369 |

## Sizing on the best combo's real edge (100 trades, $1,000 start)

| risk/trade | median ending $ | median worst drawdown |
|---:|---:|---:|
| 2% | 610 | 40% |
| 3% | 475 | 53% |
| 5% | 283 | 72% |

**Quarter-Kelly suggested risk:** <= 0% (edge says DO NOT BET)

## Caveats

- cells under ~20 trades are hypothesis seeds, confirm out-of-sample before trusting.
- R is normalised to the risk taken at each stop width (1 NEW-R = w*original stop).
- intrabar resolved ADVERSE-FIRST (reused sim_policy); BE never over-credited.
- expectancy is net of the labelled friction model; touches are not guaranteed fills.
- 5m sample pools the §44 VWAP-flip regime; descriptive, not causal.

_Not financial advice. Offline analysis/simulation only — no live changes made._
