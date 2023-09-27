import requests
import base64
import os
import json
import httpx
import numpy as np
from pprint import pprint

np.set_printoptions(formatter={'all' : lambda arg: f'{arg:.1f}'})

foldername = 'output'

base_url = os.getenv("PM_API_BASE_URL", "https://api.promethium.qcware.com")

headers = {
    "accept": "application/json",
    "x-api-key" : os.environ['PM_API_KEY']
}

client = httpx.Client(base_url=base_url, headers=headers)
filename = f'{foldername}/paxlovid_api_test_submitted.json'

data = json.loads(open(filename).read())
jobid = data['id']

# Get Workflow
response = client.get(f'/v0/workflows/{jobid}').json()
timetaken = response['duration_seconds']
name = response['name']

# Numerical results

response = requests.get(f'/v0/workflows/{jobid}/results').json()
# freqs = np.array([float(v) for v in response['results']['optimization']['vibrational_frequencies']['wavenumbers']])
mol = response['results']['artifacts']['optimized-molecule']['base64data']
print(base64.b64decode(mol).decode('utf-8'))
print(f'Name: {name}, time taken: {timetaken:.2f}s')
