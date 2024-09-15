# trading_bot.py

import schedule
import time
import logging
from data_fetcher import DataFetcher
from indicators import Indicators
from strategies import Strategies
from risk_management import RiskManagement
from dotenv import load_dotenv
import os
import pandas as pd
from bybit_demo_session import BybitDemoSession
from helpers import Helpers  # Import the Helpers module

class TradingBot:
    def __init__(self):
        load_dotenv()

        self.api_key = os.getenv("BYBIT_API_KEY")
        self.api_secret = os.getenv("BYBIT_API_SECRET") 

        if not self.api_key or not self.api_secret:
            raise ValueError("API keys not found. Please set BYBIT_API_KEY and BYBIT_API_SECRET in your .env file.")

        self.data_fetcher = BybitDemoSession(self.api_key, self.api_secret)

        self.strategy = Strategies()
        self.indicators = Indicators()
        self.risk_management = RiskManagement(
            atr_multiplier=float(os.getenv("ATR_MULTIPLIER", 1.0)),
            risk_ratio=float(os.getenv("RISK_RATIO", 1.0))
        )
        self.symbol = os.getenv("TRADING_SYMBOL", 'BTCUSDT')
        self.quantity = float(os.getenv("TRADE_QUANTITY", 0.03))

        # Load trading parameters
        self.interval = os.getenv("TRADING_INTERVAL", '1')
        self.limit = int(os.getenv("TRADING_LIMIT", 100))
        self.leverage = int(os.getenv("LEVERAGE", 10))

        # Load strategy switches
        self.enable_scalping_strategy = os.getenv("ENABLE_SCALPING_STRATEGY", "True").lower() == "true"

        # Set up logging
        logging.basicConfig(filename='trading_bot.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        
    def job(self):
        print("--------------------")

        is_open_positions = self.data_fetcher.get_open_positions(self.symbol)
        if is_open_positions:
            print("There is already an open position. A new order will not be placed.")
            return

        is_open_orders = self.data_fetcher.get_open_orders(self.symbol)
        if is_open_orders:
            print("There is an open limit order. A new order will not be placed.")
            return
        
        get_historical_data = self.data_fetcher.get_historical_data(self.symbol, self.interval, self.limit)
        if get_historical_data is None:
            print("Failed to retrieve historical data.")
            return

        df = self.strategy.prepare_dataframe(get_historical_data)

        # Calculate and print indicators using helper method
        rsi, bollinger_upper, bollinger_middle, bollinger_lower, current_price = Helpers.calculate_and_print_indicators(df, self.indicators)

        trend, support, resistance = self.strategy.breakout_strategy(df)
        if trend:

            last_closed_position = self.data_fetcher.get_last_closed_position(self.symbol)
            if last_closed_position:
                last_closed_time = int(last_closed_position['updatedTime']) / 1000
                current_time = time.time()
                time_since_last_close = current_time - last_closed_time
                print(f"Time since last closed position: {int(time_since_last_close)} seconds")
                if time_since_last_close < 120:
                    print("The last closed position was less than 2 minutes ago. A new order will not be placed.")
                    return
                
            # Stop-loss and take-profit based on breakout strategy rules
            stop_loss, take_profit = self.risk_management.calculate_breakout_risk_management(current_price, trend, support, resistance)

            # Ensure stop-loss is correctly set below buy price and above sell price
            if trend == 'breakout' and stop_loss >= current_price:
                stop_loss = current_price * 0.995  # Ensure stop-loss is below the current price
                print(f"Adjusted stop-loss for Buy order: {stop_loss:.2f}")

            print(f"Trend: {trend.upper()}")
            print(f"Support: {support:.2f}, Resistance: {resistance:.2f}")
            print(f"Stop Loss: {stop_loss:.2f}")
            print(f"Take Profit: {take_profit:.2f}")

            side = 'Buy' if trend == 'breakout' else 'Sell'
            print(f"Order side: {side}")

            order_result = self.data_fetcher.place_order(
                symbol=self.symbol,
                side=side,
                qty=self.quantity,
                current_price=current_price,
                leverage=self.leverage,
                stop_loss=stop_loss,
                take_profit=take_profit
            )

            if order_result:
                print(f"Order successfully placed: {order_result}")
            else:
                print("Failed to place order.")
        else:
            print("No breakout detected. No orders placed.")


    def run(self):
        self.job()
        schedule.every(3).seconds.do(self.job)
        while True:
            schedule.run_pending()
            time.sleep(1)

if __name__ == "__main__":
    bot = TradingBot()
    bot.run()
