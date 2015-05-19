#!/usr/bin/env python

#Module to find similar domains
# Sources
# - DMOZ category data
# - Site description
# - Domain name
# - SimilarSites crawled data
# - Site HTML

#Imports
from re import findall
from os import listdir
from collections import defaultdict, Counter
from math import sqrt
from datetime import datetime
from pdb import set_trace

from pymongo import MongoClient
from stopwords import stopwords
from bs4 import BeautifulSoup

#setup
stopwords = stopwords()
directory = '/Users/mruttley/Documents/2015-04-22 AdGroups/Bucketerer/data_crunching/alexa_data/'
html_directory = "/Users/mruttley/Documents/2015-05-11 StatCounter HTML Crawler/html/"
ranking_directory = "/Users/mruttley/Documents/2015-04-22 AdGroups/Bucketerer/data_crunching/ranking_files/"

#Auxiliary functionality

def get_ranking():
	"""Gets a ranking of domains"""
	timestamp = datetime.strftime(datetime.now(), '%Y-%m-%d')
	filename = timestamp+"top-1m.csv"
	domains = []
	with open(ranking_directory + filename) as f:
		for line in f:
			domain = line[:-1].split(",")[1].lower()
			domains.append(domain)
	return domains

def create_connection():
	"""Creates a mongodb connection"""
	
	c = MongoClient()
	c = c['bucketerer']
	
	return c

def tokenize_clean(s):
	"""Tokenizes a string and removes stopwords"""
	s = findall("[a-z]{3,}", s.lower())
	s = [x for x in s if x not in stopwords]
	return s

def get_description(domain_file):
	"""Gets information about a domain"""
	desc = False
	with open(directory + domain_file) as f:
		for line in f:
			if "DESC=" in line:
				try:
					desc = line.split('DESC=')[1].split('>')[0]
				except IndexError:
					print domain_file
					print line
					break
				break
	
	if desc:
		return [domain_file.split('.txt')[0], desc]
	else:
		return False

def descriptions():
	"""Temporary generator for descriptions"""
	for fn in listdir(directory):
		info = site_and_description(fn)
		if info:
			yield info

def load_matrix():
	"""Loads the domain keywords file into memory"""
	
	index = {
		'domain_keywords': {},
		'keyword_domains': defaultdict(list)
	}
	
	with open('domain_kws.txt') as f:
		for line in f:
			if line.endswith('\n'):
				line = line[:-1]
			line = line.split('\t')
			if len(line) > 1:
				domain = line[0]
				kws = set(line[1:])
				
				index['domain_keywords'][domain] = kws
				for kw in kws:
					index['keyword_domains'][kw].append(domain)
	
	return index

def opt_cosine_similarity(vec1, vec2):
	"""Returns the cosine similarity of two vectors, with some optimization for descriptions,
	e.g. vectors must have at least 2 words in common
	Vectors should be Counters"""

	intersection = set(vec1.keys()) & set(vec2.keys())
	
	if len(intersection) < 3 :
		return False
	
	numerator = sum([vec1[x] * vec2[x] for x in intersection])
	sum1 = sum([vec1[x]**2 for x in vec1.keys()])
	sum2 = sum([vec2[x]**2 for x in vec2.keys()])
	denominator = sqrt(sum1) * sqrt(sum2)
	if not denominator:
		return 0.0
	else:
		return float(numerator) / denominator

#File generation functionality

def generate_domain_file():
	"""Generates a file with domain \t kw \t kw
	These keywords could be from description or HTML or other sources"""
	
	files = listdir(directory)
	print "About to process {0} files".format(len(files))
	
	with open('domain_kws.txt', 'w') as f: #TODO: add unicode support
		for n, fn in enumerate(files):
			desc = get_description(fn)
			if desc:
				domain = desc[0]
				kws = tokenize_clean(desc[1])
				line = '\t'.join([domain]+kws)
				f.write(line + "\n")
			if n % 5000 == 0:
				print "Processed {0}".format(n)

def html_test(domain):
	with open(html_directory+domain+".html") as f:
		soup = BeautifulSoup(f.read())
		description = soup.findAll('meta', attrs={'name':'description', 'content':True})
		print description
		if description:
			print description[0]['content']

def parse_html_file(domain):
	"""Extracts information about a page from its HTML"""
	
	info = {}
	with open(html_directory+domain+'.html') as f:
		#import the file
		soup = BeautifulSoup(f.read())
		
		#description
		description = soup.findAll('meta', attrs={'name':'description', 'content':True})
		if description:
			info['meta_description'] = description[0]['content']
		
		#title
		if soup.title:
			info['page_title'] = soup.title.text
		
		#keywords
		keywords = soup.findAll('meta', attrs={'name':'keywords', 'content':True})
		if keywords:
			keywords = keywords[0]['content']
			if "," in keywords:
				keywords = [x.strip() for x in keywords.split(",")]
				info['meta_keywords'] = keywords
	
	return info

def generate_html_files():
	"""Creates files from the meta description, title, keywords. In future maybe page content too."""
	
	c = create_connection()
	files = set(listdir(html_directory))
	ranking = get_ranking()
	already_scanned = set([x['domain'].replace('#', '.') for x in c['domains'].find({'html':{'$exists':True}}, {'domain':1})])
	
	for n, domain in enumerate(ranking):
		if domain in already_scanned:
			#print "{0} {1} already processed".format(n, domain)
			continue
		else:
			if (domain + ".html") in files:
				try:
					info = parse_html_file(domain)
					#now update database record
					entry = c['domains'].find_one({'domain':domain.replace(".", "#")}, {'_id':1})
					if entry:
						c['domains'].update(
							{
								'_id': entry['_id']
							},
							{
							'$set': {
								'html': info
							}
						})
					else:
						c['domains'].insert({
							'domain': domain.replace(".", "#"),
							'html': info
						})
					
					print n, domain, len(info)
				
				except Exception, e:
					print Exception, e

#Testing and analysis

def test(site):
	"""Test this code:
	python -c "import similarity;similarity.test('soundcloud.com')"
	"""
	index = load_matrix()
	a = find_by_site_description(site, index)
	for x in a[:10]:
		print x[0], "\t\t\t", round(x[1], 3), "\t\t", ",".join(x[2])

def popular_words():
	index = load_matrix()
	a = defaultdict(int)
	for domain, desc in index['domain_keywords'].iteritems():
		for x in desc:
			a[x] += 1
	
	a = sorted(a.items(), key=lambda x: x[1], reverse=True)
	
	for x in a[:200]:
		print x[0]

#Record creation

def cache_similar_sites_by_html():
	"""Searches every domain for similar sites by its meta_description. Saves the top 10 to mongodb"""
	
	c = create_connection()
	
	for site in c['domains'].find({'html':{'$exists':True}}, {'html':1}):
		domain = site['domain'].replace('#', '.')
		similar = find_by_html(domain)

#Domain search functionality

def search_by_domain_keyword(c, kw):
	"""Finds domain names that match by keyword
		e.g. "golf" matching golfdigest.com
		Accepts:
		 - c, a mongodb connection
		 - kw, a string
		Returns:
		 - a list of up to 50 domain names
		"""
	
	#clean keyword
	kw = kw.lower()
	
	#search
	domains = []
	for domain in c['domains'].find({}, {'domain':1}):
		if kw in domain['domain']:
			if len(domains) <= 50:
				domains.append(domain)
	
	return domains

def find_by_site_description(starter_site, index):
	"""Given a starter site, it analyzes it and tries to
	find similar websites by matching site description. These are dmoz descriptions"""
	
	results = [["", 0, ""] for x in range(50)] #ranking
	
	#get the description of the starter site
	starter_desc = get_description(starter_site+'.txt')[1]
	starter_desc = tokenize_clean(starter_desc) #clean it and tokenize it
	print starter_desc
	starter_vector = Counter(starter_desc) #vectorize it
	
	
	for domain, desc in index['domain_keywords'].iteritems():
		kw_vector = Counter(desc) #vectorize desc
		cosim = opt_cosine_similarity(starter_vector, kw_vector)
		if cosim:
			if cosim > results[-1][1]:
				for x in range(len(results)):
					if cosim > results[x][1]:
						results = results[:x] + [[domain, cosim, desc]] + results[x:]
						results = results[:50]
						break
	
	for x in range(len(results)):
		if results[x][1] == 0:
			return results[:x] #cut off blank tail of results if present

	return results

def find_by_similar_sites(starter_site):
	"""Searches similarsites crawled data"""

def find_by_html(starter_site, verbose=False):
	"""Searches and ranks by page HTML attributes"""
	
	c = create_connection()
	results = [["", 0, ""] for x in range(50)] #ranking
	
	#get the description of the starter site
	domain = starter_site.replace('.', '#')
	entry = c['domains'].find_one({'html.meta_description':{'$exists':True}, 'domain':domain}, {'html.meta_description':1, 'domain':1})
	starter_desc = entry['html']['meta_description']
	starter_desc = tokenize_clean(starter_desc) #clean it and tokenize it
	print starter_desc
	starter_vector = Counter(starter_desc) #vectorize it
	
	
	for n, entry in enumerate(c['domains'].find({'html.meta_description':{'$exists':True}}, {'html.meta_description':1, 'domain':1})):
		domain = entry['domain']
		desc = entry['html']['meta_description']
		
		kw_vector = Counter(tokenize_clean(desc)) #vectorize desc
		cosim = opt_cosine_similarity(starter_vector, kw_vector)
		if cosim:
			if cosim > results[-1][1]:
				for x in range(len(results)):
					if cosim > results[x][1]:
						results = results[:x] + [[domain, cosim, desc]] + results[x:]
						results = results[:50]
						break
	
	if verbose: print "Scanned {0} domains".format(n)

	for x in range(len(results)):
		if results[x][1] == 0:
			results = results[:x] #cut off blank tail of results if present
			break

	if verbose:
		for x in results[:10]:
			print x[0].replace('#', '.'), "\t\t\t", round(x[1], 3), "\t\t", x[2][:100] + "..."
	else:
		return results




















	
	
	