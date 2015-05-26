#!/usr/bin/env python

#Imports the similarsites.com data

from json import loads as json_loads
from os import listdir

from pymongo import MongoClient

directory = "/Users/mruttley/Documents/2015-04-22 AdGroups/Bucketerer/similarity/similarsites/"

def create_connection():
	"""Creates a mongodb connection"""
	c = MongoClient()
	c = c['bucketerer']
	return c

def parse_file(filename):
	"""Parses a single file"""
	
	with open(directory+filename) as f:
		data = f.readlines()
		category = json_loads(data[0])
		similar = json_loads(data[1])
		
		if 'SimilarSites' not in similar:
			similar = False
		if 'Category' not in category:
			category = False
	
	return [category, similar]

def create():
	"""Main handler function"""
	
	c = create_connection()
	
	for n, domain in enumerate(listdir(directory)):
		
		category, similar = parse_file(domain)
		
		if (not category) and (not similar):
			print "{0} had no data".format(domain)
			continue
		
		domain = domain.replace('.', '#')
		
		to_add = {}
		if similar:
			#Convert similar keys to lowercase
			try:
				to_add['similar'] = {'similarsites': [{'url': x['Url'], 'score': x['Score']} for x in similar['SimilarSites']]}
			except TypeError:
				print similar
				exit()
		if category:
			to_add['category'] = {'similarsites': {'category': category['Category'],'rank': category['CategoryRank']}}
		
		entry = c['domains'].find_one({'domain':domain}, {'_id':1})
		
		if entry:
			c['domains'].update({'_id': entry['_id']},{'$set': to_add})
		else:
			print "Inserting new domain: {0}".format(domain)
			to_add['domain'] = domain
			c['domains'].insert(to_add)
		
		if n % 100 == 0:
			print n
	