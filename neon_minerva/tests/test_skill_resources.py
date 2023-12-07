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
import json

from os import getenv
from ovos_utils.messagebus import FakeBus

from neon_minerva.skill import get_skill_object, load_resource_tests


class TestSkillResources(unittest.TestCase):
    # Static parameters
    messages = list()
    bus = FakeBus()
    bus.run_forever()
    test_skill_id = 'test_skill.test'

    # Define skill and resource spec to use in tests
    resources = load_resource_tests(getenv("RESOURCE_TEST_FILE"))
    skill_entrypoint = getenv("TEST_SKILL_ENTRYPOINT")

    # Specify valid languages to test
    supported_languages = resources['languages']

    # Specify skill intents as sets
    adapt_intents = set(resources['intents']['adapt'])
    padatious_intents = set(resources['intents']['padatious'])

    # regex entities, not necessarily filenames
    regex = set(resources['regex'])
    # vocab is lowercase .voc file basenames
    vocab = set(resources['vocab'])
    # dialog is .dialog file basenames (case-sensitive)
    dialog = set(resources['dialog'])

    core_config_patch = {"secondary_langs": supported_languages}

    @classmethod
    def setUpClass(cls) -> None:
        cls.bus.on("message", cls._on_message)

        cls.skill = get_skill_object(skill_entrypoint=cls.skill_entrypoint,
                                     bus=cls.bus, skill_id=cls.test_skill_id,
                                     config_patch=cls.core_config_patch)

        cls.adapt_intents = {f'{cls.test_skill_id}:{intent}'
                             for intent in cls.adapt_intents}
        cls.padatious_intents = {f'{cls.test_skill_id}:{intent}'
                                 for intent in cls.padatious_intents}

    @classmethod
    def _on_message(cls, message):
        cls.messages.append(json.loads(message))

    def test_skill_setup(self):
        self.assertEqual(self.skill.skill_id, self.test_skill_id)
        self.assertEqual(set([self.skill._core_lang] +
                             self.skill._secondary_langs),
                         set(self.supported_languages),
                         f"expected={self.supported_languages}")

    def test_intent_registration(self):
        registered_adapt = list()
        registered_padatious = dict()
        registered_vocab = dict()
        registered_regex = dict()
        for msg in self.messages:
            if msg["type"] == "register_intent":
                registered_adapt.append(msg["data"]["name"])
            elif msg["type"] == "padatious:register_intent":
                lang = msg["data"]["lang"]
                registered_padatious.setdefault(lang, list())
                registered_padatious[lang].append(msg["data"]["name"])
            elif msg["type"] == "register_vocab":
                lang = msg["data"]["lang"]
                if msg['data'].get('regex'):
                    registered_regex.setdefault(lang, dict())
                    regex = msg["data"]["regex"].split(
                        '<', 1)[1].split('>', 1)[0].replace(
                        self.test_skill_id.replace('.', '_'), '')
                    registered_regex[lang].setdefault(regex, list())
                    registered_regex[lang][regex].append(msg["data"]["regex"])
                else:
                    registered_vocab.setdefault(lang, dict())
                    voc_filename = msg["data"]["entity_type"].replace(
                        self.test_skill_id.replace('.', '_'), '').lower()
                    registered_vocab[lang].setdefault(voc_filename, list())
                    registered_vocab[lang][voc_filename].append(
                        msg["data"]["entity_value"])
        self.assertEqual(set(registered_adapt), self.adapt_intents,
                         registered_adapt)
        for lang in self.supported_languages:
            if self.padatious_intents:
                self.assertEqual(set(registered_padatious[lang]),
                                 self.padatious_intents,
                                 registered_padatious[lang])
            if self.vocab:
                self.assertEqual(set(registered_vocab[lang].keys()),
                                 self.vocab, registered_vocab)
            if self.regex:
                self.assertEqual(set(registered_regex[lang].keys()),
                                 self.regex, registered_regex)
            for voc in self.vocab:
                # Ensure every vocab file has at least one entry
                self.assertGreater(len(registered_vocab[lang][voc]), 0)
            for rx in self.regex:
                # Ensure every rx file has exactly one entry
                self.assertTrue(all((rx in line for line in
                                     registered_regex[lang][rx])), self.regex)

    def test_dialog_files(self):
        for lang in self.supported_languages:
            dialogs = self.skill._lang_resources[lang].dialog_renderer.templates
            for dialog in self.dialog:
                self.assertIn(dialog, dialogs.keys(),
                              f"lang={lang}")

    # TODO: Consider adding tests for resource file existence
