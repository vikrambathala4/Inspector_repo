#!/bin/sh -l

# inputs provided from CLI or GitHub Actions
artifact_type=$1
artifact_path=$2

sbomgen="inspector-sbomgen"
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

$sbomgen $artifact_type $artifact_path_arg $artifact_path $prog -o sbom.json
