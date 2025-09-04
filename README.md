Here I make my first venture into algorithmic trading and backtesting. 

In this project, I study the MACD, RSI, and Bollinger bands, looking at how they are computed, how they are interpreted, and how we can use them in algorithmic trading strategies. 

I then research how one builds the machinery needed to backtest various trading strategies in python. The main reference for this comes from the work by ATJ Traders, who posted the following video on YouTube: https://www.youtube.com/watch?v=I5unWZBldus&t=309s. 
I build off of the python code in this video, and adapt the python classes included to the needs of this project. I also add an additional python class which computes various metrics which we can use to evaluate the performance of a backtest. 
We compute the daily returns of the trading strategy, the Sharpe ratio, the Beta, and the historical volatility of the returns. 

The file `Indicators.py` includes all of the functions which compute the aforementioned technical indicators, and provides the buy/sell signals used in the trading strategies. 
The file `AT.py` contains the backtesting hardware which runs the backtest for us and evaluates it's performance. 

The reader should note that none of the trading strategies I have used in this project are actually any good. They either lose money or gain so little you would almost surely lose it all in brokers fee's over the course of the time horizon. The 
purpose of this project was not to come up with a good trading strategy, but rather to provide the tools one can use to implement a trading strategy in the future. There are many things that I would like to improve about the code I have provided, and 
the parameters I have set. This will all be done at a later date. 

In the pdf file `Introduction to Algorithmic Trading and Backtesting`, I provide a more in-depth explanation to my work, and the references used to research and write this project. 

