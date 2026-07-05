from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict


@dataclass
class ProjectCharter:
    """
    Project Charter RC1

    A structured agreement for a project before code is forged.
    It is advisory and does not execute or modify files.
    """

    project_name: str
    mission_type: str
    objective: str
    in_scope: List[str] = field(default_factory=list)
    out_of_scope: List[str] = field(default_factory=list)
    success_criteria: List[str] = field(default_factory=list)
    departments: List[str] = field(default_factory=list)
    risks: List[str] = field(default_factory=list)
    milestones: List[str] = field(default_factory=list)
    artifacts: List[str] = field(default_factory=list)
    approval_status: str = "Pending"
    created_at: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))

    def to_dict(self) -> Dict:
        return {
            "project_name": self.project_name,
            "mission_type": self.mission_type,
            "objective": self.objective,
            "in_scope": self.in_scope,
            "out_of_scope": self.out_of_scope,
            "success_criteria": self.success_criteria,
            "departments": self.departments,
            "risks": self.risks,
            "milestones": self.milestones,
            "artifacts": self.artifacts,
            "approval_status": self.approval_status,
            "created_at": self.created_at,
        }

    def format(self) -> str:
        lines = [
            "PROJECT CHARTER",
            "",
            f"Project: {self.project_name}",
            f"Mission Type: {self.mission_type}",
            f"Created: {self.created_at}",
            f"Approval Status: {self.approval_status}",
            "",
            "Objective:",
            self.objective,
            "",
            "In Scope:",
        ]

        lines.extend([f"• {item}" for item in self.in_scope] or ["• None listed"])

        lines.extend([
            "",
            "Out of Scope:",
        ])

        lines.extend([f"• {item}" for item in self.out_of_scope] or ["• None listed"])

        lines.extend([
            "",
            "Success Criteria:",
        ])

        lines.extend([f"• {item}" for item in self.success_criteria] or ["• None listed"])

        lines.extend([
            "",
            "Departments Required:",
        ])

        lines.extend([f"• {item}" for item in self.departments] or ["• None listed"])

        lines.extend([
            "",
            "Risks:",
        ])

        lines.extend([f"• {item}" for item in self.risks] or ["• None listed"])

        lines.extend([
            "",
            "Milestones:",
        ])

        for index, item in enumerate(self.milestones, start=1):
            lines.append(f"{index}. {item}")

        if not self.milestones:
            lines.append("• None listed")

        lines.extend([
            "",
            "Likely Artifacts:",
        ])

        lines.extend([f"• {item}" for item in self.artifacts] or ["• None listed"])

        lines.extend([
            "",
            "Operator Approval:",
            "Required before files are written or modified.",
        ])

        return "\n".join(lines)


class ProjectCharterFactory:
    """
    Creates project charters from natural-language project descriptions.
    RC1 uses simple deterministic rules.
    """

    def create(self, mission: str) -> ProjectCharter:
        text = (mission or "").lower()

        if any(word in text for word in ["spider", "crawler", "crawl", "web pages", "web spider"]):
            return self.web_spider_charter(mission)

        if any(word in text for word in ["kayock", "identity", "profile", "forge red", "theme"]):
            return self.identity_charter(mission)

        if any(word in text for word in ["repair bay", "repair", "windows recovery"]):
            return self.repair_bay_charter(mission)

        return self.generic_feature_charter(mission)

    def web_spider_charter(self, mission: str) -> ProjectCharter:
        return ProjectCharter(
            project_name="Web Spider Toolkit",
            mission_type="Feature Development / Research Tool",
            objective=(
                "Build a polite, bounded web spider toolkit in Python and Java that can crawl allowed "
                "web pages, collect discovered links, filter target domains such as .com and .org, "
                "and write an index to a text file."
            ),
            in_scope=[
                "Python crawler implementation",
                "Java crawler implementation",
                "Seed URL input",
                "Depth limit",
                "Page count limit",
                "Request delay / rate limiting",
                "robots.txt awareness",
                "Domain suffix filtering such as .com and .org",
                "TXT index output",
                "Clear documentation and usage examples",
            ],
            out_of_scope=[
                "Bypassing login pages",
                "Ignoring robots.txt",
                "High-speed scraping",
                "Collecting private personal data",
                "Credential harvesting",
                "Distributed crawling",
                "Denial-of-service behavior",
            ],
            success_criteria=[
                "Crawler accepts seed URLs safely",
                "Crawler respects configured depth and page limits",
                "Crawler writes discovered URLs to a text file",
                "Crawler avoids duplicate URLs",
                "Crawler waits between requests",
                "Crawler can be stopped safely",
                "Both Python and Java versions produce comparable output",
                "Default settings are conservative",
            ],
            departments=[
                "Forge Master",
                "Engineer",
                "Decision Layer",
                "Confidence Engine",
                "Iron Library",
                "Diagnostics",
            ],
            risks=[
                "Accidental over-crawling",
                "Websites blocking requests",
                "Malformed URLs",
                "Infinite crawl loops",
                "Large output files",
                "Legal or ethical misuse if safety limits are removed",
            ],
            milestones=[
                "Requirements and safety boundaries",
                "Output format definition",
                "Python crawler prototype",
                "Java crawler prototype",
                "Robots.txt and rate-limit review",
                "Test against a safe local or allowed website",
                "Documentation",
                "Final confidence review",
            ],
            artifacts=[
                "web_spider_python.py",
                "WebSpider.java",
                "README_web_spider.md",
                "output/index.txt",
                "config/spider_config.json",
            ],
        )

    def identity_charter(self, mission: str) -> ProjectCharter:
        return ProjectCharter(
            project_name="Kayock's Forge Identity Profile",
            mission_type="Identity Profile",
            objective="Create a configurable Workshop identity without changing core Workshop logic.",
            in_scope=[
                "Workshop name",
                "Assistant name",
                "Theme colors",
                "Startup greeting",
                "Profile file",
                "Preview support",
            ],
            out_of_scope=[
                "Changing neural engine behavior",
                "Changing core mission routing",
                "Forking the codebase",
            ],
            success_criteria=[
                "Identity loads from profile data",
                "FOXAI profile remains available",
                "Kayock's Forge can be selected",
                "No core logic depends on hardcoded branding",
            ],
            departments=[
                "Forge Master",
                "Engineer",
                "Settings",
                "Soul Forge",
                "Diagnostics",
            ],
            risks=[
                "Hardcoded branding remains",
                "Theme changes leak into logic",
                "Profile path issues on cloned drives",
            ],
            milestones=[
                "Profile schema",
                "Identity loader",
                "Theme loader",
                "Settings integration",
                "Diagnostics validation",
            ],
            artifacts=[
                "core/identity.py",
                "Profiles/KayocksForge/identity.json",
                "ui/settings_panel.py",
            ],
        )

    def repair_bay_charter(self, mission: str) -> ProjectCharter:
        return ProjectCharter(
            project_name="Repair Bay",
            mission_type="Future Department",
            objective="Create a safe offline diagnostics and repair-assistance department for machines connected to the Workshop.",
            in_scope=[
                "Read-only system scans",
                "Log collection",
                "Drive health checks",
                "Windows repair guidance",
                "Report generation",
            ],
            out_of_scope=[
                "Automatic destructive repair",
                "Registry modification without approval",
                "Credential extraction",
                "Bypassing operating system security",
            ],
            success_criteria=[
                "Repair Bay can run read-only diagnostics",
                "Reports are understandable",
                "High-risk actions require explicit approval",
                "All actions are logged",
            ],
            departments=[
                "Forge Master",
                "Engineer",
                "Diagnostics",
                "Iron Library",
                "Confidence Engine",
            ],
            risks=[
                "Accidental destructive changes",
                "Misdiagnosis",
                "Hardware-dependent behavior",
            ],
            milestones=[
                "Safety model",
                "Read-only scanner",
                "Report format",
                "Guided repair suggestions",
                "Approval gates",
            ],
            artifacts=[
                "core/repair_bay.py",
                "core/repair_scanner.py",
                "ui/repair_bay_panel.py",
            ],
        )

    def generic_feature_charter(self, mission: str) -> ProjectCharter:
        return ProjectCharter(
            project_name="New Workshop Project",
            mission_type="Feature Development",
            objective=f"Define and plan the requested project: {mission}",
            in_scope=[
                "Requirements definition",
                "Architecture planning",
                "Safe implementation plan",
                "Diagnostics review",
            ],
            out_of_scope=[
                "Unapproved file modification",
                "Unsafe automation",
            ],
            success_criteria=[
                "Project goal is clearly defined",
                "Scope is agreed",
                "Risks are identified",
                "Operator approves before forging",
            ],
            departments=[
                "Forge Master",
                "Engineer",
                "Decision Layer",
                "Confidence Engine",
            ],
            risks=[
                "Unclear scope",
                "Feature creep",
                "Integration complexity",
            ],
            milestones=[
                "Requirements",
                "Blueprint",
                "Implementation plan",
                "Validation plan",
            ],
            artifacts=[
                "core/<new_module>.py",
                "ui/<optional_panel>.py",
                "README_<project>.md",
            ],
        )
