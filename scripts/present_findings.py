#!/usr/bin/env python3

import json
import logging
import os
import sys

output = {}


def parse_sbom(cyclonedx_sbom_json):
    metadata = cyclonedx_sbom_json.get('metadata')
    if metadata is None:
        logging.error("expected 'metadata' json object but it was not found")
        return

    component = metadata.get('component')
    if component is None:
        logging.error("expected 'component' json object but it was not found")
        return

    output["artifact_type"] = component["type"]
    output["artifact_name"] = component["name"]


def parse_inspector_findings(findings_json):
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
            logging.warning("expected inspector:sbom_scanner property but received unknown property: ", prop)

        output['total_vulnerabilities'] = total_vulns


def is_threshold_exceeded(vuln_count, threshold):
    if vuln_count >= threshold:
        return True
    return False


def main():
    inspector_scan_file = sys.argv[1]
    sbom_file = sys.argv[2]
    thresholds_enabled = sys.argv[3]
    critical_threshold = sys.argv[4]
    high_threshold = sys.argv[5]
    medium_threshold = sys.argv[6]
    low_threshold = sys.argv[7]

    sbom_json = ""
    with open(sbom_file, "r") as f:
        sbom_json = json.load(f)

    parse_sbom(sbom_json)

    findings_json = ""
    with open(inspector_scan_file, "r") as f:
        findings_json = json.load(f)

    parse_inspector_findings(findings_json)
    print(json.dumps(output, indent=4))

    thresholds = {critical_threshold: output['critical_vulnerabilities'],
                  high_threshold: output['high_vulnerabilities'],
                  medium_threshold: output['medium_vulnerabilities'],
                  low_threshold: output['low_vulnerabilities'],
                  }
    for key, value in thresholds.items():
        if is_threshold_exceeded(key, value):
            logging.warning(f"vulnerability count threshold exceeded")
            sys.exit(1)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
