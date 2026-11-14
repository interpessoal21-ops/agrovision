"""Transparent annual Earth-system trend statistics.

Mann-Kendall, Hamed-Rao variance correction, Sen slope and a circular
moving-block residual bootstrap interval. These methods do not establish
causation; the Hamed-Rao correction is an approximation and requires care
with short or irregular series.
"""
from __future__ import annotations
import math
from itertools import combinations
import numpy as np


def _clean_pairs(years, values):
    pairs=[]
    for year,value in zip(years,values):
        try: y,v=float(year),float(value)
        except (TypeError,ValueError): continue
        if math.isfinite(y) and math.isfinite(v): pairs.append((y,v))
    pairs.sort(key=lambda item:item[0])
    if len({y for y,_ in pairs})!=len(pairs): raise ValueError("Each year must occur only once.")
    if len(pairs)<8: raise ValueError("At least eight valid annual observations are required.")
    if any(pairs[i+1][0]-pairs[i][0] != 1 for i in range(len(pairs)-1)):
        raise ValueError("Autocorrelation-aware analysis requires consecutive annual observations without gaps.")
    return pairs


def _mk_core(values):
    vals=list(map(float,values)); n=len(vals)
    s=sum((vals[j]>vals[i])-(vals[j]<vals[i]) for i,j in combinations(range(n),2))
    from collections import Counter
    tie_sum=sum(c*(c-1)*(2*c+5) for c in Counter(vals).values() if c>1)
    var_s=(n*(n-1)*(2*n+5)-tie_sum)/18.0
    z=0.0 if var_s<=0 or s==0 else (s-1 if s>0 else s+1)/math.sqrt(var_s)
    return s,var_s,z,math.erfc(abs(z)/math.sqrt(2))


def mann_kendall(years,values,autocorrelation="hamed-rao"):
    pairs=_clean_pairs(years,values); vals=np.asarray([v for _,v in pairs],dtype=float); n=len(vals)
    s,var_s,z,p=_mk_core(vals)
    variance_corrected=var_s; correction=1.0; significant_lags=[]
    if autocorrelation not in ("hamed-rao","none"):
        raise ValueError("autocorrelation must be 'hamed-rao' or 'none'.")
    if autocorrelation=="hamed-rao" and var_s>0:
        ranks=np.argsort(np.argsort(vals)).astype(float)+1
        ranks-=ranks.mean()
        denom=float(np.dot(ranks,ranks))
        rho=[]
        for lag in range(1,n):
            rho.append(float(np.dot(ranks[:-lag],ranks[lag:])/denom) if denom else 0.0)
        # Hamed-Rao variance correction; only statistically significant rank ACF lags.
        cutoff=1.96/math.sqrt(n)
        for lag,r in enumerate(rho,1):
            if abs(r)>cutoff:
                significant_lags.append(lag)
        if significant_lags:
            factor=1.0
            for lag in significant_lags:
                factor += 2.0*(n-lag)*(n-lag-1)*(n-lag-2)*rho[lag-1]/(n*(n-1)*(n-2)) if n>2 else 0.0
            correction=max(1.0/n,min(3.0,factor))
            variance_corrected=var_s*correction
        z=0.0 if s==0 else (s-1 if s>0 else s+1)/math.sqrt(variance_corrected)
        p=math.erfc(abs(z)/math.sqrt(2))
    tau=s/(n*(n-1)/2)
    return {"n":n,"s":int(s),"tau":float(tau),"variance_s":float(var_s),
            "variance_corrected":float(variance_corrected),"variance_correction_factor":float(correction),
            "z":float(z),"p_value":float(p),"autocorrelation_method":autocorrelation,
            "adjusted_lags":significant_lags}


def sens_slope(years,values):
    pairs=_clean_pairs(years,values)
    slopes=[(v2-v1)/(y2-y1) for (y1,v1),(y2,v2) in combinations(pairs,2)]
    return float(np.median(slopes))


def sen_slope_block_bootstrap_ci(years,values,confidence=0.95,replicates=1000,block_length=None,seed=42):
    """Circular moving-block bootstrap of detrended residuals; reproducible percentile CI."""
    pairs=_clean_pairs(years,values); years_arr=np.asarray([p[0] for p in pairs]); vals=np.asarray([p[1] for p in pairs])
    if not 0.5 < confidence < 1: raise ValueError("confidence must be between 0.5 and 1.")
    if replicates<200: raise ValueError("Use at least 200 bootstrap replicates.")
    n=len(vals); slope=sens_slope(years_arr,vals)
    intercept=float(np.median(vals-slope*(years_arr-years_arr[0])))
    fitted=intercept+slope*(years_arr-years_arr[0]); residual=vals-fitted
    block_length=block_length or max(2,int(round(n**(1/3))))
    if not 1<=block_length<=n: raise ValueError("block_length must be between 1 and sample size.")
    rng=np.random.default_rng(seed); estimates=[]
    blocks=math.ceil(n/block_length)
    for _ in range(replicates):
        starts=rng.integers(0,n,size=blocks)
        sampled=np.concatenate([residual[(start+np.arange(block_length))%n] for start in starts])[:n]
        estimates.append(sens_slope(years_arr,fitted+sampled))
    alpha=(1-confidence)/2
    lo,hi=np.quantile(estimates,[alpha,1-alpha])
    return {"lower":float(lo),"upper":float(hi),"confidence":float(confidence),
            "replicates":int(replicates),"block_length":int(block_length),"seed":int(seed),
            "method":"circular moving-block bootstrap of detrended residuals"}


def analyze_annual_series(years,values,alpha=0.05,autocorrelation="hamed-rao",bootstrap_replicates=1000,seed=42):
    pairs=_clean_pairs(years,values); ys=[p[0] for p in pairs]; vs=[p[1] for p in pairs]
    mk=mann_kendall(ys,vs,autocorrelation=autocorrelation); slope=sens_slope(ys,vs)
    ci=sen_slope_block_bootstrap_ci(ys,vs,replicates=bootstrap_replicates,seed=seed)
    p=mk["p_value"]
    return {**mk,"sen_slope_per_year":slope,"sen_slope_ci":ci,
            "direction":"increasing" if slope>0 else "decreasing" if slope<0 else "no monotonic direction",
            "significant_at_alpha":bool(p<alpha),"alpha":float(alpha),
            "first_year":int(ys[0]),"last_year":int(ys[-1]),
            "first_value":float(vs[0]),"last_value":float(vs[-1])}
