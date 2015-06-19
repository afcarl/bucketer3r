from json import dumps, loads
from datetime import datetime
from collections import defaultdict
from functools import wraps
from hashlib import sha512

from flask import Flask, render_template, request, make_response, Response, jsonify
from flask_sslify import SSLify
from pymongo import MongoClient

import domain_search #module with further filtering capacities etc
from dmoz import get_cats
from similarity import find_by_html, find_by_dmoz_description, find_by_similarsites
from auxiliary import add_alexa_rank, get_metrics, recalculate_metrics

app = Flask(__name__)
#sslify = SSLify(app)
c = MongoClient()['bucketerer']

###### Authentication

def check_auth(username, password):
	"""This function is called to check if a username /
	password combination is valid.
	"""
	
	pw_hash = c['users'].find_one({'username':username}, {'pw_hash':1})
	if pw_hash:
		pw_hash = pw_hash['pw_hash']
		if sha512(password).hexdigest() == pw_hash: #TODO salt hashes
			return True
	
	return False

def authenticate():
	"""Sends a 401 response that enables basic auth""" #http://flask.pocoo.org/snippets/8/
	return Response(
		'Could not verify your login credentials.'
		'Please login using a username and password provided to you at Content Services. Email mruttley@mozilla.com for more details. ',
		401,
		{'WWW-Authenticate': 'Basic realm="Login Required"'})

def edit_user(c, username, password):
	"""Copied by sysadmin to create new user"""
	
	#python -c "from pymongo import MongoClient;c=MongoClient()['bucketerer'];from server import edit_user;edit_user(c,'u@mozilla.com','pw')"
	
	pw_hash = c['users'].find_one({'username':username}, {'pw_hash':1})
	if not pw_hash:
		c['users'].insert({'username':username, 'pw_hash': sha512(password).hexdigest()})
	else:
		c['users'].update({'username':username}, {'$set':{'pw_hash': sha512(password).hexdigest()}})
	

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return decorated

###### AJAX Functionality
@app.route('/get_adgroup')
@requires_auth
def get_adgroup():
	#Ajax request to get a record from the adgroups database
	name = request.args.get('name')
	data = c['adgroups'].find_one({'name':name})
	data['sites'] = sorted(data['sites'])
	del data['_id']
	return jsonify(data)

@app.route('/flag_url')
@requires_auth
def flag_url():
	"""Flags a url"""
	
	action = request.args.get('action')
	domain = request.args.get('domain')
	
	#TODO
	

@app.route('/export_all', methods=['GET', 'POST'])
@requires_auth
def export_all():
	"""Creates a file download from received post information"""
	
	data = []
	for x in c['adgroups'].find({}, {'sites':1, 'name':1, 'descriptors':1}):
		del x['_id']
		x['sites'] = sorted(list(set([y.strip().lower() for y in x['sites']]))) #TODO fix from the start
		x['descriptors'] = sorted(list(set([y.strip() for y in x['descriptors']])))
		x['name'] = x['name'].strip()
		data.append(x)
	
	data = sorted(data, key=lambda x: x['name'])
	data = dumps(data, indent=4)
	
	response = make_response(data)
	response.headers["Content-Disposition"] = "attachment; filename=adgroups.json"
	return response

@app.route('/filter_domains')
@requires_auth
def filter_domains():
	#Ajax request to filter useful domains
	kw = request.args.get('text')
	adgroup = request.args.get('adgroup')
	
	#find relevant domains by name
	domains = domain_search.get_domains_by_name(kw, c, adgroup=adgroup)
	
	#find relevant domains by category match
	#domains += domain_search.get_domains_by_category(name, c)
	
	#sort by traffic rank
	domains = sorted(domains, key=lambda x: x['rank'])
	
	return Response(dumps(domains), mimetype='application/json')

@app.route('/remove_adgroupsite')
@requires_auth
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
@requires_auth
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
@requires_auth
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
@requires_auth
def get_metrics_for_page():
	"""Retrives and recalculates metrics for a group"""
	
	adgroup_name = request.args.get('adgroup_name')
	
	recalculate_metrics(c, adgroup_name)
	metrics = get_metrics(c, adgroup_name)
	
	return Response(dumps(metrics), mimetype='application/json')

@app.route('/search_dmoz_description')
@requires_auth
def search_dmoz_description():
	"""Searches by DMOZ description"""
	
	domain = request.args.get('domain')
	adgroup = request.args.get('adgroup')
	
	results = find_by_dmoz_description(c, domain, adgroup=adgroup)
	
	return Response(dumps(results), mimetype='application/json')

@app.route("/search_html_meta_description")
@requires_auth
def search_html_meta_description():
	"""Searches for a site via HTML meta desc"""

	domain = request.args.get('domain')
	adgroup = request.args.get('adgroup')
	
	results = find_by_html(c, starter_site=domain, adgroup=adgroup)
	results = add_alexa_rank(c, results)
	
	return Response(dumps(results), mimetype='application/json')

@app.route("/search_similarsites")
@requires_auth
def search_similarsites():
	"""Searches for a site in the similarsites.com data"""

	domain = request.args.get('domain')
	adgroup = request.args.get('adgroup')
	
	results = []
	
	data = find_by_similarsites(c, starter_site=domain, adgroup=adgroup)
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

@app.route('/descriptors', methods=['POST', 'GET'])
@requires_auth
def adgroup_descriptors():
	"""Analyzes a specific adgroup"""
	
	if request.method == 'POST': #save some data
		
		a = request.form['adgroup'] #grab from headers
		d = request.form['descriptors']
		
		d = d.strip().split('\r\n') #clean data
		d = sorted(list(set([x for x in d if len(x) > 0])))
		
		data = c['adgroups'].find_one({'name':a}, {'descriptors':1}) #save data
		c['adgroups'].update({'name': a}, {'$set':{'descriptors':d}})
		
		data['total'] = len(d) #get data to display on the page
		data['show_total'] = True
		data['descriptors'] = d
		data['adgroup_name'] = a
		del data['_id']
		
	else:
		adgroup = request.args.get('adgroup')
		data = c['adgroups'].find_one({'name':adgroup}, {'descriptors':1})
		data['adgroup_name'] = adgroup
		del data['_id']
		
		if 'descriptors' not in data:
			data['descriptors'] = []
	
	return render_template("descriptors.html", data=data)	


@app.route('/analyze')
@requires_auth
def analyze_adgroup():
	"""Analyzes a specific adgroup"""
	
	adgroup = request.args.get('adgroup')
	data = c['adgroups'].find_one({'name':adgroup})
	data['adgroup_name'] = adgroup
	del data['_id']
	
	sites = []
	for site in data['sites']:
		sites.append({
			'name': site,
			'alexa_rank': 999,
			'estimated_traffic': 999
		})
	
	data['sites'] = sites
	
	return render_template("analyze.html", data=data)	

@app.route('/import', methods=['POST', 'GET'])
@requires_auth
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
@requires_auth
def export_data():
	"""Exports data to a file"""
	data = {}
	
	data['adgroup_name'] = request.args.get('name')
	if data['adgroup_name']:
		data['sitelist'] = c['adgroups'].find_one({'name':data['adgroup_name']}, {'sites':1})['sites']
	
	return render_template("export.html", data=data)

@app.route('/explore')
@requires_auth
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
		meta_related_sites = find_by_html(c, data['domain_name'])
		
		data['meta_related_sites'] = []
		for x in meta_related_sites:
			to_append = {}
			try:
				title = c['domains'].find_one({'domain':x['domain'].replace('.', '#')}, {'html.page_title': 1})['html']['page_title'][:100]
			except Exception:
				title = ""
			to_append['title'] = title
			to_append['url'] = x['domain']
			data['meta_related_sites'].append(to_append)
		
		
		#Estimated traffic & Alexa Rank
		try:
			rank = entry['alexa']['rank']['latest']
			last_date = sorted(entry['alexa']['rank'].keys())[-2]
			data['alexa_rank'] = rank
			data['alexa_latest_date'] = last_date
		except KeyError:
			data['alexa_rank'] = '?'
		
		data['estimated_daily_traffic'] = 999
		
		#Recent Alexa performance
		try:
			data['alexa_performance'] = sorted([[k, v] for k,v in entry['alexa']['rank'].iteritems() if k != 'latest'])
		except KeyError:
			data['alexa_performance'] = False
		
		#Is site in any buckets
		data['site_exists'] = False
		exists = c['adgroups'].find_one({"sites":{'$in':[data['domain_name']]}}, {'name':1})
		if exists:
			data['site_exists'] = exists['name']
		
		#Page title
		try:
			data['page_title'] = entry['html']['page_title']
		except KeyError:
			data['page_title'] = "Crawler couldn't scrape it."
		
		#Alexa Child S Rating
		try:
			data['alexa_child_s_rating'] = entry['alexa']['SD'][-2]['CHILD']['@SRATING']
		except (KeyError, IndexError):
			data['alexa_child_s_rating'] = "Unknown"
		
		#DMOZ categorization
		try:
			data['dmoz'] = get_cats(c, data['domain_name'])
		except KeyError:
			data['dmoz'] = []
		
		
	
	return render_template("explore.html", data=data)

@app.route('/view_adgroups')
@requires_auth
def view_adgroups():
	data = {}
	data['page'] = "view"
	
	#get existing adgroups
	data['buckets'] = []
	for adgroup in c['adgroups'].find():
		to_append = {
			'name': adgroup['name'],
			'name_for_id': adgroup['name'].lower().replace(' ', '_'),
			'total_sites': len(adgroup['sites'])
		}
		
		try:
			to_append['maxp'] = adgroup['metrics']['maxp']
		except KeyError:
			to_append['maxp'] = 999
		
		try:
			to_append['descriptors'] = "\n".join(adgroup['descriptors'])
			to_append['descriptors_length'] = len(adgroup['descriptors'])
		except KeyError:
			to_append['descriptors'] = ""
			to_append['descriptors_length'] = 0
		
		
		data['buckets'].append(to_append)
	data['buckets'] = sorted(data['buckets'], key=lambda x: x['name'])
	
	return render_template("view_adgroups.html", data=data)

@app.route('/new_adgroup', methods=['POST', 'GET'])
@requires_auth
def new_adgroup():
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
						'created_by': 'Bucketerer User',
						'metrics': {}
					}
				c['adgroups'].insert(data)
				data['page'] = "edit"
				data['adgroup_name'] = info['name']
				
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
			data['sites'] = sorted(data['sites'])
			data['page'] = "edit"
			data['adgroup_name'] = existing
		else:
			data['page'] = "new"
	
	return render_template("new_adgroup.html", data=data)

@app.route('/')
@requires_auth
def show_main_page():
	data = {}
	data['page'] = "main"
	return render_template("index.html", data=data)

if __name__ == '__main__':
	app.debug = True
	app.run(host="0.0.0.0", port=443, ssl_context=('/home/ec2-user/.openssl/server.crt', '/home/ec2-user/.openssl/server.key'))





