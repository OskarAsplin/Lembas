# coding=utf-8
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smtplib

def send_mail(subject, body):
	fromaddr = 'xxx-xxx-xxx-xxx-xxx@gmail.com'
	toaddrs  = 'xxx-xxx-xxx-xxx-xxx@gmail.com'

	msg = MIMEMultipart()
	msg['From'] = fromaddr
	msg['To'] = toaddrs
	msg['Subject'] = subject

	msg.attach(MIMEText(body, 'plain'))

	server = smtplib.SMTP('smtp.gmail.com', 587)
	server.starttls()
	server.login("xxx-xxx-xxx-xxx-xxx@gmail.com", "xxx-xxx-xxx-xxx-xxx")

	text = msg.as_string()
	server.sendmail(fromaddr, toaddrs, text)

	server.quit()

def send_invest_mail(exchange, coin):
	subject = 'Investing in ' + coin
	body = 'Coins bought on exchange: ' + exchange
	send_mail(subject, body)


def send_quit_trading_mail():
	subject = 'Some error occurred'
	body = 'Quiting bot'
	send_mail(subject, body)


def send_cut_losses_mail():
	subject = 'Aaaaaaaand it\'s gone!'
	body = 'Your money, it\'s all gone.'
	send_mail(subject, body)


def send_success_mail(last_trade, profit):
	if profit > 0.:
		subject = 'Trading so far has been successful'
		body = 'Profit this trade:{:.2f}\nProfit so far: {:.2f}'.format(last_trade, profit)
	else:
		subject = 'Mein Führer... Steiner...'
		body = 'Steiner hat dein Geld verloren:{:.2f}\nLast trade: {:.2f}'.format(profit, last_trade)
	send_mail(subject, body)


def send_critical_error_mail():
	subject = 'Trading failed in the middle of trade!'
	body = 'Coins still on exchange'
	send_mail(subject, body)


def send_alive_mail():
	subject = 'Trading bot still alive!'
	body = 'Everything is going according to plan'
	send_mail(subject, body)