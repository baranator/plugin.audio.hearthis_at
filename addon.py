# -*- coding: utf-8 -*-
from kodiswift import Plugin
from kodiswift import actions
import xbmcgui
import xbmcaddon
import requests
import copy


plugin = Plugin()

USER_AGENT = 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-GB; rv:1.9.0.3) Gecko/2008092417 Firefox/3.0.3'
PER_PAGE = 15
HEARTHIS = 'hearthis.at'
API_BASE_URL="https://api-v2.hearthis.at/"
COOKIES = requests.cookies.RequestsCookieJar()
USER = plugin.get_storage('user_data')

strings = {
        'genres'        : 30000,
        'playlists'     : 30001,
        'show_artist'   : 30002,
        'recently_added': 30003,
        'search'        : 30004,
        'search_artist' : 30005,
        'next'          : 30006,
        'likes'         : 30007,
        'popular'       : 30008,
        'search_track'  : 30009,
        'previous'      : 30010,
        'no_elements'   : 30011,
        'add_like'      : 30012,
        'rm_like'       : 30013,
        'my_likes'      : 30014,
        'following'     : 30015,
        'add_follow'    : 30016,
        'rm_follow'     : 30017,
        'login_failed'  : 30055
}

def _(string):
    tstring = strings.get(string)
    if tstring == None:
        return None
    else:
        return xbmcaddon.Addon().getLocalizedString(strings[string])

def api_call(path, params=None, rtype='GET', data=None, json=True):
    if logged_in():
        if params == None:
            params = {}
        params['key'] = USER['data']['key']
        params['secret'] = USER['data']['secret']
    url = API_BASE_URL+path
    headers = {'user-agent': USER_AGENT}
    
    plugin.log.info('api-call: %s with data %s' % (url,str(data)))
     
    if rtype == 'GET':
        r = requests.get(url, params=params, headers=headers, cookies=COOKIES)
    else:
        plugin.log.info("doing post")
        r = requests.post(url, params=params, data=data, headers=headers, cookies=COOKIES)
    if json:
        return r.json()
    else:
        return r.text
    



@plugin.route('/')
def main_menu():
    login()
    items1 = [
                {'label': _('recently_added'), 'path': plugin.url_for('show_feed_first', ftype='new')},
                {'label': _('popular'), 'path': plugin.url_for('show_feed_first', ftype='popular')},
                {'label': _('genres'), 'path': plugin.url_for('show_genres')},
            ]
    items_private = [   
                {'label': _('my_likes'), 'path': plugin.url_for('show_users_likes_first', user=USER['data']['permalink'])},
                {'label': _('following'), 'path': plugin.url_for('show_following_first', user=USER['data']['permalink'])},
            ]
    items2 = [
                {'label': _('search'), 'path': plugin.url_for('search')}
            ]
    
    
    
    return plugin.finish(items1 + items_private + items2)


@plugin.route('/playlist/<plink>')
def show_playlist(plink):
    plist = api_call('set/'+plink)
    return list_tracks(plist)


@plugin.route('/user/<user>/playlists', name='show_users_playlists_first', options={'page': '1', 'first': 'True'})
@plugin.route('/user/<user>/playlists/<page>')
def show_users_playlists(user, page, first=False):
    results = api_call(user, add_pp({'type': 'playlists'}, page))  
    items = []
    for l in results:
        items.append({'label': l['title'], 'path': plugin.url_for('show_playlist', plink=l['permalink'])})#,'is_playable': True})

    pagination={'call': 'show_users_playlists', 'args':{'user': user, 'page': int(page)}}
    return list_tracks(results, pagination, first)


@plugin.route('/user/<user>/likes', name='show_users_likes_first', options={'page': '1', 'first': 'True'})
@plugin.route('/user/<user>/likes/<page>')
def show_users_likes(user, page, first=False):
    results = api_call(user, add_pp({'type': 'likes'}, page))    
    pagination={'call': 'show_users_likes', 'args':{'user': user, 'page': int(page)}}
    return list_tracks(results, pagination, first)

def list_users(userlist, pagination = None, first=False, pre=[], post=[]):
    if isinstance(userlist, dict):
        dialogbox(_('no_elements'))
        return None
    items = pre
    items.append(pn_button(pagination, -1, len(userlist)))
    for u in userlist:
        plugin.log.info(str(u))
        show_user_url = plugin.url_for('show_user_first', user=u['permalink'], page=1, first='True')
        # Show like-button in context-menu, but only if logged in
        if logged_in():
            if u['following']:
                lbl = 'rm_following'
                add = 'False'
            else:
                lbl = 'add_following'
                add = 'True'
            ar_follow = ( _(lbl), actions.update_view(plugin.url_for('toggle_follow', user=u['permalink'], add=add)))
        else:
            ar_follow = None
            
        items.append({'label': '%s (%s tracks)' % (u['username'], str(u['track_count'])), 
                      'icon': u['avatar_url'], 
                      'context_menu':   [
                                            ar_follow
                                        ],
                      'path': plugin.url_for('show_user_first', user=u['permalink'], page=1, first=True)})
            
    items = items + post
    items.append(pn_button(pagination, 1, len(userlist)))
    
    #only skip history if turning pages, not if opening first page initially
    if pagination != None and first != 'True':
        ul=True
    else:
        ul=False
    return plugin.finish(items, update_listing=ul)



@plugin.route('/user/<user>/following', name='show_following_first', options={'page': '1', 'first': 'True'})
@plugin.route('/user/<user>/following/<page>')
def show_following(user, page, first=False):
    results = api_call(user+'/following', add_pp({}, page))    
    pagination={'call': 'show_following', 'args':{'user': user, 'page': int(page)}}
    return list_users(results, pagination, first)


@plugin.route('/user/<user>/<page>/<first>', name='show_user_first', options={'page': '1', 'first': 'True'})
@plugin.route('/user/<user>/<page>')
def show_user(user, page, first=False):
    u = api_call(user)
    results = api_call(user, add_pp({'type': 'tracks'}, page))  
    pagination={'call': 'show_user', 'args':{'user': user, 'page': int(page)}}
    selectors = [
                    {'label': '%s (%s)' % (_('playlists'),str(u['playlist_count'])), 'path': plugin.url_for('show_users_playlists_first', user=user)},
                    {'label': '%s (%s)' % (_('likes'), str(u['likes_count'])), 'path': plugin.url_for('show_users_likes_first', user=user)}
                ]
    return list_tracks(results, pagination, first, pre=selectors)

    
@plugin.route('/genres')
def show_genres():
    results = api_call('categories')
    items = []
    for g in results:
        items.append({
            'label': g['name'],
            'path': plugin.url_for('show_genre_first', genre=g['id'])
        })
    
    return plugin.finish(items)


@plugin.route('/feeds/<ftype>/<page>/<first>', name='show_feed_first', options={'page': '1', 'first': 'True'})
@plugin.route('/feeds/<ftype>/<page>')
def show_feed(ftype, page, first=False):
    results = api_call('feed', add_pp({'type': ftype}, page))  
    pagination={'call': 'show_feed', 'args':{'ftype': ftype, 'page': int(page)}}
    return list_tracks(results, pagination, first)


@plugin.route('/genre/<genre>/<page>/<first>', name='show_genre_first', options={'page': '1', 'first': 'True'})
@plugin.route('/genre/<genre>/<page>')
def show_genre(genre, page, first=False):
    results = api_call('categories/'+genre, add_pp({}, page))  
    pagination={'call': 'show_genre', 'args':{'genre': genre, 'page': int(page)}}
    return list_tracks(results, pagination, first)


@plugin.route('/search_for/<stype>/<skey>/<page>/<first>', name='search_for_first')
@plugin.route('/search_for/<stype>/<skey>/<page>')
def search_for(stype, skey, page, first=False):
    results = api_call('search', add_pp({'type': stype, 't': skey}, page))  
    pagination={'call': 'search_for', 'args':{'stype': stype, 'skey': skey, 'page': int(page)}}
    if stype == 'tracks':
        return list_tracks(results, pagination, first)
    elif stype == 'user':
        return list_users(results, pagination, first)


#TODO: sometimes jumps out of plugin while browsing search results
@plugin.route('/search')
def search():
    kb = xbmc.Keyboard ('', _('Search'), False)
    kb.doModal()
    if kb.isConfirmed():
        skey = kb.getText()
    else:
        return None
    selectors = [
                        {'label': _('search_artist'), 'path': plugin.url_for('search_for_first', stype='user', skey=skey, page=1, first='True')},
                        {'label': _('search_track'), 'path': plugin.url_for('search_for_first', stype='tracks', skey=skey, page=1, first='True')}
                ]
    return plugin.finish(selectors)
    
   
@plugin.route('/play/<user>/<trackid>')
def play_track(user, trackid):
    playurl='https://hearthis.at/'+user+'/'+trackid+'/listen'
    plugin.log.info('Playing: %s'%playurl)
    return plugin.set_resolved_url(playurl)   

@plugin.route('/logged_in/like/<user>/<trackid>/<add>')
def toggle_like(user, trackid, add):
    if add == 'True':
        a = 'like'
    else:
        a = 'dislike'
    results = api_call(user+'/'+trackid+'/'+a)
    plugin.log.info("Like: "+str(results))
    dialogbox(results)
    return None


@plugin.route('/logged_in/follow/<user>/<add>')
def toggle_follow(user, add):
    if add == 'True':
        a = 'follow'
    else:
        a = 'follow'
    results = api_call(user+'/'+a)
    dialogbox(results)
    return None

def dialogbox(msg):
    xbmc.executebuiltin('Notification(%s, %s)'%(HEARTHIS, msg))


def list_tracks(tracklist, pagination = None, first=False, pre=[], post=[]):
    if isinstance(tracklist, dict):
        dialogbox(_('no_elements'))
        return None
    items = pre
    items.append(pn_button(pagination, -1, len(tracklist)))
    for t in tracklist:
        #plugin.log.info(str(t))
        show_user_url = plugin.url_for('show_user_first', user=t['user']['permalink'], page=1, first='True')
        # Show like-button in context-menu, but only if logged in
        if logged_in():
            if t['favorited']:
                lbl = 'rm_like'
                add = 'False'
            else:
                lbl = 'add_like'
                add = 'True'
            ar_like = ( _(lbl), actions.update_view(plugin.url_for('toggle_like', trackid=t['permalink'], user=t['user']['permalink'], add=add)))
        else:
            ar_like = None
        items.append({
                'label': u'%s%s - %s' % ((u'[\u2665] ' if t['favorited']  else u''), t['user']['username'], t['title']),
                'icon': t['artwork_url'],
                'thumbnail': t['artwork_url'],
                'info': {
                            'duration': t.get('duration', None),
                            'artist': t['user']['username'],
                            'title': t['title'],
                            'genre': t.get('genre', None),
                            'playcount': t.get('playback_count', None)
                         },
                'context_menu': [( _('show_artist'), actions.update_view(show_user_url)),
                                 ar_like
                                ],
                'path': plugin.url_for('play_track', trackid=t['permalink'], user=t['user']['permalink']),
                'is_playable': True
        })
    items = items + post
    items.append(pn_button(pagination, 1, len(tracklist)))
    
    #only skip history if turning pages, not if opening first page initially
    if pagination != None and first != 'True':
        ul=True
    else:
        ul=False
    return plugin.finish(items, update_listing=ul)


def pn_button(pagination, direction, length=PER_PAGE):
    page = pagination['args']['page']
    if pagination != None :
        args = copy.deepcopy(pagination['args'])
        args['page'] += direction
        if direction == -1:
            if page <= 1:
                return None
            lbl=_("previous")
        else:
            if length < PER_PAGE:
                return None
            lbl=_("next")
        return {'label': '[%s ...]' % (lbl), 'path': plugin.url_for(pagination['call'], **args)}
    else:
        return None


def add_pp(obj, page):
    obj['page'] = int(page)
    obj['count'] = PER_PAGE
    return obj

def login():
    if xbmcaddon.Addon().getSetting('login_enabled') == 'false':
        return
    password = xbmcaddon.Addon().getSetting('password')
    email = xbmcaddon.Addon().getSetting('email')
    if logged_in():
        return
    result = api_call('login/', rtype='POST', data={'email': email, 'password': password})
    plugin.log.info("res: "+str(result))
    if result.get('success', True):
        plugin.log.info("login successful")
        USER['data'] = result
    else:
        dialogbox(_('login_failed'))

def logged_in():
    return USER['data'] != None

if __name__ == '__main__':
    plugin.run()
