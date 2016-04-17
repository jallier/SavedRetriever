var bar = "";
var id = "";
$(document).ready(function() {
    bar = $.snackbar({content:"", timeout:0});
    id = $(bar).attr('id');
    $("#"+id).snackbar("hide");
});

function getStatus(){
    $.getJSON('/status', function(data){
        if(data.status == 'running'){
            $(bar).attr('data-content', data.count + " posts downloaded");
            $("#"+id).snackbar("show");
            setTimeout(getStatus, 2000);
        } else if(data.status == 'finished'){
            $(bar).attr('data-content', "Downloads finished. Downloaded " + data.count + " posts");
            setTimeout(function(){
                location.reload();
            }, 2000);
        } else {
            setTimeout(getStatus, 2000);
        }
    });
}
$(document).ready(function() {
    $("#run_downloader").click(function(){
        $.post('/run').done()
        $.snackbar({content: "Beginning download"});
        getStatus();
    });
});
$(document).ready(function() {
    $("#delete_all_posts").click(function(){
        if (confirm("Are you sure you want to delete all posts from the database? If you have unsaved them on reddit, you will be unable to redownload")){
            $.getJSON('/delete_all_posts', function(data){
                if(data.status == 'success'){
                    $.snackbar({content: "All posts deleted"});
                } else {
                    $.snackbar({content: "Error deleting posts"});
                }
            });
            setTimeout(function(){
                location.reload();
            }, 2000);
        }
    });
});
$(document).ready(function() {
    $("#cancel").click(function(){
        $.post('/cancel').done();
        $.snackbar({content:"Cancelling download..."});
    });
});
$(document).ready(function() {
    $("#test").click(function(){
        $(bar).attr('data-content', 'working?');
        $("#"+id).snackbar("show");
    });
});