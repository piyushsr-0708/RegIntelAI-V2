import json
import time
from pathlib import Path

from services.ollama_service import OllamaService
from services.context_builder import ContextBuilder


DOCUMENT_ID = "MD10191"


def print_separator():
    print("=" * 80)


def main():
    total_start = time.perf_counter()

    print_separator()
    print("RegulAI1 Mitra End-to-End Backend Test")
    print_separator()

    # ----------------------------------------------------------
    # STEP 1
    # ----------------------------------------------------------

    print("\n[1] Initializing Ollama Service...")

    ollama = OllamaService()

    # ----------------------------------------------------------
    # STEP 2
    # ----------------------------------------------------------

    print("\n[2] Checking Ollama Health...")

    health = ollama.check_health()

    print(json.dumps(health, indent=4))

    if health["status"] != "online":
        print("\nOllama is offline.")
        return

    print("\nInstalled Models:")

    for model in health["installed_models"]:
        print(f"  • {model}")

    # ----------------------------------------------------------
    # STEP 3
    # ----------------------------------------------------------

    print("\n[3] Building Retrieval Context...")

    project_root = Path(__file__).resolve().parent.parent

    builder = ContextBuilder(project_root)

    context_start = time.perf_counter()

    context, metadata = builder.build_context(DOCUMENT_ID)

    context_end = time.perf_counter()

    print("\nContext Metadata")

    print("------------------------------")

    print(f"Document ID        : {metadata['document_id']}")
    print(f"Sources Used       : {metadata['sources_used']}")
    print(f"Files Processed    : {metadata['files_processed']}")
    print(f"Characters         : {metadata['characters']}")
    print(f"Maximum Characters : {metadata['max_context_characters']}")

    print(
        f"\nContext Build Time : "
        f"{context_end - context_start:.2f} seconds"
    )

    print("\nContext Preview")

    print("------------------------------")

    preview = context[:1200]

    print(preview)

    if len(context) > 1200:
        print("\n...[TRUNCATED]...")

    # ----------------------------------------------------------
    # STEP 4
    # ----------------------------------------------------------

    question = (
        "Why is document MD10191 marked NON_COMPLIANT? "
        "Which checks failed?"
        "Which registry setting caused failure?"
    )

    print("\n[4] Sending Request to Ollama...")

    inference_start = time.perf_counter()

    response = ollama.chat(
        system_prompt=(
            "You are RegulAI1 Mitra.\n"
            "You are an AI Regulatory Compliance Assistant.\n\n"
            "Answer ONLY using the supplied context.\n"
            "Do not invent information.\n"
            "If the answer is unavailable in the context, explicitly state that.\n"
            "Explain the compliance result clearly."
        ),
        context=context,
        user_question=question,
        conversation_history=[],
    )

    inference_end = time.perf_counter()

    print("\nQuestion")

    print("------------------------------")

    print(question)

    print("\nResponse")

    print("------------------------------")

    print(response)

    total_end = time.perf_counter()

    # ----------------------------------------------------------
    # SUMMARY
    # ----------------------------------------------------------

    print_separator()

    print("Performance Summary")

    print_separator()

    print(
        f"Context Build Time : "
        f"{context_end - context_start:.2f} sec"
    )

    print(
        f"Inference Time     : "
        f"{inference_end - inference_start:.2f} sec"
    )

    print(
        f"Total Pipeline     : "
        f"{total_end - total_start:.2f} sec"
    )

    print_separator()


if __name__ == "__main__":
    main()