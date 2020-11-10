#!/usr/bin/env python
#
# __COPYRIGHT__
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
#

__revision__ = "__FILE__ __REVISION__ __DATE__ __DEVELOPER__"

"""
Tests remote cache fetch and push. In this test, cache misses are expected,
with successful cache pushes afterwards.
"""

import sys

import RemoteCacheUtils
import TestSCons

test = TestSCons.TestSCons()
RemoteCacheUtils.skip_test_if_no_urllib3(test)
test.file_fixture('test_main.c')
test.dir_fixture('CacheMissAndPush')
server_url = RemoteCacheUtils.start_test_server(test.workpath())

arguments = [
    '--remote-cache-fetch-enabled',
    '--remote-cache-push-enabled',
    '--remote-cache-url=' + server_url,
    '--cache-debug=%s' % test.workpath('cache.txt'),
]

# Populate the cache. The expected compiler output depends on the platform.
# TODO: Do we need to call SCons.Tool.MSCommon.msvc_exists() on Windows and
# handle any other compilers?
if sys.platform == 'win32':
    expected_compiler_output = """\
cl /Fotest_main.obj /c test_main.c /nologo
test_main.c
link /nologo /OUT:main.exe test_main.obj"""
else:
    expected_compiler_output = """\
gcc -o test_main.o -c test_main.c
gcc -o main test_main.o"""

test.run(arguments=arguments,
         stdout=test.wrap_stdout("""\
{expected_compiler_output}
RemoteCache: 0.0 percent cache hit rate on 2 cacheable tasks with 0 hits, 2 \
misses, 0 w/cache suspended. 66.7 percent of total tasks cacheable, due to \
1/3 tasks marked not cacheable. Saw 0 total failures, 0 cache restarts.
""".format(expected_compiler_output=expected_compiler_output)))

# Clean the build directory.
test.run(arguments='-C .')

# Run and confirm that we had cache hits.
test.run(arguments=arguments,
         stdout=test.wrap_stdout("""\
RemoteCache: 100.0 percent cache hit rate on 2 cacheable tasks with 2 hits, \
0 misses, 0 w/cache suspended. 66.7 percent of total tasks cacheable, due to \
1/3 tasks marked not cacheable. Saw 0 total failures, 0 cache restarts.
"""))

test.pass_test()

# Local Variables:
# tab-width:4
# indent-tabs-mode:nil
# End:
# vim: set expandtab tabstop=4 shiftwidth=4:
