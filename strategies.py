import pandas as pd
from indicators import Indicators

class Strategies:
    def __init__(self):
        self.indicators = Indicators()

    def prepare_dataframe(self, historical_data):
        df = pd.DataFrame(historical_data)
        df.columns = ["timestamp", "open", "high", "low", "close", "volume", "turnover"]
        df['close'] = df['close'].astype(float)
        df.sort_values('timestamp', inplace=True)
        return df

    def breakout_strategy(self, df):
        current_price = df['close'].iloc[-1]
        resistance = df['Bollinger_upper'].iloc[-1]
        support = df['Bollinger_lower'].iloc[-1]

        # Identify breakout above resistance and breakdown below support
        if current_price > resistance:
            return 'breakout', support, resistance
        elif current_price < support:
            return 'breakdown', support, resistance
        return None, support, resistance
