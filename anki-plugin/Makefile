.PHONY: all forms zip clean

all: forms zip
forms: $(patsubst designer/%_dialog.ui,src/%_dialog.py,$(wildcard designer/*))
zip: build.ankiaddon

src/%_dialog.py: designer/%_dialog.ui
	pyuic6 $^ > $@

build.ankiaddon: src/*.py src/config.json
	rm -f $@
	( cd src/; zip -r ../$@ $(^F) )

clean:
	rm -rf src/__pycache__
	rm -f src/*_dialog.py
	rm -f build.ankiaddon
