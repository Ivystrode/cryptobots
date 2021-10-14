import websocket, json, pprint, talib, numpy
from binance.client import Client 
from binance.enums import *

from datetime import datetime

import keys

# SOCKET = "wss://stream.binance.us:9443/ws/ethusdt@kline_1m"
SOCKET = "wss://testnet.binance.vision/api"
# SOCKET = "wss://testnet.binance.vision/ws/ethusdt@kline_1m"

RSI_PERIOD = 2
RSI_OVERBOUGHT = 55
RSI_OVERSOLD = 50
TRADE_SYMBOL = "ETHUSDT"
TRADE_QUANTITY = 0.005

# closes = [] # a list of the candle closing prices

# JUST TO TEST THE THING AND NOT HAVE TO WAIT FOR IT TO COLLECT LOADS OF CANDLESTICK DATA:
closes = []

in_position = False # if we have bought in

client = Client(keys.TESTNET_API_KEY, keys.TESTNET_SECRET_KEY)
print(client)

# logfile = "log.txt"
# with open(logfile, "a") as f:
#     f.write("BEGIN LOG")
                
def log(msg):
    time = datetime.now().strftime("%Y%m%d%H%M")
    try:
        with open("./log.txt", "a+") as f:
            f.write(str(time) + ": " + str(msg) + "\n")
    except Exception as e:
        print(f"LOGGING ERROR - {e}")


def order(side, quantity, symbol, order_type=ORDER_TYPE_MARKET):
    print("ORDERING")
    try:
        print("sending order")
        order = client.create_order(symbol=symbol,
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

def on_open(ws):

    print("opened connection")
    msg = "opened connection"
    log(msg)

def on_close(ws):
    print("closed connection")
    
def on_message(ws, message):
    global closes
    global in_position
    # print("Received data...")
    json_message = json.loads(message)
    # pprint.pprint(json_message)
    
    candle = json_message['k']
    is_candle_closed = candle['x']
    close = candle['c'] # closing price of this candle
    
    if is_candle_closed:
        closes.append(float(close)) # needs to be a float not a string
        print(f"Candle closed at: {close}")
        print("Closes:")
        print(closes) # we build up a list of closes, convert to numpy array, and then run some TA/logic on it to make trading decisions
        
        if len(closes) > RSI_PERIOD:
            np_closes = numpy.array(closes)
            rsi = talib.RSI(np_closes, RSI_PERIOD)
            print("RSIs so far:")
            print(rsi)
            
            last_rsi = rsi[-1]
            print(f"Current RSI: {last_rsi}")
            
            if last_rsi > RSI_OVERBOUGHT:
                print("Sell signal - check if in position...")
                log("Sell signal...")
                if in_position:
                    print("SELL SIGNAL")
                    # put binance sell logic here
                    order_succeeded = order(SIDE_SELL, TRADE_QUANTITY, TRADE_SYMBOL)
                    if order_succeeded:
                        in_position = False
                        log(f"Order succeeded: SOLD {TRADE_SYMBOL}:{TRADE_QUANTITY}")
                        print("Order succeeded")
                    else:
                        print("order failed")
                        log("Order failed...")
                else:
                    log("Not in position - none to sell")
                    print("it is overbought but we dont own any so nothing to do")
            
            if last_rsi < RSI_OVERSOLD:
                print("Buy signal - check if in position...")
                log("Buy signal...")
                if in_position:
                    log("Already in position")
                    print("it is oversold but you already own it so nothing to do")
                else:
                    print("BUY SIGNAL")
                    log("Not in position - making order...")
                    order_succeeded = order(SIDE_BUY, TRADE_QUANTITY, TRADE_SYMBOL)
                    if order_succeeded:
                        in_position = True
                        log(f"Order succeeded: BOUGHT {TRADE_SYMBOL}:{TRADE_QUANTITY}")
                    else:
                        print("order failed")
                        log("Order failed...")
                    # put binance buy logic here
                    
            if RSI_OVERSOLD < last_rsi < RSI_OVERBOUGHT:
                print("Still in between, doing nothing...")
        print("----")


ws = websocket.WebSocketApp(SOCKET, on_open=on_open, on_close=on_close, on_message=on_message)
ws.run_forever()