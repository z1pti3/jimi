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
});

function autoupdate() {
	setTimeout(updateFlowchart, 2500);
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

function createLinkRAW(from,to,color) {
	var linkName = from + "->" + to;
	flowLinks[linkName] = { "from": from, "to": to, "color": color }
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
		width: 1.5
	 });
	nextId++;
}

function updateLink(from,to,color) {
	var linkName = from + "->" + to;
	flowLinks[linkName]["from"] = from
	flowLinks[linkName]["to"] = to
	flowLinks[linkName]["color"] = color
	edges.update({ 
		id: linkName,
		from: flowObjects[from]["nodeID"], 
		to: flowObjects[to]["nodeID"],
		color: color
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

function updateFlowchartNonBlocking(blocking) {
	nonlock = 0
	// Operator Updates
	for (operator in processlist["operators"]["update"]) {
		updateNode(processlist["operators"]["update"][operator]);
		delete processlist["operators"]["update"][operator]
		nonlock++
		if ((!blocking) && (nonlock > 0)) {
			setTimeout(function() { updateFlowchartNonBlocking() }, 10);
			return
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
		obj = processlist["operators"]["delete"][operator]
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
		createLinkRAW(obj["from"],obj["to"],obj["color"])
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
		updateLink(obj["from"],obj["to"],obj["color"])
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
		$.ajax({url:"/conductEditor/"+conductID+"/", type:"POST", timeout: 2000, data: JSON.stringify({ lastPollTime : lastUpdatePollTime, operators: flowObjects, links: flowLinks, CSRF: CSRF }), contentType:"application/json", success: function ( responseData ) {
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

function editFlowObject() {
	selectedNodes = network.getSelectedNodes()
	if (selectedNodes.length == 1) {
		node = nodeObjects[selectedNodes[0]]["flowID"]
		createPropertiesPanel(node);
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
        nodes : {
            fixed: {
                x: true,
                y: true
            }
        }
	};
	network = new vis.Network(container, data, options);

	network.on("click", function(params) {
		if (selectedObject != null)
		{
			if (selectedObject[1].hasOwnProperty("deselect")) {
				selectedObject[1]["deselect"]()
			}
		}
		if (params["nodes"].length == 1) {
			selectedObject = ["flowObject",nodeObjects[params["nodes"][0]]["flowID"]]
			nodeSelectionChange(nodeObjects[params["nodes"][0]]["flowID"]);
		} else {
			$('.eventItemInner').removeClass('click')
			clearSelection();
		}
		return true;
	});

	network.on("oncontext", function(params) {
		selectedNodes = network.getSelectedNodes()
		if (selectedNodes.length == 1) {
			offsetLeft = $("#flowchart").offset().left;
			nodeID = (network.getNodeAt({ "x" : params["pointer"]["DOM"]["x"], "y" : params["pointer"]["DOM"]["y"] }));
			if ((nodeID) || (nodeID == 0)) {
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
						left: getMenuPosition(params["pointer"]["DOM"]["x"]+offsetLeft, 'width', 'scrollLeft', $(menuHTML)),
						top: getMenuPosition(params["pointer"]["DOM"]["y"], 'height', 'scrollTop',$(menuHTML))
					})
					.off('click')
					.on('click', 'a', function (e) {
						$menu.hide();
				});
			}
			return true;
		}
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





// Debug Controls
executedFlows = {};
selectedExecutedFlowUID = null;
eventIndex = 0;
debugSession = null;

$.ajax({url:"/api/1.0/debug/", type:"PUT", timeout: 2000, data: JSON.stringify({ CSRF : CSRF }), contentType:"application/json", success: function ( responseData ) {
		debugSession = responseData["sessionID"];
		refreshDebugSession();
	}
});

function runDebugger() {
	selectedNodes = network.getSelectedNodes()
	if (selectedNodes.length == 1) {
		node = nodeObjects[selectedNodes[0]]["flowID"]
		var conductID = GetURLParameter("conductID")
		$.ajax({url:"/api/1.0/debug/"+debugSession+"/"+conductID+"/"+node+"/", type:"POST", data:JSON.stringify({CSRF: CSRF}), contentType:"application/json", success: function ( result ) {
				// Triggered flow
			}
		});
	}
}

function refreshDebugSession() {
	var uid = selectedExecutedFlowUID;
	$.ajax({url:"/api/1.0/debug/"+debugSession+"/list/", type:"GET", timeout: 2000, contentType:"application/json", success: function ( flowList ) {
			for (index in flowList["flowList"]) {
				if (!(flowList["flowList"][index]["id"] in executedFlows)) {
					addExecutedFlowEvent(flowList["flowList"][index]["id"],flowList["flowList"][index]["event"]);
				}
			}
			if (uid != null) {
				$.ajax({url:"/api/1.0/debug/"+debugSession+"/"+uid+"/executionList/", type:"GET", timeout: 2000, contentType:"application/json", success: function ( executionList ) {
						for (index in executionList["executionList"]) {
							if (!(executionList["executionList"][index]["id"] in executedFlows[uid]["execution"])) {
								addExecutedFlowEventResult(uid,executionList["executionList"][index]["id"],executionList["executionList"][index]["name"]);
							}
						}
					}
				});
			}
			setTimeout(refreshDebugSession, 1500);
		}
	});
}

function addExecutedFlowEvent(uid,event) {
	var parent = $('<div id="eventItem'+uid+'" class="eventItem">').attr({ "eventID" : uid }).html(event);
	parent.click(function () {
		clearSelection();
		$(".eventItemInner").addClass("hide");
		uid = $(this).attr("eventID")
		$.ajax({url:"/api/1.0/debug/"+debugSession+"/"+uid+"/executionList/", type:"GET", timeout: 2000, contentType:"application/json", success: function ( executionList ) {
				for (index in executionList["executionList"]) {
					if (!(executionList["executionList"][index]["id"] in executedFlows[uid]["execution"])) {
						addExecutedFlowEventResult(uid,executionList["executionList"][index]["id"],executionList["executionList"][index]["name"]);
					}
				}
			}
		});
		$(".eventItem"+uid).toggleClass("hide");
		selectedExecutedFlowUID = uid;
	});
	$(".eventList").append(parent);
	$(".eventList").append($('<div id="eventItemTop'+uid+'" class="hide">'));
	executedFlows[uid] = { "execution" : {} };
}

function addExecutedFlowEventResult(uid,executionUID,executionName) {
	var child = $('<div id="eventItem'+executionUID+'" class="eventItem'+uid+' eventItemInner">').attr({"eventID" : uid, "executionID" : executionUID}).html(executionName);
	child.insertBefore($("#eventItemTop"+uid));
	child.click(function () {
		clearSelection();
		$('.eventItemInner').removeClass('click')
		$(this).addClass('click');
		executionUID = $(this).attr("executionID")
		network.setSelection({ "nodes" : [] });
		$.ajax({url:"/api/1.0/debug/"+debugSession+"/"+selectedExecutedFlowUID+"/"+executionUID+"/", type:"GET", timeout: 2000, contentType:"application/json", success: function ( executionData ) {
				setSelection(executionData);
				network.setSelection({ "nodes" : [flowObjects[executionData["flowID"]]["nodeID"]] });
			}
		});
	});
	executedFlows[uid]["execution"][executionUID] = {}
}

function clearExecutedFlows() {
	$(".eventList").clear();
	executedFlows = {}
	eventIndex = 0
}

function nodeSelectionChange(flowID) {
	clearSelection();
	$('.eventItemInner').removeClass('click')
	if (selectedExecutedFlowUID!=null) {
		$.ajax({url:"/api/1.0/debug/"+debugSession+"/"+selectedExecutedFlowUID+"/"+flowID+"/flowID", type:"GET", timeout: 2000, contentType:"application/json", success: function ( executionData ) {
				setSelection(executionData);
				console.log(executionData)
				$('#eventItem'+executionData["id"]).addClass('click');
				network.setSelection({ "nodes" : [flowObjects[executionData["flowID"]]["nodeID"]] });
			}
		});
	}
}

function setSelection(execution) {
	$("#debugFlowEditor-in").val(JSON.stringify(execution["dataIn"], null, 5));
	$("#debugFlowEditor-out").val(JSON.stringify(execution["dataOut"], null, 5));
}

function clearSelection() {
	$("#debugFlowEditor-in").val("");
	$("#debugFlowEditor-out").val("");
}