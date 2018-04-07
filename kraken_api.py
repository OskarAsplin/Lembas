import logging
logger = logging.getLogger(__name__)
import krakenex
import kraken_config
from decimal import *
import time


class KrakenTrader(object):
	def __init__(self):
		self.exchangeName = 'kraken'
		self.k = krakenex.API(key=kraken_config.key, secret=kraken_config.sign)
		self.Xcoins = set(['XLM', 'XBT', 'XRP', 'XMR', 'ETH', 'ETC', 'LTC', 'REP', 'ZEC'])
		self.decimals_price = {
			'XBT': 1,
			'ETH': 2,
			'XRP': 5,
			'LTC': 2,
			'ETC': 3,
			'BCH': 1,
			'EOS': 4,
			'XMR': 2,
			'XRP': 3,
			'ZEC': 2,
			'XLM': 6,
			'DASH': 2
		}
		self.min_order_size = {
			'XBT': Decimal('0.002'),
			'ETH': Decimal('0.02'),
			'XRP': Decimal('30.0'),
			'LTC': Decimal('0.1'),
			'ETC': Decimal('0.3'),
			'BCH': Decimal('0.002'),
			'EOS': Decimal('3.0'),
			'XMR': Decimal('0.1'),
			'XRP': Decimal('30.0'),
			'ZEC': Decimal('0.03'),
			'XLM': Decimal('30.0'),
			'DASH': Decimal('0.03')
		}
		self.api_calls={
			'Depth': self.k.query_public,
			# 'AssetPairs': self.k.query_public,
			'Balance': self.k.query_private,
			'AddOrder': self.k.query_private,
			'OpenOrders': self.k.query_private,
			'CancelOrder': self.k.query_private,
			'Withdraw': self.k.query_private,
		}
		self.active_order_id = '000'

	def run_api_call(self, name, parameters = None):
		while True:
			try:
				data = self.api_calls[name](name, parameters)	
				if data['error']:
					print(data['error'])
					if data['error'] == ['EOrder:Unknown order']:
						return data
					if data['error'] == ['EAPI:Rate limit exceeded']:
						logger.info('EAPI:Rate limit exceeded at Kraken. Waiting 16 minutes.')
						time.sleep(60*16)
					time.sleep(1)
					continue
				return data
			except:
				logger.info('run_api_call() failed at Kraken: {:}'.format(name))
				print('api call failed: ' + name)
				time.sleep(1)
				continue

	def convert_kraken_standard(self, coin, currency='EUR'):
		if coin in self.Xcoins: return ['X'+coin, 'Z'+currency]
		return [coin, currency]

	def get_string_pres(self, coin):
		dec = self.decimals_price[coin]
		dec_place = Decimal('1E-'+str(dec))
		return "%." + str(dec) + "f"

	def get_open_orders(self):
		data = self.run_api_call('OpenOrders')
		if data['result']['open']: self.active_order_id = list(data['result']['open'].keys())[0]
		return data['result']['open']

	def get_coin_balance(self, coin):
		coin = self.convert_kraken_standard(coin)[0]
		data = self.run_api_call('Balance')
		if coin in data['result']:
			return Decimal(data['result'][coin])
		else:
			return Decimal('0.0')

	def get_currency_balance(self, curr):
		data = self.run_api_call('Balance')
		return float(data['result']['Z' + curr])

	def get_order_book(self, coin, currency, count='5', level=1):
		[coin, currency] = self.convert_kraken_standard(coin, currency)
		parameters = {'pair': coin + currency, 'count': count}
		data = self.run_api_call('Depth', parameters)
		bids = data['result'][coin + currency]['bids']
		asks = data['result'][coin + currency]['asks']
		return [bids, asks]

	def withdraw_crypto(self, coin, amount):
		[coin, currency] = self.convert_kraken_standard(coin)
		parameters = {'asset': coin, 'key': kraken_config.gdax_address[coin], 'amount': str("%.8f" % amount)}
		data = run_api_call('Withdraw', parameters)
		if data['error']:
			return True
		return False

	def add_buy_order(self, coin, currency, amount, order_type, price=0.0):
		str_pres = self.get_string_pres(coin)
		[coin, currency] = self.convert_kraken_standard(coin, currency)
		if order_type == 'limit':
			parameters = {'pair': coin + currency, 'type': 'buy', 'ordertype': order_type, 'price': str(str_pres % price), 'volume': str("%.6f" % amount), 'oflags': 'post'}
		elif order_type == 'market':
			parameters = {'pair': coin + currency, 'type': 'buy', 'ordertype': order_type, 'volume': str("%.6f" % amount)}
		data = self.run_api_call('AddOrder', parameters)
		self.active_order_id = data['result']['txid'][0]
		print(data)
		return data

	def add_sell_order(self, coin, currency, amount, order_type, price=0.0):
		str_pres = self.get_string_pres(coin)
		[coin, currency] = self.convert_kraken_standard(coin, currency)
		if order_type == 'limit':
			parameters = {'pair': coin + currency, 'type': 'sell', 'ordertype': order_type, 'price': str(str_pres % price), 'volume': str("%.8f" % amount), 'oflags': 'post'}
		elif order_type == 'market':
			parameters = {'pair': coin + currency, 'type': 'sell', 'ordertype': order_type, 'volume': str("%.8f" % amount)}
		data = self.run_api_call('AddOrder', parameters)
		self.active_order_id = data['result']['txid'][0]
		print(data)
		return data

	def cancel_order(self):
		parameters = {'txid': self.active_order_id}
		self.run_api_call('CancelOrder', parameters)


