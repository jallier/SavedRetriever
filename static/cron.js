//Regex to capture *, digits and spaces
re = /[\d\*]+/;
valid = true;

/** Checks if current input is valid. Used for when save button on settings page is clicked */
function isValid() {
    if (!valid) {
        $.snackbar({
            content: "Invalid cron string; please enter correct string"
        });
        return false;
    }
    return true;
}

/** Validate manually typed cron values
 * @param {string} cronValue - Cron string to evaluate.
 */
function validCronString(cronValue) {
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
    var count = 0;

    //Snackbar validation notification
    $("#cronValidate").click(function() {
        if (validCronString(input.val())) {
            $.snackbar({
                content: "Cron string valid"
            });
        } else {
            $.snackbar({
                content: "Cron string invalid. Please check and try again"
            });
        }
    });

    // apply cron with default options
    cron.cron({
        initial: input.val(),
        onChange: function() {
            console.log(count);
            if (!input.is(":focus") && count != 0) {
                input.val(cron.cron("value"));
            }
            count = 1; // Page has rendered, value can now be updated.
        }
    });

    //Show input color as validation and change the cron selectors.
    input.keyup(function() {
        if (!validCronString(input.val())) {
            input.css("border-color", "red");
            valid = false;
        } else {
            input.css("border-color", "initial");
            cron.cron("value", input.val());
            valid = true;
        }
    });
});
