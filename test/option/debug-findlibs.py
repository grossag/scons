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

import TestSCons

_python_ = TestSCons._python_

test = TestSCons.TestSCons()

test.subdir('sub1', 'sub2')

test.write('cat.py', """\
import sys
with open(sys.argv[1], 'wb') as ofp:
    for f in sys.argv[2:]:
        with open(f, 'rb') as ifp:
            ofp.write(ifp.read())
""")

test.write('SConstruct', """\
DefaultEnvironment(tools=[])
env = Environment(OBJSUFFIX = '.ooo', PROGSUFFIX = '.xxx',
                  LIBPATH = ['sub1', 'sub2', '.'],
                  LIBS = ['iii', 'jjj', 'kkk', 'lll', 'mmm'],
                  LIBPREFIXES = ['a-', 'b-', 'c-'],
                  LIBSUFFIXES = ['.aaa', '.bbb', '.ccc'],
                  LINKCOM = r'%(_python_)s cat.py $TARGET $SOURCES')
env.Program('foo', 'a.ooo',)
""" % locals())

test.write('a.ooo', "a.ooo\n")

test.write('a-iii.aaa', "a-iii.aaa\n")
test.write(['sub1', 'b-jjj.bbb'], "b-jjj.bbb\n")
test.write(['sub2', 'c-kkk.ccc'], "c-kkk.ccc\n")
test.write('a-lll.ccc', "a-lll.ccc\n")

test.run(arguments = "--debug=findlibs foo.xxx",
         stdout = test.wrap_stdout("""\
  findlibs: looking for 'a-iii.aaa' in 'sub1' ...
  findlibs: looking for 'a-iii.aaa' in 'sub2' ...
  findlibs: looking for 'a-iii.aaa' in '.' ...
  findlibs: ... FOUND 'a-iii.aaa' in '.'
  findlibs: looking for 'b-iii.aaa' in 'sub1' ...
  findlibs: looking for 'b-iii.aaa' in 'sub2' ...
  findlibs: looking for 'b-iii.aaa' in '.' ...
  findlibs: looking for 'c-iii.aaa' in 'sub1' ...
  findlibs: looking for 'c-iii.aaa' in 'sub2' ...
  findlibs: looking for 'c-iii.aaa' in '.' ...
  findlibs: looking for 'a-iii.bbb' in 'sub1' ...
  findlibs: looking for 'a-iii.bbb' in 'sub2' ...
  findlibs: looking for 'a-iii.bbb' in '.' ...
  findlibs: looking for 'b-iii.bbb' in 'sub1' ...
  findlibs: looking for 'b-iii.bbb' in 'sub2' ...
  findlibs: looking for 'b-iii.bbb' in '.' ...
  findlibs: looking for 'c-iii.bbb' in 'sub1' ...
  findlibs: looking for 'c-iii.bbb' in 'sub2' ...
  findlibs: looking for 'c-iii.bbb' in '.' ...
  findlibs: looking for 'a-iii.ccc' in 'sub1' ...
  findlibs: looking for 'a-iii.ccc' in 'sub2' ...
  findlibs: looking for 'a-iii.ccc' in '.' ...
  findlibs: looking for 'b-iii.ccc' in 'sub1' ...
  findlibs: looking for 'b-iii.ccc' in 'sub2' ...
  findlibs: looking for 'b-iii.ccc' in '.' ...
  findlibs: looking for 'c-iii.ccc' in 'sub1' ...
  findlibs: looking for 'c-iii.ccc' in 'sub2' ...
  findlibs: looking for 'c-iii.ccc' in '.' ...
  findlibs: looking for 'a-jjj.aaa' in 'sub1' ...
  findlibs: looking for 'a-jjj.aaa' in 'sub2' ...
  findlibs: looking for 'a-jjj.aaa' in '.' ...
  findlibs: looking for 'b-jjj.aaa' in 'sub1' ...
  findlibs: looking for 'b-jjj.aaa' in 'sub2' ...
  findlibs: looking for 'b-jjj.aaa' in '.' ...
  findlibs: looking for 'c-jjj.aaa' in 'sub1' ...
  findlibs: looking for 'c-jjj.aaa' in 'sub2' ...
  findlibs: looking for 'c-jjj.aaa' in '.' ...
  findlibs: looking for 'a-jjj.bbb' in 'sub1' ...
  findlibs: looking for 'a-jjj.bbb' in 'sub2' ...
  findlibs: looking for 'a-jjj.bbb' in '.' ...
  findlibs: looking for 'b-jjj.bbb' in 'sub1' ...
  findlibs: ... FOUND 'b-jjj.bbb' in 'sub1'
  findlibs: looking for 'c-jjj.bbb' in 'sub1' ...
  findlibs: looking for 'c-jjj.bbb' in 'sub2' ...
  findlibs: looking for 'c-jjj.bbb' in '.' ...
  findlibs: looking for 'a-jjj.ccc' in 'sub1' ...
  findlibs: looking for 'a-jjj.ccc' in 'sub2' ...
  findlibs: looking for 'a-jjj.ccc' in '.' ...
  findlibs: looking for 'b-jjj.ccc' in 'sub1' ...
  findlibs: looking for 'b-jjj.ccc' in 'sub2' ...
  findlibs: looking for 'b-jjj.ccc' in '.' ...
  findlibs: looking for 'c-jjj.ccc' in 'sub1' ...
  findlibs: looking for 'c-jjj.ccc' in 'sub2' ...
  findlibs: looking for 'c-jjj.ccc' in '.' ...
  findlibs: looking for 'a-kkk.aaa' in 'sub1' ...
  findlibs: looking for 'a-kkk.aaa' in 'sub2' ...
  findlibs: looking for 'a-kkk.aaa' in '.' ...
  findlibs: looking for 'b-kkk.aaa' in 'sub1' ...
  findlibs: looking for 'b-kkk.aaa' in 'sub2' ...
  findlibs: looking for 'b-kkk.aaa' in '.' ...
  findlibs: looking for 'c-kkk.aaa' in 'sub1' ...
  findlibs: looking for 'c-kkk.aaa' in 'sub2' ...
  findlibs: looking for 'c-kkk.aaa' in '.' ...
  findlibs: looking for 'a-kkk.bbb' in 'sub1' ...
  findlibs: looking for 'a-kkk.bbb' in 'sub2' ...
  findlibs: looking for 'a-kkk.bbb' in '.' ...
  findlibs: looking for 'b-kkk.bbb' in 'sub1' ...
  findlibs: looking for 'b-kkk.bbb' in 'sub2' ...
  findlibs: looking for 'b-kkk.bbb' in '.' ...
  findlibs: looking for 'c-kkk.bbb' in 'sub1' ...
  findlibs: looking for 'c-kkk.bbb' in 'sub2' ...
  findlibs: looking for 'c-kkk.bbb' in '.' ...
  findlibs: looking for 'a-kkk.ccc' in 'sub1' ...
  findlibs: looking for 'a-kkk.ccc' in 'sub2' ...
  findlibs: looking for 'a-kkk.ccc' in '.' ...
  findlibs: looking for 'b-kkk.ccc' in 'sub1' ...
  findlibs: looking for 'b-kkk.ccc' in 'sub2' ...
  findlibs: looking for 'b-kkk.ccc' in '.' ...
  findlibs: looking for 'c-kkk.ccc' in 'sub1' ...
  findlibs: looking for 'c-kkk.ccc' in 'sub2' ...
  findlibs: ... FOUND 'c-kkk.ccc' in 'sub2'
  findlibs: looking for 'a-lll.aaa' in 'sub1' ...
  findlibs: looking for 'a-lll.aaa' in 'sub2' ...
  findlibs: looking for 'a-lll.aaa' in '.' ...
  findlibs: looking for 'b-lll.aaa' in 'sub1' ...
  findlibs: looking for 'b-lll.aaa' in 'sub2' ...
  findlibs: looking for 'b-lll.aaa' in '.' ...
  findlibs: looking for 'c-lll.aaa' in 'sub1' ...
  findlibs: looking for 'c-lll.aaa' in 'sub2' ...
  findlibs: looking for 'c-lll.aaa' in '.' ...
  findlibs: looking for 'a-lll.bbb' in 'sub1' ...
  findlibs: looking for 'a-lll.bbb' in 'sub2' ...
  findlibs: looking for 'a-lll.bbb' in '.' ...
  findlibs: looking for 'b-lll.bbb' in 'sub1' ...
  findlibs: looking for 'b-lll.bbb' in 'sub2' ...
  findlibs: looking for 'b-lll.bbb' in '.' ...
  findlibs: looking for 'c-lll.bbb' in 'sub1' ...
  findlibs: looking for 'c-lll.bbb' in 'sub2' ...
  findlibs: looking for 'c-lll.bbb' in '.' ...
  findlibs: looking for 'a-lll.ccc' in 'sub1' ...
  findlibs: looking for 'a-lll.ccc' in 'sub2' ...
  findlibs: looking for 'a-lll.ccc' in '.' ...
  findlibs: ... FOUND 'a-lll.ccc' in '.'
  findlibs: looking for 'b-lll.ccc' in 'sub1' ...
  findlibs: looking for 'b-lll.ccc' in 'sub2' ...
  findlibs: looking for 'b-lll.ccc' in '.' ...
  findlibs: looking for 'c-lll.ccc' in 'sub1' ...
  findlibs: looking for 'c-lll.ccc' in 'sub2' ...
  findlibs: looking for 'c-lll.ccc' in '.' ...
  findlibs: looking for 'a-mmm.aaa' in 'sub1' ...
  findlibs: looking for 'a-mmm.aaa' in 'sub2' ...
  findlibs: looking for 'a-mmm.aaa' in '.' ...
  findlibs: looking for 'b-mmm.aaa' in 'sub1' ...
  findlibs: looking for 'b-mmm.aaa' in 'sub2' ...
  findlibs: looking for 'b-mmm.aaa' in '.' ...
  findlibs: looking for 'c-mmm.aaa' in 'sub1' ...
  findlibs: looking for 'c-mmm.aaa' in 'sub2' ...
  findlibs: looking for 'c-mmm.aaa' in '.' ...
  findlibs: looking for 'a-mmm.bbb' in 'sub1' ...
  findlibs: looking for 'a-mmm.bbb' in 'sub2' ...
  findlibs: looking for 'a-mmm.bbb' in '.' ...
  findlibs: looking for 'b-mmm.bbb' in 'sub1' ...
  findlibs: looking for 'b-mmm.bbb' in 'sub2' ...
  findlibs: looking for 'b-mmm.bbb' in '.' ...
  findlibs: looking for 'c-mmm.bbb' in 'sub1' ...
  findlibs: looking for 'c-mmm.bbb' in 'sub2' ...
  findlibs: looking for 'c-mmm.bbb' in '.' ...
  findlibs: looking for 'a-mmm.ccc' in 'sub1' ...
  findlibs: looking for 'a-mmm.ccc' in 'sub2' ...
  findlibs: looking for 'a-mmm.ccc' in '.' ...
  findlibs: looking for 'b-mmm.ccc' in 'sub1' ...
  findlibs: looking for 'b-mmm.ccc' in 'sub2' ...
  findlibs: looking for 'b-mmm.ccc' in '.' ...
  findlibs: looking for 'c-mmm.ccc' in 'sub1' ...
  findlibs: looking for 'c-mmm.ccc' in 'sub2' ...
  findlibs: looking for 'c-mmm.ccc' in '.' ...
%(_python_)s cat.py foo.xxx a.ooo
""" % locals()))

test.must_match('foo.xxx', "a.ooo\n")

test.pass_test()

# Local Variables:
# tab-width:4
# indent-tabs-mode:nil
# End:
# vim: set expandtab tabstop=4 shiftwidth=4:
