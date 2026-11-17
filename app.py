import io
from datetime import datetime, timezone
import pandas as pd
import requests
import streamlit as st
from engine import evidence_gate,scenario,enumerate_scenarios

API='https://external-api.kalshi.com/trade-api/v2'
st.set_page_config(page_title='Kalshi Guard v3',page_icon='🛡️',layout='wide')
st.title('🛡️ Kalshi Guard v3 — NFL + NBA')
st.caption('Read-only Android-friendly research dashboard • No credentials • No orders')
st.error('NO VERIFIED PICKS: Injury, news, model and combo-quote sources are NOT automatically connected. User-provided evidence is never authenticated by this app.')

@st.cache_data(ttl=120,show_spinner=False)
def get_markets(pages):
    out=[];cursor=None
    for _ in range(pages):
        params={'status':'open','limit':200}
        if cursor: params['cursor']=cursor
        response=requests.get(API+'/markets',params=params,timeout=15,headers={'User-Agent':'KalshiGuardV3Research/1.0'})
        response.raise_for_status();payload=response.json()
        out.extend(payload.get('markets',[]))
        cursor=payload.get('cursor')
        if not cursor: break
    return out

def ask_price(m):
    for key,scale in [('yes_ask_dollars',1),('yes_ask',100)]:
        try:
            p=float(m.get(key))/scale
            if 0<p<1:return p
        except (TypeError,ValueError):pass
    return None

with st.sidebar:
    league=st.selectbox('Sport',['NFL','NBA'])
    pages=st.slider('Kalshi market pages',1,20,5)
    query=st.text_input('Search market text','')
    st.caption('Public market retrieval is paginated and keyword matching is imperfect. No market result is a verified game pick.')
    st.markdown('[Official Kalshi API documentation](https://docs.kalshi.com/)')

market_tab,evidence_tab,combo_tab,guide_tab=st.tabs(['📊 Markets','🩺 Evidence','🧮 Combo scenarios','ℹ️ Guide'])
with market_tab:
    if st.button('Refresh Kalshi market data'):
        get_markets.clear()
    try:
        markets=get_markets(pages)
        retrieved=datetime.now(timezone.utc).isoformat(timespec='seconds')
        st.success(f'Public API response received: {retrieved} UTC • {len(markets)} markets sampled')
        matches=[]
        for m in markets:
            hay=' '.join(str(m.get(k,'')) for k in ('ticker','event_ticker','title','subtitle')).upper()
            if league not in hay or (query and query.upper() not in hay):continue
            matches.append({'ticker':m.get('ticker'),'event_ticker':m.get('event_ticker'),
                'title':m.get('title'),'yes_ask_dollars':ask_price(m),
                'close_time':m.get('close_time'),'snapshot_utc':retrieved})
        st.dataframe(pd.DataFrame(matches),use_container_width=True,hide_index=True)
        if matches:st.download_button('Download market snapshot',pd.DataFrame(matches).to_csv(index=False),'market_snapshot.csv','text/csv')
        else:st.info('No matches in this limited sample. This does not mean the sport has no available markets.')
    except Exception as exc:
        st.warning(f'Kalshi public API unavailable: {type(exc).__name__}: {exc}. No fake market prices are substituted.')

columns=['league','game_id','selection','source_kind','source_url','evidence_at','lineup','injuries',
         'suspensions','news','news_at','model_status','model_reference','model_at','p_low','p_mid','p_high','notes']
now=datetime.now(timezone.utc).isoformat(timespec='seconds')
template=pd.DataFrame([{'league':'NFL','game_id':'EXAMPLE-1','selection':'EXAMPLE TEAM A',
 'source_kind':'unverified','source_url':'','evidence_at':'','lineup':'unknown','injuries':'unknown',
 'suspensions':'unknown','news':'unreviewed','news_at':'','model_status':'unvalidated',
 'model_reference':'','model_at':'','p_low':0.40,'p_mid':0.50,'p_high':0.60,'notes':'EXAMPLE ONLY'}],columns=columns)
with evidence_tab:
    st.write('Use one row per game selection. Enter probability intervals based on an **independent model**, not simply Kalshi prices. Record evidence source URLs and timestamps. This tool checks the *format and freshness* of claims, not their truth.')
    st.download_button('Download evidence CSV template',template.to_csv(index=False),'evidence_template.csv','text/csv')
    file=st.file_uploader('Upload your evidence CSV',type='csv')
    if file:
        try:
            raw=pd.read_csv(file,dtype=str).fillna('')
            missing=set(columns)-set(raw.columns)
            if missing:st.error('Missing required columns: '+', '.join(sorted(missing)));rows=[]
            else:rows=raw.to_dict('records')
        except Exception as exc:st.error(f'CSV read failed: {exc}');rows=[]
    else:rows=[]
    if rows:
        report=[]
        for r in rows:
            problems=evidence_gate(r)
            report.append({'selection':r['selection'],'league':r['league'],'gate':'BLOCKED' if problems else 'CLAIMS PASS (UNVERIFIED)',
                           'issues':'; '.join(problems) or 'User assertions have not been authenticated'})
        st.dataframe(pd.DataFrame(report),use_container_width=True,hide_index=True)
        st.download_button('Download quality report',pd.DataFrame(report).to_csv(index=False),'quality_report.csv','text/csv')
    else:st.info('No evidence loaded. Automated injury, suspension, lineup and news feeds are not connected.')

with combo_tab:
    st.write('This calculator uses **one hypothetical total combo quote for every generated combination**. Real Kalshi combos can have different prices and availability. Never treat these results as executable prices.')
    c1,c2=st.columns(2)
    with c1:
        size=st.selectbox('Selections per combo',[2,3]);cost=st.number_input('Hypothetical total cost ($)',min_value=0.01,value=10.0)
        gross=st.number_input('Hypothetical gross payout ($)',min_value=0.01,value=30.0)
    with c2:
        fees=st.number_input('Estimated fees ($)',min_value=0.0,value=0.0)
        haircut=st.slider('Dependence/uncertainty stress (percentage points)',0,30,10)/100
        st.caption('Stress setting is a sensitivity test, NOT a learned correlation model.')
    if rows and len(rows)>=size:
        results=enumerate_scenarios(rows,size,cost,gross,fees,haircut)
        if results:
            frame=pd.DataFrame(results)
            st.dataframe(frame,use_container_width=True,hide_index=True)
            st.download_button('Export scenarios',frame.to_csv(index=False),'combo_scenarios.csv','text/csv')
            st.warning('These are hypothetical, blocked scenarios. Positive EV does NOT mean an actionable opportunity.')
        else:st.info('No distinct-game combinations available.')
    else:st.info(f'Upload at least {size} distinct games in the Evidence tab to generate scenarios.')

with guide_tab:
    st.markdown('''### What is live and what is not
- **Kalshi public markets:** fetched on demand if the API succeeds, with UTC snapshot timestamp.
- **Injuries / suspensions / lineups / news:** user-supplied CSV only; no automatic ingestion or independent source verification.
- **Win probabilities:** user-supplied ranges; no trained model, calibration, or historical validation provided.
- **Combo prices:** hypothetical inputs only; no live RFQ or executable quote integration.
- **Correlation:** a conservative stress slider, not a measured dependence model.
- **Alerts:** none in background; refresh manually. No automatic trading.

### How to improve quality
1. Obtain legitimate official/licensed team injury, lineup and news feeds with event timestamps.
2. Build separate NFL and NBA player-impact models, then backtest out-of-sample and assess calibration.
3. Add authenticated read-only access to Kalshi multivariate quote workflows where supported.
4. Only compare model probabilities against **real** quotes, fees and liquidity.
5. Track prediction history, stale-data incidents and false positives. Show **no picks** when checks fail.

### Deployment
Push `app.py`, `engine.py`, `requirements.txt` to GitHub, deploy `app.py` on Streamlit Community Cloud, and add the URL to your Android home screen. No Kalshi credentials are needed. Avoid uploading private account information or proprietary feed data to a public deployment.''')
