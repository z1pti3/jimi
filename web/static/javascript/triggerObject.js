var triggerObjectHTML = `
<div class="propertiesPanel propertiesPanelFullWidth propertiesPanelFullHeight theme-panelContainer">
	<div class="propertiesPanel-header theme-panelHeader">
		<span class="glyphicon glyphicon glyphicon-remove" id="close"></span>
		<label id="title"></label>
	</div>
	<div class="propertiesPanel-body theme-panelBody">
		For this action to complete the flow must execute and return within 60 seconds<br><br>
		Number of Events to Process:<br>
		<input type='text' value="0" class="inputFullWidth theme-panelTextbox" id='triggerEventCount'><br>
		Events:<br>
		<textarea id="triggerValue" type="text" class="inputFullWidth theme-panelTextArea"></textarea><br>
		Output:<br>
		<textarea id="triggerOutput" readonly="true" type="text" class="inputFullWidth inputExpand theme-panelTextArea"></textarea>
	</div>
	<div class="propertiesPanel-footer theme-panelFooter">
		<button id="trigger" class="btn btn-primary theme-panelButton">Test</button>
		<button id="close" class="btn btn-primary theme-panelButton">Close</button>
	</div>
</div>
`

var triggerExistingPanels = {}

function triggerTriggerObjectPanel(panel,flowID) {
	var conductID = GetURLParameter("conductID")
	$('#triggerOutput').text("");
	$.ajax({url: "/conductEditor/"+conductID+"/codify/?json=True&flowID="+flowID, type:"GET", contentType:"application/json", success: function(result) {
			$.ajax({url: "/codify/", type:"POST", data:JSON.stringify({ events: $('#triggerValue').val(), eventCount: $('#triggerEventCount').val(), code: result["result"], CSRF: CSRF }), contentType:"application/json", success: function(result) {
					$('#triggerOutput').text(result["result"]);
				} 
			});
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
			var panel = $(triggerObjectHTML);
			panel.css({top : "10%", left : "10%"});
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

