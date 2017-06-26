# -*- coding: utf-8 -*-
from kodiswift import Plugin
from kodiswift import actions
import xbmcgui
import cookielib, urllib2 
import simplejson as json
import copy
from language import get_string as _

plugin = Plugin()

USER_AGENT = 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-GB; rv:1.9.0.3) Gecko/2008092417 Firefox/3.0.3'
PER_PAGE = 15
HEARTHIS = 'hearthis.at'

def api_call(query):
    api_base_url="https://api-v2.hearthis.at/"
    cj = cookielib.CookieJar()
    opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
    url = api_base_url+query
    request = urllib2.Request(url)
    plugin.log.info('api-call: %s'%url)
    request.add_header('User-Agent', USER_AGENT)
    response = opener.open(request)
    jsono = response.read()
    response.close()
    return json.loads(jsono)


@plugin.route('/')
def main_menu():
    items = [
                {'label': _("Recently added"), 'path': plugin.url_for('show_feed_first', ftype='new')},
                {'label': _("Popular"), 'path': plugin.url_for('show_feed_first', ftype='popular')},
                {'label': _("Genres"), 'path': plugin.url_for('show_genres')},
                {'label': _("Search"), 'path': plugin.url_for('search')}
            ]

    return plugin.finish(items)


@plugin.route('/playlist/<plink>')
def show_playlist(plink):
    plist = api_call('set/'+plink)
    return list_tracks(plist)


@plugin.route('/user/<user>/playlists', name='show_users_playlists_first', options={'page': '1', 'first': 'True'})
@plugin.route('/user/<user>/playlists/<page>')
def show_users_playlists(user, page, first=False):
    results = api_call(add_pp('%s/?type=playlists' % (user), page))  
    items = []
    for l in results:
        items.append({'label': l['title'], 'path': plugin.url_for('show_playlist', plink=l['permalink'])})#,'is_playable': True})

    pagination={'call': 'show_users_playlists', 'args':{'user': user, 'page': int(page)}}
    return list_tracks(results, pagination, first)


@plugin.route('/user/<user>/likes', name='show_users_likes_first', options={'page': '1', 'first': 'True'})
@plugin.route('/user/<user>/likes/<page>')
def show_users_likes(user, page, first=False):
    results = api_call(add_pp('%s/?type=likes' % (user), page))    
    pagination={'call': 'show_users_likes', 'args':{'user': user, 'page': int(page)}}
    return list_tracks(results, pagination, first)


@plugin.route('/user/<user>/<page>/<first>', name='show_user_first', options={'page': '1', 'first': 'True'})
@plugin.route('/user/<user>/<page>')
def show_user(user, page, first=False):
    u = api_call(user)
    results = api_call(add_pp('%s/?type=tracks' % (user), page))
    pagination={'call': 'show_user', 'args':{'user': user, 'page': int(page)}}
    selectors = [
                    {'label': '%s (%s)' % (_("Playlists"),str(u['playlist_count'])), 'path': plugin.url_for('show_users_playlists_first', user=user)},
                    {'label': '%s (%s)' % (_("Likes"), str(u['likes_count'])), 'path': plugin.url_for('show_users_likes_first', user=user)}
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
    results = api_call(add_pp('feed/?type=%s' % (ftype), page))
    pagination={'call': 'show_feed', 'args':{'ftype': ftype, 'page': int(page)}}
    return list_tracks(results, pagination, first)


@plugin.route('/genre/<genre>/<page>/<first>', name='show_genre_first', options={'page': '1', 'first': 'True'})
@plugin.route('/genre/<genre>/<page>')
def show_genre(genre, page, first=False):
    results = api_call(add_pp('categories/%s/' % (genre), page, sep='?'))
    pagination={'call': 'show_genre', 'args':{'genre': genre, 'page': int(page)}}
    return list_tracks(results, pagination, first)


@plugin.route('/search_for/<stype>/<skey>/<page>/<first>', name='search_for_first')
@plugin.route('/search_for/<stype>/<skey>/<page>')
def search_for(stype, skey, page, first=False):
    results = api_call(add_pp('search?t=%s&type=%s' % (skey, stype), page))
    pagination={'call': 'search_for', 'args':{'stype': stype, 'skey': skey, 'page': int(page)}}
    if stype == 'tracks':
        return list_tracks(results, pagination, first)
    elif stype == 'user':
        items = [pn_button(pagination, -1, len(results))]
        for u in results:
            items.append({'label': '%s (%s tracks)' % (u['username'], str(u['track_count'])), 'icon': u['avatar_url'], 'path': plugin.url_for('show_user_first', user=u['permalink'], page=1, first=True)})
        items += [pn_button(pagination, 1, len(results))]
        return items


#TODO: sometimes jumps out of plugin while browsing search results
@plugin.route('/search')
def search():
    kb = xbmc.Keyboard ('', _("Search"), False)
    kb.doModal()
    if kb.isConfirmed():
        skey = kb.getText()
    else:
        return None
    selectors = [
                        {'label': _("Search for artist only"), 'path': plugin.url_for('search_for_first', stype='user', skey=skey, page=1, first='True')},
                        {'label': _("Search for tracks only"), 'path': plugin.url_for('search_for_first', stype='tracks', skey=skey, page=1, first='True')}
                ]
    return plugin.finish(selectors)
    
   
@plugin.route('/play/<user>/<trackid>')
def play_track(user,trackid):
    playurl='https://hearthis.at/'+user+'/'+trackid+'/listen'
    plugin.log.info('Playing: %s'%playurl)
    return plugin.set_resolved_url(playurl)   


def dialogbox(msg):
    xbmc.executebuiltin('Notification(%s, %s)'%(HEARTHIS, msg))


def list_tracks(tracklist, pagination = None, first=False, pre=[], post=[]):
    if isinstance(tracklist, dict):
        dialogbox(_('No further elements to show'))
        return None
    items = pre
    items.append(pn_button(pagination, -1, len(tracklist)))
    for t in tracklist:
        url = plugin.url_for('show_user_first', user=t['user']['permalink'], page=1, first=True)
        plugin.log.info(url)
        items.append({
                'label': '%s - %s' % (t['user']['username'], t['title']),
                'icon': t['artwork_url'],
                'thumbnail': t['artwork_url'],
                'info': {
                            'duration': t.get('duration', None),
                            'artist': t['user']['username'],
                            'title': t['title'],
                            'genre': t.get('genre', None),
                            'playcount': t.get('playback_count', None)
                         },
                'context_menu': [( _('Show artist'), actions.update_view(url))],
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


def add_pp(call, page, sep = '&'):
    return '%s%spage=%d&count=%d' % (call, sep, int(page), PER_PAGE)


if __name__ == '__main__':
    plugin.run()
