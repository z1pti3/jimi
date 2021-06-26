var panelPropertiesHTML = `
<div class="propertiesPanel theme-panelContainer">
	<div class="container-fluid propertiesPanel-header theme-panelHeader">
		<span class="glyphicon glyphicon glyphicon-remove" id="close"></span>
		<label id="title"></label>
	</div>
	<div class="propertiesPanel-main">
		<div class="container-fluid propertiesPanel-body theme-panelBody">
		</div>
		<div class="propertiesPanel-help">
		</div>
	</div>
	<div class="container-fluid propertiesPanel-footer theme-panelFooter">
		<button id="save" class="btn btn-primary button bi-save"> Save</button>
		<button id="refresh" class="btn btn-primary button bi-recycle"> Refresh</button>
		<button id="close" class="btn btn-primary button">Close</button>
		<button id="help" class="btn btn-primary button bi-question-lg"> Show Help</button>
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
			if (selectedObject != null)
			{
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
	var modelType = flowObjects[flowID]["flowType"]
	var modelID = flowObjects[flowID]["_id"]

	var jsonData = {};
	var newName = null;
	var requiredMet = true;
	panel.find("[tag=formItem]").each(function() {
		formItem = $(this)
		resultItem = $(this).attr("key")
		if (formItem.attr("type") == "text")
		{
			if (formItem.attr("required") && formItem.val() == "") {
				dropdownAlert(panel,"warning","Don't forget the required fields!",1000);
				requiredMet = false;
			}
			if (formItem.attr("current") != formItem.val()) {
				if (resultItem == "name") {
					newName = formItem.val();
				}
				jsonData[resultItem] = formItem.val();
			}
		}
		if (formItem.attr("type") == "checkbox")
		{
			if (String(formItem.attr("current")) != String(formItem.is(":checked"))) {
				jsonData[resultItem] = formItem.is(":checked");
			}
		}
		if (formItem.attr("type") == "dropdown")
		{
			jsonData[resultItem] = formItem.val();
		}
	})
	if (!requiredMet) {
		return;
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
	panel.find("#title").text(flowObjects[flowID]["name"]);
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
			var groups = {}
			var $table = $('<table width="100%">');
			for (objectItem in result["formData"]) {
				var $row = $('<tr>');
				// Tooltips
				var tooltip = "";
				if (result["formData"][objectItem].hasOwnProperty("tooltip")) {
					tooltip = result["formData"][objectItem]["tooltip"]
				}
				// Custom Label
				var label = result["formData"][objectItem]["schemaitem"]
				if (result["formData"][objectItem].hasOwnProperty("label")) {
					label = result["formData"][objectItem]["label"]
				}

				// Required
				var required = false;
				if (result["formData"][objectItem].hasOwnProperty("required")) {
					required = result["formData"][objectItem]["required"]
					if (required) {
						label = label+"*";
					}
				}

				// Group
				var group = 0;
				if (result["formData"][objectItem].hasOwnProperty("group")) {
					group = result["formData"][objectItem]["group"]
				}
				
				if (result["formData"][objectItem]["type"] == "group-checkbox") {
					var $cell = $('<td width="100px">');
					$cell.append($('<label>').attr({for: result["formData"][objectItem]["schemaitem"], "data-bs-toggle" : "tooltip", title : tooltip, class: "theme-panelLabel"}).text(label+":"));
					$row.append($cell);
					var $cell = $('<td>');
					if (result["formData"][objectItem]["checked"] == true) {
						$cell.append($('<input class="theme-panelCheckbox">').attr({type: 'checkbox', required: required, id: "properties_items"+result["formData"][objectItem]["schemaitem"], current: true, checked: true, key: result["formData"][objectItem]["schemaitem"], tag: "formItem", "data-group" : group.toString()}));
					}
					else {
						$cell.append($('<input class="theme-panelCheckbox">').attr({type: 'checkbox', required: required, id: "properties_items"+result["formData"][objectItem]["schemaitem"], current: false, key: result["formData"][objectItem]["schemaitem"], tag: "formItem", "data-group" : group.toString()}));
					}
					$cell.find("#properties_items"+result["formData"][objectItem]["schemaitem"]).on('change', function() {
						if ($(this)[0].checked) {
							$(".group_"+$(this).attr("data-group")).removeClass("hide")
						} else {
							$(".group_"+$(this).attr("data-group")).addClass("hide")
						}
					});
					groups[group.toString()] = result["formData"][objectItem]["checked"];
					$row.append($cell);
				}
				if (result["formData"][objectItem]["type"] == "input") {
					var $cell = $('<td width="100px">');
					$cell.append($('<label>').attr({for: result["formData"][objectItem]["schemaitem"], "data-bs-toggle" : "tooltip", title : tooltip, class: "theme-panelLabel"}).text(label+":"));
					$row.append($cell);
					var $cell = $('<td>');
					$cell.append($('<input class="form-control form-control-sm full-width textbox">').attr({type: 'text', value: result["formData"][objectItem]["textbox"], current: result["formData"][objectItem]["textbox"], required: required, id: "properties_items"+result["formData"][objectItem]["schemaitem"], key: result["formData"][objectItem]["schemaitem"], tag: "formItem"}));
					$row.append($cell);
				}
				if (result["formData"][objectItem]["type"] == "checkbox") {
					var $cell = $('<td width="100px">');
					$cell.append($('<label>').attr({for: result["formData"][objectItem]["schemaitem"], "data-bs-toggle" : "tooltip", title : tooltip, class: "theme-panelLabel"}).text(label+":"));
					$row.append($cell);
					var $cell = $('<td>');
					if (result["formData"][objectItem]["checked"] == true) {
						$cell.append($('<input class="theme-panelCheckbox">').attr({type: 'checkbox', required: required, id: "properties_items"+result["formData"][objectItem]["schemaitem"], current: true, checked: true, key: result["formData"][objectItem]["schemaitem"], tag: "formItem"}));
					}
					else {
						$cell.append($('<input class="theme-panelCheckbox">').attr({type: 'checkbox', required: required, id: "properties_items"+result["formData"][objectItem]["schemaitem"], current: false, key: result["formData"][objectItem]["schemaitem"], tag: "formItem"}));
					}
					$row.append($cell);
				}
				if (result["formData"][objectItem]["type"] == "json-input") {
					// output
					// <label for="delay" class="theme-panelLabel">delay:</label>					
					var $cell = $('<td width="100px">');
					$cell.append($('<label>').attr({for: result["formData"][objectItem]["schemaitem"], "data-bs-toggle" : "tooltip", title : tooltip, class: "theme-panelLabel"}).text(label+":"));
					$row.append($cell);

					// output
					// <textarea class="inputFullWidth theme-panelTextArea" type="text" id="properties_itemsdelay" current="0" key="delay" tag="formItem"></textarea>
					var $cell = $('<td>');
					$cell.append($('<textarea class="form-control form-control-sm full-width textbox">').attr({type: 'text', required: required, id: "properties_items"+result["formData"][objectItem]["schemaitem"], current: JSON.stringify(result["formData"][objectItem]["textbox"]), key: result["formData"][objectItem]["schemaitem"], tag: "formItem"}));
					$cell.find('#properties_items'+result["formData"][objectItem]["schemaitem"]).val(JSON.stringify(result["formData"][objectItem]["textbox"]));
					$row.append($cell);
				}
				if (result["formData"][objectItem]["type"] == "dropdown") {
          
					var $cell = $('<td width="100px">');
					$cell.append($('<label>').attr({for: result["formData"][objectItem]["schemaitem"], class: "theme-panelLabel"}).text(label+":"));
					$row.append($cell);

					var $cell = $('<td>');
					var $select =$('<select class="inputFullWidth theme-panelTextArea">').attr({type: 'dropdown', required: required, id: "properties_items"+result["formData"][objectItem]["schemaitem"], current: JSON.stringify(result["formData"][objectItem]["dropdown"]), key: result["formData"][objectItem]["schemaitem"], tag: "formItem"});
					
          			for (var i=0; i< result["formData"][objectItem]["dropdown"].length;i++){
						$select.append($('<option>').attr({value: result["formData"][objectItem]["dropdown"][i]}).text(result["formData"][objectItem]["dropdown"][i]));
					}
					$select.val(result["formData"][objectItem]["current"])
					// console.log(result["formData"][objectItem]["dropdown"].length)
					// console.log(result["formData"][objectItem]["dropdown"])
					
					$cell.append($select);
					$row.append($cell);
					
				}
				if (result["formData"][objectItem]["type"] == "unit-input") {
          
					var $cell = $('<td width="100px">');
					$cell.append($('<label>').attr({for: result["formData"][objectItem]["schemaitem"], class: "theme-panelLabel"}).text(label+":"));
					$row.append($cell);

					var $cell = $('<td>');
					$cell.append($('<input class="inputFullWidth theme-panelTextbox-34">').attr({type: 'text', value: result["formData"][objectItem]["textbox"], current: result["formData"][objectItem]["textbox"], required: required, id: "properties_items"+result["formData"][objectItem]["schemaitem"], key: result["formData"][objectItem]["schemaitem"], tag: "formItem"}));
					var $select =$('<select class="inputFullWidth theme-panelTextArea-14">').attr({type: 'dropdown', required: required, id: "properties_items"+result["formData"][objectItem]["selectedunit"], key: result["formData"][objectItem]["unitschema"], tag: "formItem"});

					for (var i=0; i< result["formData"][objectItem]["units"].length;i++){
						$select.append($('<option>').attr({value: result["formData"][objectItem]["units"][i]}).text(result["formData"][objectItem]["units"][i]));
					}
					$select.val(result["formData"][objectItem]["currentunit"])
					$cell.append($select);
					$row.append($cell);
					
				}		
				if (result["formData"][objectItem]["type"] == "break") {
					if (result["formData"][objectItem]["start"] == true){
						var $cell = $('<td colspan="2" width="100%">');
						$cell.append($('<label>').attr({for: result["formData"][objectItem]["schemaitem"], class: "theme-panelBreakTitle"}).text(label));
						$row.append($cell);
					}
					else 
					{
						var $cell = $('<td colspan="2" width="100%">');
						$cell.append($('<label>').attr({class: "theme-panelBreakLine"}));
						$row.append($cell);
					}
				}
				if (result["formData"][objectItem]["type"] == "script") {
					var $cell = $('<td width="100px">');
					$cell.append($('<label>').attr({for: result["formData"][objectItem]["schemaitem"], "data-bs-toggle" : "tooltip", title : tooltip, class: "theme-panelBreak"}).text(label+":"));
					$row.append($cell);
					var $cell = $('<td>');
					var $scriptTextArea = $('<textarea class="inputFullWidth theme-panelTextArea">').attr({type: 'text', required: required, id: "properties_items"+result["formData"][objectItem]["schemaitem"], current: result["formData"][objectItem]["textbox"], key: result["formData"][objectItem]["schemaitem"], tag: "formItem"});
					$scriptTextArea.keydown(function(e) {
						if(e.keyCode === 9) { // tab was pressed
							// get caret position/selection
							var start = this.selectionStart;
								end = this.selectionEnd;
							var $this = $(this);
							// set textarea value to: text before caret + tab + text after caret
							$this.val($this.val().substring(0, start)
										+ "\t"
										+ $this.val().substring(end));
							// put caret at right position again
							this.selectionStart = this.selectionEnd = start + 1;
							// prevent the focus lose
							return false;
						}
					});
					$cell.append($scriptTextArea);
					$cell.find('#properties_items'+result["formData"][objectItem]["schemaitem"]).val(result["formData"][objectItem]["textbox"]);
					$row.append($cell);
				}
				if (group > 0 && result["formData"][objectItem]["type"] != "group-checkbox") {
					$row.addClass("group_"+group.toString())
					if (!groups[group.toString()]) {
						$row.addClass("hide");
					}
				}
				$table.append($row);
			}
			panel.find(".propertiesPanel-body").append($table);

			if (result["whereUsed"].length > 1 && panel.find("#save").html() === "Save") {
				panel.find("#save").html(panel.find("#save").html() + " ("+result["whereUsed"].length+")");
			}

			// Added to fix a bug whereby the property table scroll bar does not appear
			panel.height(panel.height());

			// Set Initial Position
			if (init) {
				height = $("#flowchart").height();
				width = $("#flowchart").width();
				var posX = (width/2) - (panel.width()/2);
				var posY = (height/2) - (panel.height()/2);
				panel.css({top : posY, left : posX});
			}
		}
	});

}

function createPropertiesPanel(flowID) {
	if (!openPanels.hasOwnProperty(flowID)) {
		openPanels[flowID] = flowID;
		var panel = $(panelPropertiesHTML);
		panel.draggable({
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

		panel.find("#help").click(function () { 
			if (panel.find(".propertiesPanel-main").css("display") == "flex") {
				panel.find(".propertiesPanel-main").css("display","unset");
				panel.find(".propertiesPanel-help").css("display","none");
				panel.find("#help").text("Show Help");
				panel.width(panel.width()-900);
				panel.height(panel.height());
				left = parseInt(panel.css("left"));
				panel.css({left: left + 450});
			} else {
				panel.find(".propertiesPanel-main").css("display","flex");
				panel.find(".propertiesPanel-help").css("display","unset");
				panel.find("#help").text("Hide Help");
				panel.width(panel.width()+900);
				panel.height(panel.height());
				left = parseInt(panel.css("left"));
				panel.css({left: left - 450});
			}
		})

		// Loading properties form
		loadPropertiesPanel(flowID,panel,true);
	
		// Applying object to UI
		$('.ui-main').append(panel);
	}
}

