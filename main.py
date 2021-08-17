from flask import Flask, redirect, request
from sklearn.cluster import KMeans
import requests
import operator
import random
import string
import json

# Pour le lancer il faut installer sklearn et flask. Puis lancer le main.py
# Ce  programme n'a pas pour but d'etre parfait mais juste de vous permettre d'avoir une introductionà différents sujets tel que le clustering, flask, et les requetes en python.
#  Il y de nombreux point d'améliorations mais ce n'est pas le but ici.
app = Flask(__name__)
client_id = "votre client ID"
host = "http://127.0.0.1:5000"
redirect_uri = host+"/callback"
complete_auth_uri = "https://accounts.spotify.com/authorize?client_id="+client_id+"&redirect_uri=" + \
    redirect_uri+"&scope=user-read-private%20user-read-email%20playlist-modify-private&response_type=code&state=123"
token = ""
headers = {"Authorization": ""}


# La route callback sera celle à donner lors du premier appel à spotify c'est ici que nous allons recevoir notre token.
@app.route('/callback')
def callback():
    global token
    global headers
    # code récupére dans l'url
    code = request.args.get('code')
    data = {'code': code,
            'grant_type': 'authorization_code',
            'redirect_uri': redirect_uri}
    headers = {"Authorization": "Basic clientID+Secret en base64"}
    x = requests.post("https://accounts.spotify.com/api/token",
                      data=data, headers=headers)
    x = x.json()
    token = x['access_token']
    headers['Authorization'] = "Bearer "+token
    # Une fois que tout est terminé on redirige sur ready
    return redirect('/ready')


@app.route('/ready')
def readyEndpoint():
    return {"message": "Token OK", "lien":  host + "/playlist"}


# La fonciton getGenre va nous renvoyer un dictionnaire de genre selon des artistes données.
def getGenre(artist_ids):
    genre = {}
    rest_artist_ids = []
    # on boucle sur les artists
    for ids in artist_ids:
        rest_artist_ids.append(ids)
        # Quand on arrive à 50 on fait une recherche de genre pour les artistes récupérés
        if(len(rest_artist_ids) == 50):
            artist_data = requests.get(
                "https://api.spotify.com/v1/artists?ids="+','.join(rest_artist_ids), headers=headers).json()
            # Pour chaque artiste on va récupérer ses genres. Si le genre n'est pas dans le dict on l'ajoute et si il y est on incrément la valeur du genre.
            for a in artist_data['artists']:
                for g in a['genres']:
                    if g in genre:
                        genre[g] += 1
                    else:
                        genre[g] = 1
            rest_artist_ids = []

# Si il reste des artistes non traités, on les traites ici avec la meme logique.
    if len(rest_artist_ids) > 0:
        artist_data = requests.get(
            "https://api.spotify.com/v1/artists?ids="+','.join(rest_artist_ids), headers=headers).json()
        for a in artist_data['artists']:
            for g in a['genres']:
                if g in genre:
                    genre[g] += 1
                else:
                    genre[g] = 1
    return genre


# Ici on effectue une recherche "aléatoire" basé sur un genre et une lettre au hasard.
def searchNew(genre):
    ids_song_to_add = []
    ramdom_char = random.choice(string.ascii_letters)
    print("ramdom_char : ", ramdom_char)
    res = requests.get("https://api.spotify.com/v1/search?q=track:%22"+ramdom_char +
                       "%22+genre:%22"+genre+"%22t&type=track&limit=50", headers=headers).json()
#    res contient un tableau de chansons
#    On récupere uniquement l'id de chaque chanson.
    for s in res["tracks"]["items"]:
        ids_song_to_add.append(s["id"])
        # On récupere les attributs pour les ids récupéres dans la boucle.
    d = requests.get("https://api.spotify.com/v1/audio-features?ids=" +
                     ','.join(ids_song_to_add), headers=headers).json()
    return d


# Cet endpoint nous servira pour créer une nouvelle playlist qui sera basé sur la playlist donné en parametre.
# il s'appelera comme ceci : 127.0.O.1:5000/playlist?playlistURL=url de la playlist
@app.route('/playlist')
def playlist():
    playlist_name = ""
    full_id = []
    full_id_playlist = []
    audio_features = []
    artist_ids = []
    genre = {}
    user_id = ""
    playlist_id = ""
    playlist_url = request.args.get('playlistURL')

    # traitement de l'url pour ne récuperer que l'id, je pourrai ne demander que l'id de la playlist en parametre mais spotify ne permet pas ca c'est donc
    # plus facile de demander l'url compleete et de faire un traitement pour récupérer l'id par la suite.
    if playlist_url == None:
        return {"Message": "Url de la playlist non fourni"}

    playlist_url = playlist_url.replace(
        "https://open.spotify.com/playlist/", "")

    for c in playlist_url:
        if c == "?":
            break
        playlist_id += c
    # fin traitement

#  recupération de la playlsit
    s = requests.get("https://api.spotify.com/v1/playlists/" +
                     playlist_id, headers=headers).json()

    if "error" in s and (s['error']['status'] == 401 or s['error']['status'] == 400):
        return redirect('/')

    # récuperation du user id pour pouvoir créer la playlist
    u = requests.get("https://api.spotify.com/v1/me", headers=headers).json()

    user_id = u['id']
    playlist_name = s['name']

    # On boucle pour récuper les ids des différentes musiques
    for track in s['tracks']['items']:
        full_id.append(track['track']['id'])
        # Full id playlist contient les ids de toutes les musiques, on ajoutera d'autres ids dans le cas ou "next" n'est pas nul
        full_id_playlist.append(track['track']['id'])
        if track['track']['album']['artists'][0]['id'] not in artist_ids:
            artist_ids.append(track['track']['album']['artists'][0]['id'])

#  On récupere les features de chaque musique
    d = requests.get("https://api.spotify.com/v1/audio-features?ids=" +
                     ','.join(full_id), headers=headers).json()
    for data in d['audio_features']:
        audio_features.append(data)

    # On refait une passe tant qu'il y a des musiques à traiter
    if "next" in s['tracks']:
        s['next'] = s['tracks']['next']
        while s['next'] != None:
            full_id = []
            s = requests.get(s['tracks']['next'], headers=headers).json()
            for track in s['items']:
                full_id.append(track['track']['id'])
                full_id_playlist.append(track['track']['id'])
                if track['track']['album']['artists'][0]['id'] not in artist_ids:
                    artist_ids.append(
                        track['track']['album']['artists'][0]['id'])
            d = requests.get("https://api.spotify.com/v1/audio-features?ids=" +
                             ','.join(full_id), headers=headers).json()
            for data in d['audio_features']:
                audio_features.append(data)

    # Pour chaque artiste on recupere les genre.
    genre = getGenre(artist_ids)
    data_for_clustering = []

    # On ajouter les données necéssaire au clustering dans un tableau
    for d in audio_features:
        temp = [d['acousticness'], d['danceability'], d['energy'],
                d['instrumentalness'], d['loudness'], d['speechiness'], d['tempo']]
        data_for_clustering.append(temp)
    # On crée les clusters
    nb_clusters = int(len(data_for_clustering)/2)
    kmeans = KMeans(n_clusters=nb_clusters, max_iter=1000).fit(
        data_for_clustering)

    # On trie les genre pour commencer les rechechers par les genres les plus présents
    genre = dict(
        sorted(genre.items(), key=operator.itemgetter(1), reverse=True))

    newPlaylist = []
    for g in genre:
        print("Make search for genre : ", g)
        # Cherche de nouvelles musiques
        to_add = searchNew(g)
        # On boucle
        for elem in to_add['audio_features']:
            # Pour chaque musiques on récupere ses attributs
            to_pred = [[elem['acousticness'], elem['danceability'], elem['energy'],
                        elem['instrumentalness'], elem['loudness'], elem['speechiness'], elem['tempo']]]
            kmeans.predict(to_pred)
            # on calcul son score
            score = abs(kmeans.score(to_pred))
            if score < 0.90 and elem['id'] not in newPlaylist and elem['id'] not in full_id_playlist:
                # Si son score est bon qu'on ne l'a pas encore ajouté et que la musique n'est pas présente dans la playlist de base on ajoute.
                newPlaylist.append(elem['id'])
                print("score for "+elem['id']+" : ", score,
                      "| Len new playlist : ", len(newPlaylist))
            if len(newPlaylist) >= 35:
                print("quit")
                break
        if len(newPlaylist) >= 35:
            break

    # On fait le ménage si jamais deux musiques sont présentes
    newTracks = requests.get("https://api.spotify.com/v1/tracks?ids=" +
                             ','.join(newPlaylist), headers=headers).json()
    name_added = []
    final_json = []
    id_to_add = {"uris": []}
    for elem in newTracks['tracks']:
        if elem['name'] not in name_added:
            name_added.append(elem['name'])
            final_json.append({'id': elem["id"], "name": elem['name'],
                               'artists': elem['artists'][0]['name'], 'preview': elem['preview_url']})
            id_to_add["uris"].append("spotify:track:"+elem["id"])
        else:
            print("DOUBLE : ", elem["name"])

    # On crée la playlist puis on ajoute les musiques
    p = requests.post("https://api.spotify.com/v1/users/"+user_id+"/playlists", headers=headers,
                      data="{\"name\":\"For you inspired by " + playlist_name+"\",\"description\":\"New playlist description\",\"public\":false}".encode('utf-8')).json()
    playlist_id = p['id']
    pa = requests.post("https://api.spotify.com/v1/playlists/"+playlist_id +
                       "/tracks", headers=headers, data=json.dumps(id_to_add)).json()
    print(pa)
    return {"from": playlist_name, "data": final_json}


@app.route('/')
def auth():
    return redirect(complete_auth_uri)


app.run()
