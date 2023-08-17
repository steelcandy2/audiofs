# Copyright (C) James MacKay 2008
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

from distutils.core import setup

_pkgName = "audiofs"
_version = "0.3"
_pkgDir = "%s-%s" % (_pkgName, _version)

setup(author = "James MacKay",
    author_email = "jmackay@steelcandy.com",
    name = "AudioFS",
    url = "http://www.steelcandy.com",
    version = _version,
    description = "Audio-related FUSE filesystems, along with optional music directory management and MPD music server integration",
    license = "GPL version 3",
    platforms = "linux",
    requires = ["fuse (>=0.2)"],
    package_dir = { '': 'src' },
    packages = [_pkgName],
    scripts = ["src/%s" % s for s in ["activate-music-directory",
        "build-music-directory", "catalogue-music-directory",
        "change-music-rating", "create-compact-album-list", "create-playlist",
        "deactivate-music-directory", "dismantle-music-directory",
        "flac2mp3", "flactrack", "flac2ogg", "generate-playlists",
        "lirc-client", "list-unrated", "maintain-cache-directory",
        "mpd-add-tracks", "mpd-all", "mpd-insert-tracks", "mpd-request-tracks",
        "mpd-create-database", "mpd-decrease-rating",
        "mpd-hide-current-track-info", "mpd-increase-rating",
        "mpd-list-servers", "mpd-preload-playlists",
        "mpd-refresh-current-track-info", "mpd-server-info", "mpd-set-rating",
        "mpd-show-current-track-info", "mpd-speak-current-track-info",
        "mpd-update-radio-playlist", "mpd-select-server",
        "mpd-selected-server-mpc",
        "mpd-toggle-current-track-info", "musicsearch", "ncmpc-all",
        "preload-audio-files", "refresh-ratings-files",
        "show-music-rating"]],
    data_files = [("/etc/%s"  % _pkgName, ["etc/configuration.py.example"]),
                  ("/etc/%s"  % _pkgName, ["etc/lirc-client.map.example"]),
                  ("doc/%s"   % _pkgDir, ["doc/index.html"])])
