#
# $Id: utilities.py,v 1.84 2013/09/26 18:34:15 jgm Exp $
#
# Defines functions and classes of general utility.
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

import cgi
import errno
import os
import os.path
import signal
import stat
import sys
import time

import getopt
import shutil
import socket
import tempfile
import traceback
import xml.sax
import xml.sax.saxutils


# Constants.

# A map of additional strings to escape when quoting text to convert it
# to valid XML.
_ut_addedXmlQuotingMap = { "'": "&apos;", '"': "&quot;" }

# The IP address of localhost (as a string).
_localhostIpAddress = "127.0.0.1"

# The mask to bitwise 'or' with a file mode to set any and all
# read/write/execute permissions (or whose inverse can be bitwise 'and'ed
# with a file mode to unset any and all read/write/execute permissions).
ut_readMask     = stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH
ut_writeMask    = stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH
ut_executeMask  = stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH

# The letters that indicate the units of an amount of (disk or memory) space,
# in order from smallest to largest starting with bytes.
_ut_spaceUnitsInOrder = "BKMGT"

# The multiple between consecutive units in _ut_spaceUnitsInOrder.
_ut_spaceUnitsMultiple = 1024


# External program pathnames.
_ut_festivalProgram = "festival"
_ut_espeakProgram = "espeak"
_ut_echoProgram = "echo"
_ut_sortProgram = "sort"
_ut_teeProgram = "tee"

#_ut_speakCmd = _ut_festivalProgram + ' --tts'
_ut_speakCmd = _ut_espeakProgram + ' -z -v default'

# The format of the command to use to speak text.
_ut_speakTextCommandFmt = _ut_echoProgram + ' "%s" | ' + _ut_speakCmd

# The format of the command returned by ut_teeShellCommand().
_ut_teeCommandFmt = _ut_teeProgram + ' "%s"'


# A ut_LeastRecentlyUsedCache's next update index is allowed to be at most
# this multiple times the cache's high size.
_ut_maxLruCacheUpdateIndexMultiple = 5


# Functions.

def ut_exceptionDescription():
    """
    Returns a string containing a description of the current exception.
    """
    (type, value, trace) = sys.exc_info()
    if type is not None:
        result = "an exception of class %s was raised: %s\n%s" % \
            (type, value, traceback.format_exc())
    else:
        assert value is None
        assert trace is None
        result = "no exception has been raised"
    assert result is not None
    return result

def ut_printCallStack():
    """
    Prints our caller's call stack to standard out
    """
    print(ut_callStack(1))

def ut_callStack(level = 0):
    """
    Returns a string containing our caller's call stack, starting 'level'
    levels above our caller's stack frame.
    """
    assert level >= 0
    result = ""
    areFrames = True
    i = level
    lines = []
    while areFrames:
        i += 1
        try:
            frame = sys._getframe(i)
        except ValueError:
            areFrames = False
        code = frame.f_code
        line = "%s:%s:%s(...)" % (code.co_filename,
                                  frame.f_lineno, code.co_name)
        lines.append(line)
    lines.reverse()
    result = "\n".join(lines)
    assert result is not None
    return result

def ut_localhostIpAddress():
    """
    Returns the IP address for localhost.
    """
    #assert result is not None
    return _localhostIpAddress

def ut_isLocalhost(hname):
    """
    Returns True iff the machine with hostname 'hname' is the localhost.
    """
    try:
        addr = ut_getHostByName(hname)
        result = (addr == _localhostIpAddress)
    except IOError as ex:
        # We assume that if we can't resolve 'hname' to an IP address then it
        # can be the localhost.
        result = False
    return result

def ut_getHostByName(hname):
    """
    Returns the IP address of the machine with hostname 'hname', raising an
    IOError if getting the address fails.

    See socket.gethostbyname().
    """
    assert hname is not None
    try:
        result = socket.gethostbyname(hname)
    except:
        raise IOError("ut_getHostByName() failed to resolve the host "
                      "name '%s'" % hname)
    assert result
    return result

def ut_updateMapByExecutingFile(path, m):
    """
    Updates the map 'm' by executing the Python source file with pathname
    'path'. Each assignment in the source file of a value 'val' to a global
    variable named 'name' updates 'm' with a mapping from 'name' to 'val'.

    Raises a SyntaxError iff there's one or more syntax errors in the source
    file, and raises an IOError if 'path' isn't the pathname of an existing
    regular file.
    """
    #print("===> ut_updateMapByExecutingFile(%s, m) ..." % path )
    assert path is not None
    assert m is not None
    r = None
    content = None
    try:
        r = open(path, 'r')
        content = r.read()
    finally:
        ut_tryToCloseAll(r)
    if content is not None:
        content += "\n"  # in case it's missing from the file
        #print("    content = [%s]" % content)
        code = compile(content, path, 'exec')
        try:
            exec(code, m)
        except SyntaxError as ex:
            raise ex
        except Exception as ex:
            raise SyntaxError(ex)
    #print("    done: m = %s" % ut_prettyShortMap(m))


def ut_printableNow():
    """
    Returns a string that is a printable representation of the current
    date and time.

    Note: this method doesn't allow for any formatting of its result as it is
    intended for use in debugging.
    """
    result = time.asctime()
    assert result
    return result

def ut_prettyShortMap(m):
    """
    Returns a string representation of the map/dictionary 'm' that is
    fairly short (and of course usually omits most of its contents).
    """
    # 'm' may be None
    if m is None:
        result = "None"
    elif not m:
        result = "{}"
    else:
        (k, v) = m.items()[0]
        result = "{ %s: %s, ... [%i] }" % (k, v, len(m))
    assert result is not None
    return result

def ut_printableStat(st):
    """
    Returns a printable representation of the file stat object 'st'.
    """
    assert st is not None
    fmt = "%s(mode = %s, inode = %s, device = %s, #links = %s, uid = %s, " \
            "gid = %s, size = %s, atime = %s, mtime = %s, ctime = %s)"
    mode = st.st_mode
    if mode is not None:
        mode = "0%o" % mode
    at = time.ctime(st.st_atime)
    mt = time.ctime(st.st_mtime)
    ct = time.ctime(st.st_ctime)
    name = "[unknown]"
    try:
        name = type(st).__name__
    except:
        pass
    result = fmt % (name, mode, st.st_ino, st.st_dev, st.st_nlink,
                    st.st_uid, st.st_gid, st.st_size, at, mt, ct)
    assert result is not None
    return result

def ut_fileSize(path):
    """
    Returns the size of the file with pathname 'path', or -1 if the file's
    size couldn't be determined.
    """
    try:
        result = os.stat(path).st_size
    except:
        result = -1
    assert result >= -1
    return result

def ut_speak(txt):
    """
    Speaks the text 'txt', returning True iff successful.
    """
    res = ut_executeShellCommand(_ut_speakTextCommandFmt % txt)
    return (res is None)

def ut_sendCommandToFifo(cmd, path):
    """
    Sends/writes the (single-line) command 'cmd' to the FIFO with pathname
    'path', returning True iff the command was successfully written/sent.
    """
    assert cmd
    assert path is not None
    w = None
    try:
        w = open(path, 'w')
        w.write("%s\n" % cmd)
        result = True
    finally:
        ut_tryToCloseAll(w)
    return result


def ut_teeShellCommand(path):
    """
    Returns a string containing the shell command that will 'tee' its standard
    input into both its standard output and the file with pathname 'path'.
    """
    assert path is not None
    return _ut_teeCommandFmt % path

def ut_waitForChildProcessToTerminate(pid):
    """
    Waits - using waitpid() - for the child process with PID 'pid' to terminate
    (and not just stop, continue, etc.), blocking until it does terminate.

    If waiting fails an IOError will be raised.
    """
    assert pid > 0
    (p, status) = os.waitpid(pid, 0)
    if p < 0:
        raise IOError("Waiting for child process to terminate failed due to "
                      "an error")
    assert os.WIFEXITED(status) or os.WIFSIGNALED(status)

def ut_waitForAllExitedChildProcesses():
    """
    Waits for all child processes that have already exited (which prevents
    them from becoming zombies).

    Raises an IOError if an error occurs in waiting.
    """
    childPid = 1
    while childPid != 0:  # 0 => no child was reaped
        childPid = os.waitpid(-1, os.WNOHANG)  # -1 => any child process
        if childPid < 0:
            raise IOError("Waiting for exited child processes failed")


def ut_smartMatchKeys(k, m):
    """
    Attempts to find a match for the key 'k' among the keys of the map 'm'
    and returns a list of the (key, item) pairs corresponding to all of the
    matching keys.

    Matching keys are found in the following manner:

        - if 'k' is equal to one of 'm''s keys then it will be the only
          matching key (even if it's equal to the start of a longer key)
        - otherwise the matching keys are all of 'm''s keys that start
          with 'k': there may be zero, one or more such matching keys

    The order of the items in the returned list is undefined.
    """
    if k in m:
        result = [(k, m[k])]
    else:
        result = []
        for (key, val) in m.items():
            if key.startswith(k):
                result.append((key, val))
    assert result is not None
    return result

def ut_findAttribute(obj, name):
    """
    Returns the value of the attribute named 'name' on 'obj' if it has
    such an attribute, or returns None if it doesn't.

    Note: None is returned in the case when the attribute is present and
    has the value None, as well as when the attribute is absent: there is
    no way to distinguish the two cases.
    """
    #print("---> in ut_findAttribute(%s, %s)" % (str(obj), name))
    if hasattr(obj, name):
        result = getattr(obj, name)
    else:
        result = None
    # 'result' may be None
    return result

def ut_sortTuplesByItem(tuplesList, itemIndex):
    """
    Sorts the list of tuples 'tuplesList' in place by comparing the
    ('itemIndex'+1)th items in the tuples (using the global 'cmp()'
    function). (Each tuple must have at least ('itemIndex'+1) items in it.)
    """
    assert tuplesList is not None
    assert itemIndex >= 0
    f = lambda t1, t2: cmp(t1[itemIndex], t2[itemIndex])
    tuplesList.sort(f)

def ut_sortFileInPlace(path, fieldSep = None):
    """
    Sorts the file with pathname 'path' in place, returning True iff it's
    successfully sorted.

    The file is sorted line by line, with each line being broken up into
    fields with 'fieldSep' as the separator (or NUL ('\0') if 'fieldSep' is
    None). The i'th fields of two lines are compared to determine the lines'
    relative ordering, followed by the (i+1)'th field iff the i'th fields are
    equal for all i >= 1.
    """
    assert path is not None
    if fieldSep is None:
        fieldSep = "\\0"
    # Note: the sort 'info' page assures us that we can use the same file as
    # input and output (using the '-o' option) and the file will be sorted in
    # place.
    cmd = "%s -t '%s' -o '%s' '%s'" % (_ut_sortProgram, fieldSep, path, path)
    result = (ut_executeShellCommand(cmd) is not None)
    return result

def ut_quoteForXml(txt):
    """
    Returns the string 'txt' quoted for use in an XML document.
    """
    assert txt is not None
    result = xml.sax.saxutils.escape(txt, _ut_addedXmlQuotingMap)
    assert result is not None
    return result

def ut_quoteForXmlAttribute(txt):
    """
    Returns the string 'txt' quoted for use in an XML attribute's value.
    """
    assert txt is not None
    result = xml.sax.saxutils.quoteattr(txt, _ut_addedXmlQuotingMap)
    assert result is not None
    return result


def ut_quoteForStringFormat(txt):
    """
    Returns the string 'txt' quoted for use in a Python format string.
    """
    assert txt is not None
    result = txt.replace("%", "%%")
    assert result is not None
    return result


def ut_saxParseXmlFile(path, handler, errorHandler = None):
    """
    Parses the XML file with pathname 'path' using the SAX XML parser and the
    xml.sax.ContentHandler 'handler'. The xml.sax.ErrorHandler 'errorHandler'
    will be used as the error handler unless it's None, in which case the
    default error handler will be used.
    """
    p = xml.sax.make_parser()
    p.setContentHandler(handler)
    if errorHandler is not None:
        p.setErrorHandler(errorHandler)
    p.parse(path)

def ut_parsePortNumber(txt):
    """
    Tries to parse and return the port number (as an int) that the string
    'txt' represents, returning that int if it's successful and raising a
    ValueError if it isn't.
    """
    result = ut_parseInt(txt)
    if result < 0:
        raise ValueError("Negative port number: %i" % port)
    assert result >= 0
    return result

def ut_isInt(txt):
    """
    Returns True iff the string 'txt' is a valid textual representation of an
    int.
    """
    try:
        val = int(txt)
        result = True
    except:
        result = False
    return result

def ut_areAllNumbers(c):
    """
    Returns True iff all of the items in the list 'c' are valid
    representations of (real) numbers.
    """
    assert c is not None
    result = True
    for item in c:
        # Note that a real number is a valid representation of an int: it
        # will/would just be truncated to an int.
        if not ut_isInt(item):
            result = False
        break  # for
    return result

def ut_tryToParseInt(txt, default = None, minValue = None, maxValue = None):
    """
    Tries to parse and return the int value that the string 'txt' represents,
    returning that int if it's successful, and 'default' if it isn't or if

    - 'minValue' is not None and the int value is less than 'minValue', or
    - 'maxValue' is not None and the int value is greater than 'maxValue'.
    """
    assert txt is not None
    assert minValue is None or ut_isInt(minValue)
    assert maxValue is None or ut_isInt(maxValue)
    result = _ut_tryToParseInt(txt, default, minValue, maxValue)
    assert result is default or result is not None
    return result

def ut_parseInt(txt, minValue = None, maxValue = None):
    """
    Parses and returns the int value that 'txt' represents, returning that
    int if it's successful, and raising a ValueError if it isn't or if

    - 'minValue' is not None and the int value is less than 'minValue', or
    - 'maxValue' is not None and the int value is greater than 'maxValue'.
    """
    assert txt is not None
    assert minValue is None or ut_isInt(minValue)
    assert maxValue is None or ut_isInt(maxValue)
    result = _ut_tryToParseInt(txt, None, minValue, maxValue, isFatal = True)
    assert result is not None
    return result

def _ut_tryToParseInt(txt, default = None, minValue = None, maxValue = None,
                      isFatal = False):
    """
    Tries to parse and return the int value that the string 'txt' represents,
    returning that int if it's successful, and 'default' if it isn't or if

    - 'minValue' is not None and the int value is less than 'minValue', or
    - 'maxValue' is not None and the int value is greater than 'maxValue'.

    If 'isFatal' is True then a ValueError exception is thrown - with a
    suitable message - whenever 'default' would have been returned if
    'isFatal' were False.
    """
    assert txt is not None
    assert minValue is None or ut_isInt(minValue)
    assert maxValue is None or ut_isInt(maxValue)
    msg = None
    try:
        val = int(txt)
        if minValue is not None and val < minValue:
            msg = "'%i' is less than the minimum value '%i'" % \
                (val, minValue)
        if maxValue is not None and val > maxValue:
            msg = "'%i' is greater than the maximum value '%i'" % \
                (val, maxValue)
    except ValueError:
        msg = "'%s' is not an integer value" % txt
    if msg is None:
        result = val
    else:
        if isFatal:
            raise ValueError(msg)
        else:
            result = default
    assert result is default or result is not None
    return result

def ut_parseSpaceIntoBytes(val):
    """
    Parses 'val', which is supposed to specify an amount of (disk or memory)
    space into, returning the number of bytes it represents if successful and
    None otherwise.

    A valid value is of the form 'nnnU' where 'nnn' is a nonnegative integer
    value (with any number of digits) and 'U' is one of these letters:

        'B' - bytes
        'K' - kilobytes (where 1 kilobyte = 1024 bytes)
        'M' - megabytes (where 1 megabyte = 1024 kilobytes)
        'G' - gigabytes (where 1 gigabyte = 1024 megabytes)
        'T' - terabytes (where 1 terabyte = 1024 gigabytes)
    """
    result = None
    if len(val) > 0:
        try:
            unit = val[-1]
            num = int(val[:-1])
            if num == 0:
                result = 0
            elif num > 0:
                mult = _ut_spaceUnitsMultiple
                unitIndex = _ut_spaceUnitsInOrder.index(unit)
                result = num
                for i in xrange(unitIndex):
                    result *= mult
        except:
            # Either 'unit' isn't a valid unit or 'num' isn't an integer
            result = None
    assert result is None or result >= 0
    return result

def ut_doUpdateFile(path, *dependenciesPaths):
    """
    Returns True iff the file with pathname 'path' either doesn't exist or
    is NOT strictly newer than one or more of the files with non-None
    pathnames in 'dependenciesPaths' that exist. (That is, None can be an
    item in 'dependenciesPaths', but all such items will be ignored.)
    """
    assert path is not None
    assert dependenciesPaths is not None  # assuming that's even possible
    result = not os.path.exists(path)
    if not result:
        pathMtime = os.path.getmtime(path)
        for dep in dependenciesPaths:
            if dep is not None and os.path.exists(dep):
                depMtime = os.path.getmtime(dep)
                if depMtime >= pathMtime:
                    result = True
                    break   # for dep
    return result


def ut_tryToMakeFileAllAccess(path):
    """
    Tries to make the file with pathname 'path' readable, writable and,
    iff the file is a directory, executable by everyone. Returns True if
    it's successful and False if it isn't.

    See ut_makeFileAllAccess().
    """
    result = True
    try:
        ut_makeFileAllAccess(path)
    except OSError:
        result = False
    return result

def ut_makeFileAllAccess(path):
    """
    Makes the file with pathname 'path' readable, writable and, iff the
    file is a directory, executable by everyone; otherwise an OSError is
    raised.

    See ut_tryToMakeFileAllAccess().
    """
    mode = ut_readMask | ut_writeMask
    if os.path.isdir(path):
        mode |= ut_executeMask
    os.chmod(path, mode)

def ut_makeFileUnwritable(path):
    """
    Makes the file with pathname 'path' unwritable by changing its access
    mode.
    """
    assert path is not None
    os.chmod(path, ut_unwritableFileMode(os.stat(path).st_mode))

def ut_unwritableFileMode(mode):
    """
    Returns the file mode 'mode' with any and all write permissions unset.
    """
    return mode & ~ut_writeMask

def ut_regularFileMode(perms):
    """
    Returns the file mode (as would be part of the result of 'os.stat()')
    for a regular file whose read/write/execute permissions are the integer
    'perms' (usually/traditionally specified in octal).
    """
    return perms | stat.S_IFREG

def ut_directoryMode(perms):
    """
    Returns the file mode (as would be part of the result of 'os.stat()')
    for a directory whose read/write/execute permissions are the integer
    'perms' (usually/traditionally specified in octal).
    """
    return perms | stat.S_IFDIR

def ut_symbolicLinkMode(perms):
    """
    Returns the file mode (as would be part of the result of 'os.stat()')
    for a symbolic link whose read/write/execute permissions are the integer
    'perms' (usually/traditionally specified in octal).
    """
    return perms | stat.S_IFLNK

def ut_fifoMode(perms):
    """
    Returns the file mode (as would be part of the result of 'os.stat()')
    for a FIFO whose read/write/execute permissions are the integer
    'perms' (usually/traditionally specified in octal).
    """
    return perms | stat.S_IFIFO


def ut_mountPoint(path):
    """
    Returns the pathname of the mount point of the device that the file
    with pathname 'path' is on: it may be 'path' itself. Returns None iff
    'path' is not the pathname of an existing file.
    """
    assert path is not None
    if os.path.lexists(path):
        result = ut_removeAnyPathnameSeparatorAtEnd(path)
        while not os.path.ismount(result):
            (result, fname) = os.path.split(result)
            assert fname  # i.e. we haven't gone 'past' the root dir
    else:
        result = None
    # 'result' may be None
    return result

def ut_createDirectory(path):
    """
    Creates the directory with pathname 'path' if it isn't an existing
    directory, creating any and all missing ancestor directories.
    """
    assert path is not None
    if not os.path.isdir(path):
        os.makedirs(path)

def ut_deleteAllEmptyDirectoriesUnder(path):
    """
    Deletes all of the empty directories under the directory with pathname
    'path', including ones that become empty as a result of this function's
    actions. (So - barring newly-added directories - there should be no empty
    directories under 'path' after this function is done, provided it doesn't
    raise an exception.)
    """
    assert path is not None
    if os.path.isdir(path):
        getNumComponents = lambda p: len(ut_pathnameComponents(p))
        numPathComps = getNumComponents(path)
        for (dirpath, dirnames, filenames) in os.walk(path):
            if not dirnames and not filenames:
                # 'dirpath' is empty: delete it and any and all ancestor
                # directories under 'path' that become empty.
                d = dirpath
                while True:
                    #print("delete %s" % d)
                    os.rmdir(d)
                    d = os.path.dirname(d)
                    numComps = getNumComponents(d)
                    if numComps <= numPathComps or len(os.listdir(d)) > 0:
                        break  # while
    # Otherwise there's nothing to do

def ut_deleteFileOrDirectory(path):
    """
    Deletes the file or directory with pathname 'path' iff it exists and
    'path' is not None.
    """
    #print("---> in ut_deleteFileOrDirectory(%s)" % path)
    # 'path' may be None
    if path is not None and os.path.lexists(path):
        #print("    file is not None and it exists")
        if os.path.isdir(path):
            #print("    file is a directory ...")
            os.rmdir(path)
            #print("    ... that was successfully removed")
        else:
            #print("    file is a non-directory ...")
            os.remove(path)
            #print("    ... that was successfully removed")

def ut_deleteTree(dir):
    """
    Deletes the directory with pathname 'dir' and everything under it:
    'dir' doesn't need to be empty.
    """
    shutil.rmtree(dir)

def ut_tryToDeleteAll(*paths):
    """
    Tries to delete all of the files and directories whose pathnames are
    non-None items in 'paths', returning True iff all of them are deleted.
    No exceptions thrown by the attempts to delete the files and directories
    are propagated, and deleting an earlier file or directory doesn't prevent
    us from attempting to delete later files and directories.
    """
    assert paths is not None
    result = True
    for p in paths:
        if p is not None:
            try:
                ut_deleteFileOrDirectory(p)
            except:
                result = False
    return result

def ut_createTemporaryFile(dir, prefix):
    """
    See tempfile.mkstemp(), except that the first item in the returned
    pair is a file object that allows one to write to the file.
    """
    res = tempfile.mkstemp(dir = dir, prefix = prefix)
    assert len(res) == 2
    result = (os.fdopen(res[0], 'w'), res[1])
    return result

def ut_createTemporaryDirectory(dir, prefix):
    """
    See tempfile.mkdtemp().
    """
    result = tempfile.mkdtemp(dir = dir, prefix = prefix)
    assert result is not None
    return result

def ut_isDirectoryFullyAccessible(dir):
    """
    Returns True iff the directory with pathname 'dir' is fully accessible:
    that is, can be read and searched (aka executed).
    """
    assert dir is not None
    access = os.R_OK or os.X_OK
    return os.access(dir, access)

def ut_isDirectoryFullyChangeable(dir):
    """
    Returns True iff the directory with pathname 'dir' is fully accessible:
    that is, can be read, written and searched (aka executed).
    """
    assert dir is not None
    access = os.R_OK or os.W_OK or os.X_OK
    return os.access(dir, access)

def ut_tryToCloseAll(*objs):
    """
    Calls the close() method on all of the objects in the list 'objs' that
    are not None, returning True iff all of the calls succeed. No exceptions
    thrown by the close() calls will be propagated to callers.
    """
    assert objs is not None
    result = True
    for obj in objs:
        if obj is not None:
            try:
                obj.close()
            except:
                result = False
    return result

def ut_really(path):
    """
    Returns the pathname of the file that the pathname 'path' really names:
    it follows every symlink in every component of 'path' recursively, after
    expanding 'path' into an expanded absolute pathname.

    See ut_expandedAbsolutePathname().
    """
    assert path is not None
    result = os.path.realpath(ut_expandedAbsolutePathname(path))
    assert result is not None
    return result

def ut_expandedAbsolutePathname(path):
    """
    Returns the absolute pathname of the pathname 'path' after expanding
    '~' and '~user' constructions.
    """
    assert path is not None
    result = os.path.abspath(os.path.expanduser(path))
    assert result is not None
    assert os.path.isabs(result)
    return result

def ut_absoluteToRelativePathname(path):
    """
    Returns 'path' as a relative pathname: that is, with any leading drive
    specifier and pathname separators removed.

TODO: TEST THIS !!!! (it hasn't been used yet).
    """
    assert path is not None
    (drive, result) = os.path.splitdrive(path)
    sep = os.sep
    sepLen = len(sep)
    while (result.startwith(sep)):
        result = result[sepLen:]
    assert result is not None
    assert not os.path.isabs(result)
    return result

def ut_doesEndWithPathnameSeparator(path):
    """
    Returns True iff 'path' ends with a pathname separator.
    """
    assert path is not None
    return path.endswith(os.sep)

def ut_removeAnyPathnameSeparatorAtEnd(path):
    """
    Returns 'path' with any pathname separator at the end of it removed.
    """
    assert path is not None
    sep = os.sep
    if path.endswith(sep):
        result = path[:-len(sep)]
    else:
        result = path
    assert result is not None
    return result

def ut_pathnameComponents(path, sep = None):
    """
    Returns the pathname components of the pathname 'path'. None of the
    components will be empty unless 'path' is empty or all of its characters
    are 'sep' (in which case there will be exactly one component, and it'll
    be an empty string).
    """
    assert path is not None
    assert sep is None or len(sep) == 1  # single char
    if sep is None:
        sep = os.sep
    result = path.strip(sep).split(sep)
    assert result is not None
    return result

def ut_hasPathnamePrefix(path, prefixPath):
    """
    Returns True iff the pathname 'path' starts with the pathname
    'prefixPath'.

    Note: 'prefixPath' will only match whole pathname components, so for
    example '/usr/bin' is a prefix of '/usr/bin' and '/usr/bin/there', but is
    NOT a prefix of '/usr/binder'.

    See ut_removePathnamePrefix().
    """
    assert path is not None
    assert prefixPath is not None
    if not prefixPath:
        # Every pathname has the prefix ''.
        result = True
    else:
        prefix = ut_toCanonicalDirectory(prefixPath)
        result = (prefix == ut_toCanonicalDirectory(path)) or \
                    (os.path.commonprefix([prefix, path]) == prefix)
    return result

def ut_removePathnamePrefix(path, prefixPath, defValue = None):
    """
    Returns the result of removing the pathname 'prefixPath' from the start
    of 'path', or returns 'defValue' if 'prefixPath' is not either the same
    as 'path' or the pathname of an ancestor directory of 'path'.

    Note: 'prefixPath' will only match whole pathname components, so for
    example '/usr/bin' is a prefix of '/usr/bin' and '/usr/bin/there', but is
    NOT a prefix of '/usr/binder'.

    See ut_hasPathnamePrefix().
    """
    #print("---> in ut_removePathnamePrefix(%s, %s, %s)" % (path, prefixPath, defValue))
    assert path is not None
    assert prefixPath is not None
    if not prefixPath:
        # Removing the prefix '' does nothing.
        result = path
    else:
        result = defValue
        prefix = ut_toCanonicalDirectory(prefixPath)
        if prefix == ut_toCanonicalDirectory(path):
            result = ""
        elif os.path.commonprefix([prefix, path]) == prefix:
            result = path[len(prefix):]
            assert not os.path.isabs(result)
    assert defValue is None or result is not None
    assert result == defValue or not os.path.isabs(result)
    return result

def ut_toCanonicalDirectory(path):
    """
    Converts the directory pathname 'path' to canonical form: that is, so
    that it ends in exactly one pathname separator unless it's empty ('').
    """
    assert path is not None
    sep = os.sep
    if not path or path.endswith(sep):
        result = path
    else:
        result = path + sep
    assert result is not None
    assert len(result) >= len(path)
    assert not result or result.endswith(os.sep)
    return result

def ut_hasNonemptyFilename(path, ext = None):
    """
    Returns True iff the pathname 'path' has a non-empty filename part,
    not counting any extension it may have, and, iff ext is not None, that
    its extension is 'ext'.
    """
    #print("---> in ut_hasNonemptyFilename(%s, %s)" % (path, ext))
    assert path is not None
    (d, f) = os.path.split(path)
    #print("    d = [%s], f = [%s]" % (d, f))
    (base, e) = os.path.splitext(f)
    #print("    base = [%s], e = [%s]" % (base, e))
    result = (len(base) > 0)
    #print("    result = %s" % str(result))
    if result and ext is not None:
        #print("    is non-empty 'ext':")
        result = (e == ut_fullExtension(ext))
        #print("    result = %s" % str(result))
    return result


def ut_fullExtension(ext):
    """
    Given a file extension 'ext' returns 'ext' with the platform's extension
    separator prepended to it, iff it isn't already.
    """
    assert ext is not None
    sep = os.extsep
    if not ext.startswith(sep):
        result = sep + ext
    else:
        result = ext
    assert result is not None
    assert len(result) >= len(ext)
    return result

def ut_addExtension(path, ext):
    """
    Returns the result of adding the extension 'ext' to the pathname 'path',
    allowing for the possibility that 'path' is the pathname of a directory.
    An extension separator will be appended before 'ext' iff it doesn't
    start with one.
    """
    assert path is not None
    assert ext is not None

    # Note: normpath() will remove any pathname separators that may be at
    # the end of 'path'.
    result = os.path.normpath(path) + ut_fullExtension(ext)
    assert result is not None
    assert result.endswith(ext)
    return result

def ut_isExistingRegularFile(path):
    """
    Returns True iff the file with pathname 'path' is an existing regular
    file, or a link to an existing regular file.
    """
    assert path is not None
    return os.path.isfile(os.path.realpath(path))

def ut_touchFile(path):
    """
    Touches the file with pathname 'path', creating it if it doesn't exist
    and updating its last modified time if it does exist.

    Returns True iff the file is successfully touched and is a regular file.
    """
    assert path is not None
    result = False
    w = None
    try:
        open(path, 'w')
        result = os.path.isfile(path)
    finally:
        if w is not None:
            w.close()
    return result

def ut_readFileLines(path):
    """
    Reads the file with pathname 'path' and returns a list of its lines
    (not including any carriage returns or newlines) or None if reading
    the file wasn't completely successful.
    """
    result = None
    try:
        r = open(path, 'r')
        try:
            data = r.read()  # all of its contents
            result = data.splitlines()
        finally:
            r.close()
    except:
        result = None
    # 'result' may be None
    return result

def ut_appendFileLines(path, lines, nl = '\n'):
    """
    Appends the lines of text in the list 'lines', each followed by 'nl', in
    order to the file with pathname 'path'.

    Throws an exception unless all of the lines are successfully appended to
    the file.

    See ut_writeFileLines().
    """
    assert path is not None
    assert lines is not None
    assert nl is not None
    ut_writeFileLines(path, lines, 'a', nl)

def ut_writeFileLines(path, lines, mode = 'w', nl = '\n'):
    """
    Writes the lines of text in the list 'lines', each followed by 'nl', in
    order to the file with pathname 'path'.

    If 'mode' is "w" then any existing file with pathname 'path' will be
    overwritten, amd if 'mode' is "a" then any existing file will be appended
    to.

    Throws an exception unless all of the lines are successfully written to
    the file.
    """
    assert path is not None
    assert lines is not None
    assert mode == 'w' or mode == 'a'
    assert nl is not None
    w = open(path, mode)
    try:
        fmt = "%s" + nl
        for line in lines:
            w.write(fmt % line)
    finally:
        w.close()


def ut_readShellCommandOutput(cmd):
    """
    Executes the command 'cmd' in a shell in a separate process and
    returns a file descriptor from which can be read everything that 'cmd'
    writes to its standard output. If 'cmd' is a string then the shell will
    preprocess it, and if it's a sequence then it won't.

    Note that this function doesn't wait for the command to finish executing
    before it returns.

    See os.read().
    See ut_executeShellCommand().
    See ut_executeProgramInBackground().
    """
    assert cmd
    (result, wfd) = os.pipe()
    p = ut_CommandPipeOutputDaemonProcess(cmd, result, wfd)
            # the daemon process will close 'wfd'
    assert result
    return result

def ut_executeShellCommand(cmd):
    """
# NOTE: the sequence version doesn't seem to work, at least when tried
# in the interactive shell.
    Executes the command 'cmd' in a subshell: if 'cmd' is a string then
    the shell will preprocess it, and if it's a sequence then it won't.

    Returns None if the command exits with a non-zero exit code, and
    returns a string containing everything that the command wrote to its
    standard output otherwise.

    See page 228 of "Python Cookbook" by Alex Martelli and David Ascher.

    See ut_readShellCommandOutput().
    See ut_executeProgramInBackground().
    """
    assert cmd is not None
    #print("cmd = [%s]" % cmd)
    child = os.popen(cmd)
    result = child.read()
    err = child.close()
    if err:
        result = None
    # 'result' may be None
    return result

def ut_executeAllShellCommands(cmdList):
    """
    Executes all of the commands in 'cmdList' in subshells until one exits
    with a non-zero exit code, in which case None is returned. If all of the
    commands are executed with zero return codes then we return everything
    that the last command in 'cmdList' wrote to its standard output.

    See ut_executeShellCommand(cmd).
    """
    assert cmdList is not None
    assert len(cmdList) > 0
    for cmd in cmdList:
        result = ut_executeShellCommand(cmd)
        if result is None:
            break  # for
    # 'result' may be None
    return result

def ut_executeProgramInBackground(path, args = None):
    """
    Executes the program with pathname 'path' in the background, passing it
    the sequence of arguments 'args' (or an empty list of arguments if 'args'
    is None).

    Returns the PID of the process in which the program is executing.

    See ut_readShellCommandOutput().
    """
    #print("---> in ut_executeProgramInBackground(%s, %s)" % (path, str(args)))
    assert path is not None
    # 'args' may be None
    if args is None:
        args = []
    result = os.spawnv(os.P_NOWAIT, path, [path].extend(args))
    return result


def ut_exitNow(sig = signal.SIGKILL):
    """
    Causes the calling process to exit immediately.

    Note: unlike sys.exit() this method doesn't raise an exception of any
    kind: the calling process stops pretty much immediately.
    """
    pid = os.getpid()
    #debug("process with PID %i should be exiting immediately (due to signal %i)" % (pid, sig))
    time.sleep(3)  # give process time to finish writing to stderr, etc.
    os.kill(pid, sig)
    #debug("shouldn't get printed if the process (%i) exited immediately" % pid)

def ut_tryToKill(pid, sig = signal.SIGINT):
    """
    Tries to "kill" the process with PID 'pid' by sending it the signal
    'sig'. No error is reported if there's no process with PID 'pid', though.

    Returns True if the process was successfully sent the signal and False
    if there was no process with PID 'pid'. Otherwise an exception is
    raised.
    """
    try:
        os.kill(pid, sig)
        result = True
    except OSError as ex:
        if ex.errno != errno.ESRCH:
            raise
        else:
            result = False  # there's no process with PID 'pid'
    return result


def ut_maintainCacheDirectorySize(maxSizeInBytes, cacheDir, logOut = None,
                            minFileSizeInBytes = 0, ignoreFileFunc = None):
    """
    Deletes the least-recently accessed files under the directory with
    pathname 'cacheDir' - provided the file's size (in bytes) is nonzero and
    greater than or equal to 'minFileSizeInBytes' - until the total size (in
    bytes) of all of the regular files under 'cacheDir' is less than or equal
    to 'maxSizeInBytes'.

    If 'logOut' is not None then it is assumed to be a stream or file that
    this method is to use to write log messages to.

    If 'ignoreFileFunc' is not None then it is assumed to be a one-argument
    function that, when given the pathname of a regular file under 'cacheDir'
    returns True iff that file is NOT to be removed from the cache as part
    of maintaining it.

    Note: this method silently does nothing if 'cacheDir' isn't an
    existing directory.
    """
    assert maxSizeInBytes >= 0
    assert cacheDir is not None
    # 'logOut' may be None
    if logOut is not None:
        log = lambda msg, w = logOut: w.write("%s\n" % msg)
    else:
        log = lambda msg: None

    if ignoreFileFunc is None:
        ignoreFileFunc = lambda p: False

    log("maintaining the cache directory %s" % cacheDir)
    log("maximum allowed size = %i bytes" % maxSizeInBytes)
    if os.path.isdir(cacheDir):
        log("cache directory is an existing directory")
        totalSize = 0
        contents = []
        for dirpath, dirnames, filenames in os.walk(cacheDir):
            for f in filenames:
                p = os.path.join(dirpath, f)
                if os.path.isfile(p):
                    st = os.stat(p)
                    size = st.st_size
                    contents.append((p, size, int(st.st_atime)))
                    totalSize += size
        log("current number of files in cache = %i" % len(contents))
        log("current total size of all files in cache = %i bytes" % totalSize)
        if totalSize > maxSizeInBytes:
            contents.sort(key = lambda x: x[2])
                # sort by increasing atime
            newTotalSize = totalSize
            for (path, size, atime) in contents:
                if (size == 0 or size >= minFileSizeInBytes) and \
                    not ignoreFileFunc(path):
                    try:
                        os.remove(path)
                        newTotalSize -= size
                        log("deleted %s: new total size = %i" % (path, newTotalSize))
                    except:
                        log("couldn't delete cached file %s: skipping it" % path)
                        pass
                    if newTotalSize <= maxSizeInBytes:
                        log("finished deleting cached files: new total size = %i" % newTotalSize)
                        break
                else:
                    log("not deleting file %s either because it's size (%i bytes) is less than %i bytes, or because it was intentionally ignored" % (path, size, minFileSizeInBytes))
                    pass
    log("finished maintaining the cache directory %s" % cacheDir)


def ut_preloadFiles(paths, maxWaitInSeconds = 120, doFast = False):
    """
    Preloads the files whose pathnames are items in the list 'paths' into the
    relevant filesystem caches (assuming it will get cached in such caches)
    so that it doesn't have to be generated later.

    If 'doFast' is True then files will be preloaded as quickly as possible,
    with multiple files being preloaded simultaneously: otherwise starting to
    preload one of the files won't start until the preceding one has been
    fully preloaded. (Preloading quickly can cause the currently playing
    track to start and stop due to excess CPU and/or I/O usage.)

    'maxWaitInSeconds' specifies the maximum number of seconds to wait for
    one file to preload before starting to preload the next. If a file is
    actually empty after it's preloaded then this keeps us from waiting
    indefinitely: it can be set to a large value in cases where the file
    can't (or at least shouldn't be) empty after it's preloaded.
    """
    #print("---> in ut_preloadFiles([%s], maxWaitInSeconds = %s, doFast = %s)" % (', '.join(paths), str(maxWaitInSeconds), str(doFast)))
    assert paths is not None  # though it may be empty
    assert maxWaitInSeconds > 0
    prev = None
    size = ut_fileSize
    waitLength = 3  # seconds
    for p in paths:
        # If necessary, wait until the previous file's been fully preloaded or
        # approximately maxWaitInSeconds has elapsed, whichever comes first.
        #print("    p = [%s]" % p)
        if not doFast and prev is not None:
            #print("    waiting for prev = [%s] to finish preloading ..." % prev)
            totalWait = 0
            while totalWait < maxWaitInSeconds:
                try:
                    if size(prev) > 0:
                        #print("    prev finished preloading")
                        break  # while
                except OSError:
                    pass
                #print("    waiting a few seconds before checking again ...")
                time.sleep(waitLength)
                totalWait += waitLength
                #print("    ... done waiting")

        # Note that files can have non-zero size and still need to be
        # preloaded: see fscommon.fs_defaultFileSize().
        #print("size of file to preload is %i bytes" % size(p))
        # To preload a file we just need to read a few bytes from it.
        r = None
        try:
            #print("    preloading [%s] by reading from it a little" % p)
            r = open(p, 'rb')
            r.read(4000)
        finally:
            if r is not None:
                r.close()
        prev = p

def ut_preloadFilesInBackground(paths, doFast = False):
    """
    Preloads in the background, by default one at a time and in order, the
    files whose pathnames are in the list 'paths'.

    If 'doFast' is True then files will be preloaded as quickly as possible
    instead of one at a time: see 'ut_preloadFiles()' for details.
    """
    #debug("---> in ut_preloadFilesInBackground(%s, doFast = %s)" % (str(paths), str(doFast)))
    p = ut_PreloadFilesDaemonProcess(paths, doFast)


# Classes.

class ut_MultiplexedWritableStream(object):
    """
    The class of writable stream that actually writes to all of the
    (presumably writable) file/stream objects it's constructed from.

    See file.
    """

    def __init__(self, *writers):
        object.__init__(self)
        self._ut_writers = writers
        self._ut_debugFunc = None

    def setDebugFunction(self, fun):
        """
        Sets the one-argument function 'fun' as the function that we pass
        debugging messages to in order to have them output.
        """
        assert fun is not None
        self._ut_debugFunc = fun
        self._ut_debug("ut_MultiplexedWritableStream: set debugging function")

    def _ut_debug(self, msg):
        """
        Outputs the message 'msg' containing debugging information.
        """
        f = self._ut_debugFunc
        if f is not None:
            f(msg)


    def __enter__(self):
        self._ut_debug("---> in ut_MultiplexedWritableStream.__enter__()")
        f = lambda w: w.__enter__()
        self._ut_forAllWriters(f)

    def __exit__(self, *excinfo):
        self._ut_debug("---> in ut_MultiplexedWritableStream.__exit__()")
        allExcepts = []
        for w in self._ut_writers:
            try:
                w.__exit__(*excinfo)
            except Exception as ex:
                allExcepts.append(ex)
            except:
                ex = TypeError("a multiplexed writable stream's __exit__() "
                        "method threw an unexpected exception: %s" %
                        ut_exceptionDescription())
                allExcepts.append(ex)
        self._ut_handleAnyExceptions(allExcepts)

    def close(self):
        self._ut_debug("---> in ut_MultiplexedWritableStream.close()")
        f = lambda w: w.close()
        self._ut_forAllWriters(f)

    def fileno(self):
        self._ut_debug("---> in ut_MultiplexedWritableStream.fileno()")
        raise IOError("a ut_MultiplexedWritableStream doesn't have a "
            "(single) fileno")

    def flush(self):
        self._ut_debug("---> in ut_MultiplexedWritableStream.flush()")
        f = lambda w: w.flush()
        self._ut_forAllWriters(f)

    def isatty(self):
        self._ut_debug("---> in ut_MultiplexedWritableStream.isatty()")
        return False

    def next(self):
        self._ut_debug("---> in ut_MultiplexedWritableStream.next()")
        self._ut_handleNotReadable()

    def read(self, size = -1):
        self._ut_debug("---> in ut_MultiplexedWritableStream.read(%s)" % str(size))
        self._ut_handleNotReadable()

    def readline(self, size = -1):
        self._ut_debug("---> in ut_MultiplexedWritableStream.readline(%s)" % str(size))
        self._ut_handleNotReadable()

    def readlines(self, size = -1):
        self._ut_debug("---> in ut_MultiplexedWritableStream.readlines(%s)" % str(size))
        self._ut_handleNotReadable()

    def seek(self, offset, whence = 0):
        self._ut_debug("---> in ut_MultiplexedWritableStream.seek(%s, %s)" % (str(offset), str(whence)))
        f = lambda w, off = offset, wh = whence: w.seek(off, wh)
        self._ut_forAllWriters(f)

    def tell(self):
        self._ut_debug("---> in ut_MultiplexedWritableStream.tell()")
        raise IOError("a ut_MultiplexedWritableStream doesn't have a "
            "(single) current file position to tell")

    def truncate(self, size = -1):
        self._ut_debug("---> in ut_MultiplexedWritableStream.truncate(%s)" % str(size))
        if size < 0:
            f = lambda w: w.truncate()
        else:
            f = lambda w, sz = size: w.truncate(sz)
        self._ut_forAllWriters(f)

    def write(self, txt):
        self._ut_debug("---> in ut_MultiplexedWritableStream.write(txt)")
        f = lambda w, t = txt: w.write(t)
        self._ut_forAllWriters(f)

    def writelines(self, iter):
        self._ut_debug("---> in ut_MultiplexedWritableStream.writelines(iter)")
        f = lambda w, i = iter: w.writelines(i)
        self._ut_forAllWriters(f)

    def xreadlines(self):
        self._ut_debug("---> in ut_MultiplexedWritableStream.xreadlines()")
        self._ut_handleNotReadable()


    def _ut_forAllWriters(self, fun):
        """
        Executes the one-argument function 'fun' for each of our writers,
        using each writer in turn as its argument.
        """
        self._ut_debug("---> in _ut_forAllWriters()")
        allExcepts = []
        for w in self._ut_writers:
            try:
                self._ut_debug("    using writer of type '%s' ..." % type(w).__name__)
                fun(w)
                self._ut_debug("    ... function finished successfully")
            except Exception as ex:
                self._ut_debug("    an exception was thrown: %s" % ut_exceptionDescription())
                allExcepts.append(ex)
            except:
                self._ut_debug("    an unexpected type of exception was thrown: %s" % ut_exceptionDescription())
                ex = TypeError("a multiplexed writable stream's method "
                        "threw an unexpected exception: %s" %
                        ut_exceptionDescription())
                allExcepts.append(ex)
        self._ut_handleAnyExceptions(allExcepts)
        self._ut_debug("    at the end of _ut_forAllWriters()")

    def _ut_handleNotReadable(self):
        raise IOError("a ut_MultiplexedWritableStream isn't readable")

    def _ut_handleAnyExceptions(self, allExcepts):
        """
        Handles the list 'allExcepts' of all of the exceptions raised
        when we delegate a method call to all of our writers.
        """
        if allExcepts:
            raise allExcepts[0]  # reraise the first one thrown


class ut_AbstractProgram(object):
    """
    An abstract base class for classes that represent entire programs.
    """

    def __init__(self, *args, **kw):
        #print("---> in ut_AbstractProgram.__init__()")
        object.__init__(self)
        self._ut_programBasename = os.path.basename(sys.argv[0])

    def run(self):
        """
        Causes this program to process its arguments and then execute.
        """
        args = None
        shortHelpOpts = self._shortHelpOptions()
        longHelpOpts = self._longHelpOptionsList()
        shortHelpOptNames = ["-%s" % s for s in
                                shortHelpOpts.replace(":", "")]
        longHelpOptNames = ["--%s" % s.rstrip("=") for s in longHelpOpts]

        shortOpts = shortHelpOpts + self._shortOptions()
        longOpts = longHelpOpts + self._longOptionsList()

        argsMap = self._buildInitialArgumentsMap()
        isValid = True
        try:
            opts, args = getopt.getopt(sys.argv[1:], shortOpts, longOpts)
            for opt, val in opts:
                #print("    opt, val = %s, %s" % (opt, val))
                if opt in shortHelpOptNames or opt in longHelpOptNames:
                    isValid = False
                    break  # for
                else:
                    isValid = self._processOption(opt, val, argsMap)
                    if not isValid:
                        break  # for
        except getopt.GetoptError as ex:
            isValid = False
            self._fail("Invalid option: %s" % ex.msg)

        if args is not None and isValid:
            isValid = self._processNonOptionArguments(args, argsMap)
        if isValid:
            isValid = self._checkArgumentCombinations(argsMap)

        if not isValid:
            short = ""
            if shortHelpOptNames:
                short = "[" + "|".join(shortHelpOptNames) + "]"
            long = ""
            if longHelpOptNames:
                long = "[" + "|".join(longHelpOptNames) + "]"
            helpDesc = self._buildHelpOptionsDescription(shortHelpOptNames,
                                                         longHelpOptNames)
            msg = self._usageMessage(self._basename(), short, long, helpDesc)
            print(msg, file = sys.stderr)
            sys.exit(1)
        else:
            rc = self._execute(argsMap)
            sys.exit(rc)

    def _buildHelpOptionsDescription(self, shortHelpOpts, longHelpOpts):
        """
        Builds and returns a paragraph describing what happens if one or
        more of this program's (short or long) help options is specified.

        'shortHelpOpts' is a list of strings, each of which is a short
        option (e.g. '-?'), and 'longHelpOpts' is a list of strings, each
        of which is a long option (e.g. '--help').

        Our result is suitable for use in the description part of our
        usage message. It should be on its own line with no blank line
        immediately preceding or following it.
        """
        assert shortHelpOpts is not None
        assert longHelpOpts is not None
        result = ""
        allOpts = shortHelpOpts + longHelpOpts
        if allOpts:
            if len(allOpts) > 1:
                fmt = "If any of the help options %s or %s are"
                optsPart = fmt % (", ".join(allOpts[:-1]), allOpts[-1])
            else:
                optsPart = "If the help option %s is" % allOpts[0]
            result = """
%s specified then
this usage message will be output and the program will exit.
""" % optsPart
        assert result is not None
        return result

    def _basename(self):
        """
        Returns the basename of this program.
        """
        result = self._ut_programBasename
        assert result is not None
        return result

    def _fail(self, msg):
        """
        Outputs 'msg' as a message describing why this program failed.
        """
        print("\n%s." % msg, file = sys.stderr)

    def _warn(self, msg):
        """
        Outputs 'msg' as a warning message.
        """
        print("\n%s." % msg, file = sys.stderr)

    def _debug(self, msg):
        """
        Outputs 'msg' as a message used in debugging this program.
        """
        print(msg, file = sys.stderr)
        pass

    def _handleUnknownOption(self, opt):
        """
        Handles the option 'opt' when it's one that our _processOption()
        method doesn't know about (usually because it's not a valid option).
        Returns the boolean value that _processOption() should return.
        """
        assert opt is not None
        self._fail("Unknown option: %s" % opt)
        return False


    def _shortHelpOptions(self):
        """
        Returns a string consisting of the short (one-letter) options that
        indicate that, instead of executing, this program should print out a
        usage message and then exit.

        See _usageMessage(), _longHelpOptionsList(), _shortOptions().
        """
        return "h?"

    def _longHelpOptionsList(self):
        """
        Returns a list of strings, each of which is the name of a long option
        that indicates that instead of executing, this program should print
        out a usage message and then exit.

        See _usageMessage(), _shortHelpOptions(), _longOptionsList().
        """
        return ["help"]


    def _usageMessage(self, progName, shortHelpOpts, longHelpOpts,
                     helpOptionsDesc):
        """
        Returns the message describing how to use this program, where
        'progName' is the name to be used for this program in the message.

        'shortHelpOpts' and 'longHelpOpts' are both strings that are
        representations of the short and long options, respectively, that
        indicate that this program should just print this usage message and
        exit. 'helpOptionsDesc' is a paragraph that describes what happens
        if one or more of the (short or long) help options is specified.
        """
        assert progName
        assert shortHelpOpts is not None
        assert longHelpOpts is not None
        assert helpOptionsDesc is not None
        #assert result
        raise NotImplementedError

    def _shortOptions(self):
        """
        Returns a string consisting of all of the short (one-letter) options
        for this program in the format expected by getopt.getopt(), NOT
        including any of the common ones (like the help options).

        See _shortHelpOptions().
        """
        result = ""
        assert result is not None
        return result

    def _longOptionsList(self):
        """
        Returns a list of all of the names of all of the long options for
        this program in the format expected by getopt.getopt(), NOT
        including any of the common ones (like the help options).

        See _longHelpOptionsList().
        """
        result = []
        assert result is not None
        return result

    def _buildInitialArgumentsMap(self):
        """
        Builds and returns the initial version of the map/dictionary that
        will be used to contain all of the information parsed out of our
        command line arguments.

        This is where to set the values to use by default, in case no options
        or arguments are present to specify non-default values.
        """
        #assert result is not None
        raise NotImplementedError

    def _processOption(self, opt, val, argsMap):
        """
        Processes the option 'opt' with associated value 'val' (which will be
        None iff the option has no associated value) by updating the
        arguments map 'argsMap' appropriately.

        Returns True iff the option and its value are valid. If False is
        returned then it is expected that _fail() has been called at least
        once to report why the option and/or its value is invalid.

        See _handleUnknownOption().
        """
        assert opt
        # 'val' may be None
        assert argsMap is not None
        raise NotImplementedError

    def _processNonOptionArguments(self, args, argsMap):
        """
        Processes all of our command line arguments 'args' that are not
        options or part of options, where 'argsMap' is the arguments map
        built by processing all of the option arguments.

        Returns True iff all of the non-option arguments are valid,
        including if there aren't too many or too few arguments. If False
        is returned then it is expected that _fail() has been called at least
        once to report why the arguments are invalid.
        """
        assert args is not None
        assert argsMap is not None
        raise NotImplementedError

    def _checkArgumentCombinations(self, argsMap):
        """
        Checks that the combination of all of the arguments in 'argsMap'
        is valid. For example, it can check that two mutually incompatible
        options weren't both specified.

        Returns True iff the combination of all of the arguments is valid.
        If False is returned then it is expected that _fail() has been
        called at least once to report why the combination of arguments is
        invalid.

        Note: this method isn't called until all of the option and non-
        option arguments have been processed (by _processOption() and
        _processNonOptionArguments(), respectively).
        """
        assert argsMap is not None
        return True

    def _execute(self, argsMap):
        """
        Executes this program using the information from the arguments map
        'argsMap' built by processing all of our arguments.

        Returns the exit code that this program should return: it should be
        0 iff execution was successful.
        """
        assert argsMap is not None
        #assert result >= 0
        raise NotImplementedError


class ut_AbstractDaemonProcess(object):
    """
    An abstract base class for classes that represent daemon processes.

    Note: subclasses that override our __init__() method must be sure
    to set all fields BEFORE calling our version of __init__(): otherwise
    those values won't be visible in the daemon process.
    """

    def __init__(self, pidFile = None, doDebug = False):
        """
        Initializes us with the pathname 'pidFile' of the file to which we
        are to write the daemon process' PID, iff 'pidFile' isn't None.
        """
        #self._ut_debug("---> in ut_AbstractDaemonProcess.__init__(%s)" % pidFile)
        #self._ut_doDebug = doDebug
            # since _ut_debugForkDaemonProcess() doesn't work properly (yet)
        self._ut_pidFile = pidFile
        self._ut_forkDaemonProcess()

    def _ut_forkDaemonProcess(self):
        """
        See _ut_reallyForkDaemonProcess().
        See _ut_debugForkDaemonProcess().
        """
        if hasattr(self, '_ut_doDebug') and self._ut_doDebug == True:
            self._ut_debugForkDaemonProcess()
        else:
            self._ut_reallyForkDaemonProcess()

    def _ut_debugForkDaemonProcess(self):
        """
        Pretends to fork the daemon process, but actually just forks a
        regular one and then waits for it to finish.

        This version is here to simplify debugging subclasses.
        """
        #self._ut_debug("---> in _ut_debugForkDaemonProcess()")
        try:
            #self._ut_debug("    about to fork() ...")
            pid = os.fork()
        except OSError as ex:
            self._ut_reportError("    fork in _ut_debugForkDaemonProcess() "
                "failed: %d (%s)" % (ex.errno, ex.strerror))
            raise

        if pid == 0:  # we're in the child process
            #self._ut_debug("    in the child process ...")
            try:
                self._ut_doDaemonProcessing()
                #self._ut_debug("    child process successfully finished daemon processing")
            finally:
                #self._ut_debug("    child process about to exit()")
                sys.exit(0)
        else:  # we're in the parent process
            #self._ut_debug("    in the parent process ...")
            assert pid > 0
            os.waitpid(pid, 0)
            #self._ut_debug("    child process successfully reaped")

    def _ut_reallyForkDaemonProcess(self):
        """
        Forks the daemon process, raising an OSError iff it fails.

        See pages 229-231 of "Python Cookbook" by Alex Martelli and David
        Ascher.
        """
        #self._ut_debug("---> in _ut_reallyForkDaemonProcess() (%s)" % self.__class__)
        #self._ut_debug("    calling process PID = %i" % os.getpid())
        try:
            #self._ut_debug("    about to fork() the child ...")
            pid = os.fork()
        except OSError as ex:
            self._ut_reportError("    fork #1 failed: %d (%s)" %
                                    (ex.errno, ex.strerror))
            raise

        if pid != 0:
            #self._ut_debug("    we're in the parent process waiting for child (PID = %i) to terminate" % pid)
            ut_waitForChildProcessToTerminate(pid)
            #self._ut_debug("    child (PID = %i) terminated" % pid)
        else:  # pid == 0
            #self._ut_debug("    we're in the child process (PID = %i)" % os.getpid())
            #self._ut_debug("    decoupling from the parent environment")
            os.chdir("/")
            os.setsid()
            os.umask(0)
            #self._ut_debug("    done decoupling from parent environment")
            try:
                #self._ut_debug("    about to fork() again to create the grandchild daemon process")
                pid = os.fork()
                if pid > 0:
                    #self._ut_debug("    we're in the child process (%i): grandchild PID = %i" % (os.getpid(), pid))
                    # Record the daemon process' PID, then exit from the
                    # child (not the grandchild) process.
                    path = self._ut_pidFile
                    if path is not None:
                        ut_writeFileLines(path, ["%d" % pid])
                    #self._ut_debug("    the child process (%i) is exit()ing" % os.getpid())
                    ut_exitNow()
            except OSError as ex:
                self._ut_reportError("    fork #2 failed: %d (%s)" %
                                        (ex.errno, ex.strerror))
                raise

            #self._ut_debug("    starting the daemon's processing (in the grandchild process)")
            try:
                try:
                    self._ut_doDaemonProcessing()
                    #self._ut_debug("    daemon processing finished successfully")
                except KeyboardInterrupt:
                    pass  # Ctrl-C'd
                except:
                    self._ut_debug("    failure during daemon processing: %s" % ut_exceptionDescription())
                    pass
            finally:
                #self._ut_debug("    finished daemon processing (PID = %i)" % os.getpid())
                try:
                    path = self._ut_pidFile
                    if path is not None:
                        #self._ut_debug("    deleting the PID file '%s'" % path)
                        ut_deleteFileOrDirectory(path)
                finally:
                    #self._ut_debug("    the grandchild/daemon process (%i) is exit()ing" % os.getpid())
                    ut_exitNow()

    def _ut_doDaemonProcessing(self):
        """
        Performs all of the processing that is done in our daemon process.
        """
        #self._ut_debug("----> in _ut_doDaemonProcessing()")
        self._ut_beforeRunning()
        try:
            self._ut_run()
        finally:
            self._ut_afterRunning()

    def _ut_reportError(self, msg):
        """
        Reports the error described by the message 'msg'.
        """
        print(msg, file = sys.stderr)

    def _ut_debug(self, msg):
        """
        Reports 'msg' as a debugging message, if we're reporting them.
        """
        print(msg)
        pass


    def _ut_beforeRunning(self):
        """
        Performs any and all processing in our daemon process that is to
        occur before _ut_run() is called.
        """
        pass

    def _ut_afterRunning(self):
        """
        Performs any and all processing in our daemon process that is to
        occur after _ut_run() is called, regardless of how _ut_run()
        finishes.
        """
        pass

    def _ut_run(self):
        """
        The method that is executed in the daemon process: when it ends so
        does the daemon process.
        """
        raise NotImplementedError

class ut_AbstractCommandFifoDaemonProcess(ut_AbstractDaemonProcess):
    """
    An abstract base class for daemon processes that read commands from a
    FIFO and process them. Each command consists of a single line.

    Note: the POSIX standard only guarantees that data is atomically written
    to a FIFO if that data is 512 bytes long or less, so commands should
    usually be kept below that length.
    """

    def __init__(self, fifoPathname, pidFile = None, doDebug = False):
        """
        Initializes us with the pathname of the FIFO from which we are to
        read commands, and the pathname of the file to which we are to write
        our PID.
        """
        #self._ut_debug("---> in ut_AbstractCommandFifoDaemonProcess.__init__(%s, %s)" % (commandSource, pidFile))
        assert fifoPathname is not None
        # 'pidFile' may be None
        self._ut_fifo = fifoPathname
        ut_AbstractDaemonProcess.__init__(self, pidFile, doDebug)

    def _ut_run(self):
        #self._ut_debug("---> in ut_AbstractCommandFifoDaemonProcess._ut_run()")
        (r, wDummy) = (None, None)
        try:
            src = self._ut_fifo
            r = open(src, 'r')
            wDummy = open(src, 'w')
                # We open the FIFO for writing (though never write to it) so
                # that when a client closes it for writing we don't get an
                # EOF when reading 'r': see p.61 of "UNIX Network Programming
                # Volume 2" by W. Richard Stevens.
            while True:
                try:
                    cmd = r.readline().strip()
                except:
                    # This indicates that this daemon process has been
                    # terminated.
                    #self._ut_debug("    failed to read the next 'change ratings' command: %s" % ut_exceptionDescription())
                    break  # while
                if cmd:
                    self._ut_processCommand(cmd)
        finally:
            #self._ut_debug("    at end of ut_AbstractCommandFifoDaemonProcess._ut_run()")
            ut_tryToCloseAll(r, wDummy)

    def _ut_reportInvalidCommandStartError(self, cmd):
        """
        Reports that the command 'cmd' is invalid because its first word
        isn't the start of a recognized command.
        """
        self._ut_reportError("The command '%s' is invalid: its first "
                    "word isn't the start of a recognized command." % cmd)

    def _ut_reportTooManyCommandArguments(self, cmd):
        """
        Reports that the command 'cmd' is invalid because it has too many
        arguments.
        """
        self._ut_reportError("The command '%s' is invalid: too many "
                             "arguments were specified." % cmd)

    def _ut_processCommand(self, cmd):
        """
        Processes the command 'cmd'.
        """
        #self._ut_debug("---> in _ut_processCommand(%s)" % cmd)
        raise NotImplementedError

class ut_AbstractOutputDaemonProcess(ut_AbstractDaemonProcess):
    """
    An abstract base class for daemon processes that generate output using
    a generator object and write all of that output to a specified file
    descriptor then close that file descriptor, at least by default.

    This class doesn't know or care what type of object 'generator' is: it
    just stores it and passes it as an argument to our abstract method
    _ut_writeOutput(), which all subclasses should override.
    """

    def __init__(self, generator, wfd, bufSize = 4096, doClose = True,
                 doDebug = False):
        """
        Initializes us with the generator object 'generator' and the file
        descriptor 'wfd' to write the generator's output to. 'wfd' will be
        closed when this process is done with it iff 'doClose' is True.

        The 'bufSize' argument specifies the size of the buffer to use in
        collecting the generator's output.
        """
        assert generator is not None
        assert wfd
        assert bufSize > 0
        self._ut_generator = generator
        self._ut_wfd = wfd
        self._ut_doClose = doClose
        self._ut_bufferSize = bufSize
        ut_AbstractDaemonProcess.__init__(self, None, doDebug)

    def _ut_run(self):
        #self._ut_debug("---> in ut_AbstractOutputDaemonProcess._ut_run()")
        self._ut_writeOutput(self._ut_generator, self._ut_wfd,
                             self._ut_bufferSize)

    def _ut_writeOutput(self, generator, wfd, bufSize):
        """
        Writes out this process' output to the writable file descriptor 'w',
        where 'generator' is the object that is to be used to generate that
        output. 'bufSize' is the recommended size of any buffers used in
        generating or writing the output.

        See os.fdopen().
        """
        assert generator is not None
        assert wfd is not None
        assert bufSize > 0
        raise NotImplementedError

    def _ut_afterRunning(self):
        """
        Performs any and all processing in our daemon process that is to
        occur after _ut_run() is called, regardless of how _ut_run()
        finishes.
        """
        if self._ut_doClose:
            self._ut_closeFileDescriptor(self._ut_wfd,
                "the file descriptor the daemon process wrote to")
        ut_AbstractDaemonProcess._ut_afterRunning(self)

    def _ut_closeFileDescriptor(self, fd, desc):
        """
        Closes the file descriptor 'fd' described by 'desc', reporting an
        error (that includes 'desc') if it fails.
        """
        assert fd
        assert desc
        try:
            #self._ut_debug("    closing fd = %i (PID = %i)" % (fd, os.getpid()))
            os.close(fd)
        except OSError as ex:
            self._ut_reportError("Failed to close %s: %d (%s)" %
                                 (desc, ex.errno, ex.strerror))

    def _ut_writeCommandOutput(self, cmd, wfd, bufSize):
        """
        Writes output of the shell command 'cmd' to the writable file
        descriptor 'wfd'. 'bufSize' is the recommended size of any buffer
        used to buffer the command output.

        This method used by some subclasses to implement _ut_writeOutput().

        See _ut_writeOutput().
        """
        assert cmd
        assert wfd is not None
        assert bufSize > 0
        rfile = None
        try:
            #self._ut_debug("    about to execute command [%s]" % cmd)
            rfile = os.popen(cmd, "r", bufSize)
            try:
                #self._ut_debug("    about to write command output to file descriptor")
                while True:
                    s = rfile.read(bufSize)
                    if s:
                        os.write(wfd, s)
                    else:
                        break  # while
            except OSError as ex:
                if ex.errno == errno.EPIPE:
                    self._ut_debug("    the file descriptor we write command output to was one end of a pipe and the other end was closed")
                else:
                    raise
        finally:
            ut_tryToCloseAll(rfile)

class ut_AbstractPipeOutputDaemonProcess(ut_AbstractOutputDaemonProcess):
    """
    An abstract ut_AbstractOutputDaemonProcess that writes the generator's
    output to the writable end of a pipe. It also closes the writable end
    of the pipe in the calling process and the readable end of the pipe in
    the daemon process before the generating any output, as well as the
    writable end of the pipe in the daemon process after all of the
    generated output has been written to it.
    """

    def __init__(self, generator, rfd, wfd, doDebug = False):
        """
        Initializes us with the generator 'generator' and the pipe's readable
        and writable file descriptors ('rfd' and 'wfd', respectively).
        """
        assert generator is not None
        assert rfd
        assert wfd
        self._ut_rfd = rfd
        ut_AbstractOutputDaemonProcess. \
            __init__(self, generator, wfd, doDebug = doDebug)
        self._ut_closeFileDescriptor(wfd, "the pipe's writable end")

    def _ut_beforeRunning(self):
        ut_AbstractOutputDaemonProcess._ut_beforeRunning(self)
        self._ut_closeFileDescriptor(self._ut_rfd, "the pipe's readable end")

class ut_CommandOutputDaemonProcess(ut_AbstractOutputDaemonProcess):
    """
    Represents an ut_OutputDaemonProcess that generates its output by
    executing a shell command. The generator is a string containing a shell
    command.
    """

    def _ut_writeOutput(self, generator, wfd, bufSize):
        assert generator is not None
        assert wfd is not None
        assert bufSize > 0
        self._ut_writeCommandOutput(generator, wfd, bufSize)

class ut_CommandPipeOutputDaemonProcess(ut_AbstractPipeOutputDaemonProcess):
    """
    Represents a ut_PipeOutputDaemonProcess that generates its output by
    executing a shell command. The generator is a string containing a shell
    command.
    """

    def _ut_writeOutput(self, generator, wfd, bufSize):
        assert generator is not None
        assert wfd is not None
        assert bufSize > 0
        self._ut_writeCommandOutput(generator, wfd, bufSize)


class ut_PreloadFilesDaemonProcess(ut_AbstractDaemonProcess):
    """
    Represents a daemon process that preloads zero or more files into the
    relevant filesystem caches (assuming they will get cached in such
    caches) so that they don't have to be generated later.
    """

    def __init__(self, paths, doFast = False, doDebug = False):
        """
        Initializes us with the list containing the pathnames of the files
        that we are to preload.

        If 'doFast' is True then files will be preloaded as quickly as
        possible: see 'ut_preloadFiles()' for details.

        Note: we don't allow 'paths' to be empty because it's a waste to
        spawn this process only to have it do nothing. So we make calling
        code responsible for handling that case more sensibly.
        """
        assert paths
        self._ut_paths = paths
        self._ut_doFast = doFast
        ut_AbstractDaemonProcess.__init__(self, None, doDebug)

    def _ut_run(self):
        ut_preloadFiles(self._ut_paths, doFast = self._ut_doFast)


class ut_LeastRecentlyAddedCache(object):
    """
    Represents a cache that, when it is to contain too many items, removes
    those that were added to it the least recently (that is, the longest
    time ago).
    """

    def __init__(self, lowSize, highSize = None):
        """
        Initializes this instance so that once it contains more than
        'highSize' items the least-recently added (that is, oldest) items
        will be removed from it until it contains 'lowSize' items.
        """
        if highSize is None:
            highSize = lowSize
        assert lowSize <= highSize
        self._ut_lowSize = lowSize
        self._ut_highSize = highSize
        self._ut_map = {}
        self._ut_keysList = []
            # lists all of our keys in the order their mappings were added
            # (so new mappings' keys are appended to the end of this list)

    def get(self, key, defaultValue = None):
        """
        Returns the value that we map 'key' to, or returns 'defaultValue' if
        we don't map 'key' to a value.

        See peek().
        """
        # 'result' may be None
        return self.peek(key, defaultValue)

    def peek(self, key, defaultValue = None):
        """
        Returns the value that we map 'key' to, or returns 'defaultValue' if
        we don't map 'key' to a value.

        Note: for this class this method does exactly the same thing as
        get(): it exists so that we have the same interface as other cache
        classes.

        See get().
        """
        # 'result' may be None
        return self._ut_map.get(key, defaultValue)

    def tryToAdd(self, key, value):
        """
        If this cache doesn't already contain a mapping from the key 'key'
        then a mapping from 'key' to 'value' is added and True is returned;
        otherwise no mapping is added and False is returned.

        See add().
        """
        result = False
        if not key in self._ut_map:
            self._ut_addNewMapping(key, value)
            result = True
        return result

    def add(self, key, value):
        """
        Adds a mapping from 'key' to 'value' to this cache, replacing any
        mapping from 'key' that we used to contain.

        See tryToAdd().
        """
        m = self._ut_map
        if key in m:  # replace value in existing mapping
            m[key] = value
        else:
            self._ut_addNewMapping(key, value)

    def size(self):
        """
        Returns the number of mappings in this cache.
        """
        #assert result >= 0
        #assert len(self._ut_map) == len(self._ut_keysList)
        return len(self._ut_map)

    def __str__(self):
        """
        Returns a string representation of this cache.
        """
        m = self._ut_map
        lst = self._ut_keysList
        sz = self.size()
        itemFmt = "%" + str(len(str(sz))) + "i. [%s] --> [%s]"
        lines = []
        lines.append("Cache of class %s: low = %i, high = %i" % (self.__class__, self._ut_lowSize, self._ut_highSize))
        lines.append("From 'oldest' to 'newest' its %i items are:" % sz)
        for i in xrange(sz):
            key = lst[i]
            val = m[key]
            lines.append(itemFmt % (i, str(key), str(val)))
        result = "\n".join(lines)
        assert result is not None
        return result

    def _onRemoval(self, key, value):
        """
        The method that's called some time before the mapping from 'key' to
        'value' is removed from this cache.

        This implementation does nothing.
        """
        pass


    def _ut_addNewMapping(self, key, value):
        """
        Adds a new mapping from 'key' to 'value' to this cache. It assumes
        that it doesn't already map 'key' to anything.
        """
        self._ut_map[key] = value
        self._ut_keysList.append(key)
        if self.size() > self._ut_highSize:
            self._ut_shrink()

    def _ut_shrink(self):
        """
        Removes the least-recently added items from this cache until we're
        at our low size.
        """
        sz = self.size()
        assert sz > self._ut_highSize
        numToRemove = sz - self._ut_lowSize
        m = self._ut_map
        lst = self._ut_keysList
        for i in xrange(numToRemove):
            key = lst[i]
            self._onRemoval(key, m[key])
            del m[key]
        self._ut_keysList = lst[numToRemove:]
        assert len(self._ut_keysList) == len(self._ut_map)
        assert self.size() == self._ut_lowSize

class ut_LeastRecentlyUsedCache(object):
    """
    Represents a cache that, when it is to contain too many items, removes
    those that were accessed the least recently (that is, the longest time
    ago). (An item is considered to be accessed when it's first added and
    when it's retrieved using our get() method.)
    """

    def __init__(self, lowSize, highSize = None):
        """
        Initializes this instance so that once it contains more than
        'highSize' items the least-recently used items will be removed from
        it until it contains 'lowSize' items.
        """
        if highSize is None:
            highSize = lowSize
        assert lowSize <= highSize
        self._ut_lowSize = lowSize
        self._ut_highSize = highSize
        self._ut_map = {}
            # maps our keys to pairs, where the first item in each pair is
            # the value that the key maps to, and the second item in each
            # pair is a 0-based "update index" that indicates when the key's
            # value was last accessed
        self._ut_keysList = []
            # lists all of our keys: the first/oldest ones are approximately
            # in order by when their values were last accessed as of the last
            # time we've been _ut_compact()ed; the last/newest ones are in
            # order by when they and their values were added to us (so new
            # mappings' keys are appended to the end of this list)
        self._ut_nextUpdateIndex = 0

    def get(self, key, defaultValue = None):
        """
        Returns the value that we map 'key' to, or returns 'defaultValue' if
        we don't map 'key' to a value.

        See peek().
        """
        m = self._ut_map
        try:
            item = m[key]
        except KeyError:
            result = defaultValue
        else:
            nextUi = self._ut_nextUpdateIndex
            (result, ui) = item
            if ui != (nextUi - 1):
                m[key] = (result, nextUi)
                self._ut_incrementNextUpdateIndex()
        # 'result' may be None
        return result

    def peek(self, key, defaultValue = None):
        """
        Returns the value that we map 'key' to, or returns 'defaultValue' if
        we don't map 'key' to a value. Unlike when our get() method is used,
        retrieving a value using this method doesn't count as accessing it,
        and so how long it's kept in this cache isn't affected.

        See get().
        """
        try:
            item = self._ut_map[key]
        except KeyError:
            result = defaultValue
        else:
            result = item[0]
        # 'result' may be None
        return result

    def tryToAdd(self, key, value):
        """
        If this cache doesn't already contain a mapping from the key 'key'
        then a mapping from 'key' to 'value' is added and True is returned;
        otherwise no mapping is added and False is returned.

        See add().
        """
        result = False
        if not key in self._ut_map:
            self._ut_addNewMapping(key, value)
            result = True
        return result

    def add(self, key, value):
        """
        Adds a mapping from 'key' to 'value' to this cache, replacing any
        mapping from 'key' that we used to contain.

        See tryToAdd().
        """
        m = self._ut_map
        if key in m:  # replace value in existing mapping
            nextUi = self._ut_nextUpdateIndex
            if m[key][1] != nextUi:
                self._ut_incrementNextUpdateIndex()
            m[key] = (value, nextUi)
        else:
            self._ut_addNewMapping(key, value)

    def size(self):
        """
        Returns the number of mappings in this cache.
        """
        #assert result >= 0
        #assert len(self._ut_map) == len(self._ut_keysList)
        return len(self._ut_map)

    def __str__(self):
        """
        Returns a string representation of this cache.
        """
        m = self._ut_map
        lst = self._ut_keysList
        sz = self.size()
        lenSz = str(len(str(sz)))
        itemFmt = "%" + lenSz + "i. (ui: %" + lenSz + "i) [%s] --> [%s]"
        lines = []
        lines.append("Cache of class %s: low = %i, high = %i" % (self.__class__, self._ut_lowSize, self._ut_highSize))
        lines.append("From 'oldest' to 'newest' its %i items are:" % sz)
        for i in xrange(sz):
            key = lst[i]
            (val, updateIndex) = m[key]
            lines.append(itemFmt % (i, updateIndex, str(key), str(val)))
        result = "\n".join(lines)
        assert result is not None
        return result

    def _onRemoval(self, key, value):
        """
        The method that's called some time before the mapping from 'key' to
        'value' is removed from this cache.

        This implementation does nothing.
        """
        pass


    def _ut_incrementNextUpdateIndex(self):
        """
        Increases our next update index by one.
        """
        nextUi = self._ut_nextUpdateIndex + 1
        self._ut_nextUpdateIndex = nextUi
        if nextUi > self._ut_highSize * _ut_maxLruCacheUpdateIndexMultiple:
            ui2k = self._ut_buildUpdateIndexToKeyMap()
            self._ut_rebuildMapAndList(ui2k)

    def _ut_addNewMapping(self, key, value):
        """
        Adds a new mapping from 'key' to 'value' to this cache. It assumes
        that it doesn't already map 'key' to anything.
        """
        nextUi = self._ut_nextUpdateIndex
        self._ut_map[key] = (value, nextUi)
        self._ut_keysList.append(key)
        self._ut_nextUpdateIndex = nextUi + 1
            # we intentionally don't use _ut_incrementNextUpdateIndex()
            # here: the call to _ut_compact() next handles the case where
            # our next update index has gotten too large
        self._ut_compact()

    def _ut_compact(self):
        """
        Rebuilds this cache - possibly removing items from it in the process -
        iff it contains too many items or its next update index is too large.
        """
        highSz = self._ut_highSize
        sz = self.size()
        if sz > highSz:
            # Remove the least recently used item from this cache until we're
            # at our low size (and the update indices used are consecutive
            # starting at zero).
            ui2k = self._ut_buildUpdateIndexToKeyMap()
            self._ut_removeExcessUpdateIndexToKeyMappings(ui2k)
            self._ut_rebuildMapAndList(ui2k)
            assert self.size() == self._ut_lowSize
        else:
            maxNextUi = _ut_maxLruCacheUpdateIndexMultiple * highSz
            if self._ut_nextUpdateIndex > maxNextUi:
                # Rebuild our map and list so that the update indices used
                # are consecutive starting at zero.
                ui2k = self._ut_buildUpdateIndexToKeyMap()
                self._ut_rebuildMapAndList(ui2k)
                assert self._ut_nextUpdateIndex <= maxNextUi
            assert self.size() == sz

    def _ut_buildUpdateIndexToKeyMap(self):
        """
        Builds and returns a map from each 0-based index that is the update
        index (that is, the second item in the pair that a key is mapped to
        by _ut_map) for one of our keys to that key. (Each key should have a
        distinct update index.)
        """
        result = {}
        m = self._ut_map
        for (k, v) in m.items():
            ui = v[1]  # the update index
            assert ui not in result
            result[ui] = k
        assert result is not None
        return result

    def _ut_removeExcessUpdateIndexToKeyMappings(self, ui2k):
        """
        Removes from the update index to key map 'ui2k' enough keys so that
        it only contains _ut_lowSize keys.
        """
        # Remove the 'numToRemove' keys with the lowest update indices.
        sz = self.size()
        assert sz > self._ut_highSize
        numToRemove = sz - self._ut_lowSize
        m = self._ut_map
        for i in xrange(self._ut_nextUpdateIndex):
            key = ui2k.get(i)
            if key is not None:
                self._onRemoval(key, m[key][0])
                del ui2k[i]
                numToRemove -= 1
                if numToRemove == 0:
                    break  # for

    def _ut_rebuildMapAndList(self, ui2k):
        """
        Rebuilds/resets the values of our _ut_map and _ut_keysList fields
        from the information left in the update index to key map 'ui2k', and
        also resets our _ut_nextUpdateIndex field's value.
        """
        oldMap = self._ut_map
        newMap = {}
        newList = []
        for i in xrange(self._ut_nextUpdateIndex):
            key = ui2k.get(i)
            if key is not None:
                val = oldMap[key][0]
                newMap[key] = (val, len(newList))
                newList.append(key)
        newSize = len(newList)
        assert newSize == len(newMap)
        self._ut_map = newMap
        self._ut_keysList = newList
        self._ut_nextUpdateIndex = newSize


if __name__ == '__main__':
    # Test int-parsing functions.
    default = -666
    for txt in ["0", "hi", "  1", "2", "3   ", "   4   ", "5.0"]:
        for (min, max) in [(None, None), (0, 3), (1, 2), (None, 2), (2, None)]:
            print("*** min = %s, max = %s" % (str(min), str(max)))
            try:
                res = ut_parseInt(txt, maxValue = max, minValue = min)
                print("result of parsing '%s': [%s]" % (txt, res))
            except ValueError as ex:
                print("parsing '%s' failed: %s" % (txt, ex))
            res = ut_tryToParseInt(txt, default, minValue = min,
                                   maxValue = max)
            print("result of trying to parse '%s' (default = %s): [%s]" %
                  (txt, str(default), res))

    sep = os.sep
    print
    for p in ["/tmp", "", "/", "/tmp/somedir/"]:
        print("components of path '%s': [%s]" %
              (p, ", ".join(ut_pathnameComponents(p, sep))))
