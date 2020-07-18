var panelACLHTML = `
<div class="propertiesPanel theme-panelContainer">
	<div class="propertiesPanel-header theme-panelHeader">
		<span class="glyphicon glyphicon glyphicon-remove" id="close"></span>
		<label id="title"></label>
	</div>
	<div class="propertiesPanel-body theme-panelBody">
	<textarea id="propertiesPanelACLValue" class="inputFullWidth theme-panelTextArea"></textarea>
	</div>
	<div class="propertiesPanel-footer theme-panelFooter">
		<button id="save" class="btn btn-primary theme-panelButton">Save</button>
		<button id="refresh" class="btn btn-primary theme-panelButton">Refresh</button>
		<button id="close" class="btn btn-primary theme-panelButton">Close</button>
	</div>
</div>
`

var openACLPanels = {}

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

function saveACLValuesPanel(panel) {
	var conductID = GetURLParameter("conductID")
	var objectJson = {};
	selectedNodes = network.getSelectedNodes()
	node = nodeObjects[selectedNodes[0]]["flowID"]
	objectJson["acl"] = panel.find("#propertiesPanelACLValue").val();
	objectJson["CSRF"] = CSRF
	$.ajax({ url: "/conduct/"+conductID+"/editACL/"+node, type : "POST", data:JSON.stringify(objectJson), contentType:"application/json", success: function(result) {
			dropdownAlert(panel,"success","Save Successful",1000);
		}
	});
}

function loadACLValuesPanel(panel) {
	// Building properties form
	var conductID = GetURLParameter("conductID")
	panel.find("#title").text("come back to this");
	selectedNodes = network.getSelectedNodes()
	node = nodeObjects[selectedNodes[0]]["flowID"]
	$.ajax({ url: "/conduct/"+conductID+"/editACL/"+node, type : "GET", success: function( flowData ) {
			panel.find("#propertiesPanelACLValue").val(JSON.stringify(flowData["acl"]));
		}
	});
}

function createACLValuesPanel(node) {
	panelID = node
	if (!openACLPanels.hasOwnProperty(panelID)) {
		openACLPanels[panelID] = panelID;
		var e = window.event;
		var posX = e.clientX;
		var posY = e.clientY;
		var panel = $(panelACLHTML);
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
			delete openACLPanels[panelID];
			panel.remove();
		})

		panel.find("#save").click(function () { 
			saveACLValuesPanel(panel);
		})

		panel.find("#refresh").click(function () { 
			loadACLValuesPanel(panel);
		})

		panel.bind("keydown", function (event) { 
			if (event.ctrlKey || event.metaKey) {
                switch (String.fromCharCode(event.which).toLowerCase()) {
				case 's':
					event.preventDefault();
					saveACLValuesPanel(panel);
					break;
				}
			}
		})

		// Loading properties form
		loadACLValuesPanel(panel);
	
		// Applying object to UI
		$('.ui-main').append(panel);
	}
}

