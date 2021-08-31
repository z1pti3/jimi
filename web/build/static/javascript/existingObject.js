var existingObjectHTML = `
<div class="propertiesPanel theme-panelContainer">
	<div class="container-fluid propertiesPanel-header theme-panelHeader">
		<span class="glyphicon glyphicon glyphicon-remove" id="close"></span>
		<label id="title">Insert Existing Object</label>
	</div>
	<div class="container-fluid propertiesPanel-body theme-panelBody">
		<input type='text' class="form-control form-control-sm full-width textbox" id='existingPropertiesPanel-SearchInput'>
		<div class="existingPropertiesPanel-SearchResults" id="existingPropertiesPanel-SearchResults">
		</div>
	</div>
	<div class="container-fluid propertiesPanel-footer theme-panelFooter">
		<button id="close" class="btn btn-primary button">Close</button>
	</div>
</div>
`

var openExistingPanels = {}

function loadExistingObjectPanel(panel) {
	panel.find("#existingPropertiesPanel-SearchResults").empty();
	$.ajax({url:"/conductEditor/existingObjects/triggers/", type:"GET", success: function ( result ) {
			for ( resultItem in result["results"] ) {
				var $div = $('<div class="draggable_operator ui-draggable ui-draggable-handle ListName">');
				$div.attr("data-name",result["results"][resultItem]["name"])
				$div.attr("data-id",result["results"][resultItem]["_id"])
				$div.attr("id",result["results"][resultItem]["_id"])
				var $row = $('<tr>');
				var $cell = $('<td width="100px">');
				var $b = $('<b>');
				$b.text(result["results"][resultItem]["name"])
				$cell.append($b)
				$cell.append("</br>")
				$cell.append($('<id>').text(result["results"][resultItem]["_id"]))
				$cell.append("</br>")
				$row.append($cell);
				$div.append($row)
				panel.find("#existingPropertiesPanel-SearchResults").append($div);
				// Make draggableOperators
				$div.dblclick(function(e){
					pos = network.getViewPosition()
					var x = pos["x"]
					var y = pos["y"]
					var conductID = GetURLParameter("conductID")
					var $this = $(this);
					$.ajax({url:"/conductEditor/"+conductID+"/flow/", type:"POST", data:JSON.stringify({action: "drop", flowType: "trigger", _id: $this.attr("id"), x: x, y: y, CSRF: CSRF}), contentType:"application/json", success: function ( result ) {
						// Drop sucessfull
						}
					});
				})
			}
		}
	});
	$.ajax({url:"/conductEditor/existingObjects/actions/", type:"GET", success: function ( result ) {
			for ( resultItem in result["results"] ) {
				var $div = $('<div class="draggable_operator ui-draggable ui-draggable-handle ListName">');
				$div.attr("data-name",result["results"][resultItem]["name"])
				$div.attr("data-id",result["results"][resultItem]["_id"])
				$div.attr("id",result["results"][resultItem]["_id"])
				var $row = $('<tr>');
				var $cell = $('<td width="100px">');
				var $b = $('<b>');
				$b.text(result["results"][resultItem]["name"])
				$cell.append($b)
				$cell.append("</br>")
				$cell.append($('<id>').text(result["results"][resultItem]["_id"]))
				$cell.append("</br>")
				$row.append($cell);
				$div.append($row)
				panel.find("#existingPropertiesPanel-SearchResults").append($div);
				// Make draggableOperators
				$div.dblclick(function(e){
					pos = network.getViewPosition()
					var x = pos["x"]
					var y = pos["y"]
					var conductID = GetURLParameter("conductID")
					var $this = $(this);
					$.ajax({url:"/conductEditor/"+conductID+"/flow/", type:"POST", data:JSON.stringify({action: "drop", flowType: "action", _id: $this.attr("id"), x: x, y: y, CSRF: CSRF}), contentType:"application/json", success: function ( result ) {
						// Drop sucessfull
						}
					});
				})
			}
		}
	});
	// Searchable
	panel.find("#existingPropertiesPanel-SearchInput").keyup(function(){
		var search = $(this).val();
		var regex = new RegExp('\\b\\w*' + search + '\\w*\\b');
		$('.ListName').hide().filter(function () {
			var nr = regex.test($(this).data('name'));
			var ir = regex.test($(this).data('id'));
			if (ir || nr) {
				return true;
			}
			return false;
		}).show();
	});
}

function createExistingObjectPanel() {
	if (!openExistingPanels.hasOwnProperty("create")) {
		openExistingPanels["existing"] = "existing";
		var e = window.event;
		var posX = e.clientX;
		var posY = e.clientY;
		var panel = $(existingObjectHTML);
		panel.css({top : posY, left : posX - 250});
		panel.draggable({handle: ".propertiesPanel-header",});
		panel.resizable({
			grid: 20
		});

		// Events
		panel.click(function () {
			$('.ui-main').find(".propertiesPanel").css("z-index", 1);
			$(this).css("z-index", 2);
		})

		panel.find("#close").click(function () { 
			delete openExistingPanels["existing"];
			panel.remove();
		})

		// Loading properties form
		loadExistingObjectPanel(panel);

		// Applying object to UI
		$('.ui-main').append(panel);
	}
}

