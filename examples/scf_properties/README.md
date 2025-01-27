## Example

These examples show how to request and process SCF properties when running Single Point Calculation workflows.
Please note that these examples require a Promethium SDK version >= 0.3.12 for the SCF properties.

To run a batch `sdk` example that collects the SCF properties for molecules in a directory:
```
python batch/sdk/run.py
```
To run the `httpx` version:
```
python batch/httpx/run.py
```

To run a batch `sdk` example that collects the SCF properties based on the results of a conformer search:
```
python conformers/sdk/run.py
```

To run an `sdk` example comparing the different analysis methods for atomic charges:
```
python atomic_charges/sdk/run.py
```
To run the `httpx` version:
```
python atomic_charges/httpx/run.py
```
