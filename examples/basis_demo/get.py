import requests
import base64
import os
import json
import numpy as np
import glob
from pprint import pprint

np.set_printoptions(formatter={'all' : lambda arg: f'{arg:.1f}'})

foldername = 'output'

headers = {
    "accept": "application/json",
    "x-api-key" : os.environ['PM_API_KEY']
    }

filename = f'{foldername}/paxlovid_api_test_submitted.json'

data = json.loads(open(filename).read())
jobid = data['id']

# Get Workflow
url = f'https://api.promethium-dev.qcware.com/v0/workflows/{jobid}'
response = requests.get(url, headers=headers).json()
timetaken = response['duration_seconds']
name = response['name']

# Download results
url = f'https://api.promethium-dev.qcware.com/v0/workflows/{jobid}/results/download'
# Numerical results
url = f'https://api.promethium-dev.qcware.com/v0/workflows/{jobid}/results'

response = requests.get(url, headers=headers).json()
# freqs = np.array([float(v) for v in response['results']['optimization']['vibrational_frequencies']['wavenumbers']])
mol = response['results']['artifacts']['optimized-molecule']['base64data']
print(base64.b64decode(mol).decode('utf-8'))
print(f'Name: {name}, time taken: {timetaken:.2f}s')
