from bottle import Bottle, run, static_file, request
import bottle_sqlite
from config.config import db_path, outdent_all_siblings_below, always_add_to_global_top
from utils.find import find_prev_visible_item, find_next_visible_item, find_subtree_bounds, find_sibling_index_above, \
    find_sibling_index_below, find_subtree_bounds_all_siblings_below
from utils.generate import generate_unplaced_new_item, generate_new_subitem
from utils.server import get_request_context, generic_response, noop_response, error_response
from utils.update_multiple_items import remove_item, insert_above_item, insert_below_item, recalculate_item_ranks, \
    initialize_cache
from utils.update_single_item import decorate_item, swap_subtrees

app = Bottle()
plugin = bottle_sqlite.Plugin(dbfile=db_path)
app.install(plugin)

cache = {}
diffs = []


# TODO handle cache control for static files
# https://stackoverflow.com/questions/24672996/python-bottle-and-cache-control

@app.route("/tests/<filepath:path>", method="GET")
def get_tests(filepath):
    return static_file(filepath, root='static/tests/')


@app.route("/js/<filepath:re:.*\.js>", method="GET")
def get_js(filepath):
    return static_file(filepath, root='static/js/')


@app.route("/components/<filepath:re:.*\.js>", method="GET")
def get_components(filepath):
    return static_file(filepath, root='static/components/')


@app.route("/css/<filepath:re:.*\.css>", method="GET")
def get_css(filepath):
    return static_file(filepath, root='static/css/')


@app.route("/<filepath:re:.*\.html>", method="GET")
def get_html(filepath):
    return static_file(filepath, root='static/html/')


@app.route('/', method="GET")
def index():
    return static_file('index.html', root='./static/html')


@app.route("/img/<filepath:path>", method="GET")
def get_img(filepath):
    response = static_file(filepath, root='static/img/')
    # Note: cache-control appears not to work for Chrome if in dev mode
    response.set_header("Cache-Control", "public, max-age=604800")
    return response


@app.route("/libs/<filepath:path>", method="GET")
def get_lib(filepath):
    return static_file(filepath, root='static/libs/')


@app.post('/toggle-todo')
def toggle_todo(db):
    global cache
    item_subitem_id, item_id, subitem_index, search_filter = get_request_context(request)
    item = cache['id_to_item'][item_id]
    if '@todo' in item['subitems'][subitem_index]['tags']:
        item['subitems'][subitem_index]['tags'] = item['subitems'][subitem_index]['tags'].replace('@todo', '@done')
    elif '@done' in item['subitems'][subitem_index]['tags']:
        item['subitems'][subitem_index]['tags'] = item['subitems'][subitem_index]['tags'].replace('@done', '@todo')
    decorate_item(item)  # TODO do we need this?
    # TODO: update db
    return generic_response(cache, search_filter)


@app.post('/toggle-outline')
def toggle_outline(db):
    global cache
    item_subitem_id, item_id, subitem_index, search_filter = get_request_context(request)
    item = cache['id_to_item'][item_id]
    if 'collapse' in item['subitems'][subitem_index]:
        del item['subitems'][subitem_index]['collapse']
    else:
        item['subitems'][subitem_index]['collapse'] = True
    decorate_item(item)  # TODO do we need this?
    # TODO: update db
    return generic_response(cache, search_filter)


@app.post('/delete-subitem')
def delete_subitem(db):
    global cache
    item_subitem_id, item_id, subitem_index, search_filter = get_request_context(request)
    item = cache['id_to_item'][item_id]
    if subitem_index == 0:
        remove_item(cache, item)
        # TODO: update db
        return generic_response(cache, search_filter)
    else:
        indent = item['subitems'][subitem_index]['indent']
        subitems_ = item['subitems'][:]
        del subitems_[subitem_index]
        while subitem_index < len(subitems_) and subitems_[subitem_index]['indent'] > indent:
            del subitems_[subitem_index]
        item['subitems'] = subitems_
        decorate_item(item)  # TODO do we need this?
        # TODO: update db
        return generic_response(cache, search_filter)


@app.post('/update-subitem-content')
def update_subitem_content(db):
    global cache
    item_subitem_id, item_id, subitem_index, search_filter = get_request_context(request)
    updated_content = request.json['updatedContent']
    item = cache['id_to_item'][item_id]
    item['subitems'][subitem_index]['data'] = updated_content
    decorate_item(item)  # TODO do we need this?
    return {}  # TODO


@app.post('/move-item-up')
def move_item_up(db):
    global cache
    item_subitem_id, item_id, subitem_index, search_filter = get_request_context(request)
    item = cache['id_to_item'][item_id]
    assert subitem_index == 0, 'subitem_index should be 0'
    above = find_prev_visible_item(cache, item, search_filter)
    if above is not None:
        remove_item(cache, item)
        insert_above_item(cache, item, above)
    # TODO update db
    return generic_response(cache, search_filter)


@app.post('/move-item-down')
def move_item_down(db):
    global cache
    item_subitem_id, item_id, subitem_index, search_filter = get_request_context(request)
    item = cache['id_to_item'][item_id]
    assert subitem_index == 0, 'subitem index should be zero'
    below = find_next_visible_item(cache, item, search_filter)
    if below is not None:
        remove_item(cache, item)
        insert_below_item(cache, item, below)
    # TODO update db
    return generic_response(cache, search_filter)


@app.post('/move-subitem-up')
def move_subitem_up(db):
    global cache
    item_subitem_id, item_id, subitem_index, search_filter = get_request_context(request)
    item = cache['id_to_item'][item_id]
    sibling_index_above = find_sibling_index_above(item, subitem_index)
    if sibling_index_above is None:
        return noop_response('cannot move subitem above a parent')
    upper_bound, lower_bound = find_subtree_bounds(item, subitem_index)
    upper_bound_above, lower_bound_above = find_subtree_bounds(item, sibling_index_above)
    shift_up = lower_bound_above - upper_bound_above + 1
    new_subitem_index = subitem_index - shift_up
    swap_subtrees(item, upper_bound_above, lower_bound_above, upper_bound, lower_bound)

    decorate_item(item)
    # TODO: update db

    extra_data = {
        'newSelectedItemSubitemId': f'{item_id}:{new_subitem_index}'
    }
    return generic_response(cache, search_filter, extra_data=extra_data)


@app.post('/move-subitem-down')
def move_subitem_down(db):
    global cache
    item_subitem_id, item_id, subitem_index, search_filter = get_request_context(request)
    item = cache['id_to_item'][item_id]
    sibling_index_below = find_sibling_index_below(item, subitem_index)
    if sibling_index_below is None:
        return noop_response('cannot move subitem directly below an elder')
    upper_bound, lower_bound = find_subtree_bounds(item, subitem_index)
    upper_bound_below, lower_bound_below = find_subtree_bounds(item, sibling_index_below)
    shift_down = lower_bound_below - upper_bound_below + 1
    new_subitem_index = subitem_index + shift_down
    swap_subtrees(item, upper_bound, lower_bound, upper_bound_below, lower_bound_below)

    decorate_item(item)
    # TODO: update db

    extra_data = {
        'newSelectedItemSubitemId': f'{item_id}:{new_subitem_index}'
    }
    return generic_response(cache, search_filter, extra_data=extra_data)


@app.post('/indent')
def indent(db):
    """
    case 1: cannot indent or outdent
    X
       O
          O
          O
       X

    case 2: cannot indent, can outdent
    X
       X
          O
             O
             O
          X  <---  what do we do with this?? a) x becomes child of O b) x gets outdented as well
       X
    Either:
    a) all siblings below become children, or
    b) all siblings below get outdented

    b) seems more destructive? Currently MetaList1.0 uses method B

    outdent is more complex than indent, there is an asymmetry about the decisions that have to be made
    therefore we might not be able to straightforwardly modify our indent code.

    example of asymmetry:
        if indent >= 2, you can always outdent
        you cannot always indent, it depends on existence of similar indent sibling above

    """
    global cache
    item_subitem_id, item_id, subitem_index, search_filter = get_request_context(request)
    item = cache['id_to_item'][item_id]

    assert subitem_index > 0, "cannot indent top level item"

    sibling_index_above = find_sibling_index_above(item, subitem_index)
    if sibling_index_above is None:
        return noop_response('no sibling above exists, therefore cannot indent')
    sibling_above = item['subitems'][sibling_index_above]

    # if the (previously) sibling above is collapsed, it should be auto expanded
    if 'collapse' in sibling_above:
        del sibling_above['collapse']

    # apply indents
    upper_bound, lower_bound = find_subtree_bounds(item, subitem_index)
    for i in range(upper_bound, lower_bound+1):
        item['subitems'][i]['indent'] += 1

    decorate_item(item)
    # TODO update db

    extra_data = {
        'newSelectedItemSubitemId': item_subitem_id  # did not change
    }
    return generic_response(cache, search_filter, extra_data=extra_data)


@app.post('/outdent')
def outdent(db):
    global cache
    item_subitem_id, item_id, subitem_index, search_filter = get_request_context(request)
    item = cache['id_to_item'][item_id]
    subitem = item['subitems'][subitem_index]
    indent = subitem['indent']

    if indent < 2:
        return noop_response('cannot outdent any further')

    # indent selected subitem
    if outdent_all_siblings_below:
        upper_bound, lower_bound = find_subtree_bounds_all_siblings_below(item, subitem_index)
    else:
        upper_bound, lower_bound = find_subtree_bounds(item, subitem_index)
    for i in range(upper_bound, lower_bound+1):
        item['subitems'][i]['indent'] -= 1

    # need to update our cache
    decorate_item(item)

    # prepare a response
    extra_data = {
        'newSelectedItemSubitemId': item_subitem_id  # did not change
    }
    return generic_response(cache, search_filter, extra_data=extra_data)


@app.post('/search')
def search(db):
    global cache
    search_filter = request.json['searchFilter']
    return generic_response(cache, search_filter)


@app.post('/add-item-sibling')
def add_item_sibling(db):
    global cache
    item_subitem_id, item_id, subitem_index, search_filter = get_request_context(request)
    assert subitem_index == 0, 'expected subitem_idex == 0'
    selected_item = cache['id_to_item'][item_id]
    new_item = generate_unplaced_new_item(cache, search_filter)
    insert_below_item(cache, new_item, selected_item)
    decorate_item(new_item)
    cache['id_to_item'][new_item['id']] = new_item
    # TODO update db

    extra_data = {
        'newSelectedItemSubitemId': f'{new_item["id"]}:0'
    }
    return generic_response(cache, search_filter, extra_data=extra_data)


@app.post('/add-subitem-sibling')
def add_subitem_sibling(db):
    global cache
    item_subitem_id, item_id, subitem_index, search_filter = get_request_context(request)
    item = cache['id_to_item'][item_id]
    indent = item['subitems'][subitem_index]['indent']

    # find location to insert
    if subitem_index == 0:
        # we are adding from the title row, so it always goes to a fixed indented position
        insert_at = 1
        new_indent = 1
    else:
        new_indent = indent
        insert_at = find_sibling_index_below(item, subitem_index)
        if insert_at is None:
            # no sibling below, therefore add to end of list
            insert_at = len(item['subitems'])

    # create blank subitem and insert
    new_subitem = generate_new_subitem(indent=new_indent, tags='')
    item['subitems'].insert(insert_at, new_subitem)
    decorate_item(item)

    extra_data = {
        'newSelectedItemSubitemId': f'{item_id}:{insert_at}'
    }
    return generic_response(cache, search_filter, extra_data=extra_data)


@app.post('/add-subitem-child')
def add_subitem_child(db):
    global cache
    item_subitem_id, item_id, subitem_index, search_filter = get_request_context(request)
    item = cache['id_to_item'][item_id]

    # find location to insert
    insert_at = subitem_index + 1
    indent = item['subitems'][subitem_index]['indent'] + 1

    # create blank subitem and insert
    new_subitem = generate_new_subitem(indent=indent, tags='')
    item['subitems'].insert(insert_at, new_subitem)

    # expand the parent subitem if necessary
    parent_subitem = item['subitems'][subitem_index]
    if 'collapse' in parent_subitem:
        del parent_subitem['collapse']

    decorate_item(item)

    extra_data = {
        'newSelectedItemSubitemId': f'{item_id}:{insert_at}'
    }
    return generic_response(cache, search_filter, extra_data=extra_data)


@app.post('/add-item-top')
def add_item_top(db):
    global cache
    search_filter = request.json['searchFilter']
    if len(search_filter['texts']) > 0 or search_filter['partial_text'] is not None:
        return error_response('Cannot add new items when using a text based search filter.')
    new_item = generate_unplaced_new_item(cache, search_filter)

    if always_add_to_global_top:
        if len(cache['items']) == 0:
            new_item['prev'] = None
            new_item['next'] = None
        else:
            head = None
            for item in cache['items']:
                if item['prev'] is None:
                    head = item
                    break
            assert head is not None
            new_item['prev'] = None
            new_item['next'] = head['id']
            head['prev'] = new_item['id']
    else:
        raise NotImplementedError

    decorate_item(new_item)
    cache['id_to_item'][new_item['id']] = new_item
    recalculate_item_ranks(cache)
    # TODO update db

    extra_data = {
        'newSelectedItemSubitemId': f'{new_item["id"]}:0'
    }
    return generic_response(cache, search_filter, extra_data=extra_data)


@app.post('/paste-sibling')
def paste_sibling(db):
    global cache
    item_subitem_id, item_id, subitem_index, search_filter = get_request_context(request)
    item = cache['id_to_item'][item_id]
    indent = item['subitems'][subitem_index]['indent']

    ###########################################################
    # grab clipboard info and normalize indents
    ###########################################################
    assert 'clipboard' in request.json, 'missing clipboard from request'
    clipboard = request.json['clipboard']
    clip_item = clipboard['item']
    decorate_item(clip_item)  # in case we want to inherit parent tags
    clip_subitem_index = int(clipboard['subitemIndex'])
    clip_indent = clip_item['subitems'][clip_subitem_index]['indent']
    # inherit parent tags, but only at top level
    clip_item['subitems'][clip_subitem_index]['tags'] = ' '.join(clip_item['subitems'][clip_subitem_index]['_tags'])
    # normalize indent
    clip_item['subitems'][clip_subitem_index]['indent'] = 0
    # always add root to list
    clip_subitems = [clip_item['subitems'][clip_subitem_index]]
    # add any children
    for i in range(clip_subitem_index+1, len(clip_item['subitems'])):
        next_subitem = clip_item['subitems'][i]
        if next_subitem['indent'] <= clip_indent:  # sibling or an eldar
            break
        next_subitem['indent'] -= clip_indent  # normalize indent
        # add to our clip subitems list
        clip_subitems.append(next_subitem)
    del clip_item, clip_subitem_index  # should not need anymore
    assert len(clip_subitems) > 0, 'no clip subitems'

    if subitem_index == 0:
        # need to create new item, and insert the clipboard stuff (actually, just substitute)
        # also need to include tags from search context
        new_item = generate_unplaced_new_item(cache, search_filter)
        insert_below_item(cache, new_item, item)
        decorate_item(new_item)
        # remember to include tags from search context!
        for tag in new_item['subitems'][0]['_tags']:
            if tag not in clip_subitems[0]['_tags']:
                clip_subitems[0]['tags'] += f' {tag}'
                clip_subitems[0]['_tags'].append(tag)
        # assign subitems directly
        new_item['subitems'] = clip_subitems
        # do not need to decorate
        # do not need to handle normalized indents
        cache['id_to_item'][new_item['id']] = new_item
        recalculate_item_ranks(cache)
        # TODO update db
        extra_data = {
            'newSelectedItemSubitemId': f'{new_item["id"]}:0'
        }
        return generic_response(cache, search_filter, extra_data=extra_data)
    else:
        # handle normalized indents
        for clip_subitem in clip_subitems:
            # going underneath as a sibling
            clip_subitem['indent'] += indent
        # find the proper insertion point (earliest is immediately after)
        insertion_point = subitem_index + 1
        for i in range(insertion_point, len(item['subitems'])):
            if item['subitems'][i]['indent'] <= indent:  # sibling or eldar
                break
            insertion_point += 1
        initial_insertion_point = insertion_point
        # insert subitems
        item['subitems'][insertion_point:insertion_point] = clip_subitems
        del clip_subitems
        # decorate
        decorate_item(item)
        # do not need to update cache or recalculate ranks
        # TODO update db
        extra_data = {
            'newSelectedItemSubitemId': f'{item_id}:{initial_insertion_point}'
        }
        return generic_response(cache, search_filter, extra_data=extra_data)


@app.post('/paste-child')
def paste_child(db):
    global cache
    item_subitem_id, item_id, subitem_index, search_filter = get_request_context(request)
    item = cache['id_to_item'][item_id]
    indent = item['subitems'][subitem_index]['indent']

    ###########################################################
    # grab clipboard info and normalize indents
    ###########################################################
    assert 'clipboard' in request.json, 'missing clipboard from request'
    clipboard = request.json['clipboard']
    clip_item = clipboard['item']
    decorate_item(clip_item)  # in case we want to inherit parent tags
    clip_subitem_index = int(clipboard['subitemIndex'])
    clip_indent = clip_item['subitems'][clip_subitem_index]['indent']
    # inherit parent tags, but only at top level
    clip_item['subitems'][clip_subitem_index]['tags'] = ' '.join(clip_item['subitems'][clip_subitem_index]['_tags'])
    # normalize indent
    clip_item['subitems'][clip_subitem_index]['indent'] = 0
    # always add root to list
    clip_subitems = [clip_item['subitems'][clip_subitem_index]]
    # add any children
    for i in range(clip_subitem_index + 1, len(clip_item['subitems'])):
        next_subitem = clip_item['subitems'][i]
        if next_subitem['indent'] <= clip_indent:  # sibling or an eldar
            break
        next_subitem['indent'] -= clip_indent  # normalize indent
        # add to our clip subitems list
        clip_subitems.append(next_subitem)
    del clip_item, clip_subitem_index  # should not need anymore
    assert len(clip_subitems) > 0, 'no clip subitems'

    # handle normalized indents
    for clip_subitem in clip_subitems:
        # going underneath as a child
        clip_subitem['indent'] += indent + 1  # +1 because it is a child

    insertion_point = subitem_index + 1
    # assumption: insertion point does NOT need to account for children of our target

    # insert subitems
    # TODO use slice notation
    item['subitems'][insertion_point:insertion_point] = clip_subitems
    del clip_subitems

    # make sure the target subitem is not collapsed
    if 'collapse' in item['subitems'][subitem_index]:
        del item['subitems'][subitem_index]['collapse']

    # decorate
    decorate_item(item)
    # do not need to update cache or recalculate ranks
    # TODO update db
    extra_data = {
        'newSelectedItemSubitemId': f'{item_id}:{insertion_point}'
    }
    return generic_response(cache, search_filter, extra_data=extra_data)


if __name__ == '__main__':
    initialize_cache(cache)
    run(app)
