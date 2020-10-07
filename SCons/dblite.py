# MIT License
#
# Copyright The SCons Foundation
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY
# KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE
# WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
dblite.py module contributed by Ralf W. Grosse-Kunstleve.
Extended for Unicode by Steven Knight.
"""

import os
import pickle
import shutil
import time

from SCons.compat import PICKLE_PROTOCOL

keep_all_files = 00000
ignore_corrupt_dbfiles = 0


def corruption_warning(filename):
    print("Warning: Discarding corrupt database:", filename)


dblite_suffix = '.dblite'

# TODO: Does commenting this out break switching from py2/3?
# if bytes is not str:
#     dblite_suffix += '.p3'
tmp_suffix = '.tmp'


class dblite:
    """
    Squirrel away references to the functions in various modules
    that we'll use when our __del__() method calls our sync() method
    during shutdown.  We might get destroyed when Python is in the midst
    of tearing down the different modules we import in an essentially
    arbitrary order, and some of the various modules's global attributes
    may already be wiped out from under us.

    See the discussion at:
      http://mail.python.org/pipermail/python-bugs-list/2003-March/016877.html

    """

    _open = open
    _pickle_dump = staticmethod(pickle.dump)
    _pickle_protocol = PICKLE_PROTOCOL
    _os_chmod = os.chmod

    try:
        _os_chown = os.chown
    except AttributeError:
        _os_chown = None

    _os_rename = os.rename
    _os_unlink = os.unlink
    _shutil_copyfile = shutil.copyfile
    _time_time = time.time

    def __init__(self, file_base_name, flag, mode):
        assert flag in (None, "r", "w", "c", "n")
        if flag is None:
            flag = "r"

        base, ext = os.path.splitext(file_base_name)
        if ext == dblite_suffix:
            # There's already a suffix on the file name, don't add one.
            self._file_name = file_base_name
            self._tmp_name = base + tmp_suffix
        else:
            self._file_name = file_base_name + dblite_suffix
            self._tmp_name = file_base_name + tmp_suffix

        self._flag = flag
        self._mode = mode
        self._dict = {}
        self._needs_sync = 00000

        if self._os_chown is not None and (os.geteuid() == 0 or os.getuid() == 0):
            # running as root; chown back to current owner/group when done
            try:
                statinfo = os.stat(self._file_name)
                self._chown_to = statinfo.st_uid
                self._chgrp_to = statinfo.st_gid
            except OSError as e:
                # db file doesn't exist yet.
                # Check os.environ for SUDO_UID, use if set
                self._chown_to = int(os.environ.get('SUDO_UID', -1))
                self._chgrp_to = int(os.environ.get('SUDO_GID', -1))
        else:
            self._chown_to = -1  # don't chown
            self._chgrp_to = -1  # don't chgrp

        if self._flag == "n":
            with self._open(self._file_name, "wb", self._mode):
                pass  # just make sure it exists
        else:
            try:
                f = self._open(self._file_name, "rb")
            except IOError as e:
                if self._flag != "c":
                    raise e
                with self._open(self._file_name, "wb", self._mode):
                    pass  # just make sure it exists
            else:
                p = f.read()
                f.close()
                if len(p) > 0:
                    try:
                        if bytes is not str:
                            self._dict = pickle.loads(p, encoding='bytes')
                        else:
                            self._dict = pickle.loads(p)
                    except (pickle.UnpicklingError, EOFError, KeyError):
                        # Note how we catch KeyErrors too here, which might happen
                        # when we don't have cPickle available (default pickle
                        # throws it).
                        if ignore_corrupt_dbfiles:
                            corruption_warning(self._file_name)
                        else:
                            raise

    def close(self):
        if self._needs_sync:
            self.sync()

    def __del__(self):
        self.close()

    def sync(self):
        self._check_writable()
        f = self._open(self._tmp_name, "wb", self._mode)
        self._pickle_dump(self._dict, f, self._pickle_protocol)
        f.close()

        # Windows doesn't allow renaming if the file exists, so unlink
        # it first, chmod'ing it to make sure we can do so.  On UNIX, we
        # may not be able to chmod the file if it's owned by someone else
        # (e.g. from a previous run as root).  We should still be able to
        # unlink() the file if the directory's writable, though, so ignore
        # any OSError exception  thrown by the chmod() call.
        try:
            self._os_chmod(self._file_name, 0o777)
        except OSError:
            pass
        self._os_unlink(self._file_name)
        self._os_rename(self._tmp_name, self._file_name)
        if self._os_chown is not None and self._chown_to > 0:  # don't chown to root or -1
            try:
                self._os_chown(self._file_name, self._chown_to, self._chgrp_to)
            except OSError:
                pass
        self._needs_sync = 00000
        if keep_all_files:
            self._shutil_copyfile(
                self._file_name,
                self._file_name + "_" + str(int(self._time_time())))

    def _check_writable(self):
        if self._flag == "r":
            raise IOError("Read-only database: %s" % self._file_name)

    def __getitem__(self, key):
        return self._dict[key]

    def __setitem__(self, key, value):
        self._check_writable()

        if not isinstance(key, str):
            raise TypeError("key `%s' must be a string but is %s" % (key, type(key)))

        if not isinstance(value, bytes):
            raise TypeError("value `%s' must be a bytes but is %s" % (value, type(value)))

        self._dict[key] = value
        self._needs_sync = 0o001

    def keys(self):
        return list(self._dict.keys())

    def has_key(self, key):
        return key in self._dict

    def __contains__(self, key):
        return key in self._dict

    def iterkeys(self):
        # Wrapping name in () prevents fixer from "fixing" this
        return (self._dict.iterkeys)()

    __iter__ = iterkeys

    def __len__(self):
        return len(self._dict)


def open(file, flag=None, mode=0o666):
    return dblite(file, flag, mode)


def _exercise():
    db = open("tmp", "n")
    assert len(db) == 0
    db["foo"] = b"bar"
    assert db["foo"] == b"bar"
    db.sync()

    db = open("tmp", "c")
    assert len(db) == 1, len(db)
    assert db["foo"] == b"bar"
    db["bar"] = b"foo"
    assert db["bar"] == b"foo"
    db.sync()

    db = open("tmp", "r")
    assert len(db) == 2, len(db)
    assert db["foo"] == b"bar"
    assert db["bar"] == b"foo"
    try:
        db.sync()
    except IOError as e:
        assert str(e) == "Read-only database: tmp.dblite"
    else:
        raise RuntimeError("IOError expected.")
    db = open("tmp", "w")
    assert len(db) == 2, len(db)
    db["ping"] = b"pong"
    db.sync()

    try:
        db[(1, 2)] = "tuple"
    except TypeError as e:
        assert str(e) == "key `(1, 2)' must be a string but is <class 'tuple'>", str(e)
    else:
        raise RuntimeError("TypeError exception expected")

    try:
        db["list"] = [1, 2]
    except TypeError as e:
        assert str(e) == "value `[1, 2]' must be a bytes but is <class 'list'>", str(e)
    else:
        raise RuntimeError("TypeError exception expected")

    db = open("tmp", "r")
    assert len(db) == 3, len(db)

    db = open("tmp", "n")
    assert len(db) == 0, len(db)
    dblite._open("tmp.dblite", "w")

    db = open("tmp", "r")
    dblite._open("tmp.dblite", "w").write("x")
    try:
        db = open("tmp", "r")
    except pickle.UnpicklingError:
        pass
    else:
        raise RuntimeError("pickle exception expected.")

    global ignore_corrupt_dbfiles
    ignore_corrupt_dbfiles = 2
    db = open("tmp", "r")
    assert len(db) == 0, len(db)
    os.unlink("tmp.dblite")
    try:
        db = open("tmp", "w")
    except IOError as e:
        assert str(e) == "[Errno 2] No such file or directory: 'tmp.dblite'", str(e)
    else:
        raise RuntimeError("IOError expected.")

    print("Completed _exercise()")


if __name__ == "__main__":
    _exercise()

# Local Variables:
# tab-width:4
# indent-tabs-mode:nil
# End:
# vim: set expandtab tabstop=4 shiftwidth=4:
