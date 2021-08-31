var panelACLHTML = `
<div class="propertiesPanel theme-panelContainer">
	<div class="propertiesPanel-header theme-panelHeader">
		<span class="glyphicon glyphicon glyphicon-remove" id="close"></span>
		<label id="title"></label>
	</div>
	<div class="propertiesPanel-body theme-panelBody">
	object ACL:<br>
	<textarea id="propertiesPanelACLValue" class="form-control form-control-sm full-width textbox"></textarea>
	<br>
	<br>
	Flow UI ACL:<br>
	<textarea id="propertiesPanelUiACLValue" class="form-control form-control-sm full-width textbox"></textarea>
	</div>
	<div class="propertiesPanel-footer theme-panelFooter">
		<button id="save" class="btn btn-primary button bi-save"> Save</button>
		<button id="refresh" class="btn btn-primary button bi-recycle"> Refresh</button>
		<button id="close" class="btn btn-primary button">Close</button>
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

function saveACLValuesPanel(panel,node) {
	var conductID = GetURLParameter("conductID")
	var objectJson = {};
	objectJson["uiAcl"] = panel.find("#propertiesPanelUiACLValue").val();
	objectJson["acl"] = panel.find("#propertiesPanelACLValue").val();
	objectJson["CSRF"] = CSRF
	$.ajax({ url: "/conductEditor/"+conductID+"/editACL/"+node, type : "POST", data:JSON.stringify(objectJson), contentType:"application/json", success: function(result) {
			dropdownAlert(panel,"success","Save Successful",1000);
		}
	});
}

function loadACLValuesPanel(panel,node) {
	// Building properties form
	var conductID = GetURLParameter("conductID")
	panel.find("#title").text("Security Settings");
	$.ajax({ url: "/conductEditor/"+conductID+"/editACL/"+node, type : "GET", success: function( flowData ) {
			panel.find("#propertiesPanelUiACLValue").val(JSON.stringify(flowData["uiAcl"]));
			panel.find("#propertiesPanelACLValue").val(JSON.stringify(flowData["acl"]));
		}
	});
}

function createACLValuesPanel(node) {
	panelID = node
	if (!openACLPanels.hasOwnProperty(panelID)) {
		openACLPanels[panelID] = panelID;
		var panel = $(panelACLHTML);
		panel.draggable({handle: ".propertiesPanel-header"});
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
			saveACLValuesPanel(panel,node);
		})

		panel.find("#refresh").click(function () { 
			loadACLValuesPanel(panel,node);
		})

		panel.bind("keydown", function (event) { 
			if (event.ctrlKey || event.metaKey) {
                switch (String.fromCharCode(event.which).toLowerCase()) {
				case 's':
					event.preventDefault();
					saveACLValuesPanel(panel,node);
					break;
				}
			}
		})

		// Loading properties form
		loadACLValuesPanel(panel,node);
	
		// Applying object to UI
		$('.ui-main').append(panel);

		// Set Initial Position
		height = $("#flowchart").height();
		width = $("#flowchart").width();
		var posX = (width/2) - (panel.width()/2);
		var posY = (height/2) - (panel.height()/2);
		panel.css({top : posY, left : posX});
	}
}

