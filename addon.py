# -*- coding: utf-8 -*-
from kodiswift import Plugin
import cookielib, urllib2 
import simplejson as json

plugin = Plugin()

USER_AGENT = 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-GB; rv:1.9.0.3) Gecko/2008092417 Firefox/3.0.3'
PER_PAGE = 20

def nextpage(url, length):
    if length >= PER_PAGE:
        return [{'label': plugin.get_string(33039), 'path': url}]
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
                {'label': plugin.get_string(33034), 'path': plugin.url_for('show_feed_firstpage',ftype='new')},
                {'label': plugin.get_string(33033), 'path': plugin.url_for('show_feed_firstpage',ftype='popular')},
                {'label': plugin.get_string(33035), 'path': plugin.url_for('show_genres')},
                {'label': plugin.get_string(33036), 'path': plugin.url_for('search')}
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


def list_tracks(tracklist):
    items = []
    for t in tracklist:
        items.append({
                'label': t['user']['username']+' - '+t['title']+'',
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
    return items

@plugin.route('/feeds/<ftype>', name='show_feed_firstpage', options={'page': '1'})
@plugin.route('/feeds/<ftype>/<page>')
def show_feed(ftype, page):
    feed = api_call('feed/?type=%s&page=%d&count=%d' % (ftype, int(page), PER_PAGE))
    return list_tracks(feed) + nextpage(plugin.url_for('show_feed', ftype=ftype, page=int(page)+1), len(feed)) 

@plugin.route('/genre/<genre>', name='show_genre_firstpage', options={'page': '1'})
@plugin.route('/genre/<genre>/<page>')
def show_genre(genre, page):
    lgenre = api_call('categories/%s/?page=%d&count=%d' % (genre, int(page), PER_PAGE))
    return list_tracks(lgenre) + nextpage(plugin.url_for('show_genre', genre=genre, page=int(page)+1), len(lgenre)) 


@plugin.route('/play/<user>/<trackid>')
def play_track(user,trackid):
    #api_call('categories')
    playurl='https://hearthis.at/'+user+'/'+trackid+'/listen'
    plugin.log.info('Playing: %s'%playurl)
    return plugin.set_resolved_url(playurl)

@plugin.route('/search/<stype>/<skey>')
def search_for(stype,skey):
    results = api_call('search?t='+skey+'&type='+stype)
    if stype == 'tracks':
        return list_tracks(results)
    elif stype == 'user':
        items = []
        for u in results:
            items.append({'label': u['username']+' ('+str(u['track_count'])+' tracks)', 'icon': u['avatar_url'], 'path': plugin.url_for('show_user',user=u['permalink'])})
        return items

@plugin.route('/search/')
def search():
    kb = xbmc.Keyboard ('', plugin.get_string(33036), False)
    kb.doModal()
    if kb.isConfirmed():
        text = kb.getText()
        results = api_call('search?t='+text)
        selectors = [
                        {'label': plugin.get_string(33037), 'path': plugin.url_for('search_for', stype='user', skey=text)},
                        {'label': plugin.get_string(33038), 'path': plugin.url_for('search_for', stype='tracks', skey=text)}
                    ]
        return selectors + list_tracks(results)
    else:
        return None
            

if __name__ == '__main__':
    plugin.run()
