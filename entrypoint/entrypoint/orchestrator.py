from entrypoint import installer
from entrypoint import executor

import base64
import datetime
import json
import logging
import os
import platform
import shutil
import tempfile
import zlib


def compress_encode_file(file):
    contents = ""
    with open(file) as f:
        contents = f.read()

    compressed_contents = zlib.compress(contents.encode())
    encoded = base64.b64encode(compressed_contents).decode()
    return encoded


def set_github_output(key, value):
    if os.getenv('GITHUB_ACTIONS') == 'true':
        return os.system(f'echo "{key}={value}" >> "$GITHUB_OUTPUT"')
    else:
        return 0


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
        path_arg = "--image"

    elif "archive" in args.args.artifact_type.lower():
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
                    "--disable-progress-bar"
                    ]
    ret = executor.invoke_command(sbomgen, sbomgen_args)
    if ret != 0:
        return ret

    # encode and compress sbom so we can set
    # contents as a GitHub Output, which has a 1MB limit
    encoded_sbom = ""
    try:
        encoded_sbom = compress_encode_file(args.out_sbom)
    except Exception as e:
        logging.error(e)
        return 1

    ret = set_github_output("artifact_sbom", encoded_sbom)
    if ret != 0:
        logging.error("unable to set GitHub output for 'artifact_sbom'")
        return ret

    # make scan results file world readable so
    # github actions can upload the file as a job artifact
    os.system(f"chmod 444 {args.out_sbom}")

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

    # encode and compress sbom so we can set
    # contents as a GitHub Output, which has a 1MB limit
    encoded_scan = ""
    try:
        encoded_scan = compress_encode_file(dst_scan)
    except Exception as e:
        logging.error(e)
        return 1

    if set_github_output("inspector_scan_results", encoded_scan) != 0:
        logging.error("unable to set GitHub output for 'inspector_scan_results'")

    return ret


def get_vuln_counts(inspector_scan_path: str):
    # vuln severities
    criticals = 0
    highs = 0
    mediums = 0
    lows = 0
    nones = 0
    unknowns = 0
    infos = 0
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
        elif "none" in name:
            nones = int(value)
        elif "unknown" in name:
            unknowns = int(value)
        elif "info" in name:
            infos = int(value)
        else:
            logging.error(
                f"expected a vulnerability count property but received: '{name}': '{value}' in file {inspector_scan_path}")

    total_vulns = criticals + highs + mediums + lows + nones + unknowns + infos
    others = nones + unknowns + infos
    return True, total_vulns, criticals, highs, mediums, lows, others


def get_summarized_findings(art_type, art_name, total_vulns, criticals, highs, mediums, lows, others):
    dtg = datetime.datetime.now()
    dtg_str = dtg.strftime("%Y-%m-%d %H:%M:%S")
    results = f"""
    ------------------------------------
    Amazon Inspector Scan Summary:
    Artifact Name: {art_name}
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
        return

    findings = get_summarized_findings(args.artifact_type, args.artifact_path, total_vulns, criticals, highs, mediums,
                                       lows,
                                       others)
    print(findings)

    is_exceeded = exceeds_threshold(criticals, args.critical,
                                    highs, args.high,
                                    mediums, args.medium,
                                    lows, args.low,
                                    others, args.other)

    if is_exceeded and args.thresholds:
        logging.warning("Vulnerability thresholds exceeded!")
        return 1

    return 0
