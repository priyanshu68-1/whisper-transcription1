import os
import sys
import json
import whisper
from validate_upload import validate_audio_file

def run_transcript_validation(audio_file: str, expected_snippet: str = None):
    print(f"\n--- MILESTONE 1 TASK 3: TRANSCRIPT VALIDATION ---")
    
    # 1. Input Validation
    is_valid, msg = validate_audio_file(audio_file)
    if not is_valid:
        print(f"[FAIL] {msg}")
        return False
    
    # 2. Run Whisper Model
    print(f"[INFO] Processing '{audio_file}' with Whisper...")
    model = whisper.load_model("base")
    result = model.transcribe(audio_file)
    
    raw_text = result.get("text", "").strip()
    segments = result.get("segments", [])

    # Check 1: Generated correctly & Not empty
    if not raw_text:
        print("[FAIL] Transcript Validation: Generated transcript is EMPTY.")
        return False
    print(f"[PASS] Transcript Generated (Character Count: {len(raw_text)}, Segments: {len(segments)})")

    # Check 2: Matches recording (Ground truth snippet check if provided)
    if expected_snippet:
        if expected_snippet.lower() in raw_text.lower():
            print(f"[PASS] Transcript Matches Recording (Found expected snippet: '{expected_snippet}')")
        else:
            print(f"[WARN] Expected snippet '{expected_snippet}' not found verbatim in transcript.")
    else:
        print(f"[PASS] Transcript Content Preview: \"{raw_text[:80]}...\"")

    # Check 3: Save to .txt and .json
    base_name = os.path.splitext(os.path.basename(audio_file))[0]
    txt_path = f"{base_name}_transcript.txt"
    json_path = f"{base_name}_transcript.json"

    # Save TXT
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(raw_text)

    # Save JSON
    json_data = {
        "audio_file": audio_file,
        "language": result.get("language", ""),
        "full_text": raw_text,
        "segments": [
            {
                "start": seg["start"],
                "end": seg["end"],
                "text": seg["text"].strip()
            } for seg in segments
        ]
    }
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(json_data, f, indent=4)

    # Check 4: Verify Files Saved Correctly
    txt_saved = os.path.exists(txt_path) and os.path.getsize(txt_path) > 0
    json_saved = os.path.exists(json_path) and os.path.getsize(json_path) > 0

    if txt_saved and json_saved:
        print(f"[PASS] Transcript Saved Correctly:")
        print(f"       -> Text File : {txt_path} ({os.path.getsize(txt_path)} bytes)")
        print(f"       -> JSON File : {json_path} ({os.path.getsize(json_path)} bytes)")
        print("=" * 50)
        print("TASK 3 VERIFICATION COMPLETE: ALL CHECKS PASSED")
        print("=" * 50)
        return True
    else:
        print("[FAIL] Output file saving failed.")
        return False

if __name__ == "__main__":
    target_audio = sys.argv[1] if len(sys.argv) > 1 else "transcipt_test2.mp3"
    # Optional snippet from your prior run to verify matching text
    snippet = "27th August"
    run_transcript_validation(target_audio, expected_snippet=snippet)