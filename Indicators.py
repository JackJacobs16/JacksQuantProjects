# import the necessary libraries:
import numpy as np 
import pandas as pd 
import datetime as dt 
import matplotlib.pyplot as plt 

#    All functions are designed for input data as pd.DataFrame with the following columns:
#    1. Close: closing price
#    2. Date: Dates attatched to prices 


# define a function which computes the linearly weighted moving average:
def lwma(data: pd.DataFrame, period:int):
    weights = np.array([period-i for i in range(period)])
    lwmas = data['Close'].rolling(window=period).apply(lambda x: np.dot(weights, x)/np.sum(weights), raw=True).fillna(0)
    return lwmas

# define function which computes bollinger bands for a full dataframe of historical price data: 
def bollinger_bands(data: pd.DataFrame, period: int, n: int):
    df = pd.DataFrame(columns=['Date', 'Close', 'Upper', 'Lower']) # dataframe to encapsulate the bollinger bands against the price
    # compute the reference line:
    lwmas = lwma(data, period)
    # compute the SMA acting as the 'middle band' and the rolling standard deviations:
    sma = data['Close'].rolling(window=period).mean().fillna(0)
    sigma = data['Close'].rolling(window=period).std().fillna(0)
    df['Date']=data['Date']
    df['Close']=data['Close']
    df['Upper'] = pd.Series(lwmas+n*sigma)
    df['Lower']=pd.Series(lwmas-n*sigma)
    df['SMA']=sma
    return df     

# Breakout trading strategy for Bollinger Bands:
def bollinger_band_breakout(data: pd.DataFrame, period: int, n: int):
    """
    computes the bollinger bands for the given data. 
    Returns a numpy array containing buy/sell instructions based on the following rules:
    1. If stock price exeeds the upper band, we sell,
    2. If the stock price falls below the lower band, we buy
    """
    # create the bollinger bands:
    df = bollinger_bands(data, period, n)
    
    # compute the buy/sell signals:
    sell_signals = (df['Close']>df['Upper'])&(df['Close'].shift(1)<=df['Upper'].shift(1))
    buy_signals = (df['Close']<df['Lower'])&(df['Close'].shift(1)>=df['Lower'].shift(1))
    
    # add to dataframe:
    df['Buy'] = buy_signals
    df['Sell'] = sell_signals
    
    return df 
    

# Reversal trading strategy:
def bollinger_bands_reversal(data: pd.DataFrame, period: int, n: int, plot=False):
    """ 
    Here we trade the reversals: 
    1. If the stock price exceeds the upper band, then we sell when the stock price falls back below the upper band. 
    2. If the stock price falls below the lower band, then we buy when the stock price exceeds the lower band.
    """
    bbs = bollinger_bands(data, period, n)
    bollinger_buy = (bbs['Close']>=bbs['Lower'])&(bbs['Close'].shift(1)<=bbs['Lower'].shift(1))
    bollinger_sell = (bbs['Close']<=bbs['Upper'])&(bbs['Close'].shift(1)>=bbs['Upper'].shift(1))
    df = bbs 
    df['Buy']=bollinger_buy
    df['Sell']=bollinger_sell
    
    #plot the results:
    if plot: 
        fig = plt.figure(figsize=(20, 10))
        ax = fig.add_subplot()
        ax.plot(df['Date'], df['Close'], color="blue", label="Price")
        ax.plot(df['Date'], df['Lower'], color="red", label="Upper Band", alpha=0.7)
        ax.plot(df['Date'], df['Upper'], color="red", label="Lower Band", alpha=0.7)
        ax.plot(df['Date'], df['SMA'], color="orange", label=f"{period}-day SMA", alpha=0.7)
        ax.scatter(df[df['Buy']==+1]['Date'], df[df['Buy']==+1]['Close'], marker="^", color="green", label="Buy")
        ax.scatter(df[df['Sell']==-1]['Date'], df[df['Sell']==-1]['Close'], marker="v", color="red", label="Sell")
        plt.grid(True, which='both')
        plt.xlabel("Date", fontsize=13)
        plt.ylabel("Price ($)", fontsize=13)
        plt.title(f"{period}-day Bollinger Bands with $\\sigma$={n}", fontsize=19)
        plt.legend()
        plt.show()
    return df

    

# we now look at the MACD

# a general rule of thumb when considering the MACD is that if you have daily price data, you should consider weekly data for computing the MACD. 
# the below function converts our daily historical price data into weekly historical price data: 

def to_weekly(data: pd.DataFrame):
    """ 
    input data is daily price data with colums: {'Date' , 'Close}
    output data is weekly price data
    """
    df = data.iloc[range(0, len(data), 7)] 
    return df 

# compute the MACD and signal line for given data:
def MACD(data: pd.DataFrame, params: list[int]):
    """ 
    For a particular ticker in our ETF dataframe:
    Computes the MACD indicator with parameters (a,b,c) where MACD line = a-b EMA, signal line = c-day EMA of MACD
    If Plot=True, plot the results
    """
    macd=pd.DataFrame()
    macd['Date']=data['Date']
    macd['Close']=data['Close']
    long = macd['Close'].ewm(span=params[1], adjust=False).mean()
    short = macd['Close'].ewm(span=params[0], adjust=False).mean()
    macd['MACD']=short-long
    macd['signal']=macd['MACD'].ewm(span=params[2], adjust=False).mean()
    return macd

# Build a function which computes the MACD histogram, and generates buy/sell signals based off of its results:
def MACD_hist(data:pd.DataFrame, params: list[int]):
    data_macd = MACD(data, params)
    data_macd['Hist'] = data_macd['MACD']-data_macd['signal']
    
    # compute when a zero-line crossover occurs:
    above_zero_cross = (data_macd['MACD']>0)&(data_macd['MACD'].shift(1)<=0)
    below_zero_cross = (data_macd['MACD']<0)&(data_macd['MACD'].shift(1)>=0)
    data_macd['Above Zero Cross']=above_zero_cross.replace([True, False], [1,0])        # bullish momentum is dominant
    data_macd['Below Zero Cross']=below_zero_cross.replace([True, False], [-1, 0])      # bearish momentum is dominant
    

    # find the MACD-signal line crossover points
    data_macd['Upwards Cross'] = (data_macd['MACD'] > data_macd['signal']) & (data_macd['MACD'].shift(1) <= data_macd['signal'].shift(1)) 
    data_macd['Downwards Cross'] = (data_macd['MACD'] < data_macd['signal']) & (data_macd['MACD'].shift(1) >= data_macd['signal'].shift(1)) 
    
    data_macd['Upwards Cross']=data_macd['Upwards Cross'].replace([True, False], [1, 0])
    data_macd['Downwards Cross']=data_macd['Downwards Cross'].replace([True, False], [-1, 0])
    
    # HISTOGRAM ANALYSIS:
    # histogram represents the strength of price movements: 
    # longer bars implies stronger price movement
    # short bars implies weaker price movement
    # Changes in histogram strength often preceed reversals (backward looking in itself)
    
    # here we aim to quantify price momentum using the histogram:
    
    # we compute the running 9-day EMA of the histogram bar height. If the current height is above this EMA, then we consider there to be price strength. 
    data_macd['Momentum Strength']=data_macd['Hist'].ewm(span=params[2], adjust=False).mean()
    # ratio of histogram to momentum strength line, if >1, then there is strong momentum, if <1, there is weak momentum.
    data_macd['Hist/Momentum Strength']=data_macd['Hist']/data_macd['Momentum Strength'] 
    data_macd['Hist/Momentum Strength'] = data_macd['Hist/Momentum Strength'].fillna(1)
    return data_macd

# Build a function which, for given price data, computes the daily MACD, weekly MACD, and plots:
def MACD_daily_weekly(data: pd.DataFrame, params: list[int], n:int, plot=False):
    daily = MACD_hist(data, params)                                                 # daliy macd
    weekly = MACD_hist(to_weekly(data), params)                                     # weekly macd
    sma = SMA(daily, [n], plot=False)                                               # also compute the n-day SMA of the closing price
    df = data.copy()
    df['Daily MACD'] = daily['MACD']
    df['Daily MACD Signal'] = daily['signal']
    df['Daily Hist'] = daily['Hist']
    df['Weekly MACD'] = weekly['MACD']
    df['Weekly Signal'] = weekly['signal']
    df['Daily Upwards Cross'] = daily['Upwards Cross']
    df['Daily Downwards Cross'] = daily['Downwards Cross']
    df['Weekly Upwards Cross'] = weekly['Upwards Cross']
    df['Weekly Downwards Cross'] = weekly['Downwards Cross']
    df['Weekly Above 0'] = weekly['Above Zero Cross']
    df['Weekly Below 0'] = weekly['Below Zero Cross']
    df[f"{n}-day SMA"] = sma[f'{n}-day SMA']
    
    
    if plot: 
        fig = plt.figure(figsize=(20,10))
        ax1 = fig.add_subplot(211)
        ax1.plot(daily['Date'], daily['Close'], color="blue", label="Closing Price")
        ax1.plot(sma['Date'], sma[f'{n}-day SMA'], color="red", alpha=0.6, label=f'{n}-day SMA')
        plt.grid(True, which='both')
        plt.xlabel("Date", fontsize=10)
        plt.ylabel("Price ($)", fontsize=10)
        plt.legend()
        ax2 = fig.add_subplot(212)
        ax2.plot(weekly['Date'], weekly['MACD'], color="blue", label="MACD")
        ax2.plot(weekly['Date'], weekly['signal'], color="orange", label="9-day Signal Line")
        positive = daily['Hist'].copy()
        negative = daily['Hist'].copy()
        positive[positive<0]=0
        negative[negative>0]=0
        ax2.bar(daily['Date'], positive, color="green", alpha=0.6)
        ax2.bar(daily['Date'], negative, color="red", alpha=0.6)
        plt.grid(True, which='both')
        plt.xlabel("Date", fontsize=10)
        plt.legend()
        plt.show()
    
    return df 


# Plot the momentum strength against the MACD histogram
def MACD_Plot_Momentum_Strength(data: pd.DataFrame, params: list[int]):
    """
    Plots the histogram, macd line and signal line, as well as the momentum strength.
    Also plot the crossover points of the MACD and signal lines on both subplots
    """
    df = MACD_hist(data, params) 
    
    # identify where the histogram is +ve and where it is -ve, and isolate the two halves: 
    positive = df['Hist'].copy()
    negative = df['Hist'].copy()
    positive[positive<0]=0
    negative[negative>0]=0
    
    
    fig = plt.figure(figsize=(20,10))
    ax1 = fig.add_subplot(211)
    ax1.scatter(df[df['Upwards Cross']==+1]['Date'], df[df['Upwards Cross']==+1]['MACD'], color="green", marker="^", label="Upwards Cross")
    ax1.scatter(df[df['Downwards Cross']==-1]['Date'], df[df['Downwards Cross']==-1]['MACD'], color="red", marker="v", label="Downwards Cross")
    ax1.plot(df['Date'], df['MACD'], color="blue", label=f"MACD ({params[0], params[1]})")
    ax1.plot(df['Date'], df['signal'], color="orange", label=f"{params[2]}-day Signal Line")
    ax1.bar(df['Date'], positive, color="green", alpha=0.5)
    ax1.bar(df['Date'], negative, color="red", alpha=0.5)
    plt.grid(True, which='both')
    ax1.set_xlabel("Date", fontsize=13)
    plt.legend()
    
    ax2 = fig.add_subplot(212)
    # plot the strength of price momentum:
    ax2.scatter(df[df['Upwards Cross']==+1]['Date'], df[df['Upwards Cross']==+1]['Momentum Strength']/100, color="green", marker="^", label="Upwards Cross")
    ax2.scatter(df[df['Downwards Cross']==-1]['Date'], df[df['Downwards Cross']==-1]['Momentum Strength']/100, color="red", marker="v", label="Downwards Cross")
    ax2.plot(df['Date'], df['Momentum Strength']/100, color="blue", label="Strength of Price Momentum", linewidth=0.7)
    ax2.bar(df['Date'], positive, color="green", alpha=0.5)
    ax2.bar(df['Date'], negative, color="red", alpha=0.5)
    plt.grid(True, which='both')
    ax2.set_xlabel("Date", fontsize=13)
    plt.legend()
    
    plt.show()
    return None 

# multi-timeframe strategy with the MACD:
def MACD_multi_timeframe(data: pd.DataFrame, short_params: list[int], mid_params: list[int], long_params: list[int], plot_buysell=False):
    """
    Gives a multi-timeframe analysis of the MACD: 
    - computes the MACD line, signal line, and, if specified, plots the buy/sell crossover signals for a the medium timeframe 
    - computes and plots the short and longer term timeframe MACD and signal line pairs also.
    """
    short =  MACD_hist(data, short_params)
    mid = MACD_hist(data, mid_params)
    long = MACD_hist(data, long_params)
    
    # augment the three dataframes: 
    df = mid 
    df['Short MACD'] = short['MACD']
    df['Short Signal'] = short['signal']
    df['Long Above Zero Cross'] = long['Above Zero Cross']
    df['Long Below Zero Cross'] = long['Below Zero Cross']
    df['Short Above Zero Cross'] = short['Above Zero Cross']
    df['Short Below Zero Cross'] = short['Below Zero Cross']
    df['Short Momentum Strength'] = short['Momentum Strength']
    df['Long MACD'] = long['MACD']
    df['Long Signal'] = long['signal']
    df['Short Upwards Cross']=short['Upwards Cross']
    df['Short Downwards Cross']=short['Downwards Cross']
    df['Long Upwards Cross']=long['Upwards Cross']
    df['Long Downwards Cross']=long['Downwards Cross']

    # implement the trading strat: 
    # 1. If all 3 timeframes have an upwards crossover, we buy. 
    # 2. If all 3 timeframes have a downwards crossover, sell. 
    # or: 
    # 1. If 2/3 timeframes have an upwards crossover and the long-term above zero crossover has occured, buy
    # 2. If 2/3 timeframes have a below crossover and the long-term below zero crossover has occured, sell.
    
    # or [INCOMPLETE]
    # 1. If the buy counter falls from 3 to 2, and there is no longer strong bullish momentum, sell. 
    # 2. If the sel counter rises to -2 from -3, and there is no longer strong bearish momentum, buy. 
    
    df['Buy Counter'] = df['Upwards Cross']+df['Long Upwards Cross']+df['Short Upwards Cross']
    df['Sell Counter'] = df['Downwards Cross']+df['Short Downwards Cross']+df['Long Downwards Cross']
    
    df['Buy']=( df['Buy Counter']==+3 ) | ( (df['Buy Counter']==+2) & (df['Long Above Zero Cross']==+1) ) # | ( (df['Hist']<0)&(df['Hist/Momentum Strength']<1)&(df['Sell Counter']==-2)&(df['Sell Counter'].shift(1)==-3) )
    df['Sell']=( df['Sell Counter']==-3 )|( (df['Sell Counter']==-2) & (df['Long Below Zero Cross']==-1) ) # | ( (df['Hist']>0)&(df['Hist/Momentum Strength']<1)&(df['Buy Counter']==+2)&(df['Buy Counter'].shift(1)==+3) )

    
    # plot the MACD and signal lines for all 3 timeframes: 
    if plot_buysell:
        fig = plt.figure(figsize=(20, 20))
        ax1 = fig.add_subplot(311)
        ax1.plot(short['Date'], short['MACD'], color="lightblue", label=f"MACD {short_params}")
        ax1.plot(short['Date'], short['signal'], color="orange", label=f"MACD {short_params} Signal")
        ax1.plot(mid['Date'], mid['MACD'], color="red", label=f"MACD {mid_params}", alpha=0.6)
        ax1.plot(mid['Date'], mid['signal'], color="green", label=f"MACD {mid_params} Signal")
        ax1.plot(long['Date'], long['MACD'], color="black", label=f"MACD {long_params}", alpha=0.6)
        ax1.plot(long['Date'], long['signal'], color="purple", label=f"MACD {long_params} Signal")
        plt.grid(True, which='both')
        plt.xlabel("Date", fontsize=10)
        plt.legend()

        ax2 = fig.add_subplot(312)
        ax2.plot(df['Date'], df['Close'], color="blue", label="Closing Price", alpha=0.7)
        ax2.scatter(df[df['Buy']==True]['Date'], df[df['Buy']==True]['Close'], marker="^", label="Buy", color="green")
        ax2.scatter(df[df['Sell']==True]['Date'], df[df['Sell']==True]['Close'], marker="^", label="Sell", color="red")
        plt.grid(True, which='both')
        plt.xlabel("Date", fontsize=10)
        plt.ylabel("Price ($)", fontsize=10)
        plt.legend()
        # plot the medium term histogram and momentum strength line against both the short-term and mid-term macd and signal line, along with buy/sell signals 
        ax3 = fig.add_subplot(313)
        ax3.plot(short['Date'], short['MACD'], color="blue", label="Short MACD", alpha=0.5)
        ax3.plot(short['Date'], short['signal'], color="orange", label="Short MACD Signal", alpha=0.5)
        ax3.plot(mid['Date'], mid['MACD'], color="purple", label="Medium MACD", alpha=0.5)
        ax3.plot(mid['Date'], mid['signal'], color="black", label="Medium MACD Signal", alpha=0.5)
        ax3.scatter(df[df['Buy']==True]['Date'], df[df['Buy']==True]['MACD'], label="Buy", color="green", marker="^")
        ax3.scatter(df[df['Sell']==True]['Date'], df[df['Sell']==True]['MACD'], label="Sell", color="red", marker="v")
        positive = df['Hist'].copy()
        negative = df['Hist'].copy()
        positive[positive<0]=0
        negative[negative>0]=0
        ax3.bar(mid['Date'], positive, color="green", alpha=0.5)
        ax3.bar(mid['Date'], negative, color="red", alpha=0.5)
        ax3.plot(mid['Date'], mid['Momentum Strength'], color="yellow", alpha=1, linewidth=0.75, label="Medium Momentum Strength")
        plt.grid(True, which='both')
        plt.xlabel("Date", fontsize=10)
        plt.legend()
        plt.show()
        
    return df 


# compute the n-day SMA of Closing Price:
def SMA(data: pd.DataFrame, n: list[int], plot=False):
    df = data
    if type(n)==list:
        for m in n:
            df[f"{m}-day SMA"] = data['Close'].rolling(window=m).mean()
    df = df.iloc[max(n):]
    if plot:
        fig = plt.figure(figsize=(20,10))
        ax = fig.add_subplot(111)
        ax.plot(df['Date'], df['Close'], color="blue", label="Closing price")
        for m in n:
            ax.plot(df['Date'], df[f"{m}-day SMA"], label=f"{m}-day SMA")
        plt.grid(True, which='both')
        plt.xlabel("Date", fontsize=10)
        plt.ylabel("Price", fontsize=10)
        plt.legend()
        plt.show()
    return df


# and finally the RSI:
# We use https://www.youtube.com/watch?v=I5unWZBldus&t=309s to compute the RSI:
def RSI(data: pd.DataFrame, rsi_period: int, upper: float, lower: float, plot=False):
    """
    upper and lower are the overbought and oversold threshold levels respectively. 
    If plot=True, plot the Price, RSI, threshold lines and buy/sell signals
    """
    # Create DataFrame:
    rsi = pd.DataFrame()
    rsi['Date']=data['Date']
    rsi['Close']=data['Close']
    # compute exponential weighted aveage gain and loss during the period
    rsi['gain'] = (rsi['Close']-rsi['Close'].shift(1).fillna(0)).apply(lambda x: x if x > 0 else 0)
    rsi['loss'] = (rsi['Close']-rsi['Close'].shift(1).fillna(0)).apply(lambda x: -x if x < 0 else 0)
    rsi['ema_gain'] = rsi['gain'].ewm(span=rsi_period, min_periods=rsi_period).mean()
    rsi['ema_loss'] = rsi['loss'].ewm(span=rsi_period, min_periods=rsi_period).mean()
    # the RSI = exponential avg gain/exponential avg loss
    # the RSI is calculated based on the Relative Strength using the following formula
    rsi['rs'] = rsi['ema_gain'] / rsi['ema_loss']
    rsi['rsi_14'] = 100 - (100 / (rsi['rs'] + 1))
    
    # Original strategy:
    # generate signals to say when RSI is >70 and RSI is <30:
    #rsi['Overbought']= (rsi['rsi_14']>upper)&(rsi['rsi_14'].shift(1)<=upper)
    #rsi['Oversold']= (rsi['rsi_14']<lower)&(rsi['rsi_14'].shift(1)>=lower)
    
    
    # Reversal strategy: 
    # If rsi>overbought,  sell as soon as rsi<=overbought, 
    # If rsi<oversold, buy as soon as rsi>=oversold: 
    rsi['Overbought']=(rsi['rsi_14']<=upper)&(rsi['rsi_14'].shift(1)>upper)
    rsi['Oversold']=(rsi['rsi_14']>lower)&(rsi['rsi_14'].shift(1)<lower)

    # Overbought=Sell, Oversold=Buy
    # replace with +1 and -1 where necessary:
    rsi['Overbought'] = rsi['Overbought'].replace([True, False], [-1, 0])
    rsi['Oversold'] = rsi['Oversold'].replace([True, False], [+1, 0])
    
    if plot:
        fig = plt.figure(figsize=(20,10))
        ax1 = fig.add_subplot(211)
        ax1.plot(rsi['Date'], rsi['Close'], color="blue", label="Closing Price")
        ax1.scatter(rsi[rsi['Oversold']==+1]['Date'], rsi[rsi['Oversold']==+1]['Close'], color="green", label="Buy", marker="^")
        ax1.scatter(rsi[rsi['Overbought']==-1]['Date'], rsi[rsi['Overbought']==-1]['Close'], color="red", label="Sell", marker="v")
        plt.grid(True, which='both')
        plt.xlabel("Date", fontsize=10)
        plt.ylabel("Price ($)", fontsize=10)
        plt.legend()
        ax2 = fig.add_subplot(212)
        ax2.plot(rsi['Date'], rsi['rsi_14'], color="blue", label=f"RSI - period: {rsi_period}")
        plt.hlines(y=upper, xmin=rsi.iloc[0]['Date'], xmax=rsi.iloc[-1]['Date'], color="red", label="Overbought")
        plt.hlines(y=lower, xmin=rsi.iloc[0]['Date'], xmax=rsi.iloc[-1]['Date'], color="red", label="Overbsold" )
        ax2.scatter(rsi[rsi['Oversold']==+1]['Date'], rsi[rsi['Oversold']==+1]['rsi_14'], color="green", label="Buy", marker="^")
        ax2.scatter(rsi[rsi['Overbought']==-1]['Date'], rsi[rsi['Overbought']==-1]['rsi_14'], color="red", label="Sell", marker="v")
        plt.grid(True, which='both')
        plt.xlabel("Date", fontsize=10)
        plt.legend()
        plt.show()
    return rsi



# a strategy combining the MACD and RSI 
def RSI_and_MACD(data: pd.DataFrame, rsi_period: int, upper: float, lower: float, macd_params: list[int], moving_avg: int, plot=False):
    """
    Here we do the following:
    - compute {moving_avg}-day SMA on daily price data
    - compute the MACD (medium term parameters) on daily price data
    - compute the MACD (medium term parameters) on weekly price data
    - compute the RSI on daily price data
    
    Upwards trend: price>SMA or weekly MACD line crosses above 0
    Downwards trend: price<SMA or weekly MACD line falls below 0
    
    Then we implement the standard RSI strategy of buying when the stock breaks the oversold threshold after previously falling below it, and selling if the stock falls below the overbought threshold
    after previously breaching it. 
    """
    df = MACD_daily_weekly(data, macd_params, moving_avg, plot=False)
    rsi = RSI(data, rsi_period, upper, lower, plot=False)
    
    df['RSI'] = rsi['rsi_14']
    df['RSI Overbought'] = rsi['Overbought']
    df['RSI Oversold'] = rsi['Oversold']
        
    # determine if we are trending upwards or not: 
    df['Up']= (df['Close']>df[f"{moving_avg}-day SMA"]) | (df['Weekly Above 0']==+1)
    df['Down']= (df['Close']<df[f"{moving_avg}-day SMA"]) | (df['Weekly Below 0']==-1)
    
    # implement the trading logic to determine the buy/sell signals: 
    df['Buy'] = (df['Up']==True)&(df['RSI Oversold']==+1)
    df['Sell'] = (df['Down']==True)&(df['RSI Overbought']==-1)

    # plot the results:
    if plot: 
        fig = plt.figure(figsize=(20,10))
        ax1 = fig.add_subplot(211)
        ax1.plot(df['Date'], df['Close'], color="blue", label="Closing Price", alpha=0.7)
        ax1.plot(df['Date'], df[f"{moving_avg}-day SMA"], color="red", label="50-day SMA", alpha=0.7)
        ax1.scatter(df[df['Buy']==True]['Date'], df[df['Buy']==True]['Close'], label="Buy", marker="^", color="green")
        ax1.scatter(df[df['Sell']==True]['Date'], df[df['Sell']==True]['Close'], label="Sell", marker="v", color="red")
        plt.grid(True, which='both')
        plt.xlabel("Date", fontsize=10)
        plt.ylabel("Price ($)", fontsize=10)
        plt.legend()
        ax2 = fig.add_subplot(212)
        ax2.plot(df['Date'], df['RSI'], color="blue", label=f"RSI -Period: {rsi_period}")
        plt.hlines(y=upper, xmin=df.iloc[0]['Date'], xmax=df.iloc[-1]['Date'], color="red", label="Overbought")
        plt.hlines(y=lower, xmin=df.iloc[0]['Date'], xmax=df.iloc[-1]['Date'], color="red", label="Oversold")
        plt.xlabel("Date", fontsize=10)
        plt.legend()
        plt.grid(True, which='both')
        plt.show()

    return df 







# now let's work on some MACD divergence indicators: [INCOMPLETE]
def MACD_Divergence(data: pd.DataFrame, params: list[int], period: int, version: str, plot=False):
    """
    1. Regular Bullish Divergence: 
        - Price process makes lower lows whilst the MACD makes higher lows. 
        - we compute the difference between 
        Suggests a potential bearish to bullish trend reversal 
    """
    df = MACD_hist(data, params)
    # compute 9-day running minimum and maximum of Closing Price:
    df['Price Running Min'] = df['Close'].rolling(window=period).min()
    df['Price Running Max'] = df['Close'].rolling(window=period).max()
    # compute the 9-day running minimum and maximum of MACD indicator: 
    df['MACD Running Min'] = df['MACD'].rolling(window=period).min()
    df['MACD Running Max'] = df['MACD'].rolling(window=period).max()

    # we want to track the dates under which we have each different type of divergence: 
    divergence = []
    for i in range(0, len(df)-period, period):
        price_min_diff = df.iloc[i]['Price Running Min']-df.iloc[i+period]['Price Running Min']
        price_max_diff = df.iloc[i]['Price Running Max']-df.iloc[i+period]['Price Running Max']
        macd_min_diff = df.iloc[i]['MACD Running Min']-df.iloc[i+period]['MACD Running Min']
        macd_max_diff =  df.iloc[i]['MACD Running Max']-df.iloc[i+period]['MACD Running Max']
        # regular bullish divergence if price_min_diff>0 whilst MACD_min_diff<0:
        # regular bearish divergence if price_max_diff<0 whilst MACD_max_diff=0:
        # hidden bullish divergence if price_min_diff=0 whilst MACD_min_diffj>0:
        # hidden bearish divergence if price_max_diff==0 whilst MACD_max_diff<0:
        if version=="regular bullish" and (price_min_diff>0)and(macd_min_diff<0):
            divergence.append([df.iloc[i], df.iloc[i+period]])
        elif version=="regular bearish" and (price_max_diff<0)and(macd_max_diff==0):
            divergence.append([df.iloc[i], df.iloc[i+period]])
        elif version=="hidden bullish" and (price_min_diff==0)and(macd_min_diff>0):
            divergence.append([df.iloc[i], df.iloc[i+period]])
        elif version=="hidden bearish" and (price_max_diff==0)and(macd_max_diff<0):
            divergence.append([df.iloc[i], df.iloc[i+period]])
    
    col_close = None 
    col_macd = None
    if version=="regular bullish" or version=="hidden bullish":
        col_close = "red"
        col_macd = "green"
    elif version=="regular bearish" or version=="hidden bearish":
        col_close = "green"
        col_macd = "red"
    
    if plot:
        fig = plt.figure(figsize=(20,10))
        
        ax1 = fig.add_subplot(211)
        for points in divergence:
            ax1.plot([points[0]['Date'], points[1]['Date']], [points[0]['Close'], points[1]['Close']], color=col_close, linewidth=1.5)
        ax1.plot(df['Date'], df['Close'], color="blue", label="Closing Price", alpha=0.5)
        plt.grid(True, which='both')
        plt.xlabel("Date", fontsize=10)
        plt.ylabel("Price ($)", fontsize=10)
        plt.legend()
        
        ax2 = fig.add_subplot(212)
        for points in divergence:
            ax2.plot([points[0]['Date'], points[1]['Date']], [points[0]['MACD'], points[1]['MACD']], color=col_macd, linewidth=1.5)
        ax2.plot(df['Date'], df['MACD'], color="blue", label="MACD", alpha=0.5)
        plt.grid(True, which='both')
        plt.xlabel("Date", fontsize=10)
        plt.legend()

        plt.show()
        
        for points in divergence:
            print([points[0]['Date'], points[0]['Close']], [points[1]['Date'], points[1]['Close']])
        return None 

