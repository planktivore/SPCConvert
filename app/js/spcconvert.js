
$('.progress').fadeOut(1);

// Debouncer to throttle event triggers
function debouncer( func , timeout ) {
	var timeoutID , timeout = timeout || 200;
	return function () {
		var scope = this , args = arguments;
		clearTimeout( timeoutID );
		timeoutID = setTimeout( function () {
			func.apply( scope , Array.prototype.slice.call( args ) );
		} , timeout );
	}
};


function updateDetailImage(data) {

	if (!imageDetailActive)
		return;

	//var cameraIndex = camera.val();
	var siteURL = '';

	var base_url = siteURL+data.image_url;
	var image_url = base_url + image_ext;
	$('#TargetImg').attr("src",image_url);
	// Compute Image size from ImageDetail Container
	var aspectRatio = data.image_height/data.image_width;
	var heightScale = $('#ImageDetail').height()/data.image_height;
	var widthScale = $('#ImageDetail').width()/data.image_width;
	if (data.image_width*heightScale > 0.6*$('#ImageDetail').width()) {
		// Scale Image by width
		$('#TargetImg').width(0.6*$('#ImageDetail').width());
		$('#TargetImg').height(0.6*$('#ImageDetail').width()*aspectRatio);
	}
	else {
		$('#TargetImg').height(0.75*$('#ImageDetail').height());
		$('#TargetImg').width(0.75*$('#ImageDetail').height()/aspectRatio);

	}
	var scaleInfo = data.image_width*res;
	$('#ScaleBar').html(scaleInfo.toPrecision(3) + " mm");
	$('#ScaleBar').width($('#TargetImg').width());
	$('#ImageDetailTitle').html(image_url);

	// Info
	//console.log(data);
	$('#ImageName').html("<h5 class='info-label'>Image ID</h5>" + "<h4>" + data.image_id + "</h4>");
	$('#Timestamp').html("<h5 class='info-label'>Collection Datetime</h5>" + "<h4>" + data.image_timestamp + "</h4>");
	$('#MajorAxisLength').html("<h5 class='info-label'>Major Axis Length</h5>" + "<h4>" + (data.major_axis_length*res).toPrecision(3) + " mm</h4>");
	$('#MinorAxisLength').html("<h5 class='info-label'>Minor Axis Length</h5>" + "<h4>" + (data.minor_axis_length*res).toPrecision(3) + " mm</h4>");
	$('#AspectRatio').html("<h5 class='info-label'>Aspect Ratio </h5>" + "<h4>" + (data.aspect_ratio).toPrecision(3) + "</h4>");
	$('#Orientation').html("<h5 class='info-label'>Orientation </h5>" + "<h4>" + (data.orientation).toPrecision(3) + " degress</h4>");
};

function showImageDetail(data) {
	// Otherwise show image detail
	//var data = this.roi_data;
	siteURL = '';
	var base_url = siteURL+data.image_url;

	imagePostfixIndex = 0;
	imageDetailActive = true;
	updateDetailImage(data);
	$('#DownloadImage').on('click', data, function (event) {
		imagePostfixIndex = 3;
		var link = document.createElement('a');
		var image_url = siteURL + event.data.image_url + image_ext;
		//$('#TargetImg').attr("src",image_url);
		link.id = 'dnld_image';
		link.href = image_url;
		link.download = image_url;
		document.body.appendChild(link);
		link.click();
		document.body.removeChild(link);

	});
	$('#ShowImage').on('click', data, function (event) {
		imagePostfixIndex = 0;
		var image_url = siteURL + event.data.image_url + image_ext;
		$('#TargetImg').attr("src",image_url);
	});
	$('#ShowBinaryImage').on('click', data, function (event) {
		imagePostfixIndex = 1;
		var image_url = siteURL + event.data.image_url + '_binary.png';
		$('#TargetImg').attr("src",image_url);
	});
	$('#ShowRawColor').on('click', data, function (event) {
		imagePostfixIndex = 1;
		var image_url = siteURL + event.data.image_url + '_rawcolor' + image_ext;
		$('#TargetImg').attr("src",image_url);
	});
	/*$('#ShowBoundaryImage').on('click', data, function (event) {
		imagePostfixIndex = 2;
		var image_url = siteURL + event.data.image_url + imagePostfix[imagePostfixIndex];
		$('#TargetImg').attr("src",image_url);
	});*/
	// Add event listener for window
	$(window).resize(debouncer (function() { return updateDetailImage(data);}));
	//$(window).resize(function() { return updateDetailImage(data);});
	$('#ImageDetail').modal();

};

function buildImageMosaic(imageItems) {
    
    loadedCounter = 0;
    $('#loading-progress').removeClass('progress-bar-striped');
    $('#MosaicContainer').empty();
    
    
    for ( var i = 0; i < imageItems.length; i++ ) {
        var elem = getItemElement(imageItems[i]);
        $('#MosaicContainer').append(elem);
        loadedCounter++;
        //elem.style.backgroundImage = "url('"+img.src+"')";
        var pct = Math.floor(100*loadedCounter/imageItems.length);
        $('#loading-progress').width(pct.toString()+"%");
        if (loadedCounter >= imageItems.length) {
            $('#loading-progress').html('Finished');
            $('.progress').fadeOut(4000);
        }
        else {
            $('#loading-progress').html("Loaded "+loadedCounter.toString()+" of "+imageItems.length.toString()+" images");
        }
    }
    
    // create item element for each image
    function getItemElement(data) {
        var elem = document.createElement('div');
        image_ext = "." + data.url.split('.').slice(-1)[0];
        elem.style.backgroundImage = "url('"+data.url+"')";
        elem.className = 'image-item'
        elem.style.width = data.width.toString()+"px";
        elem.style.height = data.height.toString()+"px";
        elem.data = data;
        return elem;
    };
    
    // Delegate mouse click event to image items
    $('.image-item').on('click', function(e) {

        imageData = this.data;
        imageData.image_url = this.data.url.replace(/\.[^/.]+$/, ""); // remove extension
        imageData.image_id = imageData.image_url.split("/").slice(-1)[0]
        imageData.image_width = this.data.width;
        imageData.image_height = this.data.height;
        imageData.major_axis_length = this.data.major_axis_length;
        imageData.minor_axis_length = this.data.minor_axis_length;
        imageData.aspect_ratio = this.data.aspect_ratio;
        imageData.orientation = this.data.orientation;
        imageData.clipped_fraction = this.data.clipped_fraction;
        imageData.image_timestamp = this.data.timestring;

        // Otherwise show image detail
        showImageDetail(imageData);


    });

    // Delegate mouse enter event to image items
    $('.image-item').on('mouseenter', function(){

        var majLen = this.data.major_axis_length.toString()*res;
        var minLen = this.data.minor_axis_length.toString()*res;
        var text = this.data.timestring + ", Major Length: " + majLen.toPrecision(3) + " mm, Minor Length: " + minLen.toPrecision(3) + " mm";
        $('#info-text').html('Image Info: ');
        $('#status-text').html(text);

    });

    $('.image-item').on('mouseexit', function(){

        $('#status-text').html('');

    });
    
}

function updateMosaicImages(query) {
    
    $('#loading-progress').width("100%");
    $('#loading-progress').html('Querying Images...');
    $('#loading-progress').addClass('progress-bar-striped');
    $('#loading-progress').toggleClass('progress-bar-danger progress-bar-primary');
    
    imageItems = [];
    
    $('.progress').fadeIn(250,function () {
    
        if (typeof query['preset'] != 'undefined') {
            if (query['preset'] == 'reallybig') {
                imageItems = roistore({major_axis_length:{gt:90}}).order("height desc").get();
            }
            else if (query['preset'] == 'big') {
                imageItems = roistore({major_axis_length:{gt:45}}).order("height desc").get();
            }
            else if (query['preset'] == 'small') {
                imageItems = roistore({major_axis_length:{lt:45}}).order("height desc").get();
            }
            else if (query['preset'] == 'verysmall') {
                imageItems = roistore({major_axis_length:{lt:22}}).order("height desc").get();
            }
            else if (query['preset'] == 'long') {
                imageItems = roistore({aspect_ratio:{gt:0.0,lt:0.1}}).order("height desc").get();
            }
            else if (query['preset'] == 'round') {
                imageItems = roistore({aspect_ratio:{gt:0.8,lt:1.0}}).order("height desc").get();
            }
            $('#loading-progress').html('Building Mosaic...');
            $('#loading-progress').removeClass('progress-bar-striped');
            $('#loading-progress').toggleClass('progress-bar-danger progress-bar-primary');
            buildImageMosaic(imageItems);
        }
        else {
            $('#loading-progress').html('Query Error, Aborted.');
            $('#loading-progress').addClass('progress-bar-danger');
            $('.progress').fadeOut(4000);
        }
    });
    
}

$('#ImageDetail').on('hide.bs.modal', function (e) {
    imageDetailActive = false;
    /*$('#ShowBoundaryImage').unbind();*/
    $('#ShowBinaryImage').unbind();
    $('#ShowImage').unbind();
    $('#DownloadImage').unbind();
});


// hide status when done
$( document ).ready(function() {
    
  $('#tabs').removeClass('collapse');
  //$('.progress').addClass('collapse');
  updateMosaicImages({preset:'reallybig'});
});
