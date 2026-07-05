from core.paths import PROMPTS

DEFAULT_AGENT_PROMPT = (
    "You are Agent Fox, the local cyber-operations assistant inside FoxAI. "
    "You help Eric clearly, honestly, and creatively. You are offline and local-only. "
    "Your style is adaptive: focused during work, playful during brainstorming, and calm/direct during stress."
)

def find_agents():
    if not PROMPTS.exists():
        return []
    return sorted(PROMPTS.glob("*.txt"))

def load_agent_prompt(agent_file=None):
    if agent_file and agent_file.exists():
        return agent_file.read_text(encoding="utf-8")
    return DEFAULT_AGENT_PROMPT
