
from json import dumps, loads
from datetime import datetime

from flask import Flask, render_template, request, make_response, Response, jsonify
from pymongo import MongoClient

import domain_search #module with further filtering capacities etc
from dmoz import get_cats
from similarity import find_by_html, find_by_site_description, find_by_similarsites
from auxiliary import add_alexa_rank

app = Flask(__name__)
c = MongoClient()['bucketerer']


###### AJAX Functionality
@app.route('/get_adgroup')
def get_adgroup():
	#Ajax request to get a record from the adgroups database
	name = request.args.get('name')
	data = c['adgroups'].find_one({'name':name})
	del data['_id']
	return jsonify(data)

@app.route('/filter_domains')
def filter_domains():
	#Ajax request to filter useful domains
	kw = request.args.get('text')
	name = request.args.get('name')
	
	#find relevant domains by name
	domains = domain_search.get_domains_by_name(kw, c, name)
	
	#find relevant domains by category match
	#domains += domain_search.get_domains_by_category(name, c)
	
	#sort by traffic rank
	domains = sorted(domains, key=lambda x: x['rank'])
	
	return Response(dumps(domains), mimetype='application/json')

@app.route('/remove_adgroupsite')
def remove_adgroupsite():
	"""Removes a site from an adgroup"""
	
	adgroup_name = request.args.get('adgroup_name')
	domain = request.args.get('domain')
	
	entry = c['adgroups'].find_one({'name': adgroup_name}, {'sites':1})
	sites = [x for x in entry['sites'] if x != domain]
	
	c['adgroups'].update(
		{'_id':entry['_id']},
		{
			"$set": {
				"sites": sites
			}
		}
	)
	
	return Response(dumps({'answer': "success"}), mimetype='application/json')

@app.route('/add_adgroupsite')
def add_adgroupsite():
	"""Adds a site to an adgroup"""
	
	adgroup_name = request.args.get('adgroup_name')
	domain = request.args.get('domain')
	
	entry = c['adgroups'].find_one({'name': adgroup_name}, {'sites':1})
	
	if domain in entry['sites']:
		return Response(dumps({'answer': "already there"}), mimetype='application/json')
	
	entry['sites'].append(domain)
	c['adgroups'].update(
		{'_id':entry['_id']},
			{
				"$set": {
					"sites": entry['sites']
			}
		}
	)
	
	return Response(dumps({'answer': "success"}), mimetype='application/json')

@app.route('/delete_adgroup')
def delete_adgroup():
	"""Deletes an adgroup"""
	
	adgroup_name = request.args.get('name')
	print [adgroup_name]
	entry = c['adgroups'].find_one({'name': adgroup_name}, {'_id':1})
	if not entry:
		print "entry not found"
	c['adgroups'].remove({'_id':entry['_id']})
	
	return Response(dumps({'answer': "success"}), mimetype='application/json')

@app.route('/get_metrics')
def get_metrics():
	"""Retrives and recalculates metrics for a group"""
	
	adgroup_name = request.args.get('adgroup_name')
	
	recalculate_metrics(adgroup_name)
	metrics = get_metrics(adgroup_name)
	
	return Response(dumps(metrics), mimetype='application/json')

@app.route("/search_html_meta_description")
def search_html_meta_description():
	"""Searches for a site via HTML meta desc"""

	domain = request.args.get('domain')
	results = find_by_html(c, domain)
	results = add_alexa_rank(c, results)
	
	return Response(dumps(results), mimetype='application/json')

@app.route("/search_similarsites")
def search_similarsites():
	"""Searches for a site in the similarsites.com data"""

	domain = request.args.get('domain')
	
	results = []
	
	data = find_by_similarsites(domain)
	for x in data:
		#try and get a title
		entry = c['domains'].find_one({'domain':x['url'].replace('.', "#"), 'html.page_title':{'$exists':True}}, {'html.page_title':1})
		title = entry['html']['page_title'] if entry else ""
		
		results.append({
			'url': x['url'],
			'score': round(x['score'], 4),
			'title': title
		})
	
	results = results[:50]
	
	return Response(dumps(results), mimetype='application/json')

###### Page Functionality

@app.route('/import', methods=['POST', 'GET'])
def import_data():
	"""Imports data to an adgroup."""
	
	data = {}
	
	if request.method == 'POST':
		#de-serialize
		print request.form['domain_data']
		domain_data = loads(request.form['domain_data'])
		
		#save to the group
		total = 0
		for domain in domain_data['sites']:
			entry = c['adgroups'].find_one({'name': domain_data['adgroup']}, {'sites':1})
			
			if domain:
				if domain not in entry['sites']:
					total += 1
					entry['sites'].append(domain)
			
			c['adgroups'].update({'_id':entry['_id']}, {"$set": {"sites": entry['sites']}})
		
		#set message
		data['message'] = "Added {0} sites to {1}.".format(total, domain_data['adgroup'])
		
		#set adgroup name
		data['adgroup'] = domain_data['adgroup']
		
	else:
		adgroup_name = request.args.get('name')
		if adgroup_name:
			data['adgroup'] = adgroup_name
	
	#get the list of domains for the select box
	data['adgroups'] = [x['name'] for x in c['adgroups'].find({}, {'name':1})]
	
	return render_template("import.html", data=data)

@app.route('/export')
def export_data():
	"""Exports data to a file"""
	
	adgroup_name = request.args.get('name')

@app.route('/explore')
def explore_domains():
	data = {}
	data['page'] = "explore"
	data['domain_name'] = request.args.get('domain')

	if not data['domain_name']:
		data['domain_name'] = 'mozilla.org' #lol default
	
	entry = c['domains'].find_one({'domain':data['domain_name'].replace('.', '#')})
	
	if not entry:
		data['error'] = "Sorry, Bucketerer doesn't have any information about this domain"
	else:
		
		#get information about the website
		#1) Alexa related sites table
		if 'RL' in entry['alexa']['RLS']:
			data['alexa_related_sites'] = [{"name": x['@TITLE'], "url": x['@HREF'][:-1]} for x in entry['alexa']['RLS']['RL']]
		else:
			data['alexa_related_sites'] = False
		
		#2) SimilarSites
		if 'similar' in entry:
			if 'similarsites' in entry['similar']:
				ss = []
				for x in entry['similar']['similarsites']:
					
					#try and get a site title
					try:
						title = c['domains'].find_one({'domain':x['url'].replace('.', '#')}, {'html.page_title': 1})['html']['page_title']
					except Exception:
						title = ""
					
					ss.append({'url': x['url'], "title": title})
					
				data['ss_related_sites'] = ss
		
		#3) META related sites
		data['meta_related_sites'] = find_by_html(c, data['domain_name'])
	
	return render_template("explore.html", data=data)

@app.route('/view_adgroups')
def view_adgroups():
	data = {}
	data['page'] = "view"
	
	#get existing adgroups
	data['buckets'] = []
	for adgroup in c['adgroups'].find():
		data['buckets'].append({
				'name': adgroup['name'],
				'total_sites': len(adgroup['sites']),
				'maxp': 0,
			})
	
	return render_template("view_adgroups.html", data=data)

@app.route('/new_adgroup', methods=['POST', 'GET'])
def new_adgroups():
	data = {}
	
	if request.method == 'POST':
		#form submission, could be either setting a name, or saving actual data
		
		info = request.form['info']
		info = loads(info)
		
		if info['action'] == 'create':
			
			#check it doesn't already exist
			if c['adgroups'].find_one({'name': info['name']}, {'name':1}):
				data['error'] = 'Adgroup "{0}" already exists'.format(info['name'])
				data['page'] = 'new'
			else:
				#create the entry
				data = {
						'name': info['name'],
						'created_on': datetime.now(),
						'sites': [],
						'created_by': 'Bucketerer User'
					}
				c['adgroups'].insert(data)
				data['page'] = "edit"
				
		else:
			#info action is `edit`
			data['page'] = "edit"
			
			#save the new lot of sites
			entry = c['adgroups'].find_one({'name': info['name']}, {'_id':1})
			if entry:
				
				print info['sites']
				
				#c['adgroups'].update(
				#	{
				#		"_id": entry['_id']
				#	},
				#	{
				#		'$set': {
				#			'sites': info['sites']
				#		}
				#	}
				#)
	
	else:
		existing = request.args.get('name')
		
		if existing:
			data = c['adgroups'].find_one({'name':existing}) #add in all the data from the database entry
			data['page'] = "edit"
		else:
			data['page'] = "new"
	
	return render_template("new_adgroup.html", data=data)

@app.route('/')
def show_main_page():
	data = {}
	data['page'] = "main"
	return render_template("index.html", data=data)

if __name__ == '__main__':
	app.debug = True
	app.run()





