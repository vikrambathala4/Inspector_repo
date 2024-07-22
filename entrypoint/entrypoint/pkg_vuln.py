"""
pkg_vuln.py has functions for parsing
Inspector ScanSbom API JSON, and converting
to different formats (CSV and markdown).
"""

import csv
import json
import logging
import os
import urllib.parse

from dataclasses import dataclass
from io import StringIO
from typing import List


class Vulnerability:
    """
    Vulnerability is an object for marshalling
    vulnerability findings from Inspector's
    ScanSbom JSON into a python object that can
    be queried and manipulated
    """

    def __init__(self):
        self.vuln_id = "null"
        self.severity = "null"
        self.cvss_score = "null"
        self.published = "null"
        self.modified = "null"
        self.description = "null"
        self.installed_ver = "null"
        self.fixed_ver = "null"
        self.pkg_path = "null"
        self.epss_score = "null"
        self.exploit_available = "null"
        self.exploit_last_seen = "null"
        self.cwes = "null"


@dataclass
class CvssRating:
    severity: str = "null"
    cvss_score: str = "null"


def vulns_to_obj(inspector_scan_json) -> List[Vulnerability]:
    """
    this function parses JSON from Inspector's ScanSbom API
    and returns a list of vulnerability objects.
    """

    vuln_list = []

    # check if the input has the fields we expect; anything without
    # these fields is assumed to be garbage and None is returned
    scan_contents = inspector_scan_json.get("sbom")
    fatal_assert(scan_contents != None, "expected JSON with key 'sbom' but none was found")

    components = scan_contents.get("components")
    if not components: return vuln_list

    vulns = scan_contents.get("vulnerabilities")
    if not vulns: return vuln_list

    pkg_vulns = get_pkg_vulns(vulns)

    for v in pkg_vulns:

        vuln_obj = Vulnerability()

        # get vuln ID
        id = v.get("id")
        if id:
            vuln_obj.vuln_id = id

        # get vuln severity and EPSS score
        ratings = v.get("ratings")
        add_ratings(ratings, vuln_obj)

        # get vulnerability published date
        published = v.get("created")
        if published:
            vuln_obj.published = published

        # get vulnerability modified date
        modified = v.get("updated")
        if modified:
            vuln_obj.modified = modified

        # get vulnerability description
        description = v.get("description")
        if description:
            s = description.strip()
            s = s.replace("\n", " ")
            s = s.replace("\t", " ")
            vuln_obj.description = s

        # get package URL from each affected component
        affected_package_urls = []
        affected_package_paths = []
        affected_bom_refs = v.get("affects")
        if affected_bom_refs:

            # get PURL from each affected bom-ref
            for each_bomref in affected_bom_refs:

                # iterate over components until we find
                # the affected bom-ref
                for each_component in components:
                    ref = each_component.get("bom-ref")
                    if ref:
                        # if this is the affected component
                        if ref == each_bomref["ref"]:
                            # we found the affected bom-ref, so get PURL
                            purl = each_component.get("purl")
                            if purl:
                                purl = urllib.parse.unquote(purl)
                                affected_package_urls.append(purl)

                            # get package path
                            pkg_path = getPropertyValueFromKey(each_component, "amazon:inspector:sbom_scanner:path")
                            if pkg_path:
                                affected_package_paths.append(pkg_path)

        # combine all affected package urls into one string,
        # using a semicolon as delimiter, so this can
        # fit in one CSV cell.
        purl_str = ";".join(affected_package_urls)
        if purl_str == "":
            purl_str = "null"
        vuln_obj.installed_ver = purl_str

        path_str = ";".join(affected_package_paths)
        if path_str == "":
            path_str = "null"
        vuln_obj.pkg_path = path_str

        # get fixed package
        fixed_versions = []
        props = v.get("properties")
        if props:
            for each_prop in props:
                prop_name = each_prop.get("name")
                if prop_name:
                    if "amazon:inspector:sbom_scanner:fixed_version:comp-" in prop_name:
                        fixed_version = each_prop.get("value")
                        if fixed_version:
                            fixed_versions.append(fixed_version)
                    else:
                        continue

        fixed_str = ";".join(fixed_versions)
        if fixed_str == "":
            fixed_str = "null"
        vuln_obj.fixed_ver = fixed_str

        # get exploit available
        exploit_available = getPropertyValueFromKey(v, "amazon:inspector:sbom_scanner:exploit_available")
        if exploit_available:
            vuln_obj.exploit_available = exploit_available

        # get exploit last seen
        exploit_last_seen = getPropertyValueFromKey(v, "amazon:inspector:sbom_scanner:exploit_last_seen_in_public")
        if exploit_last_seen:
            vuln_obj.exploit_last_seen = exploit_last_seen

        # get CWEs
        cwe_list = []
        cwes = v.get("cwes")
        if cwes:
            for each_cwe in cwes:
                s = f"CWE-{each_cwe}"
                cwe_list.append(s)

        if len(cwe_list) > 0:
            cwe_str = ";".join(cwe_list)
            vuln_obj.cwes = cwe_str

        vuln_list.append(vuln_obj)

    return vuln_list


def getPropertyValueFromKey(vuln_json, key):
    """
    extracts cycloneDX properties from Inspector
    ScanSbom components
    :param vuln_json: the component from which you would like to extract a property value
    :param key: the key to the property
    :return: the value from the component's property key
    """
    props = vuln_json.get("properties")
    if props:
        for each_prop in props:
            name = each_prop.get("name")
            if name:
                if key == name:
                    value = each_prop.get("value")
                    if value:
                        return value
    return None


def add_ratings(ratings, vulnerability):
    if ratings is None:
        return

    rating = get_cvss_rating(ratings, vulnerability)
    vulnerability.severity = rating.severity
    vulnerability.cvss_score = rating.cvss_score

    epss_score = get_epss_score(ratings)
    if epss_score:
        vulnerability.epss_score = epss_score


def get_cvss_rating(ratings, vulnerability) -> CvssRating:
    rating_provider_priority = [
        'NVD',
        'MITRE',
        'AMAZON_INSPECTOR'
    ]
    for provider in rating_provider_priority:
        for rating in ratings:
            if rating['source']['name'] != provider:
                continue

            severity = rating["severity"]
            cvss_score = rating["score"] if rating['method'] == 'CVSSv31' else "null"
            if severity and cvss_score:
                return CvssRating(severity=severity, cvss_score=cvss_score)

    logging.info(f"No CVSS rating is provided for {vulnerability.vuln_id}")
    return CvssRating()


def get_epss_score(ratings):
    for rating in ratings:
        source = rating.get("source")
        if not source:
            continue

        if source["name"] == "EPSS":
            epss_score = rating["score"]
            if epss_score:
                return epss_score
    return None


def to_csv(vulns,
           artifact_name="null",
           artifact_type="null",
           artifact_hash="null",
           build_id="null",
           criticals="null",
           highs="null",
           mediums="null",
           lows="null",
           others="null"):
    csv_buffer = StringIO()
    csv_writer = csv.writer(csv_buffer, quoting=csv.QUOTE_ALL)

    # insert hash rows; these are like properties for CSV
    artifact_info = [f"#artifact_name:{artifact_name}",
                     f"artifact_type:{artifact_type}",
                     f"artifact_hash:{artifact_hash}",
                     f"build_id:{build_id}",
                     ]
    csv_writer.writerow(artifact_info)

    vuln_summary = [f"#critical_vulnerabilities:{criticals}",
                    f"high_vulnerabilities:{highs}",
                    f"medium_vulnerabilities:{mediums}",
                    f"low_vulnerabilities:{lows}",
                    f"other_vulnerabilities:{others}",
                    ]
    csv_writer.writerow(vuln_summary)

    # write the header into the CSV
    header = ["ID", "Severity", "CVSS",
              "Installed Package", "Fixed Package",
              "Path", "EPSS", "Exploit Available",
              "Exploit Last Seen", "CWEs"]
    csv_writer.writerow(header)

    # write each vuln into a CSV
    if vulns:
        for v in vulns:
            # if package vuln
            row = [v.vuln_id, v.severity, v.cvss_score,
                   v.installed_ver, v.fixed_ver,
                   v.pkg_path, v.epss_score, v.exploit_available,
                   v.exploit_last_seen, v.cwes
                   ]
            csv_writer.writerow(row)

    csv_str = csv_buffer.getvalue()
    csv_buffer.close()

    return csv_str


def to_markdown(vulns,
                artifact_name="null",
                artifact_type="null",
                artifact_hash="null",
                build_id="null",
                criticals="null",
                highs="null",
                mediums="null",
                lows="null",
                others="null"):
    if artifact_type == "directory":
        artifact_type = "repository"

    # create header info
    markdown = f"# Amazon Inspector Scan Results\n"

    if not artifact_name == "./":
        markdown += f"Artifact Name: {artifact_name}\n\n"

    markdown += f"Artifact Type: {artifact_type}\n\n"
    if artifact_hash != "null":
        markdown += f"Artifact Hash: {artifact_hash}\n\n"
    if build_id != "null":
        markdown += f"Build ID: {build_id}\n\n"

    # create summary table
    markdown += "## Vulnerability Counts by Severity\n\n"
    markdown += "| Severity | Count |\n"
    markdown += "|----------|-------|\n"
    markdown += f"| Critical | {criticals}|\n"
    markdown += f"| High     | {highs}|\n"
    markdown += f"| Medium   | {mediums}|\n"
    markdown += f"| Low      | {lows}|\n"
    markdown += f"| Other    | {others}|\n"
    markdown += "\n\n"

    if not vulns:
        markdown += ":green_circle: Your artifact was scanned with Amazon Inspector and no vulnerabilities were detected."
        markdown += "\n\n"
        return markdown

    # create vulnerability details table
    markdown += "## Vulnerability Findings\n\n"
    markdown += "| ID | Severity | [CVSS](https://www.first.org/cvss/) | Installed Package ([PURL](https://github.com/package-url/purl-spec/tree/master?tab=readme-ov-file#purl)) | Fixed Package | Path | [EPSS](https://www.first.org/epss/) | Exploit Available | Exploit Last Seen | CWEs |\n"
    markdown += "|----------|-------|-------|-------|-------|-------|-------|-------|-------|-------|\n"

    # sort vulns by CVSS score
    vulns = sort_vulns(vulns)

    # append each row to the vulnerability details table
    for v in vulns:
        markdown += f"|{v.vuln_id}| {clean_null(v.severity)} | {clean_null(v.cvss_score)} | {merge_cell(v.installed_ver)} | {merge_cell(v.fixed_ver)} | {merge_cell(clean_null(v.pkg_path))} | {clean_null(v.epss_score)} | {clean_null(v.exploit_available)} | {clean_null(v.exploit_last_seen)} | {(merge_cell(clean_null(v.cwes)))} | \n"

    markdown += "\n\n"
    return markdown


def merge_cell(a_string: str):
    """
    This function expects a string of data
    that is intended to be placed in a markdown
    table. The provided data may include multiple
    elements in a string, such as multiple PURLs
    separated with a semi-colon character ';'.
    This function splits the provided string
    so that multiple elements can fit in one
    cell in a markdown table.
    """

    # return early on empty string
    if a_string == "":
        return ""

    # we may have multiple PURLs for a single CVE,
    # so split purls into a list we can iterate on
    original_list = a_string.split(";")
    seen = set()
    unique_list = []

    # make each PURL list unique while preserving ordering
    # so that our pkg versions line up with the correct pkg names
    for item in original_list:
        if item not in seen:
            seen.add(item)
            unique_list.append(item)

    unique_formatted = []
    for each in unique_list:
        # make each element preformatted text,
        # otherwise the markdown report renders
        # with malformed characters on GitHub
        each = f"`{each}`"
        unique_formatted.append(each)

    # separate multiple elements in cell with HTML break characters
    merged_cell = '<br><br>'.join(unique_formatted)
    return merged_cell


def clean_null(a_string: str):
    if a_string == "null":
        return ""
    else:
        return a_string


def sort_vulns(vulns):
    for each in vulns:
        if each.cvss_score == "null":
            each.cvss_score = 0
    sorted_vulns = sorted(vulns, key=lambda obj: float(obj.cvss_score), reverse=True)

    for each in sorted_vulns:
        if each.cvss_score == 0:
            each.cvss_score = ""
    return sorted_vulns


def post_github_step_summary(markdown):
    step_summary_path = "/tmp/inspector.md"
    if os.getenv('GITHUB_ACTIONS'):
        step_summary_path = os.environ["GITHUB_STEP_SUMMARY"]

    try:
        with open(step_summary_path, "a") as f:
            f.write(markdown)
    except Exception as e:
        logging.error(e)
        return


def fatal_assert(expr: bool, msg: str):
    if not expr:
        logging.error(msg)
        exit(1)


def get_pkg_vulns(inspector_scan_vulns: dict):
    pkg_vulns = []

    for vuln in inspector_scan_vulns:
        # [!] at time of writing, we only have two vuln types:
        # 1. pkg vulns, 2. Dockerfile vulns
        # Therefore, we skip all Dockerfile vulns, leaving
        # only pkg vulns.
        if "IN-DOCKER" in vuln["id"]:
            continue
        pkg_vulns.append(vuln)

    return pkg_vulns
