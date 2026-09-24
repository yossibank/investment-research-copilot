import anthropic

from .agent import run_agent


def main() -> None:
    question = input("質問を入力してください: ")

    try:
        answer = run_agent(question)

    except anthropic.APITimeoutError:
        print("Claude API request timed out.")
        return

    except anthropic.RateLimitError:
        print("Claude API rate limit exceeded.")
        return

    except anthropic.APIConnectionError:
        print("Could not connect to Claude API.")
        return

    except anthropic.APIStatusError as error:
        print("Claude API error:", error.status_code)
        return

    except ValueError as error:
        print("Invalid input:", error)
        return

    except RuntimeError as error:
        print("Agent error:", error)
        return

    print("\n=== Answer ===")

    print(answer)


if __name__ == "__main__":
    main()
