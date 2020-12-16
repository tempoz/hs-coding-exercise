import argparse
import inspect
import json
import logging
import os
import pathlib
import sys

try:
  import jsonschema
except ModuleNotFoundError:
  l = logging.getLogger()
  l.error('jsonschema is not installed; please run '
          '`python -m pip install jsonschema`.')
  
SCRIPT_DIRECTORY = pathlib.Path(os.path.dirname(os.path.abspath(
  inspect.stack()[0][1])))
CHANGESET_SCHEMA_FILEPATH = SCRIPT_DIRECTORY / 'schemas' / 'changeset.json'

def parse_args():
  parser = argparse.ArgumentParser()
  parser.add_argument(
    "changeset",
    help="The JSON file containing the changes to apply to the mixtape.")
  parser.add_argument(
    "--input-file", "-i",
    help="The JSON file containing the mixtape. "
         "Reads from stdin if no file is provided.")
  parser.add_argument(
    "--output-file", "-o",
    help="The file to output the altered mixtape to. "
         "Writes to stdout if no file is provided.")
  return parser.parse_args()

def execute_playlist_additions(
        mixtape, playlists_index, songs_index, playlist_additions):
  encountered_error = False
  for playlist_addition in playlist_additions:
    encountered_error |= add_to_playlist(mixtape,
                                         playlists_index,
                                         songs_index,
                                         playlist_addition['playlist_id'],
                                         playlist_addition['song_id'])

  return encountered_error

def add_to_playlist(mixtape, playlists_index, songs_index, playlist_id, song_id):
  l = logging.getLogger(__name__)

  id_is_missing = False
  if song_id not in songs_index:
    l.error(f'No song exists with id {song_id}. Error encountered when trying '
            f'to add song with id {song_id} to playlist with id {playlist_id}.')
    id_is_missing = True

  playlist_idx = None
  try:
    playlist_idx = playlists_index[playlist_id]
  except KeyError:
    l.error(f'No playlist exists with id {playlist_id}. Error encountered when '
            f'trying to add song with id {song_id} to playlist with id '
            f'{playlist_id}.')
    id_is_missing = True

  if id_is_missing:
    return True

  mixtape['playlists'][playlist_idx]["song_ids"].append(str(song_id))

  return False

def execute_remove_playlists(mixtape, playlists_index, remove_playlists):
  l = logging.getLogger(__name__)
  if not remove_playlists:
    return False

  encountered_error = False
  missing_id_set = set(remove_playlists) - playlists_index.keys()
  if missing_id_set:
    l.error(f'No playlists exist with the following ids: {missing_id_set}. '
            f'Error encountered while trying to remove playlists.')
    encountered_error = True

  remove_playlist_idx = sorted(
    (
      playlists_index.pop(playlist_id)
      for playlist_id in remove_playlists
      if playlist_id in playlists_index
    ),
    reverse=True)

  for playlist_idx in remove_playlist_idx:
    del mixtape['playlists'][playlist_idx]

  return encountered_error

def execute_new_playlists(mixtape, playlists_index, songs_index, new_playlists):
  if not new_playlists:
    return False

  encountered_error = False

  max_playlist_id = max(playlists_index) if playlists_index else 0
  free_playlist_ids = set(range(1, max_playlist_id)) - playlists_index.keys()

  users_index = create_id_to_index_dict(mixtape.get('users', []))

  for new_playlist in new_playlists:
    playlist_id = None
    if free_playlist_ids:
      playlist_id = free_playlist_ids.pop()
    else:
      max_playlist_id += 1
      playlist_id = max_playlist_id
    err = add_playlist(mixtape,
                        users_index,
                        songs_index,
                        playlist_id,
                        new_playlist['user_id'],
                        new_playlist['song_ids'])
    if err:
      free_playlist_ids.add(playlist_id)
      encountered_error |= err

  return encountered_error
      
def add_playlist(mixtape, users_index, songs_index, playlist_id, user_id, song_ids):
  l = logging.getLogger(__name__)

  encountered_error = False
  if user_id not in users_index:
    l.error(f'No user exists with id {user_id}. Error encountered when trying '
            f'to add a new playlist with a user with id {user_id} and songs '
            f'with the following ids: {song_ids}')
    encountered_error = True

  for song_id in song_ids:
    if song_id not in songs_index:
      l.error(f'No song exists with id {song_id}. Error encountered when '
              f'trying to add a new playlist with a user with id {user_id} and '
              f'songs with the following ids: {song_ids}')
      encountered_error = True

  if encountered_error:
    return True

  if not song_ids:
    l.error(f'Empty playlists are invalid. Encountered when trying to add a '
            f'new playlist for user with id {user_id}.')

  mixtape.setdefault('playlists', []).append({
    'id': str(playlist_id),
    'user_id': str(user_id),
    'songs': [str(song_id) for song_id in song_ids]
  })

  return False

def create_id_to_index_dict(object_list):
  return { int(obj['id']): idx for idx, obj in enumerate(object_list) }

def main():
  l = logging.getLogger(__name__)
  arguments = parse_args()

  with open(CHANGESET_SCHEMA_FILEPATH) as changeset_schema_file:
    changeset_schema = json.load(changeset_schema_file)
  
  with open(arguments.changeset) as changeset_file:
    changeset = json.load(changeset_file)

  try:
    jsonschema.validate(changeset, changeset_schema)
  except NameError:
    l.error('Could not run validation on changeset. May not fail gracefully.')
    
  mixtape = None
  if arguments.input_file:
    with open(arguments.input_file) as input_file:
      mixtape = json.load(input_file)
  else:
    mixtape = json.load(sys.stdin)

  playlists_index = create_id_to_index_dict(mixtape.get('playlists', []))

  songs_index = None
  if changeset.get('playlist_additions') or changeset.get('new_playlists'):
    songs_index = create_id_to_index_dict(mixtape.get('songs', []))

  encountered_error = execute_playlist_additions(
      mixtape,
      playlists_index,
      songs_index,
      changeset.get('playlist_additions', []))

  encountered_error |= execute_remove_playlists(
      mixtape,
      playlists_index,
      changeset.get('remove_playlists', []))

  encountered_error |= execute_new_playlists(mixtape,
                                             playlists_index,
                                             songs_index,
                                             changeset.get('new_playlists', []))

  if arguments.output_file:
    with open(arguments.output_file, 'w') as output_file:
      json.dump(mixtape, output_file, indent=2)
  else:
    json.dump(mixtape, sys.stdout, indent=2)

  return 1 if encountered_error else 0

if __name__ == '__main__':
  sys.exit(main())