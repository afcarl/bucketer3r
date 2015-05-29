#!/usr/bin/env python

#Initiates the mongoDB data
#Usage:
#python -c "import create_mongodb;create_mongodb.create()"

from os import listdir
from json import load as jload
from datetime import datetime
from collections import defaultdict

from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from xmltodict import parse as xmlparse

def convert_single_alexa_file(file_location):
	"""Converts an Alexa file into a dict and returns it"""
	with open('alexa_data/' + file_location) as f:
		try:
			f = xmlparse(f)
		except Exception:
			print "Could not parse: " + file_location
			return False
	return f

def import_comscore_data():
	"""Imports comscore rankings"""
	
	c = set_up_mongodb_connection()['bucketerer']
	
	#import Q4 2014
	with open('/Users/mruttley/Documents/2015-04-22 AdGroups/brendan/comscoreQ4FirefoxTraffic.csv') as f:
		for line in f.readlines()[1:]:
			if line.endswith('\n'):
				line = line[:-1]
			line = line.split(',')
			#parse the line
			domain = line[0].lower().replace('*','')
			data = {
				"rank": float(line[1]),
				"unique_visitors": float(line[2]),
				"reach": float(line[3]),
				"reach_index": float(line[4]),
				"visits": float(line[5]),
				"minutes": float(line[6]),
				"pages": float(line[7]),
				"visits_per_visitor": float(line[8]),
				"minutes_per_visitor": float(line[9]),
				"pages_per_visitor": float(line[10])
			}
			entry = c['domains'].find_one({'domain': domain.replace('.', '#')}, {'_id':1})
			if not entry:
				print "Could not find domain: {0}".format(domain)
			else:
				c['domains'].update({'_id':entry['_id']},
					{
						'$set': {
							'comscore': {
								'traffic': {
									'2015-Q4': data
								}
							}
						}
					})

def import_alexa_data(c):
	"""Processes all alexa data. Requires a connection, c"""

	for filename in listdir('alexa_data'):
		d = convert_single_alexa_file(filename)
		if d:
			url = d['ALEXA']['@URL']
			domain = url[:-1] if url.endswith('/') else url #remove trailing slash
			domain = domain.replace('.', '#')
			
			entry = c['bucketerer']['domains'].find_one({'domain':domain})
			
			if entry:
				if 'alexa' not in entry:
					c['bucketerer']['domains'].update({'_id': entry['_id']},
						{
							'$set': {
								'alexa': d["ALEXA"]
							}
						}
					)
			else:
				c['bucketerer']['domains'].insert(
					{
						'domain': domain,
						'alexa': d["ALEXA"]
					}
				)
	
def import_existing_buckets(c):
	"""Imports existing buckets from cats.json. Requires a mongodb connection as the first argument"""
	
	with open("external_data/cats.json") as f:
		buckets = jload(f)
	
	for bucket in buckets:
		c['bucketerer']['adgroups'].insert(
			{
				"name": bucket[1],
				"sites": bucket[0].split(","),
				"created_on": datetime.now(),
				"created_by": "Mardak"
			}
		)

def set_up_mongodb_connection():
	"""Sets up and returns a mongodb instance"""
	try:
		c = MongoClient()
		return c
	except ConnectionFailure:
		print "Please start mongodb first"
		exit()

def create():
	"""Main handler function"""
	
	print "Setting up MongoDB Connection..."
	mongodb = set_up_mongodb_connection()

	#1) Alexa
	print "Importing Alexa Data..."
	import_alexa_data(mongodb)
	
	#2) Alexa rank from top 1m
	print "Creating alexa rank"
	create_alexa_rank()
	
	#3) Clean up
	print "cleaning"
	clean_up()
	
	#3) Import existing adgroups from cats.json
	#import_existing_buckets(mongodb)

def create_alexa_rank():
	"""Parses all the ranking files and assigns a rank to each entry per day. Also useful to have a 'latest' attribute"""
	
	c = MongoClient()
	
	rfloc = '/Users/mruttley/Documents/2015-04-22 AdGroups/Bucketerer/data_crunching/ranking_files/'
	files = sorted(listdir(rfloc))
	
	rankings = defaultdict(dict)
	
	#import all the files
	for fn in files:
		date = fn.replace('top-1m.csv', '')
		with open(rfloc + fn) as f:
			for n, line in enumerate(f):
				if len(line) > 4:
					domain = line.split(",")[1][:-1].replace(".", "#")
					rankings[domain][date] = n
	
	#add a latest attribute
	domains = rankings.keys()
	print "About to update {0} domains".format(len(domains))
	for n, domain in enumerate(domains):
		rankings[domain]['latest'] = rankings[domain][sorted(rankings[domain])[0]]
	
		#set the attribute
		exists = c['bucketerer']['domains'].find_one({'domain': domain}, {'domain':1})
		if exists:
			c['bucketerer']['domains'].update({
				'_id': exists['_id']
			}, {
				'$set': {
					'alexa.rank': rankings[domain]
				}
			})
		if n % 100000 == 0:
			print n
	
def clean_up():
	"""Removes corrupted records"""
	to_delete = []
	domains = []
	c = MongoClient()['bucketerer']['domains']
	for x in c.find({}, {'domain':1}):
		if "__" in x['domain']:
			to_delete.append(x['_id'])
			domains.append(x['domain'])
		if "#" not in x['domain']:
			to_delete.append(x['_id'])
			domains.append(x['domain'])
	
	print "Deleting: {0}".format(domains)
	
	for x in to_delete:
		c.remove({'_id':x})
	
	










