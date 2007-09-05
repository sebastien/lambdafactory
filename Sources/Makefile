SUGARC=sugar
SUGAR_DIR=sugar
PYTHON_DIR=python
SUGAR_SOURCES=$(shell find $(SUGAR_DIR) -name "*.spy")
SUGAR_PRODUCT=$(SUGAR_SOURCES:sugar/%.spy=python/%.py)

all: $(SUGAR_PRODUCT)
	

python/%.py: sugar/%.spy
	$(SUGARC) -c -opython $< 
