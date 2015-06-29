#!/usr/bin/env python

#Creates an ad bucket with a seed term/domain

from pymongo import MongoClient
from similarity import find_by_html, find_by_similarsites, create_connection, tokenize_clean
from tabulate import tabulate
verbose = False

def get_rank(c, domain):
	"""Gets the alexa rank for a domain. Returns False if not found"""
	
	entry = c['domains'].find_one({'domain':domain.replace(".", "#")}, {'alexa.rank.latest':1})
	try:
		return entry['alexa']['rank']['latest']
	except Exception:
		return False
		

def create_bucket_from_domain(seed_domain, total_sites=False):
	"""Creates a an ad bucket according to the parameters."""
	
	c = create_connection()
	
	#get some similar sites
	sites_by_similar = find_by_similarsites(c, starter_site=seed_domain)
	sites_by_html = find_by_html(c, starter_site=seed_domain)
	
	#merge, get rank and sort descending
	all_sites = []
	for repository in [sites_by_html, sites_by_similar]:
		for site in repository:
			domain = site['url'] if 'url' in site else site['domain']
			rank = get_rank(c, domain)
			if rank:
				if domain != seed_domain:
					all_sites.append([domain, rank])
	
	all_sites = sorted(all_sites, key=lambda x: x[1])
	
	if verbose:
		print tabulate(all_sites[:15 if not total_sites else total_sites])
	else:
		return all_sites

def create_bucket_with_raw_keywords(keywords, total_sites=False):
	"""finds sites with the keywords in their description. ranks by alexa"""
	
	c = create_connection()
	
	keywords = tokenize_clean(keywords)
	
	results = []
	for keyword in keywords:
		matches = c['domains'].find({'$text':{'$search':keyword}}, {'domain':1, 'alexa.rank.latest':1})
		for match in matches:
			results.append([match['domain'].replace('#', '.'), match['alexa']['rank']['latest']])
	
	results = sorted(results, key=lambda x: x[1])
	
	if verbose:
		print tabulate(results[:15 if not total_sites else total_sites])
	else:
		return results
	

def create_bucket_from_keywords(search_string, total_sites=False):
	"""Given some input text, this creates a bucket"""
	
	c = create_connection()
	
	#get some similar sites
	sites_by_html = find_by_html(c, starter_text=search_string)
	if verbose: print "Found {0} sites by meta desc".format(len(sites_by_html))
	
	#find similar sites to the top 10% (random number?)
	all_sites = []
	ten_pc = int(len(sites_by_html) / 10)
	for site in sites_by_html[:ten_pc]:
		domain = site['url'] if 'url' in site else site['domain']
		sites_by_similar = find_by_similarsites(c, starter_site=domain)
		ten_pc = int(len(sites_by_similar) / 10) #take top 10%
		if verbose: print "Adding {0} sites by similarsites".format(ten_pc)
		all_sites += sites_by_similar[:ten_pc]
	
	#prepend original sites_by_html to all_sites
	all_sites = sites_by_html + all_sites
	if verbose: print "Total sites: {0}".format(len(all_sites))
	
	#get rank and sort descending
	ranked_sites = []
	for site in all_sites:
		domain = site['url'] if 'url' in site else site['domain']
		rank = get_rank(c, domain)
		if rank:
			ranked_sites.append([domain, rank])
	
	ranked_sites = sorted(ranked_sites, key=lambda x: x[1])
	
	if verbose:
		print tabulate(ranked_sites[:15 if not total_sites else total_sites])
	else:
		return ranked_sites










