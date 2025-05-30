#!/usr/bin/env python
#
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
Check if SCons.Platform.virtualenv.Virtualenv() works in SConscripts.
"""

import TestSCons
import SCons.Platform.virtualenv

test = TestSCons.TestSCons()

ve = SCons.Platform.virtualenv.Virtualenv()
if not ve:
    test.skip_test("Virtualenv is not active, skipping\n")

test.write('SConstruct', """\
DefaultEnvironment(tools=[])
print(f"virtualenv: {Virtualenv()!r}")
""")

if SCons.Platform.virtualenv.virtualenv_enabled_by_default:
    test.run(['-Q'])
else:
    test.run(['-Q', '--enable-virtualenv'])

test.must_contain_all_lines(test.stdout(), [f'virtualenv: {ve!r}'])

test.pass_test()

# Local Variables:
# tab-width:4
# indent-tabs-mode:nil
# End:
# vim: set expandtab tabstop=4 shiftwidth=4:
