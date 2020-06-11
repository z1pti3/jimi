// Globals
var mouseOverOperator;
var cKeyState
var eKeyState;
var dKeyState;
var loadedFlows = {};
var pauseFlowchartUpdate = false;
var lastUpdatePollTime = 0;

// visjs
var nodes = [];
var edges = [];
var network = null;
var nextId = 0;

// jimi
var flowObjects = {};
var nodeObjects = {};
var flowLinks = {};

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

function newNode(flowID, flowType, title, x, y) {
	flowObjects[flowID] = { "title": title, "x": x, "y": y, "flowID": flowID, "flowType": flowType, "nodeID": nextId }
	nodeObjects[nextId] = { "flowID": flowID, "nodeID": nextId }
	nodes.add({ id: nextId,
		label: title, 
		x: x, 
		y: y,
		shape: "box"
	 });
	nextId++;
}

function updateNode(flowID, title, x, y) {
	flowObjects[flowID]["title"] = title
	flowObjects[flowID]["x"] = x
	flowObjects[flowID]["y"] = y
	nodes.update({ id: flowObjects[flowID]["nodeID"],
		label: title, 
		x: x, 
		y: y
	 });
}

function deleteNode(flowID) {
	nodes.delete({ id: flowObjects[flowID]["nodeID"] })
	delete nodeObjects[flowObjects[flowID]["nodeID"]]
	delete flowObjects[flowID]
}

function createLinkRAW(from,to,colour) {
	var linkName = from + "->" + to;
	flowLinks[linkName] = { "from": from, "to": to, "colour": colour }
	edges.add({ 
		from: flowObjects[from]["nodeID"], 
		to: flowObjects[to]["nodeID"],
		arrows: {
			to: {
			  enabled: true,
			  type: "arrow"
			}
		},
		smooth: {
			enabled: true,
			type: "cubicBezier",
			roundness: 0.7
		}
	 });
	nextId++;
}

function updateLink(from,to) {
	var linkName = from + "->" + to;
	flowLinks[linkName]["from"] = from
	flowLinks[linkName]["to"] = to
	edges.update([{ 
		from: flowObjects[from]["nodeID"], 
		to: flowObjects[to]["nodeID"],
		arrows: {
			to: {
			  enabled: true,
			  type: "arrow"
			}
		}
	}]);
	return true;
}

function deleteLink(from,to) {
	var linkName = from + "->" + to;
	edges.delete([{ 
		from: flowObjects[from]["nodeID"],
		to: flowObjects[to]["nodeID"]
	}]);
	delete flowLinks[linkName]
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
	//var $flowchart = $('.flowchart');
	var conductID = GetURLParameter("conductID")
	//var flowData = $flowchart.flowchart("getData");
	//console.log(flowData)
	var operators = Object.keys(flowObjects)
	var links = Object.keys(flowLinks)
	var time = new Date().getTime() / 1000;
	$.ajax({url:"/conductEditor/"+conductID+"/", type:"POST", timeout: 2000, data: JSON.stringify({ lastPollTime : lastUpdatePollTime, operators: operators, links: links }), contentType:"application/json", success: function ( responseData ) {
			lastUpdatePollTime = time;
			// Operator Updates
			for (operator in responseData["operators"]["update"]) {
				obj = responseData["operators"]["update"][operator]
				updateNode(obj["flowID"],obj["title"],obj["x"],obj["y"]);
			}
			// Operator Creates
			for (operator in responseData["operators"]["create"]) {
				obj = responseData["operators"]["create"][operator]
				newNode(obj["flowID"],obj["flowType"],obj["title"],obj["x"],obj["y"]);
			}
			// Operator Deletions
			for (operator in responseData["operators"]["delete"]) {
				obj = responseData["operators"]["delete"][operator]
				deleteNode(obj["flowID"]);
			}
			// Link Creates
			for (link in responseData["links"]["create"]) {
				obj = responseData["links"]["create"][link]
				switch (obj["logic"]){
					case true:
						var colour = "blue"
						break
					case false:
						var colour = "red"
						break
					default:
						var colour = "purple"
				}
				createLinkRAW(obj["from"],obj["to"],colour)
			}
			// Link Updates
			for (link in responseData["links"]["update"]) {
				obj = responseData["links"]["update"][link]
				updateLink(obj["from"],obj["to"])
			}
			// Link Deletions
			for (link in responseData["links"]["delete"]) {
				obj = responseData["links"]["delete"][link]
				deleteLink(obj["from"],obj["to"])
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
	var container = document.getElementById("flowchart");
	nodes = new vis.DataSet([]);
	edges = new vis.DataSet([]);
	var data = {
		nodes: nodes,
		edges: edges
	};
	var options = {
		physics: {
			enabled: false
		},
		layout : {
			improvedLayout: false
		},
		interaction: {
			multiselect: true
		}
	};
	network = new vis.Network(container, data, options);

	network.on("dragEnd", function(params) {
		if (params["nodes"].length == 1) {
			var conductID = GetURLParameter("conductID")
			$.ajax({url:"/conductEditor/"+conductID+"/flow/"+nodeObjects[params["nodes"][0]]["flowID"]+"/", type:"POST", data: JSON.stringify({action: "update", x : params["pointer"]["canvas"]["x"], y : params["pointer"]["canvas"]["y"] }), contentType:"application/json", success: function( responseData ) {
			
				}
			});
		}
		return false;
	});

	// 	onOperatorMoved: function(operatorId, position) {
	// 		var conductID = GetURLParameter("conductID")
	// 		$.ajax({url:"/conductEditor/"+conductID+"/flow/"+operatorId+"/", type:"POST", data: JSON.stringify({action: "update", x : position["left"], y : position["top"] }), contentType:"application/json", success: function( responseData ) {
	// 				return true;
	// 			}
	// 		});
	// 		return false;
	// 	},

	// 	onOperatorMouseOver: function(operatorId) {
	// 		mouseOverOperator = operatorId;
	// 	},

	// 	onOperatorMouseOut: function(operatorId) {
	// 		if (mouseOverOperator == operatorId) {
	// 			mouseOverOperator = null;
	// 		}
	// 	},

	// 	onOperatorSelect: function(operatorId) {
	// 		// Create Link
	// 		if (cKeyState) {
	// 			var selectedOperatorId = $flowchart.flowchart('getSelectedOperatorId');
	// 			createLink(selectedOperatorId,operatorId,"blue",true);
	// 			return false;
	// 		}
	// 		if (($flowchart.flowchart('getSelectedOperatorId') == operatorId) || (eKeyState)) {
	// 			createPropertiesPanel(operatorId);
	// 			return false;
	// 		}
	// 		return true;
	// 	},

	network.on("doubleClick", function(params) {
		if (params["nodes"].length == 1) {
			if (cKeyState) {
			
			} else {
				createPropertiesPanel(nodeObjects[params["nodes"][0]]["flowID"]);
			}
		}
	});

	// 	onLinkSelect: function(linkId) { 
	// 		if (eKeyState) {
	// 			var flowData = $flowchart.flowchart("getData");
	// 			var from = flowData["links"][linkId]["fromOperator"];
	// 			var to = flowData["links"][linkId]["toOperator"];
	// 			createLinkPropertiesPanel(from,to);
	// 			return false;
	// 		}
	// 		return true;
	// 	}

	// });
	updateFlowchart();
	autoupdate();
}


