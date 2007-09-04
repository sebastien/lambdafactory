SUGAR_COMPILER=do spyc
SG_PY_SOURCES=$(shell find . -name "*.spy" | cut -d/ -f2-)
SG_PY_MODULES=$(SG_PY_SOURCES:.spy=.py)

all: $(SG_PY_MODULES)
	@echo OK

%.py: %.spy
	@echo "outdated: " $(SUGAR_COMPILER) `echo $< | cut -d. -f1`
