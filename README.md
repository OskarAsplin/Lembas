# Lembas
This is the main software repository for the Lembas project. Lembas is in its entirety a trading bot which autonomously makes a profit of arbitrage in the cryptocurrency market. 

Lembas conducts arbitrage between cryptocurrencies on the international exchange sites GDAX and Kraken. The internal trading on Kraken is done by investing and selling a coin when the there is a profitable difference between the price in Euros and USD. No long term trading is done using Lembas. Future price speculation is not a part of this trading bot, as this is highly risky and can be compared to gambling. Only safe and instant trades are made.

Although the bot in its current state only performs arbitrage on Kraken and GDAX, it is made in such a way that one could easily expand its use to other exchange sites and/or markets. The logic and implemented functions in the project are generalized to be usable by other exchange APIs. To set up the bot to include another exchange site, one simply has to write the corresponding functions for the new API interface in a similar fashion to kraken_api.py and gdax_api.py. Another config.py file will also need to be written to set up a private connection to the given site.

#### File content
All trade logic is located in trading.py. The trading criterias are constantly checked in a while loop in trading_bot.py. In rules.py one can set the wanted investing rules according to ones own risk assessment. The project also contains a mail module to inform the user about current trades, profits so far, etc.

The bot is run using run_bot.py

#### Risks connected to using the bot:

- If the bot is in the middle of a trade and the bot shuts down due to a power outage on the running computer, or one of the exchange sites is currently not responding for some reason, ones money might be temporarily invested in a coin. The sell price for the given coin may then be unpredictable when the system is up and running again, resulting in a possibly unprofitable/unsuccessful trade.
- Another issue that may lead to some loss is if one trades coins with slow transaction times from one exchange to another. During the time the coin is being sent from one exchange to the other, the price may change unfavorably and lead to a loss.
- When doing internal trading between USD and EURO, one should be aware that even though these currencies are fairly stable, they may fluctuate some leading to minor losses. The variable 'prev_days_EUR_USD' combined with ivestment criteria checks manages to eliminate some of this risk of daily spikes, but it is always difficult to predict future development of these currencies.
