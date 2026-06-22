# Volume-ranked universe — backtest before wiring (run 2026-06-22)

The owner asked to scan the top 30-40 most-liquid pairs. This is the backtest-first answer (per our honesty rule: not validated unless a test backs it). Static validated forward book = `TOP_10_CRYPTO`; this study only measures whether the WIDER ranked universe adds edge.

```
Ranking the liquid candidate pool by mean USD (quote) volume...
Ranked 40 symbols (most-liquid first):
    1. BTCUSDT     avg_quote_vol=38,234,520  [core]
    2. ETHUSDT     avg_quote_vol=18,683,860  [core]
    3. SOLUSDT     avg_quote_vol=6,965,150  [core]
    4. XRPUSDT     avg_quote_vol=4,459,638  [core]
    5. BNBUSDT     avg_quote_vol=3,154,688  [core]
    6. NEARUSDT    avg_quote_vol=1,996,459  [core]
    7. XLMUSDT     avg_quote_vol=1,693,297  [core]
    8. UNIUSDT     avg_quote_vol=1,398,115  [core]
    9. TRXUSDT     avg_quote_vol=1,397,017  [core]
   10. DOGEUSDT    avg_quote_vol=1,307,857  [core]
   11. SUIUSDT     avg_quote_vol=1,098,850
   12. AVAXUSDT    avg_quote_vol=1,066,455
   13. ADAUSDT     avg_quote_vol=893,843
   14. PEPEUSDT    avg_quote_vol=545,466
   15. LINKUSDT    avg_quote_vol=527,448
   16. AAVEUSDT    avg_quote_vol=459,491
   17. LTCUSDT     avg_quote_vol=430,327
   18. BCHUSDT     avg_quote_vol=397,888
   19. INJUSDT     avg_quote_vol=363,780
   20. HBARUSDT    avg_quote_vol=337,286
   21. ICPUSDT     avg_quote_vol=258,541
   22. MKRUSDT     avg_quote_vol=254,376
   23. FILUSDT     avg_quote_vol=239,151
   24. AXSUSDT     avg_quote_vol=226,036
   25. DOTUSDT     avg_quote_vol=216,004
   26. TIAUSDT     avg_quote_vol=198,055
   27. APTUSDT     avg_quote_vol=176,959
   28. LDOUSDT     avg_quote_vol=148,363
   29. ARBUSDT     avg_quote_vol=129,351
   30. SEIUSDT     avg_quote_vol=127,630
   31. SHIBUSDT    avg_quote_vol=110,353
   32. ALGOUSDT    avg_quote_vol=107,517
   33. SANDUSDT    avg_quote_vol=104,146
   34. OPUSDT      avg_quote_vol=93,183
   35. ETCUSDT     avg_quote_vol=84,031
   36. ATOMUSDT    avg_quote_vol=74,033
   37. MANAUSDT    avg_quote_vol=41,220
   38. RUNEUSDT    avg_quote_vol=35,586
   39. GRTUSDT     avg_quote_vol=32,021
   40. VETUSDT     avg_quote_vol=27,870

Fetching 1h history + building levels (this takes a minute)...

==========================================================================
POOLED net-of-fees R-expectancy on the canonical validated bracket
(confluence>=0.5, 3.0R target, 1.5-ATR stop, maker retrace, fee_pct=0.0004)
==========================================================================

CORE (top-10 by vol):
    IN-SAMPLE          n= 896  expectancy=-0.0125R  win%=33.0  totalR=-11.2
    OUT-OF-SAMPLE      n= 368  expectancy=-0.0072R  win%=32.1  totalR=-2.6

TAIL (ranks 11-40):
    IN-SAMPLE          n=2682  expectancy=-0.0251R  win%=33.9  totalR=-67.3
    OUT-OF-SAMPLE      n=1087  expectancy=+0.0373R  win%=34.5  totalR=+40.5

ALL (top-40):
    IN-SAMPLE          n=3578  expectancy=-0.0219R  win%=33.7  totalR=-78.5
    OUT-OF-SAMPLE      n=1455  expectancy=+0.0260R  win%=33.9  totalR=+37.9

--------------------------------------------------------------------------
OOS pooled expectancy:  core -0.0072R   tail +0.0373R   (tail - core = +0.0444R)

==========================================================================
Significance-gated universe harness (walk-forward + Monte-Carlo) on the TAIL
==========================================================================
  frac profitable OOS : 3%
  median OOS Sharpe   : -2.598
  median P(profit)    : 0.02
  effective N (corr-adj): 1.3 of 30
  robust?             : False
  verdict             : Edge NOT established: profitable OOS on 3% of 30 assets (~1.3 independent), median OOS Sharpe -2.60. Promising but unproven — see notes.
   - Assets are highly correlated (median rho 0.79): 30 assets behave like ~1.3 independent bets. 'Profitable on most' is therefore much weaker evidence than the headline count, and a rising market alone can carry a long-biased strategy. Add uncorrelated assets / regimes.
   - Not profitable OOS on: SUIUSDT, AVAXUSDT, ADAUSDT, PEPEUSDT, LINKUSDT, LTCUSDT, BCHUSDT, INJUSDT, HBARUSDT, ICPUSDT, MKRUSDT, FILUSDT, AXSUSDT, DOTUSDT, TIAUSDT, APTUSDT, LDOUSDT, ARBUSDT, SEIUSDT, SHIBUSDT, ALGOUSDT, SANDUSDT, OPUSDT, ETCUSDT, ATOMUSDT, MANAUSDT, RUNEUSDT, GRTUSDT, VETUSDT.
   - Drawdowns are large (worst -62%) even when profitable — this is not a 'low risk' strategy regardless of the return.

==========================================================================
RECONCILED VERDICT (pooled-R + significance harness must agree)
==========================================================================
  🟡 DO NOT WIRE — pooled R is marginally positive OOS but the significance harness REJECTS it (not robust): the tail's apparent gain is concentrated in a few correlated assets over one OOS regime, not a stable cross-asset edge. Keep the validated top-10 only. Re-test on more history / across regimes before reconsidering.
```
