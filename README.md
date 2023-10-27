## Getting Started

To create the virtual environment:
```
pip install poetry
poetry install
```

To activate the virtual environment:
```
poetry shell
```

Add the path to the root of the this repo to your python path:
```
export PYTHONPATH=${PWD}
```

### Configuring your API Credentials

The simplest method to set your credentials is to run the CLI:
```
pm config credentials
```
which will prompt you to enter your Promethium API key. This will
be stored in a `.promethium.ini` in your home directory.

After doing this, you can simply instantiate the Promethium Client
directly using:
```
from promehtium import PromethiumClient

pc = PromethiumClient()
```
and begin using the SDK.