.PHONY: all anki tw clean

all: anki tw

anki:
	make -C anki-plugin

tw: output/index.html

output/index.html: docs/tiddlywiki.info docs/tiddlers/* tw-plugin/
	( cd docs/ && tiddlywiki --build )

clean:
	make -C anki-plugin clean
	rm -rf docs/output
