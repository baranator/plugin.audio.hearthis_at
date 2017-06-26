# -*- coding: utf-8 -*-
from kodiswift import Plugin
import cookielib, urllib2 
import simplejson as json
import copy
from language import get_string as _

plugin = Plugin()

USER_AGENT = 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-GB; rv:1.9.0.3) Gecko/2008092417 Firefox/3.0.3'
PER_PAGE = 20

def nextpage(url, length):
    if length >= PER_PAGE:
        return [{'label': _("previous"), 'path': url}]
    else:
        return []

def api_call(query):
    api_base_url="https://api-v2.hearthis.at/"
    cj = cookielib.CookieJar()
    opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
    request = urllib2.Request(api_base_url+query)
    request.add_header('User-Agent', USER_AGENT)
    response = opener.open(request)
    jsono = response.read()
    response.close()
    return json.loads(jsono)


@plugin.route('/')
def main_menu():
    items = [
                {'label': _("Recently added"), 'path': plugin.url_for('show_feed_first', ftype='new', page=1, first=True)},
                {'label': _("Popular"), 'path': plugin.url_for('show_feed_first', ftype='popular', page=1, first=True)},
                {'label': _("Genres"), 'path': plugin.url_for('show_genres')},
                {'label': _("Search"), 'path': plugin.url_for('search_first', skey='x', page=1, first=True)}
            ]

    return items

@plugin.route('/user/<user>')
def show_user(user):
    u = api_call(user)
    tracks = api_call(user+'/?type=tracks')
    selectors = [
                    {'label': 'Playlists ('+str(u['playlist_count'])+')', 'path': plugin.url_for('show_users_playlists_firstpage', user=user)},
                    {'label': 'Likes ('+str(u['likes_count'])+')', 'path': plugin.url_for('show_users_likes_firstpage', user=user)}
                ]
    return selectors +  list_tracks(tracks)

@plugin.route('/playlist/<plink>')
def play_playlist(plink):
    plist = api_call('set/'+plink)
    return list_tracks(plist)

@plugin.route('/user/<user>/playlists', name='show_users_playlists_firstpage', options={'page': '1'})
@plugin.route('/user/<user>/playlists/<page>')
def show_users_playlists(user, page):
    lists = api_call('%s/?type=playlists?page=%d&count=%d' % (user, int(page), PER_PAGE))
    items = []
    for l in lists:
        items.append({'label': l['title'], 'path': plugin.url_for('play_playlist', plink=l['permalink'])})#,'is_playable': True})
    return items + nextpage(plugin.url_for('show_users_playlists', user=user, page=int(page)+1), len(items)) 

@plugin.route('/user/<user>/likes', name='show_users_likes_firstpage', options={'page': '1'})
@plugin.route('/user/<user>/likes/<page>')
def show_users_likes(user, page):
    tracks = api_call('%s/?type=likes?page=%d&count=%d' % (user, int(page), PER_PAGE))
    return list_tracks(tracks) + nextpage(plugin.url_for('show_users_likes', user=user, page=int(page)+1), len(tracks)) 
    
@plugin.route('/genres')
def show_genres():
    genres = api_call('categories')
    items = []
    for g in genres:
        items.append({
            'label': g['name'],
            'path': plugin.url_for('show_genre_firstpage', genre=g['id'])
        })
    
    return items

def pn_button(pagination, direction):
    page = pagination['args']['page']
    if pagination != None and (direction == 1 or page > 1):
        args = copy.deepcopy(pagination['args'])
        args['page'] += direction
        lbl = '%s (%d - %d)' % ((_("next"), page*PER_PAGE+1,(page+1)*PER_PAGE) if direction == 1 else (_("previous"), (page-1)*PER_PAGE+1,page*PER_PAGE))
        return {'label': lbl, 'path': plugin.url_for(pagination['call'], **args)}
    else:
        return None



@plugin.route('/feeds/<ftype>/<page>/<first>', name='show_feed_first')
@plugin.route('/feeds/<ftype>/<page>')
def show_feed(ftype, page, first=False):
    results = api_call(add_pp('feed/?type=%s' % (ftype), page))
    pagination={'call': 'show_feed', 'args':{'ftype': ftype, 'page': int(page)}}
    return list_tracks(results, pagination, first)

@plugin.route('/genre/<genre>/<page>/<first>', name='show_genre_first')
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
        items = [pn_button(pagination, -1)]
        for u in results:
            items.append({'label': '%s (%s tracks)' % (u['username'], str(u['track_count'])), 'icon': u['avatar_url'], 'path': plugin.url_for('show_user', user=u['permalink'])})
        items += [pn_button(pagination, 1)]
        return items

#TODO: sometimes jumps out of plugin while browsing search results
@plugin.route('/search/<skey>/<page>/<first>', name='search_first')
@plugin.route('/search/<skey>/<page>')
def search(skey, page, first=False):
    if first:
        kb = xbmc.Keyboard ('', _("Search"), False)
        kb.doModal()
        if kb.isConfirmed():
            skey = kb.getText()
        else:
            return None
    results = api_call(add_pp('search?t=%s/' % (skey), page))
    selectors = [
                        {'label': _("Search for artist only"), 'path': plugin.url_for('search_for_first', stype='user', skey=skey, page=1, first=True)},
                        {'label': _("Search for tracks only"), 'path': plugin.url_for('search_for_first', stype='tracks', skey=skey, page=1, first=True)}
                        ]
    pagination={'call': 'search', 'args':{'skey': skey, 'page': int(page)}}
    return list_tracks(results, pagination, first, pre = selectors)
    
   
@plugin.route('/play/<user>/<trackid>')
def play_track(user,trackid):
    playurl='https://hearthis.at/'+user+'/'+trackid+'/listen'
    plugin.log.info('Playing: %s'%playurl)
    return plugin.set_resolved_url(playurl)   

def list_tracks(tracklist, pagination = None, first=False, pre=[], post=[]):
    items = pre
    items.append(pn_button(pagination, -1))
    for t in tracklist:
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
                'path': plugin.url_for('play_track', trackid=t['permalink'], user=t['user']['permalink']),
                'is_playable': True
        })
    items = items + post
    items.append(pn_button(pagination, 1))
    
    #only skip history if turning pages, not if opening first page initially
    if pagination != None and not first:
        ul=True
    else:
        ul=False
    
    return plugin.finish(items, update_listing=ul)# if pagination != None else False)

def add_pp(call, page, sep = '&'):
    return '%s%spage=%d&count=%d' % (call, sep, int(page), PER_PAGE)


if __name__ == '__main__':
    plugin.run()
