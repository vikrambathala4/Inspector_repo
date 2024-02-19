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


# create a directory to store output SBOMs
sbom_dir="inspector_scan_results"
mkdir $sbom_dir

# give the output SBOM a traceable name:
# 
dtg=$(date +"%Y-%m-%d_%H-%M-%S")
job=$(echo $GITHUB_RUN_ID)
out_file="$sbom_dir/$job-scan-$dtg.json"
echo "Out file $out_file"

$sbomgen $artifact_type $artifact_path_arg $artifact_path $prog --scan-sbom -o $out_file

# move the logs and give needed permissions for the uploader
mv /github/home/.inspector-sbomgen/logs/*.txt ./$job-log-$dtg.txt
chmod -R o+r logs
chmod -R o+r $sbom_dir

