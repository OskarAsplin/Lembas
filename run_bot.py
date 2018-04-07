import logging
import trading_bot
from datetime import datetime

# Initialize bot and run
logging.basicConfig(filename='trading_from_' + datetime.utcnow().strftime("%Y%m%d") + '.log',level=logging.INFO)
interval = 10       # seconds
bot = trading_bot.TradingBot(interval)
bot.run()