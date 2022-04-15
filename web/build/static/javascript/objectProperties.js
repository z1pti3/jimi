var panelPropertiesHTML = `
<div class="propertiesPanel theme-panelContainer">
	<div class="container-fluid propertiesPanel-header theme-panelHeader">
		<span class="glyphicon glyphicon glyphicon-remove" id="close"></span>
		<label id="title"></label>
	</div>
	<div class="propertiesPanel-main">
		<ul class="nav nav-tabs">
			<li class="nav-item">
				<a class="nav-link active" id="properties-tab" href="#" data-bs-toggle="tab" data-bs-target="#properties" role="tab" aria-controls="access" aria-selected="false">Properties</a>
			</li>
			<li class="nav-item">
				<a class="nav-link" id="help-tab" href="#" data-bs-toggle="tab" data-bs-target="#help" role="tab" aria-controls="access" aria-selected="false">Help</a>
			</li>
		</ul>
		<div class="tab-content text-left" id="myTabContent">
			<div class="tab-pane show active" id="properties" role="tabpanel" aria-labelledby="properties-tab">
				<div class="container-fluid propertiesPanel-body theme-panelBody">
				</div>
			</div>
			<div class="tab-pane" id="help" role="tabpanel" aria-labelledby="help-tab">
				<div class="propertiesPanel-help">
				</div>
			</div>
		</div>
	</div>
	<div id="unlinkDiv" class="container-fluid propertiesPanel-footer theme-panelFooter pb-5 hide">
		<button id="unlink" class="btn btn-primary button bi-exclude"> Unlink</button>
	</div>
	<div class="container-fluid propertiesPanel-footer theme-panelFooter">
		<button id="save" class="btn btn-primary button bi-save"> Save</button>
		<button id="refresh" class="btn btn-primary button bi-recycle"> Refresh</button>
		<button id="close" class="btn btn-primary button">Close</button>
	</div>
</div>
`

var openPanels = {}

$(document).ready(function () {
	$(window).bind("keydown", function (event) { 
		if (event.ctrlKey || event.metaKey) {
			switch (String.fromCharCode(event.which).toLowerCase()) {
			case 's':
				event.preventDefault();
				if (selectedObject != null)
				{
					if (selectedObject[0] == "objectProperties") {
						savePropertiesPanel(selectedObject[1]["flowID"],selectedObject[1]["panel"]);
					}
				}
				break;
			}
		} else if (event.keyCode == 27) {
			if (selectedObject != null) {
				if (selectedObject[0] == "objectProperties") {
					delete openPanels[selectedObject[1]["flowID"]];
					selectedObject[1]["panel"].remove();
				}
			}
		}
	})
});

function savePropertiesPanel(flowID,panel) {
	var conductID = GetURLParameter("conductID")
	var modelType = nodes.get(flowID)["flowType"]
	var modelID = nodes.get(flowID)["objID"]

	var newName = null;
	var jsonData = getForm(panel);
	if (!jsonData) {
		return;
	}
	if (jsonData.hasOwnProperty("name")) {
		newName = jsonData["name"];
	}
	// Posting
	jsonData["CSRF"] = CSRF;
	$.ajax({url:"/api/1.0/models/"+modelType+"/"+modelID+"/", type:"POST", data: JSON.stringify(jsonData), contentType:"application/json", success: function ( result ) {
			// Telling UI it has had some changes made
			if (newName) {
				postData = { "action": "update" }
				if (newName) {
					postData["title"] = newName
				}
				postData["CSRF"] = CSRF
				$.ajax({url:"/conductEditor/"+conductID+"/flow/"+flowID+"/", type:"POST", async: false, data: JSON.stringify(postData), contentType:"application/json", success: function( responseData ) {
						dropdownAlert(panel,"success","Save Successful",1000);
						loadPropertiesPanel(flowID,panel);
					},
					error: function (result) {
						dropdownAlert(panel,"error","Save Failed!",1000);
					}
				});
			} else {
				dropdownAlert(panel,"success","Save Successful",1000);
				loadPropertiesPanel(flowID,panel);
			}
		},
		error: function (result) {
			dropdownAlert(panel,"error","Save Failed!",1000);
		}
	});
}

function loadPropertiesPanel(flowID,panel,init=false) {
	// Building properties form
	var conductID = GetURLParameter("conductID")
	panel.find(".propertiesPanel-body").empty();
	panel.find(".propertiesPanel-help").empty();
	panel.find("#title").text(nodes.get(flowID)["name"]);
	$.ajax({ url: "/conduct/"+conductID+"/flowProperties/"+flowID+"/", type:"GET", success: function ( result ) {
			// help
			if (Object.keys(result["manifest"]).length > 0)
			{
				var help = panel.find(".propertiesPanel-help");
				var title = $('<label id="propertiesPanel-help-title">').text(result["manifest"]["display_name"]);
				help.append(title).append($('<hr>'));
				var description = $('<label id="propertiesPanel-help-description">').text(result["manifest"]["description"]);
				help.append(description).append($('<br>'));
				help.append($('<label id="propertiesPanel-help-Input">').text("Input:")).append($('<br>'));
				var $table = $('<table class="propertiesPanel-help-table">');
				$table.append($('<tr class="propertiesPanel-help-table-header">').append('<td><label>Name</label></td><td><label>Description</label></td><td><label>Type</label></td><td><label>Required</label></td><td><label>Syntax</label></td>'))
				for (field in  result["manifest"]["fields"]) {
					var $row = $('<tr class="propertiesPanel-help-table-content">');
					var $cell = $('<td>');
					$cell.append($('<label>').text(result["manifest"]["fields"][field]["label"]))
					$row.append($cell);
					var $cell = $('<td>');
					$cell.append($('<label>').text(result["manifest"]["fields"][field]["description"]))
					$row.append($cell);
					var $cell = $('<td class="center">');
					$cell.append($('<label>').text(result["manifest"]["fields"][field]["type"]))
					$row.append($cell);
					var $cell = $('<td class="center">');
					$cell.append($('<label>').text(result["manifest"]["fields"][field]["required"]))
					$row.append($cell);
					var $cell = $('<td class="center">');
					$cell.append($('<label>').text(result["manifest"]["fields"][field]["jimi_syntax"]))
					$row.append($cell);
					$table.append($row);
				}
				help.append($table).append($('<br>'));
				help.append($('<label id="propertiesPanel-help-Output">').text("Output:")).append($('<br>'));
				var $table = $('<table class="propertiesPanel-help-table">');
				$table.append($('<tr class="propertiesPanel-help-table-header">').append('<td><label>Name</label></td><td><label>Description</label></td><td><label>Type</label></td><td><label>Always Present</label></td><td><label>values</label></td>'))
				for (field in  result["manifest"]["data_out"]) {
					var $row = $('<tr class="propertiesPanel-help-table-content">');
					var $cell = $('<td>');
					$cell.append($('<label>').text(field))
					$row.append($cell);
					var $cell = $('<td>');
					$cell.append($('<label>').text(result["manifest"]["data_out"][field]["description"]))
					$row.append($cell);
					var $cell = $('<td class="center">');
					$cell.append($('<label>').text(result["manifest"]["data_out"][field]["type"]))
					$row.append($cell);
					var $cell = $('<td class="center">');
					$cell.append($('<label>').text(result["manifest"]["data_out"][field]["always_present"]))
					$row.append($cell);
					var $cell = $('<td>');
					var $valuesTable = $('<table class="propertiesPanel-help-table">');
					$valuesTable.append($('<tr class="propertiesPanel-help-table-header">').append('<td><label>Value</label></td><td><label>Description</label></td>'))
					for (value in  result["manifest"]["data_out"][field]["values"]) {
						var $valuesTableRow = $('<tr class="propertiesPanel-help-table-content">');
						var $valuesTableCell = $('<td>');
						$valuesTableCell.append($('<label>').text(value))
						$valuesTableRow.append($valuesTableCell);
						var $valuesTableCell = $('<td>');
						$valuesTableCell.append($('<label>').text(result["manifest"]["data_out"][field]["values"][value]["description"]))
						$valuesTableRow.append($valuesTableCell);
						$valuesTable.append($valuesTableRow)
					}
					$cell.append($valuesTable)
					$row.append($cell);
					$table.append($row);
				}
				help.append($table).append($('<br>'));
			}
		
			// formData
			panel.find(".propertiesPanel-body").append(buildForm(result["formData"]));

			if (result["whereUsed"].length > 1) {
				panel.find("#unlinkDiv").removeClass("hide");
				panel.find("#save").html("Save ("+result["whereUsed"].length+")");
			} else {
				panel.find("#unlinkDiv").addClass("hide");
				panel.find("#save").html("Save");
			}

			// Added to fix a bug whereby the property table scroll bar does not appear
			panel.height(panel.height());

			// Set Initial Position
			if (init) {
				height = $("#flowchart").height();
				width = $("#flowchart").width();
				// Checking for offset on conductEditor
				try {  
					offsetTop = $(".conductEditor-topBar").offset().top;
				} catch(error) {  
					offsetTop = 0; 
				}
				var posX = (width/2) - (panel.width()/2);
				var posY = (height/2) - (panel.height()/2) + offsetTop;
				panel.css({top : posY, left : posX});
			}

			$(".searchSelect").select2({tags:true});
		}
	});
}

function unlinkObject(flowID,panel) { 
	var conductID = GetURLParameter("conductID")
	jsonData = { action: "unlink", operatorId: flowID, CSRF: CSRF }
	$.ajax({url:"/conductEditor/"+conductID+"/flow/"+flowID+"/", type:"POST", data: JSON.stringify(jsonData), contentType:"application/json", success: function ( result ) {
			nodes.get(flowID)["objID"] = result["objectID"]
			loadPropertiesPanel(flowID,panel);
		}
	});
}

function createPropertiesPanel(flowID) {
	if (!openPanels.hasOwnProperty(flowID)) {
		openPanels[flowID] = flowID;
		var panel = $(panelPropertiesHTML);
		panel.draggable({
			handle: ".propertiesPanel-header",
			start: function(e, ui) {
				if (selectedObject != null)
				{
					if (selectedObject[1].hasOwnProperty("deselect")) {
						selectedObject[1]["deselect"]()
					}
				}
				$('.ui-main').find(".propertiesPanel").css("z-index", 1);
				panel.find(".propertiesPanel-header").addClass("theme-panelHeader-Active");
				panel.css("z-index", 2);
				selectedObject = ["objectProperties",{"panel" : panel, "flowID" : flowID, "deselect" :function(){ panel.find(".propertiesPanel-header").removeClass("theme-panelHeader-Active"); }}]
			}
		});
		panel.resizable({
			grid: 20
		});

		// Select the new panel
		$('.ui-main').find(".propertiesPanel").css("z-index", 1);
		panel.find(".propertiesPanel-header").addClass("theme-panelHeader-Active");
		selectedObject = ["objectProperties",{"panel" : panel, "flowID" : flowID, "deselect" :function(){ panel.find(".propertiesPanel-header").removeClass("theme-panelHeader-Active"); }}]

		// Events
		panel.click(function () {
			if (selectedObject != null)
			{
				if (selectedObject[1].hasOwnProperty("deselect")) {
					selectedObject[1]["deselect"]()
				}
			}
			$('.ui-main').find(".propertiesPanel").css("z-index", 1);
			panel.find(".propertiesPanel-header").addClass("theme-panelHeader-Active");
			panel.css("z-index", 2);
			selectedObject = ["objectProperties",{"panel" : panel, "flowID" : flowID, "deselect" : function(){ panel.find(".propertiesPanel-header").removeClass("theme-panelHeader-Active"); }}]
		})

		// Toggle fullscreen when double click on title bar
		panel.find(".propertiesPanel-header").dblclick(function() {
			if (panel.data("fullscreen")) {
				// Restore position
				panel.css("top",panel.data("fullscreen")["top"])
				panel.css("left",panel.data("fullscreen")["left"])
				panel.css("height",panel.data("fullscreen")["height"])
				panel.css("width",panel.data("fullscreen")["width"])
				panel.data("fullscreen",null)
			} else {
				// Save current position and size
				fullscreenData = { "top" : panel.css("top"), "left" : panel.css("left"), "height" : panel.css("height"), "width" : panel.css("width") }
				panel.data("fullscreen",fullscreenData)
				// Set fullscreen
				panel.css("top",0)
				panel.css("left",0)
				panel.css("height","100%")
				panel.css("width","100%")
				// Center panel based on max 80% size
				height = $("#flowchart").height();
				width = $("#flowchart").width();
				// Checking for offset on conductEditor
				try {  
					offsetTop = $(".conductEditor-topBar").offset().top;
				} catch(error) {  
					offsetTop = 0; 
				}
				var posX = (width/2) - (panel.width()/2);
				var posY = (height/2) - (panel.height()/2) + offsetTop;
				panel.css({top : posY, left : posX});
			}
		})

		panel.find("#close").click(function () { 
			delete openPanels[flowID];
			panel.remove();
		})

		panel.find("#save").click(function () { 
			savePropertiesPanel(flowID,panel);
		})

		panel.find("#refresh").click(function () { 
			loadPropertiesPanel(flowID,panel);
		})

		panel.find("#unlink").click(function () { 
			unlinkObject(flowID,panel);
		})

		// Loading properties form
		loadPropertiesPanel(flowID,panel,true);
	
		// Applying object to UI
		$('.ui-main').append(panel);
	}
}

