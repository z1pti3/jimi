var triggerObjectHTML = `
<div class="propertiesPanel">
	<div class="propertiesPanel-header">
		<span class="glyphicon glyphicon glyphicon-remove" id="close"></span>
		<label id="title"></label>
	</div>
	<div class="propertiesPanel-body">
		<textarea id="triggerValue" type="text" class="inputFullWidth"></textarea>
	</div>
	<div class="propertiesPanel-footer">
		<button id="trigger">Trigger</button>
		<button id="close">Close</button>
	</div>
</div>
`

var triggerExistingPanels = {}

function triggerTriggerObjectPanel(panel,flowID) {
	var conductID = GetURLParameter("conductID")
	$.ajax({url: "/conduct/"+conductID+"/forceTrigger/"+flowID+"/", type:"POST", data:JSON.stringify({events: panel.find("#triggerValue").val(), CSRF: CSRF }), contentType:"application/json", success: function ( result ) {
			dropdownAlert(panel,"success","Triggered",1000);
		}
	});
}

function createTriggerObjectPanel(flowID) {
	var conductID = GetURLParameter("conductID")
	var modelType = flowObjects[flowID]["flowType"]
	var modelID = flowObjects[flowID]["_id"]
	if (modelType == "trigger") {
		if (!triggerExistingPanels.hasOwnProperty(flowID)) {
			triggerExistingPanels[flowID] = flowID;
			var e = window.event;
			var posX = e.clientX;
			var posY = e.clientY;
			var panel = $(triggerObjectHTML);
			panel.css({top : posY, left : posX - 250});
			panel.draggable();
			panel.resizable({
				grid: 20
			});

			// Setting Title
			panel.find("#title").text(flowID);

			// Events
			panel.click(function () {
				$('.ui-main').find(".propertiesPanel").css("z-index", 1);
				$(this).css("z-index", 2);
			})

			panel.find("#close").click(function () { 
				delete triggerExistingPanels[flowID];
				panel.remove();
			})

			panel.find("#trigger").click(function () { 
				triggerTriggerObjectPanel(panel,flowID);
			})

			// Applying object to UI
			$('.ui-main').append(panel);
		}
	}
}

