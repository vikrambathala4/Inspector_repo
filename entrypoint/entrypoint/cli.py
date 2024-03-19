import argparse


def init(sys_argv=None) -> argparse.Namespace:
    """
    initializes the CLI using argparse :param: a list of arguments; you should pass sys.argv in most cases.
    Alternatively, you can provide custom values for use in unit tests
    :return: namespace containing values for each CLI key
    """
    program_description = "This program orchestrates the business logic for the Amazon Inspector GitHub Actions plugin."
    parser = argparse.ArgumentParser(description=program_description)
    parser.add_argument('--artifact-type', type=str,
                        help='The artifact you would like to scan with Amazon Inspector. Valid choices are "repository", "container", "binary", or "archive".')
    parser.add_argument("--artifact-path", type=str,
                        help='The path to the artifact you would like to scan with Amazon Inspector. If scanning a container image, you must provide a  value that follows the docker pull convention: "NAME[:TAG|@DIGEST]", for example, "alpine:latest", or a path to an image exported as tarball using "docker save".')
    parser.add_argument("--out-sbom", type=str, help="The destination file path for the generated SBOM.")
    parser.add_argument("--out-scan", type=str,
                        help="The destination file path for Inspector's vulnerability scan in JSON format.")
    parser.add_argument("--out-scan-csv", type=str,
                        help="The destination file path for Inspector's vulnerability scan in CSV format.")
    parser.add_argument("--verbose", action="store_true", help="Enables verbose console logging.")
    parser.add_argument("--sbomgen-version", type=str,
                        help="The inspector-sbomgen version you wish to use for SBOM generation.")
    parser.add_argument("--sbomgen-args", nargs="+",
                        help="Any additional arguments you wish to provide to inspector-sbomgen. Download sbomgen and execute it with './inspector-sbomgen --help' to see available arguments. https://docs.aws.amazon.com/inspector/latest/user/sbom-generator.html")
    parser.add_argument("--thresholds", action="store_true",
                        help='This will cause the program to fail with exit code 1 if vulnerability thresholds are exceeded.')
    parser.add_argument("--critical", type=int, default=0,
                        help="Specifies the number of critical vulnerabilities to trigger failure.")
    parser.add_argument("--high", type=int, default=0,
                        help="Specifies the number of high vulnerabilities to trigger failure.")
    parser.add_argument("--medium", type=int, default=0,
                        help="Specifies the number of medium vulnerabilities to trigger failure.")
    parser.add_argument("--low", type=int, default=0,
                        help="Specifies the number of low vulnerabilities to trigger failure.")
    parser.add_argument("--other", type=int, default=0,
                        help="Specifies the number of 'other' vulnerabilities to trigger failure, such as 'info', 'none', or 'unknown'.")
    parser.add_argument("--scanners", type=str, default="''",
                        help="Specifies the file scanner types you would like to execute. If left blank, the system will execute all applicable file scanners; this is the default behavior")
    parser.add_argument("--skip-scanners", type=str, default="''",
                        help="Specifies the file scanner types you do NOT wish to execute.")
    parser.add_argument("--skip-files", type=str, default="''",
                        help="Specifies one or more files and/or directories that should NOT be inventoried.")

    args = ""
    if sys_argv:
        args = parser.parse_args(sys_argv)
    else:
        args = parser.parse_args()

    return args
