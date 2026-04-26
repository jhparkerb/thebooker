.PHONY: test loc complexity funclength annotations coverage quality

test:
	python3 -m pytest pipeline/ -q

loc:
	@find . -name "*.py" | grep -v __pycache__ | sort | xargs wc -l | sort -rn

complexity:
	@python3 scripts/complexity.py $(N)

funclength:
	@python3 scripts/funclength.py $(N)

annotations:
	@python3 scripts/annotations.py

coverage:
	@python3 -m pytest pipeline/ --cov=pipeline --cov-report=term-missing -q

quality:
	@echo "=== LOC ==="; make -s loc
	@echo; echo "=== COMPLEXITY ==="; make -s complexity
	@echo; echo "=== FUNCTION LENGTH ==="; make -s funclength
	@echo; echo "=== ANNOTATIONS ==="; make -s annotations
	@echo; echo "=== COVERAGE ==="; make -s coverage
