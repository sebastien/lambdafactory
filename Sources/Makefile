# LambdaFactory Makefile
SUGARC         = sugar
SUGAR_DIR      = sugar
BUILD_DIR      = ../Build
PYTHON_DIR     = python
SUGAR_SOURCES  = $(shell find $(SUGAR_DIR) -name "*.spy")
PYTHON_SOURCES = $(shell find $(PYTHON_DIR) -name "*.*")
SUGAR_PRODUCT  = $(SUGAR_SOURCES:$(SUGAR_DIR)/%.spy=$(BUILD_DIR)/%.py)
PYTHON_PRODUCT = $(PYTHON_SOURCES:$(PYTHON_DIR)/%.py=$(BUILD_DIR)/%.py)

all:  $(BUILD_DIR) $(SUGAR_PRODUCT) $(PYTHON_PRODUCT)
	@cd $(BUILD_DIR) ; hg addremove * ; hg commit -m "Build `cat $(BUILD_DIR)/build.id`"
	@echo Build: `cat $(BUILD_DIR)/build.id`

clean:
	rm -rf $(BUILD_DIR)/build.id $(BUILD_DIR)/lambdafactory

$(BUILD_DIR):
	hg init $(BUILD_DIR)

$(BUILD_DIR)/%.py: $(SUGAR_DIR)/%.spy
	$(SUGARC) -c -o$(BUILD_DIR) $< 
	@date "+%Y-%m-%d-%HH%MM%S" > $(BUILD_DIR)/build.id

$(BUILD_DIR)/%.py: $(PYTHON_DIR)/%.py
	@mkdir -p `dirname $@`
	cp $< $@
	@date "+%Y-%m-%d-%H%M%S" > $(BUILD_DIR)/build.id


# EOF
