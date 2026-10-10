.SECONDARY:
.DELETE_ON_ERROR:

BUILD_DIR := build
DEF_DIR := def
JSON_DIR := json
IMPORT_DIR := import
MD_DIR := md
DOCS_CLASSES_DIR := ../../docs/output-reference/classes

vpath %tag $(BUILD_DIR)
vpath %.classes $(BUILD_DIR)

SOURCES := $(wildcard *-source.yaml)
TAGS := $(SOURCES:-source.yaml=.tag)
IMPORTS := $(wildcard $(IMPORT_DIR)/*-source.yaml)

all: build-ordered ${TAGS} prune-tag

build-ordered: | $(BUILD_DIR)

$(BUILD_DIR):
	mkdir $(BUILD_DIR)

%.tag: %.classes %.json-tag %.defs-tag
	touch $(BUILD_DIR)/$@

%.classes: %-source.yaml
	source2classes $< >${BUILD_DIR}/$@

%.json-tag: %-source.yaml ${IMPORTS}
	source2splitjs $<
	touch $(BUILD_DIR)/$@

%.defs-tag: %-source.yaml ${IMPORTS}
	y2t $<
	touch $(BUILD_DIR)/$@

prune-tag: ${TAGS}
	$(MAKE) -f prune.mk
	touch $(BUILD_DIR)/$@

#=> docs: regenerate the Markdown class pages (md/) via y2md.py, then sync the
#=> generated pages into the docs site. Only pages that already exist under
#=> $(DOCS_CLASSES_DIR) are overwritten, so the hand-written category index
#=> pages (index/variations/propositions/statements/evidence) are preserved and
#=> dropped Extension* pages are never introduced.
.PHONY: docs
docs: all
	@for s in $(SOURCES); do python3 y2md.py $$s; done
	@for f in $(MD_DIR)/*.md; do \
	  base=$$(basename $$f); \
	  if [ -f "$(DOCS_CLASSES_DIR)/$$base" ]; then \
	    cp "$$f" "$(DOCS_CLASSES_DIR)/$$base"; \
	  fi; \
	done
	@echo "synced generated class pages -> $(DOCS_CLASSES_DIR)"

clean:
	rm $(BUILD_DIR)/*
	rm $(DEF_DIR)/*
	rm $(JSON_DIR)/*
	rm -f $(MD_DIR)/*