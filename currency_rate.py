from forex_python.converter import CurrencyRates
from datetime import datetime, timedelta

c = CurrencyRates()

USD_to_EUR = 0.0
EUR_to_USD = 0.0

prev_days_EUR_USD = 0.0

def update_days_diff():
	global prev_days_EUR_USD
	average_prev_days = 0.0
	days = 3
	for d in range(days):
		t = datetime.today() - timedelta(days=d+1)
		average_prev_days += c.get_rate("EUR", "USD", t)
	average_prev_days /= days
	rate_now = c.get_rate("EUR", "USD", datetime.today())
	prev_days_EUR_USD = (rate_now/average_prev_days - 1.0)*100

update_days_diff()

def update_rates():
	global USD_to_EUR
	global EUR_to_USD
	USD_to_EUR = c.get_rate('USD', 'EUR')
	EUR_to_USD = c.get_rate('EUR', 'USD')

update_rates()
