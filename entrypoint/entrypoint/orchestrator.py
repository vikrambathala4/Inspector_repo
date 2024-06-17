import datetime
import json
import logging
import os
import platform
import shutil
import tempfile

from entrypoint import dockerfile
from entrypoint import installer
from entrypoint import executor
from entrypoint import pkg_vuln


def execute(args) -> int:
    logging.info(f"downloading and installing inspector-sbomgen version {args.sbomgen_version}")
    ret = install_sbomgen(args)
    require_true((ret == 0), "unable to download and install inspector-sbomgen")

    logging.info("generating SBOM from artifact")
    ret = invoke_sbomgen(args)
    require_true(ret == 0, "unable to generate SBOM with inspector-sbomgen")

    logging.info("scanning SBOM contents with Amazon Inspector")
    ret = invoke_inspector_scan(args.out_sbom, args.out_scan)
    require_true(ret == 0, "unable to scan SBOM contents with Amazon Inspector")
    set_github_actions_output('inspector_scan_results', args.out_scan)

    logging.info("tallying vulnerabilities")
    succeeded, total_vulns, criticals, highs, mediums, lows, others = get_vuln_counts(args.out_scan)
    require_true(succeeded, "unable to tally vulnerabilities")

    print_vuln_count_summary(args, total_vulns, criticals, highs, mediums, lows, others)

    set_flag_if_vuln_threshold_exceeded(args, criticals, highs, mediums, lows, others)

    write_pkg_vuln_report_csv(args, criticals, highs, mediums, lows, others)
    set_github_actions_output('inspector_scan_results_csv', args.out_scan_csv)

    pkg_vuln_markdown = write_pkg_vuln_report_markdown(args, total_vulns, criticals, highs, mediums, lows, others)
    post_pkg_vuln_github_actions_step_summary(args, pkg_vuln_markdown)
    set_github_actions_output('inspector_scan_results_markdown', args.out_scan_markdown)

    dockerfile.write_dockerfile_report_csv(args.out_scan, args.out_dockerfile_scan_csv)
    set_github_actions_output('inspector_dockerile_scan_results_csv', args.out_dockerfile_scan_csv)

    dockerfile.write_dockerfile_report_md(args.out_scan, args.out_dockerfile_scan_md)
    set_github_actions_output('inspector_dockerile_scan_results_markdown', args.out_dockerfile_scan_md)
    post_dockerfile_step_summary(args, total_vulns)

    return 0


def post_dockerfile_step_summary(args, total_vulns):
    if args.display_vuln_findings == "enabled" and int(total_vulns) > 0:
        logging.info("posting Inspector Dockerfile scan findings to GitHub Actions step summary page")

        dockerfile_markdown = ""
        try:
            with open(args.out_dockerfile_scan_md, "r") as f:
                dockerfile_markdown = f.read()
        except Exception as e:
            logging.debug(e)  # can be spammy, so set as debug log
            return

        if not dockerfile_markdown:
            return

        job_summary_file = "/tmp/inspector.md"
        if os.getenv('GITHUB_ACTIONS'):
            job_summary_file = os.environ["GITHUB_STEP_SUMMARY"]

        try:
            with open(job_summary_file, "a") as f:
                f.write(dockerfile_markdown)
        except Exception as e:
            logging.info(e)
            return


def download_install_sbomgen(sbomgen_version: str, install_dst: str) -> bool:
    cpu_arch = platform.machine()
    if "x86_64" in cpu_arch:
        cpu_arch = "amd64"

    elif "arm64" in cpu_arch:
        cpu_arch = "arm64"

    else:
        logging.error(f"expected a CPU architecture of x86_64, arm64, or amd64, but received: {cpu_arch}")
        return False

    # download sbomgen
    url = installer.get_sbomgen_url("Linux", cpu_arch, sbomgen_version)
    dst = tempfile.gettempdir()
    dst = os.path.join(dst, "inspector-sbomgen.zip")
    ret = installer.download_sbomgen(url, dst)
    if ret == "":
        return False

    # unzip sbomgen
    logging.debug(f"unpacking {dst}")
    extracted_src = dst
    extracted_dst = os.path.join(tempfile.gettempdir(), "inspector-sbomgen")
    ret = installer.extract_sbomgen(extracted_src, extracted_dst)
    if ret == "":
        return False

    # find sbomgen ELF binary
    logging.debug("locating inspector-sbomgen binary from unpacked archive")
    sbomgen_path = installer.find_file_in_dir("inspector-sbomgen", extracted_dst)
    if sbomgen_path == "":
        return False

    # install sbomgen
    # install_dst = "/usr/local/bin/inspector-sbomgen"
    logging.debug(f"installing {sbomgen_path} to {install_dst}")
    ret = installer.install_sbomgen(sbomgen_path, install_dst)
    if ret == "":
        return False

    logging.debug(f"setting inspector-sbomgen install path to: {install_dst}")
    installer.set_sbomgen_install_path(install_dst)
    return True


def invoke_sbomgen(args) -> int:
    sbomgen = installer.get_sbomgen_install_path()
    if sbomgen == "":
        logging.error("expected path to inspector-sbomgen but received empty string")
        return 1

    # marshall arguments between action.yml and cli.py
    path_arg = ""
    if args.artifact_type.lower() == "repository":
        args.artifact_type = "directory"
        path_arg = "--path"

    elif "container" in args.artifact_type.lower():
        args.artifact_type = "container"
        path_arg = "--image"

    elif "binary" in args.artifact_type.lower():
        args.artifact_type = "binary"
        path_arg = "--path"

    elif "archive" in args.artifact_type.lower():
        args.artifact_type = "archive"
        path_arg = "--path"

    else:
        logging.error(
            f"expected artifact type to be 'repository', 'container', 'binary' or 'archive' but received {args.artifact_type}")
        return 1

    # invoke sbomgen with arguments
    sbomgen_args = [args.artifact_type,
                    path_arg, args.artifact_path,
                    "--outfile", args.out_sbom,
                    "--disable-progress-bar",
                    "--timeout", args.timeout,
                    ]
    if args.scanners != "''":
        logging.info(f"setting --scanners: {args.scanners}")
        sbomgen_args.append("--scanners")
        sbomgen_args.append(args.scanners)
    elif args.skip_scanners != "''":
        logging.info(f"setting --skip-scanners: {args.skip_scanners}")
        sbomgen_args.append("--skip-scanners")
        sbomgen_args.append(args.skip_scanners)
    else:
        pass

    if args.skip_files != "''":
        logging.info(f"setting --skip-files: {args.skip_files}")
        sbomgen_args.append("--skip-files")
        sbomgen_args.append(args.skip_files)

    ret = executor.invoke_command(sbomgen, sbomgen_args)
    if ret != 0:
        return ret

    # make scan results readable by any user so
    # github actions can upload the file as a job artifact
    os.system(f"chmod 444 {args.out_sbom}")

    set_github_actions_output('artifact_sbom', args.out_sbom)

    return ret


def invoke_inspector_scan(src_sbom, dst_scan):
    aws_cli_args = ["inspector-scan", "scan-sbom",
                    "--sbom", f"file://{src_sbom}",
                    "--output-format", "CYCLONE_DX_1_5",
                    ">", f"{dst_scan}"
                    ]

    ret = executor.invoke_command("aws", aws_cli_args)
    if ret != 0:
        return ret

    return ret


def set_github_actions_output(key, value):
    if os.getenv('GITHUB_ACTIONS'):
        # set env var to expose SBOM contents
        # to github actions
        # https://docs.github.com/en/actions/using-jobs/defining-outputs-for-jobs
        logging.info(f"setting github actions output: {key}:{value}")
        os.system(f'echo "{key}={value}" >> "$GITHUB_OUTPUT"')

    return


def get_vuln_counts(inspector_scan_path: str):
    # vuln severities
    total_vulns = 0
    criticals = 0
    highs = 0
    mediums = 0
    lows = 0
    others = 0

    scan_contents = ""
    try:
        with open(inspector_scan_path, 'r') as f:
            scan_contents = json.load(f)
    except Exception as e:
        logging.error(e)
        return False

    # find the sbom->metadata->properties object
    scan_contents = scan_contents.get("sbom")
    if scan_contents is None:
        logging.error(
            f"expected Inspector scan results with 'sbom' as root object, but it was not found in file {inspector_scan_path}")
        return False, total_vulns, criticals, highs, mediums, lows, others

    metadata = scan_contents.get("metadata")
    if metadata is None:
        # no vulnerabilities found
        return True, total_vulns, criticals, highs, mediums, lows, others

    props = metadata.get("properties")
    if props is None:
        logging.error(f"expected metadata properties, but none were found in file {inspector_scan_path}")
        return False, total_vulns, criticals, highs, mediums, lows, others

    # iterate over each property and extract vulnerability counts by severity
    for prop in props:
        name = prop.get("name")
        if name is None:
            logging.error(f"expected property with 'name' key but none was found in file {inspector_scan_path}")
            continue

        value = prop["value"]
        if value is None:
            logging.error(f"expected property with 'value' key but none was found in file {inspector_scan_path}")
            continue

        if name == "amazon:inspector:sbom_scanner:critical_vulnerabilities":
            criticals = int(value)
        elif name == "amazon:inspector:sbom_scanner:high_vulnerabilities":
            highs = int(value)
        elif name == "amazon:inspector:sbom_scanner:medium_vulnerabilities":
            mediums = int(value)
        elif name == "amazon:inspector:sbom_scanner:low_vulnerabilities":
            lows = int(value)
        elif name == "amazon:inspector:sbom_scanner:other_vulnerabilities":
            others = int(value)
        else:
            logging.error(
                f"expected a vulnerability count property but received: '{name}': '{value}' in file {inspector_scan_path}")

    total_vulns = criticals + highs + mediums + lows + others
    return True, total_vulns, criticals, highs, mediums, lows, others


def get_summarized_findings(art_type, art_name, total_vulns, criticals, highs, mediums, lows, others):
    dtg = datetime.datetime.now()
    dtg_str = dtg.strftime("%Y-%m-%d %H:%M:%S")

    if art_type.lower() == "directory":
        art_type = "repository"

    results = f"""
    ------------------------------------
    Amazon Inspector Scan Summary:
    """

    if not art_name == "./":
        results += f"Artifact Name: {art_name}"

    results += f"""
    Artifact Type: {art_type}
    {dtg_str}
    ------------------------------------
    Total Vulnerabilities: {total_vulns}
    Critical:   {criticals}
    High:       {highs}
    Medium:     {mediums}
    Low:        {lows}
    Other:      {others}
    """

    return results


def exceeds_threshold(criticals, critical_threshold,
                      highs, high_threshold,
                      mediums, medium_threshold,
                      lows, low_threshold,
                      others, other_threshold) -> bool:
    is_threshold_exceed = False
    if 0 < critical_threshold <= criticals:
        is_threshold_exceed = True

    if 0 < high_threshold <= highs:
        is_threshold_exceed = True

    if 0 < medium_threshold <= mediums:
        is_threshold_exceed = True

    if 0 < low_threshold <= lows:
        is_threshold_exceed = True

    if 0 < other_threshold <= others:
        is_threshold_exceed = True

    return is_threshold_exceed


def install_sbomgen(args):
    os_name = platform.system()
    if "Linux" in os_name:
        ret = download_install_sbomgen(args.sbomgen_version, "/usr/local/bin/inspector-sbomgen")
        if not ret:
            return 1

    else:
        logging.warning(
            f"expected OS to be Linux, but our OS appears to be {os_name}; trying to use a local inspector-sbomgen binary as a fallback")
        path = shutil.which("inspector-sbomgen")
        if path is not None:
            installer.set_sbomgen_install_path(path)
        else:
            logging.error(
                "unable to find inspector-sbomgen; try downloading sbomgen for your platform and place in /usr/local/bin/inspector-sbomgen")
            return 1

    return 0


def write_pkg_vuln_report_csv(args, criticals, highs, mediums, lows, others):
    total_vulns = int(criticals) + int(highs) + int(mediums) + int(lows) + int(others)
    if total_vulns == 0:
        logging.info(f"skipping package vulnerability CSV report because no vulnerabilities were detected")
        return

    csv_output = {}
    with open(args.out_scan, "r") as f:
        inspector_scan = json.load(f)

        vulns = pkg_vuln.vulns_to_obj(inspector_scan)

        csv_output = pkg_vuln.to_csv(vulns, artifact_name=args.artifact_path,
                                     artifact_type=args.artifact_type,
                                     criticals=criticals,
                                     highs=highs,
                                     mediums=mediums,
                                     lows=lows,
                                     others=others)

        logging.info(f"writing package vulnerability CSV report to: {args.out_scan_csv}")
        with open(args.out_scan_csv, "w") as f:
            f.write(csv_output)


def write_pkg_vuln_report_markdown(args, total_vulns, criticals, highs, mediums, lows, others):
    with open(args.out_scan, "r") as f:
        inspector_scan = json.load(f)
        vulns = pkg_vuln.vulns_to_obj(inspector_scan)

        markdown = pkg_vuln.to_markdown(vulns, artifact_name=args.artifact_path,
                                        artifact_type=args.artifact_type,
                                        criticals=criticals,
                                        highs=highs,
                                        mediums=mediums,
                                        lows=lows,
                                        others=others)

        logging.info(f"writing package vulnerability markdown report to: {args.out_scan_markdown}")
        with open(args.out_scan_markdown, "w") as f:
            f.write(markdown)

        return markdown


def set_flag_if_vuln_threshold_exceeded(args, criticals, highs, mediums, lows, others):
    is_exceeded = exceeds_threshold(criticals, args.critical,
                                    highs, args.high,
                                    mediums, args.medium,
                                    lows, args.low,
                                    others, args.other)

    if is_exceeded and args.thresholds:
        set_github_actions_output('vulnerability_threshold_exceeded', 1)
    else:
        set_github_actions_output('vulnerability_threshold_exceeded', 0)


def print_vuln_count_summary(args, total_vulns, criticals, highs, mediums, lows, others):
    findings = get_summarized_findings(args.artifact_type, args.artifact_path, total_vulns, criticals, highs, mediums,
                                       lows,
                                       others)
    print(findings)


def post_pkg_vuln_github_actions_step_summary(args, markdown):
    if args.display_vuln_findings == "enabled":
        logging.info("posting Inspector scan findings to GitHub Actions step summary page")
        pkg_vuln.post_github_step_summary(markdown)


def require_true(expr: bool, msg: str):
    if not expr:
        logging.error(msg)
        exit(1)
