### help - help docs for this Makefile
.PHONY: help
help :
	@sed -n '/^###/p' Makefile

### install - install requirements in venv
.PHONY: install
install:
	python3 -m venv .venv; \
	. .venv/bin/activate; \
	pip install -r requirements.txt

### venv - start venv
.PHONY: venv
venv:
	. .venv/bin/activate
