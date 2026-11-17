"""Read-only discovery. No trading credentials or endpoints."""
import requests
from datetime import datetime, timezone
from engine import market_price
BASE = 'https://api.elections.kalshi.com/trade-api/v2'

def fetch_json(session, path, params=None):
    r=session.get(BASE+path,params=params,timeout=22,headers={'User-Agent':'KalshiGuardResearch/5.0'})
    r.raise_for_status()
    return r.json()

def sports_series(session, max_pages=10):
    """Discover sports series from Kalshi series metadata, not hardcoded league tickers."""
    found={};cursor=None;pages=0;errors=[]
    for _ in range(max_pages):
        params={'category':'Sports','limit':200}
        if cursor:params['cursor']=cursor
        try:data=fetch_json(session,'/series',params)
        except (requests.RequestException,ValueError) as e:
            errors.append(f'Series discovery failed: {type(e).__name__}: {e}');break
        pages+=1
        for s in data.get('series',[]):
            if str(s.get('category','')).casefold()!='sports':continue
            t=s.get('ticker')
            if t:found[t]=s
        nxt=data.get('cursor')
        if not nxt or nxt==cursor:break
        cursor=nxt
    return list(found.values()),{'pages':pages,'truncated':bool(cursor and pages>=max_pages),'errors':errors}

def scan_series(session,series,max_pages=2,max_series=60):
    rows=[];errors=[];scanned=0;page_count=0
    selected=series[:max_series]
    for s in selected:
        ticker=s.get('ticker','')
        cursor=None
        for _ in range(max_pages):
            params={'series_ticker':ticker,'status':'open','limit':200,'with_nested_markets':'true'}
            if cursor:params['cursor']=cursor
            try:data=fetch_json(session,'/events',params)
            except (requests.RequestException,ValueError) as e:
                errors.append(f'{ticker}: {type(e).__name__}: {e}');break
            page_count+=1
            for event in data.get('events',[]):
                for m in event.get('markets',[]):
                    price=market_price(m)
                    if price is None:continue
                    rows.append({'sport':s.get('title') or ticker,'series_ticker':ticker,
                        'event_ticker':event.get('event_ticker',''), 'ticker':m.get('ticker',''),
                        'title':m.get('title') or event.get('title',''), 'yes_ask':price,
                        'volume':m.get('volume',0),'close_time':m.get('close_time',''),
                        'market_at':datetime.now(timezone.utc).isoformat(timespec='seconds'),
                        'league':s.get('title') or ticker})
            nxt=data.get('cursor')
            if not nxt or nxt==cursor:break
            cursor=nxt
        scanned+=1
    return rows,{'series_scanned':scanned,'series_available':len(series),
                 'series_capped':len(series)>max_series,'pages_requested':page_count,
                 'per_series_page_limit':max_pages,'errors':errors}
