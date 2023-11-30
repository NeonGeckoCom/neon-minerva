# NEON AI (TM) SOFTWARE, Software Development Kit & Application Development System
#
# Copyright 2008-2023 Neongecko.com Inc. | All Rights Reserved
#
# Notice of License - Duplicating this Notice of License near the start of any file containing
# a derivative of this software is a condition of license for this software.
# Friendly Licensing:
# No charge, open source royalty free use of the Neon AI software source and object is offered for
# educational users, noncommercial enthusiasts, Public Benefit Corporations (and LLCs) and
# Social Purpose Corporations (and LLCs). Developers can contact developers@neon.ai
# For commercial licensing, distribution of derivative works or redistribution please contact licenses@neon.ai
# Distributed on an "AS IS” basis without warranties or conditions of any kind, either express or implied.
# Trademarks of Neongecko: Neon AI(TM), Neon Assist (TM), Neon Communicator(TM), Klat(TM)
# Authors: Guy Daniels, Daniel McKnight, Regina Bloomstine, Elon Gasper, Richard Leeds
#
# Specialized conversational reconveyance options from Conversation Processing Intelligence Corp.
# US Patents 2008-2023: US7424516, US20140161250, US20140177813, US8638908, US8068604, US8553852, US10530923, US10530924
# China Patent: CN102017585  -  Europe Patent: EU2156652  -  Patents Pending


import unittest

from os import getenv
from time import sleep
from chatbot_core.utils import clean_up_bot
from klat_connector import start_socket
from klat_connector.mach_server import MachKlatServer
from neon_minerva.chatbots.util import load_chatbot


class TestSubmind(unittest.TestCase):
    # Initialize a server for testing
    server = MachKlatServer()
    sleep(1)
    socket = start_socket("0.0.0.0")
    submind = None

    @classmethod
    def setUpClass(cls) -> None:
        # Determine submind to test
        submind_entrypoint = getenv("TEST_BOT_ENTRYPOINT")
        bot_class = load_chatbot(submind_entrypoint)
        # Initialize a submind instance
        cls.submind = bot_class(cls.socket, "Private", "testrunner",
                                "testpassword", on_server=False)

    @classmethod
    def tearDownClass(cls) -> None:
        clean_up_bot(cls.submind)
        cls.server.shutdown_server()
