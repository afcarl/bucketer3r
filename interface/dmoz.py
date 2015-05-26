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


def process(text):
	"""Gets cats for copy and pasted text"""
	from pymongo import MongoClient
	from codecs import open as copen #rarely used function so imports inside def
	
	c = MongoClient()['bucketerer']	
	stuff = []
	text = text.split('\n')
	print len(text)
	for n, x in enumerate(text):
		cats = get_cats(c, x.lower())
		if cats:
			stuff.append("\t".join(cats))
		else:
			stuff.append("")
		if n % 200 == 0:
			print n
	
	stuff = '\n'.join(stuff)
	with copen('stuff.txt', 'w', encoding='utf8') as f:
		f.write(stuff)
	