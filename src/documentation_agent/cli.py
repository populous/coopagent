import argparse
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

from .workflow import DocumentationAgent


def main() -> None:
    """CLI entrypoint for the documentation agent."""
    load_dotenv()

    parser = argparse.ArgumentParser(
        description="사용자 요구에 기반해 요구사항 정의를 생성합니다",
    )
    parser.add_argument(
        "--task",
        type=str,
        default=None,
        help="만들고 싶은 애플리케이션이나 시스템에 대해 작성해 주세요 (생략 시 대화형 입력)",
    )
    parser.add_argument(
        "--k",
        type=int,
        default=5,
        help="생성할 페르소나 수를 설정해 주세요 (기본값: 5)",
    )
    args = parser.parse_args()
    task = args.task
    if not task:
        task = input("만들고 싶은 애플리케이션이나 시스템을 설명해 주세요: ").strip()
    if not task:
        parser.error("--task 값 또는 대화형 입력이 필요합니다.")

    llm = ChatOpenAI(model="gpt-4o", temperature=0.0)
    agent = DocumentationAgent(llm=llm, k=args.k)
    final_output = agent.run(user_request=task)
    print(final_output)


if __name__ == "__main__":
    main()
