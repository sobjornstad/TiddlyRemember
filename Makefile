.PHONY: all zip

all: zip
zip: build.zip

build.zip: clean src/*
	( cd src/; zip -r ../$@ * )

clean:
	rm -f src/meta.json
	rm -rf src/__pycache__
	rm -f build.zip
