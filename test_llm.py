import os
import sys

from dotenv import load_dotenv

try:
    from openai import OpenAI
except Exception as exc:  # pragma: no cover
    print(f"FAIL: openai package import error: {exc}")
    sys.exit(1)


def main() -> int:
    load_dotenv()

    api_key = os.getenv("OPENAI_API_KEY")
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    if not api_key:
        print("FAIL: OPENAI_API_KEY is not set in environment or .env")
        return 1

    print(f"INFO: using model={model}")
    client = OpenAI(api_key=api_key)

    try:
        response = client.chat.completions.create(
            model=model,
            temperature=0,
            messages=[
                {"role": "system", "content": "You are concise."},
                {"role": "user", "content": "Reply with exactly: LLM_OK"},
            ],
        )
        text = (response.choices[0].message.content or "").strip()
    except Exception as exc:
        print(f"FAIL: OpenAI API call failed: {exc}")
        return 1

    print(f"INFO: raw_response={text}")
    if "LLM_OK" in text:
        print("PASS: OpenAI LLM call succeeded")
        return 0

    print("FAIL: Unexpected model response")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
