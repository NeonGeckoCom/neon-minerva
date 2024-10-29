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

from os import getenv
from os.path import join, exists
from unittest.mock import Mock

from ovos_bus_client import Message
from ovos_utils.messagebus import FakeBus
from ovos_utils.log import LOG

from neon_minerva.exceptions import IntentException
from neon_minerva.skill import get_skill_object, load_intent_tests
from neon_minerva.intent_services.padatious import PadatiousContainer, TestPadatiousMatcher
from neon_minerva.intent_services.adapt import AdaptContainer
from neon_minerva.intent_services.padacioso import PadaciosoContainer
from neon_minerva.intent_services.common_query import CommonQuery
from neon_minerva.intent_services import IntentMatch


class TestSkillIntentMatching(unittest.TestCase):
    # Static parameters
    bus = FakeBus()
    bus.run_forever()
    test_skill_id = 'test_skill.test'
    padatious_cache = join(getenv("XDG_CACHE_HOME"), "padatious")

    # Define skill and resource spec to use in tests
    valid_intents = load_intent_tests(getenv("INTENT_TEST_FILE"))
    skill_entrypoint = getenv("TEST_SKILL_ENTRYPOINT")

    # Populate configuration
    languages = list(valid_intents.keys())
    core_config_patch = {"secondary_langs": languages}
    negative_intents = valid_intents.pop('unmatched intents', dict())
    common_query = valid_intents.pop("common query", dict())

    # Define intent parsers for tests
    if getenv("TEST_PADACIOSO") == "true":
        container = PadaciosoContainer
    else:
        try:
            from padatious import IntentContainer
            container = PadatiousContainer
        except ImportError as e:
            LOG.error(f"Padatious not installed. Install "
                      f"neon-minerva[padatious] to get Padatious requirements")
            if getenv("TEST_PADACIOSO") is None:
                # Ambiguous request, just use Padacioso
                container = PadaciosoContainer
            else:
                # Explicitly requested Padatious/non-Padacioso
                raise e
    padatious_services = dict()
    adapt_services = dict()
    for lang in languages:
        padatious_services[lang] = container(lang, join(padatious_cache, lang),
                                             bus)
        adapt_services[lang] = AdaptContainer(lang, bus)

    if common_query:
        common_query_service = CommonQuery(bus)

    skill = get_skill_object(skill_entrypoint=skill_entrypoint,
                             skill_id=test_skill_id, bus=bus,
                             config_patch=core_config_patch)

    @classmethod
    def tearDownClass(cls) -> None:
        import shutil
        for service in cls.padatious_services.values():
            try:
                if exists(service.cache_dir):
                    shutil.rmtree(service.cache_dir)
            except Exception as e:
                LOG.exception(e)

    def test_intents(self):
        for lang in self.valid_intents.keys():
            self.assertIsInstance(lang.split('-')[0], str)
            self.assertIsInstance(lang.split('-')[1], str)
            for intent, examples in self.valid_intents[lang].items():
                # TODO: Better method to determine parser?
                if intent.endswith('.intent'):
                    # TODO: Configurable min confidence
                    parser = TestPadatiousMatcher(self.padatious_services[lang],
                                                  include_med=True,
                                                  include_low=True)
                else:
                    parser = self.adapt_services[lang]

                for utt in examples:
                    if isinstance(utt, dict):
                        data = list(utt.values())[0]
                        utt = list(utt.keys())[0]
                    else:
                        data = list()
                    utt = utt.lower()
                    match = parser.test_intent(utt)
                    self.assertIsInstance(match, IntentMatch)
                    self.assertEqual(match.skill_id, self.test_skill_id)
                    self.assertEqual(match.intent_type,
                                     f"{self.test_skill_id}:{intent}", utt)
                    self.assertEqual(match.utterance, utt)

                    for datum in data:
                        if isinstance(datum, dict):
                            name = list(datum.keys())[0]
                            value = list(datum.values())[0]
                        else:
                            name = datum
                            value = None
                        self.assertIn(name, match.intent_data, utt)
                        if value:
                            self.assertEqual(match.intent_data[name], value, utt)

    def test_negative_intents(self):
        config = self.negative_intents.pop('config', {})
        include_med = config.get('include_med', True)
        include_low = config.get('include_low', False)

        for lang in self.negative_intents.keys():
            adapt = self.adapt_services[lang]
            padatious = TestPadatiousMatcher(self.padatious_services[lang],
                                             include_med=include_med,
                                             include_low=include_low)
            for utt in self.negative_intents[lang]:
                with self.assertRaises(IntentException, msg=utt):
                    adapt.test_intent(utt)
                with self.assertRaises(IntentException, msg=utt):
                    padatious.test_intent(utt)

    def test_common_query(self):
        if not self.common_query:
            return

        qa_callback = Mock()
        qa_response = Mock()
        self.skill.events.add('question:action', qa_callback)
        self.skill.events.add('question:query.response', qa_response)
        for lang in self.common_query.keys():
            for utt in self.common_query[lang]:
                if isinstance(utt, dict):
                    data = list(utt.values())[0]
                    utt = list(utt.keys())[0]
                else:
                    data = dict()
                utt = utt.lower()
                message = Message('test_utterance',
                                  {"utterance": utt, "lang": lang})
                self.common_query_service.handle_question(message)
                response = qa_response.call_args[0][0]
                callback = qa_response.call_args[0][0]
                self.assertIsInstance(response, Message)
                self.assertTrue(response.data["phrase"] in utt)
                self.assertEqual(response.data["skill_id"], self.skill.skill_id)
                self.assertIn("callback_data", response.data.keys())
                self.assertIsInstance(response.data["conf"], float)
                self.assertIsInstance(response.data["answer"], str)

                self.assertIsInstance(callback, Message)
                self.assertEqual(callback.data['skill_id'], self.skill.skill_id)
                self.assertEqual(callback.data['phrase'],
                                 response.data['phrase'])
                if not data:
                    continue
                if isinstance(data.get('callback'), dict):
                    self.assertEqual(callback.data['callback_data'],
                                     data['callback'])
                elif isinstance(data.get('callback'), list):
                    self.assertEqual(set(callback.data['callback_data'].keys()),
                                     set(data.get('callback')))
                if data.get('min_confidence'):
                    self.assertGreaterEqual(response.data['conf'],
                                            data['min_confidence'])
                if data.get('max_confidence'):
                    self.assertLessEqual(response.data['conf'],
                                         data['max_confidence'])

    def test_common_play(self):
        # TODO
        pass
