### help - help docs for this Makefile
.PHONY: help
help :
	@sed -n '/^###/p' Makefile

### install - install requirements in venv
SECRETS_FILE := 'secrets.py'
.PHONY: install
install:
	python3 -m venv .venv; \
	. .venv/bin/activate; \
	pip install -r requirements.txt; \
	test -f $(SECRETS_FILE) || echo 'HOSTED_CONSUMER_KEY = ""\nHOSTED_CONSUMER_SECRET = ""\nCONSUMER_KEY = ""\nCONSUMER_SECRET = ""\nSECRET_KEY = ""' > $(SECRETS_FILE)

### venv - start venv
.PHONY: venv
venv:
	. .venv/bin/activate
