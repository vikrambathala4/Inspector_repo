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
sbom_dir="sbom"
mkdir $sbom_dir

# give the output SBOM a traceable name:
dtg=$(date +"%Y-%m-%d_%H-%M-%S")
job=$(echo $GITHUB_RUN_ID)
out_file="$sbom_dir/sbom-$job-$dtg.json"

$sbomgen $artifact_type $artifact_path_arg $artifact_path $prog -o $out_file

# move the logs and give needed permissions for the uploader
mkdir logs
mv /github/home/.inspector-sbomgen/logs/*.txt logs/inspector-sbomgen-log-$job-$dtg.txt
chmod -R o+r logs
chmod -R o+r $sbom_dir

# scan SBOM with Inspector
echo "scanning $out_file with Amazon Inspector"
scan_dir=inspector-scan
scan_file=$scan_dir/inspector-scan-$job-$dtg.json
mkdir $scan_dir
cp $out_file ./sbom_to_scan.json
aws inspector-scan scan-sbom --sbom file://sbom_to_scan.json --output-format CYCLONE_DX_1_5 > $scan_file 2>&1
chmod -R o+r $scan_dir

# present findings
python3 /present_findings.py $scan_file
