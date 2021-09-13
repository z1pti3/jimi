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

function loadObjectRevisionHistoryPanel(panel,objectType,objectID) {
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
						var options = $('<td>').append($('<button class="btn btn-primary button" onClick=restoreObjectRevisionHistory("'+classID+'","'+objectID+'","'+revision["_id"]+'")>').text("Restore"))
						row.append(options)
						var options = $('<td>').append($('<button class="btn btn-primary button" onClick=viewObjectRevisionHistory("'+classID+'","'+objectID+'","'+revision["_id"]+'")>').text("View"))
						row.append(options)
						panel.find('#objectRevisionsTable').append(row);
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

function restoreObjectRevisionHistory(classID,objectID,revisionID) {
	$.ajax({ url: "/api/1.0/revisions/"+classID+"/"+objectID+"/"+revisionID+"/", type : "GET", success: function( result ) {
			alert("Object restored!");
		}
	});	
}

function createObjectRevisionHistoryPanel(objectType,objectID) {
	panelID = objectType+"-"+objectID
	if (!openObjectRevisionHistoryPanels.hasOwnProperty(panelID)) {
		openObjectRevisionHistoryPanels[panelID] = panelID;
		var panel = $(panelObjectRevisionHistoryHTML);
		panel.draggable({handle: ".propertiesPanel-header"});
		panel.resizable({
			grid: 20
		});

		// Events
		panel.click(function () {
			$('.ui-main').find(".propertiesPanel").css("z-index", 1);
			$(this).css("z-index", 2);
		})

		panel.find("#close").click(function () { 
			delete openObjectRevisionHistoryPanels[panelID];
			panel.remove();
		})

		panel.find("#refresh").click(function () { 
			loadObjectRevisionHistoryPanel(panel,objectType,objectID);
		})

		// Loading properties form
		loadObjectRevisionHistoryPanel(panel,objectType,objectID);
	
		// Applying object to UI
		$('.ui-main').append(panel);

		// Set Initial Position
		height = $("#flowchart").height();
		width = $("#flowchart").width();
		var posX = (width/2) - (panel.width()/2);
		var posY = (height/2) - (panel.height()/2);
		panel.css({top : posY, left : posX});
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

		// Events
		panel.click(function () {
			$('.ui-main').find(".propertiesPanel").css("z-index", 1);
			$(this).css("z-index", 2);
		})

		panel.find("#close").click(function () { 
			delete openViewObjectRevisionHistoryPanels[panelID];
			panel.remove();
		})

		// Loading properties form
		panel.find(".propertiesPanel-body").append(buildForm(objectData));
	
		// Applying object to UI
		$('.ui-main').append(panel);

		// Set Initial Position
		height = $("#flowchart").height();
		width = $("#flowchart").width();
		var posX = (width/2) - (panel.width()/2);
		var posY = (height/2) - (panel.height()/2);
		panel.css({top : posY, left : posX});
		panel.css("z-index", 2);
	}
}