#!/usr/bin/env python3

import json
import logging
import sys

output = {}


def parse_findings(findings_json):
    """
    comp-1 describes the artifact being scanned
    """
    components = findings_json['components']
    for comp in components:

        # get artifact info
        if comp['bom-ref'] == 'comp-1':
            output["artifact_name"] = comp['name']
            output["artifact_type"] = comp['type']
            output["artifact_version"] = comp['version']

    # get number of vulns by severity
    total_vulns = 0
    metadata = findings_json['metadata']
    for prop in metadata['properties']:
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


def main():
    input_file = sys.argv[1]
    logging.info("reading file: ", input_file)

    findings_json = ""
    with open(input_file, "r") as f:
        findings_json = json.load(f)

    parse_findings(findings_json)
    print(json.dumps(output, indent=4))

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
