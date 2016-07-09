var bar = "";
var id = "";

/** Cancels download and displays snackbar */
function cancelDownload(){
    $.post('/cancel', function(){
        // run on success
        $.snackbar({content: "Download cancelled"})
    });
    $.snackbar({content: "Cancelling..."})
}

/** Gets JSON data from server of status of download thread. */
function getStatus() {
    $.getJSON('/status', function(data) {
        if (data.status == 'running') {
            $(bar).attr('data-content', data.count + " posts downloaded");
            $("#" + id).snackbar("show");
            setTimeout(getStatus, 2000);
        } else if (data.status == 'finished') {
            $(bar).attr('data-content', "Downloads finished. Downloaded " + data.count + " posts");
            setTimeout(function() {
                location.reload();
            }, 2000);
        } else {
            setTimeout(getStatus, 2000);
        }
    });
}

/** Requests server to delete specific post, then removes the html from the DOM */
function deletePost(post) {
    var data = {
        "post": post
    }
    $.getJSON('/delete_post', data, function(data) {
        if (data.success == true) {
            $.snackbar({
                "content": "Post deleted"
            });
            $("#" + post).remove();
        } else {
            $.snackbar({
                "content": "Error deleting post"
            });
        }
    });
}

$(document).ready(function() {
    // Create the ongoing snackbar, and hide it
    bar = $.snackbar({
        content: "",
        action_message: "Cancel",
        action_function: cancelDownload,
        timeout: 0
    });
    id = $(bar).attr('id');
    $("#" + id).snackbar("hide");

    // Click on start download button
    $("#run_downloader").click(function() {
        $.post('/run').done()
        $.snackbar({
            content: "Beginning download"
        });
        getStatus();
    });

    //Click on delete all
    $("#delete_all_posts").click(function() {
        if (confirm("Are you sure you want to delete all posts from the database? If you have unsaved them on reddit, you will be unable to redownload")) {
            $.getJSON('/delete_all_posts', function(data) {
                if (data.status == 'success') {
                    $.snackbar({
                        content: "All posts deleted"
                    });
                } else {
                    $.snackbar({
                        content: "Error deleting posts"
                    });
                }
            });
            setTimeout(function() {
                location.reload();
            }, 2000);
        }
    });

    //Click on cancel downloads
    $("#cancel").click(function() {
        $.post('/cancel').done();
        $.snackbar({
            content: "Cancelling download..."
        });
    });

    //Click on test text
    $("#test").click(function() {
        $("#delete_post").modal("show");
    });

    //Click on delete post icon.
    $(".a-icon").click(function() {
        var post_code = $(this).data("post");
        $("#delete_post").modal("show");
        $("#delete_post_confirm").click(function() {
            deletePost(post_code);
        });
    });
});
