# -*- coding: utf-8 -*-
from bs4 import BeautifulSoup
from urllib.request import urlopen #http://stackoverflow.com/questions/2792650/python3-error-import-error-no-module-name-urllib2#2792652
import feedparser
from telegraphapi import Telegraph
import telegram
from telegram import *
from mtranslate import translate
import time
import os
from gtts import gTTS
import re
import sqlite3
import schedule
import datetime

telegraph = Telegraph()
telegraph.createAccount("PythonTelegraphAPI")
TOKEN_TELEGRAM = '358045589:AAH-Bzm42xxEAeGZRLwDPsmQTSNZMKqBBrU' #DeutschFormel1Bot
TOKEN_TELEGRAM_ALERT = '391000492:AAGRaDrCno6nZ67TzGxpoKd5QkqVlidFG38'
MY_ITALIAN_READING_PER_MINUTE = 235
DATABASE_NAME = 'Formel1.db'
bot = telegram.Bot(TOKEN_TELEGRAM)
botALERT = telegram.Bot(TOKEN_TELEGRAM_ALERT)
chat_id_List = []
allUrl = []
allRssFeed = []

try:
    update_id = bot.getUpdates()[0].update_id
except IndexError:
    update_id = None

def init_DB():
	conn = sqlite3.connect( DATABASE_NAME ) 
	cursor = conn.cursor()
	cursor.execute("""CREATE TABLE IF NOT EXISTS url (url text primary key) """)           
	cursor.execute("""CREATE TABLE IF NOT EXISTS feed (url text primary key) """)
	cursor.execute("""CREATE TABLE IF NOT EXISTS users (chat_id int primary key, name text, time_added text) """)
	conn.commit()
	conn.close()

def insert_RSS_Feed_DB():
	conn = sqlite3.connect( DATABASE_NAME ) 
	cursor = conn.cursor()
	
	url = ('http://www.motorsport-total.com/rss_f1.xml',)
	cursor.execute("INSERT OR IGNORE INTO feed VALUES (?)",url)
	
	#url = ('http://www.motorsport-total.com/rss_formelsport_FE.xml',)
	#cursor.execute("INSERT OR IGNORE INTO feed VALUES (?)",url)
	
	#url = ('http://www.motorsport-total.com/rss_usracing_IndyCar.xml',)
	#cursor.execute("INSERT OR IGNORE INTO feed VALUES (?)",url)
	
	url = ('http://www.motorsport-total.com/rss_motorrad_MGP.xml',)
	cursor.execute("INSERT OR IGNORE INTO feed VALUES (?)",url)
	
	#url = ('http://www.motorsport-total.com/rss_motorrad_MGP.xml',)
	#cursor.execute("INSERT OR IGNORE INTO feed VALUES (?)",url)
	
	conn.commit()
	conn.close()

def load_RSS_Feed_DB():
	global allRssFeed
	conn = sqlite3.connect( DATABASE_NAME ) 
	cursor = conn.cursor()
	cursor.execute("""SELECT * FROM feed """)
	conn.commit()
	allRssFeed = cursor.fetchall()
	conn.close()
	
def get_nth_article():
	conn = sqlite3.connect( DATABASE_NAME ) 
	cursor = conn.cursor()
	cursor.execute("""SELECT * FROM url """)
	conn.commit()
	allUrl = list( cursor.fetchall() )
	print("aieie")
	print(allRssFeed)
	print("aieie")
	for feed in allRssFeed:
		print("aieie")
		print(feed)
		print("aieie")
		print("aieie")
		print(feed[0])
		print("aieie")
		entries = feedparser.parse(  feed[0]  ).entries
		for i in reversed( range(10) ):
			try:
				url = entries[i].link
			except:
				#print("Error while parsing " + feed)
				continue
			if  url not in [item[0] for item in allUrl]:
				url_DB = (url,)
				cursor.execute("INSERT OR IGNORE INTO url VALUES (?)", url_DB)
				conn.commit()
				html = urlopen( url ).read()
				bsObj = BeautifulSoup( html, "html.parser" )

				articleImage = bsObj.findAll("meta",{"property":"og:image"})[0].attrs["content"]
				articleTitle = bsObj.findAll("meta",{"property":"og:title"})[0].attrs["content"]
				articleUrl = bsObj.findAll("meta",{"property":"og:url"})[0].attrs["content"]
				articleContent = bsObj.findAll("div",{"class":"newstext"})[0]
				try:
					boldArticleContent = articleContent.findAll("h2",{"class":"news"})[0].get_text()
				except IndexError:
					boldArticleContent = ""
				[section.extract() for section in articleContent.findAll('section')]
				[span.extract() for span in articleContent.findAll('span')]
				[script.extract() for script in articleContent.findAll('script')]
				[noscript.extract() for noscript in articleContent.findAll('noscript')]
				[iframe.extract() for iframe in articleContent.findAll('iframe')]
				[blockquote.extract() for blockquote in articleContent.findAll('blockquote')]
				string = ""
				for p in articleContent.findAll("p"):
					paragraph = p.get_text()
					string = string + paragraph + "\n"
					
				string = string.replace("(Motorsport-Total.com) - ","")
				articleTitle = articleTitle.replace("- Motorrad bei Motorsport-Total.com","")
				articleTitle = articleTitle.replace("- WEC bei Motorsport-Total.com","")
				articleTitle = articleTitle.replace("- DTM bei Motorsport-Total.com","")
				articleTitle = articleTitle.replace("- WTCC bei Motorsport-Total.com","")
				articleTitle = articleTitle.replace("- Oldtimer bei Motorsport-Total.com","")
				
				articleTitle = articleTitle.replace("- Motorrad bei Motorsport-Total.com","")
				articleTitle = articleTitle.replace("- Rallye bei Motorsport-Total.com","")
				articleTitle = articleTitle.replace("- Formelsport bei Motorsport-Total.com","")
				
				articleTitle = articleTitle.replace("- US-Racing bei Motorsport-Total.com","")
				articleTitle = articleTitle.replace("- Mehr Motorsport bei Motorsport-Total.com","")
				sendTelegraph( articleImage, articleTitle, boldArticleContent, articleUrl, string, feed[0] )
			else:
				pass
				#print("Found no new link.")
	conn.close()
		
def load_chat_id():
	global chat_id_List
	conn = sqlite3.connect( DATABASE_NAME ) 
	cursor = conn.cursor()
	cursor.execute("""SELECT * FROM users """)
	conn.commit()
	chat_id_List = [item[0] for item in cursor.fetchall()]
	conn.close()
	
def getTimeReadingString( words ):
	lung = len(words)
	minutes = len(words) / MY_ITALIAN_READING_PER_MINUTE
	if minutes == 0:
		return str(lung) + " parole.\n~1 min."
	timeReading = str(lung) + " parole.\n~" + str( int(minutes) )  + " min, " + str( round( (minutes-int(minutes) ) * 60 ) ) + " sec"
	return timeReading

def sendTelegraph( articleImage, articleTitle, boldArticleContent, articleUrl, string ,feed ):
	html_content = ""
	boldArticleContent = boldArticleContent + "."
	articleTitle = articleTitle
	stringAll = ""
	string = string.replace("ANZEIGE","")
	string = string.replace(u'\xa0', u'')
	string = re.sub('\t+', '', string)
	string = re.sub('\t+ ', '', string)
	string = re.sub('\n +\n+ ', '\n', string)
	string = re.sub('<[^<]+?>', '', string)
	string = re.sub('\n+','\n', string).strip().replace(">","")
	string = re.sub('\n +\n', '\n', string)
	
	words = ''.join(c if c.isalnum() else ' ' for c in articleTitle + boldArticleContent + string).split() #http://stackoverflow.com/questions/17507876/trying-to-count-words-in-a-string
	timeReading = getTimeReadingString( words )
	stringToBetranslated = articleTitle + ". " + boldArticleContent + " " + string
	
	imageLink = "<a href=\"" + articleImage + "\" target=\"_blank\"><img src=\"" + articleImage + "\"></img></a><a href=\"" + articleUrl + "\" target=\"_blank\">LINK</a>\n" 
	try:
		html_content = "<h4><b>" + articleTitle + "</b>" + imageLink + "</h4>" + "<b>" + boldArticleContent + "</b>\n" + "<a href=\"" + articleUrl + "\">LINK</a>\n\n" + string + "\n\n\n" + stringTranslated 
	except:
		pass
	stringList = re.split(r"(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?)\s", stringToBetranslated)
	for paragraph in stringList:
		try:
			html_content = html_content +  "<strong>" + paragraph + "</strong>" + "\n<i>" + translate( paragraph, "en","de" ) + "</i>" + "\n\n"
		except:
			pass
	html_content = imageLink + html_content
	page = telegraph.createPage( title = articleTitle,  html_content= html_content, author_name="f126ck" )
	url2send = 'http://telegra.ph/' + page['path']
	catIntro = getCategoryIntro( feed )
	
	for chat_id in chat_id_List:
		#print("sending to chat_id: " + str(chat_id))
		try:
			bot.sendMessage(parse_mode = "Html", text =  "<a href=\"" + url2send + "\">" + catIntro + "</a>" +  "<b>" + articleTitle + "</b>" + "\n"  + timeReading, chat_id = chat_id)
		except:
			pass
			#print("1 message was not sent to recipient" )

def getCategoryIntro( feed ):
	category = ""
	if "GP2" in feed.upper():
		category = "GP2"
	if "WEC" in feed.upper():
		category = "WEC"
	if "F1" in feed.upper():
		category = "F1"
	if "MGP" in feed.upper():
		category = "MOTOGP"
	if "FORMELSPORT_FE" in feed.upper():
		category = "FORMULA E"
	if "INDYCAR" in feed.upper():
		category = "INDYCAR"
	if category != "":
		return "[" + category + "]" + "\n"
	else:
		return "LINK"

def get_new_Users():
	global update_id
	for update in bot.getUpdates(offset=update_id, timeout=10):
		try:
			chat_id = update.message.chat_id
		except:
			pass
			#print("error get_new_users")
		update_id = update.update_id + 1
		try:
			if update.message.chat_id:  # your bot can receive updates without messages
				if chat_id not in chat_id_List:
					#print( bot.getMe().name )
					#print(dir(bot.getMe()))
					now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
					textTGNewUser = 'New user subscribed to ' + bot.getMe().name + '\nFirst name: ' + update.message.from_user.first_name + '\nLast name: ' + update.message.from_user.last_name + '\n' + 'Chat_id: ' + str(chat_id) + '\nTime added: ' + now 
					botALERT.sendMessage(chat_id = 31923577, text = textTGNewUser)
					conn = sqlite3.connect( DATABASE_NAME ) 
					cursor = conn.cursor()
					url = chat_id
					
					username = update.message.from_user.first_name + " " + update.message.from_user.last_name
					#print(username)
					cursor.execute( "INSERT OR IGNORE INTO users VALUES (?,?,?)", (chat_id, username, now) )
					conn.commit()
					conn.close()			
		except Exception as e:
			#print("error getUpdates " , e)
			pass
	bot.getUpdates(offset=update_id,timeout=0)

def load_User_Me():
	
	conn = sqlite3.connect( DATABASE_NAME ) 
	cursor = conn.cursor()
	chat_id = (31923577,)
	cursor.execute("INSERT OR IGNORE INTO users VALUES (?,?,?)",(31923577,"me","") )
	conn.commit()
	conn.close()
	
def main():
	init_DB()
	insert_RSS_Feed_DB()
	load_RSS_Feed_DB()
	load_User_Me()
	load_chat_id()
	#print(chat_id_List)
	schedule.every(10).seconds.do( get_nth_article )
	get_nth_article()
	while True:
		try:
			get_new_Users()
			#get_nth_article
			schedule.run_pending()
		except NetworkError:
			#print("ADSL")
			time.sleep(10)
		except Unauthorized:
			update_id += 1
			
main()
