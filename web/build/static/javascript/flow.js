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
	
	// Key events
	$(document).keydown(function(event) {
		switch (String.fromCharCode(event.which).toLowerCase()) {
			case 'c':
				cKeyState = true;
				break;
		}
		if (event.ctrlKey || event.metaKey) {
			if (event.keyCode == 67 & document.activeElement["className"] == "vis-network" & network.getSelectedNodes().length > 0) {
				$.ajax({url:"/conductEditor/"+GetURLParameter("conductID")+"/copyObjects", data: JSON.stringify({ CSRF: CSRF, "nodes": nodes.get(network.getSelectedNodes()), "edges": edges.get(network.getSelectedEdges()) }), type:"POST", contentType:"application/json", success: function ( result ) {
					dropdownAlert(null,"Success","Flow Objects Copied!",1000);
				}
			});
			}
			if (event.keyCode == 86 & document.activeElement["className"] == "vis-network" & network.getSelectedNodes().length == 0) {
				$.ajax({url:"/conductEditor/"+GetURLParameter("conductID")+"/pasteObjects", data: JSON.stringify({ CSRF: CSRF, "centre" : network.getViewPosition(), "forcePaste" : false }), type:"POST", contentType:"application/json", success: function ( result ) {
					dropdownAlert(null,"Success","Flow Objects Pasted!",1000);
				},
				error: function ( result ){
					if (result["status"] === 302){
						if (confirm(result["responseText"])) {
							$.ajax({url:"/conductEditor/"+GetURLParameter("conductID")+"/pasteObjects", data: JSON.stringify({ CSRF: CSRF, "centre" : network.getViewPosition(), "forcePaste" : true }), type:"POST", contentType:"application/json", success: function ( result ) {
								dropdownAlert(null,"Success","Flow Objects Pasted!",1000);
							},
							error: function ( result ){ dropdownAlert(null,"Error","Couldn't Paste Flow Objects!",1000); }});
						}
						else {
							dropdownAlert(null,"Info","Did not paste objects",1000);
						}
					}
					else {
						dropdownAlert(null,"Error",result["responseText"],1000);
					}
				}
				});
			}
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
		node = nodes.get(selectedNodes[0])["id"]
		if (confirm("Are you sure you want to remove object '"+ node +"' from this conduct?")) {
			var conductID = GetURLParameter("conductID");
			$.ajax({url:"/conductEditor/"+conductID+"/flow/"+node+"/", data: JSON.stringify({ CSRF: CSRF }), type:"DELETE", contentType:"application/json", success: function ( responseData ) {
					deleteNode(node)
				}
			});
		}
	}
	else if (selectedNodes.length > 1){
		nodeList = nodes.get(selectedNodes)
		if (confirm("Are you sure you want to remove multiple objects from this conduct?")) {
			var conductID = GetURLParameter("conductID");
			$.ajax({url:"/conductEditor/"+conductID+"/flow/multiple/", data: JSON.stringify({ CSRF: CSRF, "nodes": nodeList }), type:"DELETE", contentType:"application/json", success: function ( responseData ) {
					nodes.remove(responseData["flowIDs"]);
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

function editACL() {
	selectedNodes = network.getSelectedNodes()
	if (selectedNodes.length == 1) {
		node = nodes.get(selectedNodes[0])["id"]
		createACLValuesPanel(node);
	}
}

function editObjectSystemSettings() {
	selectedNodes = network.getSelectedNodes()
	if (selectedNodes.length == 1) {
		node = nodes.get(selectedNodes[0])["id"]
		createObjectSystemSettingsValuesPanel(node);
	}
}

function loadTriggerStatistics() {
	selectedNodes = network.getSelectedNodes()
	if (selectedNodes.length == 1) {
		node = nodes.get(selectedNodes[0])["objID"]
		window.open("/statistics/trigger/"+nodes.get(selectedNodes[0])["objID"]+"/", "_blank");
	}
}

function objectRevisionHistory() {
	selectedNodes = network.getSelectedNodes()
	if (selectedNodes.length == 1) {
		createObjectRevisionHistoryPanel(nodes.get(selectedNodes[0])["flowType"],nodes.get(selectedNodes[0])["objID"]);
	}
}

function triggerSanpshotHistory() {
	selectedNodes = network.getSelectedNodes()
	if (selectedNodes.length == 1) {
		createTriggerSnapshotHistoryPanel(nodes.get(selectedNodes[0])["objID"]);
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
		node = nodes.get(selectedNodes[0])["id"]
		var conductID = GetURLParameter("conductID")
		window.open("/conductEditor/"+conductID+"/export/?flowID="+node, "_blank");
	}
}

function editWithinModelEditor() {
	selectedNodes = network.getSelectedNodes()
	if (selectedNodes.length == 1) {
		node = nodes.get(selectedNodes[0])
		window.open("/modelEditor/?modelName="+node["flowType"]+"&_id="+node["objID"], "_blank");
	}
}

function CodifyFlowObject() {
	selectedNodes = network.getSelectedNodes()
	if (selectedNodes.length == 1) {
		node = nodes.get(selectedNodes[0])["id"]
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
		node = nodes.get(selectedNodes[0])["id"]
		var conductID = GetURLParameter("conductID")
		var x = nodes.get(selectedNodes[0])["x"]
		var y = nodes.get(selectedNodes[0])["y"]-25
		$.ajax({url:"/conductEditor/"+conductID+"/flow/"+node+"/", type:"POST", data:JSON.stringify({action: "copy", operatorId: node, x: x, y: y, CSRF: CSRF}), contentType:"application/json", success: function ( result ) {
				// Coned successful
			}
		});
	}
}

function addExistingObject(objectID,flowType) {
	pos = network.getViewPosition()
	var x = pos["x"]
	var y = pos["y"]
	var conductID = GetURLParameter("conductID")
	var $this = $(this);
	$.ajax({url:"/conductEditor/"+conductID+"/flow/", type:"POST", data:JSON.stringify({action: "drop", flowType: flowType, _id: objectID, x: x, y: y, CSRF: CSRF}), contentType:"application/json", success: function ( result ) {
		// Drop sucessfull
		}
	});
}

function addNewObject(classID) {
	var conductID = GetURLParameter("conductID")
	pos = network.getViewPosition()
	var x = pos["x"]
	var y = pos["y"]
	$.ajax({url:"/conductEditor/"+conductID+"/flow/", type:"PUT", data:JSON.stringify({classID: classID, x: x, y: y, CSRF: CSRF}), contentType:"application/json", success: function ( responseData ) {
			// Created new object
		}
	});
}

function duplicateFlowObject() {
	selectedNodes = network.getSelectedNodes()
	if (selectedNodes.length == 1) {
		node = nodes.get(selectedNodes[0])["id"]
		var conductID = GetURLParameter("conductID")
		var x = nodes.get(selectedNodes[0])["x"]
		var y = nodes.get(selectedNodes[0])["y"]-25
		$.ajax({url:"/conductEditor/"+conductID+"/flow/"+node+"/", type:"POST", data:JSON.stringify({action: "clone", operatorId: node, x: x, y: y, CSRF: CSRF}), contentType:"application/json", success: function ( result ) {
				// Coned successful
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

		previousSelectedObject = selectedObject
		if (params["nodes"].length == 1) {
			if (cKeyState) {
				if (selectedObject[0] == "flowObject")
				{
					createLink(selectedObject[1],nodes.get(params["nodes"][0])["id"],"#3dbeff","",true);
				}
			}
			selectedObject = ["flowObject",nodes.get(params["nodes"][0])["id"]]
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
			selectedObject = ["flowObject",nodes.get(nodeID)["id"]]
			if (previousSelectedObject != null) {
				$("#connectFlowObject").show();
			} else {
				$("#connectFlowObject").hide();
			}
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
			offsetLeft = $("#flowchart").offset().left;
			offsetTop = $("#flowchart").offset().top;
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
