CREATE TABLE IF NOT EXISTS daily_levels (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  recorded_at  TEXT NOT NULL,           -- ISO UTC timestamp of the bar
  date         TEXT NOT NULL,           -- YYYY-MM-DD NY session date
  symbol       TEXT NOT NULL,
  timeframe    TEXT NOT NULL DEFAULT '1h',

  -- M-levels (Traders Reality grid)
  mlevel_m0    REAL,  -- midpoint S3-S2 (deep support)
  mlevel_m1    REAL,  -- midpoint S2-S1
  mlevel_m2    REAL,  -- midpoint S1-PP (below pivot)
  mlevel_m3    REAL,  -- midpoint PP-R1 (above pivot)
  mlevel_m4    REAL,  -- midpoint R1-R2
  mlevel_m5    REAL,  -- midpoint R2-R3 (deep resistance)

  -- Floor pivots
  pivot_pp     REAL,
  pivot_r1     REAL, pivot_r2 REAL, pivot_r3 REAL,
  pivot_s1     REAL, pivot_s2 REAL, pivot_s3 REAL,

  -- Daily/weekly/monthly opens
  daily_open   REAL,
  weekly_open  REAL,
  monthly_open REAL,

  -- Prior day/week
  pdh          REAL,  -- prior day high
  pdl          REAL,  -- prior day low
  pwh          REAL,  -- prior week high
  pwl          REAL,  -- prior week low
  prev_day_color REAL, -- +1 green / -1 red

  -- Session levels
  asian_high   REAL,  asian_low  REAL,
  asian_open   REAL,  ny_open    REAL,
  prior_ny_high REAL, prior_ny_low REAL,

  -- Brinks boxes
  brinks_high  REAL,  brinks_low    REAL,  -- London (08-09 UTC)
  ny_brinks_high REAL, ny_brinks_low REAL, -- NY (08-09 NY)

  -- ADR / AWR / AMR bands
  adr          REAL,
  adr_high     REAL,  adr_low  REAL,
  awr          REAL,
  awr_high     REAL,  awr_low  REAL,
  amr          REAL,
  amr_high     REAL,  amr_low  REAL,

  -- Round numbers
  round_above  REAL,  round_below REAL,

  -- EMA stack
  ema_5        REAL,  ema_13  REAL,  ema_50  REAL,
  ema_200      REAL,  ema_800 REAL,
  ema_cloud_pos INTEGER, -- +1 above / -1 below / 0 inside

  -- Weekly IB box (available Wed+)
  week_ib_high REAL,  week_ib_low REAL,

  -- Range consumption
  pct_adr_used REAL,
  pct_awr_used REAL,

  -- Day context
  day_of_week  INTEGER,  -- 0=Mon..4=Fri
  level_day    INTEGER,  -- TR level day 1-4

  UNIQUE(date, symbol, timeframe)
);

CREATE TABLE IF NOT EXISTS unrecovered_vectors (
  id             INTEGER PRIMARY KEY AUTOINCREMENT,
  symbol         TEXT NOT NULL,
  timeframe      TEXT NOT NULL,
  candle_time    TEXT NOT NULL,   -- timestamp of the climax candle
  candle_type    TEXT NOT NULL,   -- 'bull_climax' | 'bear_climax'
                                  -- 'bull_rising'  | 'bear_rising' (opt-in)
  body_open      REAL NOT NULL,
  body_close     REAL NOT NULL,
  candle_high    REAL NOT NULL,
  candle_low     REAL NOT NULL,
  volume         REAL,

  -- Recovery tracking
  active         INTEGER NOT NULL DEFAULT 1,  -- 1 = unrecovered
  recovery_price REAL,            -- price that touched the candle zone
  recovered_at   TEXT,            -- timestamp of recovery
  days_open      INTEGER,         -- updated each run: today - candle_date

  created_at     TEXT NOT NULL DEFAULT (datetime('now')),
  UNIQUE(symbol, timeframe, candle_time)
);

CREATE TABLE IF NOT EXISTS session_analytics (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  date            TEXT NOT NULL,
  symbol          TEXT NOT NULL,

  -- Asia session behavior
  asia_direction  TEXT,          -- 'bull' | 'bear' | 'choppy'
  asia_range_pips REAL,
  asia_high       REAL,
  asia_low        REAL,

  -- NY behavior (filled at end of NY session)
  ny_first_move   TEXT,          -- 'above_asia_h' | 'below_asia_l' | 'inside'
  ny_reversed     INTEGER,       -- 1 if NY faked one way then reversed
  ny_reversal_bar TEXT,          -- timestamp of the reversal bar

  -- Day classification
  day_type        TEXT,          -- 'trend' | 'reversal' | 'choppy' | 'fake_monday'
  day_of_week     INTEGER,
  net_range_pips  REAL,

  UNIQUE(date, symbol)
);
