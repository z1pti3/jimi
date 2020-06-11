// Globals
var mouseOverOperator;
var cKeyState
var eKeyState;
var dKeyState;
var loadedFlows = {};
var pauseFlowchartUpdate = false;
var lastUpdatePollTime = 0;

$(document).ready(function () {
	setupFlowchart();
	
	// Key events
	$(document).keydown(function(event) {
		switch (String.fromCharCode(event.which).toLowerCase()) {
			case 'c':
				cKeyState = true;
				break;
			case 'e':
				eKeyState = true;
				break;
			case 'd':
				dKeyState = true;
				break;
		}
	});
	$(document).keyup(function( event ) {
		// Really it needs to detect the object its on e.g. operator or link not just anything but the few listed
		if (event.keyCode == 46 && document.activeElement.type != "text" && document.activeElement.type != "checkbox" && document.activeElement.type != "textarea") {
			deleteSelected();
		}
		cKeyState = false;
		eKeyState = false;
		dKeyState = false;
	});
});

function autoupdate() {
	setInterval(updateFlowchart, 2500);
}

function deleteSelected() {
	var $flowchart = $('.flowchart');
	var selectedOperatorId = $flowchart.flowchart('getSelectedOperatorId');
	var selectedLinkId = $flowchart.flowchart('getSelectedLinkId');
	if (selectedOperatorId) {
		if (confirm("Are you sure you want to delete object '"+ selectedOperatorId +"'?")) {
			var conductID = GetURLParameter("conductID");
			$.ajax({url:"/conductEditor/"+conductID+"/flow/"+selectedOperatorId+"/", type:"DELETE", contentType:"application/json", success: function ( responseData ) {
					$flowchart.flowchart('deleteOperator', selectedOperatorId);
				}
			});
		}
	}

	if (selectedLinkId) {
		var conductID = GetURLParameter("conductID");
		var flowData = $flowchart.flowchart("getData");
		var to = flowData["links"][selectedLinkId]["toOperator"];
		var from = flowData["links"][selectedLinkId]["fromOperator"];
		$.ajax({url:"/conductEditor/"+conductID+"/flowLink/"+from+"/"+to+"/", type:"DELETE", contentType:"application/json", success: function ( responseData ) {
				var flowData = $flowchart.flowchart("getData");	
				var from = flowData["links"][selectedLinkId]["fromOperator"]
				var to = flowData["links"][selectedLinkId]["toOperator"]
				var fromOperatorData = $flowchart.flowchart("getOperatorData", from);
				var toOperatorData = $flowchart.flowchart("getOperatorData", to);
				delete fromOperatorData["properties"]["outputs"][selectedLinkId];
				delete toOperatorData["properties"]["inputs"][selectedLinkId];
				$flowchart.flowchart("deleteLink", selectedLinkId);
				$flowchart.flowchart("setOperatorData", from, fromOperatorData);
				$flowchart.flowchart("setOperatorData", to, toOperatorData);
			}
		});
	}
}

function createLinkRAW(from,to,colour) {
	var $flowchart = $('.flowchart');
	var flowData = $flowchart.flowchart("getData");
	var linkName = from + "->" + to;
	if (!flowData["links"].hasOwnProperty(linkName)) {
		var operatorData = $flowchart.flowchart("getOperatorData", from);
		var linkOperatorData = $flowchart.flowchart("getOperatorData", to);
		if ((!$.isEmptyObject(operatorData)) && (!$.isEmptyObject(linkOperatorData))) {
			operatorData["properties"]["outputs"][linkName] = { "label" : ">" }
			linkOperatorData["properties"]["inputs"][linkName] = { "label" : ">" }
			var conductID = GetURLParameter("conductID")
			$flowchart.flowchart("setOperatorData", from, operatorData);
			$flowchart.flowchart("setOperatorData", to, linkOperatorData);
			var linkData = {
				fromOperator: from,
				toOperator: to,
				fromConnector : linkName,
				toConnector : linkName,
				color : colour
			}
			$flowchart.flowchart("createLink", linkName, linkData);
			return true;
		} else {
			return false;
		}
	}
}

function updateLink(from,to,colour) {
	var $flowchart = $('.flowchart');
	$flowchart.flowchart("setLinkMainColor",from+"->"+to,colour)
	//$flowchart.flowchart("redrawLinksLayer")
	return true;
}

function createLink(from,to,colour,save) {
	if (from == to) {
		var conductID = GetURLParameter("conductID")
		$.ajax({url:"/conductEditor/"+conductID+"/flowLink/"+from+"/"+to+"/", type:"DELETE", contentType:"application/json"});
		return false
	}

	if (save) {
		var conductID = GetURLParameter("conductID")
		$.ajax({url:"/conductEditor/"+conductID+"/flowLink/"+from+"/"+to+"/", type:"PUT", contentType:"application/json", success: function ( responseData ) {
				if (createLinkRAW(from,to,colour)) {
					return true;
				} else {
					//$.ajax({url:"/conductEditor/"+conductID+"/flowLink/"+from+"/"+to+"/", type:"DELETE", contentType:"application/json"});
					return false
				}
			}
		});
	} else {
		var conductID = GetURLParameter("conductID")
		if (createLinkRAW(from,to,colour)) {
			return true;
		} else {
			//$.ajax({url:"/conductEditor/"+conductID+"/flowLink/"+from+"/"+to+"/", type:"DELETE", contentType:"application/json"});
			return false
		}
	}
	return false;
}

function saveNewLink(from,to) {
	var conductID = GetURLParameter("conductID")
	$.ajax({url:"/conductEditor/"+conductID+"/flowLink/"+from+"/"+to+"/", type:"PUT", contentType:"application/json", success: function ( responseData ) {
			return true;
		}
	});
}

function updateFlowchart() {
	var $flowchart = $('.flowchart');
	var conductID = GetURLParameter("conductID")
	var flowData = $flowchart.flowchart("getData");
	//console.log(flowData)
	var operators = Object.keys(flowData["operators"]);
	var links = Object.keys(flowData["links"])
	var time = new Date().getTime() / 1000;
	$.ajax({url:"/conductEditor/"+conductID+"/", type:"POST", timeout: 2000, data: JSON.stringify({ lastPollTime : lastUpdatePollTime, operators: operators, links: links }), contentType:"application/json", success: function ( responseData ) {
			lastUpdatePollTime = time;
			// Operator Updates
			for (operator in responseData["operators"]["update"]) {
				var operatorData = $flowchart.flowchart("getOperatorData", operator);
				operatorData["left"] = responseData["operators"]["update"][operator]["x"]
				operatorData["top"] = responseData["operators"]["update"][operator]["y"]
				operatorData["properties"]["title"] = sanitize(responseData["operators"]["update"][operator]["title"])
				if (operatorData["properties"]["title"] == "") {
					operatorData["properties"]["title"] = sanitize(operator);
				};
				$flowchart.flowchart("setOperatorData", operator, operatorData);
				if (!loadedFlows.hasOwnProperty(operator)) {
					loadedFlows[operator] = { flowID: operator, flowType: responseData["operators"]["update"][operator]["flowType"], _id: responseData["operators"]["update"][operator]["_id"] }
				}
			}
			// Operator Creates
			for (operator in responseData["operators"]["create"]) {
				var operatorData = {
					top: responseData["operators"]["create"][operator]["y"],
					left: responseData["operators"]["create"][operator]["x"],
					properties: {
						title: sanitize(responseData["operators"]["create"][operator]["title"]),

						inputs: {},
						outputs: {}
					}
				};
				if (operatorData["properties"]["title"] == "") {
					operatorData["properties"]["title"] = sanitize(operator);
				};
				if (responseData["operators"]["create"][operator]["flowType"] == "trigger") {
					operatorData["properties"]["class"] = "flowchart-operator-trigger"
				}
				if (responseData["operators"]["create"][operator]["flowSubtype"] != ""){
					operatorData["properties"]["class"] = "flowchart-operator-trigger-"+responseData["operators"]["create"][operator]["flowSubtype"]
				}
				$flowchart.flowchart('createOperator', operator, operatorData);
				if (!loadedFlows.hasOwnProperty(operator)) {
					loadedFlows[operator] = { flowID: operator, flowType: responseData["operators"]["create"][operator]["flowType"], _id: responseData["operators"]["create"][operator]["_id"] }
				}
			}
			// Operator Deletions
			for (operator in responseData["operators"]["delete"]) {
				$flowchart.flowchart("deleteOperator", operator);
			}
			// Link Creates
			for (link in responseData["links"]["create"]) {
				switch (responseData["links"]["create"][link]["logic"]){
					case true:
						var colour = "blue"
						break
					case false:
						var colour = "red"
						break
					default:
						var colour = "purple"
				}
				createLink(responseData["links"]["create"][link]["from"],responseData["links"]["create"][link]["to"],colour,false);
			}
			// Link Updates
			for (link in responseData["links"]["update"]) {
				switch (responseData["links"]["update"][link]["logic"]){
					case true:
						var colour = "blue"
						break
					case false:
						var colour = "red"
						break
					default:
						var colour = "purple"
				}
				updateLink(responseData["links"]["update"][link]["from"],responseData["links"]["update"][link]["to"],colour);
			}
			// Link Deletions
			for (link in responseData["links"]["delete"]) {
				var from = flowData["links"][link]["fromOperator"]
				var to = flowData["links"][link]["toOperator"]
				var fromOperatorData = $flowchart.flowchart("getOperatorData", from);
				var toOperatorData = $flowchart.flowchart("getOperatorData", to);
				delete fromOperatorData["properties"]["outputs"][link];
				delete toOperatorData["properties"]["inputs"][link];
				$flowchart.flowchart("deleteLink", link);
				$flowchart.flowchart("setOperatorData", from, fromOperatorData);
				$flowchart.flowchart("setOperatorData", to, toOperatorData);
			}
		},
		error: function ( error ) {
			console.log("Unable to update flowChart");
		}
	});
}

function triggerFlowObject() {
	var $flowchart = $('.flowchart');
	var selectedOperatorId = $flowchart.flowchart('getSelectedOperatorId');
	if (selectedOperatorId != null) {
		createTriggerObjectPanel(selectedOperatorId);
	}
}

function debugFlowObject() {
	var $flowchart = $('.flowchart');
	var selectedOperatorId = $flowchart.flowchart('getSelectedOperatorId');
	if (selectedOperatorId != null) {
		var conductID = GetURLParameter("conductID")
		$.ajax({url: "/conduct/"+conductID+"/debug/"+selectedOperatorId+"/", type:"GET", contentType:"application/json", success: function ( result ) {
			$.ajax({url: "/api/1.0/debug/", type:"POST", data:JSON.stringify({ "filter" : result["_id"], "level" : 100}), contentType:"application/json", success: function ( result ) {
				var win = window.open('/debug/'+result["debugID"]+"/", '_blank');
				if (win) {
					win.focus();
				} else {
					alert('Popups disabled!');
				}
			}
		});
	}
});
	}
}

function editFlowObject() {
	var $flowchart = $('.flowchart');
	var selectedOperatorId = $flowchart.flowchart('getSelectedOperatorId');
	if (selectedOperatorId != null) {
		createPropertiesPanel(selectedOperatorId);
	}
}

function deleteFlowObject() {
	var $flowchart = $('.flowchart');
	var selectedOperatorId = $flowchart.flowchart('getSelectedOperatorId');
	if (selectedOperatorId != null) {
		if (confirm("Are you sure you want to delete object '"+ selectedOperatorId +"'?")) {
			var conductID = GetURLParameter("conductID");
			$.ajax({url:"/conductEditor/"+conductID+"/flow/"+selectedOperatorId+"/", type:"DELETE", contentType:"application/json", success: function ( responseData ) {
					$flowchart.flowchart('deleteOperator', selectedOperatorId);
				}
			});
		}
	}
}

function copyFlowObject() {
	var $flowchart = $('.flowchart');
	var $container = $flowchart.parent();
	var selectedOperatorId = $flowchart.flowchart('getSelectedOperatorId');
	if (selectedOperatorId != null) {
		var selectedOperatorId = $flowchart.flowchart('getSelectedOperatorId');
		var conductID = GetURLParameter("conductID")
		var pzmatrix = $flowchart.panzoom("getMatrix");
		var currentScale = pzmatrix[0];
		var pzoff = $flowchart.offset();
		var x = ((($container.width() / 2) + -pzoff.left) / currentScale);
		var y = ((($container.height() / 2) + -pzoff.top) / currentScale);
		$.ajax({url:"/conductEditor/"+conductID+"/flow/"+selectedOperatorId+"/", type:"POST", data:JSON.stringify({action: "copy", operatorId: selectedOperatorId, x: x, y: y}), contentType:"application/json", success: function ( result ) {
				// Coned sucessfull
			}
		});
	}
}

function duplicateFlowObject() {
	var $flowchart = $('.flowchart');
	var $container = $flowchart.parent();
	var selectedOperatorId = $flowchart.flowchart('getSelectedOperatorId');
	if (selectedOperatorId != null) {
		var selectedOperatorId = $flowchart.flowchart('getSelectedOperatorId');
		var conductID = GetURLParameter("conductID")
		var pzmatrix = $flowchart.panzoom("getMatrix");
		var currentScale = pzmatrix[0];
		var pzoff = $flowchart.offset();
		var x = ((($container.width() / 2) + -pzoff.left) / currentScale);
		var y = ((($container.height() / 2) + -pzoff.top) / currentScale);
		$.ajax({url:"/conductEditor/"+conductID+"/flow/"+selectedOperatorId+"/", type:"POST", data:JSON.stringify({action: "clone", operatorId: selectedOperatorId, x: x, y: y}), contentType:"application/json", success: function ( result ) {
				// Coned sucessfull
			}
		});
	}
}

function setupFlowchart() {
	var $flowchart = $('.flowchart');
	var $container = $flowchart.parent();
	var cx = $flowchart.width() / 2;
	var cy = $flowchart.height() / 2;
	var zoomBy = 0.1;
	var currentZoom = 1;
	var minZoom = 0.25;
	var maxZoom = 2;
	$flowchart.panzoom({ });
	$flowchart.panzoom('pan', - cx + $container.width()/2, - cy + $container.height()/2);
	$flowchart.panzoom.minScale = minZoom;
	$container.on('mousewheel.focal', function( e ) {
		// Checks if the mouse is over a propertiesPanel if so dont pan/zoom flow page
		if ($('.propertiesPanel:hover').length < 1) {
			if (e.shiftKey) {
				var newZoom = 0 ;
				if (e.deltaY == -1) {
					newZoom = currentZoom - zoomBy;
				};
				if (e.deltaY == 1) {
					newZoom = currentZoom + zoomBy;
				};
				if ((newZoom > minZoom) && (newZoom < maxZoom))
				{
					currentZoom = newZoom;
				};
				$flowchart.flowchart('setPositionRatio', currentZoom);
				$flowchart.panzoom('zoom', currentZoom, {
					animate: false,
					focal: e
				});
			} else {
				var $pzmatrix = $flowchart.panzoom('getMatrix');
				$flowchart.panzoom('pan', +$pzmatrix[4], +$pzmatrix[5] + e.originalEvent.wheelDelta);
			}
		}
	});
	$flowchart.flowchart({
		canUserEditLinks : false,

		onOperatorMoved: function(operatorId, position) {
			var conductID = GetURLParameter("conductID")
			$.ajax({url:"/conductEditor/"+conductID+"/flow/"+operatorId+"/", type:"POST", data: JSON.stringify({action: "update", x : position["left"], y : position["top"] }), contentType:"application/json", success: function( responseData ) {
					return true;
				}
			});
			return false;
		},

		onOperatorMouseOver: function(operatorId) {
			mouseOverOperator = operatorId;
		},

		onOperatorMouseOut: function(operatorId) {
			if (mouseOverOperator == operatorId) {
				mouseOverOperator = null;
			}
		},

		onOperatorSelect: function(operatorId) {
			// Create Link
			if (cKeyState) {
				var selectedOperatorId = $flowchart.flowchart('getSelectedOperatorId');
				createLink(selectedOperatorId,operatorId,"blue",true);
				return false;
			}
			if (($flowchart.flowchart('getSelectedOperatorId') == operatorId) || (eKeyState)) {
				createPropertiesPanel(operatorId);
				return false;
			}
			return true;
		},

		onLinkSelect: function(linkId) { 
			if (eKeyState) {
				var flowData = $flowchart.flowchart("getData");
				var from = flowData["links"][linkId]["fromOperator"];
				var to = flowData["links"][linkId]["toOperator"];
				createLinkPropertiesPanel(from,to);
				return false;
			}
			return true;
		}

	});
	updateFlowchart();
	autoupdate();
}


