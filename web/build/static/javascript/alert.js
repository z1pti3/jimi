function dropdownAlert(parent,type,message,timeout) {
    var alert = $("#mainAlert");
    alert.removeClass("mainAlert-warning")
    alert.removeClass("mainAlert-success")
    if (type.toLowerCase() == "success") {
        alert.addClass("mainAlert-success")
    }
    if (type.toLowerCase() == "error") {
        alert.addClass("mainAlert-warning")
    }
    if (type.toLowerCase() == "warning") {
        alert.addClass("mainAlert-warning")
    }
    if (type.toLowerCase() == "info") {
        alert.addClass("mainAlert-info")
    }
    alert.find("#alert-header").text(type);
    alert.find("#alert-message").text(message);
    alert.find("#alert-smallText").text(localTime(new Date().getTime()/1000));
    $('#alertContainer').css('z-index',100);
    setTimeout(function(){ $('#alertContainer').css('z-index',0); }, 5000);
    var toast = bootstrap.Toast.getInstance(document.getElementById('mainAlert'));
    if (toast === null) {
        toast = new bootstrap.Toast(document.getElementById('mainAlert'));
    }
    toast.show()
}