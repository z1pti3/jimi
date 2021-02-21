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
			sdfdsfdsfsds
			<br>
			sdfdsf
		</div>
	</div>
	<div class="container-fluid propertiesPanel-footer theme-panelFooter">
		<button id="save" class="btn btn-primary theme-panelButton">Save</button>
		<button id="refresh" class="btn btn-primary theme-panelButton">Refresh</button>
		<button id="close" class="btn btn-primary theme-panelButton">Close</button>
		<button id="help" class="btn btn-primary theme-panelButton">Help</button>
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
				dropdownAlert(panel,"error","Dont forget the required fields!",1000);
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

function loadPropertiesPanel(flowID,panel) {
	// Building properties form
	var conductID = GetURLParameter("conductID")
	panel.find(".propertiesPanel-body").empty();
	panel.find("#title").text(flowObjects[flowID]["name"]);
	$.ajax({ url: "/conduct/"+conductID+"/flowProperties/"+flowID+"/", type:"GET", success: function ( result ) {
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
				
				if (result["formData"][objectItem]["type"] == "input") {
					var $cell = $('<td width="100px">');
					$cell.append($('<label>').attr({for: result["formData"][objectItem]["schemaitem"], title : tooltip, class: "theme-panelLabel"}).text(label+":").tooltip());
					$row.append($cell);
					var $cell = $('<td>');
					$cell.append($('<input class="inputFullWidth theme-panelTextbox">').attr({type: 'text', value: result["formData"][objectItem]["textbox"], current: result["formData"][objectItem]["textbox"], required: required, id: "properties_items"+result["formData"][objectItem]["schemaitem"], key: result["formData"][objectItem]["schemaitem"], tag: "formItem"}));
					$row.append($cell);
				}
				if (result["formData"][objectItem]["type"] == "checkbox") {
					var $cell = $('<td width="100px">');
					$cell.append($('<label>').attr({for: result["formData"][objectItem]["schemaitem"], title : tooltip, class: "theme-panelLabel"}).text(label+":").tooltip());
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
					$cell.append($('<label>').attr({for: result["formData"][objectItem]["schemaitem"], title : tooltip, class: "theme-panelLabel"}).text(label+":").tooltip());
					$row.append($cell);

					// output
					// <textarea class="inputFullWidth theme-panelTextArea" type="text" id="properties_itemsdelay" current="0" key="delay" tag="formItem"></textarea>
					var $cell = $('<td>');
					$cell.append($('<textarea class="inputFullWidth theme-panelTextArea">').attr({type: 'text', required: required, id: "properties_items"+result["formData"][objectItem]["schemaitem"], current: JSON.stringify(result["formData"][objectItem]["textbox"]), key: result["formData"][objectItem]["schemaitem"], tag: "formItem"}));
					$cell.find('#properties_items'+result["formData"][objectItem]["schemaitem"]).val(JSON.stringify(result["formData"][objectItem]["textbox"]));
					$row.append($cell);
				}
				if (result["formData"][objectItem]["type"] == "dropdown") {
          
					var $cell = $('<td width="100px">');
					$cell.append($('<label>').attr({for: result["formData"][objectItem]["schemaitem"], class: "theme-panelLabel"}).text(label+":").tooltip());
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
					$cell.append($('<label>').attr({for: result["formData"][objectItem]["schemaitem"], class: "theme-panelLabel"}).text(label+":").tooltip());
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
					$cell.append($('<label>').attr({for: result["formData"][objectItem]["schemaitem"], title : tooltip, class: "theme-panelBreak"}).text(label+":").tooltip());
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
				$table.append($row);
			}
			panel.find(".propertiesPanel-body").append($table);
			// Added to fix a bug whereby the property table scroll bar does not appear
			panel.height(panel.height());
		}
	});

}

function createPropertiesPanel(flowID) {
	if (!openPanels.hasOwnProperty(flowID)) {
		openPanels[flowID] = flowID;
		offsetLeft = $("#flowchart").offset().left;
		var e = window.event;
		var posX = e.clientX - offsetLeft;
		var posY = e.clientY;
		var panel = $(panelPropertiesHTML);
		panel.css({top : posY, left : posX + 35});
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
			if ($(".propertiesPanel-main").css("display") == "flex") {
				$(".propertiesPanel-main").css("display","unset");
				$(".propertiesPanel-help").css("display","none");
				panel.width(panel.width()-350);
				panel.height(panel.height());
			} else {
				$(".propertiesPanel-main").css("display","flex");
				$(".propertiesPanel-help").css("display","unset");
				panel.width(panel.width()+350);
				panel.height(panel.height());
			}
		})

		// Loading properties form
		loadPropertiesPanel(flowID,panel);
	
		// Applying object to UI
		$('.ui-main').append(panel);
	}
}

