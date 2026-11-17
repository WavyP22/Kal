"""Read-only, conservative scenario evaluation. No automatic betting recommendations."""
from datetime import datetime, timezone
from itertools import combinations
import math

def utc_now(): return datetime.now(timezone.utc)

def age_hours(value, now=None):
    try:
        dt=datetime.fromisoformat(str(value).replace('Z','+00:00'))
        if dt.tzinfo is None: return None
        return ((now or utc_now())-dt.astimezone(timezone.utc)).total_seconds()/3600
    except (TypeError, ValueError): return None

def valid_fresh(value, hours, now=None):
    age=age_hours(value,now)
    return age is not None and -0.0833 <= age <= hours

def number(v):
    try:
        x=float(v)
        return x if math.isfinite(x) else None
    except (ValueError,TypeError): return None

def evidence_gate(r, now=None):
    issues=[]
    league=str(r.get('league','')).upper()
    if league not in ('NFL','NBA'): issues.append('Unsupported league')
    if not str(r.get('game_id','')).strip(): issues.append('Missing game identifier')
    if not str(r.get('selection','')).strip(): issues.append('Missing selection')
    if str(r.get('source_kind','')).lower() not in ('official','licensed'): issues.append('Evidence source not declared official/licensed')
    if not str(r.get('source_url','')).startswith('https://'): issues.append('Missing HTTPS evidence URL')
    max_age=3 if league=='NBA' else 6
    if not valid_fresh(r.get('evidence_at'),max_age,now): issues.append(f'Evidence older than {max_age}h, future-dated or missing')
    if str(r.get('lineup','')).lower()!='confirmed': issues.append('Lineup unconfirmed')
    if str(r.get('injuries','')).lower()!='accounted_for': issues.append('Injuries not accounted for')
    if str(r.get('suspensions','')).lower()!='accounted_for': issues.append('Suspensions not accounted for')
    if str(r.get('news','')).lower()!='reviewed': issues.append('Breaking news not reviewed')
    if not valid_fresh(r.get('news_at'),3,now): issues.append('News review stale or missing')
    if str(r.get('model_status','')).lower()!='backtested': issues.append('Independent backtested model not documented')
    if not valid_fresh(r.get('model_at'),24,now): issues.append('Model estimate stale or missing')
    low,mid,high=[number(r.get(k)) for k in ('p_low','p_mid','p_high')]
    if None in (low,mid,high) or not (0<low<=mid<=high<1): issues.append('Invalid probability interval')
    if not str(r.get('model_reference','')).strip(): issues.append('Missing model methodology/reference')
    # All data in CSV is user-asserted, not independently authenticated.
    return issues

def scenario(rows, cost, gross_payout, fees=0, dependence_haircut=0.10, now=None):
    issues=[]
    if not 2<=len(rows)<=3: issues.append('Use two or three legs')
    ids=[str(r.get('game_id','')).strip() for r in rows]
    if len(set(ids))!=len(ids): issues.append('Multiple legs from one game')
    for r in rows:
        issues.extend(f"{r.get('selection','?')}: {x}" for x in evidence_gate(r,now))
    c,p,f,h=map(number,(cost,gross_payout,fees,dependence_haircut))
    if None in (c,p,f,h) or not (c>0 and p>0 and 0<=f<p and 0<=h<=0.5):
        issues.append('Invalid quote/fee/stress assumptions')
        return {'issues':issues,'eligible':False}
    lows=[number(r.get('p_low')) for r in rows]
    mids=[number(r.get('p_mid')) for r in rows]
    highs=[number(r.get('p_high')) for r in rows]
    if any(x is None or not 0<x<1 for x in lows+mids+highs):
        return {'issues':issues+['Missing probabilities'],'eligible':False}
    # Multiplication is a scenario assumption; haircut is sensitivity, not a calibrated dependence estimate.
    naive_low=math.prod(lows)
    conservative=max(0,naive_low-h)
    central=math.prod(mids)
    upper=min(1,math.prod(highs)+h)
    ev=conservative*(p-f)-c
    return {'issues':issues,'eligible':False,'low_joint':conservative,'central_joint':central,
            'high_joint':upper,'break_even':c/(p-f),'conservative_ev':ev,
            'conservative_roi':ev/c,'gross_profit':p-f-c,
            'note':'Unverified quote and self-reported evidence; scenario only. Not a favorable trade rating.'}

def enumerate_scenarios(rows, size, cost, payout, fees, haircut, now=None, limit=250):
    output=[]
    for combo in combinations(rows,size):
        if len({r.get('game_id') for r in combo})!=size: continue
        result=scenario(combo,cost,payout,fees,haircut,now)
        if 'conservative_ev' in result:
            output.append({'selections':' + '.join(str(r.get('selection')) for r in combo),
                           'game_ids':' | '.join(str(r.get('game_id')) for r in combo),
                           'conservative_probability':result['low_joint'],
                           'central_probability':result['central_joint'],
                           'break_even':result['break_even'],
                           'scenario_EV':result['conservative_ev'],
                           'blockers':'; '.join(result['issues']) or 'User claims pass; NOT independently verified',
                           'status':'SCENARIO ONLY'})
        if len(output)>=limit: break
    return sorted(output,key=lambda x:x['scenario_EV'],reverse=True)
