## Example

These examples show how to request and process SCF properties when running Single Point Calculation workflows.
Please note that these examples require a Promethium SDK version >= 0.3.12 for the SCF properties.

To run a batch `httpx` example invoking several workflows and collecting their results:
```
python batch/httpx/run.py
```
To run the `sdk` version:
```
python batch/sdk/run.py
```

To run an `httpx` example comparing the different analysis methods for atomic charges:
```
python atomic_charges/httpx/run.py
```
To run the `sdk` version:
```
python atomic_charges/sdk/run.py
```
