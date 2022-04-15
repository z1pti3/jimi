function localTime(epoch) {
    function appendLeadingZeroes(n){
        if(n <= 9){
            return "0" + n;
        }
        return n
    }
    var d = new Date(0);
    d.setUTCSeconds(epoch);
    var formattedDate = appendLeadingZeroes(d.getDate()) + "-" + appendLeadingZeroes(d.getMonth()+1) + "-" + appendLeadingZeroes(d.getFullYear()) + " " + appendLeadingZeroes(d.getHours()) + ":" + appendLeadingZeroes(d.getMinutes()) + ":" + appendLeadingZeroes(d.getSeconds());
    return formattedDate;
}

function GetURLParameter(sParam) {
    var sPageURL = window.location.search.substring(1);
    var sURLVariables = sPageURL.split('&');
    for (var i = 0; i < sURLVariables.length; i++) 
    {
        var sParameterName = sURLVariables[i].split('=');
        if (sParameterName[0] == sParam) 
        {
            return sParameterName[1];
        }
    }
}

function sanitize(string) {
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#x27;',
        "/": '&#x2F;',
    };
    const reg = /[&<>"'/]/ig;
    return string.replace(reg, (match)=>(map[match]));
  }

  function syntaxHighlight(json) {
    if (typeof json != 'string') {
        json = JSON.stringify(json, undefined, 2);
    }
    json = json.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    return json.replace(/("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d*)?(?:[eE][+\-]?\d+)?)/g, function (match) {
        var cls = 'number';
        if (/^"/.test(match)) {
            if (/:$/.test(match)) {
                cls = 'key';
            } else {
                cls = 'string';
            }
        } else if (/true|false/.test(match)) {
            cls = 'boolean';
        } else if (/null/.test(match)) {
            cls = 'null';
        }
        return '<span class="theme-json' + cls + '">' + match + '</span>';
    });
}

function getMenuPosition(mouse, direction, scrollDir, menu) {
    var win = $(window)[direction](),
        scroll = $(window)[scrollDir](),
        menu = menu[direction](),
        position = mouse + scroll;
                
    // opening menu would pass the side of the page
    if (mouse + menu > win && menu < mouse) 
        position -= menu;
    
    return position;
}    

function buildForm(fromData) {
    var groups = {}
    var $table = $('<table width="100%">');
    for (objectItem in fromData) {
        var $row = $('<tr>');
        // Tooltips
        var tooltip = "";
        if (fromData[objectItem].hasOwnProperty("tooltip")) {
            tooltip = fromData[objectItem]["tooltip"]
        }
        // Custom Label
        var label = fromData[objectItem]["schemaitem"]
        if (fromData[objectItem].hasOwnProperty("label")) {
            label = fromData[objectItem]["label"]
        }

        // Required
        var required = false;
        if (fromData[objectItem].hasOwnProperty("required")) {
            required = fromData[objectItem]["required"]
            if (required) {
                label = label+"*";
            }
        }

        // Group
        var group = 0;
        if (fromData[objectItem].hasOwnProperty("group")) {
            group = fromData[objectItem]["group"]
        }
        
        if (fromData[objectItem]["type"] == "group-checkbox") {
            var $cell = $('<td>');
            $row.append($cell);
            var $cell = $('<td>');
            var $div = $('<div class="form-check form-switch">')
            var $checkbox = $('<input class="form-check-input" type="checkbox">').attr({required: required, id: "properties_items"+fromData[objectItem]["schemaitem"], current: fromData[objectItem]["checked"], checked: fromData[objectItem]["checked"], key: fromData[objectItem]["schemaitem"], tag: "formItem", "data-group" : group.toString()})
            var $label = $('<label class="form-check-label theme-panelLabel" for="flexSwitchCheckDefault">').attr({ for : "properties_items"+fromData[objectItem]["schemaitem"], "data-bs-toggle" : "tooltip", "title" : tooltip }).text(label)
            $div.append($checkbox)
            $div.append($label)
            $cell.append($div)
            $row.append($cell);
            $cell.find("#properties_items"+fromData[objectItem]["schemaitem"]).on('change', function() {
                if ($(this)[0].checked) {
                    $(".group_"+$(this).attr("data-group")).removeClass("hide")
                } else {
                    $(".group_"+$(this).attr("data-group")).addClass("hide")
                }
            });
            groups[group.toString()] = fromData[objectItem]["checked"];
            $row.append($cell);
        }
        if (fromData[objectItem]["type"] == "input") {
            var $cell = $('<td width="100px">');
            $cell.append($('<label>').attr({for: fromData[objectItem]["schemaitem"], "data-bs-toggle" : "tooltip", title : tooltip, class: "theme-panelLabel"}).text(label+":"));
            $row.append($cell);
            var $cell = $('<td>');
            $cell.append($('<input class="form-control form-control-sm full-width textbox">').attr({type: 'text', value: fromData[objectItem]["textbox"], current: fromData[objectItem]["textbox"], required: required, id: "properties_items"+fromData[objectItem]["schemaitem"], key: fromData[objectItem]["schemaitem"], tag: "formItem"}));
            $row.append($cell);
        }
        if (fromData[objectItem]["type"] == "checkbox") {
            var $cell = $('<td>');
            $row.append($cell);
            var $cell = $('<td>');
            var $div = $('<div class="form-check form-switch">')
            var $checkbox = $('<input class="form-check-input" type="checkbox">').attr({required: required, id: "properties_items"+fromData[objectItem]["schemaitem"], current: fromData[objectItem]["checked"], checked: fromData[objectItem]["checked"], key: fromData[objectItem]["schemaitem"], tag: "formItem"})
            var $label = $('<label class="form-check-label theme-panelLabel" for="flexSwitchCheckDefault">').attr({ for : "properties_items"+fromData[objectItem]["schemaitem"], "data-bs-toggle" : "tooltip", "title" : tooltip }).text(label)
            $div.append($checkbox)
            $div.append($label)
            $cell.append($div)
            $row.append($cell);
        }
        if (fromData[objectItem]["type"] == "json-input") {
            // output
            // <label for="delay" class="theme-panelLabel">delay:</label>					
            var $cell = $('<td width="100px">');
            $cell.append($('<label>').attr({for: fromData[objectItem]["schemaitem"], "data-bs-toggle" : "tooltip", title : tooltip, class: "theme-panelLabel"}).text(label+":"));
            $row.append($cell);

            // output
            // <textarea class="inputFullWidth theme-panelTextArea" type="text" id="properties_itemsdelay" current="0" key="delay" tag="formItem"></textarea>
            var $cell = $('<td>');
            $cell.append($('<textarea class="form-control form-control-sm full-width textbox">').attr({type: 'text', required: required, id: "properties_items"+fromData[objectItem]["schemaitem"], current: JSON.stringify(fromData[objectItem]["textbox"]), key: fromData[objectItem]["schemaitem"], tag: "formItem"}));
            $cell.find('#properties_items'+fromData[objectItem]["schemaitem"]).val(JSON.stringify(fromData[objectItem]["textbox"]));
            $row.append($cell);
        }
        if (fromData[objectItem]["type"] == "dropdown") {
  
            var $cell = $('<td width="100px">');
            $cell.append($('<label>').attr({for: fromData[objectItem]["schemaitem"], class: "theme-panelLabel"}).text(label+":"));
            $row.append($cell);

            var $cell = $('<td>');
            var $select =$('<select class="inputFullWidth theme-panelTextArea">').attr({type: 'dropdown', required: required, id: "properties_items"+fromData[objectItem]["schemaitem"], current: JSON.stringify(fromData[objectItem]["dropdown"]), key: fromData[objectItem]["schemaitem"], tag: "formItem"});
            
              for (var i=0; i< fromData[objectItem]["dropdown"].length;i++){
                $select.append($('<option>').attr({value: fromData[objectItem]["dropdown"][i]}).text(fromData[objectItem]["dropdown"][i]));
            }
            // Fixes legacy issues for dropdowns
            if (fromData[objectItem]["value"] == null)
            {
                $select.val(fromData[objectItem]["current"])
            }
            else 
            {
                $select.val(fromData[objectItem]["value"])
            }
            $cell.append($select);
            $row.append($cell);
            
        }
        if (fromData[objectItem]["type"] == "dynamic-dropdown") {
  
            var $cell = $('<td width="100px">');
            $cell.append($('<label>').attr({for: fromData[objectItem]["schemaitem"], class: "theme-panelLabel"}).text(label+":"));
            $row.append($cell);

            var $cell = $('<td>');
            var $select =$('<select class="inputFullWidth theme-panelText searchSelect">').attr({type: 'dropdown', required: required, id: "properties_items"+fromData[objectItem]["schemaitem"], current: JSON.stringify(fromData[objectItem]["dropdown"]), key: fromData[objectItem]["schemaitem"], tag: "formItem"});
            
            var dropdownData = [];
            var matches = false;

            $.ajax({url:fromData[objectItem]["source"]+"/", type:"GET", async: false, success: function ( result ) {
                dropdownData = result["data"];
            }});

            // Add blank option
            $select.append($('<option>').attr({value: ""}).text("---"));

            for (var i=0; i< dropdownData.length;i++){
                $select.append($('<option>').attr({value: dropdownData[i]["id"]}).text(dropdownData[i]["name"]));
                if (dropdownData[i]["id"] == fromData[objectItem]["value"]) { matches = true; }
            }

            // Allows for custom options to be visible, not the nicest...
            if (matches == false && fromData[objectItem]["value"] != "None"){
                $select.append($('<option>').attr({value: fromData[objectItem]["value"]}).text(fromData[objectItem]["value"]));
            }


            // Fixes legacy issues for dropdowns
            if (fromData[objectItem]["value"] == null)
            {
                $select.val(fromData[objectItem]["current"])
            }
            else 
            {
                $select.val(fromData[objectItem]["value"])
            }
            $cell.append($select);
            $row.append($cell);
            
        }
        if (fromData[objectItem]["type"] == "unit-input") {
  
            var $cell = $('<td width="100px">');
            $cell.append($('<label>').attr({for: fromData[objectItem]["schemaitem"], class: "theme-panelLabel"}).text(label+":"));
            $row.append($cell);

            var $cell = $('<td>');
            $cell.append($('<input class="inputFullWidth theme-panelTextbox-34">').attr({type: 'text', value: fromData[objectItem]["textbox"], current: fromData[objectItem]["textbox"], required: required, id: "properties_items"+fromData[objectItem]["schemaitem"], key: fromData[objectItem]["schemaitem"], tag: "formItem"}));
            var $select =$('<select class="inputFullWidth theme-panelTextArea-14">').attr({type: 'dropdown', required: required, id: "properties_items"+fromData[objectItem]["unitschema"], key: fromData[objectItem]["unitschema"], tag: "formItem"});
            for (var i=0; i< fromData[objectItem]["units"].length;i++){
                $select.append($('<option>').attr({value: fromData[objectItem]["units"][i]}).text(fromData[objectItem]["units"][i]));
            }
            $select.val(fromData[objectItem]["currentunit"])
            $cell.append($select);
            $row.append($cell);
            
        }		
        if (fromData[objectItem]["type"] == "break") {
            if (fromData[objectItem]["start"] == true){
                var $cell = $('<td colspan="2" width="100%">');
                $cell.append($('<label>').attr({for: fromData[objectItem]["schemaitem"], class: "theme-panelBreakTitle"}).text(label));
                $row.append($cell);
            }
            else 
            {
                var $cell = $('<td colspan="2" width="100%">');
                $cell.append($('<label>').attr({class: "theme-panelBreakLine"}));
                $row.append($cell);
            }
        }
        if (fromData[objectItem]["type"] == "multiline") {
            var $cell = $('<td width="100px">');
            $cell.append($('<label>').attr({for: fromData[objectItem]["schemaitem"], "data-bs-toggle" : "tooltip", title : tooltip, class: "theme-panelBreak"}).text(label+":"));
            $row.append($cell);
            var $cell = $('<td>');
            var $multilineTextArea = $('<textarea class="inputFullWidth theme-panelTextArea">').attr({type: 'text', required: required, id: "properties_items"+fromData[objectItem]["schemaitem"], current: fromData[objectItem]["textbox"], key: fromData[objectItem]["schemaitem"], tag: "formItem"});
            $multilineTextArea.keydown(function(e) {
                if(e.keyCode === 9) { // tab was pressed
                    // get caret position/selection
                    var start = this.selectionStart;
                        end = this.selectionEnd;
                    var $this = $(this);
                    // set textarea value to: text before caret + tab + text after caret
                    $this.val($this.val().substring(0, start)
                                + "\t"
                                + $this.val().substring(end));
                    // put caret at right position again
                    this.selectionStart = this.selectionEnd = start + 1;
                    // prevent the focus lose
                    return false;
                }
            });
            $cell.append($multilineTextArea);
            $cell.find('#properties_items'+fromData[objectItem]["schemaitem"]).val(fromData[objectItem]["textbox"]);
            $row.append($cell);
        }
        if (fromData[objectItem]["type"] == "script") {
            var $cell = $('<td width="100px">');
            $table.addClass("objectPropertiesTableGrow")
            $cell.append($('<label>').attr({for: fromData[objectItem]["schemaitem"], "data-bs-toggle" : "tooltip", title : tooltip, class: "theme-panelBreak"}).text(label+":"));
            $row.append($cell);
            var $cell = $('<td height="100%">');
            var $scriptTextArea = $('<div style="min-height: 250px; height: 100%">').attr({ type: "script", id: "properties_items"+fromData[objectItem]["schemaitem"], current: fromData[objectItem]["textbox"], key: fromData[objectItem]["schemaitem"], tag: "formItem" })
            require(['vs/editor/editor.main'], function() {
                var editor = monaco.editor.create($scriptTextArea.get(0), {
                    theme: 'vs-dark',
                    wordWrap: 'on',
                    automaticLayout: true,
                    minimap: {
                        enabled: true
                    },
                    scrollbar: {
                        vertical: 'auto'
                    },
                    readOnly: false,
                    model: monaco.editor.createModel(fromData[objectItem]["textbox"],"python")
                });
                $scriptTextArea.data({editor : editor })
            })
            $scriptTextArea.resizable();
            $cell.append($scriptTextArea);
            $row.append($cell);
        }
        if (group > 0 && fromData[objectItem]["type"] != "group-checkbox") {
            $row.addClass("group_"+group.toString())
            if (!groups[group.toString()]) {
                $row.addClass("hide");
            }
        }
        $table.append($row);
    }
    return $table
}

function getForm(container) {
    var jsonData = {};
	var requiredMet = true;
	container.find("[tag=formItem]").each(function() {
		formItem = $(this)
		resultItem = $(this).attr("key")
		if (formItem.attr("type") == "text")
		{
			if (formItem.attr("required") && formItem.val() == "") {
				dropdownAlert(container,"warning","Don't forget the required fields!",1000);
				requiredMet = false;
			}
			if (formItem.attr("current") != formItem.val()) {
				jsonData[resultItem] = formItem.val();
			}
		}
		if (formItem.attr("type") == "checkbox")
		{
			if (String(formItem.attr("current")) != String(formItem.is(":checked"))) {
				jsonData[resultItem] = formItem.is(":checked");
			}
		}
		if (formItem.attr("type") == "dropdown")
		{
            console.log(formItem.val());
			jsonData[resultItem] = formItem.val();
		}
		if (formItem.attr("type") == "script")
		{
			jsonData[resultItem] = formItem.data("editor").getValue();
		}
	})
	if (!requiredMet) {
		return;
	}
    return jsonData;
}