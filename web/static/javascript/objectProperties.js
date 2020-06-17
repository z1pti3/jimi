var panelPropertiesHTML = `
<div class="propertiesPanel">
	<div class="container-fluid propertiesPanel-header">
		<span class="glyphicon glyphicon glyphicon-remove" id="close"></span>
		<label id="title"></label>
	</div>
	<div class="container-fluid propertiesPanel-body">
	</div>
	<div class="container-fluid propertiesPanel-footer">
		<button id="save">Save</button>
		<button id="refresh">Refresh</button>
		<button id="close">Close</button>
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
				break;
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
	panel.find("[tag=formItem]").each(function() {
		formItem = $(this)
		resultItem = $(this).attr("key")
		if (formItem.attr("type") == "text")
		{
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
	})
	// Posting
	$.ajax({url:"/api/1.0/models/"+modelType+"/"+modelID+"/", type:"POST", data: JSON.stringify({ action : "update", data: jsonData }), contentType:"application/json", success: function ( result ) {
			// Telling UI it has had some changes made
			if (newName) {
				postData = { "action": "update" }
				if (newName) {
					postData["title"] = newName
				}
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
				if (result["formData"][objectItem]["type"] == "input") {
					var $cell = $('<td width="100px">');
					$cell.append($('<label>').attr({for: result["formData"][objectItem]["schemaitem"]}).text(result["formData"][objectItem]["schemaitem"]+":"));
					$row.append($cell);
					var $cell = $('<td>');
					$cell.append($('<input class="inputFullWidth">').attr({type: 'text', value: result["formData"][objectItem]["textbox"], current: result["formData"][objectItem]["textbox"], id: "properties_items"+result["formData"][objectItem]["schemaitem"], key: result["formData"][objectItem]["schemaitem"], tag: "formItem"}));
					$row.append($cell);
				}
				if (result["formData"][objectItem]["type"] == "checkbox") {
					var $cell = $('<td width="100px">');
					$cell.append($('<label>').attr({for: result["formData"][objectItem]["schemaitem"]}).text(result["formData"][objectItem]["schemaitem"]+":"));
					$row.append($cell);
					var $cell = $('<td>');
					if (result["formData"][objectItem]["checked"] == true) {
						$cell.append($('<input>').attr({type: 'checkbox', id: "properties_items"+result["formData"][objectItem]["schemaitem"], current: true ,checked: true, key: result["formData"][objectItem]["schemaitem"], tag: "formItem"}));
					}
					else {
						$cell.append($('<input>').attr({type: 'checkbox', id: "properties_items"+result["formData"][objectItem]["schemaitem"], current: false, key: result["formData"][objectItem]["schemaitem"], tag: "formItem"}));
					}
					$row.append($cell);
				}
				if (result["formData"][objectItem]["type"] == "json-input") {
					var $cell = $('<td width="100px">');
					$cell.append($('<label>').attr({for: result["formData"][objectItem]["schemaitem"]}).text(result["formData"][objectItem]["schemaitem"]+":"));
					$row.append($cell);
					var $cell = $('<td>');
					$cell.append($('<textarea class="inputFullWidth">').attr({type: 'text', id: "properties_items"+result["formData"][objectItem]["schemaitem"], current: JSON.stringify(result["formData"][objectItem]["textbox"]), key: result["formData"][objectItem]["schemaitem"], tag: "formItem"}));
					$cell.find('#properties_items'+result["formData"][objectItem]["schemaitem"]).val(JSON.stringify(result["formData"][objectItem]["textbox"]));
					$row.append($cell);
					
				}
				$table.append($row);
			}
			panel.find(".propertiesPanel-body").append($table);
		}
	});

}

function createPropertiesPanel(flowID) {
	if (!openPanels.hasOwnProperty(flowID)) {
		openPanels[flowID] = flowID;
		var e = window.event;
		var posX = e.clientX;
		var posY = e.clientY;
		var panel = $(panelPropertiesHTML);
		panel.css({top : posY, left : posX + 35});
		panel.draggable();
		panel.resizable({
			grid: 20
		});

		// Events
		panel.click(function () {
			$('.ui-main').find(".propertiesPanel").css("z-index", 1);
			$(this).css("z-index", 2);
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

		panel.bind("keydown", function (event) { 
			if (event.ctrlKey || event.metaKey) {
                switch (String.fromCharCode(event.which).toLowerCase()) {
				case 's':
					event.preventDefault();
					savePropertiesPanel(flowID,panel);
					break;
				}
			}
		})

		// panel.find("#title").focusout(function () {
		// 	var title = panel.find("#title");
		// 	var conductID = GetURLParameter("conductID")
		// 	if (title.attr("current") != title.val()) {
		// 		$.ajax({url:"/conductEditor/"+conductID+"/flow/"+flowID+"/", type:"POST", data: JSON.stringify({action: "update", title : title.val() }), contentType:"application/json", success: function( responseData ) {
		// 				dropdownAlert(panel,"success","Title Updated",1000);
		// 				var $flowchart = $('.flowchart');
		// 				var operatorData = $flowchart.flowchart("getOperatorData", flowID);
		// 				operatorData["properties"]["title"] = title.val()
		// 				$flowchart.flowchart("setOperatorData", flowID, operatorData);
		// 			}
		// 		});
		// 	}
		// })

		// Loading properties form
		loadPropertiesPanel(flowID,panel);
	
		// Applying object to UI
		$('.ui-main').append(panel);
	}
}

