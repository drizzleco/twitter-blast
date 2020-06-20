function toggle_ranking(val) {
    window.history.replaceState(null, null, window.location.pathname);
    var url = new URL(window.location.href);
    // If your expected result is "http://foo.bar/?x=42&y=2"
    url.searchParams.set('rank_by', val);
    window.location = url;

}

function filter() {
    let searchParams = new URLSearchParams(window.location.search);
    searchParams.set('value', $('#search-box input').val());
    window.location = window.location.pathname + '?' + searchParams.toString();

    //Add a second foo parameter.
    // params.append('value', $('#search-box input').val());
    // //Query string is now: 'foo=1&bar=2&foo=4'
}
