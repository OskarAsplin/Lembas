# rules

# ETH transfer fee from kraken = 0.005 ETH
# LTC transfer fee from kraken = 0.001 LTC
# ETH transfer fee from gdax = 0.0 ETH
# LTC transfer fee from gdax = 0.0 LTC

# Maker fee gdax = 0 %
# Taker fee gdax = 0.3 %
# Maker fee kraken = 0.16 %
# Taker fee kraken = 0.26 %

import currency_rate

invest_lim_kraken = {
	'ETH': 1.0,
	'LTC': 1.0
}

invest_lim_gdax = {
	'ETH': 0.4,
	'LTC': 0.55
}

buy_euro_kraken = {
	'ETH': 1000,
	'LTC': 400
}

buy_euro_gdax = {
	'ETH': 300,
	'LTC': 200,
	'BCH': 200
}

buy_internal_base_eur = 300

buy_internal = {
	'EUR': buy_internal_base_eur,
	'USD': buy_internal_base_eur
}

internal_invest_lim = {
	'to_EUR': 0.8,
	'to_USD': 0.8
}

buy_euro = {
	'kraken': buy_euro_kraken,
	'gdax': buy_euro_gdax
}

sell_euro = {
	'kraken': buy_euro_gdax,
	'gdax': buy_euro_kraken
}

invest_lim = {
	'kraken': invest_lim_kraken,
	'gdax': invest_lim_gdax
}

def update_buy_internal(eur_available, usd_available):
	global buy_internal
	global buy_internal_base_eur
	mrkt_fee = 1.0026
	if eur_available < buy_internal_base_eur*mrkt_fee:
		buy_internal['EUR'] = eur_available/mrkt_fee if eur_available > 100 else 0
	else:
		buy_internal['EUR'] = buy_internal_base_eur
	if usd_available < buy_internal_base_eur*mrkt_fee*currency_rate.EUR_to_USD:
		buy_internal['USD'] = usd_available/mrkt_fee if usd_available > 100 else 0
	else:
		buy_internal['USD'] = buy_internal_base_eur*currency_rate.EUR_to_USD
