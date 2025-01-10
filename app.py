import streamlit as st
import backtrader as bt
import yfinance as yf
import pandas as pd
import datetime

# Streamlit app title
st.title("Backtrader Strategies Comparison")

# Sidebar for user inputs
st.sidebar.header("Simulation Settings")
start_date = st.sidebar.date_input("Start Date", datetime.date(1993, 10, 1))
end_date = st.sidebar.date_input("End Date", datetime.date(2023, 10, 1))

# Fetch data
st.write(f"Fetching data for SPY from {start_date} to {end_date}...")
data = yf.download('SPY', start=start_date, end=end_date, group_by='ticker')

# Preprocess data
if isinstance(data.columns, pd.MultiIndex):
    data.columns = data.columns.get_level_values(1)

data = data[['Open', 'High', 'Low', 'Close', 'Volume']]
data.reset_index(inplace=True)
data.set_index('Date', inplace=True)

# Create data feed
data_feed = bt.feeds.PandasData(dataname=data)

# Define Buy and Hold Strategy
class BuyAndHoldStrategy(bt.Strategy):
    def __init__(self):
        self.last_month = None
        self.first_time = True

    def next(self):
        current_date = self.datas[0].datetime.date(0)
        current_month = current_date.month

        if self.first_time:
            self.first_time = False
            cash = self.broker.get_cash()
            price = self.datas[0].close[0]
            size = int(cash // price)
            if size > 0:
                self.buy(size=size)
        elif self.last_month != current_month:
            self.last_month = current_month
            self.broker.add_cash(1000)
            cash = self.broker.get_cash()
            price = self.datas[0].close[0]
            size = int(cash // price)
            if size > 0:
                self.buy(size=size)

# Define Active Trading Strategy
class ActiveTradingStrategy(bt.Strategy):
    def __init__(self):
        self.last_month = None
        self.position_signal = None
        self.first_time = True
        self.sma = bt.indicators.SimpleMovingAverage(self.data.close, period=10)

    def next(self):
        current_date = self.datas[0].datetime.date(0)
        current_month = current_date.month

        if self.first_time:
            self.first_time = False
            if self.data.close[0] > self.sma[0]:
                self.position_signal = 'buy'
                cash = self.broker.get_cash()
                price = self.datas[0].close[0]
                size = int(cash // price)
                if size > 0:
                    self.buy(size=size)
            else:
                self.position_signal = 'sell'
        elif self.last_month != current_month:
            self.last_month = current_month
            self.broker.add_cash(1000)
            if self.data.close[0] > self.sma[0]:
                current_signal = 'buy'
            else:
                current_signal = 'sell'

            if self.position_signal != current_signal:
                if current_signal == 'sell' and self.position.size > 0:
                    self.close()
                elif current_signal == 'buy':
                    cash = self.broker.get_cash()
                    price = self.datas[0].close[0]
                    size = int(cash // price)
                    if size > 0:
                        self.buy(size=size)
                self.position_signal = current_signal

            if current_signal == 'buy':
                price = self.datas[0].close[0]
                size = int(1000 // price)
                if size > 0:
                    self.buy(size=size)

# Analyzer to track portfolio value
class ValueTracker(bt.Analyzer):
    def __init__(self):
        self.values = []

    def next(self):
        self.values.append((self.datas[0].datetime.date(0), self.strategy.broker.getvalue()))

# Run Buy and Hold Strategy
cerebro_bh = bt.Cerebro()
cerebro_bh.adddata(data_feed)
cerebro_bh.addstrategy(BuyAndHoldStrategy)
cerebro_bh.broker.setcash(1000)
cerebro_bh.addanalyzer(ValueTracker, _name='value_tracker')
results_bh = cerebro_bh.run()
value_tracker_bh = results_bh[0].analyzers.value_tracker.values

# Run Active Trading Strategy
cerebro_at = bt.Cerebro()
cerebro_at.adddata(data_feed)
cerebro_at.addstrategy(ActiveTradingStrategy)
cerebro_at.broker.setcash(1000)
cerebro_at.addanalyzer(ValueTracker, _name='value_tracker')
results_at = cerebro_at.run()
value_tracker_at = results_at[0].analyzers.value_tracker.values

# Convert results to DataFrame for plotting
df_bh = pd.DataFrame(value_tracker_bh, columns=['Date', 'Portfolio Value'])
df_at = pd.DataFrame(value_tracker_at, columns=['Date', 'Portfolio Value'])

# Merge both dataframes for comparison
df_combined = pd.merge(df_bh, df_at, on='Date', suffixes=('_BuyHold', '_ActiveTrading'))

# Plot the results
st.subheader("Portfolio Value Over Time")
st.line_chart(df_combined.set_index('Date'))

# Display final results
st.subheader("Final Results")
st.write(f"**Buy and Hold Final Portfolio Value:** ${df_bh['Portfolio Value'].iloc[-1]:.2f}")
st.write(f"**Active Trading Final Portfolio Value:** ${df_at['Portfolio Value'].iloc[-1]:.2f}")

# Calculate Annualized Returns
years = (end_date - start_date).days / 365.25
total_invested = 1000 * 12 * years

annual_return_bh = ((df_bh['Portfolio Value'].iloc[-1] / total_invested) ** (1 / years)) - 1
annual_return_at = ((df_at['Portfolio Value'].iloc[-1] / total_invested) ** (1 / years)) - 1

st.subheader("Annualized Returns")
st.write(f"**Buy and Hold Annualized Return:** {annual_return_bh * 100:.2f}%")
st.write(f"**Active Trading Annualized Return:** {annual_return_at * 100:.2f}%")

