#
# $Id: flac2mp3fs.py,v 1.46 2011/11/25 04:46:25 jgm Exp $
#
# Defines a class that implements a FUSE filesystem that contains the result
# of merging the files under an optional "real" directory and MP3 versions of
# FLAC files under another directory.
#
# The FUSE filesystem classes are assumed to use the fuse-python API.
#
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

import os
import os.path

import musicfs
import music
import mergedfs
from fscommon import debug, report, warn
import fscommon
import config
import utilities as ut


# Constants.

_conf = config.obtain()

# The default bitrate for MP3s (in kbits).
_fs_defaultMp3Bitrate = 192


# Option names.
fs_bitrateOption = musicfs.fs_bitrateOption
fs_flacDirOption = musicfs.fs_flacDirOption


# Classes.

class fs_FlacToMp3Filesystem(musicfs.fs_AbstractFlacReencodingFilesystem):
    """
    Represents filesystems that contain the result of merging the files
    under a 'realDir' directory (if any) and MP3 versions of each of the FLAC
    files under a directory 'flacDir'.

    A FLAC file with pathname '$flacDir/some/dirs/name.flac' will generate an
    MP3 file with pathname '$mountDir/some/dirs/name.mp3'
    """

    def __init__(self, *args, **kw):
        musicfs.fs_AbstractFlacReencodingFilesystem. \
            __init__(self, *args, **kw)
        #self._fs_converter = music.mu_FfmpegFlacToMp3TrackConverter()
        self._fs_converter = music.mu_LameFlacToMp3TrackConverter()
        self._fs_mp3Bitrate = _fs_defaultMp3Bitrate

    def fs_processOptions(self, opts):
        musicfs.fs_AbstractFlacReencodingFilesystem. \
            fs_processOptions(self, opts)
        val = fscommon.fs_parseOptionalSuboption(opts, fs_bitrateOption)
        self._fs_mp3Bitrate = musicfs.fs_parseBitrateOptionValue(val,
                                                    _fs_defaultMp3Bitrate)
        assert self._fs_mp3Bitrate > 0

    def fs_mp3Bitrate(self):
        """
        The bitrate that the MP3s that we generate are to have, in kbits.
        """
        result = self._fs_mp3Bitrate
        assert result > 0
        return result


    def fs_hasTargetMusicFileFilename(self, f):
        # Overrides version in fs_AbstractMusicFilesystem.
        assert f is not None
        return music.mu_hasMp3Filename(f)

    def fs_addTargetMusicFileExtension(self, base):
        # Overrides version in fs_AbstractFlacReencodingFilesystem.
        assert base is not None
        result = music.mu_addMp3Extension(base)
        assert result is not None
        return result

    def _fs_writeReencodedFileContentsShellCommand(self, flacPath):
        assert flacPath is not None
        result = self._fs_converter.mu_createShellCommand(flacPath,
                                                self.fs_mp3Bitrate())
        assert result is not None
        return result

    def _fs_realFileTagsMetadataFileContents(self, realPath):
        # Overrides version in fs_AbstractFlacReencodingFilesystem.
        #debug("---> in fs_FlacToMp3Filesystem._fs_realFileTagsMetadataFileContents(%s)" % realPath)
        assert realPath is not None
        result = music.mu_mp3TagsMap(realPath)
        #debug("    MP3 tags map = [%s]" % ", ".join(result))
        result = music.mu_convertMp3ToFlacTagNameMap(result)
        #debug("    FLAC tags map = [%s]" % ", ".join(result))
        result = mergedfs.fs_tagsMapToMetadataFileContents(result)
        #debug("    metadata file contents = [%s]" % result)
        assert result is not None
        return result


# Main method.

def main():
    """
    Main method.
    """
    # flac2mp3fs -o flac=PATH [real=PATH] cache=PATH [bitrate=RATE] mountpoint
    usage = """

A filesystem that contains the result of merging the MP3 files under a
directory 'realDir' (if any) and the MP3 files that are re-encodings
of the FLAC files under the directory 'flacDir'. The generated MP3
files are cached under the directory 'cacheDir'.

""" + fscommon.fs_commonUsage
    fs = fs_FlacToMp3Filesystem(version = "%prog " + fscommon.fs_fuseVersion,
                                 usage = usage, dash_s_do = 'setsingle')
    mergedfs.fs_addNoMetadataOption(fs.parser)
    fs.parser.add_option(mountopt = fs_flacDirOption,
        metavar = "PATH", help = "look for FLAC files under PATH")
    fs.parser.add_option(mountopt = mergedfs.fs_realDirOption,
        metavar = "PATH", help = "look for 'real' MP3 files under PATH")
    fs.parser.add_option(mountopt = mergedfs.fs_cacheDirOption,
        metavar = "PATH", help = "cache MP3 files under PATH")
    fs.parser.add_option(mountopt = fs_bitrateOption, metavar = "RATE",
        default = str(_fs_defaultMp3Bitrate),
        help = "the MP3s' bitrate (default = %default kbits)")
    fs.fs_start(usage)
