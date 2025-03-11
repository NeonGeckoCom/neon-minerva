# NEON AI (TM) SOFTWARE, Software Development Kit & Application Development System
# All trademark and other rights reserved by their respective owners
# Copyright 2008-2025 Neongecko.com Inc.
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

from tempfile import mkstemp
from threading import Event, Lock
from time import time
from typing import List

from neon_utils.file_utils import encode_file_to_base64_string
from ovos_utils.log import LOG
from ovos_bus_client.client import MessageBusClient
from ovos_bus_client.message import Message
from ovos_plugin_manager.tts import TTS


class UtteranceTests:
    def __init__(self, prompts: List[str], lang: str = "en-us",
                 bus_config: dict = None, user_config: dict = None,
                 audio: bool = False, tts: TTS = None):
        if not user_config:
            from neon_utils.configuration_utils import get_neon_user_config
            user_config = get_neon_user_config().content
        user_config['user']['username'] = "minerva"
        self._user_config = user_config
        bus_config = bus_config or dict()
        self.core_bus = MessageBusClient(**bus_config)
        self.core_bus.run_in_thread()
        self.lang = lang
        self.test_audio = audio
        self._tts = tts
        # TODO: Handle prompt metadata for longer timeouts
        self._prompts = prompts
        self._stt_timeout = 60     # Time to transcribe + audio parsers
        self._intent_timeout = 60  # Time to match AND handle intent
        self._speak_timeout = 60   # Time after intent handling for TTS playback

        self._results = list()
        self._audio_output_done = Event()
        self._prompt_handled = Event()
        self._prompt_lock = Lock()

        self._last_message = None
        self._audio_output_done.set()
        self.register_bus_events()

    def run_test(self) -> dict:
        """
        Run tests and return dict timing results
        """
        self._results.clear()
        for prompt in self._prompts:
            self.handle_prompt(prompt)
        aggregated_results = {"save_transcript": [],
                              "text_parsers": [],
                              "get_tts": [],
                              "intent_handler": [],
                              "total": []}
        if self.test_audio:
            aggregated_results['get_stt'] = []
        for result in self._results:
            try:
                aggregated_results['save_transcript'].append(result['save_transcript'])
                aggregated_results['text_parsers'].append(result['text_parsers'])
                aggregated_results['get_tts'].append(result['get_tts'])
                aggregated_results['intent_handler'].append(result['speech_start'] - result['handle_utterance'])
                aggregated_results['total'].append(result['finished'] - result['transcribed'])
                if self.test_audio:
                    aggregated_results['get_stt'].append(result['get_stt'])
            except KeyError:
                LOG.error(result)
        formatted_results = dict()
        for key, values in aggregated_results.items():
            formatted_results[key] = {"average": round(sum(values) /
                                                       len(values), 6),
                                      "minimum": round(min(values), 6),
                                      "maximum": round(max(values), 6)}
        return formatted_results

    def register_bus_events(self):
        """
        Register listeners to track audio and skill module states
        """
        self.core_bus.on("recognizer_loop:audio_output_start",
                         self._audio_started)
        self.core_bus.on("recognizer_loop:audio_output_end",
                         self._audio_stopped)
        self.core_bus.on("mycroft.mic.listen", self._mic_listen)
        self.core_bus.on("mycroft.skill.handler.complete",
                         self._handler_complete)

    def _audio_started(self, _):
        """
        Handle audio output started
        """
        self._audio_output_done.clear()

    def _audio_stopped(self, message):
        """
        Handle audio output finished
        @param message: Message associated with completed audio playback
        """
        LOG.debug("audio finished")
        self._last_message = message
        self._audio_output_done.set()

    def _mic_listen(self, message):
        """
        Handle start listening (for prompts that trigger `get_response`)
        @param message: Message associated with completed skill handler
        """
        LOG.debug("`get_response` call")
        # self._last_message = message
        self._prompt_handled.set()

    def _handler_complete(self, _):
        """
        Handle skill execution complete (audio output may not be complete)
        """
        LOG.debug("Skill Handler Complete")
        self._prompt_handled.set()

    def send_prompt(self, prompt: str):
        """
        Send a prompt to core for intent handling
        """
        context = {"neon_should_respond": True,
                   "source": ["minerva"],
                   "destination": ["skills"],
                   "timing": {"transcribed": time()},
                   "username": "minerva",
                   "user_profiles": [self._user_config]}
        if self.test_audio:
            if self._tts:
                _, file_path = mkstemp()
                audio, _ = self._tts.get_tts(prompt, file_path, lang=self.lang)
            else:
                resp = self.core_bus.wait_for_response(
                    Message("neon.get_tts", {'text': prompt,
                                             'speaker': {'language': self.lang,
                                                         'gender': 'female'}}),
                    timeout=self._stt_timeout)
                file_path = resp.data[self.lang]['female']
            resp = self.core_bus.wait_for_response(
                Message("neon.audio_input",
                        {"audio_data": encode_file_to_base64_string(file_path),
                         "lang": self.lang}, context),
                timeout=self._stt_timeout)
            LOG.info(resp.data)
            if prompt.lower() not in (t.lower() for t
                                      in resp.data['transcripts']):
                LOG.warning(f"Invalid transcription for '{prompt}': "
                            f"{resp.data['transcripts']}")
        else:
            self.core_bus.emit(Message("recognizer_loop:utterance",
                                       {"utterances": [prompt],
                                        "lang": self.lang}, context))

    def handle_prompt(self, prompt: str):
        """
        Send a prompt (text or audio) and collect timing results.
        @param prompt: string prompt to send for intent (and optionally STT)
            processing
        """
        with self._prompt_lock:
            # Ensure event state matches expectation
            if not self._audio_output_done.is_set():
                LOG.warning("Audio output not finished when expected!")
                self._audio_output_done.wait(self._speak_timeout)
            self._audio_output_done.clear()
            self._prompt_handled.clear()
            self._last_message = None

            # Send prompt
            self.send_prompt(prompt)
            try:
                assert self._prompt_handled.wait(self._intent_timeout)
                assert self._audio_output_done.wait(self._speak_timeout)
                assert self._last_message is not None
                if "speech_start" not in self._last_message.context["timing"]:
                    LOG.warning(f"Missing speech_start timestamp for {prompt}")
                    self._last_message.context["timing"]["speech_start"] = \
                        self._last_message.context["timing"]["handle_utterance"]
                self._results.append({**self._last_message.context["timing"],
                                      **{'finished': time()}})
            except AssertionError as e:
                LOG.error(f"{prompt}: {e}")
        LOG.debug(f"Handled {prompt}")
