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

from padatious import IntentContainer
from ovos_utils.log import LOG
from ovos_utils.messagebus import FakeBus

from neon_minerva.exceptions import IntentNotMatched, ConfidenceTooLow
from neon_minerva.intent_services import IntentMatch


class PadatiousContainer:
    def __init__(self, lang: str, cache_path: str, bus: FakeBus):
        self.lang = lang.lower()
        self.bus = bus
        self.padatious = IntentContainer(cache_path)
        self.bus.on('padatious:register_intent', self.register_intent)
        self.bus.on('padatious:register_entity', self.register_entity)

    def register_intent(self, message):
        """Messagebus handler for registering intents.

        Args:
            message (Message): message triggering action
        """
        lang = message.data.get('lang', self.lang)
        lang = lang.lower()
        if lang == self.lang:
            LOG.debug(f"Loading intent: {message.data['name']}")
            self.padatious.load_intent(message.data['name'],
                                       message.data['file_name'])
        else:
            LOG.debug(f"Ignoring {message.data['name']}")

    def register_entity(self, message):
        """Messagebus handler for registering entities.

        Args:
            message (Message): message triggering action
        """
        lang = message.data.get('lang', self.lang)
        lang = lang.lower()
        if lang == self.lang:
            self.padatious.load_entity(message.data['name'],
                                       message.data['file_name'])

    def calc_intent(self, utt: str) -> dict:
        intent = self.padatious.calc_intent(utt)
        LOG.debug(intent)
        return intent.__dict__ if intent else dict()


class TestPadatiousMatcher:
    def __init__(self, container: PadatiousContainer,
                 include_med: bool = True, include_low: bool = False):
        LOG.debug("Creating test Padatious Matcher")
        if include_low:
            self.min_conf = 0.5
        elif include_med:
            self.min_conf = 0.8
        else:
            self.min_conf = 0.95
        self.padatious = container

    def test_intent(self, utterance: str) -> IntentMatch:
        intent = self.padatious.calc_intent(utterance)
        if not intent:
            raise IntentNotMatched(utterance)
        conf = intent.get("conf") or 0.0
        if conf < self.min_conf:
            raise ConfidenceTooLow(f"{conf} less than minimum {self.min_conf}")
        skill_id = intent.get('name').split(':')[0]
        sentence = ' '.join(intent.get('sent'))
        return IntentMatch('Padatious', intent.get('name'),
                           intent.get('matches'), skill_id, sentence)
