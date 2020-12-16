## To run:

You will need to install jsonschema for JSON validation:

```sh
pip install jsonschema
```

The program accepts one (required) positional argument specifying the file
that describes the changes, one option that specifies an input file, and one
option that specifies an output file. If the options are left unspecified,
the program will read from stdin and/or write to stdout respectively. All
logging messages will be emitted to stderr.

## Example usage:

```sh
python remix.py changes.json -i mixtape-data.json -o output.json
```

Is equivalent to:

```sh
cat mixtape-data.json | python remix.py changes.json > output.json
```

## Summary

Changes are performed in the following order: First, all additions to playlists
will be applied (in the order in which they are specified in the corresponding
array), then all playlists marked for removal will be removed, and finally all
new playlists will be created. This order ensures that all playlist indices
referenced by playlist additions are allowed to resolve, so long as they match
an extant playlist, even if that playlist is marked for removal. Additionally,
it prevents a playlist addition from being applied to a new playlist, as new
playlists have unspecified IDs and this would result in undefined behavior.

The program re-uses old IDs when creating new playlists, as the input file does
not contain a field for specifying previously-consumed IDs, so there would
never be a way to ensure IDs were not re-used.

If errors are encountered in the JSON schema validation of the changes file, the
program will print the error and exit early, producing no output, as malformed 
JSON implies that the underlying objects cannot be reliably indexed. If instead
the schema validates, but some IDs referenced in the changeset do not themselves
reference existing IDs in the input file, the changes with invalid IDs will be
skipped, a corresponding error will be logged, and the program will exit with
code 1, but will still produce output based on the valid changes in the changes
file.

## Ideas for expanding to larger-scale applications

The most important thing we could do if we were moving this application to a
larger scale would be to use a database instead of a JSON file to store the
data (playlists, users, songs). As I anticipate changes would likely be coming
from external users, I would also recommend moving to a server executing update
queries on the database, likely providing a RESTful interface to do so.
For very large scale, I would also recommend moving to UUIDs instead of
auto-incrementing sequential keys for IDs to allow for a distributed database.