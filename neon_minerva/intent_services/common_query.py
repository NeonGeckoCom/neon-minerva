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

import time
from dataclasses import dataclass
from threading import Event
from typing import Dict

from ovos_utils import flatten_list
from ovos_utils.log import LOG
from neon_minerva.intent_services import IntentMatch


EXTENSION_TIME = 15
MIN_RESPONSE_WAIT = 3


@dataclass
class Query:
    session_id: str
    query: str
    replies: list = None
    extensions: list = None
    query_time: float = time.time()
    timeout_time: float = time.time() + 1
    responses_gathered: Event = Event()
    completed: Event = Event()
    answered: bool = False


class CommonQuery:
    def __init__(self, bus):
        self.bus = bus
        self.skill_id = "common_query.test"  # fake skill
        self.active_queries: Dict[str, Query] = dict()
        self._vocabs = {}
        self.bus.on('question:query.response', self.handle_query_response)
        self.bus.on('common_query.question', self.handle_question)
        # TODO: Register available CommonQuery skills

    def is_question_like(self, utterance, lang):
        # skip utterances with less than 3 words
        if len(utterance.split(" ")) < 3:
            return False
        return True

    def match(self, utterances, lang, message):
        """Send common query request and select best response

        Args:
            utterances (list): List of tuples,
                               utterances and normalized version
            lang (str): Language code
            message: Message for session context
        Returns:
            IntentMatch or None
        """
        # we call flatten in case someone is sending the old style list of tuples
        utterances = flatten_list(utterances)
        match = None
        for utterance in utterances:
            if self.is_question_like(utterance, lang):
                message.data["lang"] = lang  # only used for speak
                message.data["utterance"] = utterance
                answered = self.handle_question(message)
                if answered:
                    match = IntentMatch('CommonQuery', None, {}, None,
                                        utterance)
                break
        return match

    def handle_question(self, message):
        """
        Send the phrase to the CommonQuerySkills and prepare for handling
        the replies.
        """
        utt = message.data.get('utterance')
        sid = "test_session"
        # TODO: Why are defaults not creating new objects on init?
        query = Query(session_id=sid, query=utt, replies=[], extensions=[],
                      query_time=time.time(), timeout_time=time.time() + 1,
                      responses_gathered=Event(), completed=Event(),
                      answered=False)
        assert query.responses_gathered.is_set() is False
        assert query.completed.is_set() is False
        self.active_queries[sid] = query

        LOG.info(f'Searching for {utt}')
        # Send the query to anyone listening for them
        msg = message.reply('question:query', data={'phrase': utt})
        if "skill_id" not in msg.context:
            msg.context["skill_id"] = self.skill_id
        self.bus.emit(msg)

        query.timeout_time = time.time() + 1
        timeout = False
        while not query.responses_gathered.wait(EXTENSION_TIME):
            if time.time() > query.timeout_time + 1:
                LOG.debug(f"Timeout gathering responses ({query.session_id})")
                timeout = True
                break

        # forcefully timeout if search is still going
        if timeout:
            LOG.warning(f"Timed out getting responses for: {query.query}")
        self._query_timeout(message)
        if not query.completed.wait(10):
            raise TimeoutError("Timed out processing responses")
        answered = bool(query.answered)
        self.active_queries.pop(sid)
        LOG.debug(f"answered={answered}|"
                  f"remaining active_queries={len(self.active_queries)}")
        return answered

    def handle_query_response(self, message):
        search_phrase = message.data['phrase']
        skill_id = message.data['skill_id']
        searching = message.data.get('searching')
        answer = message.data.get('answer')

        query = self.active_queries.get("test_session")
        if not query:
            LOG.warning(f"No active query for: {search_phrase}")
        # Manage requests for time to complete searches
        if searching:
            LOG.debug(f"{skill_id} is searching")
            # request extending the timeout by EXTENSION_TIME
            query.timeout_time = time.time() + EXTENSION_TIME
            # TODO: Perhaps block multiple extensions?
            if skill_id not in query.extensions:
                query.extensions.append(skill_id)
        else:
            # Search complete, don't wait on this skill any longer
            if answer:
                LOG.info(f'Answer from {skill_id}')
                query.replies.append(message.data)

            # Remove the skill from list of timeout extensions
            if skill_id in query.extensions:
                LOG.debug(f"Done waiting for {skill_id}")
                query.extensions.remove(skill_id)

            time_to_wait = query.query_time + MIN_RESPONSE_WAIT - time.time()
            if time_to_wait > 0:
                LOG.debug(f"Waiting {time_to_wait}s before checking extensions")
                query.responses_gathered.wait(time_to_wait)
            # not waiting for any more skills
            if not query.extensions:
                LOG.debug(f"No more skills to wait for ({query.session_id})")
                query.responses_gathered.set()

    def _query_timeout(self, message):
        query = self.active_queries.get("test_session")
        LOG.info(f'Check responses with {len(query.replies)} replies')
        search_phrase = message.data.get('phrase', "")
        if query.extensions:
            query.extensions = []

        # Look at any replies that arrived before the timeout
        # Find response(s) with the highest confidence
        best = None
        ties = []
        for response in query.replies:
            if not best or response['conf'] > best['conf']:
                best = response
                ties = []
            elif response['conf'] == best['conf']:
                ties.append(response)

        if best:
            # invoke best match
            LOG.info('Handling with: ' + str(best['skill_id']))
            cb = best.get('callback_data') or {}
            self.bus.emit(message.forward('question:action',
                                          data={'skill_id': best['skill_id'],
                                                'phrase': search_phrase,
                                                'callback_data': cb}))
            query.answered = True
        else:
            query.answered = False
        query.completed.set()
