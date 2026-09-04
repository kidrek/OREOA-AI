# OREOA-AI platform v2 - Makefile (docker_build_spec.md 8)
include versions.env

TAG ?= dev
COMPOSE ?= docker compose
PYTEST ?= python3 -m pytest
export

.DEFAULT_GOAL := help

.PHONY: help secrets build build-base pins update-knowledge runtime-config \
        up down shell case-new test test-infra lint-compose sbom scan \
        clean-derived image-sizes

help: ## Show targets
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  %-18s %s\n",$$1,$$2}'

secrets: ## Generate local docker secrets (redis_password, llm_api_key) if missing
	@mkdir -p secrets
	@test -f secrets/redis_password || (head -c 32 /dev/urandom | base64 | tr -d '\n' > secrets/redis_password)
	@test -f secrets/llm_api_key || (head -c 32 /dev/urandom | base64 | tr -d '\n' > secrets/llm_api_key)
	@chmod 700 secrets
	@chmod 644 secrets/redis_password secrets/llm_api_key
	@echo "secrets ready (secrets/ is gitignored; 0644 files: bind-mounted secrets must be readable by uid 10001)"

build-base: ## Build the base image (ordered first, hardening foundation)
	docker build -f docker/base/Dockerfile \
		--build-arg PYTHON_IMAGE="$(PYTHON_IMAGE)" \
		-t oreoa/base:$(TAG) .

build: build-base ## Build all images (base first, then worker-fast, then the rest)
	$(COMPOSE) build worker-fast
	$(COMPOSE) build

pins: ## Resolve/refresh versions.env pins (scripts/make_pins.py; use YES=1 to skip confirm)
	python3 scripts/make_pins.py $(if $(YES),--yes,)

update-knowledge: ## Fetch pinned knowledge sources on the host (step 1.5)
	python3 scripts/update_knowledge.py $(FLAGS)

runtime-config: ## Render opencode.json + .claude/ from agents/ and commands/ (step 1.2)
	python3 -m oreoa.runtime_config render

up: ## Start the stack (make up LLM=1 for the local-llm override)
	$(MAKE) secrets
	$(if $(LLM),$(COMPOSE) -f compose.yaml -f compose.local-llm.yaml up -d,$(COMPOSE) up -d)

down: ## Stop the stack
	$(COMPOSE) down

shell: ## Attach the analyst TUI: make shell CASE=<id>
	@test -n "$(CASE)" || { echo "usage: make shell CASE=<case-id>"; exit 2; }
	$(COMPOSE) run --rm agent

case-new: ## Create a case skeleton: make case-new ID=<id> [TYPE=incident|exercice]
	bash scripts/case_new.sh $(ID) $(if $(TYPE),--type $(TYPE),)

lint-compose: ## Fail if privileged/cap_add/devices/docker.sock/host network appear
	$(PYTEST) tests/infra/test_compose_hardening.py

test: ## Unit tests (T1)
	$(PYTEST) tests/unit

test-infra: secrets ## Infra tests (T5) - builds nothing; run make build first
	$(PYTEST) tests/infra

sbom scan: ## (step 2) syft SBOM per image + grype/trivy scan
	@echo "sbom/scan land at work-order step 2 (CI matrix)"

clean-derived: ## Delete derived/ of a case (rebuildable), never touches evidence/
	@test -n "$(CASE)" || { echo "usage: make clean-derived CASE=<id>"; exit 2; }
	rm -rf cases/$(CASE)/derived && echo "derived/ deleted for $(CASE)"

image-sizes: ## Print docker system df per image (CI watch: worker-deep, knowledge)
	docker system df -v | sed -n '1,2p;/oreoa\//p'
