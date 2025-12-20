# Oil Notifier Makefile

REMOTE_HOST := mediaserver
REMOTE_APP_DIR := /opt/oil-notifier
REMOTE_DATA_DIR := /usr/local/etc/oil-notifier

.PHONY: install-remote run build clean

# Install/update on remote
install-remote:
	@echo "Syncing to $(REMOTE_HOST):$(REMOTE_APP_DIR)..."
	rsync -av --delete \
		--exclude='.venv' \
		--exclude='.git' \
		--exclude='images/*' \
		--exclude='oil_level_log.csv' \
		--exclude='__pycache__' \
		--exclude='.ruff_cache' \
		--exclude='.ipynb_checkpoints' \
		--exclude='.env' \
		--exclude='test/' \
		--exclude='.serena' \
		--exclude='.claude' \
		./ $(REMOTE_HOST):$(REMOTE_APP_DIR)/
	@echo "Creating docker-compose.override.yml for remote paths..."
	@printf '%s\n' \
		'services:' \
		'  oil-notifier:' \
		'    volumes:' \
		'      - $(REMOTE_DATA_DIR)/images:/app/images' \
		'      - $(REMOTE_DATA_DIR)/oil_level_log.csv:/app/oil_level_log.csv' \
		'    command: python3 check_oil_level.py --data-dir /app' \
		| ssh $(REMOTE_HOST) 'cat > $(REMOTE_APP_DIR)/docker-compose.override.yml'
	@echo "Syncing .env to $(REMOTE_HOST):$(REMOTE_APP_DIR)..."
	rsync -av .env $(REMOTE_HOST):$(REMOTE_APP_DIR)/.env
	ssh $(REMOTE_HOST) "touch $(REMOTE_DATA_DIR)/oil_level_log.csv"
	@echo "Done"

# Local development commands
run:
	python3 check_oil_level.py

build:
	docker compose build

clean:
	rm -rf __pycache__ .ruff_cache
	docker compose down --rmi local 2>/dev/null || true
