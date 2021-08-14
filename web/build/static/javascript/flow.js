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
var previousSelectedObject = null;
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
		if (confirm("Are you sure you want to remove object '"+ node +"' from this conduct?")) {
			var conductID = GetURLParameter("conductID");
			$.ajax({url:"/conductEditor/"+conductID+"/flow/"+node+"/", data: JSON.stringify({ CSRF: CSRF }), type:"DELETE", contentType:"application/json", success: function ( responseData ) {
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
		$.ajax({url:"/conductEditor/"+conductID+"/flowLink/"+from+"/"+to+"/", data: JSON.stringify({ CSRF: CSRF }), type:"DELETE", contentType:"application/json", success: function ( responseData ) {
				deleteLink(from,to)
			}
		});
	}
}

function updateNode(flow) {
	if (flow["flowID"] in flowObjects == false) {
		flowObjects[flow["flowID"]] = { "flowID": flow["flowID"], "flowType": flow["flowType"], "nodeID": nextId, "_id": flow["_id"], "name" : flow["name"], "node" : flow["node"] }
		nodeObjects[nextId] = { "flowID": flow["flowID"], "nodeID": nextId }
		flowObjects[flow["flowID"]]["node"]["id"] = nextId
		nodes.add(flowObjects[flow["flowID"]]["node"])
		nextId++;
	} else {
		flow["node"]["id"] = flowObjects[flow["flowID"]]["nodeID"]
		if ( "name" in flow ) {
			flowObjects[flow["flowID"]]["name"] = flow["name"]
		}
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

function createLinkRAW(from,to,color,text) {
	var linkName = from + "->" + to;
	flowLinks[linkName] = { "from": from, "to": to, "color": color, "text" : text }
	edges.add({ 
		id: linkName,
		from: flowObjects[from]["nodeID"], 
		to: flowObjects[to]["nodeID"],
		label: text,
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
		width: 1.5
	 });
	nextId++;
}

function updateLink(from,to,color,text) {
	var linkName = from + "->" + to;
	flowLinks[linkName]["from"] = from
	flowLinks[linkName]["to"] = to
	flowLinks[linkName]["color"] = color
	flowLinks[linkName]["text"] = text
	edges.update({ 
		id: linkName,
		from: flowObjects[from]["nodeID"], 
		to: flowObjects[to]["nodeID"],
		color: color,
		label: text
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

function createLink(from,to,colour,text,save) {
	if (from == to) {
		var conductID = GetURLParameter("conductID")
		$.ajax({url:"/conductEditor/"+conductID+"/flowLink/"+from+"/"+to+"/", type:"DELETE", contentType:"application/json"});
		return false
	}

	if (save) {
		var conductID = GetURLParameter("conductID")
		$.ajax({url:"/conductEditor/"+conductID+"/flowLink/"+from+"/"+to+"/", data: JSON.stringify({ CSRF: CSRF }), type:"PUT", contentType:"application/json", success: function ( responseData ) {
				if (createLinkRAW(from,to,colour,text)) {
					return true;
				} else {
					//$.ajax({url:"/conductEditor/"+conductID+"/flowLink/"+from+"/"+to+"/", type:"DELETE", contentType:"application/json"});
					return false
				}
			}
		});
	} else {
		var conductID = GetURLParameter("conductID")
		if (createLinkRAW(from,to,colour,text)) {
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
	$.ajax({url:"/conductEditor/"+conductID+"/flowLink/"+from+"/"+to+"/", data: JSON.stringify({ CSRF: CSRF }), type:"PUT", contentType:"application/json", success: function ( responseData ) {
			return true;
		}
	});
}

function updateFlowchartNonBlocking(blocking) {
	nonlock = 0
	// Operator Updates
	for (operator in processlist["operators"]["update"]) {
		nodes.update(processlist["operators"]["update"][operator])
		delete processlist["operators"]["update"][operator]
		nonlock++
		if ((!blocking) && (nonlock > 0)) {
			setTimeout(function() { updateFlowchartNonBlocking() }, 10);
			return
		}
	}
	// Operator Creates
	for (operator in processlist["operators"]["create"]) {
		node.add(processlist["operators"]["create"][operator])
		delete processlist["operators"]["create"][operator]
		nonlock++
		if ((!blocking) && (nonlock > 0)) {
			setTimeout(function() { updateFlowchartNonBlocking() }, 10);
			return
		}
	}
	// Operator Deletions
	for (operator in processlist["operators"]["delete"]) {
		obj = processlist["operators"]["delete"][operator]
		node.delete()
		deleteNode(obj["flowID"]);
		delete processlist["operators"]["delete"][operator]
		nonlock++
		if ((!blocking) && (nonlock > 0)) {
			setTimeout(function() { updateFlowchartNonBlocking() }, 10);
			return
		}
	}
	// Link Creates
	for (link in processlist["links"]["create"]) {
		obj = processlist["links"]["create"][link]
		edges.update(processlist["links"]["update"][link])
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
		edges.update(processlist["links"]["update"][link])
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
		edges.remove({ 
			id: obj["linkName"]
		});
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
		$.ajax({url:"/conductEditor/"+conductID+"/", type:"POST", timeout: 2000, data: JSON.stringify({ lastPollTime : lastUpdatePollTime, operators: nodes.get(), links: edges.get(), CSRF: CSRF }), contentType:"application/json", success: function ( responseData ) {
				if ((responseData["operators"]["nodes"].length > 0) || (responseData["links"]["links"].length > 0)) {
					nodes = new vis.DataSet(responseData["operators"]["nodes"]);
					edges = new vis.DataSet(responseData["links"]["links"]);
					network.setData({"nodes" : nodes, "edges" : edges});
					network.fit()
					setTimeout(updateFlowchart, 2500);
					return;
				}
				processlist = responseData
				var activeUsers = processlist["currentUsers"].join(", ");
				if (activeUsers != document.getElementById("activeUsers").innerHTML)
				{
					document.getElementById("activeUsers").innerHTML=activeUsers;
				}
				setTimeout(updateFlowchart, 2500);
				setTimeout(function() { updateFlowchartNonBlocking(true) }, 10);
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
	node = network.getSelectedNodes()
	if (node.length == 1) {
		node = nodeObjects[node[0]]["flowID"]
		createTriggerObjectPanel(node);
	}
}

function debugFlowObject() {
	selectedNodes = network.getSelectedNodes()
	if (selectedNodes.length == 1) {
		node = nodeObjects[selectedNodes[0]]["flowID"]
		var conductID = GetURLParameter("conductID")
		$.ajax({url: "/conduct/"+conductID+"/debug/"+node+"/", type:"GET", contentType:"application/json", success: function ( result ) {
				$.ajax({url: "/api/1.0/debug/", type:"POST", data:JSON.stringify({ "filter" : result["_id"], "level" : 100, CSRF: CSRF}), contentType:"application/json", success: function ( result ) {
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

function editACL() {
	selectedNodes = network.getSelectedNodes()
	if (selectedNodes.length == 1) {
		node = nodeObjects[selectedNodes[0]]["flowID"]
		createACLValuesPanel(node);
	}
}

function deleteFlowObject() {
	deleteSelected()
}

function exportConduct() {
	var conductID = GetURLParameter("conductID")
	window.open("/conductEditor/"+conductID+"/export/", "_blank");
}

function exportFlowObject() {
	selectedNodes = network.getSelectedNodes()
	if (selectedNodes.length == 1) {
		node = nodeObjects[selectedNodes[0]]["flowID"]
		var conductID = GetURLParameter("conductID")
		window.open("/conductEditor/"+conductID+"/export/?flowID="+node, "_blank");
	}
}

function CodifyFlowObject() {
	selectedNodes = network.getSelectedNodes()
	if (selectedNodes.length == 1) {
		node = nodeObjects[selectedNodes[0]]["flowID"]
		var conductID = GetURLParameter("conductID")
		window.open("/conductEditor/"+conductID+"/codify/?flowID="+node, "_blank");
	}
}

function importConduct() {
	var conductID = GetURLParameter("conductID")
	window.open("/conductEditor/"+conductID+"/import/", "_blank");
}

function codifyConduct() {
	var conductID = GetURLParameter("conductID")
	window.open("/conductEditor/"+conductID+"/codify/", "_blank");
}

function debugConduct() {
	var conductID = GetURLParameter("conductID")
	window.open("/debugFlow/?conductID="+conductID, "_blank");
}

function copyFlowObject() {
	selectedNodes = network.getSelectedNodes()
	if (selectedNodes.length == 1) {
		node = nodeObjects[selectedNodes[0]]["flowID"]
		var conductID = GetURLParameter("conductID")
		var x = flowObjects[nodeObjects[selectedNodes[0]]["flowID"]]["node"]["x"]
		var y = flowObjects[nodeObjects[selectedNodes[0]]["flowID"]]["node"]["y"]-25
		$.ajax({url:"/conductEditor/"+conductID+"/flow/"+node+"/", type:"POST", data:JSON.stringify({action: "copy", operatorId: node, x: x, y: y, CSRF: CSRF}), contentType:"application/json", success: function ( result ) {
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
		var x = flowObjects[nodeObjects[selectedNodes[0]]["flowID"]]["node"]["x"]
		var y = flowObjects[nodeObjects[selectedNodes[0]]["flowID"]]["node"]["y"]-25
		$.ajax({url:"/conductEditor/"+conductID+"/flow/"+node+"/", type:"POST", data:JSON.stringify({action: "clone", operatorId: node, x: x, y: y, CSRF: CSRF}), contentType:"application/json", success: function ( result ) {
				// Coned sucessfull
			}
		});
	}
}

function connectFlowObject() {
	if (selectedObject != null && previousSelectedObject != null)
	{
		if (selectedObject[0] == "flowObject" && previousSelectedObject[0] == "flowObject") {
			createLink(previousSelectedObject[1],selectedObject[1],"#3dbeff","",true);
		}
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
			multiselect: true,
			hover: false
		},
	};
	network = new vis.Network(container, data, options);

	network.on("dragEnd", function(params) {
		if (params["nodes"].length > 0) {
			pos = network.getPositions(params["nodes"]);
			var conductID = GetURLParameter("conductID")
			for (node in params["nodes"]) {
				// Slow need to allow batch updates in future in the backend
				$.ajax({url:"/conductEditor/"+conductID+"/flow/"+nodeObjects[params["nodes"][node]]["flowID"]+"/", type:"POST", data: JSON.stringify({action: "update", x : pos[params["nodes"][node]]["x"], y : pos[params["nodes"][node]]["y"], CSRF: CSRF }), contentType:"application/json", success: function( responseData ) {
					}
				});
			}
		}
		return false;
	});

	network.on("click", function(params) {
		if (selectedObject != null)
		{
			if (selectedObject[1].hasOwnProperty("deselect")) {
				selectedObject[1]["deselect"]()
			}
		}

		previousSelectedObject = selectedObject
		if (params["nodes"].length == 1) {
			if (cKeyState) {
				if (selectedObject[0] == "flowObject")
				{
					createLink(selectedObject[1],nodeObjects[params["nodes"][0]]["flowID"],"#3dbeff","",true);
				}
			}
			selectedObject = ["flowObject",nodeObjects[params["nodes"][0]]["flowID"]]
		} else {
			selectedObject = null;
		}

		if (previousSelectedObject != null) {
			$("#connectFlowObject").show();
		} else {
			$("#connectFlowObject").hide();
		}

		return true;
	});

	network.on("oncontext", function(params) {
		nodeID = (network.getNodeAt({ "x" : params["pointer"]["DOM"]["x"], "y" : params["pointer"]["DOM"]["y"] }));
		if ((nodeID) || (nodeID == 0)) {
			network.setSelection({ "nodes" : [nodeID] });
			previousSelectedObject = selectedObject
			selectedObject = ["flowObject",nodeObjects[nodeID]["flowID"]]
			if (previousSelectedObject != null) {
				$("#connectFlowObject").show();
			} else {
				$("#connectFlowObject").hide();
			}
			if (flowObjects[nodeObjects[nodeID]["flowID"]]["flowType"] == "trigger") {
				var menuHTML = ".contextMenuTrigger";
			} else {
				$(".contextMenuTrigger").hide();
			}
			if (flowObjects[nodeObjects[nodeID]["flowID"]]["flowType"] == "action") {
				var menuHTML = ".contextMenuAction";
			} else {
				$(".contextMenuAction").hide();
			}
			var $menu = $(menuHTML).show()
				.css({
					position: "absolute",
					left: getMenuPosition(params["pointer"]["DOM"]["x"], 'width', 'scrollLeft', $(menuHTML)),
					top: getMenuPosition(params["pointer"]["DOM"]["y"], 'height', 'scrollTop',$(menuHTML))
				})
				.off('click')
				.on('click', 'a', function (e) {
					$menu.hide();
			});
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
}


