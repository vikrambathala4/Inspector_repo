#!/bin/sh -l

# inputs provided from CLI or GitHub Actions
artifact_type=$1
artifact_path=$2

sbomgen="/usr/local/bin/inspector-sbomgen"
prog="--disable-progress-bar"
artifact_path_arg=""

if [ "$artifact_type" == "repository" ]; then
  artifact_type="directory"
  artifact_path_arg="--path"

elif [ "$artifact_type" == "container" ]; then
  artifact_path_arg="--image"

elif [ "$artifact_type" == "binary" ]; then
  artifact_path_arg="--path"

elif [ "$artifact_type" == "archive" ]; then
  artifact_path_arg="--path"

else
  echo "invalid artifact provided"
fi

pwd=$(eval pwd)
echo "current working directory: " $pwd
ls -lsah
$sbomgen $artifact_type $artifact_path_arg $artifact_path $prog --scan-sbom -o sbom.json

# give other users read perms so we can upload the sbom file as an Actions artifact
mkdir sboms
chmod -R o+r sboms
mv sbom.json sboms

# move the logs and give needed permissions for the uploader
mv /github/home/.inspector-sbomgen/logs ./
chmod -R o+r logs
