# Neon Minerva
Neon Minerva (Modular INtelligent Evaluation for a Reliable Voice Assistant) 
provides tools for testing skills.

Install the Minerva Python package with: `pip install neon-minerva`
The `minerva` entrypoint is available to interact with a bus via CLI. 
Help is available via `minerva --help`.

## Installation
Since skill intents may use Padatious, the following system packages must be 
installed before installing this package:
```shell
sudo apt install swig libfann-dev
```
To install this package from PyPI, simply run:
```shell
pip install neon-minerva
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
