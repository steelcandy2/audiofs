# Defines a class that represents a single MPD server.
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
import sys

import mergedfs
import music
import musicfs

import config
import utilities as ut


# Constants.

_conf = config.obtain()

# The base MPD music directory, ending with a pathname separator.
#_mp_mpdMusicDirectory = ut.ut_toCanonicalDirectory(_conf.baseDir)
_mp_mpdMusicDirectory = ut.ut_toCanonicalDirectory(_conf.rootDir)
_mp_mpdRealMusicDirectory = os.path.realpath(_mp_mpdMusicDirectory)

# If a regular file has one of these extensions then it is assumed to be a
# music file: otherwise it's assume to NOT be a music file.
#
# Note: we only include here the types of files that music.mu_tagsMap()
# can parse the tags of.
_mp_musicFileExtensions = [music.mu_mp3Extension, music.mu_flacExtension]
_mp_musicFileExtensions = \
    [ut.ut_fullExtension(ext) for ext in _mp_musicFileExtensions]

# The pathname of the mpc program to use to interact with an MPD server,
# and the mpd program itself.
_mp_mpcExecutable = _conf.mpcProgram
_mp_mpdExecutable = _conf.mpdProgram

# The format of the start of the command used to execute the 'mpc' command.
_mp_mpcCommandStartFormat = \
    "MPD_HOST=%s MPD_PORT=%i " + _mp_mpcExecutable + " "


# Format strings used in building various versions of an MPD database file.
_mp_infoBeginFmt = "info_begin\n"
_mp_infoEndFmt   = "info_end\n"
_mp_infoFormatFmt  = "format: %s\n"
_mp_infoVersionFmt = "mpd_version: %s\n"
_mp_infoCharsetFmt = "fs_charset: %s\n"
_mp_infoTagNames = [
    "Artist", "ArtistSort", "Album", "AlbumSort", "AlbumArtist",
    "AlbumArtistSort", "Title", "Track", "Name", "Genre", "Date", "Composer",
    "Performer", "Disc", "MUSICBRAINZ_ARTISTID", "MUSICBRAINZ_ALBUMID",
    "MUSICBRAINZ_ALBUMARTISTID", "MUSICBRAINZ_TRACKID",
    "MUSICBRAINZ_RELEASETRACKID"]
_mp_infoTagsFmt = "".join(["tag: %s\n" % t for t in _mp_infoTagNames])

_mp_mtimeFmt = "mtime: %i\n"

_mp_dirFmt = "directory: %s\n"
_mp_dirBeginFmt = "begin: %s\n"
_mp_dirEndFmt   = "end: %s\n"
_mp_dirMtimeFmt = _mp_mtimeFmt

_mp_songListBeginFmt = "songList begin\n"
_mp_songListEndFmt   = "songList end\n"

_mp_songBeginFmt = "song_begin: %s\n"
_mp_songEndFmt   = "song_end\n"

_mp_songKeyFmt = "key: %s\n"
_mp_songFileFmt = "file: %s\n"
_mp_songMtimeFmt = _mp_mtimeFmt
_mp_songTagFmt = "%s: %s\n"
_mp_songDurationFmt = "Time: %s\n"

# A map from the common music file tag names (as used in maps returned by
# default by music.mu_tagsMap()) to the names of the fields in an MPD
# database that hold the same information.
_mp_tagNameToMpdDatabaseName = {
    music.mu_flacTrackTitleTag:   "Title",
    music.mu_flacArtistTag:       "Artist",
    music.mu_flacAlbumTag:        "Album",
    music.mu_flacDateTag:         "Date",
    music.mu_flacTrackNumberTag:  "Track",
    music.mu_flacGenreTag:        "Genre",
#    music.mu_flacAlbumCddbTag:    "Disc",   # ????
    music.mu_flacCommentTag:      "Comment"
}

# The names of the common/FLAC tags corresponding to the information that
# is included in an MPD server's database file for each song, in the order
# that they are to appear.
_mp_mpdDatabaseSongTags = [music.mu_flacArtistTag, music.mu_flacAlbumTag,
    music.mu_flacTrackTitleTag, music.mu_flacDateTag, music.mu_flacGenreTag,
    music.mu_flacTrackNumberTag]

# TODO: instead of hardcoding 'UTF-8' here we should use the value of the
# 'filesystem_charset' property in /etc/mpd.conf !!!!
_mp_defaultMpdDatabaseCharset = "UTF-8"


# The names of the commands that can be sent to a
# mp_MpdInformationDisplayProcess.
_mp_showInfoCommand = "show"
_mp_hideInfoCommand = "hide"
_mp_toggleInfoCommand = "toggle"
_mp_refreshInfoCommand = "refresh"

# The basename of the FIFO to which to write commands to adjust how and
# whether information about the current MPD track is displayed.
_mp_displayInformationCommandSinkFilename = "mpd-display-info.sink"

# The basename of the file in the system directory that contains the
# MPD server information that is to be displayed (iff the file exists).
_mp_displayInformationFilename = "mpd-display-information.txt"



# Functions.

def mp_createMpdServerFromDescription(desc):
    """
    Creates and returns an mp_Mpd object that represents the MPD server
    described by 'desc', where 'desc' is a server description returned by a
    configuration object's mpdServerDescription() method.

    See config.conf_Configuration.mpdServerDescription().
    """
    assert desc is not None
    (host, port) = _conf.mpdServer(desc)
    result = mp_Mpd(host, port)
    assert result is not None
    return result

def mp_createMpdServerFromId(serverId):
    """
    Creates and returns an mp_Mpd object that represents the MPD server
    whose server ID (which is a string) is 'serverId', or returns None if
    there's no server with that ID.
    """
    assert serverId is not None
    desc = _conf.mpdServerDescription(serverId)
    if desc is not None:
        result = mp_createMpdServerFromDescription(desc)
        assert result is not None
    else:
        result = None
    # 'result' may be None
    return result

def mp_createDefaultMpdServer():
    """
    Creates and returns an mp_Mpd object that represents the default MPD
    server.
    """
    (host, port) = _conf.defaultMpdServer()
    result = mp_Mpd(host, port)
    assert result is not None
    return result


def mp_toMpdPathname(path):
    """
    Returns the pathname 'path' converted to one under our base music
    directory, if possible. (If it isn't possible to convert 'path' to a
    pathname under our base music directory then it is returned unchanged.)

    Note: there is no good way to tell from our result whether 'path' is
    under our base music directory.
    """
    #debug("---> in mp_toMpdPathname(%s)" % path)
    assert path is not None
    result = path
    base = _mp_mpdRealMusicDirectory
    p = ut.ut_really(path)
    #debug("    prefix = [%s], path = [%s]" % (base, p))
    result = ut.ut_removePathnamePrefix(p, base, path)
    assert result is not None
    return result

def mp_toMpdMusicFilePathnames(paths):
    """
    Generates the results of converting each of the pathnames in 'paths' into
    the pathnames of music files: they are converted to paths under our base
    music directory, if possible, and any directories are replaced with
    pathnames to all of the music files that it contains directly (that is,
    without descending into subdirectories).

    See mp_toMpdPathname().
    """
    #debug("---> in mp_toMpdMusicFilePathnames([%s])" % ", ".join(paths))
    assert paths is not None
    result = []
    #debug("    paths = [%s]" % ", ".join(paths))
    for p in paths:
        rp = ut.ut_really(p)
        if os.path.isdir(rp):
            for f in os.listdir(rp):
                fp = os.path.join(rp, f)
                if _mp_isMusicFile(fp):
                    yield mp_toMpdPathname(os.path.join(p, f))
        else:
            yield mp_toMpdPathname(p)

def mp_displayInformationCommandSink():
    """
    Returns the pathname of the FIFO to which to write commands to adjust how
    and whether information about the current MPD track is displayed.
    """
    result = _mp_displayInformationCommandSinkFilename
    result = os.path.join(_conf.systemDir, result)
    assert result is not None
    return result


def _mp_isMusicFile(path):
    """
    Returns True iff we recognize the file with pathname 'path' as being a
    music file.
    """
    assert path is not None
    rp = os.path.realpath(path)
    result = os.path.isfile(rp)
    if result:
        (base, ext) = os.path.splitext(rp)
        result = (ext in _mp_musicFileExtensions)
    return result

def _mp_isPathnameMetadataFile(path):
    """
    Returns True iff 'path' is the pathname of a metadata file that contains
    the pathname of the non-metadata file that it describes.
    """
    assert path is not None
    ext = mergedfs.fs_pathnameMetadataFileExtension
    result = mergedfs.fs_doesEndWithMetadataExtension(path, ext)
    return result

def _mp_readPathnameFromMetadataFile(path):
    """
    Reads and returns the pathname that is the entire contents of the
    pathname metadata file with pathname 'path', or None if the file
    doesn't exist, couldn't be read or has no contents.
    """
    assert path is not None
    result = None
    lines = ut.ut_readFileLines(path)
    if lines:
        result = lines[0]
        if len(lines) > 1:
            debug("the pathname metadata file [%s] has more than one line "
                  "in it")
    # 'result' may be None
    return result


def debug(msg):
    """
    Outputs the debugging message 'msg'.
    """
    print >> sys.stderr, msg


# Classes.

class _mp_Mpd_AbstractDatabaseBuilder(
                        musicfs.fs_AbstractMusicDirectoryCatalogueParser):
    """
    An abstract base class for classes that build an MPD server's database
    file from a music directory catalogue.
    """

    def __init__(self, dbPath, server):
        """
        Initializes this object with the pathname of the database file that
        it is to build for the MPD server 'server' (an instance of mp_Mpd).
        """
        musicfs.fs_AbstractMusicDirectoryCatalogueParser.__init__(self)
        assert dbPath is not None
        assert server is not None
        self._mp_mpdServer = server
        self._mp_dbPath = dbPath
        self._mp_writer = None
            # the file/stream object to use to write to our database file
        self._mp_songListStartDirs = []

    def _server(self):
        """
        Returns the MPD server that we're building a database for.
        """
        result = self._mp_mpdServer
        assert result is not None
        return result

    def _addSongListStartDirectory(self, relPath):
        """
        Adds the pathname 'relPath' to the end of our list of directories
        that we've started processing but haven't finished processing yet.
        """
        assert relPath is not None
        assert not os.path.isabs(relPath)
        self._mp_songListStartDirs.append(relPath)


    def _fs_beforeParsing(self):
        musicfs.fs_AbstractMusicDirectoryCatalogueParser. \
            _fs_beforeParsing(self)
        self._mp_writer = open(self._mp_dbPath, 'w')
        self._writePrologue(self._mp_writer)

    def _fs_processDirectoryStartInformation(self, info):
        assert info is not None
        relPath = info.fs_pathname()
        self._writeDirectoryStart(self._mp_writer, relPath, info)

    def _fs_processFileInformation(self, info):
        assert info is not None
        relPath = info.fs_pathname()
        w = self._mp_writer
        (dname, fname) = os.path.split(relPath)
        startDirs = self._mp_songListStartDirs
        if startDirs and startDirs[-1] == dname:
            startDirs.pop()
            self._writeSongListStart(w, dname, info)
        self._writeSongFile(w, relPath, info)

    def _fs_processDirectoryEndInformation(self, info):
        assert info is not None
        relPath = info.fs_pathname()
        self._writeDirectoryEnd(self._mp_writer, relPath, info)

    def _fs_afterParsing(self):
        assert len(self._mp_songListStartDirs) == 0
        try:
            w = self._mp_writer
            if w is not None:
                try:
                    self._writeEpilogue(w)
                finally:
                    w.close()
        finally:
            musicfs.fs_AbstractMusicDirectoryCatalogueParser. \
                _fs_afterParsing(self)


    def _writePrologue(self, w):
        """
        Writes out - using 'w' - the prologue/start of the database file.
        """
        assert w is not None
        raise NotImplementedError

    def _writeDirectoryStart(self, w, relPath, info):
        """
        Writes out - using 'w' - the start of the directory with relative
        pathname 'relPath', where 'info' contains additional information
        about the directory.
        """
        assert w is not None
        assert relPath is not None
        assert info is not None
        raise NotImplementedError

    def _writeSongListStart(self, w, relPath, info):
        """
        Writes out - using 'w' - the start of a list of songs contained in
        the directory with relative pathname 'relPath', where 'info' contains
        additional information about the directory.
        """
        assert w is not None
        assert relPath is not None
        assert info is not None
        raise NotImplementedError

    def _writeSongFile(self, w, relPath, info):
        """
        Writes out - using 'w' - the part of the database that describes the
        song/track represented by the file with relative pathname 'relPath',
        where 'info' contains additional information about the song file.
        """
        assert w is not None
        assert relPath is not None
        assert info is not None
        raise NotImplementedError

    def _writeDirectoryEnd(self, w, relPath, info):
        """
        Writes out - using 'w' - the end of the directory with relative
        pathname 'relPath', where 'info' contains additional information
        about the directory.
        """
        assert w is not None
        assert relPath is not None
        assert info is not None
        raise NotImplementedError

    def _writeEpilogue(self, w):
        """
        Writes out - using 'w' - the epilogue/end of the database file.
        """
        assert w is not None
        raise NotImplementedError

class mp_Mpd0_15DatabaseBuilder(_mp_Mpd_AbstractDatabaseBuilder):
    """
    Builds an MPD server's database file from a music directory catalogue,
    assuming the server's version is 0.15.n or lower.

    Note: I don't know if the database format changed with the server version
    number increasing to 0.16, so this builder may need to be used for early
    version 0.16.n servers, or another builder may need to be used for late
    0.15.n servers.

    See mp_Mpd0_16DatabaseBuilder.
    """

    def _writePrologue(self, w):
        assert w is not None
        w.write(_mp_infoBeginFmt)
        w.write(_mp_infoVersionFmt % self._server().version())
        w.write(_mp_infoCharsetFmt % _mp_defaultMpdDatabaseCharset)
        w.write(_mp_infoEndFmt)

    def _writeDirectoryStart(self, w, relPath, info):
        assert w is not None
        assert relPath is not None
        assert info is not None
        w.write(_mp_dirFmt % os.path.basename(relPath))
        w.write(_mp_dirBeginFmt % relPath)
        if info.fs_fileCount() > 0:
            self._addSongListStartDirectory(relPath)

    def _writeSongListStart(self, w, relPath, info):
        assert w is not None
        assert relPath is not None
        assert info is not None
        w.write(_mp_songListBeginFmt)

    def _writeSongFile(self, w, relPath, info):
        assert w is not None
        assert relPath is not None
        assert info is not None
        (dname, fname) = os.path.split(relPath)
        w.write(_mp_songKeyFmt % fname)
        w.write(_mp_songFileFmt % relPath)
        for tag in _mp_mpdDatabaseSongTags:
            val = info.fs_tagValue(tag)
            if val is not None:
                name = _mp_tagNameToMpdDatabaseName.get(tag)
                if name is not None:
                    w.write("%s: %s\n" % (name, val))
        w.write(_mp_songMtimeFmt % info.fs_lastModifiedTime())

    def _writeDirectoryEnd(self, w, relPath, info):
        assert w is not None
        assert relPath is not None
        assert info is not None
        if info.fs_fileCount() > 0:
            w.write(_mp_songListEndFmt)
        w.write(_mp_dirEndFmt % relPath)

    def _writeEpilogue(self, w):
        assert w is not None
        pass  # currently no footer to add to db file

class mp_Mpd0_16DatabaseBuilder(_mp_Mpd_AbstractDatabaseBuilder):
    """
    Builds an MPD server's database file from a music directory catalogue,
    assuming the server's version is 0.16 or higher.

    Note: I don't know if the database format changed with the server version
    number increasing to 0.16, so this builder may need to be used for late
    version 0.15.n servers, or another builder may need to be used for early
    0.16.n servers.

    See mp_Mpd0_15DatabaseBuilder.
    """

    def _writePrologue(self, w):
        assert w is not None
        w.write(_mp_infoBeginFmt)
        w.write(_mp_infoFormatFmt % "1")
        w.write(_mp_infoVersionFmt % self._server().version())
        w.write(_mp_infoCharsetFmt % _mp_defaultMpdDatabaseCharset)
        w.write(_mp_infoTagsFmt)
        w.write(_mp_infoEndFmt)

    def _writeDirectoryStart(self, w, relPath, info):
        assert w is not None
        assert relPath is not None
        assert info is not None
        w.write(_mp_dirFmt % os.path.basename(relPath))
# TODO: add 'mtime' back in if and when that information is contained in the
# catalogue !!!
# - though the way we build the catalogue doesn't make that easy, at least
#   for some directories
        #w.write(_mp_dirMtimeFmt % info.fs_lastModifiedTime())
        w.write(_mp_dirBeginFmt % relPath)

    def _writeSongListStart(self, w, relPath, info):
        assert w is not None
        assert relPath is not None
        assert info is not None
        pass # we don't write anything here

    def _writeSongFile(self, w, relPath, info):
        assert w is not None
        assert relPath is not None
        assert info is not None
        (dname, fname) = os.path.split(relPath)
        w.write(_mp_songBeginFmt % fname)
        secs = info.fs_durationInSeconds()
        if secs is not None:
            w.write(_mp_songDurationFmt % secs)
# TODO: write out a 'Time: nn' line here ???!!!???
# - where 'nn' is the track's length in seconds, I think? Maybe?
# - can we determine this without generating the track file?
#   - flactracksfs should be able to put it in each track's tag
#   - and other filesystems could copy it too (though to what MP3
#     tag?), provided the track originates in a FLAC album file
        for tag in _mp_mpdDatabaseSongTags:
            val = info.fs_tagValue(tag)
            if val is not None:
                name = _mp_tagNameToMpdDatabaseName.get(tag)
                if name is not None:
                    w.write("%s: %s\n" % (name, val))
        w.write(_mp_songMtimeFmt % info.fs_lastModifiedTime())
        w.write(_mp_songEndFmt)

    def _writeDirectoryEnd(self, w, relPath, info):
        assert w is not None
        assert relPath is not None
        assert info is not None
        w.write(_mp_dirEndFmt % relPath)

    def _writeEpilogue(self, w):
        assert w is not None
        pass  # currently no footer to add to db file



class mp_MpdInformationDisplayProcess(ut.ut_AbstractCommandFifoDaemonProcess):
    """
    Represents processes that display information from the currently selected
    MPD server on the screen.

    The display of information can be modified by sending the following
    commands to an instance's command FIFO:

        show

            Causes information to be displayed if it isn't already

        hide

            Causes information to be hidden (that is, not displayed) if
            it isn't already.

        toggle

            Causes information to be displayed if it's currently being
            hidden, and to be hidden if it's currently being displayed.

        refresh

            Causes the information that is displayed to be refreshed/updated.
    """

    def __init__(self, fifoPathname, pidFile = None, doDebug = False):
        """
        Initializes us with the pathname of our command FIFO and the pathname
        of our PID file.

        Note: our information will be hidden initially.

        See ut_AbstractCommandFifoDaemonProcess.__init__().
        """
        assert fifoPathname is not None
        # 'pidFile' may be None
        self._mp_showPid = None
        p = os.path.join(_conf.systemDir, _mp_displayInformationFilename)
        self._mp_infoPathname = p
        ut.ut_deleteFileOrDirectory(p)  # start hidden
        ut.ut_AbstractCommandFifoDaemonProcess. \
            __init__(self, fifoPathname, pidFile, doDebug)
        assert self._mp_isHidden()

    def _ut_processCommand(self, cmd):
        """
        Processes the ratings change command 'cmd'.

        See our class' comment for the syntax of all of the valid commands.
        """
        #self._ut_debug("---> in mp_MpdInformationDisplayProcess._ut_processCommand(%s)" % cmd)
        parts = cmd.split(None, 1)
        numParts = len(parts)
        assert numParts <= 2
        if numParts == 2:
            (cmdStart, rest) = parts
        elif numParts == 1:
            (cmdStart, rest) = (parts[0], "")
        if numParts > 0:  # ignore blank/empty commands
            assert cmdStart
            if cmdStart == _mp_showInfoCommand:
                self._mp_processShowCommand(cmdStart, rest, cmd)
            elif cmdStart == _mp_hideInfoCommand:
                self._mp_processHideCommand(cmdStart, rest, cmd)
            elif cmdStart == _mp_toggleInfoCommand:
                self._mp_processToggleCommand(cmdStart, rest, cmd)
            elif cmdStart == _mp_refreshInfoCommand:
                self._mp_processRefreshCommand(cmdStart, rest, cmd)
            else:
                self._ut_reportError("The command '%s' is invalid: its "
                    "first word isn't the start of a recognized command" %
                    cmd)

    def _mp_processShowCommand(self, cmdStart, args, cmd):
        """
        Processes the "show ..." command whose first word is 'cmdStart'
        and the rest of which is in the string 'args'.

        'cmd' is the command that 'cmdStart' and 'args' are parts of: 'cmd'
        is only used in error messages.
        """
        assert cmdStart == _mp_showInfoCommand
        assert args is not None  # though it may be empty
        assert cmd
        if args:
            self._ut_reportTooManyCommandArguments(cmd)
        elif self._mp_isHidden():
            self._mp_showInformation()

    def _mp_processHideCommand(self, cmdStart, args, cmd):
        """
        Processes the "hide ..." command whose first word is 'cmdStart'
        and the rest of which is in the string 'args'.

        'cmd' is the command that 'cmdStart' and 'args' are parts of: 'cmd'
        is only used in error messages.
        """
        assert cmdStart == _mp_hideInfoCommand
        assert args is not None  # though it may be empty
        assert cmd
        if args:
            self._ut_reportTooManyCommandArguments(cmd)
        elif not self._mp_isHidden():
            self._mp_hideInformation()

    def _mp_processToggleCommand(self, cmdStart, args, cmd):
        """
        Processes the "toggle ..." command whose first word is 'cmdStart'
        and the rest of which is in the string 'args'.

        'cmd' is the command that 'cmdStart' and 'args' are parts of: 'cmd'
        is only used in error messages.
        """
        #self._ut_debug("---> in _mp_processToggleCommand(%s, %s, %s)" % (cmdStart, args, cmd))
        assert cmdStart == _mp_toggleInfoCommand
        assert args is not None  # though it may be empty
        assert cmd
        if args:
            self._ut_reportTooManyCommandArguments(cmd)
        else:
            if self._mp_isHidden():
                self._mp_showInformation()
            else:
                self._mp_hideInformation()

    def _mp_processRefreshCommand(self, cmdStart, args, cmd):
        """
        Processes the "refresh ..." command whose first word is 'cmdStart'
        and the rest of which is in the string 'args'.

        'cmd' is the command that 'cmdStart' and 'args' are parts of: 'cmd'
        is only used in error messages.
        """
        assert cmdStart == _mp_refreshInfoCommand
        assert args is not None  # though it may be empty
        assert cmd
        if args:
            self._ut_reportTooManyCommandArguments(cmd)
        else:
            self._mp_refreshInformation()

    def _ut_afterRunning(self):
        if not self._mp_isHidden():
            self._mp_hideInformation()
        assert self._mp_isHidden()


    def _mp_showInformation(self):
        """
        Causes us to show our information on the screen.
        """
        assert self._mp_isHidden()
        p = self._mp_infoPathname
        self._mp_createInfoFile(p)

        prog = _conf.mpdDisplayInformationProgram
        args = _conf.mpdDisplayInformationProgramArguments
        if args is None:
            args = []
        allArgs = [prog]
        allArgs.extend(args)
        allArgs.append(p)
        #self._ut_debug("    prog = '%s', allArgs = %s" % (prog, str(allArgs)))
        self._mp_showPid = os.spawnvp(os.P_NOWAIT, prog, allArgs)
        assert not self._mp_isHidden()

    def _mp_hideInformation(self):
        """
        Causes us to hide our information so that it doesn't appear on the
        screen.
        """
        assert not self._mp_isHidden()
        pid = self._mp_showPid
        ut.ut_tryToKill(pid)
        self._mp_showPid = None
        os.waitpid(pid, 0)  # so the process doesn't stay a zombie
        assert self._mp_isHidden()

    def _mp_refreshInformation(self):
        """
        Causes our information to be refreshed/updated.
        """
        # We only do something here if we're currently showing the info,
        # since if it's hidden it'll be refreshed again just before it's
        # next shown.
        if not self._mp_isHidden():
            self._mp_hideInformation()
            self._mp_showInformation()

    def _mp_isHidden(self):
        """
        Returns True iff our information is currently hidden.
        """
        return (self._mp_showPid is None)

    def _mp_createInfoFile(self, path):
        """
        Creates (or replaces) the file with pathname 'path' that is to
        contain the information that we are to display.
        """
        assert path is not None
        w = None
        try:
            w = open(path, 'w')
            s = mp_Mpd()  # the currently selected server
            title = s.trackTitle()
            if title is not None:
                fmt = '%s - %s\nfrom "%s" (%s)\n[#%s/%s]  rating: %s' + \
                        '  (%s/%s)\n'
                w.write(fmt % (title,
                    self._mp_unknownIfNone(s.artist()),
                    self._mp_unknownIfNone(s.albumTitle()),
                    self._mp_unknownIfNone(s.releaseDate()),
                    self._mp_unknownIfNone(s.currentTrackPosition()),
                    self._mp_unknownIfNone(s.trackCount()),
                    self._mp_unknownIfNone(s.rating()),
                    self._mp_unknownIfNone(s.currentTrackElapsedTime()),
                    self._mp_unknownIfNone(s.currentTrackTotalTime())))
            else:
                w.write("[no current track]\n")
        finally:
            ut.ut_tryToCloseAll(w)

    def _mp_unknownIfNone(self, str):
        """
        Returns 'str' unless it's None, in which case "[unknown]" is
        returned.
        """
        result = str
        if result is None:
            result = "[unknown]"
        assert result is not None
        return result


class mp_AbstractMpdProgram(ut.ut_AbstractProgram):
    """
    An abstract base class for classes that interact with one or more MPD
    servers.
    """

    def _smartMatchMpdServerIds(self, k):
        """
        Smart matches 'k' against all of the MPD server IDs, returning an
        (id, desc) pair if 'k' matches the ID of exactly one server, and a
        pair (None, msg) otherwise, where 'msg' is a message that can be
        passed to _fail().
        """
        matches = _conf.smartMatchMpdServerIds(k)
        numMatches = len(matches)
        if numMatches == 1:
            result = matches[0]
        else:
            if numMatches == 0:
                msg = "There's no MPD server whose ID matches '%s'" % k
            else:
                assert numMatches > 1
                ids = ", ".join([m[0] for m in matches])
                msg = "More than one MPD server's ID matches '%s'. " \
                    "It matches all of\nthe following IDs equally " \
                    "well: %s" % (k, ids)
            result = (None, msg)
        assert result is not None
        assert len(result) == 2
        return result

class mp_AbstractIncludeTracksProgram(mp_AbstractMpdProgram):
    """
    An abstract base class for classes that include new tracks into an
    MPD server's playlist.
    """

    selectServerOption = "-s"

    def _shortOptions(self):
        result = "s:"
        assert result is not None
        return result

    def _buildInitialArgumentsMap(self):
        result = { "server": None, "paths": None }
        assert result is not None
        return result

    def _processOption(self, opt, val, argsMap):
        assert opt
        # 'val' may be None
        assert argsMap is not None
        result = True
        if opt == self.selectServerOption:
            (id, desc) = self._smartMatchMpdServerIds(val)
            if id is not None:
                argsMap["server"] = mp_createMpdServerFromDescription(desc)
            else:
                result = False
                self._fail(desc)
        else:
            result = self._handleUnknownOption(opt)
        return result

    def _processNonOptionArguments(self, args, argsMap):
        assert args is not None
        assert argsMap is not None
        result = True
        if args:
            argsMap["paths"] = args
        else:
            result = False
        return result

    def _execute(self, argsMap):
        assert argsMap is not None
        result = 0
        s = argsMap["server"]
        if s is None:
            s = mp_Mpd()  # the currently selected server
        self._includeTracks(s, argsMap["paths"])
        assert result >= 0
        return result

    def _includeTracks(self, server, paths):
        """
        Includes the tracks whose pathnames are in 'paths' in the playlist
        of the MPD server 'server'.
        """
        assert server is not None
        assert paths is not None
        raise NotImplementedError


class mp_AbstractChangeRatingProgram(ut.ut_AbstractProgram):
    """
    An abstract base class for classes that represent programs that change
    the ratings of an MPD server's tracks.
    """

    def __init__(self):
        ut.ut_AbstractProgram.__init__(self)
        self._amount = None

    def _usageMessage(self, progName, shortHelpOpts, longHelpOpts,
                      helpOptionsDesc):
        if self._amount is None:
            self._amount = self. \
                _parseAmountFromName(self._operatorCharacter(),
                                     self._defaultRatingChangeAmount())
        assert self._amount is not None
        amt = self._amount
        base = _conf.mainRatingsBasename
        rootDir = _conf.rootDir
        mainDesc = self._mainUsageDescription(amt, base, rootDir)
        result = """
usage: %(progName)s %(shortHelpOpts)s %(longHelpOpts)s [-r base] [-a amt] [file]
%(mainDesc)s
%(helpOptionsDesc)s
If the optional '-a' option is specified then the file's
rating is %(action)s 'amt', not %(amount)i.

If the optional '-r' option is specified then the file's
rating in the ratings with base name 'base' is changed
instead of its rating in the '%(base)s' ratings.

If 'file' isn't specified then the pathname of the currently
selected MPD server's current track is used, if it has one;
otherwise no file's rating is changed.
""" % { "progName": progName, "amount": amt, "mainDesc": mainDesc,
        "action": self._actionDescription(),
        "rootDir": rootDir, "base": base,
        "shortHelpOpts": shortHelpOpts, "longHelpOpts": longHelpOpts,
        "helpOptionsDesc": helpOptionsDesc }
        assert result
        return result

    def _shortOptions(self):
        result = "r:a:"
        assert result is not None
        return result

    def _buildInitialArgumentsMap(self):
        # Note: we intentionally omit "amount" from the initial map.
        result = { "base": None,
                   "path": None }
        assert result is not None
        return result

    def _processOption(self, opt, val, argsMap):
        assert opt
        # 'val' may be None
        assert argsMap is not None
        result = True
        if opt == "-r":
            argsMap["base"] = val
        elif opt == "-a":
            result = True
            try:
                argsMap["amount"] = ut.ut_parseInt(val, minValue = 0)
            except ValueError, ex:
                result = False
                self._fail("Invalid amount: '%s'" % amt)
        else:
            result = self._handleUnknownOption(opt)
        return result

    def _processNonOptionArguments(self, args, argsMap):
        assert args is not None
        assert argsMap is not None
        result = True
        if self._amount is None:
            self._amount = \
                self._parseAmountFromName(self._operatorCharacter(),
                                          self._defaultRatingChangeAmount())
        if result:
            numArgs = len(args)
            if numArgs > 1:
                result = False
                self._fail("Too many arguments")
            elif numArgs == 1:
                argsMap["path"] = args[0]
        return result

    def _execute(self, argsMap):
        assert argsMap is not None
        result = 0
        amt = self._ratingChangeAmount(argsMap)
        base = argsMap["base"]
        path = argsMap["path"]
        self._changeRating(mp_Mpd(), amt, base, path)
        assert result >= 0
        return result

    def _parseAmountFromName(self, op, default):
        """
        Parses our basename and returns the amount that it specifies, or
        'default' if it doesn't specify an amount.

        The amount specified by a program's basename is that name with all of
        the 'op' characters removed from the start of it, converted to an
        int. The 'default' is returned iff the basename doesn't represent an
        int after removing all of the 'op' characters from its start.
        """
        assert len(op) == 1
        assert default >= 0
        val = self._basename().lstrip(op)
        result = ut.ut_tryToParseInt(val, default, minValue = 0)
        assert result >= 0
        return result

    def _ratingChangeAmount(self, argsMap):
        """
        Returns the amount to use in changing a track's rating, where
        'argsMap' is our arguments map.

        See ut_AbstractProgram._execute().
        """
        assert argsMap is not None
        result = argsMap.get("amount", self._amount)
        if result is None:
            result = self._defaultRatingChangeAmount()
        assert result >= 0
        return result


    def _mainUsageDescription(self, amount, base, rootDir):
        """
        Returns the main paragraph describing this program as part of our
        usage message, where 'amount' is the amount we use in determining
        how much we change ratings by, 'base' is the default ratings basename
        and 'rootDir' is the pathname of the root directory.
        """
        assert amount >= 0
        assert base is not None
        assert rootDir is not None
        #assert result
        raise NotImplementedError

    def _actionDescription(self):
        """
        Returns a description of the action that we perform on a file, for
        use in our usage message.
        """
        #assert result is not None
        raise NotImplementedError

    def _operatorCharacter(self):
        """
        Returns the operator character removed from the start of this
        program's basename when parsing it in order to determine how much
        it should change a track's rating by.
        """
        #assert len(result) == 1
        raise NotImplementedError

    def _defaultRatingChangeAmount(self):
        """
        Returns the amount by which this program change's a track's rating
        by default: that is, when the amount can't be determined some other
        way.
        """
        #assert result >= 0
        raise NotImplementedError

    def _changeRating(self, server, amount, base, path):
        """
        Changes the rating for the audio file with pathname 'path' in the
        ratings file with base ratings name 'base' using the amount 'amount'
        and the MPD server 'server' (which is an mp_Mpd object).
        """
        assert server is not None
        assert amount >= 0
        # 'base' may be None (indicating the main ratings basename)
        # 'path' may be None (indicating the pathname of the current track)
        raise NotImplementedError


class mp_PlaylistSnapshot(object):
    """
    Represents the contents of an MPD server's playlist at a single point
    in time.
    """

    def __init__(self, pathnames, currentIndex):
        """
        Intializes us with the list 'pathnames' of all of the audio files
        in the MPD server's playlist, in order, and the 0-based index
        'currentIndex' of the file in the playlist that is the current
        file (or -1 if no item in the playlist was selected as the current
        one).

        All of the pathnames in 'pathnames' are assumed to be relative to
        their MPD server's root music directory.

        See config.conf_Configuration.rootDir
        """
        assert pathnames is not None
        #assert "no item in 'pathnames' is None"
        assert currentIndex >= -1
        assert currentIndex < len(pathnames)
        self._mp_pathnames = pathnames
        self._mp_currentItemIndex = currentIndex

    def allPathnames(self):
        """
        Returns a list of the pathnames of all of the files in this snapshot
        of a playlist.

        All of the pathnames in the result are relative to the root music
        directory of the MPD server whose playlist this is a snapshot of.

        See config.conf_Configuration.rootDir
        """
        #assert self._mp_pathnames is not None
        return self._mp_pathnames

    def pathname(self, index):
        """
        Returns the pathname of the ('index'+1)th file in this snapshot of a
        playlist. An IndexError is raised if there's no ('index'+1)th file
        in this snapshot.
        """
        result = self._mp_pathnames[index]
        assert result is not None
        return result

    def currentItemPathname(self):
        """
        Returns the pathname of the current file in this snapshot of a
        playlist, or None if no file was selected as the current one.
        """
        index = self.currentItemIndex()
        if index >= 0:
            result = self._mp_pathnames[index]
        else:
            result = None
        # 'result' may be None
        return result

    def currentItemIndex(self, defaultValue = -1):
        """
        Returns the 0-based index of the current file in this snapshot of a
        playlist, or 'defaultValue' if no file was selected as the current
        one.
        """
        result = self._mp_currentItemIndex
        if result < 0:
            result = defaultValue
        #debug("result = %i, defaultValue = %i" % (result, defaultValue))
        assert result >= 0 or result == defaultValue
        #assert result < len(self.allPathnames()) or result == defaultValue
        return result

    def __str__(self):
        sz = len(self._mp_pathnames)
        currInd = self.currentItemIndex()
        result = "playlist with %i items (curr ind = %i):\n" % (sz, currInd)
        for i in xrange(sz):
            if i == currInd:
                result += " > "
            else:
                result += "   "
            result += str(self.pathname(i)) + "\n"
        assert result is not None
        return result

class mp_Mpd(object):
    """
    Represents an MPD server.
    """

    def __init__(self, host = None, port = None):
        """
        Initializes this mp_Mpd object with the hostname and port of the
        MPD server that it represents, or to those of the currently selected
        MPD server if both 'host' and 'port' are None.
        """
        #debug("---> in mp_Mpd.__init__(%s, %s)" % (host, str(port)))
        assert (host is None) == (port is None)
        assert host is None or host  # non-empty
        assert port is None or port >= 0
        object.__init__(self)
        if host is None:
            #debug("    setting host/port to that of selected MPD server")
            (host, port) = _conf.selectedMpdServer()
        #debug("    host = [%s], port = [%s]" % (host, str(port)))
        assert host
        assert port >= 0
        self._mp_host = host
        self._mp_port = port

    def __str__(self):
        result = "%s:%i (version=%s)" % (self._mp_host, self._mp_port,
                                         self.version())
        assert result is not None
        return result

    def isSelectedServer(self):
        """
        Returns True iff we represent the currently selected MPD server.
        """
        (h, p) = _conf.selectedMpdServer()
        return (self._mp_host == h) and (self._mp_port == p)

    def makeSelectedServer(self):
        """
        Makes this server the currently selected MPD server, if it isn't
        already. Returns True if we weren't the currently selected server,
        and False if it was already the currently selected server.

        An IOError is raised iff we fail to make this server the selected
        server.
        """
        result = not self.isSelectedServer()
        if result:
            _conf.setSelectedMpdServer(self._mp_host, self._mp_port)
        return result


    def currentTrackIndex(self):
        """
        Returns the 0-based index of our current track, or -1 if we don't
        currently have a current track.
        """
        cmdArgs = '--format "%position%" current'
        output = self.executeMpcCommand(cmdArgs).strip()
        if not output:
            result = -1
        else:
            result = int(output) - 1
            assert result >= 0
        assert result >= -1
        return result

    def currentTrackPathname(self):
        """
        Returns the pathname of the current track, or None if there is no
        track that is paused or playing.

        The returned pathname will be relative to the root music directory.
        """
        result = self.currentTrackIndex()
        if result == 0:
            result = None
        assert (result is None) or (result > 0)
        return result

    def currentTrackPosition(self):
        """
        Returns the 1-based position of the current track in the list of all
        of the tracks in the current playlist, or returns 0 if there is no
        current track.

        Note: a track's position and its track number are two different
        things, and are rarely the same.

        See trackNumber().
        """
        result = 0
        line = self._mp_mpcStatusInformationLine(1)
        if line:
            words = line.split()
            if len(words) > 1:
                parts = words[1].split('/')
                if parts:
                    strNum = parts[0].lstrip('#')
                    result = ut.ut_tryToParseInt(strNum, 0, minValue = 1)
        assert result >= 0
        return result

    def currentTrackElapsedTime(self):
        """
        Returns a string representation (of the form 'mm:ss') of the amount
        of time in the current track that has already been played, or None
        if there's no current track.
        """
        result = None
        line = self._mp_mpcStatusInformationLine(1)
        if line:
            words = line.split()
            if len(words) > 2:
                parts = words[2].split('/')
                if parts:
                    result = parts[0]
                    assert result is not None
        # 'result' may be None
        return result

    def currentTrackTotalTime(self):
        """
        Returns a string representation (of the form 'mm:ss') of the total
        duration/time of the current track, or None if there's no current
        track.
        """
        result = None
        line = self._mp_mpcStatusInformationLine(1)
        if line:
            words = line.split()
            if len(words) > 2:
                parts = words[2].split('/')
                if parts:
                    result = parts[1]
                    assert result is not None
        # 'result' may be None
        return result


    def trackCount(self):
        """
        Returns the total number of tracks currently in our MPD server's
        playlist, or returns None if that information can't be obtained.
        """
        data = self.executeMpcCommand("playlist")
        if data is None:
            result = None
        else:
            result = len(data.splitlines())
        assert result is None or result >= 0
        return result

    def _mp_mpcStatusInformationLine(self, lineIndex):
        """
        Returns the ('lineIndex' + 1)th line of the status information
        returned by _mp_mpcStatusInformation(), or returns None if it
        can't be obtained or there isn't any such line in the status
        information.

        See _mp_mpcStatusInformation().
        """
        assert lineIndex >= 0
        result = None
        data = self._mp_mpcStatusInformation()
        if data:
            lines = data.splitlines()
            if len(lines) > lineIndex:
                result = lines[lineIndex]
                assert result is not None
        # 'result' may be None
        return result

    def _mp_mpcStatusInformation(self, fmt = None):
        """
        Returns a string containing status information obtained using the
        mpc command, or returns None if it can't be obtained.

        If 'fmt' isn't None then it's passed as the '--format' option's
        argument in the mpc command used to get the status information.

        See _mp_mpcStatusInformationLine().
        """
        #debug("---> in _mp_mpcStatusInformationLine(%s)" % fmt)
        # 'fmt' may be None
        args = "volume +0"
        if fmt is not None:
            args = "--format '%s' %s" % (fmt, args)
        result = self.executeMpcCommand(args)
        # 'result' may be None
        return result


    def trackNumber(self, path = None):
        """
        Returns the track number of the track with pathname 'path' (or of the
        current track if 'path' is None), or returns None if the track number
        can't be obtained (including if 'path' is None and there's no current
        track).

        'path' is assumed to be relative to the root music directory.

        Note: a track's position and its track number are two different
        things, and are rarely the same.

        See currentTrackPosition().
        See musicfs.fs_MusicMetadataManager.fs_trackNumber().
        """
        result = None
        if path is None:
            path = self.currentTrackPathname()
        if path is not None:
            mm = musicfs.fs_MusicMetadataManager()
            result = mm.fs_trackNumber(path)
        # 'result' may be None
        return result

    def trackTitle(self, path = None):
        """
        Returns the title of the track with pathname 'path' (or of the
        current track if 'path' is None), or returns None if the title can't
        be obtained (including if 'path' is None and there's no current
        track).

        'path' is assumed to be relative to the root music directory.
        """
        result = None
        if path is None:
            path = self.currentTrackPathname()
        if path is not None:
            mm = musicfs.fs_MusicMetadataManager()
            result = mm.fs_title(path)
        # 'result' may be None
        return result

    def artist(self, path = None):
        """
        Returns the artist for the track with pathname 'path' (or for the
        current track if 'path' is None), or returns None if the artist can't
        be obtained (including if 'path' is None and there's no current
        track).

        'path' is assumed to be relative to the root music directory.
        """
        result = None
        if path is None:
            path = self.currentTrackPathname()
        if path is not None:
            mm = musicfs.fs_MusicMetadataManager()
            result = mm.fs_artist(path)
        # 'result' may be None
        return result

    def albumTitle(self, path = None):
        """
        Returns the title of the album containing the track with pathname
        'path' (or of the current track if 'path' is None), or returns None
        if the title can't be obtained (including if 'path' is None and
        there's no current track).

        'path' is assumed to be relative to the root music directory.
        """
        result = None
        if path is None:
            path = self.currentTrackPathname()
        if path is not None:
            mm = musicfs.fs_MusicMetadataManager()
            result = mm.fs_albumTitle(path)
        # 'result' may be None
        return result

    def genre(self, path = None):
        """
        Returns the genre of the track with pathname 'path' (or of the
        current track if 'path' is None), or returns None if the genre can't
        be obtained (including if 'path' is None and there's no current
        track).

        'path' is assumed to be relative to the root music directory.
        """
        result = None
        if path is None:
            path = self.currentTrackPathname()
        if path is not None:
            mm = musicfs.fs_MusicMetadataManager()
            result = mm.fs_genre(path)
        # 'result' may be None
        return result

    def releaseDate(self, path = None):
        """
        Returns the release date of the track with pathname 'path' (or of the
        current track if 'path' is None), or returns None if the release date
        can't be obtained (including if 'path' is None and there's no current
        track).

        'path' is assumed to be relative to the root music directory.
        """
        result = None
        if path is None:
            path = self.currentTrackPathname()
        if path is not None:
            mm = musicfs.fs_MusicMetadataManager()
            result = mm.fs_releaseDate(path)
        # 'result' may be None
        return result

    def comment(self, path = None):
        """
        Returns the comment associated with the track with pathname 'path'
        (or with the current track if 'path' is None), or returns None if the
        comment can't be obtained (including if 'path' is None and there's no
        current track).

        'path' is assumed to be relative to the root music directory.
        """
        result = None
        if path is None:
            path = self.currentTrackPathname()
        if path is not None:
            mm = musicfs.fs_MusicMetadataManager()
            result = mm.fs_comment(path)
        # 'result' may be None
        return result


    def showCurrentTrackInformation(self):
        """
        Causes information about the default MPD server's current track to be
        shown on the screen.
        """
        self._mp_sendDisplayInformationCommand(_mp_showInfoCommand)

    def hideCurrentTrackInformation(self):
        """
        Causes information about the default MPD server's current track to be
        hidden: that is, to not be shown on the screen.
        """
        self._mp_sendDisplayInformationCommand(_mp_hideInfoCommand)

    def toggleShowingCurrentTrackInformation(self):
        """
        Causes information about the default MPD server's current track to be
        shown if it's currently hidden, or hidden if it's currently being
        shown.
        """
        self._mp_sendDisplayInformationCommand(_mp_toggleInfoCommand)

    def refreshShownCurrentTrackInformation(self):
        """
        Refreshes the information shown about the default MPD server's
        current track (assuming the information's currently being shown).
        """
        self._mp_sendDisplayInformationCommand(_mp_refreshInfoCommand)

    def _mp_sendDisplayInformationCommand(self, cmd):
        """
        Sends the command 'cmd' to the MPD current track information display
        daemon for the default MPD server, returning True iff the command is
        successfully sent.
        """
        assert cmd
        sink = mp_displayInformationCommandSink()
        return ut.ut_sendCommandToFifo(cmd, sink)


    def add(self, paths):
        """
        Adds the music files whose pathnames are in 'paths' to the end of our
        playlist, in order, returning True iff all of the files are
        successfully added.

        Note: once enqueuing one file fails no attempt is made to enqueue
        any of the subsequent files.
        """
        assert paths is not None
        return self._mp_add(paths, False)

    def addAndPreload(self, paths):
        """
        The same as add(), except that an attempt is made to preload the
        music files so that they'll (hopefully) be in music filesystems'
        caches.

        Note: files that are not successfully added are not preloaded.
        """
        #debug("---> addAndPreload(%s)" % ", ".join(paths))
        assert paths is not None
        return self._mp_add(paths, True)

    def insert(self, paths, startPos = 0):
        """
        Inserts the music files whose pathnames are in 'paths' into our
        playlist, in order and such that they immediately follow the track
        that was initially the 'startPos''th track, returning True iff all of
        the files are successfully inserted.

        Note: if 'startPos' is 0 then the tracks are inserted so that they'll
        be the first tracks in our playlist.
        """
        assert paths is not None
        assert startPos >= 0
        return self._mp_insert(paths, startPos, False)

    def insertAndPreload(self, paths, startPos = 0):
        """
        The same as insert(), except that an attempt is made to preload the
        music files so that they'll (hopefully) be in music filesystems'
        caches.

        Note: files that are not successfully added are not preloaded.
        """
        #debug("---> insertAndPreload(%i, %s)" % (startPos, ", ".join(paths)))
        assert paths is not None
        assert startPos >= 0
        return self._mp_insert(paths, startPos, True)

    def request(self, paths):
        """
        Requests the music files whose pathnames are in 'paths' by inserting
        them into our playlist immediately after the current track (or at the
        start of our playlist if we have no current track): thus the
        requested tracks will be played immediately after the current track
        is done.
        """
        assert paths is not None
        # If we don't have a current track then currentTrackPosition() will
        # return 0, which will cause the requested tracks to be inserted at
        # the start of our playlist.
        self.insert(paths, self.currentTrackPosition())

    def requestAndPreload(self, paths):
        """
        The same as request(), except that an attempt is made to preload the
        music files so that they'll (hopefully) be in music filesystems'
        caches.

        Note: files that are not successfully added are not preloaded.
        """
        #debug("---> requestAndPreload(%s)" % ", ".join(paths))
        assert paths is not None
        # If we don't have a current track then currentTrackPosition() will
        # return 0, which will cause the requested tracks to be inserted at
        # the start of our playlist.
        self.insertAndPreload(paths, self.currentTrackPosition())

    def _mp_add(self, paths, doPreload):
        """
        Adds the music files whose pathnames are in 'paths' to the end of our
        playlist, in order, returning True iff all of the files are
        successfully added.

        If 'doPreload' is True then an attempt is made to preload the music
        files that are to be added so that they'll (heopfully) be in music
        filesystems' caches.

        Note: once enqueuing one file fails no attempt is made to enqueue
        any of the subsequent files.
        """
        #debug("---> _mp_add(%s)" % ", ".join(paths))
        assert paths is not None
        result = True
        if paths:
            #debug("    are paths")
            filePaths = [f for f in mp_toMpdMusicFilePathnames(paths)]
            #debug("    # filePaths = %i" % len(filePaths))
            if doPreload:
                #debug("    preloading files")
                self._mp_preload(filePaths)
            for p in filePaths:
                assert p is not None
                #debug("    adding file [%s]" % p)
                result = self._mp_addFile(p)
                if not result:
                    #debug("    adding file failed")
                    break  # for loop
        #debug("    all files added? %s" % result)
        return result

    def _mp_insert(self, paths, startPos, doPreload):
        """
        Inserts the music files whose pathnames are in 'paths' into our
        playlist, in order and such that they immediately follow the track
        that was initially the 'startPos''th track, returning True iff all of
        the files are successfully inserted.

        If 'doPreload' is True then an attempt is made to preload the music
        files that are to be inserted so that they'll (heopfully) be in music
        filesystems' caches.

        Note: if 'startPos' is 0 then the tracks are inserted so that they'll
        be the first tracks in our playlist.
        """
        assert paths is not None
        assert startPos >= 0
        result = True
        if paths:
            # Since mpd doesn't have a way to insert tracks we add them to
            # the end of the playlist ...
            oldCount = self.trackCount()
            filePaths = [f for f in mp_toMpdMusicFilePathnames(paths)]
            if doPreload:
                self._mp_preload(filePaths)
            for p in filePaths:
                assert p is not None
                result = self._mp_addFile(p)
                if not result:
                    break  # for loop

            # ... then move the added tracks to their new positions.
            newCount = self.trackCount()
            currPos = oldCount + 1
            newPos = startPos + 1
            while currPos <= newCount:
                # mpc move currPos newPos
                self.executeMpcCommand("move %i %i" % (currPos, newPos))
                currPos += 1
                newPos += 1
        return result

    def _mp_preload(self, paths):
        """
        Preloads the music files whose pathnames are in 'paths'.

        At least currently all of the music files will be added in the
        background.
        """
        #debug("---> _mp_preload(%s)" % ", ".join(paths))
        if paths:
            d = _mp_mpdMusicDirectory
            join = os.path.join
            #debug("    music dir = [%s]" % d)
            ut.ut_preloadFilesInBackground([join(d, p) for p in paths])


    def removeFirstTracks(self, n = 1):
        """
        Removes the first 'n' tracks from our playlist, returning True iff
        they're all successfully removed.
        """
        assert n > 0
        result = True
        for i in xrange(n):
            wasRemoved = self.doesMpcCommandSucceed("del 1")
            if not wasRemoved:
                result = False
        return result

    def crop(self):
        """
        Removes all of the songs from our playlist except the current one,
        returning True iff they're all successfully removed.
        """
        return self.doesMpcCommandSucceed("crop")

    def clear(self):
        """
        Removes all of the songs from our playlist (including the current
        one), returning True iff they're all successfully removed.
        """
        return self.doesMpcCommandSucceed("clear")


# Note: this is a seriously bad idea since it'll cause the music filesystems
# to actually create all of their music files. Use createDatabaseFile()
# instead, which - though it takes a few minutes to run - uses the filesystems'
# metadata.
#
#    def update(self, paths = None):
#        """
#        Scans everything under our base music directory for updates if
#        'paths' is None, and only scans (everything under?) the paths in
#        'paths' otherwise. Returns True iff the scanning is completed
#        successfully.
#        """
#        args = "update"
#        if paths is not None:
#            c = [("'%s'" % mp_toMpdPathname(p)) for p in paths]
#            args = "%s %s" % (args, " ".join(c))
#        return self.doesMpcCommandSucceed(args)


    def playOrPause(self):
        """
        If stopped starts playing; if playing pauses. Returns True iff we
        successfully switch to playing or pausing.
        """
        return self.doesMpcCommandSucceed("toggle")

    def pause(self):
        """
        Pauses the playing of the current song, returning True iff it is
        successfully paused.

        Note: this also will succeed if we're already paused.
        """
        return self.doesMpcCommandSucceed("pause")

    def next(self):
        """
        Starts playing the next song in our playlist after the current one,
        returning True iff the next song successfully starts playing.
        """
        return self.doesMpcCommandSucceed("next")

    def previous(self):
        """
        Starts playing the previous song in our playlist before the current
        one, returning True iff the next song successfully starts playing.
        """
        return self.doesMpcCommandSucceed("prev")


    def volume(self):
        """
        Returns our current volume level.
        """
        result = self.executeMpcCommand("volume").strip()
        result = int(result[8:-1])
            # removes the 'volume: ' prefix and the '%' suffix
        assert result >= 0
        assert result <= 100
        return result

    def setVolume(self, newValue):
        """
        Sets our volume to 'newValue', returning True iff it is successfully
        set.
        """
        assert newValue >= 0
        assert newValue <= 100
        return self.doesMpcCommandSucceed("volume %i" % newValue)

    def adjustVolume(self, adj):
        """
        Adjusts our volume by 'adj' (increasing it if 'adj' is positive and
        decreasing it if 'adj' is negative), returning True iff it is
        successfully adjusted.

        Note: our volume cannot be adjusted to be less than 0 or greater than
        100: specifying a value of 'adj' that would do so will instead adjust
        our volume to 0 or 100, as appropriate.
        """
        assert adj >= -100
        assert adj <= 100
        return self.doesMpcCommandSucceed("volume %+i" % adj)


    def playlistSnapshot(self):
        """
        Returns an mp_PlaylistSnapshot that represents the current state of
        this server's current playlist, or returns None if the server doesn't
        have a current playlist.
        """
        result = None
        cmdArgs = '--format "%file%" playlist'
        output = self.executeMpcCommand(cmdArgs)
        if output is not None:
            sep = " "
            paths = []
            for line in output.splitlines():
                line = line.strip()  # removes leading space if it has one
                if line.find(sep) < 0:
                    # Assume it's the output of the new (version 0.22, or
                    # maybe earlier?) mpc command.
                    path = line
                else:
                    # Assume it's the output of an old (version 0.15, or
                    # maybe later?) mpc command.
                    (num, foundSep, path) = line.partition(sep)
                    assert foundSep == sep
                    assert path
                        # otherwise partition() failed to find 'sep'
                paths.append(path)
            result = mp_PlaylistSnapshot(paths, self.currentTrackIndex())
        # 'result' can be None
        return result

    def doesMpcCommandSucceed(self, cmdArgs):
        """
        Executes the 'mpc' program with arguments in the string 'cmdArgs'
        to interact with our MPD server, returning True iff the command
        succeeds. (Any command output is lost.)

        Note: 'cmdArgs' is a string, not a list.

        See executeMpcCommand().
        """
        return (self.executeMpcCommand(cmdArgs) is not None)

    def executeMpcCommand(self, cmdArgs):
        """
        Executes the 'mpc' program with arguments in the string 'cmdArgs'
        to interact with our MPD server, returning the output if it's
        successful and None if executing the command failed.

        Note: 'cmdArgs' is a string, not a list.

        See doesMpcCommandSucceed().
        """
        #debug("---> in executeMpcCommand(%s)" % cmdArgs)
        start = _mp_mpcCommandStartFormat % (self._mp_host, self._mp_port)
        #debug("    start = [%s]" % start)
        cmd = "%s %s" % (start, cmdArgs)
        result = ut.ut_executeShellCommand(cmd)
        # 'result' may be None
        return result


    def rating(self, base = None, path = None):
        """
        Returns the rating for the audio file with pathname 'path' in the
        ratings file with base name 'base', or in the main ratings file if
        'base' is None. If 'path' is None then the rating for the current
        track will be returned if there is a current track, and None will be
        returned if there isn't a current track. None will also be returned
        if the track's rating can't be obtained.

        If 'subdir' is None then 'path' will be assumed to be relative to the
        base music directory. But if 'subdir' isn't None then 'path' will be
        assumed to be relative to the subdirectory 'subdir' of the root (NOT
        the base) music directory. So if 'subdir' is the empty path '' then
        'path' will be assumed to be relative to the root music directory.
        """
        # 'base' may be None
        # 'path' may be None
        if path is None:
            path = self.currentTrackPathname()
        result = None
        if path is not None:
            mm = musicfs.fs_MusicMetadataManager()
            result = mm.fs_rating(path, base, '')
        assert result is None or result >= 0
        assert result is None or result <= config.maxRating
        return result

    def increaseRating(self, amount, base = None, path = None):
        """
        Attempts to increase by 'amount' the rating for the audio file with
        pathname 'path' in the ratings file with base name 'base', or in the
        main ratings file if 'base' is None. If 'path' is None then the
        rating of the current track will be changed if there is a current
        track, and nothing will be done if there isn't a current track.

        Note: any attempt to increase the rating above the maximum rating
        will increase it to that maximum.

        See musicfs.fs_MusicMetadataManager.fs_increaseRating().
        """
        assert amount >= 0
        # 'base' may be None
        # 'path' may be None
        if path is None:
            path = self.currentTrackPathname()
        if path is not None:
            mm = musicfs.fs_MusicMetadataManager()
            #ut.ut_speak("Increase by %i" % amount)
            mm.fs_increaseRating(amount, path, base, "")
                # subdir is "" since 'path' is relative to the root dir
        # Otherwise we're to change the rating of the current track when
        # there isn't one, so we just do nothing.

    def decreaseRating(self, amount, base = None, path = None):
        """
        Attempts to decrease by 'amount' the rating for the audio file with
        pathname 'path' in the ratings file with base name 'base', or in the
        main ratings file if 'base' is None. If 'path' is None then the
        rating of the current track will be changed if there is a current
        track, and nothing will be done if there isn't a current track.

        Note: any attempt to decrease the rating below 1 will decrease it to
        1. (You can't decrease a rating to 0: you can only set it to 0.)

        See musicfs.fs_MusicMetadataManager.fs_decreaseRating().
        """
        assert amount >= 0
        # 'base' may be None
        # 'path' may be None
        if path is None:
            path = self.currentTrackPathname()
        if path is not None:
            mm = musicfs.fs_MusicMetadataManager()
            #ut.ut_speak("Decrease rating by %i" % amount)
            mm.fs_decreaseRating(amount, path, base, "")
                # subdir is "" since 'path' is relative to the root dir
        # Otherwise we're to change the rating of the current track when
        # there isn't one, so we just do nothing.

    def setRating(self, amount, base = None, path = None):
        """
        Attempts to set to 'amount' the rating for the audio file with
        pathname 'path' in the ratings file with base name 'base', or in the
        main ratings file if 'base' is None. If 'path' is None then the
        rating of the current track will be changed if there is a current
        track, and nothing will be done if there isn't a current track.

        Note: any attempt to set the rating to one above the maximum rating
        will set it to that maximum.

        See musicfs.fs_MusicMetadataManager.fs_setRating().
        """
        assert amount >= 0
        # 'base' may be None
        # 'path' may be None
        if path is None:
            path = self.currentTrackPathname()
        if path is not None:
            mm = musicfs.fs_MusicMetadataManager()
            #ut.ut_speak("Set to %i" % amount)
            mm.fs_setRating(amount, path, base, "")
                # subdir is "" since 'path' is relative to the root dir
        # Otherwise we're to change the rating of the current track when
        # there isn't one, so we just do nothing.


    def version(self):
        """
        Returns the version string identifying the version of this MPD
        server, or None if the version can't be determined.
        """
        cmd = "%s --version" % _mp_mpdExecutable
        result = None
        data = ut.ut_executeShellCommand(cmd)
        if data is not None:
            lines = data.splitlines()
            if len(lines) > 0:
                line = lines[0].strip()
                words = line.split(" ")
                if len(words) > 0:
                    result = words[-1].strip()
        return result

    def createDatabaseFile(self, path, catalogue = None):
        """
        Creates the database file for this MPD server in the file with
        pathname 'path', overwriting it if it already exists. The database
        is created from the contents of the music directory cataloged file
        with pathname 'catalogue', or the main music directory catalogue
        file if 'catalogue' is None.
        """
        if catalogue is None:
            catalogue = _conf.cataloguePathname
        version = self.version()
        if version.startswith("0.15."):
            builder = mp_Mpd0_15DatabaseBuilder(path, self)
        else:
            builder = mp_Mpd0_16DatabaseBuilder(path, self)
        builder.fs_parse(catalogue)


    def _mp_addFile(self, path):
        """
        Adds the one music file whose pathname is 'path', where 'path' is
        assumed to have been yielded by mp_toMpdMusicFilePathnames().

        Returns True iff the file is successfully added.
        """
        #debug("---> in _mp_addFile(%s)" % path)
        assert path is not None
        return self.doesMpcCommandSucceed("add '%s'" % path)


def main():
    server = mp_Mpd()
    unknown = "[unknown]"

    print
    print "MPD server version = '%s'" % server.version()

    print ""
    val = server.currentTrackPathname()
    if val is None:
        val = unknown
    print "current track pathname: %s" % val
    val = server.trackNumber()
    if val is None:
        val = unknown
    print "current track number: %s" % val
    val = server.trackTitle()
    if val is None:
        val = unknown
    print "              title: %s" % val
    val = server.artist()
    if val is None:
        val = unknown
    print "              artist: %s" % val
    val = server.albumTitle()
    if val is None:
        val = unknown
    print "              album: %s" % val
    val = server.genre()
    if val is None:
        val = unknown
    print "              genre: %s" % val
    val = server.releaseDate()
    if val is None:
        val = unknown
    print "              release date: %s" % val
    val = server.comment()
    if val is None:
        val = unknown
    print "              comment: %s" % val

    print
    val = server.currentTrackPosition()
    if val == 0:
        val = unknown
    print "current track position: %s" % str(val)
    val = server.rating()
    if val is None:
        val = unknown
    print "current track rating: %s" % str(val)
    val = server.trackCount()
    if val is None:
        val = unknown
    print "total number of tracks: %s" % str(val)

if __name__ == '__main__':
    main()
#    s = mp_Mpd()
#    print "%s, by %s. From the album %s." % (s.currentTrackTitle(),
#        s.currentTrackArtist(), s.currentTrackAlbumTitle())
