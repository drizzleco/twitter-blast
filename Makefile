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
	pip install -r requirements.txt
	test -f $(SECRETS_FILE) || echo 'CONSUMER_KEY = "" \
	CONSUMER_SECRET = "" \
	SECRET_KEY = ""' > $(SECRETS_FILE)

### venv - start venv
.PHONY: venv
venv:
	. .venv/bin/activate
