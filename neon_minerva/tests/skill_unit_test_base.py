# NEON AI (TM) SOFTWARE, Software Development Kit & Application Framework
# All trademark and other rights reserved by their respective owners
# Copyright 2008-2022 Neongecko.com Inc.
# Contributors: Daniel McKnight, Guy Daniels, Elon Gasper, Richard Leeds,
# Regina Bloomstine, Casimiro Ferreira, Andrii Pernatii, Kirill Hrymailo
# BSD-3 License
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

import unittest
import shutil

from os import environ, getenv
from os.path import dirname, join
from unittest.mock import Mock
from ovos_utils.messagebus import FakeBus

from neon_minerva.skill import get_skill_object


class SkillTestCase(unittest.TestCase):
    # Define test directories
    test_fs = join(dirname(__file__), "skill_fs")
    data_dir = join(test_fs, "data")
    conf_dir = join(test_fs, "config")
    environ["XDG_DATA_HOME"] = data_dir
    environ["XDG_CONFIG_HOME"] = conf_dir

    # Define static parameters
    bus = FakeBus()
    bus.run_forever()
    test_skill_id = 'test_skill.test'

    skill = None

    @classmethod
    def setUpClass(cls) -> None:
        # Get test skill
        skill_entrypoint = getenv("TEST_SKILL_ENTRYPOINT")
        if not skill_entrypoint:
            from ovos_plugin_manager.skills import find_skill_plugins
            skill_entrypoints = list(find_skill_plugins().keys())
            assert len(skill_entrypoints) == 1
            skill_entrypoint = skill_entrypoints[0]

        cls.skill = get_skill_object(skill_entrypoint=skill_entrypoint,
                                     skill_id=cls.test_skill_id, bus=cls.bus)
        # Override speak and speak_dialog to test passed arguments
        cls.skill.speak = Mock()
        cls.skill.speak_dialog = Mock()

    def setUp(self):
        self.skill.speak.reset_mock()
        self.skill.speak_dialog.reset_mock()

    @classmethod
    def tearDownClass(cls) -> None:
        shutil.rmtree(cls.test_fs)
