# NEON AI (TM) SOFTWARE, Software Development Kit & Application Development System
#
# Copyright 2008-2025 Neongecko.com Inc. | All Rights Reserved
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

PROMPT = "hello!"

RESPONSES = {"Ned": "Hi, I'm Ned. How are you, testrunner?",
             "Eliza": "Hello... I'm glad you could drop by today.",
             "terry": "Hey",
             "Ima": "I am ready to talk",
             "wolfram": "Hello, human",
             "kbot": "hello!",
             "alice": "Hi there!",
             "abstain": ""}

VOTES_BY_USER = {
    '1prompt1': {
        'bot1': [],
        'bot2': ['bot1'],
        'bot3': [],
        'bot4': [],
        'abstain': ['bot2', 'bot3', 'bot4']
    },
    '2prompt2': {
        'bot1': [],
        'bot2': [],
        'bot4': [],
        'abstain': ['bot1', 'bot2', 'bot4']
    },
    '3prompt3': {
        'bot1': [],
        'bot2': ['bot1'],
        'bot3': [],
        'bot4': [],
        'abstain': ['bot2', 'bot3', 'bot4']
    }
}

SELECTIONS = {
    'bot1': [('prompt1', 'bot2'), ('prompt2', 'abstain'), ('prompt3', 'bot2')],
    'bot2': [('prompt1', 'abstain'), ('prompt2', 'abstain'), ('prompt3', 'abstain')],
    'bot3': [('prompt1', 'abstain'), ('prompt3', 'abstain')],
    'bot4': [('prompt1', 'abstain'), ('prompt2', 'abstain'), ('prompt3', 'abstain')]
}

SELECTION_HISTORY = ['bot2', 'bot2', 'bot2']

PARTICIPANT_HISTORY = [(),  # element 0 is expected to be an empty tuple
                       ('bot1', 'bot2', 'bot3', 'bot4'),
                       ('bot1', 'bot2', 'bot3', 'bot4')]

# ContextKeeper constants
RECENT_USERS = [f"user{number}" for number in range(20)]
RECENT_SHOUTS = [
    "Who is the president of Ukraine?",
    "Who is the president of the US?",
    "What is the distance between them?",
    "When was he born?"
]
