test:
		pytest tests/test_client.py -v --cov=promethium --cov-report=term --cov-report=html --cov-branch --pdb
