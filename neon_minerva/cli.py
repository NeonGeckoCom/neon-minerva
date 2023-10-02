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

from pprint import pformat
from os.path import expanduser, relpath, isfile, isdir
from click_default_group import DefaultGroup
from unittest.runner import TextTestRunner
from unittest import makeSuite

from neon_minerva.version import __version__


def _init_tests(debug: bool = False):
    from os.path import join
    from os import makedirs
    from tempfile import mkdtemp
    base_dir = mkdtemp()
    config = join(base_dir, "config")
    data = join(base_dir, "data")
    cache = join(base_dir, "cache")
    makedirs(config, exist_ok=True)
    makedirs(data, exist_ok=True)
    makedirs(cache, exist_ok=True)
    os.environ["XDG_CONFIG_HOME"] = config
    os.environ["XDG_DATA_HOME"] = data
    os.environ["XDG_CACHE_HOME"] = cache

    if debug:
        os.environ["OVOS_DEFAULT_LOG_LEVEL"] = "DEBUG"

def _get_test_file(test_file: str) -> str:
    """
    Parse an input path to locate a test file that may be relative to `~` or the
    current working directory.
    @param test_file: test file argument
    @returns: best guess at the desired file path (may not exist)
    """
    test_file = expanduser(test_file)
    if not isfile(test_file):
        test_file = relpath(test_file)
    return test_file


def _get_skill_entrypoint(skill_entrypoint: str) -> str:
    """
    Parse an input skill entrypoint and resolve either a locally installed skill
    path, or an entrypoint for a plugin skill.
    @param skill_entrypoint: Plugin entrypoint or path to skill
    @returns: absolute file path if exists, else input entrypoint
    """
    skill_path = expanduser(skill_entrypoint)
    if not isdir(skill_path):
        skill_path = relpath(skill_path)
    if isdir(skill_path):
        return skill_path
    return skill_entrypoint


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
@click.option('--debug', is_flag=True, default=False,
              help="Flag to enable debug logging")
@click.argument("skill_entrypoint")
@click.argument("test_file")
def test_resources(skill_entrypoint, test_file, debug):
    _init_tests(debug)
    os.environ["TEST_SKILL_ENTRYPOINT"] = _get_skill_entrypoint(skill_entrypoint)
    test_file = _get_test_file(test_file)
    if not isfile(test_file):
        click.echo(f"Could not find test file: {test_file}")
        exit(2)
    os.environ["RESOURCE_TEST_FILE"] = test_file
    from neon_minerva.tests.test_skill_resources import TestSkillResources
    TextTestRunner().run(makeSuite(TestSkillResources))


@neon_minerva_cli.command
@click.option('--debug', is_flag=True, default=False,
              help="Flag to enable debug logging")
@click.option('--padacioso', is_flag=True, default=False,
              help="Flag to enable testing with Padacioso instead of Padatious")
@click.argument("skill_entrypoint")
@click.argument("test_file")
def test_intents(skill_entrypoint, test_file, debug, padacioso):
    _init_tests(debug)
    os.environ["TEST_PADACIOSO"] = "true" if padacioso else "false"
    os.environ["TEST_SKILL_ENTRYPOINT"] = _get_skill_entrypoint(skill_entrypoint)
    test_file = _get_test_file(test_file)
    if not isfile(test_file):
        click.echo(f"Could not find test file: {test_file}")
        exit(2)
    os.environ["INTENT_TEST_FILE"] = test_file
    from neon_minerva.tests.test_skill_intents import TestSkillIntentMatching
    TextTestRunner().run(makeSuite(TestSkillIntentMatching))


@neon_minerva_cli.command
@click.option('-l', '--lang', default="en-us",
              help="Language of test_file inputs")
@click.argument("test_file")
def test_text_inputs(lang, test_file):
    from neon_utils.file_utils import load_commented_file
    from neon_minerva.integration.text import TextIntentTests
    prompts = load_commented_file(test_file).split('\n')
    click.echo(f"Testing {len(prompts)} prompts")
    runner = TextIntentTests(prompts, lang)
    results = runner.run_test()
    click.echo(pformat(results))
