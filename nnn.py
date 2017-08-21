# -*- coding: utf-8 -*-
from newspaper import Article
import feedparser
from telegraphapi import Telegraph
import telegram
from telegram.error import *
from mtranslate import translate
import time
import re
import sqlite3
import schedule
import datetime
import os
import threading
import traceback
import postgresql

telegraph = Telegraph()
telegraph.createAccount("PythonTelegraphAPI")
TOKEN_TELEGRAM = '358045589:AAH-Bzm42xxEAeGZRLwDPsmQTSNZMKqBBrU' #DeutschFormel1Bot
MY_ITALIAN_READING_PER_MINUTE = 235
DATABASE_NAME = 'Formel1.db'
bot = telegram.Bot(TOKEN_TELEGRAM)
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
	url = ('http://www.motorsport-total.com/rss_motorrad_MGP.xml',)
	cursor.execute("INSERT OR IGNORE INTO feed VALUES (?)",url)
	conn.commit()
	conn.close()

def load_RSS_Feed_DB():
	global allRssFeed
	conn = sqlite3.connect( DATABASE_NAME ) 
	cursor = conn.cursor()
	cursor.execute("""SELECT * FROM feed """)
	conn.commit()
	allRssFeed = [item[0] for item in cursor.fetchall()]
	conn.close()
	
def get_nth_article():
	conn = sqlite3.connect( DATABASE_NAME ) 
	cursor = conn.cursor()
	cursor.execute("""SELECT * FROM url """)
	conn.commit()
	allUrl = [item[0] for item in cursor.fetchall()]
	for feed in allRssFeed:
		print("parsing entries")
		print(feed)
		entries = feedparser.parse( feed ).entries
		for i in reversed( range(10) ):
			try:
				url = entries[i].link
				#print("\t" + url )
			except Exception as e:
				print("excp1", e)
				continue
			if  url not in allUrl:
				try:
					url1 = (url,)
					cursor.execute("INSERT OR IGNORE INTO url VALUES (?)", url1 )
					conn.commit()
				except Exception as e:
					print("excp1", e)
				article = Article(url)
				article.download()
				article.parse()
				
				text = article.text
				articleImage = article.top_image
				articleTitle = article.title
				#print( article.url)
				articleUrl = article.url
				string = text
				string = re.sub( r"Zoom © .*[\n]*\(Motorsport-Total\.com\)" , "" , string) # elimina
				string = re.sub( r"[0-9]+\. [A-Za-z]+ [0-9]+ - [0-9]+:[0-9]+ Uhr", "", string ) # elimina data
				boldArticleContent = ""
				######
				#MULTITHREADING
				######
				multithreading = 1
				if multithreading:
					threading.Thread(target=sendTelegraph, args=(articleImage, articleTitle, boldArticleContent, articleUrl, string, feed)).start()
				else:
					sendTelegraph( articleImage, articleTitle, boldArticleContent, articleUrl, string, feed )
				
				
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
	boldArticleContent = boldArticleContent #+ "."
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
	imageLink = '<a href="{}" target="_blank"><img src="{}"></img></a><a href="{}" target="_blank">LINK</a>\n\n'.format(articleImage,articleImage,articleUrl)
	
	try:
		#html_content = "<h4><b>" + articleTitle + "</b>" + imageLink + "</h4>" + "<b>" + boldArticleContent + "</b>\n" + "<a href=\"" + articleUrl + "\">LINK</a>\n\n" + string + "\n\n\n" + stringTranslated 
		html_content = '<h4><b>{}</b>{}</h4><b>{}</b>\n<a href="{}">LINK</a>\n\n{}\n\n\n{}'.format(articleTitle,imageLink,boldArticleContent,articleUrl,string,stringTranslated)

	except:
		pass
	stringList = re.split(r"(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?)\s", stringToBetranslated)
	TOKEN_TRANSLATE = ' 9992362973473279238732489 ' # token che serve per dividere i paragrafi e correttamente associarli ad ogni sua traduzione... non 
	                                                # basta mettere il punto perchè a volte viene tradotto ... con una virgola! 
	                                                # NB spazio numero casuale spazio
	                                                # se non c'è spazio non traduce prima parola (giustamente)
	stringToTranslate = TOKEN_TRANSLATE.join(stringList)
	stringBulkTranslated = translate( stringToTranslate, "en","de" )
	paragraphTranslated = stringBulkTranslated.split(TOKEN_TRANSLATE)
	i = 0
	#print(paragraphTranslated)
	for paragraph in stringList:
		try:
			html_content = html_content +  '<strong>{}</strong>\n<i>{}</i>\n\n'.format(paragraph,paragraphTranslated[i])
			i = i + 1
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
	schedule.every(10).seconds.do( get_nth_article )
	#start = time.time()
	get_nth_article()
	#end = time.time()
	#print(end - start)
	b
	while True:
		try:
			#pass
			schedule.run_pending()
		except NetworkError:
			time.sleep(10)
		except Unauthorized:
			update_id += 1
try:
	main()
except Exception as e:
	TOKEN_ALERT='440851070:AAGb1zdxKqYN-j6HAfQ1VE76SP6VrHvVbuI'
	botALERT = telegram.Bot(TOKEN_ALERT)
	text = "[!] Error:\n<b>{}:{}</b> in DeutschFormel1bot on function ".format( (type(e).__name__), e)
	botALERT.sendMessage(chat_id=31923577, text = text , parse_mode="Html")
