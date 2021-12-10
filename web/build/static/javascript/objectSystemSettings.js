var panelObjectSystemSettingsHTML = `
<div class="propertiesPanel theme-panelContainer">
	<div class="propertiesPanel-header theme-panelHeader">
		<span class="glyphicon glyphicon glyphicon-remove" id="close"></span>
		<label id="title"></label>
	</div>
	<div class="propertiesPanel-body theme-panelBody">
		<table width="100%">
			<tr>
				<td width="100px">
					<label class="theme-panelLabel">Scope:</label>
				</td>
				<td>
					<select class="inputFullWidth theme-panelTextArea" id="objectScope">
						<option>None</option>
						<option>Group</option>
						<option>Everyone</option>
					</select>
				</td>
			<tr>
		</table>
	</div>
	<div class="propertiesPanel-footer theme-panelFooter">
		<button id="save" class="btn btn-primary button bi-save"> Save</button>
		<button id="refresh" class="btn btn-primary button bi-recycle"> Refresh</button>
		<button id="close" class="btn btn-primary button">Close</button>
	</div>
</div>
`

var openObjectSystemSettingsPanels = {}

$(document).ready(function () {
	$(window).bind("keydown", function (event) { 
		if (event.ctrlKey || event.metaKey) {
			switch (String.fromCharCode(event.which).toLowerCase()) {
			case 's':
				event.preventDefault();
				break;
			}
		} else if (event.keyCode == 27) {
			if (selectedObject != null) {
				if (selectedObject[0] == "objectSystemSettings") {
					selectedObject[1]["panel"].find("#close").click();
				}
			}
		}
	})
});

function saveObjectSystemSettingsValuesPanel(panel,node) {
	var conductID = GetURLParameter("conductID")
	var objectJson = {};
	objectJson["scope"] = panel.find("#objectScope").prop('selectedIndex');
	objectJson["CSRF"] = CSRF
	$.ajax({ url: "/conductEditor/"+conductID+"/editObjectSystemSettings/"+node+"/", type : "POST", data:JSON.stringify(objectJson), contentType:"application/json", success: function(result) {
			dropdownAlert(panel,"success","Save Successful",1000);
		}
	});
}

function loadObjectSystemSettingsValuesPanel(panel,node) {
	var conductID = GetURLParameter("conductID")
	panel.find("#title").text("Object System Settings");
	$.ajax({ url: "/conductEditor/"+conductID+"/editObjectSystemSettings/"+node+"/", type : "GET", success: function( result ) {
			if (result["scope"] == 0) {
				panel.find("#objectScope").val("None");
			} else if (result["scope"] == 1) {
				panel.find("#objectScope").val("Group");
			} else if (result["scope"] == 2) {
				panel.find("#objectScope").val("Everyone");
			}
		}
	});
}

function createObjectSystemSettingsValuesPanel(node) {
	panelID = node
	if (!openObjectSystemSettingsPanels.hasOwnProperty(panelID)) {
		openObjectSystemSettingsPanels[panelID] = panelID;
		var panel = $(panelObjectSystemSettingsHTML);
		panel.draggable({handle: ".propertiesPanel-header"});
		panel.resizable({
			grid: 20
		});

		panel.find(".propertiesPanel-header").addClass("theme-panelHeader-Active");
		panel.css("z-index", 2);
		selectedObject = ["objectSystemSettings",{"panel" : panel, "flowID" : null, "deselect" : function(){ panel.find(".propertiesPanel-header").removeClass("theme-panelHeader-Active"); }}]

		// Events
		panel.click(function () {
			$('.ui-main').find(".propertiesPanel").css("z-index", 1);
			$(this).css("z-index", 2);
			panel.find(".propertiesPanel-header").addClass("theme-panelHeader-Active");
			panel.css("z-index", 2);
			selectedObject = ["objectSystemSettings",{"panel" : panel, "flowID" : null, "deselect" : function(){ panel.find(".propertiesPanel-header").removeClass("theme-panelHeader-Active"); }}]
		})

		panel.find("#close").click(function () { 
			delete openObjectSystemSettingsPanels[panelID];
			panel.remove();
		})

		panel.find("#save").click(function () { 
			saveObjectSystemSettingsValuesPanel(panel,node);
		})

		panel.find("#refresh").click(function () { 
			loadObjectSystemSettingsValuesPanel(panel,node);
		})

		panel.bind("keydown", function (event) { 
			if (event.ctrlKey || event.metaKey) {
                switch (String.fromCharCode(event.which).toLowerCase()) {
				case 's':
					event.preventDefault();
					saveObjectSystemSettingsValuesPanel(panel,node);
					break;
				}
			}
		})

		// Loading properties form
		loadObjectSystemSettingsValuesPanel(panel,node);
	
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

