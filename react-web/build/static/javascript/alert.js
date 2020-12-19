var alertHTML = `
<div class="alert theme-popupContainer" id="alert-container" role="alert">
    <div class="alert theme-popup">
        <p class="alert-p" id="alert-message"></p>
    </div>
</div>
`

function dropdownAlert(parent,type,message,timeout) {
    var alert = $(alertHTML);
    if (type == "success") {
        alert.addClass("alert-success")
    }
    if (type == "error") {
        alert.addClass("alert-danger")
    }
    if (type == "warning") {
        alert.addClass("alert-warning")
    }
    if (type == "info") {
        alert.addClass("alert-info")
    }
    $.when(parent.append(alert)).then(function() {
        alert.find("#alert-message").text(message);
        alert.slideDown();
        window.setTimeout(function() {
            $.when(alert.slideUp()).then(function() {
                alert.remove(); 
            })
        }, timeout);
    })
}