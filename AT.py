# import the necessary libraries
import numpy as np 
import matplotlib.pyplot as plt 
import datetime as dt
import pandas as pd 
import Indicators as Ind 


"""
The class `Position` is taken from the work by ATJ Traders - Algo Trading (https://www.youtube.com/watch?v=I5unWZBldus&t=309s). I have adapted it slightly for the 
needs of this project. 

The classes which act as the algorithmic trading hardware are also inspired by the aforementioned source, but I have changed certain aspects. For example, the reference code did not permit 
multiple trades being open at the same time. The code below allows us to have multiple open positions simultaneously, which I hope will generate better performance. 
However, I have also added machinery which stops all trading if we ever reach a point where we have insufficient funds to close a trade. ALl is explained in the notes below. 
"""

# create a class which defines our positions in the trading strategy:
class Position: 
    def __init__(self, open_date, open_price, type, vol, stop_loss, take_profit):
        self.open_date = open_date                                  # date of opening the position
        self.open_price = open_price                                # price at which we open the position
        self.type = type                                            # buy or sell?
        self.volume = vol                                           # no. of shares bought/sold 
        self.stop_loss = stop_loss                                  # stop-loss threshold 
        self.take_profit = take_profit                              # take-profit thershold
        self.status = "Open"                                        # open or closed? 
        self.id = self.generate_id()                                # position id so that we may identify each position within an order book
        # Placeholders to be filled onced the position is closed 
        self.close_date = None                                      # date of closing the position
        self.close_price = None                                     # closing price
        self.pnl = None                                             # profit/loss
        
    # to print the position details into a pd.DataFrame:
    def print_order(self):
        order = {'Id': self.id, 'Open Date': self.open_date, 'Open Price': self.open_price, 'Type': self.type, 
                 'Volume': self.volume, 'Stop-Loss': self.stop_loss, 'Take-Profit': self.take_profit, 
                 'Status': self.status, 'Close Date': self.close_date, 'Close Price': self.close_price, 'PnL': self.pnl}
        return order 
    
    # close a position on a given date and at a given price:
    def position_close(self, close_date, close_price):
        self.close_date=close_date 
        self.close_price=close_price 
        diff = self.close_price-self.open_price
        if self.type=='Buy':
            self.pnl = diff*self.volume
        elif self.type=='Sell':
            self.pnl = -diff*self.volume
        self.status='Closed' 
    
    # function which generates an id for each position.:
    def generate_id(self):
        """
        Id should be of the form: date + volume + type
        e.g.: '200101011000B is a 'Buy' trade of 1000 shares on the 1st January 2001.
        """
        open_date = dt.datetime.strftime(self.open_date, format="%Y-%m-%d")                 # should be of length 10 in form: 'YYYY-MM-DD'. 
        date_id= open_date[0:4]+open_date[5:7]+open_date[8:10]                              # remove '-' from date
        type = 'B' if self.type=='Buy' else 'S'
        id = date_id + str(self.volume) + type
        return id
    
    
# Define our first trading strategy to be a breakout strategy using Bollinger bands. 
class BollingerBreakout: 
    def __init__(self, starting_balance: float, data: pd.DataFrame, bollinger_period: int, bollinger_width: int, risk_free: pd.DataFrame):
        """ 
        starting_balance: floating point indicating the amount of money we have initially, 
        data: pd.DataFrame with columns ['Date', 'Close'] containing the historical price data of the stock in question. 
        (bollinger_period, bollinger_width) settings for the bollinger bands. See indicators.py for details. 
        """
        self.starting_balance = starting_balance                                                                                                        # starting balance
        self.current_balance = starting_balance                                                                                                         # tracks our current balance whilst trading
        self.balance_history = [[data.iloc[0]['Date'], starting_balance]]                                                                               # records how our balance changes over the session
        self.bollinger_period = bollinger_period
        self.bollinger_width = bollinger_width
        self.data = Ind.bollinger_band_breakout(data, self.bollinger_period, self.bollinger_width).iloc[bollinger_period:]                              # computes the bollinger bands and indicates the buy/sell signals                                                                                                                        
        self.positions = []                                                                                                                             # stores all positions opened and closed throughout trading
        self.book = None                                                                                                                                # our orderbook formally created once trading has completed
        self.trading_allowed=True                                                                                                                       # if False, no more trades may take place.
        self.equity=None                                                                                                                                # to contain the equity curve of our strategy throughout the time horizon of our backtest
        self.risk_free = risk_free                                                                                                                      # risk-free asset to be used when evaluating backtest
        self.benchmark = data                                                                                                                            # our benchmark asset will be the underlying stock

    def add_position(self, open_price: float, open_date: dt.datetime, volume: float, type: str, stop_loss: float, take_profit: float):
        if self.trading_allowed:
            pos = Position(open_date, open_price, type, volume, stop_loss, take_profit)                                                                     # create a position
            if pos.type=='Buy':                                 
                if self.current_balance>=(pos.volume*pos.open_price):                                                                                       # if 'buy' and we have sufficient funds
                    self.positions.append(pos)
                    new_balance = self.current_balance-(pos.volume*pos.open_price)
                    self.current_balance = new_balance                                                                                                      # update balance
                    self.balance_history.append([open_date, self.current_balance])                                                                   # add balance history
                    return True
                else:                                                                                                                                       # if we do not have sufficient funds, don't make the trade
                    return False
            if pos.type=="Sell":                                                                                                                            # it costs nothing to make a sell trade
                self.positions.append(pos)
                new_balance = self.current_balance+(pos.volume*pos.open_price)
                self.current_balance = new_balance
                self.balance_history.append([open_date, self.current_balance])
                return True
    
    def trading_logic(self, row):
        """
        for a row of price data taken from self.data, we place an order if there is a buy or sell signal.  
        The order is taken to self.add_position() and a trade is placed if we are able. 
        """
        standard_volume = 100                                                                                                                           # we set a standard volume on all trades
        if row['Buy']==True:                                                                                                                            # if a buy signal
            stop_loss = row['Close']*0.95                                                                                                               # set stop loss
            take_profit = row['Close']*1.05                                                                                                             # set take profit
            self.add_position(row['Close'], row['Date'], standard_volume, 'Buy', stop_loss, take_profit)                                                # add the position
        elif row['Sell']==True:
            stop_loss = row['Close']*1.05
            take_profit = row['Close']*0.95
            self.add_position(row['Close'], row['Date'], standard_volume, 'Sell', stop_loss, take_profit)
            
    def has_positions(self):
        """
        Checks if the strategy has any open positions. Returns True/False 
        """
        for pos in self.positions:
            if pos.status=='Open':
                return True 
        return False 

    def close_position(self, id, close_date, close_price, forced_close=False):
        """
        Closes a position - specified by its ID - at a given price on a given date. 
        Updates our balance post trade, and adds to the log book.  
        Recall that if we do not have the sufficient funds to close a 'sell' trade, then we must close all 'buy' positions in the entire book, and then come back to see if we can close out
        the 'sell' trade. If we can, to show some risk management, we stop all trading for fear of being too close to isolvancy. If we cannot close the trade, we force the trade to close and 
        except that we now owe some money. We have gone bust! 
        
        `forced_close=True` means we close trades even if we have insufficient funds. We allow our current balance to go negative. 
        """
        # find the position by its id: 
        for position in self.positions:
            if (position.id == id)&(position.status=='Open'):                                                                                           # find position by its id and check if it's open
                
                if position.type=='Buy':                                                                                                                # if type=='buy', close instantly.
                    position.position_close(close_date, close_price)                                                                                    # updates status and computes pnl etc...
                    new_balance = self.current_balance+(position.volume*close_price)                                                                    # compute the new balance
                    self.current_balance = new_balance                                                                                                  # update current balance
                    self.balance_history.append([close_date, self.current_balance])                                                              # add to balance change history
                    return True

                elif (position.type=='Sell')&((self.current_balance>=(position.volume*close_price))|(forced_close==True)):    # if type=='Sell', we may only close if we have sufficient funds
                    position.position_close(close_date, close_price)
                    new_balance = self.current_balance-(position.volume*close_price)                                                                    # compute the new balance
                    self.current_balance = new_balance                                                                                                  # update current balance
                    self.balance_history.append([close_date, self.current_balance])                                                              # add to balance change history
                    return True
                
                elif (position.type=='Sell')&(self.current_balance<(position.volume*close_price))&(forced_close==False):                                # if we do not have sufficient funds to close the trade:
                    if self.close_buy_positions(position, close_date, close_price)==True:                                                                                                      
                        print(f"Position [id: {position.id}] closed due to insufficient funds on initial attempt. All positions closed on {close_date.date()} and trading terminated due to risk parameter breaches.")
                    else:
                        print(f"All Trading Terminated on {close_date.date()} due to negative equity resulting from insufficient funds to close intial trade [id: {position.id}].")
                    return self.terminate_trading(close_date, close_price) 
        

    def close_buy_positions(self, original_position, close_date, close_price):
        """
        
        This function closes all trades with the specified type: 'Buy', so that we may increase our current balance.
        
        If, afterwards, we have sufficient funds to close the original 'sell' trade (which triggered the use of this function), then we do so and output==True. 
        If we still cannot close the original 'sell' trade, we output False. 
        """
        # close all 'buy' positions:
        if self.has_positions():
            for position in self.positions:
                if (position.status=='Open')&(position.type=='Buy'):
                    self.close_position(position.id, close_date, close_price)
            # now check if we can close the original sell position:
            if self.current_balance>=(original_position.volume*close_price):
                return True 
        return False
        
    def terminate_trading(self, close_date, close_price):
        """
        Closes out any outstanding positions, and returns self.book.   
        """
        if self.has_positions():
            for position in self.positions:
                self.close_position(position.id, close_date, close_price, forced_close=True)
        self.trading_allowed = False
        self.balance_history = pd.DataFrame(self.balance_history, columns=['Date', 'Equity'])
        self.equity = self.balance_history.drop_duplicates(subset=['Date'], keep='last')
        return self.get_book()
                
    def get_book(self):
        """
        Prints a pandas dataframe containing the orderbook of our trades. 
        """
        orderbook = pd.DataFrame([pos.print_order() for pos in self.positions])        
        self.book = orderbook
        return self.book

    def take_profit_stop_loss(self, row):
        """
        row: contains price data and buy/sell signals for a particular date.
        We iterate through all open positions and check whether or not the stop-loss or take-profit criterion have been met.  
        """
        if self.has_positions():
            for position in self.positions:
                # if 'buy' and price exceeds take-profit, close: 
                if (position.type=='Buy')&(position.take_profit<=row['Close']):
                    self.close_position(position.id, row['Date'], position.take_profit, forced_close=False)
                # if 'buy' and price falls below stop-loss, close:
                elif (position.type=='Buy')&(position.stop_loss>=row['Close']):
                    self.close_position(position.id, row['Date'], position.stop_loss, forced_close=False)
                # if 'sell' and price exceeds stop-loss, close:
                elif (position.type=='Sell')&(position.stop_loss<=row['Close']):
                    self.close_position(position.id, row['Date'], position.stop_loss, forced_close=False)
                # if 'sell' and price falls below take-profit, close:
                elif (position.type=='Sell')&(position.take_profit>=row['Close']):
                    self.close_position(position.id, row['Date'], position.take_profit, forced_close=False)

    def simulate(self):
        """
        Conducts the trading by iterating through each row of data, checking whether or not we need to close positions due to stop-loss or take-profit, then 
        checking if there are any buy signals so that we may open a position.  
        """
        for i, row in self.data.iterrows():
            if self.trading_allowed:
                self.take_profit_stop_loss(row)
                self.trading_logic(row)
        # if we make it to the end of the data with no balance problems, close the book:
        return self.terminate_trading(self.data.iloc[-1]['Date'], self.data.iloc[-1]['Close'])

    def plot(self, currency: str):
        """
        Plots the results of the backtest by plotting the price process of the stock we are trading, the buy/sell signal, and our current balance over the time period.  
        
        We also plot the bollinger bands. 
        """
        # for plotting, we include a currency symbol just for aesthetics: 
        data = self.data[self.data['Date']<=self.book.iloc[-1]['Close Date']]
        fig = plt.figure(figsize=(15, 7))
        # plot the price process throughout the time horizon with buy/sell signals on dates where we made trades
        ax1 = fig.add_subplot(211)
        ax1.plot(data['Date'], data['Close'], color="blue", label="Closing Price", alpha=0.75)
        ax1.plot(data['Date'], data['Upper'], color="purple", label="Upper Band", alpha=0.8)
        ax1.plot(data['Date'], data['Lower'], color="orange", label="Lower Band", alpha=0.8)
        ax1.scatter(self.book[self.book['Type']=='Buy']['Open Date'], self.book[self.book['Type']=='Buy']['Open Price'], marker="^", label="Buy", color="green")
        ax1.scatter(self.book[self.book['Type']=='Sell']['Open Date'], self.book[self.book['Type']=='Sell']['Open Price'], marker="v", label="Sell", color="red")
        plt.grid(True, which='both')
        plt.xlabel("Date", fontsize=10)
        plt.ylabel("Closing Price ", fontsize=10)
        plt.legend()
        plt.title(rf"Bollinger Band Breakout Strategy, $m$:{self.bollinger_period}, $\sigma$={self.bollinger_width}, starting balance: {self.starting_balance}, terminal balance: {round(self.current_balance, 3)}")
        
        # plot the equity curve of our trading strategy during the time horizon. 
        ax2 = fig.add_subplot(212)
        ax2.plot(self.equity['Date'], self.equity['Equity'], color="blue", label="Equity")
        plt.hlines(y=self.starting_balance, xmin=self.equity.iloc[0]['Date']-dt.timedelta(days=5), xmax=self.equity.iloc[-1]['Date']+dt.timedelta(days=5), color="red", label="Starting Balance")
        plt.grid(True, which='both')
        plt.xlabel("Date", fontsize=10)
        plt.ylabel("Equity")
        plt.legend()
        plt.show()
        return None
    
    def backtest(self):
        """
        Carries out the full test then plots the results and evaluates backtest using the `evaluate` class. 
        `risk_free` contains yield data for the risk-free rate. 
        `benchmark` contains price data for the benchmark asset.  
        """
        self.simulate()
        eval = Evaluate(self, self.risk_free, self.benchmark, self.starting_balance)
        self.plot()
        return eval.full_eval()
    
    
    
    
# we now define a second trading strategy which is a reversal strategy again using Bollinger bands. 
# Here we buy once the stock falls rises above the lower band after initially falling below it.
# Here we sell once the stock falls below the upper band after initially rising above it.
# Nothing really needs changing from `BollingerBreakout` except for the computation for `self.data`. See Indicators.py for details.
class BollingerReversal:
    def __init__(self, starting_balance: float, data: pd.DataFrame, bollinger_period: int, bollinger_width: int, risk_free: pd.DataFrame):
        """ 
        starting_balance: floating point indicating the amount of money we have initially, 
        data: pd.DataFrame with columns ['Date', 'Close'] containing the historical price data of the stock in question. 
        (bollinger_period, bollinger_width) settings for the bollinger bands. See indicators.py for details. 
        """
        self.starting_balance = starting_balance                                                                                                        # starting balance
        self.current_balance = starting_balance                                                                                                         # tracks our current balance whilst trading
        self.balance_history = [[data.iloc[0]['Date'], starting_balance]]                                                                               # records how our balance changes over the session
        self.bollinger_period = bollinger_period
        self.bollinger_width = bollinger_width
        self.data = Ind.bollinger_bands_reversal(data, self.bollinger_period, self.bollinger_width, plot=False).iloc[bollinger_period:]                 # computes the bollinger bands and indicates the buy/sell signals                                                                                                                        
        self.positions = []                                                                                                                             # stores all positions opened and closed throughout trading
        self.book = None                                                                                                                                # our orderbook formally created once trading has completed
        self.trading_allowed=True                                                                                                                       # if False, no more trades may take place.
        self.equity=None                                                                                                                                # to contain the equity curve of our strategy throughout the time horizon of our backtest
        self.risk_free = risk_free                                                                                                                      # risk-free asset to be used when evaluating backtest
        self.benchmark = data                                                                                                                           # our benchmark asset will be the underlying stock

    def add_position(self, open_price: float, open_date: dt.datetime, volume: float, type: str, stop_loss: float, take_profit: float):
        if self.trading_allowed:
            pos = Position(open_date, open_price, type, volume, stop_loss, take_profit)                                                                 # create a position
            if pos.type=='Buy':                                 
                if self.current_balance>=(pos.volume*pos.open_price):                                                                                   # if 'buy' and we have sufficient funds
                    self.positions.append(pos)
                    new_balance = self.current_balance-(pos.volume*pos.open_price)
                    self.current_balance = new_balance                                                                                                  # update balance
                    self.balance_history.append([open_date, self.current_balance])                                                                      # add balance history
                    return True
                else:                                                                                                                                   # if we do not have sufficient funds, don't make the trade
                    return False
            if pos.type=="Sell":                                                                                                                        # it costs nothing to make a sell trade
                self.positions.append(pos)
                new_balance = self.current_balance+(pos.volume*pos.open_price)
                self.current_balance = new_balance
                self.balance_history.append([open_date, self.current_balance])
                return True
    
    def trading_logic(self, row):
        """
        for a row of price data taken from self.data, we place an order if there is a buy or sell signal.  
        The order is taken to self.add_position() and a trade is placed if we are able. 
        """
        standard_volume = 100                                                                                                                           # we set a standard volume on all trades
        if row['Buy']==True:                                                                                                                            # if a buy signal
            stop_loss = row['Close']*0.95                                                                                                               # set stop loss
            take_profit = row['Close']*1.05                                                                                                             # set take profit
            self.add_position(row['Close'], row['Date'], standard_volume, 'Buy', stop_loss, take_profit)                                                # add the position
        elif row['Sell']==True:
            stop_loss = row['Close']*1.05
            take_profit = row['Close']*0.95
            self.add_position(row['Close'], row['Date'], standard_volume, 'Sell', stop_loss, take_profit)
            
    def has_positions(self):
        """
        Checks if the strategy has any open positions. Returns True/False 
        """
        for pos in self.positions:
            if pos.status=='Open':
                return True 
        return False 

    def close_position(self, id, close_date, close_price, forced_close=False):
        """
        Closes a position - specified by its ID - at a given price on a given date. 
        Updates our balance post trade, and adds to the log book.  
        Recall that if we do not have the sufficient funds to close a 'sell' trade, then we must close all 'buy' positions in the entire book, and then come back to see if we can close out
        the 'sell' trade. If we can, to show some risk management, we stop all trading for fear of being too close to isolvancy. If we cannot close the trade, we force the trade to close and 
        except that we now owe some money. We have gone bust! 
        
        `forced_close=True` means we close trades even if we have insufficient funds. We allow our current balance to go negative. 
        """
        # find the position by its id: 
        for position in self.positions:
            if (position.id == id)&(position.status=='Open'):                                                                                           # find position by its id and check if it's open
                
                if position.type=='Buy':                                                                                                                # if type=='buy', close instantly.
                    position.position_close(close_date, close_price)                                                                                    # updates status and computes pnl etc...
                    new_balance = self.current_balance+(position.volume*close_price)                                                                    # compute the new balance
                    self.current_balance = new_balance                                                                                                  # update current balance
                    self.balance_history.append([close_date, self.current_balance])                                                                     # add to balance change history
                    return True

                elif (position.type=='Sell')&((self.current_balance>=(position.volume*close_price))|(forced_close==True)):    # if type=='Sell', we may only close if we have sufficient funds
                    position.position_close(close_date, close_price)
                    new_balance = self.current_balance-(position.volume*close_price)                                                                    # compute the new balance
                    self.current_balance = new_balance                                                                                                  # update current balance
                    self.balance_history.append([close_date, self.current_balance])                                                                     # add to balance change history
                    return True
                
                elif (position.type=='Sell')&(self.current_balance<(position.volume*close_price))&(forced_close==False):                                # if we do not have sufficient funds to close the trade:
                    if self.close_buy_positions(position, close_date, close_price)==True:                                                                                                      
                        print(f"Position [id: {position.id}] closed due to insufficient funds on initial attempt. All positions closed on {close_date.date()} and trading terminated due to risk parameter breaches.")
                    else:
                        print(f"All Trading Terminated on {close_date.date()} due to negative equity resulting from insufficient funds to close intial trade [id: {position.id}].")
                    return self.terminate_trading(close_date, close_price) 
        

    def close_buy_positions(self, original_position, close_date, close_price):
        """
        
        This function closes all trades with the specified type: 'Buy', so that we may increase our current balance.
        
        If, afterwards, we have sufficient funds to close the original 'sell' trade (which triggered the use of this function), then we do so and output==True. 
        If we still cannot close the original 'sell' trade, we output False. 
        """
        # close all 'buy' positions:
        if self.has_positions():
            for position in self.positions:
                if (position.status=='Open')&(position.type=='Buy'):
                    self.close_position(position.id, close_date, close_price)
            # now check if we can close the original sell position:
            if self.current_balance>=(original_position.volume*close_price):
                return True 
        return False
        
    def terminate_trading(self, close_date, close_price):
        """
        Closes out any outstanding positions, and returns self.book.   
        """
        if self.has_positions():
            for position in self.positions:
                self.close_position(position.id, close_date, close_price, forced_close=True)
        self.trading_allowed = False
        self.balance_history = pd.DataFrame(self.balance_history, columns=['Date', 'Equity'])
        self.equity = self.balance_history.drop_duplicates(subset=['Date'], keep='last')
        return self.get_book()
                
    def get_book(self):
        """
        Prints a pandas dataframe containing the orderbook of our trades. 
        """
        orderbook = pd.DataFrame([pos.print_order() for pos in self.positions])        
        self.book = orderbook
        return self.book

    def take_profit_stop_loss(self, row):
        """
        row: contains price data and buy/sell signals for a particular date.
        We iterate through all open positions and check whether or not the stop-loss or take-profit criterion have been met.  
        """
        if self.has_positions():
            for position in self.positions:
                # if 'buy' and price exceeds take-profit, close: 
                if (position.type=='Buy')&(position.take_profit<=row['Close']):
                    self.close_position(position.id, row['Date'], position.take_profit, forced_close=False)
                # if 'buy' and price falls below stop-loss, close:
                elif (position.type=='Buy')&(position.stop_loss>=row['Close']):
                    self.close_position(position.id, row['Date'], position.stop_loss, forced_close=False)
                # if 'sell' and price exceeds stop-loss, close:
                elif (position.type=='Sell')&(position.stop_loss<=row['Close']):
                    self.close_position(position.id, row['Date'], position.stop_loss, forced_close=False)
                # if 'sell' and price falls below take-profit, close:
                elif (position.type=='Sell')&(position.take_profit>=row['Close']):
                    self.close_position(position.id, row['Date'], position.take_profit, forced_close=False)

    def simulate(self):
        """
        Conducts the trading by iterating through each row of data, checking whether or not we need to close positions due to stop-loss or take-profit, then 
        checking if there are any buy signals so that we may open a position.  
        """
        for i, row in self.data.iterrows():
            if self.trading_allowed:
                self.take_profit_stop_loss(row)
                self.trading_logic(row)
        # if we make it to the end of the data with no balance problems, close the book:
        return self.terminate_trading(self.data.iloc[-1]['Date'], self.data.iloc[-1]['Close'])

    def plot(self):
        """
        Plots the results of the backtest by plotting the price process of the stock we are trading, the buy/sell signal, and our current balance over the time period.  
        
        We also plot the bollinger bands. 
        """
        data = self.data[self.data['Date']<=self.book.iloc[-1]['Close Date']]
        fig = plt.figure(figsize=(15, 7))
        # plot the price process throughout the time horizon with buy/sell signals on dates where we made trades
        ax1 = fig.add_subplot(211)
        ax1.plot(data['Date'], data['Close'], color="blue", label="Closing Price", alpha=0.75)
        ax1.plot(data['Date'], data['Upper'], color="purple", label="Upper Band", alpha=0.8)
        ax1.plot(data['Date'], data['Lower'], color="orange", label="Lower Band", alpha=0.8)
        ax1.scatter(self.book[self.book['Type']=='Buy']['Open Date'], self.book[self.book['Type']=='Buy']['Open Price'], marker="^", label="Buy", color="green")
        ax1.scatter(self.book[self.book['Type']=='Sell']['Open Date'], self.book[self.book['Type']=='Sell']['Open Price'], marker="v", label="Sell", color="red")
        plt.grid(True, which='both')
        plt.xlabel("Date", fontsize=10)
        plt.ylabel("Closing Price", fontsize=10)
        plt.legend()
        plt.title(rf"Bollinger Band Reversal Strategy, $m$:{self.bollinger_period}, $\sigma$={self.bollinger_width}, starting balance: {self.starting_balance}, terminal balance: {round(self.current_balance, 3)}")
        
        # plot the equity curve of our trading strategy during the time horizon. 
        ax2 = fig.add_subplot(212)
        ax2.plot(self.equity['Date'], self.equity['Equity'], color="blue", label="Equity")
        plt.hlines(y=self.starting_balance, xmin=self.equity.iloc[0]['Date']-dt.timedelta(days=5), xmax=self.equity.iloc[-1]['Date']+dt.timedelta(days=5), color="red", label="Starting Balance")
        plt.grid(True, which='both')
        plt.xlabel("Date", fontsize=10)
        plt.ylabel("Equity")
        plt.legend()
        plt.show()
        return None
    
    def backtest(self):
        """
        Carries out the full test then plots the results and evaluates backtest using the `evaluate` class. 
        `risk_free` contains yield data for the risk-free rate. 
        `benchmark` contains price data for the benchmark asset.  
        """
        self.simulate()
        eval = Evaluate(self, self.risk_free, self.benchmark, self.starting_balance)
        self.plot()
        return eval.full_eval()



# a third strategy we could try involves the MACD. 
# Here we compute 3 different MACDs and their respective signal lines. 
# The most basic crossover strategy with the MACD is to buy when the MACD line crosses above its singal line, and to sell when the MACD crosses below its signal line. 
# Here we, inspired by an article on Simple moving averages (https://medium.com/@redsword_23261/multi-timeframe-macd-indicator-crossover-trading-strategy-c6821366a1fe), suggest the following:
# Buy when all 3 of the MACDs exhitbit an upwards crossover, and sell when all 3 exhibit a downwards crossover. 
# We also stipulate that if 2/3 MACDs have an upwards crossover, and the long-term MACD line crosses above 0, we should buy. 
# Moreover, if 2/3 MACDs have a downwards crossover, and the long-term MACD line crosses below 0, we should sell. 

class MACD_multi_timeframe:
    def __init__(self, starting_balance: float, data: pd.DataFrame, short_params: list[int], mid_params: list[int], long_params: list[int], risk_free: pd.DataFrame):
        """ 
        starting_balance: floating point indicating the amount of money we have initially, 
        data: pd.DataFrame with columns ['Date', 'Close'] containing the historical price data of the stock in question. 
        (bollinger_period, bollinger_width) settings for the bollinger bands. See indicators.py for details. 
        """
        self.starting_balance = starting_balance                                                                                                        # starting balance
        self.current_balance = starting_balance                                                                                                         # tracks our current balance whilst trading
        self.balance_history = [[data.iloc[0]['Date'], starting_balance]]                                                                               # records how our balance changes over the session
        self.short_params = short_params                                                                                                                # short timeframe MACD settings
        self.mid_params = mid_params                                                                                                                    # medium timeframe MACD params
        self.long_params = long_params                                                                                                                  # long timeframe MACD params
        self.data = Ind.MACD_multi_timeframe(data, self.short_params, self.mid_params, self.long_params, plot_buysell=False)                            # computes the MACD information and indicates the buy/sell signals                                                                                                                        
        self.positions = []                                                                                                                             # stores all positions opened and closed throughout trading
        self.book = None                                                                                                                                # our orderbook formally created once trading has completed
        self.trading_allowed=True                                                                                                                       # if False, no more trades may take place.
        self.equity=None                                                                                                                                # to contain the equity curve of our strategy throughout the time horizon of our backtest
        self.risk_free = risk_free                                                                                                                      # risk-free asset to be used when evaluating backtest
        self.benchmark = data                                                                                                                           # our benchmark asset will be the underlying stock

    def add_position(self, open_price: float, open_date: dt.datetime, volume: float, type: str, stop_loss: float, take_profit: float):
        if self.trading_allowed:
            pos = Position(open_date, open_price, type, volume, stop_loss, take_profit)                                                                 # create a position
            if pos.type=='Buy':                                 
                if self.current_balance>=(pos.volume*pos.open_price):                                                                                   # if 'buy' and we have sufficient funds
                    self.positions.append(pos)
                    new_balance = self.current_balance-(pos.volume*pos.open_price)
                    self.current_balance = new_balance                                                                                                  # update balance
                    self.balance_history.append([open_date, self.current_balance])                                                                      # add balance history
                    return True
                else:                                                                                                                                   # if we do not have sufficient funds, don't make the trade
                    return False
            if pos.type=="Sell":                                                                                                                        # it costs nothing to make a sell trade
                self.positions.append(pos)
                new_balance = self.current_balance+(pos.volume*pos.open_price)
                self.current_balance = new_balance
                self.balance_history.append([open_date, self.current_balance])
                return True
    
    def trading_logic(self, row):
        """
        for a row of price data taken from self.data, we place an order if there is a buy or sell signal.  
        The order is taken to self.add_position() and a trade is placed if we are able. 
        """
        standard_volume = 100                                                                                                                           # we set a standard volume on all trades
        if row['Buy']==True:                                                                                                                            # if a buy signal
            stop_loss = row['Close']*0.95                                                                                                               # set stop loss
            take_profit = row['Close']*1.05                                                                                                             # set take profit
            self.add_position(row['Close'], row['Date'], standard_volume, 'Buy', stop_loss, take_profit)                                                # add the position
        elif row['Sell']==True:
            stop_loss = row['Close']*1.05
            take_profit = row['Close']*0.95
            self.add_position(row['Close'], row['Date'], standard_volume, 'Sell', stop_loss, take_profit)
            
    def has_positions(self):
        """
        Checks if the strategy has any open positions. Returns True/False 
        """
        for pos in self.positions:
            if pos.status=='Open':
                return True 
        return False 

    def close_position(self, id, close_date, close_price, forced_close=False):
        """
        Closes a position - specified by its ID - at a given price on a given date. 
        Updates our balance post trade, and adds to the log book.  
        Recall that if we do not have the sufficient funds to close a 'sell' trade, then we must close all 'buy' positions in the entire book, and then come back to see if we can close out
        the 'sell' trade. If we can, to show some risk management, we stop all trading for fear of being too close to isolvancy. If we cannot close the trade, we force the trade to close and 
        except that we now owe some money. We have gone bust! 
        
        `forced_close=True` means we close trades even if we have insufficient funds. We allow our current balance to go negative. 
        """
        # find the position by its id: 
        for position in self.positions:
            if (position.id == id)&(position.status=='Open'):                                                                                           # find position by its id and check if it's open
                
                if position.type=='Buy':                                                                                                                # if type=='buy', close instantly.
                    position.position_close(close_date, close_price)                                                                                    # updates status and computes pnl etc...
                    new_balance = self.current_balance+(position.volume*close_price)                                                                    # compute the new balance
                    self.current_balance = new_balance                                                                                                  # update current balance
                    self.balance_history.append([close_date, self.current_balance])                                                                     # add to balance change history
                    return True

                elif (position.type=='Sell')&((self.current_balance>=(position.volume*close_price))|(forced_close==True)):    # if type=='Sell', we may only close if we have sufficient funds
                    position.position_close(close_date, close_price)
                    new_balance = self.current_balance-(position.volume*close_price)                                                                    # compute the new balance
                    self.current_balance = new_balance                                                                                                  # update current balance
                    self.balance_history.append([close_date, self.current_balance])                                                                     # add to balance change history
                    return True
                
                elif (position.type=='Sell')&(self.current_balance<(position.volume*close_price))&(forced_close==False):                                # if we do not have sufficient funds to close the trade:
                    if self.close_buy_positions(position, close_date, close_price)==True:                                                                                                      
                        print(f"Position [id: {position.id}] closed due to insufficient funds on initial attempt. All positions closed on {close_date.date()} and trading terminated due to risk parameter breaches.")
                    else:
                        print(f"All Trading Terminated on {close_date.date()} due to negative equity resulting from insufficient funds to close intial trade [id: {position.id}].")
                    return self.terminate_trading(close_date, close_price) 
        

    def close_buy_positions(self, original_position, close_date, close_price):
        """
        
        This function closes all trades with the specified type: 'Buy', so that we may increase our current balance.
        
        If, afterwards, we have sufficient funds to close the original 'sell' trade (which triggered the use of this function), then we do so and output==True. 
        If we still cannot close the original 'sell' trade, we output False. 
        """
        # close all 'buy' positions:
        if self.has_positions():
            for position in self.positions:
                if (position.status=='Open')&(position.type=='Buy'):
                    self.close_position(position.id, close_date, close_price)
            # now check if we can close the original sell position:
            if self.current_balance>=(original_position.volume*close_price):
                return True 
        return False
        
    def terminate_trading(self, close_date, close_price):
        """
        Closes out any outstanding positions, and returns self.book.   
        """
        if self.has_positions():
            for position in self.positions:
                self.close_position(position.id, close_date, close_price, forced_close=True)
        self.trading_allowed = False
        self.balance_history = pd.DataFrame(self.balance_history, columns=['Date', 'Equity'])
        self.equity = self.balance_history.drop_duplicates(subset=['Date'], keep='last')
        return self.get_book()
                
    def get_book(self):
        """
        Prints a pandas dataframe containing the orderbook of our trades. 
        """
        orderbook = pd.DataFrame([pos.print_order() for pos in self.positions])        
        self.book = orderbook
        return self.book

    def take_profit_stop_loss(self, row):
        """
        row: contains price data and buy/sell signals for a particular date.
        We iterate through all open positions and check whether or not the stop-loss or take-profit criterion have been met.  
        """
        if self.has_positions():
            for position in self.positions:
                # if 'buy' and price exceeds take-profit, close: 
                if (position.type=='Buy')&(position.take_profit<=row['Close']):
                    self.close_position(position.id, row['Date'], position.take_profit, forced_close=False)
                # if 'buy' and price falls below stop-loss, close:
                elif (position.type=='Buy')&(position.stop_loss>=row['Close']):
                    self.close_position(position.id, row['Date'], position.stop_loss, forced_close=False)
                # if 'sell' and price exceeds stop-loss, close:
                elif (position.type=='Sell')&(position.stop_loss<=row['Close']):
                    self.close_position(position.id, row['Date'], position.stop_loss, forced_close=False)
                # if 'sell' and price falls below take-profit, close:
                elif (position.type=='Sell')&(position.take_profit>=row['Close']):
                    self.close_position(position.id, row['Date'], position.take_profit, forced_close=False)

    def simulate(self):
        """
        Conducts the trading by iterating through each row of data, checking whether or not we need to close positions due to stop-loss or take-profit, then 
        checking if there are any buy signals so that we may open a position.  
        """
        for i, row in self.data.iterrows():
            if self.trading_allowed:
                self.take_profit_stop_loss(row)
                self.trading_logic(row)
        # if we make it to the end of the data with no balance problems, close the book:
        return self.terminate_trading(self.data.iloc[-1]['Date'], self.data.iloc[-1]['Close'])

    def plot(self):
        """
        Plots the results of the backtest by plotting the price process of the stock we are trading, the buy/sell signal, and our current balance over the time period.  
        
        We also plot the three MACD lines and signal lines.
        
        Finally, we plot the medium-term MACD histogram and its `mid_params[2]`-day EMA, seeing how the price momentum changes over time. 
        """
        data = self.data[self.data['Date']<=self.book.iloc[-1]['Close Date']]
        fig = plt.figure(figsize=(25, 9))
        # plot the price process throughout the time horizon with buy/sell signals on dates where we made trades
        ax1 = fig.add_subplot(221)
        ax1.plot(data['Date'], data['Close'], color="blue", label="Closing Price", alpha=0.75)
        # plot the buy/sell signals:
        ax1.scatter(self.book[self.book['Type']=='Buy']['Open Date'], self.book[self.book['Type']=='Buy']['Open Price'], marker="^", label="Buy", color="green")
        ax1.scatter(self.book[self.book['Type']=='Sell']['Open Date'], self.book[self.book['Type']=='Sell']['Open Price'], marker="v", label="Sell", color="red")
        plt.grid(True, which='both')
        plt.xlabel("Date", fontsize=10)
        plt.ylabel("Closing Price", fontsize=10)
        plt.legend()
        plt.title(rf"MACD Multi Timeframe Strategy, starting balance: {self.starting_balance}, terminal balance: {round(self.current_balance, 3)}")
        # plot the MACDs and their signal lines, along with the medium term histogram:
        ax2 = fig.add_subplot(222)
        ax2.plot(data['Date'], data['MACD'], color="blue", label=f"Medim-term MACD. Settings: {self.mid_params}")
        ax2.plot(data['Date'], data['signal'], color="orange", label=f"Mid-Term MACD Signal Line")
        ax2.plot(data['Date'], data['Short MACD'], color="green", label=f"Short-term MACD. Settings: {self.short_params}")
        ax2.plot(data['Date'], data['Short Signal'], color="purple", label=f"Short-term MACD Signal Line")
        ax2.plot(data['Date'], data['Long MACD'], color="black", label=f"Long-term MACD. Settings: {self.long_params}")
        ax2.plot(data['Date'], data['Long Signal'], color="red", label=f"Long-term MACD Signal Line")
        # plot the buy/sell singals here aswell: 
        ax2.scatter(data[data['Buy']==True]['Date'], data[data['Buy']==True]['MACD'], marker="^", color="green", label="Buy")
        ax2.scatter(data[data['Buy']==True]['Date'], data[data['Buy']==True]['MACD'], marker="v", color="red", label="Sell")
        plt.grid(True, which='both')
        plt.xlabel("Date", fontsize=10)
        plt.legend(loc="lower right", fontsize='xx-small')
        # plot the equity curve of our trading strategy during the time horizon. 
        ax3 = fig.add_subplot(223)
        ax3.plot(self.equity['Date'], self.equity['Equity'], color="blue", label="Equity")
        plt.hlines(y=self.starting_balance, xmin=self.book.iloc[0]['Open Date']-dt.timedelta(days=5), xmax=self.book.iloc[-1]['Close Date']+dt.timedelta(days=5), color="red", label="Starting Balance")
        plt.grid(True, which='both')
        plt.xlabel("Date", fontsize=10)
        plt.ylabel("Equity")
        plt.legend()
        
        ax4 = fig.add_subplot(224)
        # separate times when the histogram is positive, and when it is negative:
        pve = data['Hist'].copy()
        nve = data['Hist'].copy()
        pve[pve<0]=0
        nve[nve>0]=0
        ax4.bar(data['Date'], pve, color="green")
        ax4.bar(data['Date'], nve, color="red")
        ax4.plot(data['Date'], data['Momentum Strength'], color="blue", alpha=0.5, label=f"{self.mid_params[2]}-day EMA of Medium Timeframe Histogram")
        plt.grid(True, which='both')
        plt.xlabel("Date", fontsize=10)
        plt.legend()
        
        plt.show()
        return None
    
    def backtest(self):
        """
        Carries out the full test then plots the results and evaluates backtest using the `evaluate` class. 
        `risk_free` contains yield data for the risk-free rate. 
        `benchmark` contains price data for the benchmark asset.  
        """
        self.simulate()
        eval = Evaluate(self, self.risk_free, self.benchmark, self.starting_balance)
        self.plot()
        return eval.full_eval()    


# finally, we consider a strategy which combines the RSI and MACD:
# we do the following:
# 1. Compute a long-term simple moving average of the daily price
# 2. Comput the MACD on the daily price data
# 3. Compute the RSI on the daily price data
# If the stock breaks the oversold threshold after previously falling below it, we buy if we are in an upward trend. 
# If the stock falls below the overbought threshold after previously moving above it, we sell if we are in a downwards trend. 
# An upwards trend is defined as a period of time where the stock price is > than the simple moving average, or where the MACD has crossed above 0. 
# A downwards trend is defined as a period of time where the stock price is < the simple moving average, or where the MACD is crossed below 0. 

class RSI_and_MACD:
    def __init__(self, starting_balance: float, data: pd.DataFrame, macd_params: list[int], rsi_period: int, rsi_upper: float, rsi_lower: float, moving_avg, risk_free: pd.DataFrame):
        """ 
        starting_balance: floating point indicating the amount of money we have initially, 
        data: pd.DataFrame with columns ['Date', 'Close'] containing the historical price data of the stock in question. 
        (bollinger_period, bollinger_width) settings for the bollinger bands. See indicators.py for details. 
        """
        self.starting_balance = starting_balance                                                                                                                    # starting balance
        self.current_balance = starting_balance                                                                                                                     # tracks our current balance whilst trading
        self.balance_history = [[data.iloc[0]['Date'], starting_balance]]                                                                                           # records how our balance changes over the session
        self.macd_params = macd_params                                                                                                                              # MACD settings 
        self.rsi_upper = rsi_upper                                                                                                                                  # rsi_overbought threshold
        self.rsi_lower = rsi_lower                                                                                                                                  # rsi_oversold threshold 
        self.rsi_period = rsi_period                                                                                                                                # rsi_period 
        self.moving_avg = moving_avg                                                                                                                                # moving average period
        self.data = Ind.RSI_and_MACD(data, self.rsi_period, self.rsi_upper, self.rsi_lower, self.macd_params, self.moving_avg, plot=False).iloc[self.moving_avg:]   # computes MACD and RSI indicators and sets the buy/sell signals.                                                                                                      
        self.positions = []                                                                                                                                         # stores all positions opened and closed throughout trading
        self.book = None                                                                                                                                            # our orderbook formally created once trading has completed
        self.trading_allowed=True                                                                                                                                   # if False, no more trades may take place.
        self.equity=None                                                                                                                                            # to contain the equity curve of our strategy throughout the time horizon of our backtest
        self.risk_free = risk_free                                                                                                                                  # risk-free asset to be used when evaluating backtest
        self.benchmark = data                                                                                                                                       # our benchmark asset will be the underlying stock

    def add_position(self, open_price: float, open_date: dt.datetime, volume: float, type: str, stop_loss: float, take_profit: float):
        if self.trading_allowed:
            pos = Position(open_date, open_price, type, volume, stop_loss, take_profit)                                                                 # create a position
            if pos.type=='Buy':                                 
                if self.current_balance>=(pos.volume*pos.open_price):                                                                                   # if 'buy' and we have sufficient funds
                    self.positions.append(pos)
                    new_balance = self.current_balance-(pos.volume*pos.open_price)
                    self.current_balance = new_balance                                                                                                  # update balance
                    self.balance_history.append([open_date, self.current_balance])                                                                      # add balance history
                    return True
                else:                                                                                                                                   # if we do not have sufficient funds, don't make the trade
                    return False
            if pos.type=="Sell":                                                                                                                        # it costs nothing to make a sell trade
                self.positions.append(pos)
                new_balance = self.current_balance+(pos.volume*pos.open_price)
                self.current_balance = new_balance
                self.balance_history.append([open_date, self.current_balance])
                return True
    
    def trading_logic(self, row):
        """
        for a row of price data taken from self.data, we place an order if there is a buy or sell signal.  
        The order is taken to self.add_position() and a trade is placed if we are able. 
        """
        standard_volume = 100                                                                                                                           # we set a standard volume on all trades
        if row['Buy']==True:                                                                                                                            # if a buy signal
            stop_loss = row['Close']*0.95                                                                                                               # set stop loss
            take_profit = row['Close']*1.05                                                                                                             # set take profit
            self.add_position(row['Close'], row['Date'], standard_volume, 'Buy', stop_loss, take_profit)                                                # add the position
        elif row['Sell']==True:
            stop_loss = row['Close']*1.05
            take_profit = row['Close']*0.95
            self.add_position(row['Close'], row['Date'], standard_volume, 'Sell', stop_loss, take_profit)
            
    def has_positions(self):
        """
        Checks if the strategy has any open positions. Returns True/False 
        """
        for pos in self.positions:
            if pos.status=='Open':
                return True 
        return False 

    def close_position(self, id, close_date, close_price, forced_close=False):
        """
        Closes a position - specified by its ID - at a given price on a given date. 
        Updates our balance post trade, and adds to the log book.  
        Recall that if we do not have the sufficient funds to close a 'sell' trade, then we must close all 'buy' positions in the entire book, and then come back to see if we can close out
        the 'sell' trade. If we can, to show some risk management, we stop all trading for fear of being too close to isolvancy. If we cannot close the trade, we force the trade to close and 
        except that we now owe some money. We have gone bust! 
        
        `forced_close=True` means we close trades even if we have insufficient funds. We allow our current balance to go negative. 
        """
        # find the position by its id: 
        for position in self.positions:
            if (position.id == id)&(position.status=='Open'):                                                                                           # find position by its id and check if it's open
                
                if position.type=='Buy':                                                                                                                # if type=='buy', close instantly.
                    position.position_close(close_date, close_price)                                                                                    # updates status and computes pnl etc...
                    new_balance = self.current_balance+(position.volume*close_price)                                                                    # compute the new balance
                    self.current_balance = new_balance                                                                                                  # update current balance
                    self.balance_history.append([close_date, self.current_balance])                                                                     # add to balance change history
                    return True

                elif (position.type=='Sell')&((self.current_balance>=(position.volume*close_price))|(forced_close==True)):    # if type=='Sell', we may only close if we have sufficient funds
                    position.position_close(close_date, close_price)
                    new_balance = self.current_balance-(position.volume*close_price)                                                                    # compute the new balance
                    self.current_balance = new_balance                                                                                                  # update current balance
                    self.balance_history.append([close_date, self.current_balance])                                                                     # add to balance change history
                    return True
                
                elif (position.type=='Sell')&(self.current_balance<(position.volume*close_price))&(forced_close==False):                                # if we do not have sufficient funds to close the trade:
                    if self.close_buy_positions(position, close_date, close_price)==True:                                                                                                      
                        print(f"Position [id: {position.id}] closed due to insufficient funds on initial attempt. All positions closed on {close_date.date()} and trading terminated due to risk parameter breaches.")
                    else:
                        print(f"All Trading Terminated on {close_date.date()} due to negative equity resulting from insufficient funds to close intial trade [id: {position.id}].")
                    return self.terminate_trading(close_date, close_price) 
        

    def close_buy_positions(self, original_position, close_date, close_price):
        """
        
        This function closes all trades with the specified type: 'Buy', so that we may increase our current balance.
        
        If, afterwards, we have sufficient funds to close the original 'sell' trade (which triggered the use of this function), then we do so and output==True. 
        If we still cannot close the original 'sell' trade, we output False. 
        """
        # close all 'buy' positions:
        if self.has_positions():
            for position in self.positions:
                if (position.status=='Open')&(position.type=='Buy'):
                    self.close_position(position.id, close_date, close_price)
            # now check if we can close the original sell position:
            if self.current_balance>=(original_position.volume*close_price):
                return True 
        return False
        
    def terminate_trading(self, close_date, close_price):
        """
        Closes out any outstanding positions, and returns self.book.   
        """
        if self.has_positions():
            for position in self.positions:
                self.close_position(position.id, close_date, close_price, forced_close=True)
        self.trading_allowed = False
        self.balance_history = pd.DataFrame(self.balance_history, columns=['Date', 'Equity'])
        self.equity = self.balance_history.drop_duplicates(subset=['Date'], keep='last')
        return self.get_book()
                
    def get_book(self):
        """
        Prints a pandas dataframe containing the orderbook of our trades. 
        """
        orderbook = pd.DataFrame([pos.print_order() for pos in self.positions])        
        self.book = orderbook
        return self.book

    def take_profit_stop_loss(self, row):
        """
        row: contains price data and buy/sell signals for a particular date.
        We iterate through all open positions and check whether or not the stop-loss or take-profit criterion have been met.  
        """
        if self.has_positions():
            for position in self.positions:
                # if 'buy' and price exceeds take-profit, close: 
                if (position.type=='Buy')&(position.take_profit<=row['Close']):
                    self.close_position(position.id, row['Date'], position.take_profit, forced_close=False)
                # if 'buy' and price falls below stop-loss, close:
                elif (position.type=='Buy')&(position.stop_loss>=row['Close']):
                    self.close_position(position.id, row['Date'], position.stop_loss, forced_close=False)
                # if 'sell' and price exceeds stop-loss, close:
                elif (position.type=='Sell')&(position.stop_loss<=row['Close']):
                    self.close_position(position.id, row['Date'], position.stop_loss, forced_close=False)
                # if 'sell' and price falls below take-profit, close:
                elif (position.type=='Sell')&(position.take_profit>=row['Close']):
                    self.close_position(position.id, row['Date'], position.take_profit, forced_close=False)

    def simulate(self):
        """
        Conducts the trading by iterating through each row of data, checking whether or not we need to close positions due to stop-loss or take-profit, then 
        checking if there are any buy signals so that we may open a position.  
        """
        for i, row in self.data.iterrows():
            if self.trading_allowed:
                self.take_profit_stop_loss(row)
                self.trading_logic(row)
        # if we make it to the end of the data with no balance problems, close the book:
        return self.terminate_trading(self.data.iloc[-1]['Date'], self.data.iloc[-1]['Close'])

    def plot(self):
        """
        Plots the results of the backtest by plotting the price process of the stock we are trading, the buy/sell signal, and our current balance over the time period.  
        
        We also plot the MACD lines, with the histogram and we then plot the RSI.
        
        """
        data = self.data[self.data['Date']<=self.book.iloc[-1]['Close Date']]
        fig = plt.figure(figsize=(25, 9))
        # plot the price process throughout the time horizon with buy/sell signals on dates where we made trades
        ax1 = fig.add_subplot(221)
        ax1.plot(data['Date'], data['Close'], color="blue", label="Closing Price", alpha=0.75)
        # plot the buy/sell signals:
        ax1.scatter(self.book[self.book['Type']=='Buy']['Open Date'], self.book[self.book['Type']=='Buy']['Open Price'], marker="^", label="Buy", color="green")
        ax1.scatter(self.book[self.book['Type']=='Sell']['Open Date'], self.book[self.book['Type']=='Sell']['Open Price'], marker="v", label="Sell", color="red")
        ax1.plot(data['Date'], data[f"{self.moving_avg}-day SMA"], color="purple", label=f"{self.moving_avg}-day SMA")
        plt.grid(True, which='both')
        plt.xlabel("Date", fontsize=10)
        plt.ylabel("Closing Price", fontsize=10)
        plt.legend()
        plt.title(rf"RSI and MACD Strategy, starting balance: {self.starting_balance}, terminal balance: {round(self.current_balance, 3)}")
        # plot the MACDs and their signal lines, along with the medium term histogram:
        ax2 = fig.add_subplot(222)
        ax2.plot(data['Date'], data['Daily MACD'], color="blue", label=f"MACD Line. Settings: {self.macd_params}")
        ax2.plot(data['Date'], data['Daily MACD Signal'], color="orange", label=f"MACD Signal Line")
        pve = data['Daily Hist'].copy()
        nve = data['Daily Hist'].copy()
        pve[pve<0]=0
        nve[nve>0]=0
        ax2.bar(data['Date'], pve, color="green")
        ax2.bar(data['Date'], nve, color="red")
        # plot the buy/sell singals here aswell: 
        ax2.scatter(data[data['Buy']==True]['Date'], data[data['Buy']==True]['Daily MACD'], marker="^", color="green", label="Buy")
        ax2.scatter(data[data['Buy']==True]['Date'], data[data['Buy']==True]['Daily MACD'], marker="v", color="red", label="Sell")
        plt.grid(True, which='both')
        plt.xlabel("Date", fontsize=10)
        plt.legend()
        # plot the equity curve of our trading strategy during the time horizon. 
        ax3 = fig.add_subplot(223)
        ax3.plot(self.equity['Date'], self.equity['Equity'], color="blue", label="Equity")
        plt.hlines(y=self.starting_balance, xmin=self.equity.iloc[0]['Date']-dt.timedelta(days=5), xmax=self.equity.iloc[-1]['Date']+dt.timedelta(days=5), color="red", label="Starting Balance")
        plt.grid(True, which='both')
        plt.xlabel("Date", fontsize=10)
        plt.ylabel("Equity")
        plt.legend()
        
        ax4 = fig.add_subplot(224)
        ax4.plot(data['Date'], data['RSI'], color="blue", label=f"RSI. Period: {self.rsi_period}", alpha=0.75)
        plt.hlines(y=self.rsi_upper, xmin=data.iloc[0]['Date'], xmax=data.iloc[-1]['Date'], color="red", label="Overbought")
        plt.hlines(y=self.rsi_lower, xmin=data.iloc[0]['Date'], xmax=data.iloc[-1]['Date'], color="red", label="Oversold")
        plt.grid(True, which='both')
        plt.xlabel("Date", fontsize=10)
        plt.legend()
        
        plt.show()
        return None  

    def backtest(self):
        """
        Carries out the full test then plots the results and evaluates backtest using the `evaluate` class. 
        `risk_free` contains yield data for the risk-free rate. 
        `benchmark` contains price data for the benchmark asset.  
        """
        self.simulate()
        eval = Evaluate(self, self.risk_free, self.benchmark, self.starting_balance)
        self.plot()
        return eval.full_eval()    

    

# define a class which evaluates the results of the backtest by computing a few key metrics:
# we compute gross, net, and log returns, and use these to compute the beta and Sharpe ratios. 
# The beta is computed with respect to the benchmark, which is taken to be the underlying stock price data. 
# ... I.e. we are comparing our trading strategy to just simply buying and holding the underlying stock throughout the time horizon of the backtest.
# The Sharpe ratio is computed with respect to a risk-free asset, such as 10Yr US Tbill yields. 
class Evaluate:
    def __init__(self, strategy, risk_free: pd.DataFrame, benchmark: pd.DataFrame, starting_balance: float):
        self.starting_balance = starting_balance                                                                            # initial capital
        self.book = strategy.book                                                                                           # order book created during trading
        self.risk_free = risk_free                                                                                          # time series data of the risk-free asset
        self.benchmark = benchmark                                                                                          # time series data of the benchmark asset
        self.equity = strategy.equity.copy()                                                                                # equity curve throughout the time horizon
    
    # define a funcion which computes the returns for a given strategy order book: 
    def compute_book_returns(self):
        """
        We compute the daily gross returns, net returns, and log returns, all for future use in examining our backtest.
        """
        # net return is the pnl/original value of trade.
        book_gross_returns = self.equity['Equity']/self.equity['Equity'].shift(1)
        book_net_returns = book_gross_returns -1 
        book_log_returns = np.log(book_gross_returns)
        returns = pd.DataFrame()
        returns ['Close Date'] = self.equity['Date']
        returns['Gross Return'] = book_gross_returns
        returns['Log Return'] = book_log_returns
        returns['Net Return'] = book_net_returns
        return returns  

    # compute the net return on equity of the strategy:
    def compute_return_on_equity(self):
        return self.compute_net_PnL()/self.starting_balance
    
    # compute the net profit/loss of the strategy:
    def compute_net_PnL(self):
        return self.equity.iloc[-1]['Equity']-self.starting_balance
    
    # compute the Sharpe ratio of the strategy with respect to the risk-free asset.
    def compute_Sharpe(self):
        """ 
        Takes the order_book from one of our strategies, and given price data for our risk-free asset,
        computes the Sharpe ratio of our trading strategy over the time horizon of the historical data.
        """
        # first let's sort out the trading data of our risk_free asset. 
        # the dataframe should contain two columns: 'Date', 'Yield'. 
        # It will be daily data, so we must remove dates from the dataframe which don't align with trading dates in `book`.
        dates = self.equity['Date']
        risk_free_aligned = []
        
        for date in dates:
            r = self.risk_free[self.risk_free['Date'].eq(date)]
            if not len(r['Date'].values)==0:                                                                                            # some datapoints are missing, so we unfortunately must skip them:
                row = {'Date': r['Date'].values[0], 'Yield': r['Yield'].values[0]}
                risk_free_aligned.append(row)
        risk_free_aligned = pd.DataFrame(risk_free_aligned)
        # now we must compute the risk-free returns:
        risk_free_book_returns = risk_free_aligned.copy()
        risk_free_book_returns['Daily Gross Return'] = (risk_free_aligned['Yield']/risk_free_aligned['Yield'].shift(1))
        risk_free_book_returns['Daily Log Return'] = np.log(risk_free_book_returns['Daily Gross Return'])
        risk_free_book_returns = risk_free_book_returns.iloc[1:]
        # augment the returns dataframe for the sharpe ratio: 
        book_log_returns = self.compute_book_returns()
        returns = book_log_returns.copy()
        returns['Risk Free Log returns'] = risk_free_book_returns['Daily Log Return']
        returns['Excess Returns'] = returns['Log Return']-returns['Risk Free Log returns']
        mean_excess_return = np.mean(returns['Excess Returns'])
        std_excess_return = np.std(returns['Excess Returns'])
        return mean_excess_return/std_excess_return
    
    # compute the historical volatility of the log returns of the strategy:
    def compute_volatility(self):
        returns = self.compute_book_returns()
        return np.std(returns['Net Return'])
    
    # compute the beta of the strategy with respect to the benchmark:
    def compute_beta(self):
        """
        We take the benchmark to be the underlying asset, so that we may compare the trading strategy to just simply
        buying and holding the underlying asset. 
        Again, we consider the log-returns.
        """
        # we begin by aligning the dates of the trading strategy trades with that of the benchmark dataframe:
        book_dates = self.equity['Date']
        benchmark_aligned = []
        for date in book_dates:
            r = self.benchmark[self.benchmark['Date'].eq(date)]
            row = {'Date': r['Date'].values[0], 'Close': r['Close'].values[0]}
            benchmark_aligned.append(row)
        benchmark_aligned = pd.DataFrame(benchmark_aligned)
        # now extract the returns
        book_log_returns = self.compute_book_returns()['Log Return']
        benchmark_gross_returns = benchmark_aligned['Close']/benchmark_aligned['Close'].shift(1)
        benchmark_log_returns = np.log(benchmark_gross_returns)
        # compute variance of benchmark returns
        benchmark_log_returns_var = np.var(benchmark_log_returns.iloc[1:])
        log_returns_covar = np.cov(book_log_returns.iloc[1:], benchmark_log_returns.iloc[1:])[0,1]
        return log_returns_covar/benchmark_log_returns_var
        
    def full_eval(self):
        """
        Computes all of the metrics listed in this class for a given trading strategy: 
        """     
        return_on_equity = self.compute_return_on_equity()*100
        net_pnl = self.compute_net_PnL()
        sharpe = self.compute_Sharpe()
        vol = self.compute_volatility()*100
        beta = self.compute_beta()
        return {'Starting Balance': f"{self.starting_balance}",
                'PnL': f"{net_pnl:.3f}", 'Return on Equity (%)': f"{return_on_equity:.3f}",
                'Sharpe Ratio': f"{sharpe:.3f}", 
                'Volatility (%)': f"{vol:.3f}", 'Beta': f"{beta:.3f}"}