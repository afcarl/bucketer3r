if(typeof(String.prototype.trim) === "undefined")
{ //https://stackoverflow.com/questions/1418050/string-strip-for-javascript
    String.prototype.trim = function() 
    {
        return String(this).replace(/^\s+|\s+$/g, '');
    };
}

function handle_edit(){
	//Handles the create/edit button being pressed on new_adgroup
	
	form = document.getElementById('data_transfer_form') //A hidden form at the bottom of the page used for sending data
	field = document.getElementById('info') //A hidden field in the above
	data = {} //an object which will later be serialized
	
	data.name = document.getElementById("adgroup_name").value
	
	//detect creation or edit and then gather the data
	if (document.getElementById("create_edit").innerHTML.indexOf('Create') != -1) {
		data.action = 'create'
		if (data.name.trim() == "") {
			alert("Please choose a name for this adgroup")
			return false
		}
	}else{
		data.action = 'edit'
		//grab the chosen sites
		data.sites = []
		siteBlocks = document.getElementsByClassName('adgroupsite')
		for (var x in siteBlocks) {
			site = siteBlocks[x].childNodes.innerHTML
			data.sites.push(site)
		}
	}
	
	//jsonify it
	data = JSON.stringify(data)
	
	//add to the form
	field.value = data
	
	//submit it
	form.submit()
}

function hide_everything(args) {
	//hides all components on the page apart from the
	//name entry field
	
	if (document.getElementById("create_edit").innerHTML.indexOf('Create') != -1) {
		divs = document.getElementsByTagName('div')
		for (var x in divs) {
			if (divs[x].className) {
				if (divs[x].className.indexOf('col-md') != -1) {
					if (divs[x].className.indexOf('adgroupname') == -1) {
						divs[x].style.visibility = "hidden"
					}
				}
			}
		}
	}
	
}

function load_category_table() {
	//Fills the category table on the new_adgroup page
	
	//set up the url
	url = "/category_info"
	if (location.href.indexOf('name=')!=-1) { //add a name if necessary
		name = location.href.split('name=')[1].split('&')[0]
		url += '?name=' + name
	}else{
		url += "?"
	}
	
	//make the request
	var xmlhttp;
	xmlhttp=new XMLHttpRequest()
	xmlhttp.onreadystatechange=function(){
		if (xmlhttp.readyState==4 && xmlhttp.status==200){
			resp = xmlhttp.responseText
			resp = JSON.parse(resp) //parse the json
		}
	}
	
	xmlhttp.open("GET", url);
	xmlhttp.send();	
}

function filter_domains(){
	//Handles AJAX requests for thought starters when creating a new adgroup
	starter = document.getElementById('thought_starter').value
	if (starter.length < 3) {
		return false
	}
	//clear
	tbody = document.getElementById('suggested_domains')
	tbody.innerHTML = "<tr><td colspan='3' style='text-align:center;'><img src='/static/img/spinner.gif'></td></tr>"
	//construct URL
	url = "/filter_domains?text=" + starter
	if (location.href.indexOf('name=')!=-1) { //add a name if necessary
		name = location.href.split('name=')[1].split('&')[0]
		url += '&name=' + name
	}
	//run
	var xmlhttp;
	xmlhttp=new XMLHttpRequest()
	xmlhttp.onreadystatechange=function(){
		if (xmlhttp.readyState==4 && xmlhttp.status==200){
			resp = xmlhttp.responseText
			resp = JSON.parse(resp) //parse the json
			tbody.innerHTML = '' //clear the spinner
			for (var x in resp) {
				row = document.createElement("tr")
				
				domain = document.createElement("td")
				domain_text = document.createTextNode(resp[x].domain)
				domain.appendChild(domain_text)
				
				rank = document.createElement("td")
				rank_number = document.createTextNode(resp[x].rank)
				rank.appendChild(rank_number)
				
				traffic = document.createElement("td")
				traffic_number = document.createTextNode(resp[x].traffic)
				traffic.appendChild(traffic_number)
				
				row.appendChild(domain)
				row.appendChild(rank)
				row.appendChild(traffic)
				
				tbody.appendChild(row)
			}
		}
	}
	xmlhttp.open("GET",url);
	xmlhttp.send();	
}

function insertAfter(newNode, referenceNode) {
	//http://stackoverflow.com/a/4793630/849354
    referenceNode.parentNode.insertBefore(newNode, referenceNode.nextSibling);
}

function expandcat(row_id) {
	//Creates or deletes a row expansion to show details about a particular category
	row = document.getElementById(row_id)
	
	//change the plus to a minus
	icon = row.getElementsByTagName('span')[0]
	if (icon.classList.contains("glyphicon-plus")) {
		icon.className = 'glyphicon glyphicon-minus'
	}else{
		icon.className = 'glyphicon glyphicon-plus'
	}
	
	//create or delete the extra row
	info_row = document.getElementById("info_" + row_id)
	if (info_row) { //delete
		info_row.parentNode.removeChild(info_row)
	}else{ //create
		
		//set up elements
		new_row = document.createElement('tr')
		new_td = document.createElement('td')
		site_list = document.createElement('div')
		site_list.className = "sitelist"
		site_list.id = 'site_list_' + row_id
		
		control_group = document.createElement("div")
		control_group.className = 'controlgroup'
		delete_button = document.createElement('button')
		delete_button.className = 'btn btn-primary controlbutton'
		delete_button.appendChild(document.createTextNode("Delete"))
		edit_button = document.createElement("button")
		edit_button.className = 'btn btn-primary controlbutton'
		url = '/new_adgroup?name=' + row_id.replace('row_', '')
		
		edit_button.addEventListener(
			"click",
			redirect(url)
		)
		
		edit_button.appendChild(document.createTextNode("Edit"))
		control_group.appendChild(edit_button)
		control_group.appendChild(delete_button)
		
		new_td.appendChild(control_group)
		new_td.appendChild(site_list)
		
		new_row.id = 'info_' + row_id
		new_row.appendChild(new_td)
		
		//new td must span all columns
		new_td.colSpan = row.parentNode.children[0].children.length
		
		//add to the DOM
		insertAfter(new_row, row)
		
		//get row data and insert the list of domains
		get_adgroup_data(row_id.replace('row_', ''))
	}
	
}

function redirect(url){
	//Annoying closure workaround
	return function(){
		location.href = url
	}
}

function get_adgroup_data(adgroup_name){
	//makes an ajax call to get adgroup data
	var xmlhttp;
	xmlhttp=new XMLHttpRequest()
	xmlhttp.onreadystatechange=function(){
		if (xmlhttp.readyState==4 && xmlhttp.status==200){
			resp = xmlhttp.responseText
			resp = JSON.parse(resp) //parse the json
			sl = document.getElementById("site_list_row_" + adgroup_name)
			for(var x in resp.sites){
				site = document.createElement("span")
				btn = document.createElement('button')
				btn.innerHTML = resp.sites[x]
				btn.className = 'btn sitebtn'
				btn.addEventListener("click", redirect("/explore?domain=" + resp.sites[x]))
				site.appendChild(btn)
				sl.appendChild(site)
			}
		}
	}
	xmlhttp.open("GET","/get_adgroup?name=" + adgroup_name);
	xmlhttp.send();	
}

function remove_site(domain, nodeid){
	//Removes a site from the box on the new_adgroup page
	//remove the box
	box = document.getElementById('adgroupsite_' + nodeid)
	box.parentNode.removeChild(box)
	adgroup_name = location.href.split("name=")[1].split("&")[0]
	
	//send ajax request to remove the site
	var xmlhttp;
	xmlhttp=new XMLHttpRequest()
	xmlhttp.onreadystatechange=function(){
		if (xmlhttp.readyState==4 && xmlhttp.status==200){
			resp = JSON.parse(xmlhttp.responseText)
			if (resp['answer'] == 'success') {
				console.log("Removed " + domain)
			}
		}
	}
	xmlhttp.open("GET","/remove_adgroupsite?adgroup_name=" + adgroup_name + "&domain=" + domain);
	xmlhttp.send();	
}
