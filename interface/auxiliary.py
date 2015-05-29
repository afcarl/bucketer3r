#Auxiliary functionality that doesn't fit into any particular module

def add_alexa_rank(c, results):
	"""Adds the alexa rank to a list of dictionaries containing domains."""
	
	for x in range(len(results)):
		entry = c['domains'].find_one({'domain':results[x]['domain'].replace('.', '#')}, {'alexa.rank.latest':1})
		rank = entry['alexa']['rank']['latest']
		results[x]['alexa_rank'] = rank
	
	return results

def calculate_maxp(sitelist):
	return 999

def calculate_daily_traffic(sitelist):
	return 999

def calculate_daily_clickthrough(sitelist, expected_traffic):
	return 999

def calculate_hitp(sitelist):
	return 999

def get_metrics(c, adgroup_name):
	"""Gets metrics for an adgroup"""
	
	entry = c['adgroups'].find_one({'name':adgroup_name}, {'metrics':1, 'sites':1})
	metrics = {}
	
	for k,v in entry['metrics'].iteritems():
		metrics['metric_' + k] = v #add prefix
	
	#add total domains
	metrics['metric_total_domains'] = len(entry['sites'])
	
	return metrics

def recalculate_metrics(c, adgroup_name):
	"""Recalculates metrics for an adgroup"""

	#setup
	entry = c['adgroups'].find_one({'name':adgroup_name})
	
	#calculate metrics
	metrics = {
		"expected_daily_traffic": calculate_daily_traffic(entry['sites']),
		"maxp": calculate_maxp(entry['sites']),
		"hitp": calculate_hitp(entry['sites'])
	}
	metrics["expected_daily_clickthrough"] = calculate_daily_clickthrough(entry['sites'], metrics['expected_daily_traffic']),
	
	c['adgroups'].update({'_id':entry['_id']}, {'$set':{'metrics':metrics}})
	
