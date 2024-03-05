import json
import logging
import sys

from tabulate import tabulate


# stores the output that is presented to the user on program completion
class Output:
    def __init__(self):
        self.artifact_type = ""
        self.artifact_name = ""
        self.scan_serial = ""
        self.scan_timestamp = ""
        self.total_vulns_found = 0
        self.criticals_found = 0
        self.critical_threshold = 0
        self.highs_found = 0
        self.high_threshold = 0
        self.mediums_found = 0
        self.medium_threshold = 0
        self.lows_found = 0
        self.low_threshold = 0

    def present_output(self):
        separator = "-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-="
        print(separator)
        print("\tAmazon Inspector Finding Summary")
        print(separator)

        print(f"Artifact Type: {self.artifact_type}")
        print(f"Artifact Name: {self.artifact_name}")  # TODO: add image ID for containers
        print(f"Inspector Scan Serial Number: {self.scan_serial}")
        print(f"Inspector Scan Timestamp: {self.scan_timestamp}")
        # print(f"Total Vulnerabilities Found: {self.total_vulns_found}")
        """
        print(f"Critical Vulnerabilities Found: {self.criticals_found}")
        print(f"Critical Threshold: {self.critical_threshold}")
        print(f"High Vulnerabilities Found: {self.highs_found}")
        print(f"High Threshold: {self.high_threshold}")
        print(f"Medium Vulnerabilities Found: {self.mediums_found}")
        print(f"Medium Threshold: {self.medium_threshold}")
        print(f"Low Vulnerabilities Found: {self.lows_found}")
        print(f"Low Threshold: {self.low_threshold}")
        """

        # TODO: add support for "Info", "None", "Unknown"
        header = ["Total", "Critical", "High", "Medium", "Low"]
        table = []
        row = [self.total_vulns_found, self.criticals_found, self.highs_found, self.mediums_found, self.lows_found]
        table.append(row)
        print(tabulate(table, headers=header))
        print()


new_output = Output()


def parse_sbom(cyclonedx_sbom_json):
    """
    given a cyclonedx sbom, this function will try to extract
    the artifact's name, type, and other metadata.
    """
    serial_number = cyclonedx_sbom_json.get('serialNumber')
    if serial_number is None:
        logging.warning("expected 'serialNumber' json object but it was not found")
        return
    new_output.scan_serial = serial_number

    metadata = cyclonedx_sbom_json.get('metadata')
    if metadata is None:
        logging.warning("expected 'metadata' json object but it was not found")
        return

    timestamp = metadata.get('timestamp')
    if timestamp is None:
        logging.warning("expected 'timestamp' in metadata object but it was not found")
        return
    new_output.scan_timestamp = timestamp

    component = metadata.get('component')
    if component is None:
        logging.warning("expected 'component' json object but it was not found")
        return

    new_output.artifact_type = component["type"]
    new_output.artifact_name = component["name"]


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
            new_output.criticals_found = prop['value']
            total_vulns += int(prop['value'])

        elif 'high' in prop['name']:
            new_output.highs_found = prop['value']
            total_vulns += int(prop['value'])

        elif 'medium' in prop['name']:
            new_output.mediums_found = prop['value']
            total_vulns += int(prop['value'])

        elif 'low' in prop['name']:
            new_output.lows_found = prop['value']
            total_vulns += int(prop['value'])

        else:
            logging.warning("skipping unknown property:\n    ", prop)

    new_output.total_vulns_found = total_vulns


def is_threshold_exceeded(threshold, vuln_count):
    if int(threshold) == 0:
        return False

    if int(vuln_count) >= int(threshold):
        return True

    return False


def check_vuln_thresholds(inspector_scan_file: str, sbom_file: str, thresholds_enabled: str, critical_threshold: int,
                          high_threshold: int, medium_threshold: int, low_threshold: int):
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
        new_output.critical_threshold = critical_threshold

    if high_threshold > 0:
        new_output.high_threshold = critical_threshold

    if medium_threshold > 0:
        new_output.medium_threshold = critical_threshold

    if low_threshold > 0:
        new_output.low_threshold = critical_threshold

    # display output to the user
    new_output.present_output()

    thresholds_enabled = thresholds_enabled.lower().strip()
    if thresholds_enabled != "true":
        logging.info("thresholds disabled, exiting")
        sys.exit(0)

    logging.info("checking if vulnerability thresholds are exceeded")
    # map our thresholds to the number of vulnerabilities by severity
    severity_mapping = {critical_threshold: new_output.criticals_found,
                        high_threshold: new_output.highs_found,
                        medium_threshold: new_output.mediums_found,
                        low_threshold: new_output.lows_found,
                        }

    # check if the vuln threshold is exceeded for each severity
    for threshold, num_vulns in severity_mapping.items():
        if is_threshold_exceeded(threshold, num_vulns):
            logging.warning(f"vulnerability count threshold exceeded - exiting with code 1")
            sys.exit(1)
