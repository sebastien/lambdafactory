# LambdaFactory Makefile
SUGARC         = sugar
SUGAR_DIR      = sugar
SUGAR_FLAGS    = -L$(SUGAR_DIR)
BUILD_DIR      = ../Build
DIST_DIR       = ../Distribution
PYTHON_DIR     = python
SUGAR_SOURCES  = $(shell find $(SUGAR_DIR) -name "*.spy")
PYTHON_SOURCES = $(shell find $(PYTHON_DIR) -name "*.*")
SUGAR_PRODUCT  = $(SUGAR_SOURCES:$(SUGAR_DIR)/%.spy=$(BUILD_DIR)/%.py)
PYTHON_PRODUCT = $(PYTHON_SOURCES:$(PYTHON_DIR)/%=$(BUILD_DIR)/%)

all:  $(BUILD_DIR) $(SUGAR_PRODUCT) $(PYTHON_PRODUCT)
	@cd $(BUILD_DIR) ; git add * ; git commit -a -m "Build `cat $(BUILD_DIR)/build.id`"
	@echo Build: `cat $(BUILD_DIR)/build.id`

dist: $(DIST_DIR) $(SUGAR_PRODUCT) $(PYTHON_PRODUCT)
	rsync -av --delete --exclude ".*" --exclude "*.pyc" $(BUILD_DIR)/ $(DIST_DIR)
	
clean:
	rm -rf $(BUILD_DIR)/build.id $(BUILD_DIR)/lambdafactory

reset: clean
	cd $(BUILD_DIR) && git reset --hard

$(BUILD_DIR):
	mkdir -p $(BUILD_DIR) && cd $(BUILD_DIR) && git init

$(DIST_DIR):
	mkdir $(DIST_DIR)

$(BUILD_DIR)/%.py: $(SUGAR_DIR)/%.spy
	$(SUGARC)  -c -o$(BUILD_DIR) $(SUGAR_FLAGS) $< 
	@date "+%Y-%m-%d-%HH%MM%S" > $(BUILD_DIR)/build.id

$(BUILD_DIR)/%: $(PYTHON_DIR)/%
	@mkdir -p `dirname $@`
	cp $< $@
	@date "+%Y-%m-%d-%H%M%S" > $(BUILD_DIR)/build.id

# EOF
