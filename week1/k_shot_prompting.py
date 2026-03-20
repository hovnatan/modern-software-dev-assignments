from dotenv import load_dotenv
from ollama import chat

load_dotenv()

NUM_RUNS_TIMES = 5

# TODO: Fill this in!
YOUR_SYSTEM_PROMPT = """You are a precise string reversal tool. To reverse a word:
1. First, list every character with its position (1-indexed), one per line.
2. Then read the characters from the LAST position to the FIRST.
3. Concatenate them into a single word.
4. Output ONLY that final reversed word on its own line — no numbering, no explanation.
5. Number of characters in the reversed word is the same as the number of characters in the original word.

Examples:

Input: "program"
p(1) r(2) o(3) g(4) r(5) a(6) m(7)
Reversed: m(7) a(6) r(5) g(4) o(3) r(2) p(1)
Output: margorp

Input: "httpstatus"
h(1) t(2) t(3) p(4) s(5) t(6) a(7) t(8) u(9) s(10)
Reversed: s(10) u(9) t(8) a(7) t(6) s(5) t(4) t(3) h(2) h(1)
Output: "sutatsptth"

IMPORTANT: After your reasoning, your very last line must be ONLY the reversed word and nothing else."""

USER_PROMPT = """
Reverse the order of letters in the following word. Only output the reversed word, no other text:

httpstatus
"""


EXPECTED_OUTPUT = "sutatsptth"


def test_your_prompt(system_prompt: str) -> bool:
    """Run the prompt up to NUM_RUNS_TIMES and return True if any output matches EXPECTED_OUTPUT.

    Prints "SUCCESS" when a match is found.
    """
    for idx in range(NUM_RUNS_TIMES):
        print(f"Running test {idx + 1} of {NUM_RUNS_TIMES}")
        response = chat(
            model="mistral-nemo:12b",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": USER_PROMPT},
            ],
            options={"temperature": 0.5},
        )
        output_text = response.message.content.strip()
        if output_text.strip() == EXPECTED_OUTPUT.strip():
            print("SUCCESS")
            return True
        else:
            print(f"Expected output: {EXPECTED_OUTPUT}")
            print(f"Actual output: {output_text}")
    return False


if __name__ == "__main__":
    test_your_prompt(YOUR_SYSTEM_PROMPT)
