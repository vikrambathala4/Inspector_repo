from entrypoint import converter
from entrypoint import installer
from entrypoint import executor

import datetime
import json
import logging
import os
import platform
import shutil
import tempfile


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
    extracted_src = dst
    extracted_dst = os.path.join(tempfile.gettempdir(), "inspector-sbomgen")
    ret = installer.extract_sbomgen(extracted_src, extracted_dst)
    if ret == "":
        return False

    # find sbomgen ELF binary
    sbomgen_path = installer.find_file_in_dir("inspector-sbomgen", extracted_dst)
    if sbomgen_path == "":
        return False

    # install sbomgen
    # install_dst = "/usr/local/bin/inspector-sbomgen"
    ret = installer.install_sbomgen(sbomgen_path, install_dst)
    if ret == "":
        return False

    installer.set_sbomgen_install_path(install_dst)
    return True


def set_github_actions_output(key, value):
    if os.getenv('GITHUB_ACTIONS'):
        # set env var to expose SBOM contents
        # to github actions
        # https://docs.github.com/en/actions/using-jobs/defining-outputs-for-jobs
        logging.info(f"setting github actions output: {key}:{value}")
        os.system(f'echo "{key}={value}" >> "$GITHUB_OUTPUT"')

    return


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

    set_github_actions_output('inspector_scan_results', dst_scan)

    return ret


def get_vuln_counts(inspector_scan_path: str):
    # vuln severities
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
        return False, criticals, highs, mediums, lows, others

    metadata = scan_contents.get("metadata")
    if metadata is None:
        # no vulnerabilities found
        return True, criticals, highs, mediums, lows, others

    props = metadata.get("properties")
    if props is None:
        logging.error(f"expected metadata properties, but none were found in file {inspector_scan_path}")
        return False, criticals, highs, mediums, lows, others

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


def execute(args) -> int:
    os_name = platform.system()
    if "Linux" in os_name:
        logging.info(f"downloading and installing inspector-sbomgen version {args.sbomgen_version}")
        download_install_sbomgen(args.sbomgen_version, "/usr/local/bin/inspector-sbomgen")

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

    logging.info("generating SBOM from artifact")
    ret = invoke_sbomgen(args)
    if ret != 0:
        logging.error("unable to generate SBOM with inspector-sbomgen")
        return 1

    logging.info("scanning SBOM contents with Amazon Inspector")
    ret = invoke_inspector_scan(args.out_sbom, args.out_scan)
    if ret != 0:
        logging.error("unable to scan SBOM contents with Amazon Inspector")
        return 1

    # make scan results file world readable so
    # github actions can upload the file as a job artifact
    os.system(f"chmod 444 {args.out_scan}")

    logging.info("tallying vulnerabilities")
    succeeded, total_vulns, criticals, highs, mediums, lows, others = get_vuln_counts(args.out_scan)
    if not succeeded:
        return 1

    findings = get_summarized_findings(args.artifact_type, args.artifact_path, total_vulns, criticals, highs, mediums,
                                       lows,
                                       others)
    print(findings)

    # create CSV output
    csv_output = {}
    with open(args.out_scan, "r") as f:
        inspector_scan = json.load(f)
        vulns = converter.vulns_to_obj(inspector_scan)

        csv_output = converter.to_csv(vulns, artifact_name=args.artifact_path,
                                      artifact_type=args.artifact_type,
                                      criticals=criticals,
                                      highs=highs,
                                      mediums=mediums,
                                      lows=lows,
                                      others=others)

        with open(args.out_scan_csv, "w") as f:
            f.write(csv_output)

        set_github_actions_output('inspector_scan_results_csv', args.out_scan_csv)

        # create markdown report
        logging.info("creating Inspector scan job summary")
        markdown = converter.to_markdown(vulns, artifact_name=args.artifact_path,
                                         artifact_type=args.artifact_type,
                                         criticals=criticals,
                                         highs=highs,
                                         mediums=mediums,
                                         lows=lows,
                                         others=others)

        if args.display_vuln_findings:
            logging.info("posting markdown to job summary")
            converter.post_github_step_summary(markdown)

    is_exceeded = exceeds_threshold(criticals, args.critical,
                                    highs, args.high,
                                    mediums, args.medium,
                                    lows, args.low,
                                    others, args.other)

    if is_exceeded and args.thresholds:
        set_github_actions_output('vulnerability_threshold_exceeded', 1)
    else:
        set_github_actions_output('vulnerability_threshold_exceeded', 0)

    return 0
