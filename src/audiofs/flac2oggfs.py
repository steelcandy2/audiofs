# Defines a class that implements a FUSE filesystem that contains the result
# of merging the files under an optional "real" directory and OGG versions of
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

# The default bitrate for OGG files (in kbits).
_fs_defaultOggBitrate = 192


# Option names.
fs_bitrateOption = musicfs.fs_bitrateOption
fs_flacDirOption = musicfs.fs_flacDirOption


# Classes.

class fs_FlacToOggFilesystem(musicfs.fs_AbstractFlacReencodingFilesystem):
    """
    Represents filesystems that contain the result of merging the files
    under a 'realDir' directory (if any) and OGG versions of each of the FLAC
    files under a directory 'flacDir'.

    A FLAC file with pathname '$flacDir/some/dirs/name.flac' will generate an
    OGG file with pathname '$mountDir/some/dirs/name.ogg'
    """

    def __init__(self, *args, **kw):
        musicfs.fs_AbstractFlacReencodingFilesystem. \
            __init__(self, *args, **kw)
        #self._fs_converter = music.mu_FfmpegFlacToOggTrackConverter()
        self._fs_converter = music.mu_OggEncFlacToOggTrackConverter()
        self._fs_oggBitrate = _fs_defaultOggBitrate

    def fs_processOptions(self, opts):
        musicfs.fs_AbstractFlacReencodingFilesystem. \
            fs_processOptions(self, opts)
        val = fscommon.fs_parseOptionalSuboption(opts, fs_bitrateOption)
        self._fs_oggBitrate = musicfs.fs_parseBitrateOptionValue(val,
                                                    _fs_defaultOggBitrate)
        assert self._fs_oggBitrate > 0

    def fs_oggBitrate(self):
        """
        The bitrate that the OGG files that we generate are to have, in
        kbits.
        """
        result = self._fs_oggBitrate
        assert result > 0
        return result


    def fs_hasTargetMusicFileFilename(self, f):
        # Overrides version in fs_AbstractMusicFilesystem.
        assert f is not None
        return music.mu_hasOggFilename(f)

    def fs_addTargetMusicFileExtension(self, base):
        # Overrides version in fs_AbstractFlacReencodingFilesystem.
        assert base is not None
        result = music.mu_addOggExtension(base)
        assert result is not None
        return result

    def _fs_writeReencodedFileContentsShellCommand(self, flacPath):
        assert flacPath is not None
        result = self._fs_converter.mu_createShellCommand(flacPath,
                                                self.fs_oggBitrate())
        assert result is not None
        return result

    def _fs_realFileTagsMetadataFileContents(self, realPath):
        # Overrides version in fs_AbstractFlacReencodingFilesystem.
        #debug("---> in fs_FlacToOggFilesystem._fs_realFileTagsMetadataFileContents(%s)" % realPath)
        assert realPath is not None
        result = music.mu_oggTagsMap(realPath)
        #debug("    OGG tags map = [%s]" % ", ".join(result))
        result = music.mu_convertOggToFlacTagNameMap(result)
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
    # flac2oggfs -o flac=PATH [real=PATH] cache=PATH [bitrate=RATE] mountpoint
    usage = """

A filesystem that contains the result of merging the OGG files under a
directory 'realDir' (if any) and the OGG files that are re-encodings
of the FLAC files under the directory 'flacDir'. The generated OGG
files are cached under the directory 'cacheDir'.

""" + fscommon.fs_commonUsage
    fs = fs_FlacToOggFilesystem(version = "%prog " + fscommon.fs_fuseVersion,
                                 usage = usage, dash_s_do = 'setsingle')
    mergedfs.fs_addNoMetadataOption(fs.parser)
    fs.parser.add_option(mountopt = fs_flacDirOption,
        metavar = "PATH", help = "look for FLAC files under PATH")
    fs.parser.add_option(mountopt = mergedfs.fs_realDirOption,
        metavar = "PATH", help = "look for 'real' OGG files under PATH")
    fs.parser.add_option(mountopt = mergedfs.fs_cacheDirOption,
        metavar = "PATH", help = "cache OGG files under PATH")
    fs.parser.add_option(mountopt = fs_bitrateOption, metavar = "RATE",
        default = str(_fs_defaultOggBitrate),
        help = "the OGG files' bitrate (default = %default kbits)")
    fs.fs_start(usage)
