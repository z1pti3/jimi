
$(document).ready(function () {
    $(window).bind("keydown", function (event) { 
        if (event.ctrlKey || event.metaKey) {
            if (event.keyCode == 223) {
                window.top.swtichTab();
            }
        }
    })
});