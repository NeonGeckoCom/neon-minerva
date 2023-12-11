# Neon Minerva
Neon Minerva (Modular INtelligent Evaluation for a Reliable Voice Assistant) 
provides tools for testing skills.

Install the Minerva Python package with: `pip install neon-minerva`
The `minerva` entrypoint is available to interact with a bus via CLI. 
Help is available via `minerva --help`.

## Installation
If testing Padatious intents, the following system packages must be 
installed before installing this package:
```shell
sudo apt install swig libfann-dev
```
To install this package from PyPI, simply run:
```shell
pip install neon-minerva
```

If testing with Padatious, install with the `padatious` extras:
```shell
pip install neon-minerva[padatious]
```

## Usage
This package provides a CLI for local testing of skills. Skills installed with 
`pip` can be specified by entrypoint, or skills cloned locally can be specified
by root directory.

### Resource Tests
To test that skill resources are defined for all supported languages,
`minerva test-resources <skill-entrypoint> <test-file>`
> - <skill-entrypoint\> is the string entrypoint for the skill to test as specified in `setup.py` OR the path to 
    the skill's root directory 
> - <test-file\> is a relative or absolute path to the resource test file, usually `test_resources.yaml`

### Intent Tests
To test that skill intents match as expected for all supported languages,
`minerva test-intents <skill-entrypoint> <test-file>`
> - <skill-entrypoint\> is the string entrypoint for the skill to test as specified in `setup.py` OR the path to 
    the skill's root directory 
> - <test-file\> is a relative or absolute path to the resource test file, usually `test_intents.yaml`
> - The `--padacioso` flag can be added to test with Padacioso instead of Padatious for relevant intents

## Advanced Usage
In addition to convenient CLI methods, this package also provides test cases that
may be extended.

### Skill Unit Tests
`neon_minerva.tests.skill_unit_test_base` provides `SkillTestCase`, a class
that supplies boilerplate setup/teardown/mocking for testing a skill. An example
skill test implementation could look like:

```python
from os import environ
from neon_minerva.tests.skill_unit_test_base import SkillTestCase

environ['TEST_SKILL_ENTRYPOINT'] = "my_skill.test"

class MySkillTest(SkillTestCase):
    def test_skill_init(self):
        self.assertEqual(self.skill.skill_id, "my_skill.test")
    ...
```

Be sure to review the base class for mocked methods and test paths as these may
change in the future.

### Chatbot Unit Tests
`neon_minerva.chatbots` contains mocked data for testing as well as some utility
methods. `neon_minerva.tests.chatbot_v1_test_base` provides `TestSubmind` which
may be extended to test a submind bot in a mocked v1 environment. For example:

```python
from os import environ
from datetime import datetime
from chatbot_core.utils.enum import ConversationState

from neon_minerva.tests.chatbot_v1_test_base import TestSubmind
from neon_minerva.chatbots.test_constants import PROMPT, RESPONSES

environ["TEST_BOT_ENTRYPOINT"] = "tester"


class TestTester(TestSubmind):
    def test_submind_chatbot(self):
        self.submind.state = ConversationState.RESP
        response = self.submind.ask_chatbot("testrunner", PROMPT,
                                            datetime.now().strftime(
                                                "%I:%M:%S %p"))
        self.assertIsInstance(response, str)
        self.assertIsNotNone(response)
```
> Make sure to install the `chatbots` extra to use this test case
