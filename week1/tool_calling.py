import ast
import json
import os
from collections.abc import Callable

from dotenv import load_dotenv
from ollama import chat

load_dotenv()

NUM_RUNS_TIMES = 3


# ==========================
# Tool implementation (the "executor")
# ==========================
def _annotation_to_str(annotation: ast.AST | None) -> str:
    if annotation is None:
        return "None"
    try:
        return ast.unparse(annotation)  # type: ignore[attr-defined]
    except Exception:
        # Fallback best-effort
        if isinstance(annotation, ast.Name):
            return annotation.id
        return type(annotation).__name__


def _list_function_return_types(file_path: str) -> list[tuple[str, str]]:
    with open(file_path, encoding="utf-8") as f:
        source = f.read()
    tree = ast.parse(source)
    results: list[tuple[str, str]] = []
    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            return_str = _annotation_to_str(node.returns)
            results.append((node.name, return_str))
    # Sort for stable output
    results.sort(key=lambda x: x[0])
    return results


def output_every_func_return_type(file_path: str = None) -> str:
    """Tool: Return a newline-delimited list of "name: return_type" for each top-level function."""
    path = file_path or __file__
    if not os.path.isabs(path):
        # Try file relative to this script if not absolute
        candidate = os.path.join(os.path.dirname(__file__), path)
        if os.path.exists(candidate):
            path = candidate
    pairs = _list_function_return_types(path)
    return "\n".join(f"{name}: {ret}" for name, ret in pairs)


# Sample functions to ensure there is something to analyze
def add(a: int, b: int) -> int:
    return a + b


def greet(name: str) -> str:
    return f"Hello, {name}!"


# Tool registry for dynamic execution by name
TOOL_REGISTRY: dict[str, Callable[..., str]] = {
    "output_every_func_return_type": output_every_func_return_type,
}

# ==========================
# Prompt scaffolding
# ==========================

# TODO: Fill this in!
YOUR_SYSTEM_PROMPT = f"""You are a helpful assistant that can call tools to help you solve problems. You will be given a problem and you will need to call the appropriate tool to solve it. You will then return the result of the tool call. Available tools: {TOOL_REGISTRY.keys()}. If you need to call a tool return the tool call in JSON format: {{"tool": <tool_name>, "args": {{<tool_args>}}}}. You will only return the JSON object, no other text or explanation."""


def resolve_path(p: str) -> str:
    if os.path.isabs(p):
        return p
    here = os.path.dirname(__file__)
    c1 = os.path.join(here, p)
    if os.path.exists(c1):
        return c1
    # Try sibling of project root if needed
    return p


def extract_tool_call(text: str) -> dict[str, object]:
    """Parse a single JSON object from the model output."""
    print("DEBUG: extract_tool_call", text)
    text = text.strip()
    # Some models wrap JSON in code fences; attempt to strip
    if text.startswith("```") and text.endswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json\n"):
            text = text[5:]
    try:
        obj = json.loads(text)
        return obj
    except json.JSONDecodeError:
        raise ValueError("Model did not return valid JSON for the tool call")


def run_model_for_tool_call(system_prompt: str) -> dict[str, object]:
    response = chat(
        model="llama3.1:8b",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "Call the tool now."},
        ],
        options={"temperature": 0.3},
    )
    content = response.message.content
    return extract_tool_call(content)


def execute_tool_call(call: dict[str, object]) -> str:
    name = call.get("tool")
    if not isinstance(name, str):
        raise ValueError("Tool call JSON missing 'tool' string")
    func = TOOL_REGISTRY.get(name)
    if func is None:
        raise ValueError(f"Unknown tool: {name}")
    args = call.get("args", {})
    if not isinstance(args, dict):
        raise ValueError("Tool call JSON 'args' must be an object")

    # Best-effort path resolution if a file_path arg is present
    if "file_path" in args and isinstance(args["file_path"], str):
        args["file_path"] = (
            resolve_path(args["file_path"]) if str(args["file_path"]) != "" else __file__
        )
    elif "file_path" not in args:
        # Provide default for tools expecting file_path
        args["file_path"] = __file__

    return func(**args)


def compute_expected_output() -> str:
    # Ground-truth expected output based on the actual file contents
    return output_every_func_return_type(__file__)


def test_your_prompt(system_prompt: str) -> bool:
    """Run once: require the model to produce a valid tool call; compare tool output to expected."""
    expected = compute_expected_output()
    print("DEBUG: expected", expected)
    for _ in range(NUM_RUNS_TIMES):
        try:
            call = run_model_for_tool_call(system_prompt)
        except Exception as exc:
            print(f"Failed to parse tool call: {exc}")
            continue
        print("DEBUG: call", call)
        try:
            actual = execute_tool_call(call)
        except Exception as exc:
            print(f"Tool execution failed: {exc}")
            continue
        if actual.strip() == expected.strip():
            print(f"Generated tool call: {call}")
            print(f"Generated output: {actual}")
            print("SUCCESS")
            return True
        else:
            print("Expected output:\n" + expected)
            print("Actual output:\n" + actual)
    return False


if __name__ == "__main__":
    test_your_prompt(YOUR_SYSTEM_PROMPT)
