var panelObjectRevisionHistoryHTML = `
<div class="propertiesPanel theme-panelContainer">
	<div class="propertiesPanel-header theme-panelHeader">
		<span class="glyphicon glyphicon glyphicon-remove" id="close"></span>
		<label id="title"></label>
	</div>
	<div class="propertiesPanel-body theme-panelBody">
		<table width="100%" id="objectRevisionsTable">
		</table>
	</div>
	<div class="propertiesPanel-footer theme-panelFooter">
		<button id="refresh" class="btn btn-primary button bi-recycle"> Refresh</button>
		<button id="close" class="btn btn-primary button">Close</button>
	</div>
</div>
`

var panelViewObjectRevisionHistoryHTML = `
<div class="propertiesPanel theme-panelContainer">
	<div class="propertiesPanel-header theme-panelHeader">
		<span class="glyphicon glyphicon glyphicon-remove" id="close"></span>
		<label id="title"></label>
	</div>
	<div class="propertiesPanel-body theme-panelBody">
		<table width="100%" id="objectRevisionsTable">
		</table>
	</div>
	<div class="propertiesPanel-footer theme-panelFooter">
		<button id="close" class="btn btn-primary button">Close</button>
	</div>
</div>
`

var openObjectRevisionHistoryPanels = {}
var openViewObjectRevisionHistoryPanels = {}

$(document).ready(function () {
	$(window).bind("keydown", function (event) { 
		if (event.ctrlKey || event.metaKey) {
			switch (String.fromCharCode(event.which).toLowerCase()) {
			case 's':
				event.preventDefault();
				break;
			}
		} else if (event.keyCode == 27) {
			if (selectedObject != null) {
				if (selectedObject[0] == "objectRevisionHistory" || selectedObject[0] == "viewObjectRevisionHistory") {
					selectedObject[1]["panel"].find("#close").click();
				}
			}
		}
	})
});

function loadObjectRevisionHistoryPanel(panel,objectType,objectID,init=false) {
	panel.find("#title").text("Object Revisions");
	$.ajax({ url: "/api/1.0/models/"+objectType+"/"+objectID+"/", type : "GET", success: function( result ) {
			classID= result["classID"]
			$.ajax({ url: "/api/1.0/revisions/"+classID+"/"+objectID+"/", type : "GET", success: function( result ) {
					panel.find('#objectRevisionsTable').empty();
					for (x in result["revisions"]) {
						revision = result["revisions"][x]
						var row = $('<tr>')
						var createdTime = $('<td>').text(localTime(revision["creationTime"]))
						row.append(createdTime)
						var id = $('<td>').text(revision["_id"])
						row.append(id)
						var createdBy = $('<td>').text(revision["createdBy"])
						row.append(createdBy)
						var options = $('<td>').append($('<button class="btn btn-primary button" onClick=restoreObjectRevisionHistory("'+classID+'","'+objectID+'","'+revision["_id"]+'","'+objectType+'")>').text("Restore"))
						row.append(options)
						var options = $('<td>').append($('<button class="btn btn-primary button" onClick=viewObjectRevisionHistory("'+classID+'","'+objectID+'","'+revision["_id"]+'")>').text("View"))
						row.append(options)
						panel.find('#objectRevisionsTable').append(row);
					}
					// Set Initial Position
					if (init) {
						height = $("#flowchart").height();
						width = $("#flowchart").width();
						// Checking for offset on conductEditor
						try {  
							offsetTop = $(".conductEditor-topBar").offset().top;
						} catch(error) {  
							offsetTop = 0; 
						}
						var posX = (width/2) - (panel.width()/2);
						var posY = (height/2) - (panel.height()/2) + offsetTop;
						panel.css({top : posY, left : posX});
					}
				}
			});
		}
	});
}

function viewObjectRevisionHistory(classID,objectID,revisionID) {
	$.ajax({ url: "/api/1.0/revisions/"+classID+"/"+objectID+"/"+revisionID+"/view/", type : "GET", success: function( result ) {
			createViewObjectRevisionHistoryPanel(classID,objectID,revisionID,result["formData"])
		}
	});	
}

function restoreObjectRevisionHistory(classID,objectID,revisionID,objectType) {
	$.ajax({ url: "/api/1.0/revisions/"+classID+"/"+objectID+"/"+revisionID+"/", type : "GET", success: function( result ) {
			alert("Object restored!");
			var panelID = objectType+"-"+objectID
			loadObjectRevisionHistoryPanel($('#'+panelID),objectType,objectID);
		}
	});	
}

function createObjectRevisionHistoryPanel(objectType,objectID) {
	var panelID = objectType+"-"+objectID
	if (!openObjectRevisionHistoryPanels.hasOwnProperty(panelID)) {
		openObjectRevisionHistoryPanels[panelID] = panelID;
		var panel = $(panelObjectRevisionHistoryHTML);
		panel.draggable({handle: ".propertiesPanel-header"});
		panel.resizable({
			grid: 20
		});

		panel.attr("id",panelID);

		panel.find(".propertiesPanel-header").addClass("theme-panelHeader-Active");
		panel.css("z-index", 2);
		selectedObject = ["objectRevisionHistory",{"panel" : panel, "flowID" : null, "deselect" : function(){ panel.find(".propertiesPanel-header").removeClass("theme-panelHeader-Active"); }}]

		// Events
		panel.click(function () {
			$('.ui-main').find(".propertiesPanel").css("z-index", 1);
			$(this).css("z-index", 2);
			panel.find(".propertiesPanel-header").addClass("theme-panelHeader-Active");
			panel.css("z-index", 2);
			selectedObject = ["objectRevisionHistory",{"panel" : panel, "flowID" : null, "deselect" : function(){ panel.find(".propertiesPanel-header").removeClass("theme-panelHeader-Active"); }}]
		})

		panel.find("#close").click(function () { 
			delete openObjectRevisionHistoryPanels[panelID];
			panel.remove();
		})

		panel.find("#refresh").click(function () { 
			loadObjectRevisionHistoryPanel(panel,objectType,objectID);
		})

		// Loading properties form
		loadObjectRevisionHistoryPanel(panel,objectType,objectID,true);
	
		// Applying object to UI
		$('.ui-main').append(panel);
	}
}


function createViewObjectRevisionHistoryPanel(classID,objectID,revisionID,objectData) {
	panelID = classID+"-"+revisionID+"-"+objectID
	if (!openViewObjectRevisionHistoryPanels.hasOwnProperty(panelID)) {
		openViewObjectRevisionHistoryPanels[panelID] = panelID;
		var panel = $(panelViewObjectRevisionHistoryHTML);
		panel.draggable({handle: ".propertiesPanel-header"});
		panel.resizable({
			grid: 20
		});

		panel.find(".propertiesPanel-header").addClass("theme-panelHeader-Active");
		panel.css("z-index", 2);
		selectedObject = ["viewObjectRevisionHistory",{"panel" : panel, "flowID" : null, "deselect" : function(){ panel.find(".propertiesPanel-header").removeClass("theme-panelHeader-Active"); }}]

		// Events
		panel.click(function () {
			$('.ui-main').find(".propertiesPanel").css("z-index", 1);
			$(this).css("z-index", 2);
			panel.find(".propertiesPanel-header").addClass("theme-panelHeader-Active");
			panel.css("z-index", 2);
			selectedObject = ["viewObjectRevisionHistory",{"panel" : panel, "flowID" : null, "deselect" : function(){ panel.find(".propertiesPanel-header").removeClass("theme-panelHeader-Active"); }}]
		})

		panel.find("#close").click(function () { 
			delete openViewObjectRevisionHistoryPanels[panelID];
			panel.remove();
		})

		// Loading properties form
		panel.find("#title").text("Object Revision "+revisionID+" - Preview");
		panel.find(".propertiesPanel-body").append(buildForm(objectData));
	
		// Applying object to UI
		$('.ui-main').append(panel);

		// Set Initial Position
		height = $("#flowchart").height();
		width = $("#flowchart").width();
		// Checking for offset on conductEditor
		try {  
			offsetTop = $(".conductEditor-topBar").offset().top;
		} catch(error) {  
			offsetTop = 0; 
		}
		var posX = (width/2) - (panel.width()/2);
		var posY = (height/2) - (panel.height()/2) + offsetTop;
		panel.css({top : posY, left : posX});
		panel.css("z-index", 2);
	}
}