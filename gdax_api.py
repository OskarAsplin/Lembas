import logging
logger = logging.getLogger(__name__)
import gdax
import gdax_config
from decimal import *
import time


class GDAXTrader(object):
	def __init__(self):
		self.exchangeName = 'gdax'
		self.auth_client = gdax.AuthenticatedClient(gdax_config.key, gdax_config.b64secret, gdax_config.passphrase)
		self.public_client = gdax.PublicClient()
		self.decimals_price = {
			'ETH': 2,
			'LTC': 2,
			'BCH': 2
		}
		self.min_order_size = {
			'ETH': Decimal('0.01'),
			'LTC': Decimal('0.1'),
			'BCH': Decimal('0.01')
		}
		self.api_calls={
			'get_orders': self.auth_client.get_orders,
			'get_account': self.auth_client.get_account,
			'get_product_order_book': self.public_client.get_product_order_book,
			'get_product_historic_rates': self.public_client.get_product_historic_rates,
			'crypto_withdraw': self.auth_client.crypto_withdraw,
			'buy': self.auth_client.buy,
			'sell': self.auth_client.sell,
			'cancel_all': self.auth_client.cancel_all
		}

	def run_api_call(self, name, coin='LTC', price=0.0, amount_coin=0.0, trade_type='market', level=1, post_only=False, currency='EUR'):
		while True:
			try:
				if name == 'get_account':
					data = self.auth_client.get_account(gdax_config.account_id[coin])
				elif name == 'get_product_order_book':
					data = self.public_client.get_product_order_book(product_id=coin + '-' + currency, level=level)
					data['bids']
					data['asks']
				elif name == 'crypto_withdraw':
					data = self.auth_client.crypto_withdraw(amount=str(amount_coin), currency=coin, crypto_address=gdax_config.kraken_address[coin])
				elif name == 'buy':
					if post_only:
						data = self.auth_client.buy(price= str(price), size= str("%.8f" % amount_coin), product_id= coin + '-' + currency, type= trade_type, post_only= post_only)
					else:
						data = self.auth_client.buy(price= str(price), size= str("%.8f" % amount_coin), product_id= coin + '-' + currency, type= trade_type)
				elif name == 'sell':
					if post_only:
						data = self.auth_client.sell(price= str(price), size= str(amount_coin), product_id= coin + '-' + currency, type= trade_type, post_only= post_only)
					else:
						data = self.auth_client.sell(price= str(price), size= str(amount_coin), product_id= coin + '-' + currency, type= trade_type)
				elif name == 'get_product_trades':
					data = self.public_client.get_product_trades(product_id= coin + '-' + currency)
				else:
					data = self.api_calls[name]()
				return data
			except:
				logger.info('run_api_call() failed at GDAX: {:}'.format(name))
				print('api call failed: ' + name)
				print(coin)
				time.sleep(1)
				continue

	def get_string_pres(self, coin):
		dec = self.decimals_price[coin]
		dec_place = Decimal('1E-'+str(dec))
		return "%." + str(dec) + "f"

	def get_open_orders(self):
		data = self.run_api_call('get_orders')
		return data[0]

	def get_coin_balance(self, coin):
		data = self.run_api_call('get_account', coin=coin)
		return Decimal(data['available'])

	def get_currency_balance(self, currency):
		data = self.run_api_call('get_account', coin=currency)
		return float(data['available'])

	def get_order_book(self, coin, currency, count='5', level=1):
		data = self.run_api_call('get_product_order_book', coin=coin, level=level, currency=currency)
		return [data['bids'], data['asks']]

	def withdraw_crypto(self, coin, amount):
		data = self.run_api_call('crypto_withdraw', coin=coin, amount_coin=amount)
		print(data)
		return False

	def add_buy_order(self, coin, currency, amount, order_type, price=0.0):
		if order_type == 'limit':
			data = self.run_api_call('buy', coin=coin, price=price, amount_coin=amount, trade_type=order_type, post_only= True)
		elif order_type == 'market':
			data = self.run_api_call('buy', coin=coin, amount_coin=amount, trade_type=order_type)
		print(data)
		return data

	def add_sell_order(self, coin, currency, amount, order_type, price=0.0):
		if order_type == 'limit':
			data = self.run_api_call('sell', coin=coin, price=price, amount_coin=amount, trade_type=order_type, post_only= True)
		elif order_type == 'market':
			data = self.run_api_call('sell', coin=coin, amount_coin=amount, trade_type=order_type)
		print(data)
		return data

	def cancel_order(self):
		self.run_api_call('cancel_all')

