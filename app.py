import streamlit as st
import plotly.express as px
import plotly.graph_objs as go

import yfinance as yf

import altair as alt
import time
import requests

import numpy as np
import pandas as pd
import datetime
import calendar
from datetime import date, timedelta
import xlrd

st.set_page_config('Structured products',layout='wide')

st.title('Structured products follow up tool')

tradedate = datetime.date(2021,6,22)
valuedate = datetime.date(2021,7,6)
days_in_month = calendar.monthrange(valuedate.year,valuedate.month)[1]
memkostart = valuedate + timedelta(days=days_in_month)
fixingdate = datetime.date(2022,7,6)


dates = pd.DataFrame([tradedate,valuedate,memkostart,fixingdate],index=['Trade date','Value date','KO Memory start date','Fixing date'])
dates.columns = ['Key dates']

valuedate = datetime.date(2021,7,6)

stocklist = ['Shell','Credit Agricole','Infineon','Daimler']
strikes = [1038.6,8.9357,24.4494,59.3925]
fixings = [strike / 0.75 for strike in strikes[::-1]]
knockouts = [fixing * 0.97 for fixing in fixings]
knockins = [strike * 0.60 / 0.75 for strike in strikes[::-1]]

summarydf = pd.DataFrame([knockouts,knockins,strikes,fixings],index=['KnockOut','KnockIn','Strike','Trade price'])
summarydf.columns = stocklist[::-1]

### Boursorama ###

names = ['Shell','Credit Agricole','Infineon','Daimler']

@st.cache(suppress_st_warning=True,ttl=3600,allow_output_mutation=True)
def getprices():
    tickers = ['1uRDSB.L','1rPACA','1zIFX','1zDAI']


    bigdf = pd.DataFrame()

    for ticker in tickers:
        time.sleep(2)
        url = 'https://www.boursorama.com/bourse/action/graph/ws/GetTicksEOD?symbol='+ticker+'&length=365&period=0&guid='


        data = requests.get(url)
        df = pd.DataFrame(data.json()).loc['QuoteTab','d']
        df = pd.DataFrame.from_dict(df)

        def dayfromnumber(string):
            date = datetime.datetime.fromordinal(string)
            try:
                date = datetime.datetime(date.year+1969,date.month,date.day+1)
            except:
                date = datetime.datetime(date.year+1969,date.month,28)
            return date

        df['date'] = df['d'].apply(dayfromnumber)
        df[ticker] = df['c']
        df = df[[ticker,'date']]

        bigdf = pd.concat([df,bigdf])


    bigdf = bigdf.groupby('date').mean()

    return bigdf

# st.stop()
#
# s = yf.Ticker('RDSB.L')
# ca = yf.Ticker('ACA.PA')
# inf = yf.Ticker('IFX.DE')
# daim = yf.Ticker('DAI.DE')
#
# tickers = [s,ca,inf,daim]
#
# prices = []
# for ticker in tickers:
#     try:
#         pricelist = ticker.history(start='2021-07-06',prepost=True)['Close']
#         prices.append(pricelist)
#     except:
#         prices.append(0)
#
#
#
# dailyclose = pd.DataFrame(prices).transpose()
#
# dailyclose.columns = stocklist
#
#
# dailyclose = dailyclose[::-1]
# dailyclose.reset_index(inplace=True)
#
# dailyclose['Date']=dailyclose['Date'].apply(lambda x: datetime.date(x.year,x.month,x.day))
# dailyclose.set_index('Date',inplace=True)

dailyclose = getprices()

dailyclose.columns=names[::-1]


# Dividends

# dividends = []
# for ticker in tickers:
#     dividend = ticker.dividends
#     dividends.append(dividend)
# divdf = pd.DataFrame([dividends[i] for i in range(4)]).transpose()
# divdf.columns = stocklist

with st.beta_expander('Display key information'):

    col1,col2 = st.beta_columns(2)

    with col1:
        st.subheader('Coupon rate = 8.9%')

    with col2:
        st.subheader('Key Dates')
        st.table(dates)

    st.subheader('Key information')
    st.table(summarydf.style.format('{:.4f}'))
    # st.subheader('Dividends')
    # st.table(divdf)
    triggerstart = st.date_input('Input first observation date',datetime.date(2021,8,6))


### Triggers

st.header('Triggers met')

dailyclose.reset_index(inplace=True)

dailyclose['date'] = dailyclose['date'].apply(lambda x: datetime.date(x.year,x.month,x.day))


dailyclose.set_index('date',inplace=True)

dailyclosefilter = dailyclose[dailyclose.index>=triggerstart]

dailyclose = dailyclose[dailyclose.index>=datetime.date(2021,7,6)]
dailyclose = dailyclose[::-1]

maxprice = pd.DataFrame(dailyclosefilter.max())
maxprice.columns=['Max price']

minprice = pd.DataFrame(dailyclosefilter.min())
minprice.columns=['Min price']

summarydf = summarydf.transpose()

triggerdf = pd.concat([maxprice,minprice,summarydf],axis=1)
triggerdf = triggerdf.drop(['Strike','Trade price'],axis=1)

def isko(max,ko):
    if max>ko:
        return True
    else:
        return False

def iski(min,ki):
    if min<ki:
        return True
    else:
        return False

triggerdf['Is KO'] = triggerdf.apply(lambda x: isko(x['Max price'],x['KnockOut']),axis=1)
triggerdf['Is KI'] = triggerdf.apply(lambda x: iski(x['Min price'],x['KnockIn']),axis=1)

if triggerdf['Is KO'].sum()==4:
    st.subheader('A Knock Out event has occurred. The note will early redeem.')
elif triggerdf['Is KI'].sum()>0:
    st.subheader('WARNING: A Knock In event has occurred.')

triggerdf = triggerdf[['Is KO','Max price','KnockOut','Is KI','Min price','KnockIn']]


def highlight_trigger(x):
    if x ==1:
        color='lightgreen'
    else:
        color=''
    return 'background-color: %s'% color

def color_negative_red(val):
    color = 'red' if val < 0 else 'green'
    return 'color: %s' % color


st.table(triggerdf.style.applymap(highlight_trigger)
    .format('{:.4f}',subset=['Max price','KnockOut','Min price','KnockIn']))


st.header('Underlying variation over time')

pricechange = dailyclose / fixings -1


def highlight_change(x):
    if x >-0.03:
        color='lightgreen'
    else:
        color='red'
    return 'background-color: %s'% color



with st.beta_expander('Show daily variation'):
    st.table(dailyclose.pct_change(-1).head(5).style.format('{:.2%}').applymap(color_negative_red))

with st.beta_expander('Show variation since inception'):
    st.subheader('Stock performance')
    st.table(pricechange.head(10).style
        .format('{:.2%}',subset=stocklist)
        .applymap(highlight_change,subset=stocklist))

with st.beta_expander('Show prices'):
    st.table(dailyclose.head(5).style.format('{:.2f}'))


pricechange.reset_index(inplace=True)


# pricechange['Trading Day'] = [i+1 for i in range(len(pricechange))][::-1]
# for stock in stocklist:
#     pricechange[stock] = pd.to_numeric(pricechange[stock])
#
# maxchg = pricechange[stocklist].to_numpy().max()+0.03
# minchg = pricechange[stocklist].to_numpy().min()-0.03
#
# fig = px.line(pricechange,x='date',y=[stock for stock in stocklist])
#
# fig.update_xaxes(rangeslider_visible=True,showgrid=True,gridcolor='LightPink')
# fig.update_yaxes(range=[minchg,maxchg],showgrid=True,gridcolor='LightPink',title='Variation')
# fig.update_traces(mode='lines+markers')
# fig.update_layout(template='ggplot2',xaxis=dict(tickmode='array',tickvals=pricechange['date'],dtick=1,ticktext=[str(date)[:10] for date in pricechange['date']]),yaxis_tickformat='.2%',legend=dict(orientation='h',title='Stock'))
# st.plotly_chart(fig,use_container_width=True)

pricechange.set_index('date',inplace=True)
pricechange = pd.DataFrame(pricechange).stack()

pricechange = pd.DataFrame(pricechange).reset_index()
pricechange.columns = ['date','Stock','Variation']



highlight = alt.selection(type='interval',bind='scales',encodings=['x','y'])

fig = alt.Chart(pricechange).mark_line().encode(alt.X('date:T'),alt.Y('Variation:Q',scale=alt.Scale(domain=(-0.15,0.05)),axis=alt.Axis(format='.2%')),color='Stock:N',tooltip=[
      {"type": "temporal", "field": "date"},
      {"type": "quantitative", "field": "Variation"},
      {"type": "nominal", "field": "Stock"}]).add_selection(highlight)
line1 = alt.Chart(pd.DataFrame({'Variation':[-0.03]})).mark_rule(strokeDash=[10,10],color='green',strokeWidth=2).encode(y='Variation')

st.altair_chart(fig+line1,use_container_width=True)


with st.beta_expander('Adjust parameters'):
    stopflag = st.checkbox('Accrual stops')
    if stopflag:
        stopaccrual = st.date_input('Stop accrual',datetime.date(2021,8,6))
        d1 = stopaccrual
    else:
        d1 = datetime.date.today()
    d0 = valuedate

    nbdays = (d1-d0).days + 1

    kiflag = st.checkbox('Knock In triggered')

if kiflag == False:
    accrual = nbdays*100000*0.089/360
elif pricechange[stocklist].iloc[0].min() <= 0.6:
    accrual = nbdays*100000*0.089/360 + pricechange[stocklist].iloc[0].min()*100000
else:
    accrual = nbdays*100000*0.089/360

accrualmessage = 'Product income since inception = '+'{:.2f}'.format(accrual)+' SGD'

st.subheader(accrualmessage)
