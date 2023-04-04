#!/usr/bin/env python3
#
# steam.py: read steam data in python
# Copyright (C) 2023 Rafael Stauffer
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#

import os
import os.path
from pathlib import Path
from sys import platform

__doc__ = """
Gets the steam game path for win64 and linux
"""


class AcfReader:
    """
    Reads steam ACF/VDF files
    Files are composed out of tab separated key value pairs in quotation marks
    Subelements are encased in curly brackets
    """

    def __init__(self):
        self.filepath = None
        self.data = {}

    def _key_value_split(self, data: str):
        schema = {}

        has_key = False
        current_key = ""

        position = 0
        while position < len(data):
            if has_key:
                if '"' in data[position]:
                    if (
                        data[position].count('"') == 1
                    ):  # this value contains whitespace and was split up
                        schema[current_key] = data[position].removeprefix('"')
                        position += 1
                        while not '"' in data[position]:
                            schema[current_key] = (
                                schema[current_key] + " " + data[position]
                            )
                            position += 1
                        schema[current_key] = (
                            schema[current_key] + " " + data[position].removesuffix('"')
                        )
                    else:
                        schema[current_key] = (
                            data[position].removeprefix('"').removesuffix('"')
                        )
                elif "{" in data[position]:
                    level = 1
                    position += 1
                    start_position = position
                    while level > 0:
                        if '"' in data[position]:
                            pass
                        if "{" in data[position]:
                            level += 1
                        elif "}" in data[position]:
                            level -= 1
                        position += 1
                    position -= (
                        1  # we tend to overshoot with the while check, reign back in
                    )
                    if position - start_position < 2:  # this is an empty list
                        schema[current_key] = {}
                    else:
                        schema[current_key] = self._key_value_split(
                            data[start_position:position]
                        )
                else:
                    raise ValueError(
                        f"ACF-File {self.filepath}\nExpected value or list on position {position}, got {data[position]}"
                    )

                has_key = False
            else:
                if not '"' in data[position]:
                    raise ValueError(
                        f"ACF-File {self.filepath}\nExpected key on position {position}, got {data[position]}"
                    )

                has_key = True
                current_key = data[position].removeprefix('"').removesuffix('"')
                schema[current_key] = None
            position += 1

        return schema

    def load(self, path):
        """
        Loads a file from path
        """

        self.filepath = path
        self.data = {}

        with open(path, "r", encoding="utf-8") as infile:
            self.data = self._key_value_split(infile.read().strip().split())

    def get_game_base_path(self, steam_gameid):
        """
        This method reads from the libraryfolders
        """

        if len(self.data) < 1:
            raise ValueError("No data loaded. Load libraryfolders.vdf first")

        if not "libraryfolders" in self.data:
            raise ValueError("Root node 'libraryfolders' not found. Wrong file?")

        for savepoint_id in self.data["libraryfolders"]:
            for app_id in self.data["libraryfolders"][savepoint_id]["apps"]:
                if app_id == steam_gameid:
                    return self.data["libraryfolders"][savepoint_id]["path"]

        raise FileNotFoundError("Game base path could not be determined")

    def _check_loaded_manifest(self):
        """
        Checks if this is a loaded manifest
        """

        if len(self.data) < 1:
            raise ValueError("No data loaded. Load appmanifest_<gameid>.acf first")

        if not "AppState" in self.data:
            raise ValueError("Root node 'AppState' not found. Wrong file?")

    def get_game_installdir(self):
        """
        returns installdir
        """

        self._check_loaded_manifest()

        return self.data["AppState"]["installdir"]

    def get_game_name(self):
        """
        returns name
        """

        self._check_loaded_manifest()

        return self.data["AppState"]["name"]

    def get_appid(self):
        """
        returns appid
        """

        self._check_loaded_manifest()

        return self.data["AppState"]["appid"]

def get_all_installed_games():
    """
    Returns dict of all installed games with appid
    """

    installed_games = {}

    steam_path = get_steam_path()

    libfolder_path = os.path.join(steam_path, "steamapps", "libraryfolders.vdf")
    reader = AcfReader()
    reader.load(libfolder_path)

    for drive_id in reader.data["libraryfolders"]:
        steamapps_path = os.path.join(
            reader.data["libraryfolders"][drive_id]["path"], "steamapps"
        )

        for acf_name in os.listdir(steamapps_path):
            if ".acf" in acf_name:
                manifest_reader = AcfReader()
                manifest_reader.load(os.path.join(steamapps_path, acf_name))

                installed_games[manifest_reader.get_game_name()] = manifest_reader.get_appid()

    return installed_games

def get_appid_by_name(gamename):
    """
    Searches steam libraries and reads all manifest files to find app id for a given gamename
    """

    installed_games = get_all_installed_games()

    if not gamename in installed_games:
        raise FileNotFoundError(
            f"No game with name {gamename} was found in the steam library"
        )

    return installed_games.get(gamename)


def get_game_appdata_path(steam_gameid, install_dir_override: str | None = None):
    """
    Returns appdata save path for a steam app
    steam_gameid: steam app id returned by get_appid_by name
    install_dir_override: set searched foldername manually if appmanifest contains wrong data
    """

    steam_path = get_steam_path()

    libfolder_path = os.path.join(steam_path, "steamapps", "libraryfolders.vdf")
    reader = AcfReader()
    reader.load(libfolder_path)
    base_path = reader.get_game_base_path(steam_gameid)

    manifest_path = os.path.join(
        base_path, "steamapps", f"appmanifest_{steam_gameid}.acf"
    )

    manifest_reader = AcfReader()
    manifest_reader.load(manifest_path)

    installdir = manifest_reader.get_game_installdir()
    if install_dir_override:
        installdir = install_dir_override

    emulated_path = os.path.join(
        base_path,
        "steamapps",
        "compatdata",
        str(steam_gameid),
        "pfx",
        "drive_c",
        "users",
        "steamuser",
        "AppData",
        "Local",
        installdir,
    )

    if os.path.exists(emulated_path):  # are we emulated in proton?
        return emulated_path

    emulated_path_low = os.path.join(
        base_path,
        "steamapps",
        "compatdata",
        str(steam_gameid),
        "pfx",
        "drive_c",
        "users",
        "steamuser",
        "AppData",
        "LocalLow",
        installdir,
    )

    if os.path.exists(
        emulated_path_low
    ):  # are we emulated in proton with a local low path
        return emulated_path_low

    standard_path = os.path.expandvars(os.path.join("%LOCALAPPDATA%", installdir))

    if os.path.exists(standard_path):  # we have a local appdata path?
        return standard_path

    standard_path = os.path.expandvars(os.path.join("%APPDATA%", installdir))

    if os.path.exists(standard_path):  # we have a appdata path?
        return standard_path

    appdata_path = Path(os.path.expandvars(os.path.join("%LOCALAPPDATA%")))
    standard_path = os.path.join(appdata_path.parent.absolute(), "LocalLow", installdir)

    if os.path.exists(standard_path):  # we have a locallow appdata path?
        return standard_path

    raise FileNotFoundError("appdata not found")


def get_game_install_path(steam_gameid):
    """
    Returns installation path for a steam app
    steam_gameid: steam app id returned by get_appid_by name
    """

    steam_path = get_steam_path()

    libfolder_path = os.path.join(steam_path, "steamapps", "libraryfolders.vdf")
    reader = AcfReader()
    reader.load(libfolder_path)
    base_path = reader.get_game_base_path(steam_gameid)

    manifest_path = os.path.join(
        base_path, "steamapps", f"appmanifest_{steam_gameid}.acf"
    )

    manifest_reader = AcfReader()
    manifest_reader.load(manifest_path)

    return os.path.join(
        base_path, "steamapps", "common", manifest_reader.get_game_installdir()
    )


def get_steam_path():
    """
    Returns steam installation path
    """

    if platform in ("linux", "linux2"):
        # linux

        return os.path.expanduser("~/.var/app/com.valvesoftware.Steam/.steam/steam")

    if platform == "darwin":
        # OS X

        raise NotImplementedError("OS X not supported")

    if platform == "win32":
        # Windows...

        import winreg

        con_registry = winreg.ConnectRegistry(None, winreg.HKEY_LOCAL_MACHINE)

        con_key = winreg.OpenKey(con_registry, "SOFTWARE\\Wow6432Node\\Valve\\Steam")
        item_value, _ = winreg.QueryValueEx(con_key, "InstallPath")

        return item_value

    raise NotImplementedError("Unknown platform")


def _get_loginuser_vdf():
    """
    Returns acf reader with loginusers data which contains the last logged in user
    """

    loginuser_path = os.path.join(get_steam_path(), "config", "loginusers.vdf")
    login_reader = AcfReader()
    login_reader.load(loginuser_path)
    return login_reader


def _get_loginuser_info(key: str):
    """
    Returns the value to key from loginusers user
    """

    reader = _get_loginuser_vdf()

    for _, user_data in reader.data.get("users").items():
        return user_data.get(key)

    raise ValueError("No user in loginusers.vdf found")


def get_personal_name():
    """
    Returns the personal name (currently displayed name) of the latest steam account
    """

    return _get_loginuser_info("PersonaName")


def get_account_name():
    """
    Returns the account name (the one which the account was created with) of the latest steam account
    """

    return _get_loginuser_info("AccountName")


if __name__ == "__main__":
    import unittest

    class TestSteamReader(unittest.TestCase):
        """
        Tests the steam reader
        Scenarios are tailored to my setup and will fail if not changed
        """

        def test_install_path(self):
            """
            Check if install path of syntetik is found on drive
            """

            # get_game_install_path('984110')  # synthetik arena
            game_path = get_game_install_path("528230")  # synthetik ultimate

            self.assertEqual(
                "/data/steam/SteamLibrary/steamapps/common/Synthetik", game_path
            )

        def test_appdata_path(self):
            """
            Check if emulated appdata of syntetik is found on drive
            """

            appdata_path = get_game_appdata_path("528230")
            self.assertEqual(
                "/data/steam/SteamLibrary/steamapps/compatdata/528230/pfx/drive_c/users/steamuser/AppData/Local/Synthetik",
                appdata_path,
            )

        def test_appid_by_name(self):
            """
            Check if Dominions 5 and Noita appid can be found
            """

            appid = get_appid_by_name("Dominions 5")
            self.assertEqual("722060", appid)

            appid = get_appid_by_name("Noita")
            self.assertEqual("881100", appid)

    unittest.main()
