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
		
		adgroup_name = row_id.replace('row_', '')
		
		dropdown = document.createElement('div')
		dropdown.className = "dropdown controlgroup"
		
		button = document.createElement('button')
		button.className = "btn btn-default dropdown-toggle"
		button.type = "button"
		button.id = "dropdownMenu_" + adgroup_name.replace(" ", "_")
		button.setAttribute('data-toggle', "dropdown")
		button.setAttribute('aria-expanded', 'true')
		button.appendChild(document.createTextNode('Select Action '))
		caret = document.createElement('span')
		caret.className = 'caret'
		button.appendChild(caret)
		
		ul = document.createElement('ul')
		ul.className = 'dropdown-menu'
		ul.setAttribute('role', 'menu')
		ul.setAttribute("aria-labelledby", 'dropdownMenu_' + adgroup_name.replace(" ", "_"))
		
		buttons = [
			["Edit", '/new_adgroup?name=' + adgroup_name],
			["Delete", delete_adgroup(adgroup_name)],
			["Import", '/import?name=' + adgroup_name],
			["Export", '/export?name=' + adgroup_name]
		]
		
		buttons.forEach(function(datum){
			li = document.createElement('li')
			li.setAttribute('role', 'presentation')
			a = document.createElement('a')
			a.setAttribute('role', 'menuitem')
			a.setAttribute('tabindex', '-1')
			a.href = "#"
			a.appendChild(document.createTextNode(datum[0]))
			if (typeof(datum[1]) === "string") {
				a.addEventListener('click', redirect(datum[1]))
			}else{
				a.addEventListener('click', datum[1])
			}
			li.appendChild(a)
			ul.appendChild(li)
		})
		
		dropdown.appendChild(button)
		dropdown.appendChild(ul)
		
		new_td.appendChild(dropdown)
		new_td.appendChild(site_list)
		
		new_row.id = 'info_' + row_id
		new_row.appendChild(new_td)
		
		//new td must span all columns
		new_td.colSpan = row.parentNode.children[0].children.length
		
		//add to the DOM
		insertAfter(new_row, row)
		
		//get row data and insert the list of domains
		get_adgroup_data(adgroup_name)
	}
	
}

function delete_adgroup(adgroup_name) {
	//Deletes an adgroup
	
	return function(){
		if (confirm("Are you sure you would like to delete " + adgroup_name + "?")) {
			if (confirm("Really, really sure? This can't be un-done")) {
				var xmlhttp;
				xmlhttp=new XMLHttpRequest()
				xmlhttp.onreadystatechange=function(){
					if (xmlhttp.readyState==4 && xmlhttp.status==200){
						resp = xmlhttp.responseText
						resp = JSON.parse(resp) //parse the json
						if (resp.answer === 'success') {
							alert("Successfully deleted adgroup: " + adgroup_name)
						}
						//now remove that row in the page
						if (location.href.indexOf('/view_adgroups')!=-1) {
							
						}
					}
				}
				xmlhttp.open("GET","/delete_adgroup?name=" + adgroup_name);
				xmlhttp.send();	
			}
		}
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

function add_site(domain, node_to_remove=false){
	//Adds a site to the adgroup - on both the frontend and backend
	//Also removes the site from whatever table/list it was added
	
	if (node_to_remove) {
		node_to_remove.parentNode.removeChild(node_to_remove)
	}
	
	recalculate_metrics() //recalculate metrics in the box 
	
	adgroup_name = location.href.split("name=")[1].split("&")[0]
	
	//send ajax request to add the site
	var xmlhttp;
	xmlhttp=new XMLHttpRequest()
	xmlhttp.onreadystatechange=function(){
		if (xmlhttp.readyState==4 && xmlhttp.status==200){
			resp = JSON.parse(xmlhttp.responseText)
			if (resp['answer'] == 'success') {
				console.log("Added " + domain)
			}else{
				console.log("Error adding " + domain)
			}
		}
	}
	xmlhttp.open("GET","/add_adgroupsite?adgroup_name=" + adgroup_name + "&domain=" + domain);
	xmlhttp.send();	
}

function recalculate_metrics(){
	//Recalculates all the metrics in the box at the top right
	
	var xmlhttp;
	xmlhttp=new XMLHttpRequest()
	xmlhttp.onreadystatechange=function(){
		if (xmlhttp.readyState==4 && xmlhttp.status==200){
			var resp = JSON.parse(xmlhttp.responseText)
			var metrics = Object.keys(resp)
			for (var x in metrics) {
				if (metrics[x].substring(0,7)==="metric_") {
					document.getElementById(metrics[x]).innerHTML = resp[metrics[x]]
				}
			}
		}
	}
	xmlhttp.open("GET","/get_metrics?adgroup_name=" + adgroup_name);
	xmlhttp.send();	
	
}

function remove_site(domain){
	//Removes a site from the box on the new_adgroup page
	//remove the box
	box = document.getElementById('adgroupsite_' + domain.replace(/\./g, "_"))
	box.parentNode.removeChild(box)
	
	recalculate_metrics() //recalculate metrics in the box 
	
	adgroup_name = location.href.split("name=")[1].split("&")[0]
	
	//send ajax request to remove the site
	var xmlhttp;
	xmlhttp=new XMLHttpRequest()
	xmlhttp.onreadystatechange=function(){
		if (xmlhttp.readyState==4 && xmlhttp.status==200){
			resp = JSON.parse(xmlhttp.responseText)
			if (resp['answer'] == 'success') {
				console.log("Removed " + domain)
			}else{
				console.log("Error in removing " + domain)
			}
		}
	}
	xmlhttp.open("GET","/remove_adgroupsite?adgroup_name=" + adgroup_name + "&domain=" + domain);
	xmlhttp.send();
}

function switch_suggest(tab){
	//switches the box underneath the suggest tab
	
	divs = document.querySelectorAll(".domain_suggest")
	for (var x in divs){
		var div = document.getElementById(divs[x].id)
		if (div != undefined) {
			if (divs[x].id != tab) {
				div.style.display = 'none'
				document.getElementById(divs[x].id+'_tab').className = ''
			}else{
				div.style.display = 'block'
				document.getElementById(tab+'_tab').className = 'active'
				document.getElementById(tab+'_starter').focus()
			}
		}
	}
	
}

function search_html_meta_description(){
	//Searches for similar domains by HTML meta description
	
	domain = document.getElementById("html_meta_description_starter").value
	
	//create the spinner row
	tbody = document.getElementById('html_meta_description_table').children[1]
	tbody.innerHTML = "<tr><td colspan='4' style='text-align:center;'><img src='/static/img/spinner.gif'></td></tr>"
	
	var xmlhttp;
	xmlhttp=new XMLHttpRequest()
	xmlhttp.onreadystatechange=function(){
		if (xmlhttp.readyState==4 && xmlhttp.status==200){
			resp = xmlhttp.responseText
			resp = JSON.parse(resp) //parse the json
			
			//remove the spinner row
			tbody.innerHTML = ""
			
			//enter the data
			for (var x in resp) {
				//get info from response
				url = resp[x].domain
				desc = resp[x].desc
				rank = resp[x].alexa_rank
				score = resp[x].score.toFixed(4)
				
				//shorten the description
				if (desc.length > 300) {
					desc = desc.substring(0, 300) + "..."
				}
				
				button = "<button class='btn adgroupsite' onclick='add_site'><span class='glyphicon glyphicon-plus' aria-hidden='true'></span> <span>"+url+"</span></button>"
				button.replace('add_site', 'add_site("' + url + '")')
				
				//construct the row
				data = "<tr>"
				data += "<td>" + button + "</td>"
				data += "<td>" + score + "</td>"
				data += "<td>" + rank + "</td>"
				data += "<td><span style='font-size:small;'>" + desc + "</span></td>"
				data += "</tr>"
				
				//append it to the data
				tbody.innerHTML += data
				
				//focus again on the enter box
				document.getElementById("html_meta_description_starter").focus()
			}
		}
	}
	xmlhttp.open("GET","/search_html_meta_description?domain=" + domain);
	xmlhttp.send();
}

function search_similarsites(){
	//Searches similarsites.com data
	
	domain = document.getElementById("similarsites_starter").value
	
	//create the spinner row
	tbody = document.getElementById('similarsites_table').children[1]
	tbody.innerHTML = "<tr><td colspan='3' style='text-align:center;'><img src='/static/img/spinner.gif'></td></tr>"
	
	var xmlhttp;
	xmlhttp=new XMLHttpRequest()
	xmlhttp.onreadystatechange=function(){
		if (xmlhttp.readyState==4 && xmlhttp.status==200){
			resp = xmlhttp.responseText
			resp = JSON.parse(resp) //parse the json
			tbody.innerHTML = "" //remove the spinner row
			for (var x in resp) { //enter the data
				//get info from response
				url = resp[x].url
				score = resp[x].score
				title = resp[x].title
				
				//shorten the title
				if (title.length > 300) {
					title = title.substring(0, 300) + "..."
				}
				
				button = "<button class='btn adgroupsite' onclick='add_site'><span class='glyphicon glyphicon-plus' aria-hidden='true'></span> "
				button += "<span>"+url+"</span></button>"
				button = button.replace('add_site', 'add_site("' + url + '", this.parentNode.parentNode)')
				
				console.log(button)
				
				//construct the row
				data = "<tr>"
				data += "<td>" + button + "</td>"
				data += "<td>" + score + "</td>"
				data += "<td>" + title + "</td>"
				data += "</tr>"
				
				//append it to the data
				tbody.innerHTML += data
				
				//focus again on the enter box
				document.getElementById("similarsites_starter").focus()
			}
		}
	}
	xmlhttp.open("GET","/search_similarsites?domain=" + domain);
	xmlhttp.send();
}

function enterkey(box_id) {
	//Closure work around to capture the enter key
	return function(e) {
		if (e.keyCode == 13) {
			window["search_" + box_id.replace("_starter", "")]()
		}
	}
}

function assign_enter_capture() {
	//Assigns an event to each input box, when the enter key is pressed
	var inputs = document.querySelectorAll(".domain_suggest") //find all the input boxes 
	for (var x in inputs){
		var box_id = inputs[x].id + "_starter"
		var box = document.getElementById(box_id) //now we have the correct input box
		if (box != undefined) { //(some weird glitch)
			box.addEventListener("keypress", enterkey(box_id))
		}
	}
}

function save_imported_data(){
	//Saves imported data
	
	//add to POST form
	//clear the boxes and hide the area
	//submit iframe
	//display success message
	
}

function process_import(){
	//Handles data importing (apart from the final submit)
	
	//what data
	raw_data = document.getElementById("importtext").value
	
	//is it valid
	data = clean_import_data(raw_data)
	if (data === false) {
		alert("There's something wrong with the data you tried to import")
	}
	
	//which adgroup
	adgroup = document.getElementById("which_adgroup").value
	if (value.indexOf("Select an")!=-1) {
		alert("Please select an adgroup to import into.\n\nIf you'd like to create a new adgroup altogether, please use the 'New Adgroup' link above first. ")
		return false
	}
	
	//shrink the text import field in half
	text_import_div = document.getElementById("text_import_div")
	text_import_div.className = 'col-md-6'
	
	//create a second div to the right
	var conf_div = document.createElement('div')
	conf_div.className = 'col-md-6'
	conf_div.id = "conf_div"
	insertAfter(conf_div, text_import_div)
	
	//create a button
	var submit_button = document.createElement("button")
	submit_button.className = "btn btn-primary"
	submit_button.innerHTML = "Looks good, save these to " + adgroup
	submit_button.addEventListener("click", function(){
		return function(){
			//set form data
			var field = document.getElementById("domain_data")
			var container = document.getElementById("sitelist")
			
			data = {
				'adgroup': adgroup,
				'sites': []
			}
			
			for (var x in container.children) {
				site = container.children[x].innerHTML
				data.sites.push(site)
			}
			
			field.value = JSON.stringify(data)
			
			//submit it
			var form = document.getElementById("data_transfer")
			form.submit()
		}
	})
	
	//create a list of domains
	
	
	
}

function clean_import_data(data){
	//Cleans up import data
	
	//replace commas and tab characters with spaces
	//tokenize into domains
	//check that each domain looks like a domain (at least a dot, strip http/s)
	//return as a list
	
}