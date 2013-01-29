var markersArray = [];
google.maps.Map.prototype.clearOverlays = function(){
	// add clearOverlays to the map prototype
	// clears all the markers from the map
	for (var i = 0; i < markersArray.length; i++){
		markersArray[i].setMap(null);
	}
}
function placeMarker(lat,lon){
	var location = new google.maps.LatLng(lat,lon);
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
	for (var i=0;i<results.length;i++){
		obit = results[i]
		// extract the obituary location
		var geoPoint = obit.geo_point;
		var lat = geoPoint.lat;
		var lon = geoPoint.lon;
		// add the marker to the map
		marker = placeMarker(lat,lon);
		// attach the overlay to the marker
		content = '<div class="overlay-container">';
		content += '<p>'+obit.name+'</p>';
		content += '<a href="'+obit.obituary_url+'">Full Info</a></div>';
		attachOverlay(marker,content);
	}
}
function doSearch(lat,lon){
	base_url = '/search'
	var deceased_name = $('#deceased_name').val()
	var pob = $('#pob').val()
	var pod = $('#pod').val()
	var dob = $('#dob').val()
	var dod = $('#dod').val()
	
	base_url += '?name='+deceased_name
	base_url += '&pob='+pob
	base_url += '&pod='+pod
	base_url += '&dob='+dob
	base_url += '&dod='+dod
	
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
