.PHONY: test loc complexity

test:
	python3 -m pytest pipeline/ -q

loc:
	@find . -name "*.py" | grep -v __pycache__ | sort | xargs wc -l | sort -rn

complexity:
	@python3 scripts/complexity.py $(N)
