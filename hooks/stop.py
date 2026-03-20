"""Stop hook — prompts user for manual session feedback fields.

Fires when Claude finishes responding. Returns a blocking prompt once per session
to collect satisfaction, category, and other manual fields.
"""

import json
import sys

from lib.config import get_config
from lib.state import read_state

SURVEY_PROMPT = """Before we wrap up, I'd like to capture a quick session survey for the AI Journey Logger.

Please answer these questions (I'll save your responses automatically):

1. **Model fit** — Was the model a good fit for this session? (right / overkill / underpowered)
2. **Category** — What best describes this session? (debugging / feature / refactor / brainstorming / learning)
3. **Mode** — Were you actively guiding or did Claude run autonomously? (guided / autonomous)
4. **Iterations** — How many attempts to get the result you wanted? (1-5)
5. **Iteration friction** — What caused extra iterations, if any? (bad prompt, misunderstanding, scope change, or n/a)
6. **Learned something** — Did Claude surface anything you didn't know? (brief answer or n/a)
7. **Satisfaction** — Overall satisfaction with this session? (1-5)
8. **Publish** — Publish this to your blog? (yes / no)
9. **Blog summary** — If publishing, one-paragraph summary (or skip)

After the user answers, write the results to the state file by running this exact command (fill in actual values):

```bash
python3 -c "
import json
from pathlib import Path
state_file = Path.home() / '.claude-journey' / '.session-state'
data = json.loads(state_file.read_text())
data['manual'] = {
    'model_fit': '<VALUE>',
    'category': '<VALUE>',
    'mode': '<VALUE>',
    'iterations_to_happy': <NUMBER>,
    'iteration_friction': '<VALUE>',
    'learned_something': '<VALUE>',
    'satisfaction': <NUMBER>,
    'publish': <true_or_false>,
    'blog_summary': '<VALUE>'
}
state_file.write_text(json.dumps(data))
print('Session survey saved.')
"
```"""


def run_stop(hook_input: dict) -> dict | None:
    """Check if manual fields need collection. Returns block response or None."""
    config = get_config()
    state = read_state(config.state_file)

    if state is None:
        return None

    if state.get("session_id") != hook_input.get("session_id"):
        return None

    if "manual" in state:
        return None

    return {
        "decision": "block",
        "reason": SURVEY_PROMPT,
    }


def main():
    try:
        hook_input = json.loads(sys.stdin.read())
        result = run_stop(hook_input)
        if result:
            print(json.dumps(result))
    except Exception as e:
        print(f"Stop hook error: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()
