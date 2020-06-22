app :=  calibration

image:
	docker build -t $(app) .

fmt:
	isort --recursive .
	autoflake --recursive --in-place --remove-all-unused-imports --remove-unused-variables .
	black .

lint:
	flake8
	isort --recursive . --check-only
	black . --check
