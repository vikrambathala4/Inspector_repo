#!/bin/sh -l

sub_command=$1
artifact_to_scan=$2

if [ "$sub_command" == "repository" ]; then

  # Generate SBOM from the repository contents
  ./inspector-sbomgen directory --path $artifact_to_scan -o sbom.json

  # get timestamp in format: YYYY-MM-DD_HH:MM:SS
  timestamp=$(date +"%Y-%m-%d_%H:%M:%S")
  new_filename="sbom_${timestamp}.json"
  mv sbom.json $new_filename

else
  echo "TODO: error"
fi

