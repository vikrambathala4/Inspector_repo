#!/usr/bin/env python3

import json
import logging
import sys

# stores the output that is presented to the user on program completion
output = {}


def parse_sbom(cyclonedx_sbom_json):
    """
    given a cyclonedx sbom, this function will try to extract
    the artifact's name and type
    """
    metadata = cyclonedx_sbom_json.get('metadata')
    if metadata is None:
        logging.warning("expected 'metadata' json object but it was not found")
        return

    component = metadata.get('component')
    if component is None:
        logging.warning("expected 'component' json object but it was not found")
        return

    output["artifact_type"] = component["type"]
    output["artifact_name"] = component["name"]


def parse_inspector_findings(findings_json):
    """
    given inspector scan-sbom findings in cyclonedx json,
    this function extracts vulnerability counts by severity (critical/high/medium/low)
    and stores the counts in the 'output' variable
    """

    # try to find the sbom->metadata->properties array
    sbom = findings_json.get('sbom')
    if sbom is None:
        logging.error("expected root json object, 'sbom', but it was not found")
        return

    metadata = sbom.get('metadata')
    if metadata is None:
        logging.error("expected 'metadata' json object but it was not found")
        return
    props = metadata.get('properties')
    if props is None:
        logging.error("expected 'properties' json object but it was not found")
        return

    # iterate over the properties array and get vulnerability counts
    total_vulns = 0
    for prop in props:
        if 'critical' in prop['name']:
            output['critical_vulnerabilities'] = prop['value']
            total_vulns += int(prop['value'])

        elif 'high' in prop['name']:
            output['high_vulnerabilities'] = prop['value']
            total_vulns += int(prop['value'])

        elif 'medium' in prop['name']:
            output['medium_vulnerabilities'] = prop['value']
            total_vulns += int(prop['value'])

        elif 'low' in prop['name']:
            output['low_vulnerabilities'] = prop['value']
            total_vulns += int(prop['value'])

        else:
            logging.warning("skipping unknown property:\n    ", prop)

    output['total_vulnerabilities'] = total_vulns


def is_threshold_exceeded(threshold, vuln_count):
    if int(threshold) == 0:
        return False

    if int(vuln_count) >= int(threshold):
        return True

    return False


def main():
    # cli args are provided from entrypoint.sh
    inspector_scan_file = sys.argv[1]
    sbom_file = sys.argv[2]
    thresholds_enabled = sys.argv[3]
    critical_threshold = int(sys.argv[4])
    high_threshold = int(sys.argv[5])
    medium_threshold = int(sys.argv[6])
    low_threshold = int(sys.argv[7])

    # get artifact name and type from the sbom generated by inspector-sbomgen
    sbom_json = ""
    with open(sbom_file, "r") as f:
        sbom_json = json.load(f)
    parse_sbom(sbom_json)

    # get vulnerability counts by severity from Inspector scan-sbom json
    findings_json = ""
    with open(inspector_scan_file, "r") as f:
        findings_json = json.load(f)
    parse_inspector_findings(findings_json)

    # add vuln thresholds to output object
    if critical_threshold > 0:
        output["critical_threshold"] = critical_threshold

    if high_threshold > 0:
        output["high_threshold"] = critical_threshold

    if medium_threshold > 0:
        output["medium_threshold"] = critical_threshold

    if low_threshold > 0:
        output["low_threshold"] = critical_threshold

    # display output to the user
    logging.info(f"\n{json.dumps(output, indent=4)}")

    thresholds_enabled = thresholds_enabled.lower().strip()
    if thresholds_enabled != "true":
        sys.exit(0)

    # map our thresholds to the number of vulnerabilities by severity
    severity_mapping = {critical_threshold: output['critical_vulnerabilities'],
                        high_threshold: output['high_vulnerabilities'],
                        medium_threshold: output['medium_vulnerabilities'],
                        low_threshold: output['low_vulnerabilities'],
                        }

    # check if the vuln threshold is exceeded for each severity
    for threshold, num_vulns in severity_mapping.items():
        if is_threshold_exceeded(threshold, num_vulns):
            logging.warning(f"vulnerability count threshold exceeded - exiting with code 1")
            sys.exit(1)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
