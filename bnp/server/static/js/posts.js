function getPosts() {
    // Get public posts
    $.ajax({
        type: 'GET',
        url: '/api/get_public_profile_diaries/',
        data: { 'profile_id' : getProfileID() },
        dataType: 'json',
        success: function(posts) {
            posts.forEach(function(post) {
                insertPost(post);
            });
        },
        error: function() {
            showError('Cannot post. Try again later.');
        }        
    });
    // Get private posts
    $.ajax({
        type: 'GET',
        url: '/api/posts/',
        data: { 'profile_id' : getProfileID() },
        dataType: 'json',
        success: function(posts) {
            posts.forEach(function(post) {
                insertPost(post);
            });
        },
        error: function() {
            showError('Cannot post. Try again later.');
        }        
    });


}

$(function() {
    getPosts();

});

