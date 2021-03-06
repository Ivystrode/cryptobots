from datetime import datetime
import asyncio, websocket, json, talib, sqlalchemy, time
import numpy as np 
import pandas as pd
import matplotlib.pyplot as plt

from binance.client import Client 
from binance.enums import *
from binance import BinanceSocketManager

import keys

# ==========SETUP==========
# SOCKET = "wss://stream.binance.us:9443/ws/ethusdt@kline_1m"

TRADE_SYMBOL = "ETHUSDT"
STD_TQ = 0.005 # Default trade quantity

RSI_PERIOD = 14
PRICE_CHECK_INTERVAL = 2
RSI_OB = 70
RSI_OS = 30

in_position = False
position = 0
have_data = False

engine = sqlalchemy.create_engine(f'sqlite:///{TRADE_SYMBOL}stream.db')
client = Client(keys.API_KEY, keys.SECRET_KEY)

def log(msg):
    """
    Writes the actions to a log file
    """
    time = datetime.now().strftime("%Y%m%d%H%M")
    try:
        with open("./log.txt", "a+") as f:
            f.write(str(time) + ": " + str(msg) + "\n")
    except Exception as e:
        print(f"LOGGING ERROR - {e}")

# ==========DATA COLLECTION==========

def createframe(msg):
    """Transform the message from the API to a dataframe with only the data we want"""
    df = pd.DataFrame([msg])
    df = df.loc[:,['s','E','p']] # 1 row, 3 columns
    df.columns = ['symbol','time','price']
    df.price = df.price.astype(float) # want price as float not a string
    df.time = pd.to_datetime(df.time, unit='ms') # make timestamp readable
    return df

async def collect_data():
    """
    This function will acquire the requested data (price etc) from the binance api
    """
    global have_data
    # client = Client(keys.API_KEY, keys.SECRET_KEY)
    have_data = False

    bsm = BinanceSocketManager(client)

    socket = bsm.trade_socket(TRADE_SYMBOL)
    
    await socket.__aenter__() # why do these need to be awaits?
    msg = await socket.recv()
    
    frame = createframe(msg) # create a frame to put into the database...
    frame.to_sql(TRADE_SYMBOL, engine, if_exists='append', index=False) # enter the frame into the database...
    
    stringified_frame = f"{frame['symbol'][0]} price as at {frame['time'][0]}: ${frame['price'][0]}"

    print(stringified_frame)
    have_data = True


# ==========TRADING==========

def order(side, quantity, symbol, order_type=ORDER_TYPE_MARKET):
    """
    This function will place an order once the conditions in trade_main() are met
    """
    print("ORDERING")
    try:
        print("sending order")
        order = client.create_test_order(symbol=symbol,
                                     side=side, 
                                     type=order_type,
                                     quantity=quantity)
        print(order)
        log(str(order))
        return True
    except Exception as e:
        print(e)
        log(f"Error with order: {e}")
        return False
    
async def during_data_collection():
    """
    This function will take place while we AWAIT the data from the binance API
    """
    global have_data
    i = 0
    while i < 30:
        if not have_data:
            print(f"Awaiting data: {str(i)}")
            await asyncio.sleep(0.5)
            i += 1
        else:
            break
        
async def trade_main():
    """
    Runs the data collection as an asynchronous task, and once data is received runs it against the trade logic
    """
    global in_position
    global position
    global have_data
    log("Bot has started")
    
    while True:
        data_collection = asyncio.create_task(collect_data())
        meanwhile = asyncio.create_task(during_data_collection())
        print("\nREQUESTING DATA...")
        await data_collection
        await meanwhile
        
        prices = pd.read_sql('ETHUSDT', engine)
        prices = prices['price'].values.tolist()
        
        if len(prices) > RSI_PERIOD:
            prices = np.array(prices)
            rsi = talib.RSI(prices, RSI_PERIOD)
            
            last_rsi = rsi[-1]
            print(f"Current RSI: {last_rsi}")
            if in_position:
                print(f"Current Position: {str(position)}")
            
            stored_time = datetime.now()#.strftime("%Y%m%d%H%M%S")
            
            store_last_rsi = pd.DataFrame([[stored_time, float(last_rsi)]])
            
            print(store_last_rsi)
            
            store_last_rsi.columns = ['store_time','rsi']
            store_last_rsi.store_time = stored_time
            store_last_rsi.rsi = store_last_rsi.rsi.astype(float)
            
            store_last_rsi.to_sql(f"{TRADE_SYMBOL}_RSI", engine, if_exists='append', index=False)
            
            if last_rsi > RSI_OB:
                print("Sell signal - check if in position...")
                log("Sell signal...")
                if in_position:
                    print("SELL SIGNAL")
                    # put binance sell logic here
                    order_succeeded = order(SIDE_SELL, STD_TQ, TRADE_SYMBOL)
                    if order_succeeded:
                        in_position = False
                        log(f"Order succeeded: SOLD {TRADE_SYMBOL}:{STD_TQ}")
                        print("Order succeeded")
                    else:
                        print("order failed")
                        log("Order failed...")
                else:
                    log("Not in position - none to sell")
                    print("it is overbought but we dont own any so nothing to do")
            
            if last_rsi < RSI_OS:
                print("Buy signal - check if in position...")
                log("Buy signal...")
                if in_position:
                    log("Already in position")
                    print("it is oversold but you already own it so nothing to do")
                else:
                    print("BUY SIGNAL")
                    log("Not in position - making order...")
                    order_succeeded = order(SIDE_BUY, STD_TQ, TRADE_SYMBOL)
                    if order_succeeded:
                        in_position = True
                        position = STD_TQ
                        log(f"Order succeeded: BOUGHT {TRADE_SYMBOL}:{STD_TQ}")
                    else:
                        print("order failed")
                        log("Order failed...")
                    # put binance buy logic here
                    
            if RSI_OS < last_rsi < RSI_OB:
                print("Still in between, doing nothing...")
        print("----")
        
        await asyncio.sleep(PRICE_CHECK_INTERVAL)


asyncio.run(trade_main())