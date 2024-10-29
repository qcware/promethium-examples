# Promethium - GPU-powered Quantum Chemistry

![Promethium Logo](promethium.svg)

This repository contains examples of how to run quantum chemical calculations using the Promethium
Application Programming Interface (API) and the Promethium Python Software Development Kit (SDK).
The Promethium API & SDK provide flexible ways to programmatically interact with Promethium.
This enables:
* Customized multi-workflow logic (e.g., running one workflow and spawning another with the result),
* Integration with custom in-house or open source molecular library software,
* Large-scale flexible analysis of workflow results.

The API can be accessed from any programming language. API documentation can be found [here](https://app.promethium.qcware.com/docs/api).
The SDK is currently only available for Python. 

## Getting Started with the Promethium API & Software Development Kit (SDK)

Please visit the API tab in the [Promethium settings page](https://app.promethium.qcware.com/settings/) to:

1. Install the Promethium Python Software Development Kit (SDK), and,
2. Create your API key.

Installing the Promethium SDK will provide both the Python client, and the Command-Line Tool (CLI).

### Using the Command-Line Tool (CLI)

Once you have installed the CLI, you can type:
```
promethium
```
to see a list of available commands. You can also use the short-form alias `pm` for `promethium`.
When running, you should see the help documentation similar to that shown below.
```
Usage: promethium [OPTIONS] COMMAND [ARGS]...

  Command Line Interface (CLI) for Promethium by QC Ware

Options:
  -v, --version       Print version and exit.
  -k, --api-key TEXT  Set Promethium API Key.
  --help              Show this message and exit.

Commands:
  config (cfg)        Configure the Promethium CLI.
  files (fs)          Manage your files.
  preparation (prep)  Manage molecule preparation.
  workflows (wf)      Manage Promethium workflows.
```

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
directly in python using:
```
from promethium_sdk import PromethiumClient

pc = PromethiumClient()
```
and begin using the SDK.

The command-line tool also provides a convenient interface to interact with Promethium.
To submit a simple single point calculation, simply run:
```
pm workflows new examples/Getting_Started/01_Single_Point_Calculation/json/config.json
```
After executing, you should see the response, containing the id of the workflow.
```
{
  "version": "v1",
  "id": "e47aa2e6-e5be-43ce-aa1a-073296bd5c0a",
  "name": "nirmatrelvir_api_spc",
  "kind": "SinglePointCalculation",
  "created_at": "2024-10-29T17:39:14.825060Z",
  "last_updated_at": "2024-10-29T17:39:14.825060Z",
  "started_at": "2024-10-29T17:39:15.139696Z",
  "stopped_at": null,
  "status": "RUNNING",
  "duration_seconds": 0.0,
  "parameters": { ... }, # omitted for brevity
  "resources": {
    "gpu_type": "a100",
    "gpu_count": 1
  },
  "metadata": null
}
```
In this case, the id of the workflow is `e47aa2e6-e5be-43ce-aa1a-073296bd5c0a`.
You can then check on the status of the workflow using:
```
pm workflows status e47aa2e6-e5be-43ce-aa1a-073296bd5c0a
```
which will return the status:
```
{
  "status": "COMPLETED"
}
```
To obtain the results of the workflow, simply run:
```
pm workflows results e47aa2e6-e5be-43ce-aa1a-073296bd5c0a
```
and you will see a response of the form:
```
{
  "id": "e47aa2e6-e5be-43ce-aa1a-073296bd5c0a",
  "kind": "SinglePointCalculation",
  "api_version": "v1",
  "status": "COMPLETED",
  "results": {
    "rhf": {
      "converged": true,
      "energy": -1770.0261097898197,
      "scalars": {
        "Escf": -1770.0261097898197,
        "Enuc": 4051.9492823967644,
        "Exc": -168.47833887343737,
        "Evv10": 0.9763936368644728
      }
    },
    "artifacts": {}
  }
}
```
Schemas for all requests/responses are provided in the API documentation.
Congratulations, you ran your first Promethium workflow using the Command-Line Interface (CLI)!

The remainder of this repository covers many examples of how to use the python SDK.
If this is your first time using the Promethium SDK, we recommend running the
[Getting Started](examples/Getting_Started) examples.

## Example Overview

This repository contains a variety of examples for interacting with Promethium programmatically.

Each example has up to three different versions:

1. Interacting with the Promethium API via the SDK (recommended),
2. Directly querying the API directly via a python library such as `httpx` or `requests`, and,
3. Directly querying the API via `cURL`.

Please reach out to [Promethium support](mailto:promethium@qcware.com) with any questions.

