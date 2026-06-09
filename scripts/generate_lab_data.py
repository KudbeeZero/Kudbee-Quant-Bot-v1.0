"""Generate REAL chart data (assets/js/lab-data.js) from the live engine."""
import json
import numpy as np
import pandas as pd
from kudbee_quant.ingest import load_ohlcv
from kudbee_quant.levels import build_levels
from kudbee_quant.confluence.stack import confluence_position
from kudbee_quant.backtest.money import trade_log, simulate_account
from kudbee_quant.backtest.bracket import bracket_backtest, bracket_excursions
from kudbee_quant.scenarios.patterns import double_top_bottom_break

CRYPTO=["binance:BTCUSDT","binance:ETHUSDT","binance:BNBUSDT","binance:SOLUSDT",
        "binance:XRPUSDT","binance:ADAUSDT","binance:DOGEUSDT","binance:AVAXUSDT",
        "binance:LINKUSDT","binance:DOTUSDT"]
STOCKS=["yahoo:SPY","yahoo:AAPL","yahoo:NVDA","yahoo:MSFT","yahoo:TSLA","yahoo:AMZN"]
INT="1h"; LIM=4000; STOP=1.5; TR=3.0; RETR=0.25; MINPCT=0.5; FEE=0.0004

def frames(specs):
    out={}
    for s in specs:
        try: out[s]=build_levels(load_ohlcv(s,interval=INT,limit=LIM))
        except Exception as e: print("skip",s,str(e)[:40])
    return out

print("loading crypto..."); FC=frames(CRYPTO)
print("loading stocks..."); FS=frames(STOCKS)

def ds(arr,k=160):  # downsample to <=k points
    if len(arr)<=k: return [round(float(x),4) for x in arr]
    idx=np.linspace(0,len(arr)-1,k).astype(int)
    return [round(float(arr[i]),4) for i in idx]

# --- Equity curves (confluence trades, last 300) ---
logs=[]
for s,df in FC.items():
    lg=trade_log(df,confluence_position(df,min_pct=MINPCT),stop_atr=STOP,target_r=TR,
                 fee_pct=FEE,limit_retrace_atr=RETR); logs.append(lg)
allt=pd.concat(logs,ignore_index=True).sort_values("timestamp").reset_index(drop=True)
sample=allt.tail(300).reset_index(drop=True)
modes=[("10x full notional","full_notional",None,10.0),
       ("10% risk / trade","fixed_fractional",0.10,10.0),
       ("2% risk / trade","fixed_fractional",0.02,10.0),
       ("1% risk / trade","fixed_fractional",0.01,10.0)]
equity={"labels":[], "curves":{}}
for name,mode,rf,lev in modes:
    r=simulate_account(sample,100.0,mode=mode,risk_frac=rf or 0.02,leverage=lev)
    equity["curves"][name]={"curve":ds(r.equity_curve),"final":round(r.equity_final,2),
        "ret":round(r.ret_pct,0),"dd":round(r.max_drawdown_pct,1),"ruined":r.ruined,
        "risk":round(r.avg_risk_pct,1)}
equity["sample"]={"n":len(sample),"exp":round(float(sample["net_r"].mean()),3),
    "win":round(float((sample["net_r"]>0).mean())*100,0),
    "stop":round(float(sample["stop_pct"].mean())*100,2)}

# --- MFE survival (TP1 vs TP2) ---
def survival(F):
    ex=pd.concat([bracket_excursions(df,confluence_position(df,min_pct=MINPCT),
        stop_atr=STOP,limit_retrace_atr=RETR) for df in F.values()],ignore_index=True)
    m=ex["mfe_r"].to_numpy()
    return {"n":int(len(m)),"pts":[[X,round(float((m>=X).mean())*100,0)]
            for X in [0.5,1,1.5,2,2.5,3,3.5,4]]}
surv={"crypto":survival(FC),"stocks":survival(FS)}

# --- Expectancy by fee (pooled) ---
def exp_by_fee(F):
    out={}
    for lbl,fee in [("0%",0.0),("0.02%",0.0002),("0.04%",0.0004),("0.20%",0.0020)]:
        tr=[]
        for df in F.values():
            tr+=list(bracket_backtest(df,confluence_position(df,min_pct=MINPCT),
                stop_atr=STOP,target_r=TR,fee_pct=fee,limit_retrace_atr=RETR,
                entry_window=6).trades)
        out[lbl]=round(float(np.mean(tr)),3)
    return out
expfee={"crypto":exp_by_fee(FC),"stocks":exp_by_fee(FS)}

# --- Double top/bottom pattern ---
pe=[]; pn=0
for df in FC.values():
    res=bracket_backtest(df,double_top_bottom_break(df,tol_atr=0.5),stop_atr=STOP,
        target_r=TR,fee_pct=FEE,limit_retrace_atr=RETR,entry_window=6)
    if res.n_trades>=5: pe.append(res.expectancy_r); pn+=res.n_trades
pattern={"mean":round(float(np.mean(pe)),3),"pos":round(sum(1 for x in pe if x>0)/len(pe)*100,0),
         "n":pn}

# --- LONG vs SHORT vs BOTH (the two-sided backtest scenario) ---
def stat(d):
    return {"n":int(len(d)),"exp":round(float(d["net_r"].mean()),3) if len(d) else 0.0,
            "win":round(float((d["net_r"]>0).mean())*100,0) if len(d) else 0.0,
            "total":round(float(d["net_r"].sum()),1) if len(d) else 0.0}
longs=allt[allt["direction"]>0]; shorts=allt[allt["direction"]<0]
def eq_curve(d):
    if not len(d): return [100.0]
    s=simulate_account(d.reset_index(drop=True),100.0,mode="fixed_fractional",risk_frac=0.01,leverage=1.0)
    return ds(s.equity_curve,120)
longshort={"long":stat(longs),"short":stat(shorts),"both":stat(allt),
           "curves":{"long":eq_curve(longs),"short":eq_curve(shorts),"both":eq_curve(allt)}}

# --- Exchange fee comparison (round-trip MAKER cost, the strategy's real cost) ---
venues=[
 {"name":"MEXC (futures promo)","rt":0.0000},
 {"name":"US stocks (commission-free)","rt":0.00020},
 {"name":"Hyperliquid","rt":0.00030},
 {"name":"Bybit (perp)","rt":0.00040},
 {"name":"Binance (futures)","rt":0.00040},
 {"name":"dYdX","rt":0.00040},
 {"name":"Coinbase (taker, typical)","rt":0.00120},
 {"name":"Binance (spot, BNB disc.)","rt":0.00150},
 {"name":"Kraken","rt":0.00320},
]

DATA={"equity":equity,"survival":surv,"expfee":expfee,"pattern":pattern,
      "longshort":longshort,"venues":venues,
      "generated":"2026-06-09","assets":{"crypto":len(FC),"stocks":len(FS)}}
out="window.KUDBEE_LAB = "+json.dumps(DATA,separators=(",",":"))+";\n"
open("assets/js/lab-data.js","w").write(out)
print("wrote assets/js/lab-data.js",len(out),"bytes")
print(json.dumps(DATA,indent=1)[:600])
