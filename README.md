## Amazon Inspector for GitHub Actions

Amazon Inspector is a vulnerability management service that continually scans your AWS workloads for known software vulnerabilities and unintended network exposure.

Using this action, you can automatically scan supported artifacts with Amazon Inspector from your GitHub Actions workflows.


## Overview

Amazon Inspector for GitHub Actions can be used to scan the following artifacts within your GitHub Actions workflows:

1. Your repository contents
2. Container images
3. Compiled Go and Rust binaries
4. Archives *(.zip, .tar, .tar.gz)*

This action is powered by the [Amazon Inspector SBOM Generator (inspector-sbomgen)](https://docs.aws.amazon.com/inspector/latest/user/sbom-generator.html).


## Usage

1. Create an AWS account if needed [(see here)](https://docs.aws.amazon.com/inspector/latest/user/configure-cicd-account.html#cicd-iam-role).

2. Configure IAM permissions [(see here)](https://docs.aws.amazon.com/inspector/latest/user/configure-cicd-account.html#cicd-iam-role).

3. Configure AWS authentication on GitHub if needed. We recommend using [configure-aws-credentials](https://github.com/aws-actions/configure-aws-credentials) for this purpose.

4. Copy and paste this text into your workflow file:

```
- name: Invoke Amazon Inspector Scan
uses: aws/amazon-inspector-github-actions-plugin@v1
with:
  artifact_type: 'repository'
  artifact_path: './'
```

5. Modify the input options as needed. See [here for real-world examples](./.github/workflows/).

## Options

The following input arguments are available in this action.

See [action.yml](./action.yml) for more detail.

| Option | Required | Description |
|---|---|---|
| artifact_type | **Yes** | The artifact you would like to scan with Amazon Inspector. Valid choices are "repository", "container", "binary", or "archive". |
| artifact_path | **Yes** | The path to the artifact you would like to scan with Amazon Inspector. If scanning a container image, you must provide a  value that follows the docker pull convention: "NAME[:TAG\|@DIGEST]", for example, "alpine:latest", or a path to an image exported as tarball using "docker save". |
| output_sbom_path | No | The destination file path for the generated SBOM. |
| output_inspector_scan_path | No | The destination file path for Inspector's vulnerability scan (JSON format). |
| output_inspector_scan_path_csv | No | The destination file path for Inspector's vulnerability scan (CSV format). |
| sbomgen_version | No | The inspector-sbomgen version you wish to use for SBOM generation. See [here for more info](https://docs.aws.amazon.com/inspector/latest/user/sbom-generator.html). |
| critical_threshold | No | Specifies the number of critical vulnerabilities to trigger job failure. |
| high_threshold | No | Specifies the number of high vulnerabilities to trigger job failure. |
| medium_threshold | No | Specifies the number of medium vulnerabilities to trigger job failure. |
| low_threshold | No | Specifies the number of low vulnerabilities to trigger job failure. |
| other_threshold | No | Specifies the number of 'other' vulnerabilities to trigger job failure, such as 'info', 'none', or 'unknown'. |
| scanners | No | Specifies the file scanners that you would like inspector-sbomgen to execute. By default, inspector-sbomgen will try to run all file scanners that are applicable to the target artifact. If this argument is set, inspector-sbomgen will only execute the specified file scanners. Provide your input as a single string. Separate each file scanner with a comma. Execute 'inspector-sbomgen list-scanners' to get a list of available scanners. See [here for more info](https://docs.aws.amazon.com/inspector/latest/user/sbom-generator.html). |
| skip_scanners | No | Specifies a list of file scanners that should NOT be executed; this argument cannot be combined with 'scanners'. If this argument is set, inspector-sbomgen will execute all file scanners except those you specified. Provide your input as a single string. Separate each file scanner with a comma. To view a list of available file scanners, execute 'inspector-sbomgen list-scanners'. See [here for more info](https://docs.aws.amazon.com/inspector/latest/user/sbom-generator.html). |
| skip_files | No | Specifies one or more files and/or directories that should NOT be inventoried. Separate each file with a comma and enclose the entire string in double quotes. |

## Security

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.

## License

This project is licensed under the Apache-2.0 License.

