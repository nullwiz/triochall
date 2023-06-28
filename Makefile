setup: down build up buildb coverage initialdata report
rundev: down build up-db initialdata

down:
	docker compose down 

build: 
	docker-compose build 

env:
	python3 -m venv .venv
	. .venv/bin/activate && pip install -r requirements.txt
buildb:
	. .venv/bin/activate && PYTHONPATH=${PWD} DB_HOST=localhost python api/db/manage_postgres_tables.py --drop 
	. .venv/bin/activate && PYTHONPATH=${PWD} DB_HOST=localhost python api/db/redis_flushall.py
initialdata:
	. .venv/bin/activate && PYTHONPATH=${PWD} DB_HOST=localhost python api/db/manage_postgres_tables.py --drop --create
up:
	docker-compose up -d

up-db: 
	docker-compose up -d postgres redis redisinsight

coverage:
	. .venv/bin/activate && PYTHONPATH=${PWD} DB_HOST=localhost REDIS_HOST=localhost coverage run --concurrency=greenlet --source api/ -m pytest tests/ -v 

report:
	. .venv/bin/activate && PYTHONPATH=${PWD} coverage report -m
