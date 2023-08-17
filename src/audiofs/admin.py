#
# $Id: admin.py,v 1.28 2011/03/23 19:29:37 jgm Exp $
#
# Defines functions and classes used to administer a music directory and the
# associated programs, etc.
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
import time

import getopt

import mpd
import musicfs

import config
import utilities as ut


# Constants.

_conf = config.obtain()

# Verbosity levels (for error/message reporting).
SILENT = 0              # only report errors via a non-zero exit code
QUIET = 1               # only report errors
NORMAL_VERBOSITY = 2    # report errors and messages
VERBOSE = 3             # report errors, messages and debugging info

_ad_allVerbosityLevels = range(VERBOSE + 1)

# The mount option(s) used to specify a "real" files directory.
_ad_realOptsPart = ',real=%s'


# The basename of the README file that's created in the root music directory.
_ad_readmeFilename = "README.txt"

# The basename of the file to which to write the process ID (PID) of the
# daemon process that processes commands to change music files' ratings.
_ad_changeRatingPidFilename = "change-ratings.pid"

# The basename of the file to which to write the process ID (PID) of the
# daemon process that processes commands to adjust how and whether
# information about the current MPD track is displayed.
_ad_mpdDisplayInformationPidFilename = "mpd-display-info.pid"


# The basename of the script that dismantles the music directory that we
# build.
_ad_dismantleScriptFilename = "dismantle-music-directory"

# A list of the basenames of the miscellaneous scripts that are symlinked
# under a music directory's "binaries" subdirectory.
_ad_miscellaneousScriptsFilenames = ["create-playlist",
    "maintain-cache-directory", "mpd-add-tracks", "mpd-create-database",
    "mpd-decrease-rating", "mpd-increase-rating", "mpd-set-rating",
    "mpd-hide-current-track-info", "mpd-show-current-track-info",
    "mpd-refresh-current-track-info", "mpd-toggle-current-track-info",
    "mpd-speak-current-track-info",
    "preload-audio-files", "refresh-ratings-files",
    "activate-music-directory", "deactivate-music-directory",
    "catalogue-music-directory"]


# The format of the command used to unmount a filesystem.
_fs_unmountCommandFormat = _conf.fusermountProgram + ' -uq "%s"'

# The verbosity-related command line options.
_ad_verbosityOptions = "[-QSV] [--quiet|--silent|--verbose]"

# A description of the verbosity-related command line options.
_ad_verbosityOptionsDescription = """
    --silent or -S prevents anything from being output to
        standard output or standard error, including error
        messages (so the only way to detect errors would be
        from examining the exit code)
    --quiet or -Q prevents anything except error messages
        from being output to standard output or standard error
    --verbose or -V causes extra information (which is usually
        only useful for debugging this program) to be output

If more than one of the '-S', '-Q' or '-V' options - or the
equivalent long options - is specified then the last one is the
one that is used. If none are specified then both informational
and error messages are output. (Informational messages are
always written to standard output and error messages are always
written to standard error.)"""


# Functions.

def ad_verbosityOptions():
    """
    Returns a string consisting of the verbosity-related command line
    options, as might appear in the first line of the description of a
    program that accepted such options.
    """
    result = _ad_verbosityOptions
    assert result is not None
    return result

def ad_verbosityOptionsDescription():
    """
    Returns a description of the verbosity-related command line options,
    as might appear in the description of a program that accepted such
    options.
    """
    result = _ad_verbosityOptionsDescription
    assert result is not None
    return result

def ad_parseVerbosityOptions(cmdArgs):
    """
    Parses the command line arguments 'cmdArgs' - which is assumed NOT to
    include the program's name as its first argument - and returns a
    pair consisting of the verbosity level specified by any options in
    'cmdArgs' and a list of the arguments in 'cmdArgs', in order, that are
    NOT verbosity-related options.

    Note: if no verbosity-related options are in 'cmdArgs' then the default
    verbosity level 'NORMAL_VERBOSITY' will be the first item in the returned
    pair.
    """
    assert cmdArgs is not None
    otherArgs = []
    verbosity = NORMAL_VERBOSITY
    args = None
    try:
        opts, args = getopt.getopt(cmdArgs, "VSQ",
                                   ["verbose", "silent", "quiet"])
        for opt, val in opts:
            if opt in ("-V", "--verbose"):
                verbosity = VERBOSE
            elif opt in ("-Q", "--quiet"):
                verbosity = QUIET
            elif opt in ("-S", "--silent"):
                verbosity = SILENT
    except getopt.GetoptError, ex:
        otherArgs.append(ex.opt)
    if args:
        otherArgs.extend(args)
    result = (verbosity, otherArgs)
    assert len(result) == 2
    assert result[0] >= 0
    assert result[1] is not None
    return result


# Classes.

class ad_AdminError(Exception):
    """
    The base class for all administration-specific exception classes.
    """
    pass

class ad_FatalAdminError(ad_AdminError):
    """
    The class of exception thrown when, during an administrative operation,
    an error happens that causes the operation to terminate immediately.
    """
    pass


class ad_AbstractMusicDirectoryProgram(ut.ut_AbstractProgram):
    """
    An abstract base class for classes that represent programs that build,
    activate, dismantle, etc. music directories.
    """

    def _usageMessage(self, progName, shortHelpOpts, longHelpOpts,
                     helpOptionsDesc):
        assert progName
        assert shortHelpOpts is not None
        assert longHelpOpts is not None
        assert helpOptionsDesc is not None

        result = """
usage: %(progName)s %(shortHelpOpts)s %(longHelpOpts)s %(verbosityOpts)s %(otherOpts)s

%(mainUsage)s%(otherOptionsDesc)s
%(helpOptionsDesc)s
The other options are:
%(verbosityOptsDesc)s
""" % { "progName": progName, "shortHelpOpts": shortHelpOpts,
        "longHelpOpts": longHelpOpts, "verbosityOpts": ad_verbosityOptions(),
        "mainUsage": self._ad_mainUsageDescription(),
        "helpOptionsDesc": helpOptionsDesc,
        "verbosityOptsDesc": ad_verbosityOptionsDescription(),
        "otherOpts": self._ad_otherOptionsUsage(),
        "otherOptionsDesc": self._ad_otherOptionsDescription() }
        assert result is not None
        return result

    def _shortOptions(self):
        result = "VSQ" + self._ad_otherShortOptions()
        assert result is not None
        return result

    def _longOptionsList(self):
        result = ["verbose", "silent", "quiet"]
        result.extend(self._ad_otherLongOptionsList())
        assert result is not None
        return result

    def _buildInitialArgumentsMap(self):
        result = { "verbosity": NORMAL_VERBOSITY }
        self._ad_addOtherInitialArguments(result)
        assert result is not None
        return result

    def _processOption(self, opt, val, argsMap):
        assert opt
        # 'val' may be None
        assert argsMap is not None
        result = True
        verbosity = None
        if opt in ("-V", "--verbose"):
            verbosity = VERBOSE
        elif opt in ("-Q", "--quiet"):
            verbosity = QUIET
        elif opt in ("-S", "--silent"):
            verbosity = SILENT
        else:
            result = self._ad_processOtherOption(opt, val, argsMap)
        if verbosity is not None:
            argsMap["verbosity"] = verbosity
        return result

    def _processNonOptionArguments(self, args, argsMap):
        assert args is not None
        assert argsMap is not None
        result = True
        if len(args) != 0:
            self._fail("Too many arguments.")
            result = False
        return result

    def _execute(self, argsMap):
        """
        Executes this program using the information from the arguments map
        'argsMap' built by processing all of our arguments.
        """
        assert argsMap is not None
        result = 0
        a = ad_MusicDirectoryAdministrator(argsMap["verbosity"])
        try:
            self._ad_administer(a, argsMap)
        except ad_FatalAdminError, ex:
            self._fail(str(ex))
            result = 2
        assert result >= 0
        return result


    def _ad_mainUsageDescription(self):
        """
        Returns a paragraph describing what this program does, without going
        in to what the various options do.
        """
        #assert result
        raise NotImplementedError

    def _ad_administer(self, ad, argsMap):
        """
        Performs whatever administration task(s) that this program does,
        using the ad_MusicDirectoryAdministrator 'ad' and the arguments
        map 'argsMap' to do it.

        Raises an ad_FatalAdminError iff one or more tasks are not
        successfully performed.
        """
        #assert ad is not None
        #assert argsMap is not None
        raise NotImplementedError


    def _ad_otherOptionsUsage(self):
        """
        All of this program's other options, as they would appear in the
        first line of the program's usage message.
        """
        #assert result is not None
        return ""

    def _ad_otherOptionsDescription(self):
        """
        A description of this program's other options.
        """
        #assert result is not None
        return ""

    def _ad_otherShortOptions(self):
        """
        Returns our other short options as a string, in a form suitable for
        being appended to another string to build the result of our
        _shortOptions() method.
        """
        #assert result is not None
        return ""

    def _ad_otherLongOptionsList(self):
        """
        Returns our other long options as a list of strings, in a form
        suitable for extend()ing another list to build the result of our
        _longOptionsList() method.
        """
        #assert result is not None
        return []

    def _ad_addOtherInitialArguments(self, argsMap):
        """
        Adds any other initial arguments to 'argsMap'.
        """
        pass

    def _ad_processOtherOption(self, opt, val, argsMap):
        """
        Processes the other option 'opt' and its associated value 'val' by
        updating 'argsMap' appropriately and returning True if successful,
        or reports failure and returns False if 'opt' isn't one of our
        other options or it and/or 'val' are somehow incorrect.

        This version always reports 'opt' as being an unknown option.
        """
        self._handleUnknownOption(opt)


class ad_MusicDirectoryAdministrator(object):
    """
    Represents objects used to administer a music directory.
    """

    def __init__(self, verbosity = NORMAL_VERBOSITY):
        assert verbosity in _ad_allVerbosityLevels
        self._ad_verbosity = verbosity
        object.__init__(self)


    def ad_buildMusicDirectory(self, doGenerateDocs = False,
                               doGeneratePlaylists = False):
        """
        Builds the music directory and everything in it, and starts any and
        all programs associated with it.

        Note: this method will raise a ??? exception iff the root
        directory specified in the configuration isn't an existing empty
        directory.
        """
        rootDir = _conf.rootDir
        self._ad_checkRootDirectoryIsEmptyAndChangeable(rootDir)
        realDir = _conf.realFilesDir
        self._ad_populateRealSubdirectoryFromDataDirectories(realDir,
                                                             _conf.dataDirs)
        baseDir = _conf.baseDir
        self._ad_populateBaseDirectoryFromRealDirectory(realDir, baseDir)
        self._ad_createOtherFilesDirectoryStructure(_conf.otherDir)
        self._ad_buildCaches()

        # Start all daemon processes.
        #
        # Note: the ratings change daemon needs to be running before we
        # refresh our metadata files from our catalogue.
        self.ad_startRatingsChangeDaemon()
        self.ad_startMpdCurrentTrackDisplayDaemon()

        # Note: the search database needs to be refreshed before we mount
        # the music search filesystem.
        self._ad_report("Refreshing metadata, ratings, etc. files from the "
                        "catalogue ...")
        mm = musicfs.fs_MusicMetadataManager()
        mm.fs_refreshAllMetadataFilesFromCatalogue()

        self._ad_mountAudioFilesystems()
        self._ad_mountMusicSearchFilesystem()

        self._ad_createReadmeFile(rootDir)

        # I have no idea why, but this seems to fix some problems with newly-
        # built music directories (such as the main process using way too
        # much CPU, apparently indefinitely).
        #
        # It also fixes a problem with commands to change a file's rating -
        # after the first one - not making it to the change ratings daemon.
        # Again, I have no idea why ...
        self._ad_report("\nDeactivating and then reactivating the music "
                        "directory ...")
        time.sleep(1)
        self.ad_deactivateMusicDirectory()
        time.sleep(1)
        self.ad_activateMusicDirectory()

        if doGeneratePlaylists or doGenerateDocs:
            self._ad_report("\nYou can now start using the music directory")
            self._ad_report("while we generate some more files ...\n")
            if doGeneratePlaylists:
                self._ad_report("Generating playlists ...")
                mm.fs_generatePlaylists()
            if doGenerateDocs:
                self._ad_report("Generating documentation ...")
                mm.fs_generateDocumentation()
        self._ad_report("\nSuccessfully created '%s' and its contents.\n" %
                        rootDir)

    def ad_dismantleMusicDirectory(self):
        """
        Completely dismantles the music directory by stopping any and all
        programs associated with it, then deleting everything under the
        music directory so that it's an empty directory.
        """
        self.ad_deactivateMusicDirectory()
        self._ad_deleteEverythingUnderDirectory(_conf.rootDir)

    def ad_activateMusicDirectory(self):
        """
        Rebuilds the parts of the music directory and its contents that are
        disabled or removed when it is deactivated, and starts any and all
        programs that are stopped when that happens.

        See ad_deactivateMusicDirectory().
        """
        # Build/mount all of the cache directories/filesystems, then mount
        # all of the audio filesystems and (if required) the music search
        # filesystem.
        self._ad_buildCaches()
        self._ad_mountAudioFilesystems()
        self._ad_mountMusicSearchFilesystem()

        # Start all daemon processes.
        self.ad_startRatingsChangeDaemon()
        self.ad_startMpdCurrentTrackDisplayDaemon()

    def ad_deactivateMusicDirectory(self):
        """
        Deactivates the music directory by stopping any and all programs
        associated with it, then unmounting any and all music filesystems
        mounted under the music directory.

        See ad_activateMusicDirectory().
        """
        # Stop all daemon processes.
        self.ad_stopMpdCurrentTrackDisplayDaemon()
        self.ad_stopRatingsChangeDaemon()

        # Unmount all of the (music and non-music) filesystems iff they're
        # still mounted.
        for mp in _conf.allFilesystemMountPoints:
            self._ad_unmountFilesystem(mp)


    def _ad_checkRootDirectoryIsEmptyAndChangeable(self, rootDir):
        """
        Checks that the pathname 'rootDir' of a music directory's root
        directory is an existing changeable directory that is also empty, and
        die()s reporting an appropriate message if it isn't.
        """
        assert rootDir is not None
        if not os.path.isdir(rootDir):
            self._ad_die("The root directory '%s'\neither doesn't exist or "
                "isn't a directory." % rootDir)
        if not ut.ut_isDirectoryFullyChangeable(rootDir):
            self._ad_die("The root directory '%s'\nisn't fully changeable: "
                "reading and/or writing and/or searching\nit will fail." %
                rootDir)
        if len(os.listdir(rootDir)) > 0:
            self._ad_die("The root directory '%s'\nmust be empty but "
                "isn't." % rootDir)

    def _ad_populateRealSubdirectoryFromDataDirectories(self, realDir,
                                                        dataDirs):
        """
        Creates directories and symlinks under the "real audio files"
        subdirectory of our music directory for directories and files,
        respectively, under each of the data directories whose pathnames
        are in 'dataDirs'.

        If any part of populating 'realDir' fails it will die() with a
        message describing why it failed.
        """
        assert realDir is not None
        assert dataDirs is not None
        #assert "each entry in 'dataDirs' is not None
        oldCwd = os.getcwd()
        try:
            for dd in dataDirs:
                self._ad_report("Processing data directory '%s' ..." % dd)
                if not os.path.isdir(dd):
                    self._ad_die("The data directory '%s'\neither doesn't "
                        "exist or isn't a directory." % dd)
                if not ut.ut_isDirectoryFullyAccessible(dd):
                    self._ad_die("The data directory '%s'\nisn't fully "
                        "accessible: reading and/or searching it will "
                        "fail." % dd)
                os.chdir(dd)
                self._ad_createDataDirectorySubtreeAnalogue(".", realDir)
        finally:
            os.chdir(oldCwd)

    def _ad_populateBaseDirectoryFromRealDirectory(self, realDir, baseDir):
        """
        Creates subdirectories and symlinks under the base directory with
        pathname 'baseDir' from the "real files" directory with pathname
        'realDir' and its contents.

        Note: both 'baseDir' and 'realDir' are subdirectories (or the same
        as) our music directory.
        """
        assert realDir is not None
        assert baseDir is not None

        # Create a subdirectory under the base directory for each
        # direct subdirectory of 'realDir'.
        for d in os.listdir(realDir):
            if os.path.isdir(os.path.join(realDir, d)):
                self._ad_createDirectory(os.path.join(baseDir, d))

        # If there's a 'mainKindAndFormatSubdir' under the 'realDir' then
        # create a corresponding symlink to it under 'baseDir'.
        kfd = _conf.mainKindAndFormatSubdir
        src = os.path.join(realDir, kfd)
        dest = os.path.join(baseDir, kfd)
        if os.path.isdir(src):
            self._ad_createDirectory(os.path.dirname(dest))
                # 'dest' may or may not already exist
            self._ad_createSymlink(src, dest)
        else:
            self._ad_report("The main kind and format directory '%s' "
                            "doesn't exist." % src)

    def _ad_createOtherFilesDirectoryStructure(self, otherDir):
        """
        Creates the directory with pathname 'otherDir' if it doesn't already
        exist, as well as some directories and symlinks under it.

        Note: this method doesn't create all of the content underneath
        'otherDir': it just creates the main structure.
        """
        assert otherDir is not None
        self._ad_report("Creating 'other' directory and its "
                        "subdirectories ...")
        self._ad_createDirectory(otherDir)
        binDir = _conf.binDir
        self._ad_createDirectory(binDir)
        self._ad_createDirectory(_conf.systemDir)
        self._ad_createDirectory(_conf.documentationDir)
        self._ad_createBinariesSymlinks(binDir)
        self._ad_report("Creating a symlink to the metadata directory ...")
        d = ut.ut_expandedAbsolutePathname(_conf.sourceMetadataDir)
        self._ad_createSymlink(d, _conf.metadataDir)
        self._ad_createDirectory(_conf.playlistsDir)
        self._ad_createDirectory(_conf.generatedPlaylistsDir)
        self._ad_report("Creating a symlink to the custom playlists "
                        "directory ...")
        d = ut.ut_expandedAbsolutePathname(_conf.sourcePlaylistsDir)
        self._ad_createSymlink(d, _conf.customPlaylistsDir)
        self._ad_report("Creating a symlink to the ratings directory ...")
        d = ut.ut_expandedAbsolutePathname(_conf.sourceRatingsDir)
        self._ad_createSymlink(d, _conf.ratingsDir)
        self._ad_createDirectory(_conf.searchDir)

    def _ad_createBinariesSymlinks(self, binDir):
        """
        Creates symlinks to various binaries in the directory with pathname
        'binDir': if it fails it die()s with a message explaining why.
        """
        assert binDir is not None
        assert os.path.isdir(binDir)

        # Symlink (the real path of) this script and the associated
        # 'dismantle' script.
        f = os.path.realpath(sys.argv[0])
        assert not ut.ut_doesEndWithPathnameSeparator(f)
            # since realpath() will remove it
        (ourDir, ourName) = os.path.split(f)
        self._ad_report("Creating symlinks to music directory build and "
                        "dismantle scripts ...")
        af = os.path.abspath(f)
        self._ad_createSymlink(af, os.path.join(binDir, ourName))
        self._ad_createSymlink(af, os.path.join(binDir,
                                        _ad_dismantleScriptFilename))

        # Symlink (the real path of) each of the filesystem scripts.
        ourDir = os.path.abspath(ourDir)
        for name in _conf.allFilesystemFilenames:
            self._ad_report("Creating symlink to filesystem script "
                            "'%s' ..." % name)
            self._ad_createSymlink(os.path.join(ourDir, name),
                                   os.path.join(binDir, name))

        # Symlink miscellaneous scripts into the 'bin' subdirectory.
        self._ad_report("Creating symlinks to miscellaneous scripts ...")
        for name in _ad_miscellaneousScriptsFilenames:
            self._ad_createSymlink(os.path.join(ourDir, name),
                                   os.path.join(binDir, name))

    def _ad_buildCaches(self):
        """
        Build the caches: that is, ensure that the cache directories exist.
        """
        # Create the cache directories iff they don't already exist. (The
        # list may contain duplicates, but it doesn't hurt to try to create
        # the directory more than once.)
        for d in _conf.allCacheDirs:
            self._ad_createDirectory(d)

    def _ad_mountAudioFilesystems(self):
        """
        Mounts the filesystems that transmogrify one type and kind of audio
        file into another.
        """
        binDir = _conf.binDir
        commonOpts = _conf.commonMountOptions
        if commonOpts:
            commonOpts += ","
        optsFmt = commonOpts + 'albums=%s,cache=%s'
        realDir = _conf.flactrackRealDir
        if os.path.isdir(realDir):
            optsFmt += _ad_realOptsPart
            opts = optsFmt % (_conf.flactrackAlbumsDir,
                              _conf.flactrackCacheDir, realDir)
        else:
            opts = optsFmt % (_conf.flactrackAlbumsDir,
                              _conf.flactrackCacheDir)
        self._ad_mountFilesystem(binDir, _conf.flactrackFilename, opts,
                                 _conf.flactrackMountPoint)
        self._ad_mountFlacToMp3Filesystems(binDir, commonOpts)
        self._ad_mountFlacToOggFilesystems(binDir, commonOpts)


    def _ad_mountMusicSearchFilesystem(self):
        """
        Mounts the filesystem that allows music files to be searched based
        on a number of criteria, provided that a search directory has been
        configured.
        """
        c = _conf
        if c.isNonemptySearchDirectory():
            import musicsearchfs
                # we do this here to avoid requiring search-specific
                # dependencies when there's no music search directory
            tags = c.searchableTagNames
            commonOpts = _conf.commonMountOptions
            if commonOpts:
                commonOpts += ","
            optsFmt = commonOpts + 'db=%s,tags=%s,base=%s'
            opts = optsFmt % (musicfs.fs_searchDatabasePathname(),
                              musicsearchfs.fs_tagSeparator.join(tags),
                              _conf.rootDir)
            self._ad_mountFilesystem(c.binDir, c.musicsearchFilename, opts,
                                     c.searchDir)

    def _ad_mountFlacToMp3Filesystems(self, binDir, commonOpts):
        """
        Mounts any and all flac2mp3 filesystems.
        """
        assert binDir is not None
        assert commonOpts is not None
        c = _conf
        optsFmt = commonOpts + 'bitrate=%i,flac=%s,cache=%s'
        realDir = c.flac2mp3RealDir
        flacDir = c.flac2mp3FlacDir
        cacheDir = c.flac2mp3CacheDir
        isRealDir = os.path.isdir(realDir)
        if isRealDir:
            optsFmt += _ad_realOptsPart
        fname = c.flac2mp3Filename
        for (mp, bitrate) in c.flac2mp3MountPointToBitrateMap.items():
            if isRealDir:
                opts = optsFmt % (bitrate, flacDir, cacheDir, realDir)
            else:
                opts = optsFmt % (bitrate, flacDir, cacheDir)
            self._ad_mountFilesystem(binDir, fname, opts, mp)

    def _ad_mountFlacToOggFilesystems(self, binDir, commonOpts):
        """
        Mounts any and all flac2ogg filesystems.
        """
        assert binDir is not None
        assert commonOpts is not None
        c = _conf
        optsFmt = commonOpts + 'bitrate=%i,flac=%s,cache=%s'
        realDir = c.flac2oggRealDir
        flacDir = c.flac2oggFlacDir
        cacheDir = c.flac2oggCacheDir
        isRealDir = os.path.isdir(realDir)
        if isRealDir:
            optsFmt += _ad_realOptsPart
        fname = c.flac2oggFilename
        for (mp, bitrate) in c.flac2oggMountPointToBitrateMap.items():
            if isRealDir:
                opts = optsFmt % (bitrate, flacDir, cacheDir, realDir)
            else:
                opts = optsFmt % (bitrate, flacDir, cacheDir)
            self._ad_mountFilesystem(binDir,fname, opts, mp)


    def ad_startRatingsChangeDaemon(self):
        """
        Starts the ratings change daemon process.
        """
        cmdSink = musicfs.fs_changeRatingCommandSink()
        if os.path.exists(cmdSink):
            self._ad_report("The FIFO to which to write commands to change "
                            "ratings already exists.")
        else:
            self._ad_report("Creating the FIFO to which to write commands "
                            "to change ratings ...")
            os.mkfifo(cmdSink)
        pidFile = self._ad_changeRatingPidPathname()
        musicfs.fs_ChangeRatingsCommandProcessor(cmdSink, pidFile)

    def ad_stopRatingsChangeDaemon(self):
        """
        Stops the ratings change daemon process.
        """
        pidFile = self._ad_changeRatingPidPathname()
        self._ad_stopProcess(pidFile, "ratings change daemon")
        self._ad_tryToDeleteFile(pidFile)
        cmdSink = musicfs.fs_changeRatingCommandSink()
        self._ad_tryToDeleteFile(cmdSink)

    def _ad_changeRatingPidPathname(self):
        """
        Returns the pathname of the file that contains the PID of the ratings
        change daemon process (iff it's currently running).
        """
        result = os.path.join(_conf.systemDir, _ad_changeRatingPidFilename)
        assert result is not None
        return result


    def ad_startMpdCurrentTrackDisplayDaemon(self):
        """
        Starts the MPD current track information display daemon.
        """
        if self._ad_doDisplayMpdCurrentTrackInformation():
            cmdSink = mpd.mp_displayInformationCommandSink()
            if os.path.exists(cmdSink):
                self._ad_report("The FIFO to which to write commands to "
                    "adjust how and whether MPD current track information "
                    "is displayed already exists.")
            else:
                self._ad_report("Creating the FIFO to which to write "
                    "commands to adjust how and whether MPD current track "
                    "information is displayed ...")
                os.mkfifo(cmdSink)
            pidFile = self._ad_mpdDisplayInformationPidPathname()
            mpd.mp_MpdInformationDisplayProcess(cmdSink, pidFile)
        else:
            self._ad_report("The MPD current track information display "
                "daemon was NOT started because the configuration specified "
                "that it wasn't to be used.")

    def ad_stopMpdCurrentTrackDisplayDaemon(self):
        """
        Stops the MPD current track information display daemon.
        """
        pidFile = self._ad_mpdDisplayInformationPidPathname()
        if self._ad_doDisplayMpdCurrentTrackInformation():
            self._ad_stopProcess(pidFile,
                             "MPD current track information display daemon")
        else:
            self._ad_debug("Didn't attempt to stop the MPD current track "
                "information display daemon because the configuration "
                "specified that it wasn't to be used.")
        self._ad_tryToDeleteFile(pidFile)
        cmdSink = mpd.mp_displayInformationCommandSink()
        self._ad_tryToDeleteFile(cmdSink)

    def _ad_mpdDisplayInformationPidPathname(self):
        """
        Returns the pathname of the file to which to write the process ID
        (PID) of the daemon process that processes commands to adjust how and
        whether information about the current MPD track is displayed.
        """
        result = _ad_mpdDisplayInformationPidFilename
        result = os.path.join(_conf.systemDir, result)
        assert result is not None
        return result

    def _ad_doDisplayMpdCurrentTrackInformation(self):
        """
        Returns True iff the configuration specifies that information about
        the default NPD server's current track is to be displayed.
        """
        prog = _conf.mpdDisplayInformationProgram
        return (prog is not None)


    def _ad_createReadmeFile(self, d):
        """
        Creates a README file in the directory with pathname 'd', or fail()s
        with an appropriate error message.
        """
        fmt = """Everything in and under this directory was automatically generated,
and may be deleted and regenerated at some point in the future, so

    DO NOT ADD OR CHANGE ANYTHING UNDER THIS DIRECTORY!

This directory's contents were generated by the program with pathname
'%s' (to which
there is a symlink in our '%s' subdirectory).

The contents of this directory amalgamate the music files found under
the following directories:

    %s

"""
        f = os.path.join(d, _ad_readmeFilename)
        if os.path.exists(f):
            self._ad_fail("Couldn't create the README file '%s' since\n"
                "a file with that pathname already exists" % f)
        else:
            w = None
            try:
                w = open(f, 'w')
                progName = os.path.abspath(sys.argv[0])
                w.write(fmt % (progName, _conf.binDir,
                               "\n    ".join(_conf.dataDirs)))
            finally:
                ut.ut_tryToCloseAll(w)

    def _ad_createDataDirectorySubtreeAnalogue(self, srcTopDir, destTopDir):
        """
        Creates an analogue for the data directory subtree whose topmost
        directory is 'srcTopDir': the analogue's topmost directory will be
        'destTopDir'. Analogues are NOT created for non-directories that are
        determined to definitely NOT be audio files.

        Note: 'destTopDir' will be created iff it doesn't already exist.

        An analogue for a directory under 'srcTopDir' is created by creating
        a corresponding directory with the same name under 'destTopDir'; an
        analogue for a file 'f' under 'srcTopDir' is created by creating a
        corresponding symbolic link under 'destTopDir' with the same basename
        as 'f' and that links to 'f'.

        Note: we defined this recursive method instead of just using
        'os.walk()' since the latter doesn't seem to walk down symlinks to
        directories (though it does consider the symlinks themselves to be
        directories).
        """
        self._ad_debug("---> in createDataDirectorySubtreeAnalogue(%s, %s)" % (srcTopDir, destTopDir))
        assert srcTopDir is not None
        assert not os.path.isabs(srcTopDir)
        assert destTopDir is not None
        exts = _conf.nonAudioFileExtensions
        nonAudioExts = set([ut.ut_fullExtension(e) for e in exts])
        self._ad_reallyCreateDataDirectorySubtreeAnalogue(srcTopDir,
                                                    destTopDir, nonAudioExts)

    def _ad_reallyCreateDataDirectorySubtreeAnalogue(self, srcTopDir,
                                                destTopDir, nonAudioExts):
        """
        See createDataDirectorySubtreeAnalogue().
        """
        self._ad_createDirectory(destTopDir)
        for f in os.listdir(srcTopDir):
            src = os.path.join(srcTopDir, f)
            dest = os.path.join(destTopDir, f)
            if os.path.isdir(src):
                if f in _conf.nonAudioSubdirectories:
                    self._ad_debug("    Ignoring the data subdirectory "
                        "'%s':\n    it is a non-audio subdirectory." % src)
                elif ut.ut_isDirectoryFullyAccessible(src):
                    self._ad_reallyCreateDataDirectorySubtreeAnalogue(src,
                                                        dest, nonAudioExts)
                else:
                    self._ad_report("    Ignoring the data subdirectory "
                        "'%s':\n    reading and/or searching it will fail." %
                        src)
            elif os.path.exists(src):
                (base, ext) = os.path.splitext(f)
                if ext not in nonAudioExts:
                    # We symlink to 'src''s absolute pathname.
                    self._ad_createSymlink(os.path.abspath(src), dest)
                else:
                    self._ad_debug("not symlinking '%s' since it isn't an "
                                   "audio file" % src)
            else:
                self._ad_debug("not symlinking '%s' since it's a broken "
                               "link" % src)


    def _ad_mountFilesystem(self, scriptsDir, script, opts, mountPoint,
                            doDebug = False):
        """
        Mounts a filesystem using the script in our 'scriptsDir' with
        filename 'script' on the directory 'mountPoint', passing the script
        the options 'opts'.

        Note: the mount point and any missing ancestor directories will be
        created if they don't already exist.
        """
        #self._ad_debug("---> in mountFilesystem(%s, %s, %s, %s, %s)" % (scriptsDir, script, str(opts), mountPoint, str(doDebug)))
        if getattr(_conf, 'doMountFilesystems', True):
            self._ad_debug("Creating mount point '%s' if it doesn't "
                           "already exist." % mountPoint)
            self._ad_createDirectory(mountPoint)
            if doDebug:
                coreOpts = "-d -o"
            else:
                coreOpts = "-o"
            fmt = '%s ' + coreOpts + ' %s %s'
            cmd = fmt % (os.path.join(scriptsDir, script), opts, mountPoint)
            self._ad_debug("Mounting filesystem using the command [%s]" % cmd)
            result = (ut.ut_executeShellCommand(cmd) is not None)
            if result:
                self._ad_report("Mounted filesystem on '%s'." % mountPoint)
            else:
                self._ad_fail("Failed to mount a filesystem using '%s'" %
                              script)
        else:
            self._ad_debug("Not mounting a filesystem on '%s' because "
                "automatic mounting and unmounting of filesystems has been "
                "disabled.")
            result = True  # considered successful if we're not to mount it.
        return result

    def _ad_unmountFilesystem(self, path):
        """
        Unmounts the filesystem mount on the directory with pathname 'path',
        reporting success or failure.
        """
        assert path is not None
        if getattr(_conf, 'doMountFilesystems', True):
            cmd = _fs_unmountCommandFormat % path
            if ut.ut_executeShellCommand(cmd) is None:
                self._ad_fail("Couldn't unmount a filesystem from '%s'" %
                              path)
            else:
                self._ad_report("Unmounted the filesystem mounted at '%s'." %
                                path)
        else:
            self._ad_report("Not unmounting the filesystem on '%s' because "
                "automatic mounting and unmounting of filesystems has been "
                "disabled.")

    def _ad_createDirectory(self, d):
        """
        Creates the directory with pathname 'd', or die()s with an
        appropriate error message.

        Note: no error is reported if 'd' already exists. Any missing
        ancestor directories of 'd' are created in addition to 'dir'.
        """
        assert d is not None
        try:
            ut.ut_createDirectory(d)
            self._ad_debug("created the subdirectory '%s' (or it already "
                           "existed)" % d)
        except OSError, ex:
            self._ad_die("Couldn't create the subdirectory '%s': "
                         "%s" % (d, str(ex)))

    def _ad_createSymlink(self, src, dest):
        """
        Creates a symlink with pathname 'dest' that links to the file with
        pathname 'src', or die()s with an appropriate error message.
        """
        assert src is not None
        assert dest is not None
        try:
            os.symlink(src, dest)
            self._ad_debug("created symlink '%s' ->\n    %s" % (dest, src))
        except OSError, ex:
            self._ad_die("Couldn't create the symlink '%s' that\nlinks to "
                         "'%s': %s" % (dest, src, str(ex)))

    def _ad_deleteEverythingUnderDirectory(self, d):
        """
        Deletes everything under the directory with pathname 'd', but not the
        directory itself.

        Returns True iff everything is successfully deleted.
        """
        assert d is not None
        self._ad_report("Deleting everything under '%s' ..." % d)
            # we report this since it may take a while to finish
        if os.path.isdir(d):
            result = True
            for f in os.listdir(d):
                path = os.path.join(d, f)
                try:
                    if os.path.isdir(path):
                        ut.ut_deleteTree(path)
                    else:
                        os.remove(path)
                except:
                    result = False
                    if os.path.isdir(path):
                        fmt = "Couldn't delete the directory '%s' (and " + \
                              "possibly some or all of the files and " + \
                              "directories under it)"
                    else:
                        fmt = "Couldn't delete the file '%s'"
                    self._ad_fail(fmt % path)
            if result:
                self._ad_report("Deleted  everything under '%s'." % d)
        else:
            result = False
            self._ad_report("The directory '%s' doesn't exist" % d)
        return result

    def _ad_stopProcess(self, pidFile, name):
        """
        Stops the process named 'name' whose PID is the sole contents of (the
        first line of) the file with pathname 'pidFile'.

        Note: 'name' is only used as the name of the process in error (and
        other) messages.

        Note: this method does NOT delete the pidFile.

        Returns True iff the process is successfully stopped.
        """
        #self._ad_debug("---> in stopProcess(%s, %s)" % (pidFile, name))
        assert pidFile is not None
        assert name is not None
        self._ad_report("Stopping the %s ..." % name)
        result = False
        if os.path.isfile(pidFile):
            lines = ut.ut_readFileLines(pidFile)
            if lines:
                strPid = lines[0].strip()
                try:
                    pid = ut.ut_parseInt(strPid, minValue = 2)
                except:
                    self._ad_fail("Stopping the '%s' process failed: the "
                        "first line of the PID file '%s' is '%s', which "
                        "isn't a valid PID." % (name, pidFile, strPid))
                else:
                    try:
                        self._ad_debug("about to kill process with ID %i" %
                                       pid)
                        res = ut.ut_tryToKill(pid)
                        self._ad_debug("finished killing process: existed? "
                                       "%s" % str(res))
                        result = True
                    except:
                        self._ad_debug("killing the process raised an exception")
                        result = False
            else:
                self._ad_fail("Stopping the '%s' process failed: there was "
                    "no PID in the PID file '%s'" % (name, pidFile))
        else:
            self._ad_fail("The '%s' was not stopped since its PID file '%s' "
                          "doesn't exist." % (name, pidFile))
        return result


    def _ad_tryToDeleteFile(self, path):
        """
        Tries to delete the file (or directory) with pathname 'path',
        returning True if it's successful, and reporting the failure and
        returning False if it isn't.
        """
        assert path is not None
        result = False
        try:
            ut.ut_deleteFileOrDirectory(path)
            result = True
        except OSError, ex:
            self._ad_report("Failed to delete the file '%s': %s" % (path, ex))
        return result

    def _ad_die(self, msg):
        """
        Writes 'msg' to standard error and then raises a ad_FatalAdminError.
        """
        assert msg is not None
        if self._ad_verbosity > SILENT:
            print >> sys.stderr, "\n%s\n" % msg
        raise ad_FatalAdminError, msg

    def _ad_fail(self, msg):
        """
        Writes 'msg' to standard error and then returns: we don't exit.
        """
        assert msg is not None
        if self._ad_verbosity > SILENT:
            print >> sys.stderr, msg

    def _ad_report(self, msg):
        """
        Writes 'msg' to standard output.
        """
        assert msg is not None
        if self._ad_verbosity > QUIET:
            print msg

    def _ad_debug(self, msg):
        """
        Writes 'msg' to standard output as debugging information.
        """
        assert msg is not None
        if self._ad_verbosity >= VERBOSE:
            print "DEBUG: " + msg
