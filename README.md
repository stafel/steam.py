# steam.py
inofficial python library to read steam data

Need to install mods or modify a save game? No more searching or guessing!

```python
from steam import get_appid_by_name, get_game_appdata_path

sy_appid = get_appid_by_name("SYNTHETIK")
data_path = get_game_appdata_path(sy_appid)
# TODO: The fun stuff here
```

Hacked together for my own usecases. OS X support is nonexistant.

Functions:
- get_steam_path: Return steam install path. Linux: flatpak only at the moment.
- get_all_installed_games: Returns dict with game name and appid of all installed games.
- get_appid_by_name: Returns the steam appid from a game name.
- get_game_install_path: Returns the installation path for an appid.
- get_game_appdata_path: Returns the appdata path for an appid. Overwrite the searched directory with install_dir_override if steam has incomplete data.
- get_personal_name: Returns the currently displayed name of the last logged in user.
- get_account_name: Returns steam account name of the last logged in user.