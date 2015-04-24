#Crawls data from the Alexa API

#This can be run as follows:
# python -c "import alexa;alexa.crawl()"

#It assumes that there's a folder called 'alexa_data' in the same directory

import requests
from codecs import open as copen
from os import listdir
from subprocess import call
from datetime import datetime
from xml.dom.minidom import parse
from xmltodict import parse as xmlparse
from json import dump

def get_data(domain):
	data = requests.get("http://data.alexa.com/data?cli=10&dat=snbamz&url=" + domain)
	if data.ok:
		return data.text
	else:
		return False

def save_data(domain, data):
	with copen('alexa_data/' + domain + '.txt', 'w', encoding='utf8') as f:
		f.write(data)

def precrawled_sites():
	"""Finds all sites that have already been crawled"""
	files = listdir("alexa_data/")
	files = [x.split(".txt")[0] for x in files]
	return files

def get_ranked_domains():
	"""Gets latest ranking file from alexa"""
	timestamp = datetime.strftime(datetime.now(), '%Y-%m-%d')
	filename = timestamp+"top-1m.csv"
	if filename not in listdir("ranking_files/"):
		location = 'http://s3.amazonaws.com/alexa-static/top-1m.csv.zip'
		call(['wget', location])
		call(['unzip', 'top-1m.csv.zip'])
		call(['mv', 'top-1m.csv', 'ranking_files/'+filename])
		call('rm', '-f', 'top-1m.csv.zip')
	domains = []
	with open('ranking_files/' + filename) as f:
		for line in f:
			domain = line[:-1].split(",")[1].lower()
			domains.append(domain)
	return domains

def crawl():
	"""Crawls the Alexa API for site data"""
	#get some domain data from the ranking file
	domains = get_ranked_domains()
	precrawled = precrawled_sites()
	#get data for each one
	for n, domain in enumerate(domains):
		if domain in precrawled:
			success = "Already Crawled"
		else:
			domain = domain.replace('/', '__')
			data = get_data(domain)
			if data:
				if 'click here to continue' not in data:
					save_data(domain, data)
					success = True
				else:
					print "Daily API limit reached"
					exit()
			else:
				success = False	
		print n, domain, success

def analyze_stuff():
	"""Outputs some interesting stats about data categorization"""
	please_click_here = []
	cats_slash = []
	slash_cats = []
	neither = []
	
	files = listdir("alexa_data")
	
	for fn in files:
		with open('alexa_data/' + fn) as f:
			f = f.read()
			if 'click here to continue' in f:
				please_click_here.append(fn)
			else:
				added = False
				if '<CATS/>' in f:
					cats_slash.append(fn)
					added = True
				if '</CATS>' in f:
					slash_cats.append(fn)
					added = True
				if not added:
					neither.append(fn)
	
	print "{0} files total in directory".format(len(files))
	print "{0} were retrieved successfully. {1} got the limit message".format(len(files)-len(please_click_here), len(please_click_here))
	print "{0} contain </CATS> i.e. some categories".format(len(slash_cats))
	print "{0} contain <CATS/> i.e. possibly no categories".format(len(cats_slash))
	print "{0} contain both </CATS> and <CATS/>".format(len([x for x in slash_cats if x in cats_slash]))
	print "{0} contain neither </CATS> nor <CATS/>".format(len(neither))

def create_json():
	"""Creates 2 gigantic json payloads from the xml data,
	one formatted nicely and one with no extra whitespace"""	
	result = {}
	for fn in listdir('alexa_data/'):
		with open('alexa_data/' + fn) as f:
			try:
				jdoc = xmlparse(f.read())
				result[fn.replace(".txt", "")] = jdoc
			except Exception:
				print fn
				
	with open('data_formatted.json', 'w') as f:
		dump(result, f)
	
	with open('data.json', 'w') as f:
		dump(result, f, indent=4, sort_keys=True)
