import requests
import spotipy
import spotipy.util as util
from Secrets import CLIENT_ID, CLIENT_SECRET
from collections import OrderedDict

# spotipy docs: https://spotipy.readthedocs.io/en/2.12.0/
# Spotify Web API docs: https://developer.spotify.com/documentation/web-api/

# Sorts the specified playlist by artist name

# COMMAND LINE:
# operable from the command line by creating aliases
# to access aliases, type "edit" in command line
# command to run this file: sortmusic

# Authorization
SCOPE = "user-top-read playlist-modify-private playlist-modify-public playlist-read-private user-library-modify user-library-read streaming app-remote-control user-modify-playback-state user-read-playback-state"
REDIRECT_URI = "http://localhost:8888"
token = util.prompt_for_user_token("danielwei816",
                                   SCOPE,
                                   client_id=CLIENT_ID,
                                   client_secret=CLIENT_SECRET,
                                   redirect_uri=REDIRECT_URI)

spotify = spotipy.Spotify(auth=token)
user_id = spotify.me()["id"]

# gets all tracks in playlist
# we need this function because the spotify API has a limit of 100 tracks per request
# if the playlist has more than 100 songs, we need this function to make multiple requests to obtain all songs
# OUTPUT: a list of full Spotify Track objects
def getAllTracks(playlist_id):
    all_tracks = []
    tracks = spotify.playlist_tracks(playlist_id, limit=100)

    for actual_track in [item["track"] for item in tracks["items"]]: # actual track, since the original track object is layered in complexity
        all_tracks.append(actual_track)

    total_tracks = tracks["total"]
    counted_tracks = len(tracks["items"]) # we can only pull 100 tracks at a time
    while (counted_tracks < total_tracks):
        tracks = spotify.playlist_tracks(playlist_id, limit=100, offset=counted_tracks)
        for actual_track in [item["track"] for item in tracks["items"]]: 
            all_tracks.append(actual_track)
        counted_tracks += len(tracks["items"]) # we can only pull 100 tracks at a time
    
    return all_tracks

playlist_title = input("Name of playlist to sort: ")

# attempt to find the playlist
playlists = spotify.current_user_playlists()
playlist_id = None
for playlist in playlists["items"]:
    if playlist["name"] == playlist_title:
        playlist_id = playlist["id"]
        break


if playlist_id is not None: 

     # dictionary to map each artist to a list if their tracks
    dictionary = {}
    all_tracks = getAllTracks(playlist_id)
   
    for track in all_tracks:
        
        artist = track["artists"][0]["name"].lower() # we only care about the first artist
        track_id = track["id"]
        song_list = []

        if (artist in dictionary):
            song_list = dictionary[artist]

        song_list.append(track_id)
        dictionary[artist] = song_list

    # sort the dictionary by artist name
    dictionary = OrderedDict(sorted(dictionary.items(), key = lambda x : x[0]))
    
    # make a master list of every song in the dictionary
    all_songs = []
    for artist in dictionary:
        for song in dictionary[artist]:
            all_songs.append(song)

    # clear all tracks
    spotify.user_playlist_replace_tracks(user_id, playlist_id, [])

    # add tracks back in sorted order (must break into groups of 100)
    add_position = 0
    while (len(all_songs) > 0):
        subset_size = 100 if len(all_songs) > 100 else len(all_songs)
        subset = all_songs[0:subset_size]
        spotify.user_playlist_add_tracks(user_id, playlist_id, subset, add_position)
        all_songs = all_songs[subset_size: len(all_songs)]
        add_position += len(subset)

    print("Sorted")
else:
    print("Playlist couldn't be found.")