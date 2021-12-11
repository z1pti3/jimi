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
var previousSelectedObject = null;
var selectedObject = null;
var processlist = {};
var init = false;

$(document).ready(function () {
	setupFlowchart();
});

function autoupdate() {
	setTimeout(updateFlowchart, 2500);
}

function deleteSelected() {
	selectedNodes = network.getSelectedNodes()
	if (selectedNodes.length == 1) {
		node = nodes.get(selectedNodes[0])["id"]
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
		link = edges.get(links[0])
		var conductID = GetURLParameter("conductID");
		var to = link["to"]
		var from = link["from"]
		$.ajax({url:"/conductEditor/"+conductID+"/flowLink/"+from+"/"+to+"/", data: JSON.stringify({ CSRF: CSRF }), type:"DELETE", contentType:"application/json", success: function ( responseData ) {
				deleteLink(from,to)
			}
		});
	}
}

function deleteNode(flowID) {
	nodes.remove({ id: flowID })
}

function createLinkRAW(from,to,color,text) {
	var linkName = from + "->" + to;
	edges.add({ 
		id: linkName,
		from: from, 
		to: to,
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

function deleteLink(from,to) {
	var linkName = from + "->" + to;
	edges.remove({ id: linkName });
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
		nodes.add(processlist["operators"]["create"][operator])
		delete processlist["operators"]["create"][operator]
		nonlock++
		if ((!blocking) && (nonlock > 0)) {
			setTimeout(function() { updateFlowchartNonBlocking() }, 10);
			return
		}
	}
	// Operator Deletions
	for (operator in processlist["operators"]["delete"]) {
		nodes.remove({ id: processlist["operators"]["delete"][operator]["id"] })
		delete processlist["operators"]["delete"][operator]
		nonlock++
		if ((!blocking) && (nonlock > 0)) {
			setTimeout(function() { updateFlowchartNonBlocking() }, 10);
			return
		}
	}
	// Link Creates
	for (link in processlist["links"]["create"]) {
		edges.add(processlist["links"]["create"][link])
		delete processlist["links"]["create"][link]
		nonlock++
		if ((!blocking) && (nonlock > 0)) {
			setTimeout(function() { updateFlowchartNonBlocking() }, 10);
			return
		}
	}
	// Link Updates
	for (link in processlist["links"]["update"]) {
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
		edges.remove({ id: obj["id"] });
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

function debugFlowObject() {
	selectedNodes = network.getSelectedNodes()
	if (selectedNodes.length == 1) {
		node = nodes.get(selectedNodes[0])["id"]
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
		node = nodes.get(selectedNodes[0])["id"]
		createPropertiesPanel(node);
	}
}

function deleteFlowObject() {
	deleteSelected()
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
				$.ajax({url:"/conductEditor/"+conductID+"/flow/"+nodes.get(params["nodes"][node])["id"]+"/", type:"POST", data: JSON.stringify({action: "update", x : pos[params["nodes"][node]]["x"], y : pos[params["nodes"][node]]["y"], CSRF: CSRF }), contentType:"application/json", success: function( responseData ) {
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
		if (params["nodes"].length == 1) {
			selectedObject = ["flowObject",nodes.get(params["nodes"][0])["id"]]
			nodeSelectionChange(nodes.get(params["nodes"][0])["id"]);
		} else {
			clearSelection();
		}
		return true;
	});

	network.on("oncontext", function(params) {
		selectedNodes = network.getSelectedNodes()
		if (selectedNodes.length == 1) {
			offsetLeft = $("#flowchart").offset().left;
			offsetTop = $("#flowchart").offset().top;
			nodeID = (network.getNodeAt({ "x" : params["pointer"]["DOM"]["x"], "y" : params["pointer"]["DOM"]["y"] }));
			if ((nodeID) || (nodeID == 0)) {
				if (nodes.get(nodeID)["flowType"] == "trigger") {
					var menuHTML = ".contextMenuTrigger";
				} else {
					$(".contextMenuTrigger").hide();
				}
				if (nodes.get(nodeID)["flowType"] == "action") {
					var menuHTML = ".contextMenuAction";
				} else {
					$(".contextMenuAction").hide();
				}
				var $menu = $(menuHTML).show()
					.css({
						position: "absolute",
						left: getMenuPosition(params["pointer"]["DOM"]["x"]+offsetLeft, 'width', 'scrollLeft', $(menuHTML)),
						top: getMenuPosition(params["pointer"]["DOM"]["y"]+offsetTop, 'height', 'scrollTop',$(menuHTML))
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
			createPropertiesPanel(nodes.get(params["nodes"][0])["id"]);
		}
		if ((params["nodes"].length == 0) && (params["edges"].length == 1)) {
			to = edges.get(params["edges"][0])["to"]
			from = edges.get(params["edges"][0])["from"]
			createLinkPropertiesPanel(from,to);
		}
		return true;
	});

	updateFlowchart();
}





// Debug Controls
executedFlows = {};
selectedExecutedFlowUID = null;
selectedExecutedFlowPreserveDataID = -1;
eventIndex = 0;
debugSession = null;

function runDebuggerNew() {
	selectedNodes = network.getSelectedNodes()
	if (selectedNodes.length == 1) {
		node = nodes.get(selectedNodes[0])["id"]
		var conductID = GetURLParameter("conductID")
		$.ajax({url:"/api/1.0/debug/"+debugSession+"/"+conductID+"/"+node+"/", type:"POST", data:JSON.stringify({CSRF: CSRF}), contentType:"application/json", success: function ( result ) {
				// Triggered flow
			}
		});
	}
}

function clearDebugger() {
	$.ajax({url:"/api/1.0/debug/clear/"+debugSession+"/", type:"GET", contentType:"application/json", success: function ( result ) {
			clearExecutedFlows();
		}
	});
}

function runDebugger() {
	selectedNodes = network.getSelectedNodes()
	if (selectedNodes.length == 1) {
		dataIn = $("#debugFlowEditor-in").val()
		node = nodes.get(selectedNodes[0])["id"]
		var conductID = GetURLParameter("conductID")
		$.ajax({url:"/api/1.0/debug/"+debugSession+"/"+conductID+"/"+node+"/", type:"POST", data:JSON.stringify({dataIn : dataIn, preserveDataID : selectedExecutedFlowPreserveDataID, CSRF: CSRF}), contentType:"application/json", success: function ( result ) {
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
					var event = flowList["flowList"][index]["event"]
					if (event.constructor === Object) {
						event = JSON.stringify(event, null, 5)
					}
					addExecutedFlowEvent(flowList["flowList"][index]["id"],flowList["flowList"][index]["name"],event,flowList["flowList"][index]["preserveDataID"]);
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
			setTimeout(refreshDebugSession, 2500);
		}
	});
}

function addExecutedFlowEvent(uid,eventName,event,preserveDataID) {
	var parent = $('<div id="eventItem'+uid+'" class="eventItem">').attr({ "eventID" : uid, "preserveDataID" : preserveDataID, "event" : event }).html(eventName);
	parent.click(function () {
		clearSelection();
		$(".eventItemInner").addClass("hide");
		uid = $(this).attr("eventID")
		$("#debugFlowEditor-in-event").val($(this).attr("event"), null, 5);
		$("#debug_continue_button").prop('disabled', false);
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
		selectedExecutedFlowPreserveDataID = $(this).attr("preserveDataID");
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
		$(this).addClass('click');
		executionUID = $(this).attr("executionID")
		network.setSelection({ "nodes" : [] });
		$.ajax({url:"/api/1.0/debug/"+debugSession+"/"+selectedExecutedFlowUID+"/"+executionUID+"/", type:"GET", timeout: 2000, contentType:"application/json", success: function ( executionData ) {
				setSelection(executionData);
				network.setSelection({ "nodes" : [executionData["flowID"]] });
			}
		});
	});
	executedFlows[uid]["execution"][executionUID] = {}
}

function clearExecutedFlows() {
	$(".eventList").empty();
	executedFlows = {}
	eventIndex = 0
}

function nodeSelectionChange(flowID) {
	clearSelection();
	if (selectedExecutedFlowUID!=null) {
		$.ajax({url:"/api/1.0/debug/"+debugSession+"/"+selectedExecutedFlowUID+"/"+flowID+"/flowID/", type:"GET", timeout: 2000, contentType:"application/json", success: function ( executionData ) {
				setSelection(executionData);
				$('#eventItem'+executionData["id"]).addClass('click');
				network.setSelection({ "nodes" : [executionData["flowID"]] });
			}
		});
	}
}

function setSelection(execution) {
	$("#debug_continue_button").prop('disabled', false);
	$("#debugFlowEditor-in").val(JSON.stringify(execution["dataIn"], null, 5));
	$("#debugFlowEditor-in-event").val(JSON.stringify(execution["dataIn"]["flowData"]["event"], null, 5));
	$("#debugFlowEditor-in-action").val(JSON.stringify(execution["dataIn"]["flowData"]["action"], null, 5));
	$("#debugFlowEditor-in-var").val(JSON.stringify(execution["dataIn"]["flowData"]["var"], null, 5));
	$("#debugFlowEditor-out").val(JSON.stringify(execution["dataOut"], null, 5));
	$("#debugFlowEditor-out-event").val(JSON.stringify(execution["dataOut"]["flowData"]["event"], null, 5));
	$("#debugFlowEditor-out-action").val(JSON.stringify(execution["dataOut"]["flowData"]["action"], null, 5));
	$("#debugFlowEditor-out-var").val(JSON.stringify(execution["dataOut"]["flowData"]["var"], null, 5));
}

function clearSelection() {
	$('.eventItemInner').removeClass('click')
	$("#debug_continue_button").prop('disabled', true)
	$("#debugFlowEditor-in").val("");
	$("#debugFlowEditor-in-event").val("");
	$("#debugFlowEditor-in-action").val("");
	$("#debugFlowEditor-in-var").val("");
	$("#debugFlowEditor-out").val("");
	$("#debugFlowEditor-out-event").val("");
	$("#debugFlowEditor-out-action").val("");
	$("#debugFlowEditor-out-var").val("");
}

function getDebugSessions() {
	$.ajax({url:"/api/1.0/debug/", type:"GET", timeout: 2000, contentType:"application/json", success: function ( result ) {
			$('#existingDebugList').empty()
			for (debugSession in result["results"]) {
				var item = $('<div style="width:100%; height:45px">')
				item.append($('<span style="vertical-align: sub">').text(result["results"][debugSession]["id"] + " - " + result["results"][debugSession]["createdBy"]))
				item.append($('<button type="button" class="btn btn-primary button bi-play" style="display:inline; right:90px; position:absolute" onclick="loadDebugSession(\''+result["results"][debugSession]["id"]+'\')">').text(" Launch"));
				item.append($('<button class="btn btn-primary button bi-trash" style="display:inline; right:0; position:absolute" onclick="deleteDebugSession(\''+result["results"][debugSession]["id"]+'\')">').text(" Delete"))
				$('#existingDebugList').append(item);
			}
		}
	});
}

function newDebugSession() {
	$.ajax({url:"/api/1.0/debug/", type:"PUT", timeout: 2000, data: JSON.stringify({ CSRF : CSRF }), contentType:"application/json", success: function ( responseData ) {
			getDebugSessions();
		}
	});
}

function deleteDebugSession(debugID) {
	$.ajax({url:"/api/1.0/debug/"+debugID+"/", type:"DELETE", timeout: 2000, data: JSON.stringify({ CSRF : CSRF }), contentType:"application/json", success: function ( responseData ) {
			getDebugSessions();
		}
	});
}

function loadDebugSession(debugID) {
	debugSession = debugID;

	var url = location.href.split("&")[0]+"&debugID="+debugSession;
	window.location.replace(url,"_self");
	refreshDebugSession();
}

function showDebugSessions() {
	getDebugSessions();
	$("#debugSessions").modal('show');
}