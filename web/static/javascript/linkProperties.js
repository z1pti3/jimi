var panelLinkHTML = `
<div class="propertiesPanel">
	<div class="propertiesPanel-header">
		<span class="glyphicon glyphicon glyphicon-remove" id="close"></span>
		<label id="title"></label>
	</div>
	<div class="propertiesPanel-body">
	<textarea id="propertiesPanelLinkValue" class="inputFullWidth"></textarea>
	</div>
	<div class="propertiesPanel-footer">
		<button id="save">Save</button>
		<button id="refresh">Refresh</button>
		<button id="close">Close</button>
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
		}
	})
});

function saveLinkPropertiesPanel(from,to,panel) {
	var conductID = GetURLParameter("conductID")
	var objectJson = {};
	objectJson["logic"] = panel.find("#propertiesPanelLinkValue").val();
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
		}
	});
}

function createLinkPropertiesPanel(from,to) {
	panelID = from+"->"+to
	if (!openLinkPanels.hasOwnProperty(panelID)) {
		openLinkPanels[panelID] = panelID;
		var e = window.event;
		var posX = e.clientX;
		var posY = e.clientY;
		var panel = $(panelLinkHTML);
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
	}
}

