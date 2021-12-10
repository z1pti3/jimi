var panelLinkHTML = `
<div class="propertiesPanel theme-panelContainer">
	<div class="propertiesPanel-header theme-panelHeader">
		<span class="glyphicon glyphicon glyphicon-remove" id="close"></span>
		<label id="title"></label>
	</div>
	<div class="propertiesPanel-body theme-panelBody">
	<table width="100%">
		<tr>
			<td width="100px"><label class="theme-panelLabel">Link Order:</label></td>
			<td><input id="propertiesPanelLinkOrder" class="form-control form-control-sm full-width textbox" value="0"/></td>
		</tr>
		<tr>
			<td width="100px"><label class="theme-panelLabel">Link Tag:</label></td>
			<td><input id="propertiesPanelLinkTag" class="form-control form-control-sm full-width textbox" value="0"/></td>
		</tr>
		<tr>
			<td width="100px"><label class="theme-panelLabel">Link Logic:</label></td>
			<td><textarea id="propertiesPanelLinkValue" class="form-control form-control-sm full-width textbox"></textarea></td>
		</tr>
	</table>
	</div>
	<div class="propertiesPanel-footer theme-panelFooter">
		<button id="save" class="btn btn-primary button bi-save"> Save</button>
		<button id="refresh" class="btn btn-primary button bi-recycle"> Refresh</button>
		<button id="close" class="btn btn-primary button">Close</button>
	</div>
</div>
`

var openLinkPanels = {}

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
				if (selectedObject[0] == "linkProperties") {
					selectedObject[1]["panel"].find("#close").click();
				}
			}
		}
	})
});

function saveLinkPropertiesPanel(from,to,panel) {
	var conductID = GetURLParameter("conductID")
	var objectJson = {};
	objectJson["tag"] = panel.find("#propertiesPanelLinkTag").val();
	objectJson["order"] = panel.find("#propertiesPanelLinkOrder").val();
	objectJson["logic"] = panel.find("#propertiesPanelLinkValue").val();
	objectJson["CSRF"] = CSRF
	$.ajax({ url: "/conduct/"+conductID+"/flowlogic/"+from+"/"+to+"/", type : "POST", data:JSON.stringify(objectJson), contentType:"application/json", success: function(result) {
			dropdownAlert(panel,"success","Save Successful",1000);
		}
	});
}

function loadLinkPropertiesPanel(from,to,panel) {
	// Building properties form
	var conductID = GetURLParameter("conductID")
	panel.find("#title").text(to+"->"+from);
	$.ajax({ url: "/conduct/"+conductID+"/flowlogic/"+from+"/"+to+"/", type : "GET", success: function( flowData ) {
			panel.find("#propertiesPanelLinkValue").val(flowData["result"]["logic"]);
			panel.find("#propertiesPanelLinkOrder").val(flowData["result"]["order"]);
			panel.find("#propertiesPanelLinkTag").val(flowData["result"]["tag"]);
		}
	});
}

function createLinkPropertiesPanel(from,to) {
	panelID = from+"->"+to
	if (!openLinkPanels.hasOwnProperty(panelID)) {
		openLinkPanels[panelID] = panelID;
		var panel = $(panelLinkHTML);
		panel.draggable({handle: ".propertiesPanel-header",});
		panel.resizable({
			grid: 20
		});

		$('.ui-main').find(".propertiesPanel").css("z-index", 1);
		panel.find(".propertiesPanel-header").addClass("theme-panelHeader-Active");
		selectedObject = ["linkProperties",{"panel" : panel, "flowID" : null, "deselect" :function(){ panel.find(".propertiesPanel-header").removeClass("theme-panelHeader-Active"); }}]

		// Events
		panel.click(function () {
			$('.ui-main').find(".propertiesPanel").css("z-index", 1);
			$(this).css("z-index", 2);
			panel.find(".propertiesPanel-header").addClass("theme-panelHeader-Active");
			panel.css("z-index", 2);
			selectedObject = ["linkProperties",{"panel" : panel, "flowID" : null, "deselect" : function(){ panel.find(".propertiesPanel-header").removeClass("theme-panelHeader-Active"); }}]
		})

		panel.find("#close").click(function () { 
			delete openLinkPanels[panelID];
			panel.remove();
		})

		panel.find("#save").click(function () { 
			saveLinkPropertiesPanel(from,to,panel);
		})

		panel.find("#refresh").click(function () { 
			loadLinkPropertiesPanel(from,to,panel);
		})

		panel.bind("keydown", function (event) { 
			if (event.ctrlKey || event.metaKey) {
                switch (String.fromCharCode(event.which).toLowerCase()) {
				case 's':
					event.preventDefault();
					saveLinkPropertiesPanel(from,to,panel);
					break;
				}
			}
		})

		// Loading properties form
		loadLinkPropertiesPanel(from,to,panel);
	
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

