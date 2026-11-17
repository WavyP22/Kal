import json
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import requests
import pandas as pd
import streamlit as st
from discovery import sports_series,scan_series
from classify import classify
from smart import candidates
from datefilter import TIMEZONES,day_scope,local_day
from schedule import enrich_start_times

st.set_page_config(page_title='Kalshi Guard v7.1',page_icon='🛡️',layout='wide')
st.title('🛡️ Kalshi Guard v7.1')
st.caption('Sports markets • Local-day filtering • 2–6 leg research combos • Read-only')
st.warning('Research only. No independent probability model, injury verification, executable combo quotes, or trade placement. Synthetic combo prices are NOT Kalshi offers.')

@st.cache_data(ttl=600,show_spinner=False)
def discover(pages):
    with requests.Session() as s:return sports_series(s,pages)
@st.cache_data(ttl=120,show_spinner=False)
def scan(series,pages,cap):
    with requests.Session() as s:return scan_series(s,series,pages,cap)

with st.sidebar:
    st.header('Settings')
    tz_label=st.selectbox('Time zone',list(TIMEZONES),index=0,help='Choose the time zone of your device. Eastern is the default; browser auto-detection is not available in this version.')
    tz=TIMEZONES[tz_label]
    today=datetime.now(ZoneInfo(tz)).date()
    st.caption(f'Local date: {today.isoformat()} • {tz}')
    day_choice=st.radio('Game date',['Today','Tomorrow','Choose a date'],index=0)
    chosen=today if day_choice=='Today' else today+timedelta(days=1) if day_choice=='Tomorrow' else st.date_input('Select date',value=today,min_value=today-timedelta(days=1),max_value=today+timedelta(days=30))
    st.caption(f'Showing starts on {chosen.isoformat()} (midnight to midnight local time).')
    series_pages=st.slider('Discovery pages',1,20,5)
    series_cap=st.slider('Maximum series',5,200,60,5)
    event_pages=st.slider('Event pages per series',1,5,2)
    if st.button('Clear cached scan'):
        discover.clear();scan.clear();st.session_state.pop('rows',None)
    st.caption('Scan limits can omit markets. Missing game starts are cross-checked against ESPN schedules using exact two-team matchups; ambiguous matches remain excluded.')

if st.button('🔄 Scan Kalshi sports markets',type='primary'):
    with st.spinner('Discovering and scanning public sports markets…'):
        series,disc=discover(series_pages)
        rows,coverage=scan(series,event_pages,series_cap) if series else ([],{'errors':['No sports series returned']})
        st.session_state.update(rows=rows,disc=disc,coverage=coverage,series_count=len(series))

rows=st.session_state.get('rows',[])
coverage=st.session_state.get('coverage',{})
if coverage:
    a,b,c=st.columns(3)
    a.metric('Series discovered',st.session_state.get('series_count',0))
    b.metric('Series scanned',coverage.get('series_scanned',0))
    c.metric('Quoted markets',len(rows))
    if coverage.get('series_capped') or st.session_state.get('disc',{}).get('truncated'):
        st.warning('Partial scan: configured limits were reached.')
    errors=coverage.get('errors',[])+st.session_state.get('disc',{}).get('errors',[])
    if errors:st.error('Some API calls failed: '+'; '.join(errors[:3]))

if not rows:
    st.info('Press Scan Kalshi sports markets to load live public market data. No fake plays will be displayed.')
    st.stop()

annotated=[]
for r in rows:
    cat,level=classify(r)
    annotated.append({**r,'category':cat,'level':level})
with st.spinner('Checking game schedules for missing start times…'):
    annotated=enrich_start_times(annotated,chosen,tz)
verified,unknown,other=day_scope(annotated,tz,chosen)

sport_names=sorted({r['category'] for r in verified})
a,b=st.columns(2)
with a:sport=st.selectbox('Sport',['All sports']+sport_names)
scoped=[r for r in verified if sport=='All sports' or r['category']==sport]
with b:level=st.selectbox('League / level',['All levels']+sorted({r['level'] for r in scoped}))
scoped=[r for r in scoped if level=='All levels' or r['level']==level]

plays_tab,combo_tab,unknown_tab,details_tab=st.tabs(['🎯 Day’s plays','🧠 Smart combos (2–6)','🕒 Unverified start times','🔎 Market details'])
with plays_tab:
    st.subheader(f'Games starting {chosen.strftime("%b %d, %Y")}')
    st.caption(f'{len(scoped)} quoted markets • {tz} • A YES ask is a price, not a predicted win probability.')
    stake=st.number_input('Budget ($)',min_value=1.0,value=10.0,step=5.0,key='play_budget')
    search=st.text_input('Search plays')
    display=[r for r in scoped if search.lower() in str(r.get('title','')).lower()]
    for r in display[:100]:
        p=float(r['yes_ask'])
        if not 0<p<1:continue
        contracts=int((stake+1e-9)//p)
        cost=contracts*p;profit=contracts-cost
        with st.container(border=True):
            st.markdown('**'+str(r['title'])+'**')
            dt=datetime.fromisoformat(r['game_start_time'].replace('Z','+00:00')).astimezone(ZoneInfo(tz))
            st.caption(f"{r['category']} • {r['level']} • Starts {dt.strftime('%I:%M %p')}")
            x,y,z=st.columns(3)
            x.metric('YES price / implied',f'{p*100:.1f}¢ / {p*100:.1f}%')
            y.metric('Gross payout',f'${contracts:.2f}' if contracts else '—')
            z.metric('Profit (ROI)',f'${profit:.2f}' if contracts else '—',f'({(profit/cost*100):.1f}%)' if contracts else None,delta_color='off')
            st.caption(f'{contracts} whole contracts • Cost ${cost:.2f} • Before fees • YES must win')
    if len(display)>100:st.info('First 100 shown; narrow filters to see more.')
    if not display:st.info('No games with verified start times match this date and filter. Check Unverified start times.')

with combo_tab:
    st.subheader(f'Same-day combos • {chosen.strftime("%b %d")}')
    st.warning('Generated groups are hypothetical. This app does NOT confirm that Kalshi offers these combinations as one executable trade. Do not treat the synthetic payout as a real quote.')
    n=st.select_slider('Number of picks',options=[2,3,4,5,6],value=2)
    budget=st.number_input('Example combo budget ($)',min_value=1.0,value=10.0,step=5.0,key='combo_budget')
    combos=candidates(scoped,n,budget)
    if not combos:st.info('Not enough distinct events with verified same-day starts and quoted YES prices.')
    for idx,item in enumerate(combos,1):
        with st.container(border=True):
            st.markdown(f'**Combo {idx} • {n} picks**')
            for leg in item['legs_detail']:
                st.write(f"• {leg['title']} — YES {float(leg['yes_ask'])*100:.1f}¢ ({leg['level']})")
                st.caption('Market ticker: '+str(leg['ticker']))
            x,y,z=st.columns(3)
            x.metric('Synthetic implied',f"{item['synthetic_implied_probability']:.1%}")
            y.metric('Hypothetical gross',f"${item['hypothetical_gross_payout']:.2f}")
            z.metric('Hypothetical profit',f"${item['hypothetical_profit']:.2f}",f"({item['hypothetical_roi_pct']:.1f}%)",delta_color='off')
            st.caption('Not a real Kalshi combo quote. Multiplication assumes independent legs; real prices, fees and correlations may differ.')
    if combos:
        export=[{k:v for k,v in c.items() if k!='legs_detail'} for c in combos]
        st.download_button('Export combo research',pd.DataFrame(export).to_csv(index=False),'kalshi_v7_combo_research.csv','text/csv')

with unknown_tab:
    st.subheader('Start time not verified')
    st.info(f'{len(unknown)} quoted markets could not be matched to a verified scheduled game start. They are deliberately NOT included in Today, Tomorrow or combos.')
    if unknown:
        st.dataframe(pd.DataFrame(unknown)[['category','level','title','ticker','event_ticker','close_time']],hide_index=True,use_container_width=True)
        st.download_button('Export unverified starts',pd.DataFrame(unknown).to_csv(index=False),'unverified_start_times.csv','text/csv')
    st.caption('Market close_time and expiration_time are not reliable replacements for the scheduled game start.')

with details_tab:
    st.subheader('Raw market details')
    st.caption('Includes markets from the selected day after sport/league filtering. Technical fields are hidden from the main plays view.')
    if scoped:
        st.dataframe(pd.DataFrame(scoped),hide_index=True,use_container_width=True)
        st.download_button('Export selected markets',pd.DataFrame(scoped).to_csv(index=False),'kalshi_v7_markets.csv','text/csv')
    st.write(f'Other-date markets: {len(other)} • Unverified start times: {len(unknown)}')
    st.caption('No browser timezone auto-detection, verified injuries, independently calibrated odds, or actual combo trading is implemented.')
