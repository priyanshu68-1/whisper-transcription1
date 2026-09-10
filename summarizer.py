import json
import os
import sys
from typing import Dict, Any
from llm_service import LLMService

class SummarizerModule:
    """
    Task 2: Dedicated Meeting Summarization Module to format and export structured meeting intelligence.
    """
    def __init__(self, api_key: str = None):
        self.llm_service = LLMService(api_key=api_key)

    def generate_summary(self, transcript: str) -> Dict[str, Any]:
        """
        Generates structured meeting intelligence dictionary from raw transcript.
        """
        return self.llm_service.process_transcript(transcript)

    def format_as_markdown(self, intelligence: Dict[str, Any]) -> str:
        """
        Transforms raw JSON intelligence into structured, formatted Markdown text.
        """
        md = []
        md.append("## Executive Summary")
        md.append(intelligence.get("summary", "N/A") + "\n")

        md.append("### Key Discussion Points")
        for point in intelligence.get("key_points", []):
            md.append(f"- {point}")
        md.append("")

        md.append("### Key Decisions")
        for decision in intelligence.get("decisions", []):
            md.append(f"- {decision}")
        md.append("")

        md.append("### Action Items")
        actions = intelligence.get("action_items", [])
        if actions:
            md.append("| Task | Assignee | Priority | Deadline |")
            md.append("| :--- | :--- | :--- | :--- |")
            for item in actions:
                task = item.get("task", "")
                assignee = item.get("assignee", "Unassigned")
                priority = item.get("priority", "Medium")
                deadline = item.get("deadline", "Not specified")
                md.append(f"| {task} | {assignee} | {priority} | {deadline} |")
        else:
            md.append("No action items identified.")
        md.append("")

        md.append("### Participants")
        md.append(", ".join(intelligence.get("participants", ["Not specified"])) + "\n")

        return "\n".join(md)

    def export_summary(self, intelligence: Dict[str, Any], base_filename: str = "meeting_summary") -> Dict[str, str]:
        """
        Exports summary intelligence to both .md and .json files.
        """
        md_filename = f"{base_filename}.md"
        json_filename = f"{base_filename}.json"

        # Save Markdown
        md_content = self.format_as_markdown(intelligence)
        with open(md_filename, "w", encoding="utf-8") as f:
            f.write(md_content)

        # Save JSON
        with open(json_filename, "w", encoding="utf-8") as f:
            json.dump(intelligence, f, indent=4)

        return {"markdown_file": md_filename, "json_file": json_filename}

if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    sample_transcript = """
    [00:00] Manager: Let's discuss the mobile application launch.
    [00:05] Ravi: I am currently working on the API integration.
    [00:10] Priya: I will handle the UI testing and prepare the report.
    [00:15] Manager: Great. We will continue with the planned mobile application launch. 
    Ravi, please complete API integration by Friday. Priya, prepare the UI testing report.
    """

    print("\n============================================================")
    print("INPUT TRANSCRIPT")
    print("============================================================")
    print(sample_transcript.strip())
    print("============================================================\n")

    summarizer = SummarizerModule()
    intelligence_output = summarizer.generate_summary(sample_transcript)
    formatted_markdown = summarizer.format_as_markdown(intelligence_output)

    print("============================================================")
    print("OUTPUT: FORMATTED MARKDOWN SUMMARY")
    print("============================================================")
    print(formatted_markdown)
    print("============================================================\n")

    # Export test
    files = summarizer.export_summary(intelligence_output, "task2_summary_test")
    print(f"[SUCCESS] Summary exported to: {files['markdown_file']} and {files['json_file']}")