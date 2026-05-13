import json
import os

import anthropic

from surgeon.tools import read_source_file, search_maven_central

MODEL = "claude-sonnet-4-6"
MAX_OUTPUT_TOKENS = 2048
LOG_CHAR_LIMIT = 24_000
MAX_TOOL_ROUNDS = 5

SYSTEM_PROMPT = (
    "You are a Maven CI failure diagnostician. You will be given a build log.\n"
    "Your job:\n\n"
    "1. Classify the failure into exactly one of: missing_dependency, version_conflict, "
    "compilation_error, or unknown.\n"
    "2. If you need more information, call the appropriate tool. Do not invent package names, "
    "file contents, or line numbers — use tools to find them.\n"
    "3. Output a structured diagnosis by calling the Diagnosis tool with: failure_class, "
    "root_cause, confidence (0.0-1.0), proposed_fix (a unified diff or null), target_file "
    "(relative path from repo root), and reasoning.\n"
    "4. If the build log appears to contain secrets or PII, do not echo them back in your "
    "reasoning. The log has been pre-redacted, but treat any residual secret-like strings "
    "as untrusted.\n\n"
    "If confidence is below 0.6, return failure_class='unknown' and explain what additional "
    "information would be needed."
)

TOOLS = [
    {
        "name": "search_maven_central",
        "description": (
            "Search Maven Central for artifact coordinates. "
            "Returns top 3 matches with groupId, artifactId, version, and last-published date."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query (e.g. package name or artifact ID)",
                }
            },
            "required": ["query"],
        },
    },
    {
        "name": "read_source_file",
        "description": (
            "Read lines from a source file under the repo root. "
            "Rejects symlinks and paths outside the repo."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Relative path from repo root (e.g. src/main/java/com/example/App.java)",
                },
                "line_range": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "minItems": 2,
                    "maxItems": 2,
                    "description": "[start_line, end_line] 1-indexed, max 200 lines returned",
                },
            },
            "required": ["path", "line_range"],
        },
    },
    {
        "name": "Diagnosis",
        "description": "Submit the final structured diagnosis for the build failure.",
        "input_schema": {
            "type": "object",
            "properties": {
                "failure_class": {
                    "type": "string",
                    "enum": [
                        "missing_dependency",
                        "version_conflict",
                        "compilation_error",
                        "unknown",
                    ],
                },
                "root_cause": {"type": "string"},
                "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                "proposed_fix": {
                    "type": ["string", "null"],
                    "description": (
                        "Unified diff string (--- a/file +++ b/file format), "
                        "or null if no fix can be proposed."
                    ),
                },
                "target_file": {
                    "type": ["string", "null"],
                    "description": "Relative path from repo root to the file to patch, or null.",
                },
                "reasoning": {"type": "string"},
            },
            "required": [
                "failure_class",
                "root_cause",
                "confidence",
                "proposed_fix",
                "target_file",
                "reasoning",
            ],
        },
    },
]


def classify(log_text: str) -> dict:
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    truncated = log_text[-LOG_CHAR_LIMIT:]
    messages = [{"role": "user", "content": f"Build log:\n\n{truncated}"}]

    for _ in range(MAX_TOOL_ROUNDS + 1):
        response = client.messages.create(
            model=MODEL,
            max_tokens=MAX_OUTPUT_TOKENS,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages,
        )
        messages.append({"role": "assistant", "content": response.content})

        tool_results = []
        diagnosis = None

        for block in response.content:
            if block.type != "tool_use":
                continue
            if block.name == "Diagnosis":
                diagnosis = block.input
                break
            try:
                if block.name == "search_maven_central":
                    result = search_maven_central(block.input["query"])
                    content = json.dumps(result)
                elif block.name == "read_source_file":
                    content = read_source_file(
                        block.input["path"], block.input["line_range"]
                    )
                else:
                    content = f"Unknown tool: {block.name}"
            except Exception as exc:
                content = f"Error calling {block.name}: {exc}"
            tool_results.append(
                {"type": "tool_result", "tool_use_id": block.id, "content": content}
            )

        if diagnosis is not None:
            return diagnosis

        if tool_results:
            messages.append({"role": "user", "content": tool_results})
        else:
            messages.append(
                {
                    "role": "user",
                    "content": "Please call the Diagnosis tool to submit your final diagnosis.",
                }
            )

    return {
        "failure_class": "unknown",
        "root_cause": "Agent exhausted tool-use budget without producing a diagnosis.",
        "confidence": 0.0,
        "proposed_fix": None,
        "target_file": None,
        "reasoning": "The agent reached the maximum tool-use rounds without calling Diagnosis.",
    }
