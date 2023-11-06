## Getting Started

Please visit the API tab in the [Promethium settings page](https://app.promethium.qcware.com/settings/) to:

1. Install the Promethium Python Software Developmet Kit (SDK), and,
2. Create your API key.

Installing the Promethium SDK will provide both the Python client, and the Command-Line Tool (CLI).

### Using the Command-Line Tool (CLI)

Once you have installed the CLI, you can type:
```
promethium
```
to see a list of available commands. You can also use the short-form alias `pm` for `promethium`.

### Configuring your API Credentials

The simplest method to set your credentials is to run the CLI:
```
pm config credentials
```
which will prompt you to enter your Promethium API key. This will
be stored in a `.promethium.ini` in your home directory.

This initializes your credentials for use with both the CLI and the
Python client.

After doing this, in Python you can simply instantiate the Promethium Client
directly using:
```
from promethium import PromethiumClient

pc = PromethiumClient()
```
and begin using the SDK.

## Examples

This repository contains a variety of examples for interacting with Promethium programmatically.

Each example has two versions:

1. Interacting with the Promethium API via the SDK (recommended), and,
2. Directly querying the API.

Please reach out to [Promethium support](mailto:promethium@qcware.com) with any questions.

