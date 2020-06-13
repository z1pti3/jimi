// Globals
var mouseOverOperator;
var cKeyState
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
var selectedObject = null;

$(document).ready(function () {
	setupFlowchart();
	
	// Key events
	$(document).keydown(function(event) {
		switch (String.fromCharCode(event.which).toLowerCase()) {
			case 'c':
				cKeyState = true;
				break;
		}
	});
	$(document).keyup(function( event ) {
		// Really it needs to detect the object its on e.g. operator or link not just anything but the few listed
		if (event.keyCode == 46 && document.activeElement.type != "text" && document.activeElement.type != "checkbox" && document.activeElement.type != "textarea") {
			deleteSelected();
		}
		cKeyState = false;
	});
});

function autoupdate() {
	setInterval(updateFlowchart, 2500);
}

function deleteSelected() {
	selectedNodes = network.getSelectedNodes()
	if (selectedNodes.length == 1) {
		node = nodeObjects[selectedNodes[0]]["flowID"]
		if (confirm("Are you sure you want to delete object '"+ node +"'?")) {
			var conductID = GetURLParameter("conductID");
			$.ajax({url:"/conductEditor/"+conductID+"/flow/"+node+"/", type:"DELETE", contentType:"application/json", success: function ( responseData ) {
					deleteNode(node)
				}
			});
		}
	}

	links = network.getSelectedEdges()
	if (links.length == 1) {
		link = flowLinks[links[0]]
		var conductID = GetURLParameter("conductID");
		var to = link["to"]
		var from = link["from"]
		$.ajax({url:"/conductEditor/"+conductID+"/flowLink/"+from+"/"+to+"/", type:"DELETE", contentType:"application/json", success: function ( responseData ) {
				deleteLink(from,to)
			}
		});
	}
}

function newNode(flowID, objectID, flowType, title, x, y) {
	flowObjects[flowID] = { "title": title, "x": x, "y": y, "flowID": flowID, "flowType": flowType, "nodeID": nextId, "_id": objectID }
	nodeObjects[nextId] = { "flowID": flowID, "nodeID": nextId }
	nodes.add({ id: nextId,
		label: title, 
		x: x, 
		y: y,
		shape: "box",
		widthConstraint: {
			minimum: 125,
			maximum: 125
		},
		heightConstraint: {
			minimum: 35,
			maximum: 35
		},
		borderWidth: 3
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
	nodes.remove({ id: flowObjects[flowID]["nodeID"] })
	delete nodeObjects[flowObjects[flowID]["nodeID"]]
	delete flowObjects[flowID]
}

function createLinkRAW(from,to,color) {
	var linkName = from + "->" + to;
	flowLinks[linkName] = { "from": from, "to": to, "colour": color }
	edges.add({ 
		id: linkName,
		from: flowObjects[from]["nodeID"], 
		to: flowObjects[to]["nodeID"],
		color: {
			color: color
		},
		arrows: {
			middle: {
			  enabled: true,
			  type: "arrow"
			}
		},
		smooth: {
			enabled: true,
			type: "cubicBezier",
			roundness: 0.7
		},
		width: 3
	 });
	nextId++;
}

function updateLink(from,to) {
	var linkName = from + "->" + to;
	flowLinks[linkName]["from"] = from
	flowLinks[linkName]["to"] = to
	edges.update({ 
		id: linkName,
		from: flowObjects[from]["nodeID"], 
		to: flowObjects[to]["nodeID"]
	});
	return true;
}

function deleteLink(from,to) {
	var linkName = from + "->" + to;
	edges.remove({ 
		id: linkName
	});
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

function updateFlowchart(init) {
	var conductID = GetURLParameter("conductID")
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
				newNode(obj["flowID"],obj["_id"],obj["flowType"],obj["title"],obj["x"],obj["y"]);
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
						var color = "blue"
						break
					case false:
						var color = "red"
						break
					default:
						var color = "purple"
				}
				createLinkRAW(obj["from"],obj["to"],color)
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

			// fit
			if (init) {
				network.fit();
			}
		},
		error: function ( error ) {
			console.log("Unable to update flowChart");
		}
	});
}

function triggerFlowObject() {
	nodes = network.getSelectedNodes()
	if (nodes.length == 1) {
		node = nodeObjects[nodes[0]]["flowID"]
		createTriggerObjectPanel(node);
	}
}

function debugFlowObject() {
	selectedNodes = network.getSelectedNodes()
	if (selectedNodes.length == 1) {
		node = nodeObjects[selectedNodes[0]]["flowID"]
		var conductID = GetURLParameter("conductID")
		$.ajax({url: "/conduct/"+conductID+"/debug/"+node+"/", type:"GET", contentType:"application/json", success: function ( result ) {
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
	selectedNodes = network.getSelectedNodes()
	if (selectedNodes.length == 1) {
		node = nodeObjects[selectedNodes[0]]["flowID"]
		var conductID = GetURLParameter("conductID")
		var x = flowObjects[nodeObjects[selectedNodes[0]]["flowID"]]["x"]
		var y = flowObjects[nodeObjects[selectedNodes[0]]["flowID"]]["y"]-25
		$.ajax({url:"/conductEditor/"+conductID+"/flow/"+node+"/", type:"POST", data:JSON.stringify({action: "copy", operatorId: node, x: x, y: y}), contentType:"application/json", success: function ( result ) {
				// Coned sucessfull
			}
		});
	}
}

function duplicateFlowObject() {
	selectedNodes = network.getSelectedNodes()
	if (selectedNodes.length == 1) {
		node = nodeObjects[selectedNodes[0]]["flowID"]
		var conductID = GetURLParameter("conductID")
		var x = flowObjects[nodeObjects[selectedNodes[0]]["flowID"]]["x"]
		var y = flowObjects[nodeObjects[selectedNodes[0]]["flowID"]]["y"]-25
		$.ajax({url:"/conductEditor/"+conductID+"/flow/"+node+"/", type:"POST", data:JSON.stringify({action: "clone", operatorId: node, x: x, y: y}), contentType:"application/json", success: function ( result ) {
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
		if (params["nodes"].length > 0) {
			pos = network.getPositions(params["nodes"]);
			var conductID = GetURLParameter("conductID")
			for (node in params["nodes"]) {
				// Slow need to allow batch updates in future in the backend
				$.ajax({url:"/conductEditor/"+conductID+"/flow/"+nodeObjects[params["nodes"][node]]["flowID"]+"/", type:"POST", data: JSON.stringify({action: "update", x : pos[params["nodes"][node]]["x"], y : pos[params["nodes"][node]]["y"] }), contentType:"application/json", success: function( responseData ) {
					}
				});
			}
		}
		return false;
	});

	network.on("click", function(params) {
		if (params["nodes"].length == 1) {
			if (cKeyState) {
				createLink(selectedObject,nodeObjects[params["nodes"][0]]["flowID"],"blue",true);
			}
			selectedObject = nodeObjects[params["nodes"][0]]["flowID"]
		} else {
			selectedObject = null;
		}
		return true;
	});

	network.on("doubleClick", function(params) {
		if (params["nodes"].length == 1) {
			createPropertiesPanel(nodeObjects[params["nodes"][0]]["flowID"]);
		}
		if ((params["nodes"].length == 0) && (params["edges"].length == 1)) {
			link = flowLinks[params["edges"][0]]
			to = link["to"]
			from = link["from"]
			createLinkPropertiesPanel(from,to);
		}
		return true;
	});

	updateFlowchart(true);
	autoupdate();
}


