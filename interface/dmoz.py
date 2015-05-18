#DMOZ related functionality

from collections import defaultdict

def compile_domain_stats(c, domains):
	"""Compiles category information for a list of domains"""
	
	cats = defaultdict(int)
	
	for domain in domains:
		info = get_cats(c, domain)
		for cat in info:
			cats[cat] += 1
	
	cats = sorted(cats.items(), key=lambda x: x[1], reverse=True)
	return cats

def get_cats(c, domain):
	"""Gets the top dmoz categories for a given domains"""
	
	entry = c['domains'].find_one({'domain':domain.replace('.', '#')}, {'alexa.DMOZ.SITE.CATS.CAT':1})
	cats = entry['alexa']['DMOZ']['SITE']['CATS']['CAT'] #urgh this API
	if cats != {}:
		if type(cats) == list:
			return [x['@ID'] for x in cats]
		else:
			return [cats['@ID']]