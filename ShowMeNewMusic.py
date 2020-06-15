import requests
import spotipy
import spotipy.util as util
from Secrets import CLIENT_ID, CLIENT_SECRET
from threading import Timer

# spotipy docs: https://spotipy.readthedocs.io/en/2.12.0/
# Spotify Web API docs: https://developer.spotify.com/documentation/web-api/

# Generates a playlist of new music based on a certain set of criteria, either my most listened tracks or artists
# This program will not recommend songs that are already in specified "filter playlists", and the program will not recommend
# the same song again if it has recommended that song in the last 200 recommendations
# If the user currently has a player open, the playlist will be autoplayed

# COMMAND LINE:
# operable from the command line by creating aliases
# to access aliases, type "edit" in command line
# command to run this file: newmusic

# Constants
SEARCH_CRITERIA = "TRACK" # What data to use to make recommendations, either TRACK or ARTIST
PLAYLIST_LENGTH = 50 # minimum number of songs to include
PLAYLIST_TITLE = "Show Me New Music"
FILTER_PLAYLISTS = ["Not Rap", "i cant speak korean"]

# Authorization
SCOPE = "user-top-read playlist-modify-private playlist-modify-public playlist-read-private user-library-modify user-library-read streaming app-remote-control user-modify-playback-state user-read-playback-state"
REDIRECT_URI = "http://localhost:8888"
token = util.prompt_for_user_token("danielwei816",
                                   SCOPE,
                                   client_id=CLIENT_ID,
                                   client_secret=CLIENT_SECRET,
                                   redirect_uri=REDIRECT_URI)

spotify = spotipy.Spotify(auth=token)

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

#retrieving my top artists, tracks
top_artists = spotify.current_user_top_artists(time_range="short_term")
top_tracks = spotify.current_user_top_tracks(time_range="short_term")

# retrieving Spotify IDs and names of my top 5 artists and tracks
top_five_artists_id, top_five_tracks_id, top_five_artists_name, top_five_tracks_name = [], [], [], []
for i in range(0, 5):
    top_five_artists_id.append(top_artists["items"][i]["id"])
    top_five_tracks_id.append(top_tracks["items"][i]["id"])
    top_five_artists_name.append(top_artists["items"][i]["name"])
    top_five_tracks_name.append(top_tracks["items"][i]["name"])

#finding my top genres by analyzing the genres of my top artists
genre_dictionary = {}
for artist in top_artists["items"]:
    genres = artist["genres"]
    for genre in genres:
        if genre in genre_dictionary:
            genre_dictionary[genre] += 1
        else:
            genre_dictionary[genre] = 1

sorted_genres = sorted(genre_dictionary.items(),
                       key=lambda x: x[1], reverse=True)

max_genres = 5 if len(sorted_genres) >= 5 else len(sorted_genres)
top_genres = []
usable_genres = spotify.recommendation_genre_seeds()
for i in range(0, max_genres):
    genre = sorted_genres[i][0]
    if (genre in usable_genres["genres"]):
        top_genres.append(genre)

print("My top genres: " + str(top_genres))
print("My top artists: " + str(top_five_artists_name))
print("My top tracks: " + str(top_five_tracks_name))

# repeatedly find recommendations until our playlist has at least 30 songs
# checks against an array of playlist names the I've listed to filter out songs I've already found
# NOTE: an interesting detail for the future: I believe Spotify has many duplicate songs: songs that are the same by name
# and sound but are uploaded multiple times under different ids...which could mess up the filtering process. Will disregard this for now.

master_filter_ids = []
master_filter_names = []

playlists = spotify.current_user_playlists()
for filter_playlist in FILTER_PLAYLISTS:
    for playlist in playlists["items"]:
        tracks = getAllTracks(playlist["id"])
        if playlist["name"] == filter_playlist:
            for track_id in [track["id"] for track in tracks]:
                master_filter_ids.append(track_id)

# also exclude previously recommended songs
prev_recs = open("PreviouslyRecommended.txt", "r")
for track_id in prev_recs:
    track_id = track_id.replace("\n", "")
    master_filter_ids.append(track_id)
prev_recs.close()

master_playlist_ids = [] # the final list of songs (in Spotify id format)

while len(master_playlist_ids) < PLAYLIST_LENGTH:
    # get recommendation tracks based on my top tracks
    # (recommendations can be based on any 5 seeds consisting of a combo of genres, artists, or tracks)
    # NOTE: spotify returns a different result from this function every time it is called
    recommendations = []

    if SEARCH_CRITERIA == "TRACK":
        recommendations = spotify.recommendations(seed_tracks=top_five_tracks_id)
    else:
        recommendations = spotify.recommendations(seed_artists=top_five_artists_id)
    
    recommended_track_ids = [track["id"]
                             for track in recommendations["tracks"]]

    recommended_track_ids = [track_id for track_id in recommended_track_ids if track_id not in master_filter_ids and track_id not in master_playlist_ids]

    # These lists might actually be different lengths due to the issue stated in the NOTE above.
    for track_id in recommended_track_ids:
        master_playlist_ids.append(track_id)

# add our new recommendations to the previously recommended list so they don't get recommended again either
prev_recs = open("PreviouslyRecommended.txt", "r")
contents = prev_recs.readlines()
prev_recs.close()

if len(contents) + len(master_playlist_ids) >= 200:
    # print("OOOPS")
    prev_recs = open("PreviouslyRecommended.txt", "w")

    for id in master_playlist_ids:
        contents.insert(0, id + "\n")

    contents = contents[0:100]

    prev_recs.writelines(contents)
    
else:
    prev_recs = open("PreviouslyRecommended.txt", "a")
    for id in master_playlist_ids:
        prev_recs.write(id + "\n")

prev_recs.close()

print("Forming playlist...")

# create playlist and add tracks
# get user id
user_id = spotify.me()["id"]

# see if playlist already exists
new_playlist = None
playlists = spotify.current_user_playlists()
for playlist in playlists["items"]:
    if playlist["name"] == PLAYLIST_TITLE:
        new_playlist = playlist
        break

if new_playlist is None:
    new_playlist = spotify.user_playlist_create(user_id, PLAYLIST_TITLE, True)
    spotify.user_playlist_add_tracks(user_id, new_playlist["id"], master_playlist_ids)
else:
    spotify.user_playlist_replace_tracks(user_id, new_playlist["id"], master_playlist_ids)

def begin_playback(spotify, device_id):
    spotify.start_playback(device_id=device_id, context_uri=new_playlist["uri"], offset={"position": 0})
    spotify.shuffle(False)
    
playback = spotify.current_playback()
device_id = None
if playback is not None:
    device_id = playback["device"]["id"]
else:
    user_devices = spotify.devices()
    if len(user_devices["devices"]) > 0:
        device_id = user_devices["devices"][0]["id"]

# start playing the playlist, starting at the first song and turning off shuffle
# delay the playing to make time for the api to finish creating the new playlist
print("Done. ENJOY!")
if device_id is not None:
    t = Timer(5.0, begin_playback, [spotify, device_id])
    t.start()
else:
    print("No devices available to play music.")

