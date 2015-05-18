from flask import Flask, render_template, request, make_response, Response, jsonify
from pymongo import MongoClient
from json import dumps, loads
from datetime import datetime
import domain_search #module with further filtering capacities etc
from dmoz import get_cats

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

###### Page Functionality
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
		#1) Related sites table
		if 'RL' in entry['alexa']['RLS']:
			data['related_sites'] = [{"name": x['@TITLE'], "url": x['@HREF'][:-1]} for x in entry['alexa']['RLS']['RL']]
		else:
			data['related_sites'] = False
	
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





