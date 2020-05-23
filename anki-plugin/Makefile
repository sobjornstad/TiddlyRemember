.PHONY: all forms zip clean

all: forms zip
forms: src/import_dialog.py src/settings_dialog.py
zip: build.ankiaddon

src/import_dialog.py: designer/import_dialog.ui 
	pyuic5 $^ > $@

src/settings_dialog.py: designer/settings_dialog.ui 
	pyuic5 $^ > $@

build.ankiaddon: src/*.py src/config.json
	rm -f $@
	( cd src/; zip -r ../$@ *.py config.json )

clean:
	rm -f src/__pycache__
	rm -f src/*_dialog.py
	rm -f build.ankiaddon
