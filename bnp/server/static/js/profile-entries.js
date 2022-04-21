function showError(message) {
    $('#messages').html(message);
}

function getProfileID() {
    return parseInt($('#profile-id').html());
}

function getLoginProfileID() {
    return parseInt($('#login-profile-id').html());
}

function getPosts() {
    // Get private posts
    var profid = getProfileID();
    var login_id = getLoginProfileID();
    if (profid == login_id) {
        $.ajax({
            type: 'GET',
            url: '/api/get_private_diaries/',
            data: { 'profile_id' : getProfileID() },
            dataType: 'json',
            success: function(entries) {
                entries.forEach(function(entry) {
                    insertPrivateDiary(entry);
                }); 
            },
            error: function() {
                showError('Cannot post private diaries. Try again later.');
            }        
        });
    }
    else {
        var msghtml = $('<h3 class="warning text-center">You do not have permission to see this content</div>')
        $('#private-entries').append(msghtml);
    }
    // Get public posts
    $.ajax({
        type: 'GET',
        url: '/api/get_public_profile_diaries/',
        data: { 'profile_id' : getProfileID() },
        dataType: 'json',
        success: function(entries) {
            entries.forEach(function(entry) {
                insertPublicDiary(entry);
            });
        },
        error: function() {
            showError('Cannot post public diaries. Try again later.');
        }        
    });
}

function insertPrivateDiary(entry) {
    var entryhtml = $('<div class="entry p-2 rounded" entryid="' + entry.id + '"></div>');
    entryhtml.append('<div class="entry-head">From diary ' + entry.name + '</div>');
    entryhtml.append('<div class="entry-author">Submitted by <a href="#">' + entry.profile.username + '</a> @ ' + entry.date + ' (#' + entry.id + ')</div>');

    entryhtml.append('<hr class="line" size="8" width="100%" color="dark">');
    entryhtml.append('<div class="entry-body">' + entry.content + '</div>');
    $('#private-entries').append(entryhtml);
}

function insertPublicDiary(entry) {
    var entryhtml = $('<div class="entry p-2 rounded" entryid="' + entry.id + '"></div>');
    entryhtml.append('<div class="entry-head">From diary ' + entry.diaryname + '</div>');
    entryhtml.append('<div class="entry-author">Submitted by <a href="#">' 
        + entry.username + '</a> @ ' + entry.date + ' (#' + entry.id + ')</div>');

    entryhtml.append('<hr class="line" size="8" width="100%" color="dark">');
    entryhtml.append('<div class="entry-body">' + entry.text + '</div>');
    $('#public-entries').append(entryhtml);
}

$(function() {
    getPosts();

});

