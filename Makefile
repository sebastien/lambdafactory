# -----------------------------------------------------------------------------
#
# Python Project Makefile
# =======================
#
# Updated: 2016-11-01
# Author:  FFunction <ffctn.com>
#
# -----------------------------------------------------------------------------

PROJECT          ?=lambdafactory
SOURCES_PATH     ?=src
BUILD_PATH       ?=.build
DIST_PATH        ?=dist

# === SOURCES =================================================================

SOURCES_PY       =$(shell find $(SOURCES_PATH)/py -name "*.py")
SOURCES_SPY      =$(shell find $(SOURCES_PATH)/spy -name "*.spy")
SOURCES_PYMODULES=$(filter-out $(SOURCES_PATH)/spy/,$(shell find $(SOURCES_PATH)/spy/ -type "d")) 
SOURCES_MD       =$(wildcard *.md)
SOURCES_ALL      =$(SOURCES_SUGAR_PY) $(SOURCES_MODULES) $(SOURCES_MD)

# === BUILD ===================================================================

BUILD_PY        =$(SOURCES_SPY:$(SOURCES_PATH)/spy/%.spy=$(BUILD_PATH)/%.py)\
                 $(SOURCES_PY:$(SOURCES_PATH)/py/%.py=$(BUILD_PATH)/%.py)\
                 $(SOURCES_PYMODULES:$(SOURCES_PATH)/spy/%=$(BUILD_PATH)/%/__init__.py)
BUILD_ALL       =$(BUILD_PY)

# === DIST ====================================================================

DIST_PY         =$(BUILD_PY:$(BUILD_PATH)/%.py=$(DIST_PATH)/%.py)
DIST_HTML       =$(SOURCES_MD:%.md=%.html)
DIST_ALL        =$(DIST_PY) $(DIST_MODULES) $(DIST_HTML)

# === TOOLS ===================================================================

SUGAR           =sugar
PYTHON          =PYTHONPATH=$(SOURCES)/py:$(PYTHONPATH) && python3.5
PANDOC          =pandoc

# === HELPERS =================================================================

YELLOW           =`tput setaf 11`
GREEN            =`tput setaf 10`
BLUE             =`tput setaf 12`
CYAN             =`tput setaf 14`
RED              =`tput setaf 1`
GRAY             =`tput setaf 7`
RESET            =`tput sgr0`

TIMESTAMP       :=$(shell date +'%F')
BUILD_ID        :=$(shell git rev-parse --verify HEAD)
MAKEFILE_PATH   := $(abspath $(lastword $(MAKEFILE_LIST)))
MAKEFILE_DIR    := $(notdir $(patsubst %/,%,$(dir $(MAKEFILE_PATH))))


# From: http://marmelab.com/blog/2016/02/29/auto-documented-makefile.html
.DEFAULT_GOAL   := build
.PHONY          : build dist help clean

# -----------------------------------------------------------------------------
#
# RULES
#
# -----------------------------------------------------------------------------


build: $(BUILD_ALL) ## Builds all the project assets

dist: $(DIST_ALL) ## Updates the distribution of the project

help: ## Displays a description of the different Makefile rules
	@echo "$(CYAN)★★★ $(PROJECT) Makefile ★★★$(RESET)"
	@grep -E -o '((\w|-)+):[^#]+(##.*)$$'  $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":|##"}; {printf "make \033[01;32m%-15s\033[0m🕮 %s\n", $$1, $$3}'

clean: ## Cleans the build files
	@echo "$(RED)♻  clean: Cleaning $(words $(BUILD_ALL)) files $(RESET)"
	@echo "$(BLUE)♻  $(BUILD_ALL) $(RESET)"
	@echo $(BUILD_ALL) | xargs -n1 rm 2> /dev/null ; true
	@test -e $(BUILD_PATH) && rm -r $(BUILD_PATH) ; true

release: $(PRODUCT)
	git commit -a -m "Release $(VERSION)" ; true
	git tag $(VERSION) ; true
	git push --all ; true
	python setup.py clean sdist register upload

check:
	export PYTHONPATH=$(BUILD_PATH):$(PTYHONPATH) && pychecker -100 $(BUILD_PY)

# -----------------------------------------------------------------------------
#
# BUILDING
#
# -----------------------------------------------------------------------------

$(BUILD_PATH)/%.py: $(SOURCES_PATH)/py/%.py
	@echo "$(GREEN)📝  $@ [PY]$(RESET)"
	@mkdir -p `dirname $@`
	@cp --preserve=mode $< $@

$(BUILD_PATH)/%.py: $(SOURCES_PATH)/spy/%.spy
	@echo "$(GREEN)📝  $@ [SPY]$(RESET)"
	@mkdir -p `dirname $@`
	@$(SUGAR) -L$(SOURCES_PATH)/spy -clpy $< > $@
	@cp --attributes-only --preserve=mode $< $@

$(BUILD_PATH)%/__init__.py: $(SOURCES_PATH)/spy/%
	@echo "$(GREEN)📝  $@ [PY MODULE]$(RESET)"
	@mkdir -p `dirname $@`
	@touch $@

$(DIST_PATH)/%.py: $(BUILD_PATH)/%.py
	@echo "$(GREEN)📝  $@ [DIST]$(RESET)"
	@mkdir -p `dirname $@`
	@cp --preserve=mode $< $@

%.html: %.md
	@echo "$(GREEN)📝  $@ [PANDOC]$(RESET)"
	@mkdir -p `dirname $@`
	@$(PANDOC) $< -thtml -s -c "https://cdn.rawgit.com/sindresorhus/github-markdown-css/gh-pages/github-markdown.css"  | sed 's|<body>|<body><div class=markdown-body style="padding:4em;max-width:55em;">|g' > $@

# -----------------------------------------------------------------------------
#
# HELPERS
#
# -----------------------------------------------------------------------------

print-%:
	@echo $*=
	@echo $($*) | xargs -n1 echo | sort -dr

# EOF

