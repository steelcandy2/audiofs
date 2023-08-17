#
# $Id: music.py,v 1.35 2012/10/12 02:28:35 jgm Exp $
#
# Defines music-related constants, functions and classes, including ones
# dealing with specific audio file formats.
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

import audiofs.utilities as ut
import audiofs.config as config


# Constants.

_conf = config.obtain()

# The artist name that's used when the real name can't be obtained.
mu_unknownArtistName = "[Unknown Artist]"

# The extension on FLAC files.
mu_flacExtension = config.flacExtension
mu_fullFlacExtension = ut.ut_fullExtension(mu_flacExtension)

# The extension on CUE files (which are generally associated with album
# FLAC files).
mu_cueExtension = "cue"
mu_fullCueExtension = ut.ut_fullExtension(mu_cueExtension)

# The extension on MP3 files.
mu_mp3Extension = config.mp3Extension
mu_fullMp3Extension = ut.ut_fullExtension(mu_mp3Extension)

# The extension on OGG files.
mu_oggExtension = config.oggExtension
mu_fullOggExtension = ut.ut_fullExtension(mu_oggExtension)


# The end of the base filename of a "various artists" album FLAC file.
_mu_variousArtistsFilenameEnd = \
    ut.ut_addExtension("_VariousArtists", mu_flacExtension)

# The separator between the artist name and the title name in the "title"
# of a track in a CUE file for a "various artists" album. (The first such
# separator is the actual separator.)
mu_artistTitleSep = " / "


# The separator between the name and value parts of a tag in the format
# that a FLAC file's tags are exported by 'metaflac'.
_mu_exportedFlacTagNameValueSeparator = "="

# The separator between the name and value parts of a tag in the format
# that an OGG file's tags are exported by 'vorbiscomment'.
_mu_exportedOggTagNameValueSeparator = "="

# The separator between the name and value parts of a tag in the format
# that an MP3 file's tags are exported by 'mid3v2'.
_mu_exportedMp3TagNameValueSeparator = "="


# The names of the various common FLAC tags.
mu_flacTrackTitleTag   = "TITLE"       # track title
mu_flacArtistTag       = "ARTIST"      # artist/performer name
mu_flacAlbumTag        = "ALBUM"       # album title
mu_flacDateTag         = "DATE"        # release date/year
mu_flacTrackNumberTag  = "TRACKNUMBER" # 1-based track number
mu_flacGenreTag        = "GENRE"       # genre name
mu_flacAlbumCddbTag    = "CDDB"        # album's CDDB ID
mu_flacCommentTag      = "COMMENT"     # comment

# The names of various common MP3 tags.
_mu_mp3TrackTitleTag    = "TIT2"        # track title
_mu_mp3ArtistTag        = "TPE1"        # artist/performer name
_mu_mp3AlbumTag         = "TALB"        # album title
_mu_mp3DateTag          = "TYER"        # release date/year
_mu_mp3TrackNumberTag   = "TRCK"        # 1-based track number
_mu_mp3GenreTag         = "TCON"        # genre name
_mu_mp3CommentTag       = "COMM"        # comment

# A map from the names of FLAC tags to the 'lame' MP3 program options that
# are used to set the values of corresponding tags in MP3s.
_mu_flacTagNameToLameOptionNameMap = {
    mu_flacTrackTitleTag:   "--tt",
    mu_flacArtistTag:      "--ta",
    mu_flacAlbumTag:       "--tl",
    mu_flacDateTag:        "--ty",
    mu_flacTrackNumberTag: "--tn",
    mu_flacGenreTag:       "--tg",
    mu_flacCommentTag:     "--tc"
}

# A map from the names of common MP3 tags to the names of the corresponding
# FLAC tags.
_mu_mp3TagNameToFlacTagNameMap = {
    _mu_mp3TrackTitleTag:   mu_flacTrackTitleTag,
    _mu_mp3ArtistTag:       mu_flacArtistTag,
    _mu_mp3AlbumTag:        mu_flacAlbumTag,
    _mu_mp3DateTag:         mu_flacDateTag,
    _mu_mp3TrackNumberTag:  mu_flacTrackNumberTag,
    _mu_mp3GenreTag:        mu_flacGenreTag,
    _mu_mp3CommentTag:      mu_flacCommentTag
}


# External command names.
_mu_cueprintCommand = _conf.cueprintProgram
_mu_cuebreakpointsCommand = _conf.cuebreakpointsProgram
_mu_ffmpegCommand = _conf.ffmpegProgram
_mu_ffprobeCommand = _conf.ffprobeProgram
_mu_flacCommand = _conf.flacProgram
_mu_metaflacCommand = _conf.metaflacProgram
_mu_lameCommand = _conf.lameProgram
_mu_id3v2Command = _conf.id3v2Program
_mu_oggencCommand = _conf.oggencProgram
_mu_vorbiscommentCommand = _conf.vorbiscommentProgram


# Command formats.

_mu_flacAlbumTrackTitlesCmdStart = _mu_cueprintCommand + ' -t "%%t\n" "%s"'

_mu_nicePrefix = _conf.niceCommandPrefix
if _mu_nicePrefix:
    _mu_nicePrefix += " "

_mu_discardFile = _conf.discardFile
_mu_discardStandardError = ' 2> "%s"' % _mu_discardFile
_mu_writeStandardErrorToOutput = ' 2>&1 '

# flac -d -w --totally-silent -c $range "$albumFile" | \
#    flac $setTagOpts -w --totally-silent -f --fast --no-seektable -o - -
#
# where '$range' consists of a '--skip' and/or '--until' option and
# '$setTagOpts' consists of zero or more '-T' options with appropriate
# arguments.
#
# Note: the '--no-seektable' option is necessary because apparently it can't
# be added when flac is writing to its standard output.
_mu_defaultFlacAlbumToTrackCmdFmt = _mu_nicePrefix + _mu_flacCommand + \
    ' -d -w --totally-silent -c %s "%s" | ' + _mu_flacCommand + \
    ' %s -w --totally-silent -f --fast --no-seektable -o - -'

# ffmpeg -y -f flac -acodec flac [-ss secs] -i "$albumFile" [-t secs]
#    -metadata TITLE="$title" -metadata track=$trackNum $range - 2>/dev/null
_mu_ffmpegFlacAlbumToTrackCmdFmt = _mu_nicePrefix + _mu_ffmpegCommand + \
    ' -y -f flac -acodec flac %s -i "%s" -f flac %s -metadata ' + \
    'TITLE="%s" -metadata track=%s -' + _mu_discardStandardError


# flac -dwc --totally-silent "${flacFile}" | \
#    lame --noreplaygain --silent ${tagOpts} --add-id3v2 -b ${bitrate} - -
_mu_lameFlacToMp3CmdFmt = _mu_nicePrefix + _mu_flacCommand + \
    ' -dwc --totally-silent "%s" | ' + \
    _mu_lameCommand + ' --noreplaygain --silent %s --add-id3v2 -b %i - -'

# ffmpeg -y -f flac -i "$flacFile" -f mp3 -acodec libmp3lame \
#    -ab ${bitrate}k - 2>/dev/null
_mu_ffmpegFlacToMp3CmdFmt = _mu_nicePrefix + _mu_ffmpegCommand + \
    ' -y -f flac -i "%s" -f mp3 -acodec libmp3lame -ab %ik -' + \
    _mu_discardStandardError

# oggenc -Q -b ${bitrate} -o - "${flacFile}"
_mu_oggencFlacToOggCmdFmt = _mu_nicePrefix + _mu_oggencCommand + \
    ' -Q -b %i -o - "%s"'

# ffmpeg -y -f flac -i "$flacFile" -f ogg -acodec libvorbis \
#    -ab ${bitrate}k - 2>/dev/null"
_mu_ffmpegFlacToOggCmdFmt = _mu_nicePrefix + _mu_ffmpegCommand + \
    ' -y -f flac -i "%s" -f ogg -acodec libvorbis -ab %ik -' + \
    _mu_discardStandardError

_mu_flacTotalSamplesCmdFmt = _mu_metaflacCommand + \
    ' --show-total-samples "%s"' + _mu_discardStandardError
_mu_flacSampleRateCmdFmt = _mu_metaflacCommand + \
    ' --show-sample-rate "%s"' + _mu_discardStandardError

_mu_ffprobeTrackInformationCmdFmt = _mu_ffprobeCommand + ' "%s"' + \
    _mu_writeStandardErrorToOutput


# Functions.

def mu_hasFlacFilename(path):
    """
    Returns True iff the pathname 'path' ends in the FLAC extension and its
    filename part, not counting the FLAC extension, is non-empty.
    """
    assert path is not None
    return ut.ut_hasNonemptyFilename(path, mu_flacExtension)

def mu_addFlacExtension(path):
    """
    Returns the result of appending the extension for FLAC files -
    including the leading dot - to 'path'.
    """
    assert path is not None
    result = ut.ut_addExtension(path, mu_fullFlacExtension)
    assert result is not None
    return result

def mu_hasCueFilename(path):
    """
    Returns True iff the pathname 'path' ends in the CUE extension and its
    filename part, not counting the CUE extension, is non-empty.
    """
    assert path is not None
    return ut.ut_hasNonemptyFilename(path, mu_fullCueExtension)

def mu_addCueExtension(path):
    """
    Returns the result of appending the extension for CUE files -
    including the leading dot - to 'path'.
    """
    assert path is not None
    result = ut.ut_addExtension(path, mu_cueExtension)
    assert result is not None
    return result

def mu_hasMp3Filename(path):
    """
    Returns True iff the pathname 'path' ends in the MP3 extension and its
    filename part, not counting the MP3 extension, is non-empty.
    """
    assert path is not None
    return ut.ut_hasNonemptyFilename(path, mu_fullMp3Extension)

def mu_addMp3Extension(path):
    """
    Returns the result of appending the extension for MP3 files -
    including the leading dot - to 'path'.
    """
    assert path is not None
    result = ut.ut_addExtension(path, mu_mp3Extension)
    assert result is not None
    return result

def mu_hasOggFilename(path):
    """
    Returns True iff the pathname 'path' ends in the OGG extension and its
    filename part, not counting the OGG extension, is non-empty.
    """
    assert path is not None
    return ut.ut_hasNonemptyFilename(path, mu_fullOggExtension)

def mu_addOggExtension(path):
    """
    Returns the result of appending the extension for OGG files -
    including the leading dot - to 'path'.
    """
    assert path is not None
    result = ut.ut_addExtension(path, mu_oggExtension)
    assert result is not None
    return result


def mu_durationInSeconds(path):
    """
    Returns the duration, in seconds, of the audio file with pathname 'path',
    or -1 if the duration couldn't be determined.

    Note: this works on audio files in just about any format (unlike
    mu_flacFileDurationInSeconds()).

    Note: our result can be a float.

    See mu_allFlacAlbumTracksDurationsInSeconds().
    """
    #mu_debug("---> mu_durationInSeconds(%s)" % path)
    assert path is not None
    result = -1
    cmd = _mu_ffprobeTrackInformationCmdFmt % path
    #mu_debug("    cmd = [%s]" % cmd)
    info = ut.ut_executeShellCommand(cmd)
    if info is not None:
        #mu_debug("    info is not None")
        for line in info.splitlines():
            line = line.strip()
            #mu_debug("    line = [%s]" % line)
            if line.startswith("Duration: "):
                #mu_debug("    found duration line")
                parts = line.split(", ", 1)
                #mu_debug("    num parts = %i" % len(parts))
                if len(parts) > 0:
                    res = parts[0]
                    #mu_debug("    res = [%s]" % res)
                    parts = res.split(": ", 1)
                    #mu_debug("    num subparts = %i" % len(parts))
                    if len(parts) > 0:
                        res = parts[1].strip()
                        #mu_debug("    res = [%s]" % res)
                        result = _mu_convertSexagesimalDurationToSeconds(res)
    assert result >= -1
    #mu_debug("    result = %s" % str(result))
    return result

def mu_allFlacAlbumTracksDurationsInSeconds(albumFile, cueFile):
    """
    Returns a list of integers, where the 'i''th item in the list is:
        - the duration, in seconds, of the 'i''th track on the album
          represented by the album FLAC file with pathname 'albumFile' and
          the corresponding CUE file with pathname 'cueFile', or
        - -1 if the track's duration couldn't be determined
    or returns None if the album's breakpoints couldn't be obtained from
    'cueFile'.

    See mu_durationInSeconds().
    """
    #mu_debug("---> mu_allFlacAlbumTracksDurationsInSeconds(%s, %s)" % (albumFile, cueFile))
    assert albumFile is not None
    assert cueFile is not None
    breakpoints = _mu_flacCueFileBreakpoints(cueFile)
    if breakpoints is None:
        result = None
    else:
        numTracks = len(breakpoints) + 1
        #mu_debug("    # tracks = %i" % numTracks)
        albumLen = mu_durationInSeconds(albumFile)
        #mu_debug("    album duration = %s" % str(albumLen))
        if numTracks == 1:
            result = [albumLen]
        else:
            v = _mu_flacCueFileBreakpointToSeconds(breakpoints[0])
            result = [v]
                # the length of the first track is the first breakpoint in
                # seconds
            for i in range(1, numTracks - 1):
                v1 = _mu_flacCueFileBreakpointToSeconds(breakpoints[i - 1])
                v2 = _mu_flacCueFileBreakpointToSeconds(breakpoints[i])
                if v1 < 0 or v2 < 0:
                    res = -1
                else:
                    # Note: the 'max()' call shouldn't be necessary, but it
                    # handles incorrect/inaccurate CUE file breakpoints more
                    # sociably.
                    res = max(v2 - v1, 0)
                        # the 'i''th track's duration is the ('i'+1)th
                        # breakpoint in seconds minus the 'i''th breakpoint
                        # in seconds (except for the first and last track)
                        #
                    assert res >= 0
                result.append(res)
            res = -1
            if albumLen >= 0:
                v1 = _mu_flacCueFileBreakpointToSeconds(breakpoints[-1])
                if v1 >= 0:
                    # Note: the 'max()' call shouldn't be necessary, but it
                    # handles incorrect/inaccurate CUE file breakpoints (as
                    # well as possible differences in calculating the album
                    # length and the breakpoint in seconds) more sociably.
                    res = max(albumLen - v1, 0)
                        # the last track's duration is the entire album's
                        # duration minus the last breakpoint in seconds
                    assert res >= 0
            result.append(res)  # last track's duration
        #mu_debug("    result = [%s]" % ", ".join([str(x) for x in result]))
        assert result is not None
        assert len(result) == numTracks
    # 'result' can be None
    return result

def mu_flacFileDurationInSeconds(path):
    """
    Returns the duration, in seconds, of the FLAC audio file with pathname
    'path', or -1 if the duration couldn't be determined.

    See mu_durationInSeconds().
    """
    assert path is not None
    result = -1
    numSamples = mu_totalSamplesInFlacFile(path)
    if numSamples >= 0:
        rate = mu_flacFileSampleRate(path)
        if rate > 0:  # '>' avoids dividing by zero too
            result = numSamples / float(rate)
    assert result >= 0.0 or result == -1
    return result

def mu_totalSamplesInFlacFile(path):
    """
    Returns the total number of samples in the FLAC file with pathname 'path',
    or -1 if the total number of samples couldn't be obtained. The result is
    an int.
    """
    assert path is not None
    cmd = _mu_flacTotalSamplesCmdFmt % path
    result = ut.ut_executeShellCommand(cmd)
    if result is None:
        result = -1
    else:
        try:
            result = int(result)
        except ValueError:
            result = -1
    assert result >= -1
    return result

def mu_flacFileSampleRate(path):
    """
    Returns the sample rate for the FLAC file with pathname 'path', or -1 if
    the sample rate couldn't be obtained. The result is an int.
    """
    assert path is not None
    cmd = _mu_flacSampleRateCmdFmt % path
    result = ut.ut_executeShellCommand(cmd)
    if result is None:
        result = -1
    else:
        try:
            result = int(result)
        except ValueError:
            result = -1
    assert result >= -1
    return result

def mu_allAlbumTrackInformation(albumFile, cueFile):
    """
    Returns a list of (trackNumber, title, artist) triples, one for each
    track on the album represented by the album FLAC and CUE files with
    pathnames 'albumFile' and 'cueFile', respectively, or returns None if
    some or all of the track information couldn't be obtained (or at least
    set to a default value). The 'i''th triple in the returned list contains
    information about the album's ('i'+1)th track.

    Note: the track number in each triple is a positive int: it hasn't been
    formatted with any leading zeroes. (Use mu_formatTrackNumber() to format
    them).

    See mu_formatTrackNumber().
    """
    assert albumFile is not None
    assert cueFile is not None
    result = None
    cmd = _mu_flacAlbumTrackTitlesCmdStart % cueFile
    titles = ut.ut_executeShellCommand(cmd)
    if titles is not None:
        result = []
        titles = titles.splitlines()
        if mu_isMultipleArtistAlbumFile(albumFile, cueFile):
            # Each title contains the track title and artist.
            sep = mu_artistTitleSep
            num = 0
            for t in titles:
                num += 1
                (artist, foundSep, t) = t.partition(sep)
                if foundSep != sep:
                    # Couldn't parse the artist name out of the title.
                    t = artist  # = all of original 'title'
                    artist = mu_unknownArtistName
                info = (num, t, artist)
                result.append(info)
        else:  # each track has the same artist
            artist = mu_albumArtistNameFromCueFile(cueFile)
            num = 0
            for t in titles:
                num += 1
                info = (num, t, artist)
                result.append(info)
    # 'result' may be None
    return result

def mu_trackTitleAndArtistFromCueFile(albumFile, cueFile, trackNumber):
    """
    Returns the title and artist name for the 'trackNumber'th track of the
    album represented by the album FLAC file with pathname 'albumFile' and
    CUE file with pathname 'cueFile'. One or both components of the returned
    pair will be None if a proper value can't be determined for them.

    See mu_allAlbumTrackInformation().
    """
    assert trackNumber > 0
    assert albumFile is not None
    assert cueFile is not None
    title = _mu_trackTitleFromCueFile(cueFile, trackNumber)
    if title is None:
        artist = None
    else:
        if mu_isMultipleArtistAlbumFile(albumFile, cueFile):
            sep = mu_artistTitleSep
            (artist, foundSep, title) = title.partition(sep)
            if foundSep != sep:
                # Couldn't parse the artist name out of the title.
                title = artist  # = all of original 'title'
                artist = None
        else:
            artist = mu_albumArtistNameFromCueFile(cueFile)
    result = (title, artist)
    assert result is not None
    assert len(result) == 2
    # none, one or both of result[0] and result[1] may be None
    return result

def mu_isMultipleArtistAlbumFile(albumFile, cueFile):
    """
    Returns True iff the album represented by the album FLAC file with
    pathname 'albumFile' and the corresponding CUE file with pathname
    'cueFile' has tracks by different artists.
    """
    assert albumFile is not None
    assert cueFile is not None
    return albumFile.endswith(_mu_variousArtistsFilenameEnd)

def _mu_trackTitleFromCueFile(cueFile, trackNumber):
    """
    Returns the title of the 'trackNumber'th track in the CUE file with
    pathname 'cueFile', or returns None if the title couldn't be obtained or
    there's no 'trackNumber'th track in 'cueFile'.

    See mu_allAlbumTrackInformation().
    """
    assert cueFile is not None
    assert trackNumber > 0
    cmd = '%s -n %i -t "%s" "%s"' % \
            (_mu_cueprintCommand, trackNumber, '%t', cueFile)
    result = ut.ut_executeShellCommand(cmd)
    # 'result' may be None
    return result

def mu_albumArtistNameFromCueFile(cueFile):
    """
    Returns the artist name of the album that the CUE file with pathname
    'cueFile' represents, or returns None if the artist name couldn't be
    obtained.

    See mu_allAlbumTrackInformation().
    """
    assert cueFile is not None
    cmd = '%s -d "%s" "%s"' % (_mu_cueprintCommand, '%P', cueFile)
    result = ut.ut_executeShellCommand(cmd)
    # 'result' may be None
    return result

def mu_trackCountFromCueFile(cueFile):
    """
    Returns the total number of tracks on the album represented by the CUE
    file with pathname 'cueFile', or returns 0 if the number of tracks
    couldn't be determined.

    See mu_allAlbumTrackInformation().
    """
    result = 0
    assert cueFile is not None
    cmd = '%s -d "%s" "%s"' % (_mu_cueprintCommand, '%N', cueFile)
    res = ut.ut_executeShellCommand(cmd)
    if res is not None:
        result = ut.ut_tryToParseInt(res, 0, minValue = 1)
    # 'result' may be None
    assert result >= 0
    return result

def mu_formatTrackNumber(trackNum):
    """
    Formats the track number 'trackNum' as a string.
    """
    assert trackNum > 0
    result = "%02i" % trackNum
    assert result
    return result


def mu_hasMusicFilename(f):
    """
    Returns True iff the pathname or filename is that of a music file that
    we recognize and can handle.
    """
    return mu_hasFlacFilename(f) or mu_hasMp3Filename(f)

def mu_tagsMap(musicFile, defValue = None, useCommonTags = True):
    """
    Returns a map from the name of each of the tags on the file with
    pathname 'musicFile' to their value, or returns 'defValue' if we
    don't recognize 'musicFile' as a music file (including if it isn't
    an existing non-directory file).

    'result' will use tag names for common tags that are the same across
    all types of music files if 'useCommonTags' is True: otherwise the
    type-specific tag names will be used in 'result'.
    """
    assert musicFile is not None
    result = None
    if os.path.exists(musicFile) and not os.path.isdir(musicFile):
        if mu_hasFlacFilename(musicFile):
            result = mu_flacTagsMap(musicFile)
            assert result is not None
        elif mu_hasMp3Filename(musicFile):
            result = mu_mp3TagsMap(musicFile)
            if useCommonTags:
                result = mu_convertMp3ToFlacTagNameMap(result)
            assert result is not None
        elif mu_hasOggFilename(musicFile):
            result = mu_oggTagsMap(musicFile)
            if useCommonTags:
                result = mu_convertOggToFlacTagNameMap(result)
            assert result is not None
# TODO: ADD CODE HERE TO HANDLE OTHER MUSIC FILE TYPES !!!
    if result is None:
        result = defValue
    assert defValue is None or result is not None
    return result

def mu_copyFlacTags(srcFile, destFile):
    """
    Copies the tags of the FLAC file with pathname 'srcFile' into the FLAC
    file with pathname 'destFile'.

    Returns True iff all of the tags are successfully copied.
    """
    assert srcFile is not None
    assert destFile is not None

    # metaflac --export-tags-to=- ${srcFile} | \
    #   metaflac --import-tags-from=- ${destFile}
    mfc = _mu_metaflacCommand
    fmt = '%s --export-tags-to=- "%s" | %s --import-tags-from=- "%s"'
    cmd = fmt % (mfc, srcFile, mfc, destFile)
    result = (ut.ut_executeShellCommand(cmd) is not None)
    return result

def mu_setFlacTag(flacFile, tagName, tagValue):
    """
    Sets the value of the tag named 'tagName' on the FLAC file with pathname
    'flacFile' so that its value is 'tagValue', replacing any existing value
    for that tag.

    Returns True iff the tag is successfully set.
    """
    assert flacFile is not None
    assert tagName is not None
    assert tagValue is not None
    mfc = _mu_metaflacCommand
    fmt = '%s --remove-tag=%s --set-tag="%s=%s" "%s"'
    cmd = fmt % (mfc, tagName, tagName, tagValue, flacFile)
    result = (ut.ut_executeShellCommand(cmd) is not None)
    return result

def mu_flacTagsMap(flacFile):
    """
    Returns a map from the name of each of the tags on the FLAC file with
    pathname 'flacFile' to their value.
    """
    #print "---> in mu_flacTagsMap(%s)" % flacFile
    assert flacFile is not None
    cmd = '%s --export-tags-to=- "%s"' % (_mu_metaflacCommand, flacFile)
    #print "    executing command [%s]" % cmd
    flacTags = ut.ut_executeShellCommand(cmd)
    #print "    flacTags = [%s]" % flacTags
    result = {}
    if flacTags is not None:
        #print "    command succeeded"
        sep = _mu_exportedFlacTagNameValueSeparator
        #print "    sep = [%s]" % sep
        for line in flacTags.splitlines():
            #print "    exported line = [%s]" % line
            (name, junk, value) = line.partition(sep)
            #print "    parsing exported line: name = [%s], value = [%s]" % (name, value)
            if name and value:
                # Ignore tags with no value. Later instances of the same tag
                # replace earlier ones.
                #print "    adding mapping to map"
                result[name] = value
    assert result is not None
    return result

def mu_flacAlbumTrackTagsMap(albumFile, cueFile, trackNumber):
    """
    Returns a map from the names to the values of each of the tags that would
    be on a FLAC file that represents the 'trackNumber'th track on the album
    represented by the album FLAC file with pathname 'albumFile' and the CUE
    file with pathname 'cueFile'.

    Note: this method will NOT cause a FLAC file for the track to be
    generated.
    """
    #print "---> in mu_flacTagsMap(%s)" % flacFile
    assert albumFile is not None
    assert cueFile is not None
    assert trackNumber > 0
    result = mu_flacTagsMap(albumFile)
    (title, artist) = mu_trackTitleAndArtistFromCueFile(albumFile, cueFile,
                                                        trackNumber)
    if artist is not None:
        result[mu_flacArtistTag] = artist
    if title is None:
        title = ""
    result[mu_flacTrackTitleTag] = title
    result[mu_flacTrackNumberTag] = mu_formatTrackNumber(trackNumber)
    assert result is not None
    return result


def mu_convertMp3ToFlacTagNameMap(m):
    """
    Returns the result of converting the MP3 tags map 'm' into a FLAC
    tags map by substituting each of the keys in 'm' that are common
    MP3 tag names with the corresponding FLAC tag names, and leaving any
    others unchanged.
    """
    nameMap = _mu_mp3TagNameToFlacTagNameMap
    result = {}
    for (k, v) in m.items():
        newKey = nameMap.get(k, k)
        result[newKey] = v
    assert result is not None
    assert len(result) == len(m)
    return result

def mu_mp3TagsMap(mp3File):
    """
    Returns a map from the name of each of the tags on the MP3 file with
    pathname 'mp3File' to their value.
    """
    #print "---> in mu_mp3TagsMap(%s)" % mp3File
    assert mp3File is not None
    cmd = '%s -l "%s"' % (_mu_id3v2Command, mp3File)
    #print "    executing command [%s]" % cmd
    mp3Tags = ut.ut_executeShellCommand(cmd)
    #print "    mp3Tags = [%s]" % mp3Tags
    result = {}
    if mp3Tags is not None:
        #print "    command succeeded"
        sep = _mu_exportedMp3TagNameValueSeparator
        #print "    sep = [%s]" % sep

        # The first line (if there is one) is a header line, so we skip it.
        for line in mp3Tags.splitlines()[1:]:
            #print "    exported line = [%s]" % line
            (name, junk, value) = line.partition(sep)
            #print "    parsing exported line: name = [%s], value = [%s]" % (name, value)
            if name and value:
                # Ignore tags with no value. Later instances of the same tag
                # replace earlier ones.
                #print "    adding mapping to map"
                result[name] = value
    assert result is not None
    return result

def mu_convertOggToFlacTagNameMap(m):
    """
    Returns the result of converting the OGG tags map 'm' into a FLAC
    tags map by substituting each of the keys in 'm' that are common
    OGG tag names with the corresponding FLAC tag names, and leaving any
    others unchanged.
    """
    result = m  # since OGG tags and FLAC tags are the same
    assert result is not None
    assert len(result) == len(m)
    return result

def mu_oggTagsMap(oggFile):
    """
    Returns a map from the name of each of the tags on the OGG file with
    pathname 'oggFile' to their value.
    """
    #print "---> in mu_oggTagsMap(%s)" % oggFile
    assert oggFile is not None
    cmd = '%s -l "%s"' % (_mu_vorbiscommentCommand, oggFile)
    #print "    executing command [%s]" % cmd
    oggTags = ut.ut_executeShellCommand(cmd)
    #print "    oggTags = [%s]" % oggTags
    result = {}
    if oggTags is not None:
        #print "    command succeeded"
        sep = _mu_exportedOggTagNameValueSeparator
        #print "    sep = [%s]" % sep
        for line in oggTags.splitlines():
            #print "    exported line = [%s]" % line
            (name, junk, value) = line.partition(sep)
            #print "    parsing exported line: name = [%s], value = [%s]" % (name, value)
            if name and value:
                # Ignore tags with no value. Later instances of the same tag
                # replace earlier ones.
                #print "    adding mapping to map"
                result[name] = value
    assert result is not None
    return result


def mu_buildLameTagOptionsFromFlacTagMap(flacTagMap):
    """
    Returns a string containing options to the 'lame' MP3 encoder that set
    an MP3 file's tags to the corresponding tags in 'flacTagMap', a map of
    the names of the tags on a FLAC file to their values.

    Note: not all of the tags in 'flacTagMap' will necessarily be used: only
    the ones corresponding to the standard MP3 tags will be used.
    """
    #print "---> in mu_buildLameTagOptionsFromFlacTagMap(%s)" % repr(flacTagMap)
    assert flacTagMap is not None
    tagToOptionMap = _mu_flacTagNameToLameOptionNameMap
    parts = []
    for (k, v) in flacTagMap.items():
        optName = tagToOptionMap.get(k)
        if optName is not None:
            parts.append('%s "%s"' % (optName, mu_escapedTagValue(v)))
    result = " ".join(parts)
    assert result is not None
    return result


# Uncomment this when we need to debug/trace this module's functions (in
# which case use the 'mu_debug()' function).
#def _fs_buildLog():
#    """
#    Builds and returns an open file object on the file to log information to.
#    """
#    #print "---> in _fs_buildLog()"
#    path = "~/log/music.py.log"
#    path = ut.ut_expandedAbsolutePathname(path)
#    assert path is not None
#    result = open(path, "w")
#    assert result is not None
#    return result
#
#_fs_log = _fs_buildLog()
#
#def mu_debug(msg):
#    """
#    Logs the debugging message 'msg', if we're logging debugging messages.
#    """
#    #print "---> in mu_debug(%s)" % msg
#    print >> _fs_log, msg
#    _fs_log.flush()


def _mu_appendRedirectToFileSuffix(cmd, path):
    """
    Returns the result of appending to the shell command 'cmd' a suffix that
    redirects the command's standard output to the file with pathname 'path'.
    """
    assert path is not None
    result = '%s > "%s"' % (cmd, path)
    assert result is not None
    return result

def mu_escapedTagValue(txt):
    """
    Returns the value 'txt' of a music file tag with all characters that
    need to be escaped escaped.
    """
    assert txt is not None
    result = txt.replace('"', '\\"')
    assert result is not None
    return result

def _mu_convertSexagesimalDurationToSeconds(d):
    """
    Converts the string 'd' - which is assumed to represent a duration in the
    format 'HH:MM:SS[.mm]' - into the corresponding number of seconds, or
    returns -1 if 'd' isn't in the required format.

    Note: our result can be a float.
    """
    #mu_debug("in _mu_convertSexagesimalDurationToSeconds(%s)" % d)
    assert d is not None
    result = -1
    parts = d.split(":")
    if len(parts) == 3:
        parts.reverse()  # in place
        m = 1
        result = 0
        try:
            for p in parts:
                result += (float(p) * m)
                m *= 60
        except ValueError:
            result = -1
    assert result is not None
    assert result == -1 or result >= 0
    #mu_debug("    result = %s" % str(result))
    return result

def _mu_flacCueFileBreakpoints(cueFile):
    """
    Returns a list of the breakpoints in the cue file with pathname
    'cueFile', or None if they couldn't be obtained.
    """
    assert cueFile is not None
    cmd = "%s '%s'" % (_mu_cuebreakpointsCommand, cueFile)
    result = ut.ut_executeShellCommand(cmd)
    if result is not None:
        result = result.splitlines()
    # 'result' may be None
    return result

def _mu_flacCueFileBreakpointToSeconds(br):
    """
    Returns the result of converting the FLAC cue file breakpoint 'br' to
    the corresponding number of seconds, or returns -1 if the conversion
    could not be done (likely because the format of 'br' is invalid).

    Note: 'br' is assumed to be in the same format as one of the items in a
    list returned by _mu_flacCueFileBreakpoints().
    """
    #mu_debug("---> in _mu_flacCueFileBreakpointToSeconds(self, [%s]) ..." % br)
    assert br is not None
    parts = br.split(":")
    #mu_debug("    parts = [%s]" % parts)
    assert parts
    if not ut.ut_areAllNumbers(parts):
        #mu_debug("    not all parts are numbers")
        result = -1
    else:
        parts = [float(x) for x in parts]
        #mu_debug("    all parts are numbers")
        result = 0.0
        #mu_debug("    reversing 'parts'")
        parts.reverse()
        #mu_debug("    parts = [%s]" % parts)
        factor = 1.0
        for p in parts:
            #mu_debug("    p = %s, factor = %s" % (p, factor))
            assert p >= 0
            result += (p * factor)
            factor *= 60.0
            #mu_debug("    p = %s, result = %s" % (p, result))
    #mu_debug("    result = %s" % result)
    assert result >= -1
    return result


class mu_AlbumTrackExtractor(object):
    """
    The interface implemented by classes that extract a single track from
    an audio file that represents a whole album.
    """

    def mu_createShellCommand(self, albumFile, metadataFile, trackNum,
                                 title, artist):
        """
        Returns a string containing the shell command (line) that outputs to
        its standard output the contents of the per-track audio file for the
        'trackNum''th track on the album represented by the album audio file
        with pathname 'albumFile' and optionally an associated metadata file
        with pathname 'metadataFile'; or returns None if the command can't be
        generated.

        The command will add the appropriate tahs to the per-track audio
        file, including setting the title to 'title', the artist to 'artist'
        and the track number to (a properly formatted) 'trackNum'.
        """
        assert albumFile is not None
        # 'metadataFile' may be None
        assert trackNum > 0
        assert title is not None
        assert artist is not None
        # 'result' may be None
        raise NotImplementedError

class mu_FallbackAlbumTrackExtractor(mu_AlbumTrackExtractor):
    """
    The class of album track extractor that tries to use its primary
    extractor to extract a track, but if that fails uses its backup
    extractor (if it has one).
    """

    def __init__(self, primary, backup):
        assert primary is not None
        # 'backup' may be None
        mu_AlbumTrackExtractor.__init__(self)
        self._mu_primary = primary
        self._mu_backup = backup

    def mu_createShellCommand(self, albumFile, metadataFile, trackNum,
                                 title, artist):
        assert albumFile is not None
        # 'metadataFile' may be None
        assert trackNum > 0
        assert title is not None
        assert artist is not None
        result = self._mu_primary.mu_createShellCommand(albumFile,
                                    metadataFile, trackNum, title, artist)
        if result is None and self._mu_backup is not None:
            #mu_debug("Falling back to backup mu_AlbumTrackExtractor")
            result = self._mu_backup.mu_createShellCommand(albumFile,
                                    metadataFile, trackNum, title, artist)
        # 'result' may be None
        return result

class mu_AbstractFlacAlbumTrackExtractor(mu_AlbumTrackExtractor):
    """
    An abstract base class for album track extractors that extract a single
    track - in FLAC format - from a FLAC audio file that represents a whole
    album.
    """

    def mu_createShellCommand(self, albumFile, metadataFile, trackNum,
                              title, artist):
        """
        Returns a string containing the shell command (line) that outputs to
        its standard output the contents of the per-track audio file for the
        'trackNum''th track on the album represented by the album audio file
        with pathname 'albumFile' and optionally an associated metadata file
        with pathname 'metadataFile'; or returns None if the command can't be
        generated.

        The command will add the appropriate tags to the per-track audio
        file, including setting the title to 'title', the artist to 'artist'
        and the track number to (a properly formatted) 'trackNum'.
        """
        #mu_debug("---> mu_createShellCommand(self, [%s], [%s], [%s], [%s], [%s]" % (albumFile, metadataFile, str(trackNum), title, artist))
        assert albumFile is not None
        # 'metadataFile' may be None
        assert trackNum > 0
        assert title is not None
        assert artist is not None

        result = None
        if metadataFile is not None:
            result = self._mu_reallyCreateShellCommand(albumFile,
                                metadataFile, trackNum, title, artist)
        # 'result' may be None
        return result

    def _mu_reallyCreateShellCommand(self, albumFile, cueFile, trackNum,
                                     title, artist):
        """
        See mu_AlbumTrackExtractor.mu_createShellCommand().
        """
        assert albumFile is not None
        assert cueFile is not None
        assert trackNum > 0
        assert title is not None
        assert artist is not None
        # 'result' may be None
        raise NotImplementedError

class mu_DefaultFlacAlbumTrackExtractor(mu_AbstractFlacAlbumTrackExtractor):
    """
    The class of album track extractor that extract a single track - in FLAC
    format - from a FLAC audio file that represents a whole album, where the
    extraction is done using the default/reference 'flac' program.
    """

    def _mu_reallyCreateShellCommand(self, albumFile, cueFile, trackNum,
                                     title, artist):
        assert albumFile is not None
        assert cueFile is not None
        assert trackNum > 0
        assert title is not None
        assert artist is not None
        #mu_debug("---> in mu_DefaultFlacAlbumTrackExtractor._mu_reallyCreateShellCommand(self, [%s], [%s], %i, [%s], [%s]) ..." % (albumFile, cueFile, trackNum, title, artist))
        result = self._mu_rangeOptions(cueFile, trackNum)
        if result is not None:
            m = mu_flacTagsMap(albumFile)
            m[mu_flacTrackTitleTag] = title
            m[mu_flacArtistTag] = artist
            m[mu_flacTrackNumberTag] = mu_formatTrackNumber(trackNum)
            tagOpts = ['-T "%s=%s"' %
                (k, mu_escapedTagValue(v)) for (k, v) in m.items()]
            result = _mu_defaultFlacAlbumToTrackCmdFmt % (result, albumFile,
                                                          ' '.join(tagOpts))
            #mu_debug("result = '%s'" % result)
        # 'result' may be None
        return result

    def _mu_rangeOptions(self, cueFile, trackNum):
        """
        Returns the options to pass to the 'flac' command to extract the
        'trackNum''th track from the album FLAC file whose associated CUE
        file has the pathname 'cueFile', or None if the range options
        couldn't be built.
        """
        assert cueFile is not None
        assert trackNum > 0
        result = None
        breaks = _mu_flacCueFileBreakpoints(cueFile)
        if breaks is not None:
            numBreaks = len(breaks)
            if trackNum == 1:
                result = "--until %s" % breaks[0]
            elif trackNum == numBreaks + 1:
                result = "--skip %s" % breaks[-1]
            else:
                assert trackNum > 1
                assert trackNum <= numBreaks
                result = "--skip %s --until %s" % \
                    (breaks[trackNum - 2], breaks[trackNum - 1])
        # 'result' may be None
        return result

class mu_FfmpegFlacAlbumTrackExtractor(mu_AbstractFlacAlbumTrackExtractor):
    """
    The class of album track extractor that extract a single track - in FLAC
    format - from a FLAC audio file that represents a whole album, where the
    extraction is done using the 'ffmpeg' program.
    """

    def _mu_reallyCreateShellCommand(self, albumFile, cueFile, trackNum,
                                     title, artist):
        assert albumFile is not None
        assert cueFile is not None
        assert trackNum > 0
        assert title is not None
        assert artist is not None
        #mu_debug("---> in mu_FfmpegFlacAlbumTrackExtractor._mu_reallyCreateShellCommand(self, [%s], [%s], %i, [%s], [%s]) ..." % (albumFile, cueFile, trackNum, title, artist))
        result = self._mu_rangeOptions(cueFile, trackNum)
        if result is not None:
            assert len(result) == 2
            result = _mu_ffmpegFlacAlbumToTrackCmdFmt % (result[0],
                albumFile, result[1], title, mu_formatTrackNumber(trackNum))
            #mu_debug("result = '%s'" % result)
        # 'result' may be None
        return result

    def _mu_rangeOptions(self, cueFile, trackNum):
        """
        Returns the pair of options to pass to the 'ffmpeg' command to
        specify the starting position and duration, respectively, of the
        'trackNum''th track from the album FLAC file whose associated CUE
        file has the pathname 'cueFile'; or returns None if the range options
        couldn't be built. (Note that one of the options may be an empty
        string, in which case the option can be ignored.)
        """
        #mu_debug("---> in mu_FfmpegFlacAlbumTrackExtractor._mu_rangeOptions(self, [%s], %i) ..." % (cueFile, trackNum))
        assert cueFile is not None
        assert trackNum > 0
        result = None
        breaks = _mu_flacCueFileBreakpoints(cueFile)
        #mu_debug("    breaks (%i) = [%s]" % (len(breaks), ", ".join(breaks)))
        if breaks is not None:
            numBreaks = len(breaks)
            if trackNum == 1:
                secs = _mu_flacCueFileBreakpointToSeconds(breaks[0])
                #mu_debug("    secs = %s" % secs)
                if secs >= 0:
                    result = ["", "-t %s" % secs]
            elif trackNum == numBreaks + 1:
                secs = _mu_flacCueFileBreakpointToSeconds(breaks[-1])
                if secs >= 0:
                    result = ["-ss %s" % secs, ""]
            else:
                assert trackNum > 1
                assert trackNum <= numBreaks
                start = breaks[trackNum - 2]
                end = breaks[trackNum - 1]
                startSecs = _mu_flacCueFileBreakpointToSeconds(start)
                endSecs = _mu_flacCueFileBreakpointToSeconds(end)
                if startSecs < 0 or endSecs < 0 or startSecs > endSecs:
                    #mu_debug("invalid breakpoint: startSecs = %s, endSecs = %s" % (startSecs, endSecs))
                    assert result is None
                else:
                    result = ["-ss %s" % startSecs,
                              "-t %s" % (endSecs - startSecs)]
        # 'result' may be None
        assert result is None or len(result) == 2
        return result


class mu_TrackConverter(object):
    """
    The interface implemented by classes that convert an audio file that
    represents a track into an audio file of (usually) different format that
    represents the same track.

    Note: while the audio files being converted usually represent tracks,
    subclasses can usually also be used to convert arbitrary audio files
    (including ones that represent entire albums). But they will generally
    only convert entire audio files.
    """

    def mu_createShellCommand(self, srcFile, bitrate):
        """
        Returns a string containing the shell command (line) that outputs to
        its standard output the contents of the audio file that is the result
        of converting the audio file with pathname 'srcFile' to the format
        that we convert audio files to; or returns None if the command can't
        be generated.

        If 'bitrate' is zero then a lossless conversion will be performed if
        possible; otherwise if 'bitrate' is greater than zero then a lossy
        conversion will be performed if possible, resulting in an audio file
        with a bitrate of 'bitrate' kilobits per second. If it is not
        possible to perform the conversion specified by 'bitrate' then this
        method will return None.
        """
        assert srcFile is not None
        assert bitrate >= 0
        # 'result' can be None
        raise NotImplementedError

class mu_FallbackTrackConverter(mu_TrackConverter):
    """
    The class of track converter that tries to use its primary converter to
    convert a track, but if that fails uses its backup converter (if it has
    one).
    """

    def __init__(self, primary, backup):
        assert primary is not None
        # 'backup' may be None
        mu_TrackConverter.__init__(self)
        self._mu_primary = primary
        self._mu_backup = backup

    def mu_createShellCommand(self, srcFile, bitrate):
        assert srcFile is not None
        assert bitrate >= 0
        result = self._mu_primary.mu_createShellCommand(srcFile, bitrate)
        if result is None and self._mu_backup is not None:
            #mu_debug("Falling back to backup mu_TrackConverter")
            result = self._mu_backup.mu_createShellCommand(srcFile, bitrate)
        # 'result' can be None
        return result

class mu_AbstractFlacTrackConverter(mu_TrackConverter):
    """
    An abstract base class for track converters that convert audio files in
    FLAC format to another format.
    """
    pass

class mu_AbstractFlacToMp3TrackConverter(mu_AbstractFlacTrackConverter):
    """
    An abstract base class for track converters that convert audio files in
    FLAC format to MP3 files.
    """

    def mu_createShellCommand(self, srcFile, bitrate):
        assert srcFile is not None
        assert bitrate >= 0
        if bitrate > 0:
            result = self._mu_reallyCreateShellCommand(srcFile, bitrate)
        else:
            result = None
                # since there's no such thing as a lossless MP3
        # 'result' can be None
        return result

    def _mu_reallyCreateShellCommand(self, srcFile, bitrate):
        assert srcFile is not None
        assert bitrate > 0
        # 'result' can be None
        raise NotImplementedError

class mu_LameFlacToMp3TrackConverter(mu_AbstractFlacToMp3TrackConverter):
    """
    The class of track converter that converts FLAC audio files into MP3
    files using the 'lame' program.
    """

    def _mu_reallyCreateShellCommand(self, srcFile, bitrate):
        assert srcFile is not None
        assert bitrate > 0

        #mu_debug("---> in mu_LameFlacToMp3TrackConverter._mu_reallyCreateShellCommand(self, [%s], %i) ..." % (srcFile, bitrate))
        #mu_debug("    building opts to copy FLAC tags to the MP3")
        tagsMap = mu_flacTagsMap(srcFile)
        #mu_debug("        built tagsMap")
        commentsTag = mu_flacCommentTag
        if commentsTag not in tagsMap:
            #mu_debug("        no comment tag")
# TODO: add ReplayGain info to comment here !!!????!!!
            cddbId = tagsMap.get(mu_flacAlbumCddbTag)
            if cddbId is not None:
                tagsMap[mu_flacCommentTag] = "Album CDDB ID: %s" % cddbId
        #mu_debug("        building 'lame' options to set tags ...")
        tagOpts = mu_buildLameTagOptionsFromFlacTagMap(tagsMap)
        #mu_debug("        built options: [%s]" % tagOpts)

        result = _mu_lameFlacToMp3CmdFmt % (srcFile, tagOpts, bitrate)
        #mu_debug("result = '%s'" % result)
        assert result is not None  # stronger postcond
        return result

class mu_FfmpegFlacToMp3TrackConverter(mu_AbstractFlacToMp3TrackConverter):
    """
    The class of track converter that converts FLAC audio files into MP3
    files using the 'ffmpeg' program.
    """

    def _mu_reallyCreateShellCommand(self, srcFile, bitrate):
        #mu_debug("---> in mu_FfmpegFlacToMp3TrackConverter._mu_reallyCreateShellCommand(self, [%s], %i) ..." % (srcFile, bitrate))
        assert srcFile is not None
        assert bitrate > 0
        result = _mu_ffmpegFlacToMp3CmdFmt % (srcFile, bitrate)
        #mu_debug("result = '%s'" % result)
        assert result is not None  # stronger postcond
        return result

class mu_AbstractFlacToOggTrackConverter(mu_AbstractFlacTrackConverter):
    """
    An abstract base class for track converters that convert audio files in
    FLAC format to Ogg Vorbis files.
    """

    def mu_createShellCommand(self, srcFile, bitrate):
        assert srcFile is not None
        assert bitrate >= 0
        if bitrate > 0:
            result = self._mu_reallyCreateShellCommand(srcFile, bitrate)
        else:
            result = None
                # since there's no such thing as a lossless Ogg Vorbis file
        # 'result' can be None
        return result

    def _mu_reallyCreateShellCommand(self, srcFile, bitrate):
        assert srcFile is not None
        assert bitrate > 0
        # 'result' can be None
        raise NotImplementedError

class mu_OggEncFlacToOggTrackConverter(mu_AbstractFlacToOggTrackConverter):
    """
    The class of track converter that converts FLAC audio files into Ogg
    Vorbis files using the 'oggenc' program.
    """

    def _mu_reallyCreateShellCommand(self, srcFile, bitrate):
        assert srcFile is not None
        assert bitrate > 0
        #mu_debug("---> in mu_OggEncFlacToOggTrackConverter._mu_reallyCreateShellCommand(self, [%s], %i) ..." % (srcFile, bitrate))
        result = _mu_oggencFlacToOggCmdFmt % (bitrate, srcFile)
            # the tags from 'srcFile' - including the ReplayGain ones - are
            # automatically added to the Ogg file by default
        #mu_debug("result = '%s'" % result)
        assert result is not None  # stronger postcond
        return result

class mu_FfmpegFlacToOggTrackConverter(mu_AbstractFlacToOggTrackConverter):
    """
    The class of track converter that converts FLAC audio files into Ogg
    Vorbis files using the 'ffmpeg' program.
    """

    def _mu_reallyCreateShellCommand(self, srcFile, bitrate):
        #mu_debug("---> in mu_FfmpegFlacToOggTrackConverter._mu_reallyCreateShellCommand(self, [%s], %i) ..." % (srcFile, bitrate))
        assert srcFile is not None
        assert bitrate > 0
        result = _mu_ffmpegFlacToOggCmdFmt % (srcFile, bitrate)
        #mu_debug("result = '%s'" % result)
        assert result is not None  # stronger postcond
        return result
