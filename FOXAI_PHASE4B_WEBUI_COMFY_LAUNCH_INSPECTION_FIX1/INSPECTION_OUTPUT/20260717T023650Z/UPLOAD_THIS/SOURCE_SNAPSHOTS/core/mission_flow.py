class MissionFlow:
    """
    Read-only mission flow descriptions for FOXAI.

    This is the first version of a structured Workshop blueprint.
    It explains how different request types move through the system.
    """

    FLOWS = {
        "chat": [
            ("Operator", "Types a normal conversational request."),
            ("Mission Control", "Logs the request and announces analysis."),
            ("Director", "Classifies the request as Conversation."),
            ("Brainstem", "Marks the Workshop busy."),
            ("ChatAgent / Agent Fox", "Adds the user message and launches neural response generation."),
            ("Neural Engine", "Processes the chat request through llama-server."),
            ("Mission Control", "Displays the response and completes the mission."),
            ("Mission Archive", "Saves the conversation log."),
        ],
        "red canvas": [
            ("Operator", "Submits an image-style or visual prompt."),
            ("Mission Control", "Announces Director analysis."),
            ("Director", "Classifies the request as Creative."),
            ("Brainstem", "Marks the Workshop busy and prevents overlapping missions."),
            ("RedCanvasAgent", "Routes the request into Red Canvas."),
            ("PromptSmith", "Enhances the positive and negative prompts."),
            ("Comfy Bridge", "Submits workflow_api.json to ComfyUI."),
            ("ComfyUI", "Renders the image."),
            ("Red Canvas Output", "Downloads and saves the generated image."),
            ("Preview Panel", "Displays the latest generated image."),
            ("Mission Archive", "Saves the creative mission log."),
        ],
        "iron library": [
            ("Operator", "Requests a local library search."),
            ("Mission Control", "Logs the request and announces analysis."),
            ("Director", "Classifies the request as Research."),
            ("Brainstem", "Marks the Workshop busy."),
            ("LibraryAgent", "Routes the query into Iron Library."),
            ("Iron Library", "Searches indexed local documents and project files."),
            ("Mission Control", "Displays search results."),
            ("Mission Archive", "Saves the research mission log."),
        ],
        "engineer": [
            ("Operator", "Requests code, architecture, or project analysis."),
            ("Mission Control", "Logs the request and announces analysis."),
            ("Director", "Classifies the request as Engineering."),
            ("Brainstem", "Marks the Workshop busy."),
            ("EngineerAgent", "Determines the requested analysis type."),
            ("ProjectIndex", "Maps files, classes, functions, and imports."),
            ("DependencyGraph", "Maps import relationships when needed."),
            ("RuntimeGraph", "Maps object references and call sites when needed."),
            ("Engineer", "Reports findings in read-only mode."),
            ("Mission Archive", "Saves the engineering mission log."),
        ],
        "diagnostics": [
            ("Operator", "Opens Diagnostics or sends report to Mission Control."),
            ("Diagnostics", "Runs Workshop health inspection."),
            ("Brainstem", "Reports current state, active mission, and neural server status."),
            ("Hardware Monitor", "Reports CPU, RAM, disk, and uptime."),
            ("Creative Systems", "Checks ComfyUI, workflow, checkpoints, and output folder."),
            ("Iron Library", "Checks document index readiness."),
            ("Workshop Advisor", "Recommends stable model, threads, context, and reply tokens."),
            ("Mission Control", "Displays the report if requested."),
        ],
    }

    def list_flows(self):
        lines = [
            "MISSION FLOW BLUEPRINT",
            "",
            "Known mission flows:",
            "",
        ]

        for name in sorted(self.FLOWS):
            lines.append(f"• {name}")

        lines.extend([
            "",
            "Ask examples:",
            "• Engineer, trace Red Canvas mission",
            "• Engineer, trace chat mission",
            "• Engineer, trace Iron Library mission",
            "• Engineer, trace Engineer mission",
            "",
            "Safety Status:",
            "Read-only. No files were modified.",
        ])

        return "\n".join(lines)

    def trace(self, query):
        flow_name = self.extract_flow(query)

        if flow_name not in self.FLOWS:
            return self.list_flows()

        lines = [
            "MISSION FLOW TRACE",
            "",
            f"Flow: {flow_name.title()}",
            "",
        ]

        steps = self.FLOWS[flow_name]

        for i, (stage, description) in enumerate(steps, start=1):
            lines.append(f"{i}. {stage}")
            lines.append(f"   {description}")
            if i < len(steps):
                lines.append("   ↓")

        lines.extend([
            "",
            "Interpretation:",
            self.interpret(flow_name),
            "",
            "Safety Status:",
            "Read-only. No files were modified.",
        ])

        return "\n".join(lines)

    def extract_flow(self, query):
        lowered = query.lower()

        aliases = {
            "red canvas": "red canvas",
            "image": "red canvas",
            "render": "red canvas",
            "creative": "red canvas",
            "chat": "chat",
            "conversation": "chat",
            "agent fox": "chat",
            "iron library": "iron library",
            "library": "iron library",
            "research": "iron library",
            "engineer": "engineer",
            "engineering": "engineer",
            "diagnostics": "diagnostics",
            "diagnostic": "diagnostics",
            "health": "diagnostics",
        }

        for key, value in aliases.items():
            if key in lowered:
                return value

        return ""

    def interpret(self, flow_name):
        interpretations = {
            "chat": "Chat missions depend primarily on Director routing, Brainstem state, ChatAgent, and the local neural engine.",
            "red canvas": "Red Canvas missions are the most complex path because they involve Director routing, PromptSmith, Comfy Bridge, ComfyUI, output retrieval, and UI preview.",
            "iron library": "Iron Library missions are read-only research operations over local indexed files.",
            "engineer": "Engineer missions are read-only architecture and code analysis operations using ProjectIndex, DependencyGraph, and RuntimeGraph.",
            "diagnostics": "Diagnostics missions inspect Workshop health and provide facts used by Mission Control, Engineer, and future Settings recommendations.",
        }

        return interpretations.get(flow_name, "No interpretation available yet.")
