import json
import requests
import pandas as pd
import streamlit as st
from datetime import datetime, timezone
from discovery import sports_series,scan_series
from engine import gate,evaluate,combos
from classify import classify
from smart import candidates

st.set_page_config(page_title='Kalshi Guard v5 — All Sports',page_icon='🛡️',layout='wide')
st.title('🛡️ Kalshi Guard v6 | Sports & Combos')
st.caption('Read-only public market research • Android-friendly • No trading account or API key')
st.warning('NOT AN AUTOMATIC PICK FINDER. Prices are not predictions. Injuries/news, calibrated models, and executable combo quotes are not connected. No verified favorable plays are generated.')

with st.sidebar:
    st.header('Scan controls')
    series_pages=st.slider('Sports series discovery pages',1,20,5)
    series_cap=st.slider('Maximum series to scan',5,200,60,5)
    event_pages=st.slider('Event pages per series',1,5,2)
    st.caption('Higher limits mean more API requests. A capped scan is not full coverage.')
    if st.button('Clear cached results'):
        discover.clear();scan.clear()
    st.markdown('[Kalshi public API documentation](https://docs.kalshi.com/)')

@st.cache_data(ttl=600,show_spinner=False)
def discover(pages):
    with requests.Session() as session:return sports_series(session,pages)

@st.cache_data(ttl=120,show_spinner=False)
def scan(series,max_pages,max_series):
    with requests.Session() as session:return scan_series(session,series,max_pages,max_series)

market_tab,smart_tab,review_tab,combo_tab,about_tab=st.tabs(['🎯 Plays by sport','🧠 Smart combos (2–6)','🩺 Evidence review','🧮 Manual scenarios','ℹ️ Details'])
with market_tab:
    if st.button('Scan Kalshi sports markets',type='primary'):
        with st.spinner('Discovering sports series and retrieving public markets...'):
            series,disc=discover(series_pages)
            st.session_state['series']=series
            st.session_state['discovery']=disc
            if series:
                rows,coverage=scan(series,event_pages,series_cap)
                st.session_state['rows']=rows
                st.session_state['coverage']=coverage
            else:
                st.session_state['rows']=[]
                st.session_state['coverage']={'errors':['No Sports series returned; API schema or availability may differ']}
    disc=st.session_state.get('discovery',{})
    coverage=st.session_state.get('coverage',{})
    rows=st.session_state.get('rows',[])
    if disc or coverage:
        a,b,c=st.columns(3)
        a.metric('Sports series discovered',len(st.session_state.get('series',[])))
        b.metric('Series scanned',coverage.get('series_scanned',0))
        c.metric('Quoted markets returned',len(rows))
        if disc.get('truncated') or coverage.get('series_capped'):
            st.warning('PARTIAL COVERAGE: Scan limits reached. Do not interpret results as every sports market.')
        if disc.get('errors') or coverage.get('errors'):
            st.error('Some requests failed. Coverage incomplete. '+ '; '.join((disc.get('errors',[])+coverage.get('errors',[]))[:5]))
        st.caption('Sports discovery relies on Kalshi series metadata. The API can change, and no scan guarantees every sports market. Open markets without valid quoted asks are omitted.')
    if rows:
        df=pd.DataFrame(rows)
        df[['category','level']]=pd.DataFrame([classify(r) for r in rows],index=df.index)
        sports=sorted(df['category'].dropna().unique())
        selected=st.selectbox('Sport', ['All sports']+sports)
        filtered=df if selected=='All sports' else df[df['category']==selected]
        levels=sorted(filtered['level'].dropna().unique())
        level=st.selectbox('Level / league', ['All levels']+levels)
        shown=filtered if level=='All levels' else filtered[filtered['level']==level]
        shown=shown.copy()
        query=st.text_input('Search teams, markets or tickers')
        if query:shown=shown[shown['title'].str.contains(query,case=False,na=False,regex=False)|shown['ticker'].str.contains(query,case=False,na=False,regex=False)]
        plays_tab,technical_tab=st.tabs(['🎯 Plays & payouts','🔎 Market details'])
        with plays_tab:
            st.caption('Prices imply break-even odds, NOT a model-estimated chance of winning. All returns are before fees. No picks are certified favorable.')
            stake=st.number_input('Example budget ($)',min_value=1.0,max_value=100000.0,value=10.0,step=5.0)
            shown=shown.sort_values(['category','level','title'])
            st.caption(f'{len(shown)} quoted YES markets • Showing first 100; use filters to narrow results')
            for _,r in shown.head(100).iterrows():
                price=float(r['yes_ask'])
                if not 0<price<1:continue
                # Kalshi YES contracts settle for $1; show an affordable whole-contract example.
                contracts=int((stake+1e-9)//price)
                cost=contracts*price
                payout=float(contracts)
                profit=payout-cost
                roi=(profit/cost*100) if cost else 0
                with st.container(border=True):
                    st.markdown(f"**{r['title']}**")
                    st.caption(f"{r['category']}  •  {r['level']}")
                    a,b,c=st.columns(3)
                    a.metric('YES price / implied odds',f'{price*100:.1f}¢ / {price*100:.1f}%')
                    if contracts:
                        b.metric('Gross payout',f'${payout:,.2f}')
                        c.metric('Potential profit',f'${profit:,.2f}',f'({roi:.1f}% before fees)',delta_color='off')
                        st.caption(f'Example: {contracts} whole contracts costing ${cost:.2f} of your ${stake:.2f} budget; pays ${payout:.2f} only if YES wins. Fees excluded.')
                    else:
                        b.metric('Gross payout','—')
                        c.metric('Potential profit','—')
                        st.caption('Budget too small for one contract at the displayed price.')
            if len(shown)>100:st.info('Only the first 100 matches are displayed. Narrow the sport or search to see more.')
        with technical_tab:
            st.caption('Raw market information for auditing and troubleshooting.')
            st.dataframe(shown[['category','level','sport','title','yes_ask','volume','ticker','event_ticker','close_time','market_at']],hide_index=True,use_container_width=True)
            st.download_button('Export market snapshot',shown.to_csv(index=False),'kalshi_all_sports_snapshot.csv','text/csv')
    else:st.info('Press Scan Kalshi sports markets to begin. No demo markets are substituted for missing live data.')

with smart_tab:
    st.subheader('Smart combos | 2 to 6 plays')
    st.warning('RESEARCH ONLY: These combinations use multiplied single-market ask prices, NOT actual Kalshi combo quotes. They do not use independent win predictions or verified injury/news feeds. They are NOT favorable-play recommendations.')
    rows=st.session_state.get('rows',[])
    if not rows:
        st.info('Scan sports markets on the Plays tab first.')
    else:
        annotated=[]
        for r in rows:
            category,level=classify(r)
            annotated.append({**r,'category':category,'level':level})
        categories=sorted({r['category'] for r in annotated})
        sport=st.selectbox('Combo sport', ['All sports']+categories,key='combo_sport')
        scoped=[r for r in annotated if sport=='All sports' or r['category']==sport]
        levels=sorted({r['level'] for r in scoped})
        level=st.selectbox('Combo level', ['All levels']+levels,key='combo_level')
        scoped=[r for r in scoped if level=='All levels' or r['level']==level]
        size=st.select_slider('Number of plays',options=[2,3,4,5,6],value=2)
        stake=st.number_input('Illustrative stake ($)',min_value=1.0,value=10.0,step=5.0,key='combo_stake')
        st.caption('Candidate pool limited to 30 markets and 25 results for speed. One leg per event; other correlations are not modeled. Prices can change.')
        results=candidates(scoped,size,stake)
        if not results:
            st.info('Not enough distinct games with quoted prices for this combo size and filter.')
        else:
            for item in results:
                with st.container(border=True):
                    st.markdown('**'+item['plays']+'**')
                    st.caption(item['levels']+' • Unverified synthetic scenario')
                    a,b,c=st.columns(3)
                    a.metric('Synthetic implied odds',f"{item['synthetic_implied_probability']:.1%}")
                    b.metric('Hypothetical payout',f"${item['hypothetical_gross_payout']:,.2f}")
                    c.metric('Profit (ROI)',f"${item['hypothetical_profit']:,.2f}",f"({item['hypothetical_roi_pct']:.1f}%)",delta_color='off')
            st.download_button('Export scenarios',pd.DataFrame(results).to_csv(index=False),'kalshi_combo_scenarios.csv','text/csv')

with review_tab:
    rows=st.session_state.get('rows',[])
    st.write('Manual evidence entry only. A user-provided URL is not independently verified. Every sport requires its own reliable sources and model.')
    if not rows:st.info('Scan markets first.')
    else:
        choices={f"{r['sport']} | {r['title']} [{r['ticker']}]":r for r in rows}
        label=st.selectbox('Select market',list(choices))
        r=choices[label]
        with st.form('review'):
            lineup=st.selectbox('Lineup/participant status',['Unknown','Confirmed','Unconfirmed'])
            injury=st.selectbox('Injury, suspension or absence review',['Unknown','Reviewed','Unresolved'])
            news=st.selectbox('News and conditions review',['Unknown','Reviewed','Unresolved'])
            url=st.text_input('Evidence source HTTPS URL')
            model=st.selectbox('Independent model status',['Unvalidated','Validated'])
            st.caption('Validated means independently backtested and calibrated; selecting it does not make it true.')
            low=st.number_input('Lower probability %',1.0,99.0,40.0)
            mid=st.number_input('Central probability %',1.0,99.0,50.0)
            high=st.number_input('Upper probability %',1.0,99.0,60.0)
            saved=st.form_submit_button('Save manual review')
        if saved:
            if low<=mid<=high:
                st.session_state.setdefault('reviews',{})[r['ticker']]={**r,'lineup':lineup,'injury':injury,'news':news,'source_url':url,'evidence_at':datetime.now(timezone.utc).isoformat(),'model':model,'p_low':low/100,'p_mid':mid/100,'p_high':high/100}
                st.success('Saved in this browser session. Not independently authenticated.')
            else:st.error('Probabilities must satisfy lower ≤ central ≤ upper.')
        reviews=list(st.session_state.get('reviews',{}).values())
        if reviews:
            st.dataframe(pd.DataFrame([{'market':x['title'],'sport':x['sport'],'data_quality_issues':'; '.join(gate(x)) or 'Format checks passed; external evidence still unverified'} for x in reviews]),hide_index=True,use_container_width=True)
            st.download_button('Export evidence JSON',json.dumps(reviews,indent=2),'evidence.json','application/json')

with combo_tab:
    reviews=list(st.session_state.get('reviews',{}).values())
    st.warning('These are hypothetical scenarios, NOT executable Kalshi combos or recommendations. Different games are not necessarily statistically independent.')
    size=st.radio('Leg count',[2,3],horizontal=True)
    if len(reviews)<size:st.info(f'Save at least {size} distinct-event reviews first.')
    else:
        options={f"{r['title']} [{r['ticker']}]":r for r in reviews}
        chosen=st.multiselect('Select legs',list(options),max_selections=size)
        stress=st.slider('Conservative joint probability haircut (percentage points)',0,25,5)/100
        quote=st.checkbox('Enter a separate combo quote manually (not verified)')
        if quote:
            cost=st.number_input('Cost ($)',min_value=.01,value=10.0)
            payout=st.number_input('Gross payout ($)',min_value=.01,value=25.0)
            fees=st.number_input('Fees ($)',min_value=0.0,value=0.0)
        else:cost=payout=None;fees=0
        if len(chosen)==size:
            result=evaluate([options[x] for x in chosen],cost,payout,fees,stress)
            st.metric('Conservative scenario probability',f"{result.get('p_conservative',0):.1%}")
            st.metric('Central scenario probability',f"{result.get('p_central',0):.1%}")
            if 'ev_low' in result:st.metric('Illustrative conservative EV',f"${result['ev_low']:.2f}")
            st.error('BLOCKED: No verified favorable play')
            for issue in result['issues']:st.write('• '+issue)
        if st.checkbox('Show scenario combinations'):
            results=combos(reviews,size)
            if results:
                df=pd.DataFrame(results)
                st.dataframe(df,hide_index=True,use_container_width=True)
                st.download_button('Export scenario CSV',df.to_csv(index=False),'scenarios.csv','text/csv')

with about_tab:
    st.markdown('''### What this version actually does
- Discovers series categorized **Sports** through the public Kalshi API, then retrieves a bounded sample of open events and quoted YES markets across those series.
- Lets you filter and export the resulting market snapshot.
- Supports manual evidence reviews and illustrative two-/three-leg scenario calculations.

### What it cannot do yet
- Guarantee that **all** sports markets were discovered or scanned. Limits, API errors and missing ask quotes reduce coverage.
- Automatically verify injuries, suspensions, starting lineups, weather or news across sports.
- Estimate calibrated probabilities from a trained, independently tested model.
- Obtain executable combo RFQ prices or certify positive expected value.
- Place trades, access accounts or identify verified favorable picks.

**All results are research-only.** Markets without usable quoted YES asks are omitted. No fallback or invented prices are used.
''')
