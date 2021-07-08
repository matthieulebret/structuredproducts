import streamlit as st
import plotly.express as px
import plotly.graph_objs as go

import yfinance as yf

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
fixings = [strike / 0.75 for strike in strikes]
knockouts = [fixing * 0.97 for fixing in fixings]
knockins = [strike * 0.60 / 0.75 for strike in strikes]

summarydf = pd.DataFrame([knockouts,knockins,strikes,fixings],index=['KnockOut','KnockIn','Strike','Trade price'])
summarydf.columns = stocklist


s = yf.Ticker('RDSB.L')
ca = yf.Ticker('ACA.PA')
inf = yf.Ticker('IFX.DE')
daim = yf.Ticker('DAI.DE')


tickers = [s,ca,inf,daim]
prices = []
for ticker in tickers:
    pricelist = ticker.history(start='2021-07-06')['Close']
    prices.append(pricelist)


dailyclose = pd.DataFrame(prices).transpose()
dailyclose.columns = stocklist
dailyclose = dailyclose[::-1]
dailyclose.reset_index(inplace=True)


dailyclose['Date']=dailyclose['Date'].apply(lambda x: datetime.date(x.year,x.month,x.day))
dailyclose.set_index('Date',inplace=True)


# Dividends

dividends = []
for ticker in tickers:
    dividend = ticker.dividends
    dividends.append(dividend)
divdf = pd.DataFrame([dividends[i] for i in range(4)]).transpose()
divdf.columns = stocklist

with st.beta_expander('Display key information'):

    col1,col2 = st.beta_columns(2)

    with col1:
        st.subheader('Coupon rate = 8.9%')

    with col2:
        st.subheader('Key Dates')
        st.table(dates)

    st.subheader('Key information')
    st.table(summarydf.style.format('{:.4f}'))
    st.subheader('Dividends')
    st.table(divdf)
    triggerstart = st.date_input('Input first observation date',datetime.date(2021,8,6))


### Triggers

st.header('Triggers met')

dailyclosefilter = dailyclose[dailyclose.index>=triggerstart]

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

dailyclose.iloc[-1] = fixings
pricechange = dailyclose / dailyclose.iloc[-1] - 1


def highlight_change(x):
    if x >-0.03:
        color='lightgreen'
    else:
        color='lightred'
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

pricechange['Trading Day'] = [i+1 for i in range(len(pricechange))][::-1]
for stock in stocklist:
    pricechange[stock] = pd.to_numeric(pricechange[stock])

maxchg = pricechange[stocklist].to_numpy().max()+0.03
minchg = pricechange[stocklist].to_numpy().min()-0.03

fig = px.line(pricechange,x='Trading Day',y=[stock for stock in stocklist])
fig.add_shape(
        type='line',
        x0=1,
        x1=len(pricechange),
        y0=-0.03,
        y1=-0.03,
        line=dict(color='MediumPurple',
            width=4,
            dash='dot'))


fig.update_xaxes(rangeslider_visible=True,showgrid=True,gridcolor='LightPink')
fig.update_yaxes(range=[minchg,maxchg],showgrid=True,gridcolor='LightPink',title='Variation')
fig.update_traces(mode='lines+markers')
fig.update_layout(template='ggplot2',xaxis=dict(tickmode='array',tickvals=pricechange['Trading Day'],dtick=1,ticktext=[str(date)[:10] for date in pricechange['Date']]),yaxis_tickformat='.2%',legend=dict(orientation='h',title='Stock'))


st.plotly_chart(fig,use_container_width=True)


pricechange.set_index('Date',inplace=True)


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
