var markersArray = [];
google.maps.Map.prototype.clearOverlays = function(){
	// add clearOverlays to the map prototype
	// clears all the markers from the map
	for (var i = 0; i < markersArray.length; i++){
		markersArray[i].setMap(null);
/* 		markersArray.eq(i).setMap(null); */
	}
	
	console.log(markersArray)
}
function placeMarker(location){
	var marker = new google.maps.Marker({
		position : location,
		map : map
	})
	// add the new marker to the global array of existing markers
	markersArray.push(marker)
	// add click event listener to the marker
	return marker;
}

function attachOverlay(marker, content) {
  // closure for attaching content to a marker
  var infowindow = new google.maps.InfoWindow(
      { content: content,
        size: new google.maps.Size(50,50)
      });
  google.maps.event.addListener(marker, 'click', function() {
    infowindow.open(map,marker);
  });
}
var r; // debug
function doSearchResponse(response){
	var results = response.results;
	var loggedIn = response.logged_in;
	r = results; // debug

	
	if (results.length == 0){
		$("#noresults").show()
	}else{
		$("#noresults").hide()
		var bounds = new google.maps.LatLngBounds();
		for (var i=0;i<results.length;i++){
			obit = results[i]
			// extract the obituary location
			var geoPoint = obit.geo_point;
			var lat = geoPoint.lat;
			var lon = geoPoint.lon;
			var location = new google.maps.LatLng(lat,lon);
			// add the marker to the map
			marker = placeMarker(location);
			// add the location to the bounds calculator
			bounds.extend(location);
			// attach the overlay to the marker
			content = '<div class="overlay-container">';
			if (obit.photo_urls.length > 0){
				content += '<img class="photo_thumb img-rounded" src="'+obit.photo_urls[0]+'" />';
			}
			content += '<p class="obit-name lead">'+obit.name+'</p>';
			if (obit.dob != ''){
				content += '<p class="obit-name">Born on '+obit.dob+'</p>';
			}
			
			if (obit.dod != ''){
				content += '<p class="obit-name">Passed away on '+obit.dod+'</p>';
			}
			
			content += '<a class="btn btn-info btn-block" href="'+obit.obituary_url+'">View Details</a></div>';
			attachOverlay(marker,content);
		}
		
		// Set minimum zoom on fitBounds
		google.maps.event.addListener(map, 'zoom_changed', function() {
			zoomChangeBoundsListener = google.maps.event.addListener(map, 'bounds_changed', function(event) {
				if (this.getZoom() > 15 && this.searchZoom == true) {
					// Change max/min zoom here
							this.setZoom(15);
							this.initialZoom = false;
						}
					google.maps.event.removeListener(zoomChangeBoundsListener);
				});
			});
		// set flag for zoom_changed because of search result
		map.searchZoom = true;
		// fit bounds to the markers
		map.fitBounds(bounds);
	}
}
function doSearch(lat,lon){
	base_url = '/search'
	var deceased_name = $('#deceased_name').val()
	var pob = $('#pob').val()
	var pod = $('#pod').val()
	var dob = $('#dob').val()
	var dod = $('#dod').val()

	console.log(lat)
	console.log(lon)
	
	base_url += '?name='+deceased_name
	base_url += '&pob='+pob
	base_url += '&pod='+pod
	base_url += '&dob='+dob
	base_url += '&dod='+dod

	if (lat && lon){
		base_url += '&lat='+lat
		base_url += '&lon='+lon
	}
	
	// add the oid
	base_url += '&oid='+$('#oid').val();
	
	url = base_url
	console.log(base_url)
	d = {}
	$.getJSON(url,function(data){
		d = data;
		console.log(data)
		var status_code = data.status.code
		var response = data.response
		if (status_code == 200){
			// successful search
			console.log('success!');
			// clear all the existing searches
			map.clearOverlays();
			// add all the new responses
			doSearchResponse(response);
		}else if(status_code == 400){
			// invalid input
			invalidID = '#'+response.invalid_input;
			$(invalidID).parent().addClass('error')
		}else if(status_code == 500){
			// uh oh. server error
			console.error('UH OH. SERVER ERROR')
			console.log(data)
		}
		
	})
	
}

function showAll(){
	$("#deceased_name,#dob,#dod,#pob,#pod,#oid").val("");
	$("#searchForm").submit()
}

function nearMe(){
	$("#deceased_name,#dob,#dod,#pob,#pod,#oid").val("");
	crd = map.getCenter();
		        
    $("#lat").val(crd.lat());
	$("#lon").val(crd.lng());
	// $("#searchForm").submit()
	doSearch(crd.lat(),crd.lng())
}

$(document).on("ready",function() { 
	// initial search
	$("#oid").val(oid);
	$("#searchForm").submit();
	$("#oid").val("");

	$("#nearme").click(function(e){
        e.preventDefault()
        nearMe()
	})
	
	$("#showall").click(function(e){
		e.preventDefault()
		showAll()
	})
	
})
