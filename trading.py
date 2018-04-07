import logging
logger = logging.getLogger(__name__)
from datetime import datetime
import time
import rules
import currency_rate
import send_crypto_mail
from decimal import *


class TradeTools(object):
	def __init__(self, trader):
		self.trader = trader

	def safe_market_buy_price(self, coin, currency='EUR', internal=False):
		if internal:
			currency_amount = rules.buy_internal[currency]
		else:
			currency_amount = rules.buy_euro[self.trader.exchangeName][coin]
		[bids, asks] = self.trader.get_order_book(coin, currency, count='25', level=2)
		total = 0
		total_min = (currency_amount)/float(asks[0][0])
		for price,size,_ in asks:
			total += float(size)
			if total >= total_min:
				return Decimal(price)
		print('total_min too big at safe_market_buy_price. total_min: %2.2f total: %2.2f' % (total_min, total))
		return Decimal(asks[-1][0])

	def safe_market_sell_price(self, coin, currency='EUR', internal=False):
		if internal:
			currency_amount = rules.buy_internal[currency]
		else:
			currency_amount = rules.sell_euro[self.trader.exchangeName][coin]
		[bids, asks] = self.trader.get_order_book(coin, currency, count='25', level=2)
		total = 0
		total_min = (currency_amount)/float(bids[0][0])
		for price,size,_ in bids:
			total += float(size)
			if total >= total_min:
				return Decimal(price)
		print('total_min too big at safe_market_sell_price. total_min: %2.2f total: %2.2f' % (total_min, total))
		return Decimal(bids[-1][0])

	def get_market_ask_bid(self, coin, currency='EUR'):
		[bids, asks] = self.trader.get_order_book(coin, currency, count='5', level=1)
		bid = Decimal(bids[0][0])
		ask = Decimal(asks[0][0])
		return [ask, bid]

	def low_limit_buy_price(self, coin, currency='EUR'):
		dec = self.trader.decimals_price[coin]
		dec_place = Decimal('1E-'+str(dec))
		[ask, bid] = self.get_market_ask_bid(coin, currency)
		my_bid_price = bid + 1*dec_place if ask - bid > 1*dec_place else bid
		return my_bid_price

	def low_limit_sell_price(self, coin, currency='EUR'):
		dec = self.trader.decimals_price[coin]
		dec_place = Decimal('1E-'+str(dec))
		[ask, bid] = self.get_market_ask_bid(coin, currency)
		my_ask_price = ask - 1*dec_place if ask - bid > 1*dec_place else ask
		return my_ask_price

	def valid_order_size(self, coin, size):
		return True if size >= self.trader.min_order_size[coin] else False

	def internal_limit_buy_diff(self, coin, b_currency='EUR', s_currency='USD'):
		buy_price = float(self.low_limit_buy_price(coin, currency=b_currency))
		sell_price = float(self.safe_market_sell_price(coin, currency=s_currency, internal=True))
		if b_currency=='USD': buy_price = currency_rate.USD_to_EUR * buy_price
		if s_currency=='USD': sell_price = currency_rate.USD_to_EUR * sell_price
		diff = 100*(sell_price/buy_price - 1.)
		if b_currency == 'USD':
			if diff > rules.internal_invest_lim['to_EUR']:
				return [True, diff, buy_price]
		elif b_currency == 'EUR':
			if diff > rules.internal_invest_lim['to_USD']:
				return [True, diff, buy_price]
		return [False, diff, buy_price]

# code:
# 0 - No attempted trades
# 1 - Succesful trade
# 2 - Trade aborted but no coins on exchanges
# 3 - Trade failed

class TradeLogic(object):
	def __init__(self):
		pass

	def get_internal_coin_amount(self, price, currency):
		return (Decimal(rules.buy_internal[currency])/price).quantize(Decimal('.000001'), rounding=ROUND_DOWN)

	def buy_limit_order(self, tradeTools, coin, b_currency, fun_coin_amount, fun_criteria, *args):
		logger.info('buy_limit_order(). Coin: {:}\tB_currency: {:}'.format(coin, b_currency))
		print('buy_limit_order')
		trader = tradeTools.trader
		# Add limit order
		my_bid_price = tradeTools.low_limit_buy_price(coin, currency=b_currency)
		amount_coin = fun_coin_amount(my_bid_price, b_currency)
		data = trader.add_buy_order(coin, currency=b_currency, amount=amount_coin, order_type='limit', price=my_bid_price)

		# Checking if order was filled
		open_orders = trader.get_open_orders()
		while open_orders:
			time.sleep(1)
			# Check if criteria is met
			[trade, _, _] = fun_criteria(*args)
			if trade == False:
				trader.cancel_order()

			market_bid = tradeTools.get_market_ask_bid(coin, currency=b_currency)[1]

			if market_bid - my_bid_price > Decimal('0.0') or trade == False:
				# Cancel order
				trader.cancel_order()
				open_orders = trader.get_open_orders()
				while open_orders:
					trader.cancel_order()
					open_orders = trader.get_open_orders()

				coin_balance = trader.get_coin_balance(coin)

				if tradeTools.valid_order_size(coin, coin_balance):
					print('Some of the order was filled. Quiting buy_limit_order()')
					return 1
				else:
					[trade, _, _] = fun_criteria(*args)
					if trade == False:
						print('Nothing was bought. Quiting buy_limit_order()')
						return 2
					else:
						# Add limit order
						my_bid_price = tradeTools.low_limit_buy_price(coin, currency=b_currency)
						amount_coin = fun_coin_amount(my_bid_price, b_currency)
						data = trader.add_buy_order(coin, currency=b_currency, amount=amount_coin, order_type='limit', price=my_bid_price)

			open_orders = trader.get_open_orders()
		return 1

	def sell_limit_order(self, tradeTools, coin, s_currency, fun_criteria):
		logger.info('sell_limit_order(). Coin: {:}\tS_currency: {:}'.format(coin, s_currency))
		trader = tradeTools.trader
		# Add limit order
		coin_balance = trader.get_coin_balance(coin)
		if not tradeTools.valid_order_size(coin, coin_balance):
			return 1
		my_ask_price = tradeTools.low_limit_sell_price(coin, currency=s_currency)
		data = trader.add_sell_order(coin, currency=s_currency, amount=coin_balance, order_type='limit', price=my_ask_price)

		# Checking if order was filled
		open_orders = trader.get_open_orders()
		while open_orders:
			time.sleep(1)
			# Check if criteria is met
			market_ask = tradeTools.get_market_ask_bid(coin, currency=s_currency)[0]
			trade = fun_criteria(market_ask)
			if trade == False:
				trader.cancel_order()
				return 3

			if my_ask_price - market_ask > Decimal('0.0'):
				# Cancel order
				trader.cancel_order()
				open_orders = trader.get_open_orders()
				while open_orders:
					trader.cancel_order()
					open_orders = trader.get_open_orders()

				market_ask = tradeTools.get_market_ask_bid(coin, currency=s_currency)[0]
				trade = fun_criteria(market_ask)
				if trade == False:
					print('Nothing was sold. Criteria no longer met.')
					return 3
				else:
					# Add limit order
					coin_balance = trader.get_coin_balance(coin)
					if not tradeTools.valid_order_size(coin, coin_balance):
						return 1
					my_ask_price = tradeTools.low_limit_sell_price(coin, currency=s_currency)
					data = trader.add_sell_order(coin, currency=s_currency, amount=coin_balance, order_type='limit', price=my_ask_price)

			open_orders = trader.get_open_orders()
		return 1

	def internal_trade(self, tradeTools, coin, b_currency='USD', s_currency='EUR'):
		logger.info('internal_trade(). Coin: {:}\tB_currency: {:}\tS_currency: {:}'.format(coin, b_currency, s_currency))
		trader = tradeTools.trader
		print('make_internal_trade()')

		# Add limit order
		self.buy_limit_order(tradeTools, coin, b_currency, self.get_internal_coin_amount, tradeTools.internal_limit_buy_diff, coin, b_currency, s_currency)

		# Check coin balance
		coin_balance = trader.get_coin_balance(coin)
		if not tradeTools.valid_order_size(coin, coin_balance):
			print('No coins were bought. internal_trade')
			return 2

		print('Amount of coins bought: ' + str(coin_balance))

		# # Add sell order (market)
		# print('Adding sell order (market) for coin amount: ' + str(coin_balance))
		# data = trader.add_sell_order(coin, currency=s_currency, amount=coin_balance, order_type='market')

		# Sell market/limit
		start_ask_price = tradeTools.low_limit_sell_price(coin, currency=s_currency)
		fun_criteria = lambda x: True if (x/start_ask_price) > 0.999 else False
		self.sell_limit_order(tradeTools, coin, s_currency, fun_criteria)

		coin_balance = trader.get_coin_balance(coin)
		if tradeTools.valid_order_size(coin, coin_balance):
			trader.add_sell_order(coin, s_currency, amount=coin_balance, order_type='market')
		
		time.sleep(2)
		coin_balance = trader.get_coin_balance(coin)
		if not tradeTools.valid_order_size(coin, coin_balance):
			print('internal_trade() finished successfully')
			return 1
		print('Some coins still on exchange!')
		print(coin_balance)
		return 3

	def cross_exchange_trade(self, from_exchange_tools, to_exchange_tools, coin, amount_coin, fun_critera):
		code = self.buy_cross_exchange(from_exchange_tools, to_exchange_tools, coin, amount_coin, fun_critera)
		if code == 1:
			t = datetime.time(datetime.now())
			print('Coins were bought at time: ' + "{:d}:{:02d}".format(t.hour, t.minute))
			send_crypto_mail.send_invest_mail(from_exchange_tools.trader.exchangeName, coin)
			code = self.sell_cross_exchange(to_exchange_tools, coin)
		return code

	def buy_cross_exchange(self, from_exchange_tools, to_exchange_tools, coin, amount_coin, fun_critera):
		logger.info('buy_cross_exchange(). Exchange: {:}\tCoin: {:}'.format(from_exchange_tools.trader.exchangeName, coin))
		print('Starting buy_cross_exchange()')
		amount_coin = Decimal(amount_coin)
		trader = from_exchange_tools.trader
		if from_exchange_tools.trader.exchangeName == 'gdax':
			eur_balance = trader.get_coin_balance('EUR')
			get_cross_coin_amount = lambda price, curr: (eur_balance/price).quantize(Decimal('.00000001'), rounding=ROUND_DOWN)
		else:
			get_cross_coin_amount = lambda x, y: amount_coin

		# Add limit order
		self.buy_limit_order(from_exchange_tools, coin, 'EUR', get_cross_coin_amount, fun_critera, coin, from_exchange_tools, to_exchange_tools)

		# Check coin balance
		coin_balance = trader.get_coin_balance(coin)
		if not from_exchange_tools.valid_order_size(coin, coin_balance):
			print('No coins were bought. Exiting program')
			return 2

		# Check if bought amount was enough
		remaining_amount = Decimal('0.0')
		if coin_balance < amount_coin*Decimal('0.9') and from_exchange_tools.trader.exchangeName == 'kraken':
			remaining_amount = amount_coin - coin_balance
		elif coin == 'ETH' and coin_balance < Decimal('0.05'):
			remaining_amount = Decimal('0.05') - coin_balance
		elif coin_balance < to_exchange_tools.valid_order_size(coin, coin_balance):
			remaining_amount = to_exchange_tools.trader.min_order_size[coin] - coin_balance

		if remaining_amount != Decimal('0.0'):
			print('Some of the order was filled. Buying the rest for market and sending to other exchange')
			if not from_exchange_tools.valid_order_size(coin, remaining_amount): remaining_amount = trader.min_order_size[coin]
			data = trader.add_buy_order(coin, 'EUR', amount=remaining_amount, order_type='market')

		# Withdraw to other exchange
		time.sleep(2)
		coin_balance = trader.get_coin_balance(coin)
		trader.withdraw_crypto(coin, coin_balance)
		
		# Checking if withdrawal went through
		time.sleep(3)
		coin_balance = trader.get_coin_balance(coin)
		if not from_exchange_tools.valid_order_size(coin, coin_balance):
			print('buy_cross_exchange() finished successfully')
			return 1
		print('Some coins still on exchange!')
		print(coin_balance)
		return 3

	def sell_cross_exchange(self, to_exchange_tools, coin):
		logger.info('sell_cross_exchange(). Exchange: {:}\tCoin: {:}'.format(to_exchange_tools.trader.exchangeName, coin))
		trader = to_exchange_tools.trader
		print('Starting sell_cross_exchange()')
	
		# Check for received coins
		print('Checking for received coins')
		coin_balance = trader.get_coin_balance(coin)
		while not to_exchange_tools.valid_order_size(coin, coin_balance):
			time.sleep(10)
			coin_balance = trader.get_coin_balance(coin)
		
		print('Coins received in ' + trader.exchangeName + ': ' + str(coin_balance))

		# Sell market/limit
		start_ask_price = to_exchange_tools.low_limit_sell_price(coin, currency='EUR')
		fun_criteria = lambda x: True if (x/start_ask_price) > 0.999 else False
		self.sell_limit_order(to_exchange_tools, coin, 'EUR', fun_criteria)

		coin_balance = trader.get_coin_balance(coin)
		if to_exchange_tools.valid_order_size(coin, coin_balance):
			trader.add_sell_order(coin, 'EUR', amount=coin_balance, order_type='market')

		# Check that no coins are left on exchange
		time.sleep(2)
		coin_balance = trader.get_coin_balance(coin)
		if not to_exchange_tools.valid_order_size(coin, coin_balance):
			print('Coins sold successfully.')
			return 1
		else:
			print('OPERATION FAILED! COINS STILL IN ACCOUNT: ' + str(coin_balance))
			return 3

