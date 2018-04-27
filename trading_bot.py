import trading
import kraken_api
import gdax_api
import rules
import currency_rate
import send_crypto_mail
from decimal import *
import gdax
import requests
import time
from datetime import datetime, timedelta, timezone
import json
import traceback
import logging
logger = logging.getLogger(__name__)


class PriorData(object):
	def __init__(self):
		self.public_client = gdax.PublicClient()

	def get_1hr_change(self, coin):
		coin_stats_url = {'ETH': 'https://api.coinmarketcap.com/v1/ticker/ethereum/', 'LTC': 'https://api.coinmarketcap.com/v1/ticker/litecoin/'}
		while True:
			try:
				response = requests.get(coin_stats_url[coin])
				data = response.json()
				return float(data[0]['percent_change_1h'])
			except:
				time.sleep(1)
				continue

	def past_price_diff_gdax(self, coin, minutes):
		t = datetime.utcnow() - timedelta(minutes=minutes)
		t = t.replace(tzinfo=timezone.utc).isoformat()
		while True:
			try:
				data = self.public_client.get_product_trades(product_id= coin + '-EUR')
				for d in data:
					if d['time'] < t:
						return 100*(float(data[0]['price'])/float(d['price']) - 1.)
				return 100*(float(data[0]['price'])/float(data[-1]['price']) - 1.)
			except:
				print('Error retrieving price gdax')
				time.sleep(1)
				continue

	def past_price_diff_kraken(self, coin, minutes):
		t = time.time() - minutes * 60

		while True:
			try:
				parameters = {"pair": 'X' + coin + 'ZEUR'}
				response = requests.get("https://api.kraken.com/0/public/Trades", params=parameters)
				data = response.json()
				while data['error']:
					print(data['error'])
					time.sleep(1)
					response = requests.get("https://api.kraken.com/0/public/Trades", params=parameters)
					data = response.json()
				break
			except:
				print('Error retrieving price kraken')
				time.sleep(1)
				continue

		for d in reversed(data['result']['X' + coin + 'ZEUR']):
			if d[2] < t:
				return 100*(float(data['result']['X' + coin + 'ZEUR'][-1][0])/float(d[0]) - 1.)
		return 100*(float(data['result']['X' + coin + 'ZEUR'][-1][0])/float(data['result']['X' + coin + 'ZEUR'][0][0]) - 1.)


class InvestCritera(object):
	def __init__(self):
		self.prior = PriorData()
		self.past_price_diff = {
			'kraken': self.prior.past_price_diff_kraken,
			'gdax': self.prior.past_price_diff_gdax
		}

	def cross_market_buy_diff(self, coin, from_trader, to_trader):
		buy_price = float(from_trader.safe_market_buy_price(coin))
		sell_price = float(to_trader.safe_market_sell_price(coin))
		return [100*(sell_price/buy_price - 1.), buy_price]

	def cross_limit_buy_diff(self, coin, from_trader, to_trader):
		buy_price = float(from_trader.low_limit_buy_price(coin))
		sell_price = float(to_trader.safe_market_sell_price(coin))
		return [100*(sell_price/buy_price - 1.), buy_price]

	def cross_invest_criteria(self, coin, from_trader, to_trader):
		if self.prior.get_1hr_change(coin) > 0 and self.past_price_diff[from_trader.trader.exchangeName](coin, 4) >= 0:
			[diff, price] = self.cross_market_buy_diff(coin, from_trader, to_trader)
			print(coin + ' diff at ' + from_trader.trader.exchangeName + ': \t%2.2f' % (diff))
			if diff > rules.invest_lim[from_trader.trader.exchangeName][coin]:
				return [True, diff, float(price)]
		return [False, 0.0, 0.0]


	def internal_invest_criteria(self, trade_tools):
		# coins = ['XLM', 'XBT', 'XRP', 'XMR', 'EOS', 'ETH', 'BCH', 'GNO', 'ETC', 'LTC', 'REP', 'ZEC', 'DASH']
		coins = ['XBT', 'ETH', 'XRP', 'LTC', 'ETC', 'BCH', 'EOS', 'XMR', 'DASH', 'ZEC', 'XLM']

		to_EUR_lim = rules.internal_invest_lim['to_EUR'] + max(0, currency_rate.prev_days_EUR_USD)
		to_USD_lim = rules.internal_invest_lim['to_USD'] + max(0, -currency_rate.prev_days_EUR_USD)

		high_coin_to_USD = 'ETH'
		high_coin_to_EUR = 'ETH'
		diff_to_usd = -50.
		diff_to_eur = -50.
		for coin in coins:
			if rules.buy_internal['EUR'] > 1:
				eur_to_usd = trade_tools.internal_limit_buy_diff(coin, b_currency='EUR', s_currency='USD')[1]
				if eur_to_usd > diff_to_usd:
					diff_to_usd = eur_to_usd
					high_coin_to_USD = coin
				if diff_to_usd > to_USD_lim: return ['to_USD', diff_to_usd, high_coin_to_USD]
			
			if rules.buy_internal['USD'] > 1:
				usd_to_eur = trade_tools.internal_limit_buy_diff(coin, b_currency='USD', s_currency='EUR')[1]
				if usd_to_eur > diff_to_eur:
					diff_to_eur = usd_to_eur
					high_coin_to_EUR = coin
				if diff_to_eur > to_EUR_lim: return ['to_EUR', diff_to_eur, high_coin_to_EUR]
			time.sleep(0.5)

		print('To EUR: {:.2f}\tTo USD: {:.2f}'.format(diff_to_eur, diff_to_usd))
		return ['NO_TRADE', max(diff_to_eur, diff_to_usd), 'XXX']


class TradingBot(object):
	def __init__(self, interval=60, internal_trading=False, cross_exchange_trading=False):
		self.internal_trading = internal_trading
		self.cross_exchange_trading = cross_exchange_trading
		currency_rate.update_rates()
		currency_rate.update_days_diff()
		k_trader = kraken_api.KrakenTrader()
		g_trader = gdax_api.GDAXTrader()
		self.kraken_trade_tools = trading.TradeTools(k_trader)
		self.gdax_trade_tools = trading.TradeTools(g_trader)
		self.criteria_check = InvestCritera()
		self.trade_machine = trading.TradeLogic()

		self.euro_kraken = self.kraken_trade_tools.trader.get_currency_balance('EUR')
		self.usd_kraken = self.kraken_trade_tools.trader.get_currency_balance('USD')
		self.euro_gdax = self.gdax_trade_tools.trader.get_currency_balance('EUR')
		self.start_euro = self.euro_gdax + self.euro_kraken + currency_rate.USD_to_EUR * self.usd_kraken
		self.deal_in_progress = False
		self.interval = interval

		rules.update_buy_internal(eur_available=self.euro_kraken, usd_available=self.usd_kraken)

	def run(self):
		logger.info('Starting with Euros: {:.2f}\tKraken {:.2f}\tGDAX: {:.2f}\tDollars:\tKraken: {:.2f}'.format(self.start_euro, 
			self.euro_kraken, self.euro_gdax, self.usd_kraken))
		print('Starting with Euros: {:.2f}\tKraken {:.2f}\tGDAX: {:.2f}\tDollars:\tKraken: {:.2f}'.format(self.start_euro, 
			self.euro_kraken, self.euro_gdax, self.usd_kraken))
		t = datetime.time(datetime.now())
		logger.info('Trading bot alive. ' + '\tTime: ' + "{:d}:{:02d}".format(t.hour, t.minute))
		code = 0
		i = 0
		try:
			while True:
				i += 1
				t = datetime.time(datetime.now())
				print('Trading bot alive. ' + '\tTime: ' + "{:d}:{:02d}".format(t.hour, t.minute) + '\t\tPress ctrl + c to stop')

				if i > 0 and (i*self.interval) % (360*60) == 0:
					send_crypto_mail.send_alive_mail()

				if i > 0 and (i*self.interval) % (60*60) == 0:
					logger.info('Trading bot alive. ' + '\tTime: ' + "{:d}:{:02d}".format(t.hour, t.minute))
					rate_before = currency_rate.USD_to_EUR
					currency_rate.update_rates()
					currency_rate.update_days_diff()
					if rate_before != currency_rate.USD_to_EUR:
						change = (currency_rate.USD_to_EUR - rate_before) * self.usd_kraken
						logger.info('Currency rate change loss/profit: {:.2f}\tNew USD_to_EUR rate: {:}'.format(change, currency_rate.USD_to_EUR))
				
				if self.cross_exchange_trading:
					coins = ['ETH', 'LTC']
					for coin in coins:
						# ---------------- Kraken -------------------------
						if self.euro_kraken > (rules.buy_euro_kraken[coin] + 50):
							[trade, _, price] = self.criteria_check.cross_invest_criteria(coin, from_trader=self.kraken_trade_tools, to_trader=self.gdax_trade_tools)
							if trade:
								self.deal_in_progress = True
								amount = rules.buy_euro_kraken[coin]/price
								logger.info('Attempting cross exchange trade from Kraken. Coin: {:}\tAmount: {:.6f}\tPrice: {:.2f}'.format(coin, amount, price))
								code = self.trade_machine.cross_exchange_trade(from_exchange_tools=self.kraken_trade_tools, to_exchange_tools=self.gdax_trade_tools, 
									coin=coin, amount_coin=amount, fun_critera=self.criteria_check.cross_invest_criteria)
							if code != 0:
								break

						# ---------------- GDAX ---------------------------
						if self.euro_gdax > (rules.buy_euro_gdax[coin] + 50):
							[trade, _, price] = self.criteria_check.cross_invest_criteria(coin, from_trader=self.gdax_trade_tools, to_trader=self.kraken_trade_tools)
							if trade:
								self.deal_in_progress = True
								amount = rules.buy_euro_gdax[coin]/price
								logger.info('Attempting cross exchange trade from GDAX. Coin: {:}\tAmount: {:6f}\tPrice: {:.2f}'.format(coin, amount, price))
								code = self.trade_machine.cross_exchange_trade(from_exchange_tools=self.gdax_trade_tools, to_exchange_tools=self.kraken_trade_tools, 
									coin=coin, amount_coin=amount, fun_critera=self.criteria_check.cross_invest_criteria)
							if code != 0:
								break

				if self.internal_trading:
					# Internal trading on Kraken ---------------------------------------------
					if code == 0:
						[trade, diff, coin] = self.criteria_check.internal_invest_criteria(self.kraken_trade_tools)
						print('{:}: {:.2f}\t coin: {:}'.format(trade, diff, coin))
						if trade == 'to_EUR' or trade == 'to_USD':
							b_curr = 'USD' if trade == 'to_EUR' else 'EUR'
							s_curr = 'EUR' if trade == 'to_EUR' else 'USD'
							[trade, diff, price] = self.kraken_trade_tools.internal_limit_buy_diff(coin, b_currency=b_curr, s_currency=s_curr)
							print('Double check trade:{:}, diff: {:.2f}'.format(trade, diff))
							if trade:
								logger.info('Attempting internal trade. Coin: {:}\tB_currency: {:}\tS_currency: {:}'.format(coin, b_curr, s_curr))
								self.deal_in_progress = True
								code = self.trade_machine.internal_trade(self.kraken_trade_tools, coin, b_currency=b_curr, s_currency=s_curr)

				# ---------------- Test if all is well after a trade ---------------------
				# code:
				# 0 - No attempted trades
				# 1 - Succesful trade
				# 2 - Trade aborted but no coins on exchanges
				# 3 - Trade failed
				if code == 1:
					print('Succesful trade.')
				elif code == 2:
					print('Trade aborted, but no coins on excanges. All is well.')
				elif code == 3:
					print('Coins bought and still on exchange. Trading bot is dead.')
					logger.warning('Coins bought and still on exchange. Trading bot is dead.')
					send_crypto_mail.send_critical_error_mail()
					break

				if self.deal_in_progress:
					self.deal_in_progress = False
					euros_before_trade = self.euro_gdax + self.euro_kraken + currency_rate.USD_to_EUR * self.usd_kraken
					self.euro_kraken = self.kraken_trade_tools.trader.get_currency_balance('EUR')
					self.usd_kraken = self.kraken_trade_tools.trader.get_currency_balance('USD')
					self.euro_gdax = self.gdax_trade_tools.trader.get_currency_balance('EUR')
					euros_now = self.euro_gdax + self.euro_kraken + currency_rate.USD_to_EUR * self.usd_kraken
					last_trade_profit = euros_now - euros_before_trade
					profit = euros_now - self.start_euro
					rules.update_buy_internal(eur_available=self.euro_kraken, usd_available=self.usd_kraken)
					if code == 1:
						logger.info('Available currencies after trade:\tEuro GDAX: {:.2f}\tEuro Kraken: {:.2f}\tUSD Kraken: {:.2f}'.format(self.euro_gdax, self.euro_kraken, self.usd_kraken))
						t = datetime.time(datetime.now())
						logger.info('Trade completed at {:d}:{:02d}. Profit this trade:{:.2f}\tProfit so far: {:.2f}\tTotal Euros: {:.2f}'.format(t.hour, t.minute, last_trade_profit, profit, euros_now))
						print('Profit this trade:{:.2f}\tProfit so far: {:.2f}\tTotal Euros: {:.2f}'.format(last_trade_profit, profit, euros_now))
						send_crypto_mail.send_success_mail(last_trade_profit, profit)
					if profit < - 25.0:
						print('Too many losses for today. Trading bot is dead')
						send_crypto_mail.send_cut_losses_mail()
						break

				code = 0
				time.sleep(self.interval)

		except Exception as e:
			logger.error(traceback.format_exc())
			print('Exiting program and sending quit trading mail')
			send_crypto_mail.send_quit_trading_mail()
