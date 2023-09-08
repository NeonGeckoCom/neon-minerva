# NEON AI (TM) SOFTWARE, Software Development Kit & Application Development System
# All trademark and other rights reserved by their respective owners
# Copyright 2008-2021 Neongecko.com Inc.
# BSD-3
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
# 1. Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
# 3. Neither the name of the copyright holder nor the names of its
#    contributors may be used to endorse or promote products derived from this
#    software without specific prior written permission.
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO,
# THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
# PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR
# CONTRIBUTORS  BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
# EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA,
# OR PROFITS;  OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
# LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
# NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE,  EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import os
import click

from os.path import expanduser, relpath, isfile
from click_default_group import DefaultGroup
from unittest.runner import TextTestRunner
from unittest import makeSuite

from neon_minerva.version import __version__


def _init_test_dir():
    from os.path import join
    from os import makedirs
    from tempfile import mkdtemp
    base_dir = mkdtemp()
    config = join(base_dir, "config")
    data = join(base_dir, "data")
    makedirs(config, exist_ok=True)
    makedirs(data, exist_ok=True)
    os.environ["XDG_CONFIG_HOME"] = config
    os.environ["XDG_DATA_HOME"] = data


@click.group("minerva", cls=DefaultGroup,
             no_args_is_help=True, invoke_without_command=True,
             help="Minerva: Modular INtelligent Evaluation for a Reliable "
                  "Voice Assistant.\n\n"
                  "See also: minerva COMMAND --help")
@click.option("--version", "-v", is_flag=True, required=False,
              help="Print the current version")
def neon_minerva_cli(version: bool = False):
    if version:
        click.echo(f"Minerva version {__version__}")


@neon_minerva_cli.command
@click.argument("skill_entrypoint")
@click.argument("test_file")
def test_resources(skill_entrypoint, test_file):
    _init_test_dir()
    os.environ["TEST_SKILL_ENTRYPOINT"] = skill_entrypoint
    test_file = expanduser(test_file)
    if not isfile(test_file):
        test_file = relpath(test_file)
    if not isfile(test_file):
        click.echo(f"Could not find test file: {test_file}")
        exit(2)
    os.environ["RESOURCE_TEST_FILE"] = test_file
    from neon_minerva.tests.test_skill_resources import TestSkillLoading
    TextTestRunner().run(makeSuite(TestSkillLoading))

