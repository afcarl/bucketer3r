#Auxiliary functionality that doesn't fit into any particular module

from collections import defaultdict

def add_alexa_rank(c, results):
	"""Adds the alexa rank to a list of dictionaries containing domains."""
	
	for x in range(len(results)):
		entry = c['domains'].find_one({'domain':results[x]['domain'].replace('.', '#')}, {'alexa.rank.latest':1})
		rank = entry['alexa']['rank']['latest']
		results[x]['alexa_rank'] = rank
	
	return results

def get_data_for_sitelist(c, sitelist):
	"""A dict of rank and expected uniques for a sitelist"""
	
	siteinfo = defaultdict(list)
	
	#get latest alexa ranks for all the sites
	for site in sitelist:
		entry = c['domains'].find_one({'domain': site.replace('.', '#')}, {'alexa.rank.latest':1})
		if entry:
			siteinfo[site].append(entry['alexa']['rank']['latest'])
	
	#unique visits
	for site, info in siteinfo.iteritems():
		entry = c['comscore_estimations'].find_one({'rank': info[0]}, {'unique_visitors':1})
		if entry:
			siteinfo[site].append(entry['unique_visitors'])
	
	return siteinfo
	

def calculate_maxp(siteinfo):
	
	total = 0
	largest = 0
	for site, info in siteinfo.iteritems():
		if len(info) == 2:
			total += info[1]
			if info[1] > largest:
				largest = info[1]
	
	maxp = float(largest) / total
	
	return maxp

def calculate_daily_traffic(siteinfo):
	
	total = 0
	for site, info in siteinfo.iteritems():
		if len(info) == 2:
			total += info[1]
	
	traffic = int(float(total) / 91.25)
	
	return traffic

def calculate_daily_clickthrough(sitelist, expected_traffic):
	return 999

def calculate_hitp(sitelist):
	return 999

def get_metrics(c, adgroup_name):
	"""Gets metrics for an adgroup"""
	
	entry = c['adgroups'].find_one({'name':adgroup_name}, {'metrics':1, 'sites':1})
	if 'metrics' not in entry:
		recalculate_metrics(c, adgroup_name)
		entry = c['adgroups'].find_one({'name':adgroup_name}, {'metrics':1, 'sites':1})
	
	metrics = {}
	
	for k,v in entry['metrics'].iteritems():
		if type(v) == float:
			metrics['metric_' + k] = round(v, 3) #add prefix
		else:
			metrics['metric_' + k] = v #add prefix
	
	#add total domains
	metrics['metric_total_domains'] = len(entry['sites'])
	
	return metrics

def recalculate_metrics(c, adgroup_name):
	"""Recalculates metrics for an adgroup"""

	#setup
	entry = c['adgroups'].find_one({'name':adgroup_name})
	siteinfo = get_data_for_sitelist(c, entry['sites'])
	
	#calculate metrics
	metrics = {
		"expected_daily_traffic": calculate_daily_traffic(siteinfo),
		"maxp": calculate_maxp(siteinfo),
		"hitp": calculate_hitp(siteinfo)
	}
	metrics["expected_daily_clickthrough"] = calculate_daily_clickthrough(entry['sites'], metrics['expected_daily_traffic']),
	
	c['adgroups'].update({'_id':entry['_id']}, {'$set':{'metrics':metrics}})
	
