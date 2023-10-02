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

from threading import Event, Lock
from typing import List
from ovos_utils.log import LOG
from ovos_bus_client.client import MessageBusClient
from ovos_bus_client.message import Message


class TextIntentTests:
    def __init__(self, prompts: List[str], lang: str = "en-us", bus_config: dict = None):
        bus_config = bus_config or dict()
        self.core_bus = MessageBusClient(**bus_config)
        self.core_bus.run_in_thread()
        self.lang = lang
        self._prompts = prompts
        self._results = list()
        self._audio_output_done = Event()
        self._prompt_handled = Event()
        self._prompt_lock = Lock()
        self._last_message = None
        self._audio_output_done.set()
        self.register_bus_events()

    def run_test(self) -> List[Message]:
        self._results.clear()
        for prompt in self._prompts:
            self.handle_prompt(prompt)
        # TODO: Format results into parseable data
        return self._results

    def register_bus_events(self):
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
        self._last_message = message
        self._audio_output_done.set()

    def _mic_listen(self, message):
        """
        Handle start listening (for prompts that trigger `get_response`)
        @param message: Message associated with completed skill handler
        """
        self._last_message = message
        self._prompt_handled.set()

    def _handler_complete(self, _):
        """
        Handle skill execution complete (audio output may not be complete)
        """
        self._prompt_handled.set()

    def send_prompt(self, prompt: str):
        """
        Send a prompt to core for intent handling
        """
        # TODO: Define user profile
        self.core_bus.emit(Message("recognizer_loop:utterance",
                                   {"utterances": [prompt],
                                    "lang": self.lang},
                                   {"neon_should_respond": True,
                                    "source": ["minerva"],
                                    "destination": ["skills"],
                                    "username": "minerva"}))

    def handle_prompt(self, prompt: str):
        with self._prompt_lock:
            # Ensure event state matches expectation
            if not self._audio_output_done.is_set():
                LOG.warning("Audio output not finished when expected!")
                self._audio_output_done.set()
            self._prompt_handled.clear()
            self._last_message = None

            # Send prompt
            self.send_prompt(prompt)
            assert self._prompt_handled.wait(60)
            assert self._audio_output_done.wait(30)
            assert self._last_message is not None
            self._results.append(self._last_message)
        LOG.debug(f"Handled {prompt}")
