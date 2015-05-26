#Auxiliary functionality that doesn't fit into any particular module

def add_alexa_rank(c, results):
	"""Adds the alexa rank to a dataset.
	Expects a list of dictionaries"""
	
	for x in range(len(results)):
		entry = c['domains'].find_one({'domain':results[x]['domain'].replace('.', '#')}, {'alexa.rank.latest':1})
		rank = entry['alexa']['rank']['latest']
		results[x]['alexa_rank'] = rank
	
	return results

def get_metrics(c, adgroup_name):
	"""Gets metrics for an adgroup"""
	
	metrics = {}
	entry = c['adgroups'].find_one({'name':adgroup_name})
	
	#total domains
	metrics['metric_total_domains'] = len(entry['domains'])
	
	#expected daily traffic
	#metrics['metric_expected_daily_traffic'] = 999
	
	#expected daily clickthrough
	#metrics['metric_expected_daily_clickthrough'] = 999
	
	#max p
	metrics['metric_max_p'] = entry['max_p']
	
	return metrics

def recalculate_metrics(c, adgroup_name):
	"""Recalculates metrics for an adgroup"""

	metrics = {}
	entry = c['adgroups'].find_one({'name':adgroup_name})
	
	#expected daily traffic
	#metrics['metric_expected_daily_traffic'] = 999
	
	#expected daily clickthrough
	#metrics['metric_expected_daily_clickthrough'] = 999
	
	#max p
	metrics['metric_max_p'] = entry['max_p']
	
	return metrics
	
	
