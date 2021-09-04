var newObjectHTML = `
<div class="propertiesPanel propertiesPanelsmall theme-panelContainer">
	<div class="propertiesPanel-header theme-panelHeader">
		<span class="glyphicon glyphicon glyphicon-remove" id="close"></span>
		<label id="title">Create New Object</label>
	</div>
	<div class="propertiesPanel-body theme-panelBody">
		<select class="inputFullWidth theme-panelSelect" id="newObjectPanel-objectType" style="width: 100%"></select>
	</div>
	<div class="propertiesPanel-footer theme-panelFooter">
		<button id="save" class="btn btn-primary button">Create</button>
		<button id="existing" onClick="createExistingObjectPanel()" class="btn btn-primary button">Existing</button>
		<button id="close" class="btn btn-primary button">Close</button>
	</div>
</div>
`

var openNewPanels = {}

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

function saveNewObjectPanel(panel) {
	classID = panel.find("#newObjectPanel-objectType").val();
	if (classID != "") {
		var conductID = GetURLParameter("conductID")
		pos = network.getViewPosition()
		var x = pos["x"]
		var y = pos["y"]
		$.ajax({url:"/conductEditor/"+conductID+"/flow/", type:"PUT", data:JSON.stringify({classID: classID, x: x, y: y, CSRF: CSRF}), contentType:"application/json", success: function ( responseData ) {
				// Created new object
			}
		});
	}
}

function loadNewObjectPanel(panel) {
	panel.find("#newObjectPanel-objectType").empty();
	$.get( "/conduct/PropertyTypes/", function( data ) { 
		panel.find("#newObjectPanel-objectType").append(new Option("",""));
		for (result in data["results"]) {
			panel.find("#newObjectPanel-objectType").append(new Option(data["results"][result]["name"], data["results"][result]["_id"]));
		}
	});
}

function createNewObjectPanel() {
	if (!openNewPanels.hasOwnProperty("create")) {
		openNewPanels["create"] = "create";
		var e = window.event;
		var posX = e.clientX;
		var posY = e.clientY;
		var panel = $(newObjectHTML);
		panel.css({top : posY + 40, left : posX - 325});
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
			delete openNewPanels["create"];
			panel.remove();
		})

		panel.find("#save").click(function () { 
			saveNewObjectPanel(panel);
		})

		panel.bind("keydown", function (event) { 
			if (event.ctrlKey || event.metaKey) {
				switch (String.fromCharCode(event.which).toLowerCase()) {
				case 's':
					event.preventDefault();
					saveNewObjectPanel(panel);
					break;
				}
			}
		})

		// Loading properties form
		loadNewObjectPanel(panel);

		// Setting searchable
		panel.find("#newObjectPanel-objectType").select2({ theme : "theme-panelSelect" });

		// Applying object to UI
		$('.ui-main').append(panel);
	}
}

