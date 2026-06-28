.PHONY: demo local backend slack test

# One-click Docker setup (judge-ready)
demo:
	docker-compose up --build

# Local dev: backend + slack client (one script)
local:
	python scripts/start_local.py

# Backend only
backend:
	cd backend && uvicorn main:app --reload --port 8000

# Slack client only
slack:
	cd backend && python slack_client.py

# Run tests
test:
	pytest tests/ -v
