#Functionality to search for various domains

def get_domains_by_name(kw, c, adgroup=False):
	"""Searches for domains by a text fragment that matches the domain name (not the tld)"""
	domains = []
	
	existing = set()
	if adgroup:
		existing = set(c['adgroups'].find_one({'name': adgroup}, {'sites':1})['sites'])
	
	for domain in c['domains'].find({}, {'domain': 1, 'alexa.rank.latest':1}):
		try:
			rank = domain['alexa']['rank']['latest']
			domain_name = domain['domain'].replace('#', '.')
			if kw in domain_name:
				if domain_name not in existing:
					domains.append({
						"domain": domain_name,
						"rank": rank
					})
		except KeyError:
			pass
	
	return domains[:50]


def get_domains_by_category(name, c):
	"""Searches for domains by category"""
	domains = []
	
	for domain in c['domains'].find({}, {'domain': 1, }):
		cats = something
		if name in cats:
			domains.append({
				"domain": domain['domain']
			})
	
	return domains