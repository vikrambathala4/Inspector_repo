#!/bin/sh -l

ls -lsah

unzip testData.zip

./github/workspace/inspector-sbomgen directory --path testData -o sbom.json
