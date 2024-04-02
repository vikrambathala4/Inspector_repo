## Amazon Inspector for GitHub Actions

Amazon Inspector is a vulnerability management service that scans AWS workloads and [CycloneDX SBOMs](https://cyclonedx.org/) for known software vulnerabilities.

Using this action, you can automatically scan supported artifacts with Amazon Inspector from your GitHub Actions workflows.


## Overview

Amazon Inspector for GitHub Actions can be used to detect software vulnerabilities in the following artifacts within your GitHub Actions workflows:

1. Your repository contents
2. Container images
3. Compiled Go and Rust binaries
4. Archives *(.zip, .tar, .tar.gz)*

This action is powered by the [Amazon Inspector SBOM Generator (inspector-sbomgen)](https://docs.aws.amazon.com/inspector/latest/user/sbom-generator.html).

## Prerequisites

1. **Required:** You must have an active AWS account to use this action. Guidance on creating an AWS account is provided [here](https://docs.aws.amazon.com/inspector/latest/user/configure-cicd-account.html).

2. **Required:** You must have read access to the **InspectorScan:ScanSbom** API. [See here for configuration instructions](https://docs.aws.amazon.com/inspector/latest/user/configure-cicd-account.html#cicd-iam-role).

3. **Required:** You must configure AWS authentication on GitHub. We recommend using [configure-aws-credentials](https://github.com/marketplace/actions/configure-aws-credentials-action-for-github-actions) for this purpose.

4. **Required:** Create a GitHub Actions workflow if you do not already have one. Guidance on doing so is available [here](https://docs.github.com/en/actions/quickstart).

5. *Optional:* Configure container registry authentication if needed. GitHub Actions are available for this purpose including [Docker Login](https://github.com/marketplace/actions/docker-login).



## Usage

The following examples demonstrate how to use this action:

- Copy and paste the provided YAML excerpts into your GitHub Actions workflow file.

- Modify the input options as needed.


- See [here for example workflows](./.github/workflows/).


### 1. Scan Repository

This example will scan your repository contents for vulnerable software packages.

```yaml
- name: Invoke Amazon Inspector Scan
  uses: aws/amazon-inspector-github-actions-plugin@v1
  with:
    artifact_type: 'repository'
    artifact_path: './' # change this if you would like to scan a specific sub-directory, otherwise the entire repo will be scanned.
```

- [*See here for more information on the types of package vulnerabilities this action can detect*](https://docs.aws.amazon.com/inspector/latest/user/sbom-generator.html).


### 2. Scan Container Image

This example will scan a container image for vulnerable software packages.

```yaml
- name: Invoke Amazon Inspector Scan
  uses: aws/amazon-inspector-github-actions-plugin@v1
  with:
    artifact_type: 'container'
    artifact_path: 'alpine:latest' # change this to the image you would like to scan
```

This action can scan containers exported as tarballs, locally built images, and images from remote registries.

For locally built images, this action only supports images built with Docker engine.

- [*See here for an example on building an image, scanning the image, and failing the build if vulnerabilities are detected*](./.github/workflows/container_local.yml).


### 3. Scan Compiled Go or Rust Binary

This example will scan a compiled Go or Rust binary's package dependencies for vulnerabiliies.

```yaml
- name: Invoke Amazon Inspector Scan
  uses: aws/amazon-inspector-github-actions-plugin@v1
  with:
    artifact_type: 'binary'
    artifact_path: './path/to/binary' # change this to your binary's filepath
```

### 4. Scan Archive

This example will scan an archive for vulnerable software packages. The supported archive formats are **.zip**, **.tar**, and **.tar.gz**.

```yaml
- name: Invoke Amazon Inspector Scan
  uses: aws/amazon-inspector-github-actions-plugin@v1
  with:
    artifact_type: 'archive'
    artifact_path: './path/to/archive' # change this to your archive's filepath
```

## Action Inputs 

The following input options can be added to this action to control its behavior.

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
| scanners | No | Specifies the file scanners that you would like inspector-sbomgen to execute. By default, inspector-sbomgen will try to run all file scanners that are applicable to the target artifact. If this argument is set, inspector-sbomgen will only execute the specified file scanners. Provide your input as a single string. Separate each file scanner with a comma. To view a list of available file scanners, execute `inspector-sbomgen list-scanners`. [See here for more info](https://docs.aws.amazon.com/inspector/latest/user/sbom-generator.html). |
| skip_scanners | No | Specifies a list of file scanners that should NOT be executed; this argument cannot be combined with 'scanners'. If this argument is set, inspector-sbomgen will execute all file scanners except those you specified. Provide your input as a single string. Separate each file scanner with a comma. To view a list of available file scanners, execute `inspector-sbomgen list-scanners`. See [here for more info](https://docs.aws.amazon.com/inspector/latest/user/sbom-generator.html). |
| skip_files | No | Specifies one or more files and/or directories that should NOT be inventoried. Separate each file with a comma and enclose the entire string in double quotes. |
| timeout | No | Specifies a timeout in seconds. If this timeout is exceeded, the action will gracefully conclude and present any findings discovered up to that point. |

## Action Outputs

The following outputs are set by this action:

| **Option** | **Description** |
|---|---|
| artifact_sbom | The filepath to the generated SBOM. |
| inspector_scan_results | The filepath to the Inspector vulnerability scan in JSON format. |
| inspector_scan_results_csv | The filepath to the Inspector vulnerability scan in CSV format. |
| vulnerability_threshold_exceeded | This variable is set to 1 if any vulnerability threshold was exceeded, otherwise it is 0. |

## Security

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.

## License

This project is licensed under the Apache-2.0 License.

