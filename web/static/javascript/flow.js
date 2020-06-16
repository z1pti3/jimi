// Globals
var mouseOverOperator;
var mouseHold;
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
var processlist = {};
var init = false;

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
	setTimeout(updateFlowchart, 2500);
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

function updateNode(flow) {
	if (flow["flowID"] in flowObjects == false) {
		flowObjects[flow["flowID"]] = { "flowID": flow["flowID"], "flowType": flow["flowType"], "nodeID": nextId, "_id": flow["_id"], "node" : flow["node"] }
		nodeObjects[nextId] = { "flowID": flow["flowID"], "nodeID": nextId }
		flowObjects[flow["flowID"]]["node"]["id"] = nextId
		nodes.add(flowObjects[flow["flowID"]]["node"])
		nextId++;
	} else {
		flow["node"]["id"] = flowObjects[flow["flowID"]]["nodeID"]
		if (("x" in flow["node"] || "y" in flow["node"]) && ("color" in flow["node"] == false) && ("label" in flow["node"] == false)) {
			flowObjects[flow["flowID"]]["node"]["x"] = flow["node"]["x"]
			flowObjects[flow["flowID"]]["node"]["y"] = flow["node"]["y"]
			network.moveNode(flowObjects[flow["flowID"]]["nodeID"],flow["node"]["x"],flow["node"]["y"])
		} else {
			if ("x" in flow["node"] || "y" in flow["node"]) {
				flowObjects[flow["flowID"]]["node"]["x"] = flow["node"]["x"]
				flowObjects[flow["flowID"]]["node"]["y"] = flow["node"]["y"]
			}
			if ("color" in flow["node"]) {
				flowObjects[flow["flowID"]]["node"]["color"] = flow["node"]["color"]
			}
			if ("label" in flow["node"]) {
				flowObjects[flow["flowID"]]["node"]["label"] = flow["node"]["label"]
			}
			nodes.update(flow["node"])
		}
	}
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
		width: 2.5
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

function updateFlowchartNonBlocking(blocking) {
	nonlock = 0
	// Operator Updates
	for (operator in processlist["operators"]["update"]) {
		if (selectedObject != operator) {
			updateNode(processlist["operators"]["update"][operator]);
			delete processlist["operators"]["update"][operator]
			nonlock++
			if ((!blocking) && (nonlock > 0)) {
				setTimeout(function() { updateFlowchartNonBlocking() }, 10);
				return
			}
		}
	}
	// Operator Creates
	for (operator in processlist["operators"]["create"]) {
		updateNode(processlist["operators"]["create"][operator]);
		delete processlist["operators"]["create"][operator]
		nonlock++
		if ((!blocking) && (nonlock > 0)) {
			setTimeout(function() { updateFlowchartNonBlocking() }, 10);
			return
		}
	}
	// Operator Deletions
	for (operator in processlist["operators"]["delete"]) {
		if (selectedObject != operator) {
			obj = processlist["operators"]["delete"][operator]
			deleteNode(obj["flowID"]);
			delete processlist["operators"]["delete"][operator]
			nonlock++
			if ((!blocking) && (nonlock > 0)) {
				setTimeout(function() { updateFlowchartNonBlocking() }, 10);
				return
			}
		}
	}
	// Link Creates
	for (link in processlist["links"]["create"]) {
		obj = processlist["links"]["create"][link]
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
		delete processlist["links"]["create"][link]
		nonlock++
		if ((!blocking) && (nonlock > 0)) {
			setTimeout(function() { updateFlowchartNonBlocking() }, 10);
			return
		}
	}
	// Link Updates
	for (link in processlist["links"]["update"]) {
		obj = processlist["links"]["update"][link]
		updateLink(obj["from"],obj["to"])
		delete processlist["links"]["update"][link]
		nonlock++
		if ((!blocking) && (nonlock > 0)) {
			setTimeout(function() { updateFlowchartNonBlocking() }, 10);
			return
		}
	}
	// Link Deletions
	for (link in processlist["links"]["delete"]) {
		obj = processlist["links"]["delete"][link]
		linkName = obj["linkName"]
		edges.remove({ 
			id: linkName
		});
		delete flowLinks[linkName]
		delete processlist["links"]["delete"][link]
		nonlock++
		if ((!blocking) && (nonlock > 0)) {
			setTimeout(function() { updateFlowchartNonBlocking() }, 10);
			return
		}
	}
}

function updateFlowchart() {
	if ((processlist) || (processlist.length == 0)) {
		var conductID = GetURLParameter("conductID")
		$.ajax({url:"/conductEditor/"+conductID+"/", type:"POST", timeout: 2000, data: JSON.stringify({ lastPollTime : lastUpdatePollTime, operators: flowObjects, links: Object.keys(flowLinks) }), contentType:"application/json", success: function ( responseData ) {
				processlist = responseData
				setTimeout(updateFlowchart, 2500);
				if (init == false) {
					if (nodes.length > 0) {
						init = true;
						network.fit()
					}
					updateFlowchartNonBlocking(true);
					setTimeout(function() { updateFlowchartNonBlocking(true) }, 10);
				} else {
					setTimeout(function() { updateFlowchartNonBlocking(false) }, 10);
				}
				if (nodes.length > 0) {
					if (init == false) {
						init = true;
						network.fit()
					}
				}
			},
			error: function ( error ) {
				console.log("Unable to update flowChart");
				setTimeout(updateFlowchart, 2500);
			}
		});
	} else {
		setTimeout(updateFlowchart, 2500);
	}
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
	selectedNodes = network.getSelectedNodes()
	if (selectedNodes.length == 1) {
		node = nodeObjects[selectedNodes[0]]["flowID"]
		createPropertiesPanel(node);
	}
}

function deleteFlowObject() {
	deleteSelected()
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

	updateFlowchart();
	autoupdate();
}


