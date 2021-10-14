import pandas as pd
import sqlalchemy
from binance.client import Client 
from binance import BinanceSocketManager
import keys
import asyncio


def createframe(msg):
    """transform the message from the API to a dataframe with only the data we want"""
    df = pd.DataFrame([msg])
    df = df.loc[:,['s','E','p']] # 1 row, 3 columns
    df.columns = ['symbol','time','price']
    df.price = df.price.astype(float) # want price as float not a string
    df.time = pd.to_datetime(df.time, unit='ms') # make timestamp readable
    return df

async def main():
    client = Client(keys.API_KEY, keys.SECRET_KEY)

    bsm = BinanceSocketManager(client)

    socket = bsm.trade_socket('BTCUSDT')

    engine = sqlalchemy.create_engine('sqlite:///BTCUSDTstream.db')
    while True:
        await socket.__aenter__() # why do these need to be awaits?
        msg = await socket.recv()
        frame = createframe(msg) # create a frame to put into the database...
        frame.to_sql('BTCUSDT', engine, if_exists='append', index=False) # enter the frame into the database...
        print(frame)

asyncio.run(main())