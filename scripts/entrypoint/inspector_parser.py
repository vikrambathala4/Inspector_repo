import json
import logging
import sys
import urllib.parse
from tabulate import tabulate


class InspectorFinding:
    def __init__(self):
        self.package_names = []
        self.vulnerability_id = ""
        self.cvss_severity = ""
        self.cvss_score = ""
        self.installed_versions = []
        self.fixed_versions = []
        self.analysis_state = ""
        self.advisories = ""


def print_summarized_findings_as_table(summarized_findings):
    sorted_findings = sorted(summarized_findings, key=lambda obj: obj.cvss_score, reverse=True)

    header = ["Vulnerability ID", "CVSSv3 Severity", "CVSSv3 Score", "Affected Packages", "Installed Versions"]
    table = []
    for finding in sorted_findings:
        name_cell = "\n".join(finding.package_names)
        installed_ver_cell = "\n".join(finding.installed_versions)

        row = [finding.vulnerability_id, finding.cvss_severity, finding.cvss_score, name_cell, installed_ver_cell]
        table.append(row)
    print(tabulate(table, headers=header, stralign="left", numalign="left"))
    return


def print_summarized_findings(summarized_findings):
    sorted_findings = sorted(summarized_findings, key=lambda obj: obj.cvss_score, reverse=True)
    for finding in sorted_findings:
        print(f"Vulnerability ID: {finding.vulnerability_id}")
        print(f"CVSSv3 Severity: {finding.cvss_severity}")
        print(f"CVSSv3 Score: {finding.cvss_score}")
        print(f"Analysis State: {finding.analysis_state}")
        print(f"Affected Packages (Name, Installed Version, Fixed Version):")
        pkg_table = []
        padding = "    "
        for pkg in finding.package_names:
            row = [padding, pkg, "1.1.1", "1.2.3"]
            pkg_table.append(row)
        print(tabulate(pkg_table, tablefmt="plain"))
        # print(f"Affected Versions: {finding.installed_versions}")
        # print(f"Fixed Versions: {finding.fixed_versions}")
        print(f"Advisories:")
        i = 1
        for adv in finding.advisories:
            print(f"  {i}. {adv}")
            i += 1
        print("................................................................")


def get_summarized_findings(inspector_scan_json):
    findings = get_findings(inspector_scan_json)
    vulnerabilities = get_vulnerabilities(findings)
    if vulnerabilities is None:
        return None

    summarized_findings = []
    for vuln in vulnerabilities:
        finding = InspectorFinding()
        finding.cvss_severity, finding.cvss_score = get_cvss_severity(vuln)
        if finding.cvss_severity == None:
            finding.cvss_severity = "unknown"

        finding.vulnerability_id = get_vuln_id(vuln)
        finding.analysis_state = get_analysis_state(vuln)

        advisories = get_advisories(vuln)
        if advisories is not None:
            finding.advisories = advisories

        affected_components = get_affected_components(vuln)
        for each_comp in affected_components:
            component = get_component(findings, each_comp)
            name, ver = get_component_name_version(component)
            finding.package_names.append(name)
            finding.installed_versions.append(ver)

            fixed_ver = get_fixed_version(vuln, each_comp)
            if fixed_ver is None or fixed_ver == "unknown":
                fixed_ver = ""
            finding.fixed_versions.append(fixed_ver)

            summarized_findings.append(finding)

    return summarized_findings


def get_findings(inspector_scan_json):
    """
    given a JSON formatted Inspector Scan-Sbom response,
    extract all keys under the root key, "sbom" so that
    we can begin parsing components and vulnerabilities.
    Returns a dict on success, or None on failure.
    """
    findings = inspector_scan_json.get("sbom")
    if findings is None:
        logging.warning("expected 'sbom' json object but it was not found")
        return None
    return findings


def get_vulnerabilities(findings_json):
    """
    This function takes the output of 'inspector_parser.get_findings'
    as its input. Given this input, it extracts the CycloneDX
    vulnerabilities array, and returns it to the caller.
    Returns None if vulnerabilities array is not present.
    """
    vulnerabilities = findings_json.get("vulnerabilities")
    if vulnerabilities is None:
        return None
    return vulnerabilities


def get_cvss_severity(vuln_json):
    ratings = vuln_json.get("ratings")
    if ratings is None:
        return None, 0

    severity = ""
    score = 0
    for rating in ratings:
        method = rating.get("method")
        if method is None or method != "CVSSv31":
            continue

        severity = rating.get("severity")
        if severity is None:
            severity = "unknown"

        score = rating.get("score")
        if score is None:
            score = 0

    return severity, score


def get_vuln_id(vuln_json):
    vuln_id = vuln_json.get("id")
    if vuln_id is None:
        logging.warning("expected value from key 'id' but received none")
        sys.exit(1)
    return vuln_id


def get_analysis_state(vuln_json):
    analysis = vuln_json.get("analysis")
    if analysis is None:
        logging.warning("expected json object from key 'analysis' but received none")
        sys.exit(1)

    analysis_state = analysis.get("state")
    if analysis_state is None:
        logging.warning("expected value from key 'state' but received none")
        sys.exit(1)

    return analysis_state


def get_advisories(vuln_json):
    advisories = vuln_json.get("advisories")
    if advisories is None:
        return None

    advisory_urls = []
    for adv in advisories:
        url = adv["url"]
        advisory_urls.append(url)
    return advisory_urls


def get_affected_components(vuln_json):
    affects = vuln_json.get("affects")
    if affects is None:
        logging.warning("expected value from key 'affects' but received none")
        sys.exit(1)

    affected_components = []
    for each in affects:
        component = each.get("ref")
        if component is None:
            logging.warning("expected value from key 'ref' but received none")
            sys.exit(1)
        affected_components.append(component)

    return affected_components


def get_component(findings_json, bom_ref):
    components = findings_json.get("components")
    if components is None:
        logging.warning("expected value from key 'components' but received none")
        sys.exit(1)

    for comp in components:
        ref = comp.get("bom-ref")
        if ref is None:
            logging.warning("expected value from key 'bom-ref' but received none")
            sys.exit(1)

        if bom_ref == ref:
            return comp


def get_component_name_version(comp_json):
    name = comp_json.get("name")
    if name is None:
        logging.warning("expected value from key 'name' but received none")
        sys.exit(1)
    name = urllib.parse.unquote(name)
    version = comp_json.get("version")
    if version == "":
        version = "unknown"
    version = urllib.parse.unquote(version)
    return name, version


def get_fixed_version(vuln_json, bom_ref):
    properties = vuln_json.get("properties")
    if properties is None:
        return "unknown"

    prop_namespace = "amazon:inspector:sbom_scanner:fixed_version:"
    for prop in properties:
        name = prop.get("name")
        if not prop_namespace in name:
            continue

        if not bom_ref in name:
            continue

        fixed_version = prop.get("value")
        if fixed_version == "" or fixed_version is None:
            return "unknown"
        fixed_version = urllib.parse.unquote(fixed_version)
        return fixed_version
