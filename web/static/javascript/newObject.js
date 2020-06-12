var newObjectHTML = `
<div class="propertiesPanel propertiesPanelsmall">
	<div class="propertiesPanel-header">
		<span class="glyphicon glyphicon glyphicon-remove" id="close"></span>
		<label id="title">Create New Object</label>
	</div>
	<div class="propertiesPanel-body">
		<select class="inputFullWidth" id="newObjectPanel-objectType"></select>
	</div>
	<div class="propertiesPanel-footer">
		<button id="save">Create</button>
		<button id="existing" onClick="createExistingObjectPanel()">Existing</button>
		<button id="close">Close</button>
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
		$.ajax({url:"/conductEditor/"+conductID+"/flow/", type:"PUT", data:JSON.stringify({classID: classID, x: x, y: y}), contentType:"application/json", success: function ( responseData ) {
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
		panel.css({top : posY, left : posX - 250});
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

		// Applying object to UI
		$('.ui-main').append(panel);
	}
}

