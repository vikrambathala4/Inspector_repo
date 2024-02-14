#!/bin/sh -l

# Action inputs
artifact_to_scan=$1
container_image=$2
sbomgen="inspector-sbomgen"
prog="--disable-progress-bar"

if [ "$artifact_to_scan" == "repository" ]; then
  artifact_to_scan="directory"
  $sbomgen $artifact_to_scan --path ./ $prog -o /tmp/sbom.json

elif [ "$artifact_to_scan" == "container" ]; then
  $sbomgen $artifact_to_scan --image $container_image $prog -o /tmp/sbom.json

elif [ "$artifact_to_scan" == "binary" ]; then
  $sbomgen $artifact_to_scan --image $container_image $prog -o /tmp/sbom.json

else
  echo "invalid artifact provided"
fi

