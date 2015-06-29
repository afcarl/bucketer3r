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
verbose = False

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

def opt_cosine_similarity(vec1, vec2, min_intersection=3):
	"""Returns the cosine similarity of two vectors, with some optimization for descriptions,
	e.g. vectors must have at least 2 words in common
	Vectors should be Counters"""

	intersection = set(vec1.keys()) & set(vec2.keys())
	
	if min_intersection:
		if len(intersection) < min_intersection:
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

def find_by_dmoz_description(starter_site, index):
	"""Given a starter site, it analyzes it and tries to find similar websites by matching the dmoz description."""
	
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

def find_by_similarsites(c, starter_site=False, adgroup=False):
	"""Searches similarsites crawled data. Returns a list [{url, score}]"""
	
	existing = set()
	if adgroup:
		existing = set(c['adgroups'].find_one({'name':adgroup},{'sites':1})['sites'])
	
	if starter_site:
		entry = c['domains'].find_one({'domain':starter_site.replace('.', "#"), 'similar.similarsites':{'$exists':True}}, {'similar.similarsites':1})
		if entry:
			return [x for x in entry['similar']['similarsites'] if x['url'] not in existing]
		else:
			return []
	else:
		sites = defaultdict(int)
		for existing_site in existing:
			try:
				data = c['domains'].find_one({'domain':existing_site.replace('.','#')},{'similar.similarsites':1})['similar']['similarsites']
				for similar_site in data:
					sites[similar_site['url']] += similar_site['score'] #merge dupes
			except (KeyError, TypeError):
				pass
		
		k = sites.keys()
		for x in k: #merrr
			if x in existing:
				del sites[x]
		
		
		#print sorted(list(sites.keys()))
		#print sorted(list(existing))
		
		sites = sorted([{'url':k,'score':v} for k,v in sites.iteritems()], key=lambda x: x['score'], reverse=True)
		return sites

def find_by_html(connection, starter_site=False, starter_text=False, check_cache=True, adgroup=False):
	"""
	 - Searches and ranks by the page's meta description in the HTML
	connection	  :  a mongodb connection
	starter_site  :  some domain name
	starter_text  :  some text instead of a domain name (typically some compiled domains)
	verbose		  :  whether you want the results printed to the terminal
	check_cache	  :  set to false if you want to always pull new data
	 - returns a list of dictionaries [{url, score, desc}]
	 - can be tested with: import similarity;c=similarity.create_connection();similarity.find_by_html(c,starter_text='recipes')
	"""
	
	#first grab a set of sites that we shouldn't match (since they already exist)
	existing = set()
	if adgroup:
		if verbose: print "Getting sites that we shouldn't match in the adgroup"
		try:
			existing = set(connection['adgroups'].find_one({'name':adgroup}, {'sites':1})['sites'])
			if verbose: print "done"
		except (TypeError, KeyError):
			pass
	
	#if a starter site was provided, get the description
	if starter_site:
		domain = starter_site.replace('.', '#')
		#get the meta description
		entry = connection['domains'].find_one({'html.meta_description': {'$exists':True}, 'domain': domain },{'html.meta_description': 1, 'similar.meta_description': 1, 'domain': 1})
	
		#check if there's anything in the cache
		results = []
		if check_cache:
			if verbose: print "checking cache"
			try:
				if entry:
					if verbose: print "entry was true"
					results = entry['similar']['meta_description']
					if results:
						if verbose: print "getting descs"
						for x in range(len(results)):
							desc = connection['domains'].find_one({"domain":results[x]['domain'].replace('.',"#")}, {"html.meta_description":1})
							desc = desc['html']['meta_description']
							results[x]['desc'] = desc
						return results
			except KeyError:
				pass
		
		#nothing was found in the cache
		#get starter site's description to compare things to
		try:
			if verbose: print "setting starter descs"
			starter_desc = entry['html']['meta_description']
		except (KeyError, TypeError):
			return []
	else:
		
		if starter_text:
			#use the starter text instead
			starter_desc = starter_text
			if verbose: print "Starter desc being set to: {0}".format(starter_desc)
		else:
			#starter desc must be that of all the adgroup items combined
			starter_desc = ""
			if verbose: print "getting meta desc for all sites in adgroup"
			for site in existing:
				entry = connection['domains'].find_one({'domain':site.replace('.', "#")}, {'html.meta_description':1})
				if entry:
					try:
						desc = entry['html']['meta_description']
						starter_desc += " " + desc
					except KeyError:
						pass
	
	if verbose: print "After main decisioning, starter desc is: {0}".format(starter_desc)
	
	#set up a ranking placeholder for the top 50 results
	if verbose: print "creating placeholder"
	results = [{"url": "", "score": 0, "desc": ""} for x in range(50)]
	
	#clean/tokenize/vectorize the text
	if verbose: print "vectorizing"
	starter_desc = tokenize_clean(starter_desc) #clean it and tokenize it
	if verbose: print "Starter desc: {0}".format(starter_desc)
	starter_vector = Counter(starter_desc) #vectorize it
	if verbose: print "Starter vector: {0}".format(starter_vector)
	
	#scan all other domains
	if verbose: print "iterating through all domains"
	
	added = 0
	for n, record in enumerate(connection['domains'].find({'html.meta_description':{'$exists':True}}, {'html.meta_description':1, 'domain':1})):
	
		domain = record['domain'].replace("#", ".")
		
		if domain != starter_site:
			if domain not in existing:
				desc = record['html']['meta_description']
				kw_vector = Counter(tokenize_clean(desc)) #vectorize desc
				cosim = opt_cosine_similarity(starter_vector, kw_vector, min_intersection=False)
				
				if cosim:
					if cosim > results[-1]["score"]:
						
						for x in range(len(results)):
							if cosim > results[x]["score"]:
								results = results[:x] + [{"domain":domain, "score":cosim, "desc": desc}] + results[x:]
								added += 1
								results = results[:50]
								break
		if verbose:
			if n % 50000 == 0:
				print n, added
	
	if verbose: print "results is of len {0}".format(len(results))
	if verbose:
		for x in results:
			print x
	
	for x in range(len(results)):
		if results[x]["score"] == 0:
			results = results[:x] #cut off blank tail of results if present
			break
	
	if starter_site:
		if verbose: print "saving to cache"
		#save to cache
		connection['domains'].update({'_id': entry['_id']},
			{
				'$set': { #have to remove the description, don't want to save it twice
					'similar.meta_description': [{'domain':x['domain'],'score':x['score']} for x in results]
				}
			})
	
	if verbose: print "results being return are of len {0}".format(len(results))
	return results

def suggest_by_existing_content(c, sitelist):
	"""Accepts a list of sites. Suggests more similar sites by various metrics. Sorts them by popularity initially."""
	
	
	
	


















	
	
	