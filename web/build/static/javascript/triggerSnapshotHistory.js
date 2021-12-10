var panelTriggerSnapshotHistoryHTML = `
<div class="propertiesPanel theme-panelContainer">
	<div class="propertiesPanel-header theme-panelHeader">
		<span class="glyphicon glyphicon glyphicon-remove" id="close"></span>
		<label id="title"></label>
	</div>
	<div class="propertiesPanel-body theme-panelBody">
		<table width="100%" id="snapshotHistoryTable">
		</table>
	</div>
	<div class="propertiesPanel-footer theme-panelFooter">
		<button id="refresh" class="btn btn-primary button bi-recycle"> Refresh</button>
		<button id="close" class="btn btn-primary button">Close</button>
	</div>
</div>
`

var openTriggerSnapshotHistoryPanels = {}

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
				if (selectedObject[0] == "triggerSnapshotHistory") {
					selectedObject[1]["panel"].find("#close").click();
				}
			}
		}
	})
});

function loadTriggerSnapshotHistoryPanel(panel,triggerID,init=false) {
	panel.find("#title").text("Trigger Snapshots");
	$.ajax({ url: "/api/1.0/debug/snapshot/"+triggerID+"/", type : "GET", success: function( result ) {
			panel.find('#snapshotHistoryTable').empty();
			for (x in result["results"]) {
				snapshot = result["results"][x]
				var row = $('<tr>')
				var createdTime = $('<td>').text(localTime(snapshot["time"]))
				row.append(createdTime)
				var options = $('<td>').append($('<button class="btn btn-primary button" onClick=openTriggerSnapshotHistory("'+snapshot["eventUID"]+'")>').text("Open"))
				row.append(options)
				panel.find('#snapshotHistoryTable').append(row);
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

function openTriggerSnapshotHistory(eventUID) {
	var conductID = GetURLParameter("conductID")
	$.ajax({ url: "/api/1.0/debug/snapshot/"+eventUID+"/", type : "PUT", data:JSON.stringify({CSRF: CSRF}), success: function( result ) {
			var win = window.open("/debugFlow/?conductID="+conductID+"&debugID="+result["sessionID"], '_blank');
			if (win) {
				win.focus();
			} else {
				alert('Popups disabled!');
			}
		}
	});	
}

function createTriggerSnapshotHistoryPanel(triggerID) {
	var panelID = triggerID
	if (!openTriggerSnapshotHistoryPanels.hasOwnProperty(panelID)) {
		openTriggerSnapshotHistoryPanels[panelID] = panelID;
		var panel = $(panelTriggerSnapshotHistoryHTML);
		panel.draggable({handle: ".propertiesPanel-header"});
		panel.resizable({
			grid: 20
		});

		panel.attr("id",panelID);

		$('.ui-main').find(".propertiesPanel").css("z-index", 1);
		panel.find(".propertiesPanel-header").addClass("theme-panelHeader-Active");
		selectedObject = ["triggerSnapshotHistory",{"panel" : panel, "flowID" : null, "deselect" :function(){ panel.find(".propertiesPanel-header").removeClass("theme-panelHeader-Active"); }}]

		// Events
		panel.click(function () {
			$('.ui-main').find(".propertiesPanel").css("z-index", 1);
			$(this).css("z-index", 2);
			panel.find(".propertiesPanel-header").addClass("theme-panelHeader-Active");
			panel.css("z-index", 2);
			selectedObject = ["triggerSnapshotHistory",{"panel" : panel, "flowID" : null, "deselect" : function(){ panel.find(".propertiesPanel-header").removeClass("theme-panelHeader-Active"); }}]
		})

		panel.find("#close").click(function () { 
			delete openTriggerSnapshotHistoryPanels[panelID];
			panel.remove();
		})

		panel.find("#refresh").click(function () { 
			loadTriggerSnapshotHistoryPanel(panel,triggerID);
		})

		// Loading properties form
		loadTriggerSnapshotHistoryPanel(panel,triggerID,true);
	
		// Applying object to UI
		$('.ui-main').append(panel);
	}
}
