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
from typing import Optional

import yaml

from os.path import expanduser, isfile

from ovos_utils.messagebus import FakeBus
from ovos_workshop.skills.base import BaseSkill


def get_skill_object(skill_entrypoint: str, bus: FakeBus,
                     skill_id: str, config_patch: Optional[dict] = None) -> BaseSkill:
    """
    Get an initialized skill object by entrypoint with the requested skill_id.
    @param skill_entrypoint: Skill plugin entrypoint
    @param bus: FakeBus instance to bind to skill for testing
    @param skill_id: skill_id to initialize skill with
    @returns: Initialized skill object
    """
    if config_patch:
        from ovos_config.config import update_mycroft_config
        update_mycroft_config(config_patch)
    from ovos_plugin_manager.skills import find_skill_plugins
    plugins = find_skill_plugins()
    if skill_entrypoint not in plugins:
        raise ValueError(f"Requested skill not found: {skill_entrypoint}")
    plugin = plugins[skill_entrypoint]
    skill = plugin(bus=bus, skill_id=skill_id)
    return skill


def load_resource_tests(test_file: str) -> dict:
    """
    Load resource tests from a file
    @param test_file: Test file to load
    @returns: Loaded test spec
    """
    test_file = expanduser(test_file)
    if not isfile(test_file):
        raise FileNotFoundError(test_file)
    with open(test_file) as f:
        resources = yaml.safe_load(f)
    return resources


if __name__ == "__main__":
    get_skill_object("skill-about.neongeckocom", FakeBus(), "test")