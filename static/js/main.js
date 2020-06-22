function toggle_ranking(val) {
    window.history.replaceState(null, null, window.location.pathname);
    var url = new URL(window.location.href);
    url.searchParams.set('rank_by', val);
    window.location = url;

}

function filter() {
    let searchParams = new URLSearchParams(window.location.search);
    searchParams.set('value', $('#search-box input').val());
    window.location = window.location.pathname + '?' + searchParams.toString();
}

function showLoading(el) {
    $(el).siblings('.loading').attr('style', 'display: flex !important')
}
