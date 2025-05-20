## Example

Performs a Conformer Search with the following filter stages:
1. Force field filter (MMFF, UFF, GFN-FF, Open-FF Sage)
2. Semi-empirical filter (ANI-2x, GFN2-xTB)
3. Coarse DFT filter (B3LYP-D3/def2-SVP)
4. Fine DFT filter (wB97M-V/def2-TZVP) - optional

To run the `httpx` version:
```
python httpx/run.py
```
To run the `sdk` version:
```
python sdk/run.py
```
