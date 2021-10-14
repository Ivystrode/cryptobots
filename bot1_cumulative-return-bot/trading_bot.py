import pandas as pd
import matplotlib.pyplot as plt
import sqlalchemy, time
from binance.client import Client 
from binance import BinanceSocketManager
import keys

# USING TESTNET FOR NOT TRADING REAL MONEY!!
client = Client(keys.TESTNET_API_KEY, keys.TESTNET_SECRET_KEY)

# ONLY NECESSARY FOR USING THE TESTNET
client.API_URL = 'https://testnet.binance.vision/api'

bsm = BinanceSocketManager(client)

engine = sqlalchemy.create_engine('sqlite:///BTCUSDTstream.db')

df = pd.read_sql('BTCUSDT', engine)

# print(df)

# df.price.plot()
# plt.show()


# Trend following - if crypto rising by x% buy, sell at +/- 0.15%
def strategy(entry, lookback, qty, open_position=False):
    global df
    while True:
        lookbackperiod = df.iloc[-lookback:] # over the last [lookback] number of price datapoints fetched (so last X rows)
        cumulative_return = (lookbackperiod.price.pct_change() + 1).cumprod() - 1
        if not open_position:
            print("waiting to buy...")
            print(f"Entry: {entry} Cumulative return: {cumulative_return[cumulative_return.last_valid_index()]}")
            if cumulative_return[cumulative_return.last_valid_index()] > entry:
                print("BUY BEGIN")
                print(f"Entry: {entry} Cumulative return: {cumulative_return[cumulative_return.last_valid_index()]}")
                order = client.create_test_order(symbol='BTCUSDT',
                                            side='BUY',
                                            type='MARKET',
                                            quantity=qty)
                print("BUYING!!!")
                print(order)
                open_position=True
                break # DON'T OPEN ANY MORE POSITIONS ONCE YOU HAVE BOUGHT
            time.sleep(2)
            
    if open_position:
        print("open position!")
        while True:
            print("entering sell loop")
            df = pd.read_sql('BTCUSDT', engine)
            sincebuy = df.loc[df.time > pd.to_datetime(order['transactTime'],
                                                       unit='ms')]
            if len(sincebuy) > 1:
                sincebuyreturn = (sincebuy.price.pct_chance() + 1).cumprod() - 1
                last_entry = sincebuyreturn[sincebuyreturn.last_valid_index()]
                if last_entry > 0.0015 or last_entry < -0.0015:
                    order = client.create_test_order(symbol='BTCUSDT',
                                            SIDE='SELL',
                                            type='MARKET',
                                            quantity=qty)
                    print("SELLING!")
                    print(order)
                    break # MAKE SURE TO BREAK OR YOU WILL SELL AGAIN
                
strategy(0.001, 60, 0.001)