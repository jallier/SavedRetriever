//Regex to capture *, digits and spaces
re = /[\d\*]+/;

function validCronString(cronValue) {
    /**
     * Validate manually typed cron values
     */
    var inp_arr = cronValue.trim().split(" ");

    if (inp_arr.length < 5) { //Too few chars in the input string
        return false;
    }
    if (inp_arr[0] >= 60) { //Minutes greater than 60
        return false;
    }
    if (inp_arr[1] >= 24) { //Hours greater than 24
        return false;
    }
    if (inp_arr[2] >= 32) { //Days of month greater than 31
        return false;
    }
    if (inp_arr[3] >= 13) { //Months of year greater than 12
        return false;
    }
    if (inp_arr[4] >= 7) { //Day of week greater than 7
        return false;
    }
    //Return false if any invalid chars in the string
    for (var i = 0; i < inp_arr.length; i++) {
        console.log(inp_arr[i]);
        if (!re.test(inp_arr[i])) {
            return false;
        }
        if (inp_arr[i].length > 2) {
            return false;
        }
    }
    // Cron is valid
    return true;
}

$(document).ready(function() {
    var input = $(".cronInput");
    var cron = $('#cronSelector');

    // apply cron with default options
    cron.cron({
        onChange: function() {
            if (!input.is(":focus")){
                input.val(cron.cron("value"));
            }
        }
    });

    input.keyup(function() {
        if (!validCronString(input.val())) {
            input.css("border-color", "red");
        } else {
            input.css("border-color", "initial");
            cron.cron("value", input.val());
        }
    });

    $("#cronValidate").click(function(){
        if(validCronString(input.val())){
            $.snackbar({
                content: "Cron string valid"
            });
        } else {
            $.snackbar({
                content: "Cron string invalid. Please check and try again"
            });
        }
    });
});
