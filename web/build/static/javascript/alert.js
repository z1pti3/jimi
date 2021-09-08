function dropdownAlert(parent,type,message,timeout) {
    var alert = $("#mainAlert");
    alert.removeClass("mainAlert-warning")
    alert.removeClass("mainAlert-success")
    if (type == "success") {
        alert.addClass("mainAlert-success")
    }
    if (type == "error") {
        alert.addClass("mainAlert-warning")
    }
    if (type == "warning") {
        alert.addClass("mainAlert-warning")
    }
    if (type == "info") {
        alert.addClass("mainAlert-warning")
    }
    alert.find("#alert-header").text(type);
    alert.find("#alert-message").text(message);
    var toast = new bootstrap.Toast(document.getElementById('mainAlert'));
    toast.show()
}