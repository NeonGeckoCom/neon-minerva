# NEON AI (TM) SOFTWARE, Software Development Kit & Application Framework
# All trademark and other rights reserved by their respective owners
# Copyright 2008-2025 Neongecko.com Inc.
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

from typing import Optional
from adapt.engine import IntentDeterminationEngine
from ovos_workshop.intents import open_intent_envelope
from ovos_utils.log import LOG
from ovos_utils.messagebus import FakeBus
from ovos_bus_client.util import get_message_lang

from neon_minerva.exceptions import IntentNotMatched, ConfidenceTooLow
from neon_minerva.intent_services import IntentMatch


class AdaptContainer:
    def __init__(self, lang: str, bus: FakeBus):
        self.lang = lang.lower()
        self.bus = bus
        self.adapt = IntentDeterminationEngine()
        self.bus.on('register_vocab', self.handle_register_vocab)
        self.bus.on('register_intent', self.handle_register_intent)

    def handle_register_vocab(self, message):
        entity_value = message.data.get('entity_value')
        entity_type = message.data.get('entity_type')
        regex_str = message.data.get('regex')
        alias_of = message.data.get('alias_of')
        lang = get_message_lang(message)
        if lang != self.lang:
            return
        if regex_str:
            self.adapt.register_regex_entity(regex_str)
        else:
            self.adapt.register_entity(entity_value, entity_type,
                                       alias_of=alias_of)

    def handle_register_intent(self, message):
        intent = open_intent_envelope(message)
        self.adapt.register_intent_parser(intent)

    def test_intent(self, utterance: str) -> Optional[IntentMatch]:
        best_intent = None
        try:
            intents = [i for i in self.adapt.determine_intent(
                utterance, 100,
                include_tags=True)]
            if intents:
                best_intent = max(intents,
                                  key=lambda x: x.get('confidence', 0.0))
        except Exception as err:
            LOG.exception(err)

        if not best_intent:
            raise IntentNotMatched(utterance)
        LOG.debug(best_intent)
        skill_id = best_intent['intent_type'].split(":")[0]
        _norm_id = skill_id.replace('.', '_')
        intent_data = {k.replace(_norm_id, '', 1): v for k, v in
                       best_intent.items() if k.startswith(_norm_id) and
                       isinstance(v, str)}
        LOG.debug(intent_data)
        ret = IntentMatch('Adapt', best_intent['intent_type'], intent_data,
                          skill_id, utterance)
        return ret
