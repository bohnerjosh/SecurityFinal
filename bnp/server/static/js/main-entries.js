function showError(message) {
    $('#messages').html(message);
}

function getDiaries() {
    $.ajax({
        type: 'GET',
        url: '/api/get_main_diary_entries/',
        dataType: 'json',
        success: function(entries) {
            if (entries.length < 5) {
                $('#append-diary').attr("hidden", true);
            }
            entries.forEach(function(entry) {
                insertEntry(entry);
            });
        },
        error: function() {
            showError('Cannot post public diaries. Try again later.');
        }        
    });
}

function insertEntry(entry) {
    var entryhtml = $('<div class="entry p-2 rounded" entryid="' + entry.id + '"></div>');
    entryhtml.append('<div class="entry-head">From diary ' + entry.diaryname + '</div>');
    entryhtml.append('<div class="entry-author">Submitted by <a href="/profile/' + entry.u_id + '">' 
        + entry.username + '</a> @ ' + entry.date + ' (#' + entry.id + ')</div>');

    entryhtml.append('<hr class="line" size="8" width="100%" color="dark">');
    entryhtml.append('<div class="entry-body">' + entry.text + '</div>');
    $('#entries').append(entryhtml);
}

$(function() {
    getDiaries();
});
