.PHONY: all forms zip clean

all: forms zip
forms: 5forms 6forms
5forms: $(patsubst designer/%_dialog.ui,src/%_dialog5.py,$(wildcard designer/*))
6forms: $(patsubst designer/%_dialog.ui,src/%_dialog6.py,$(wildcard designer/*))
zip: build.ankiaddon

src/%_dialog5.py: designer/%_dialog.ui
	pyuic5 $^ > $@

src/%_dialog6.py: designer/%_dialog.ui
	pyuic6 $^ > $@

build.ankiaddon: src/*.py src/config.json
	rm -f $@
	( cd src/; zip -r ../$@ $(^F) )

clean:
	rm -rf src/__pycache__
	rm -f src/*_dialog.py
	rm -f build.ankiaddon
