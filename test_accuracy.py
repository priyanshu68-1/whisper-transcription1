import sys
import whisper
import jiwer

def evaluate_accuracy(audio_file: str, ground_truth_text: str, model_size: str = "base"):
    print(f"\n--- MILESTONE 1 TASK 5: ACCURACY TESTING ---")
    print(f"[INFO] Audio File  : {audio_file}")
    print(f"[INFO] Model Size  : {model_size}")
    
    # 1. Run Whisper Model
    model = whisper.load_model(model_size)
    result = model.transcribe(audio_file)
    hypothesis_text = result.get("text", "").strip()

    # 2. Text Normalization Pipeline
    transformation = jiwer.Compose([
        jiwer.ToLowerCase(),
        jiwer.RemovePunctuation(),
        jiwer.RemoveMultipleSpaces(),
        jiwer.Strip()
    ])

    ref_clean = transformation(ground_truth_text)
    hyp_clean = transformation(hypothesis_text)

    # 3. Compute WER metrics using updated jiwer API
    output = jiwer.process_words(ref_clean, hyp_clean)
    wer = output.wer
    accuracy = (1.0 - wer) * 100.0

    substitutions = output.substitutions
    deletions = output.deletions
    insertions = output.insertions
    total_words = len(ref_clean.split())

    # 4. Display Accuracy Report
    print("\n" + "=" * 55)
    print("ACCURACY TEST REPORT")
    print("=" * 55)
    print(f"Ground Truth : \"{ground_truth_text}\"")
    print(f"Hypothesis   : \"{hypothesis_text}\"")
    print("-" * 55)
    print(f"Total Words (N)     : {total_words}")
    print(f"Substitutions (S)   : {substitutions} (incorrect words)")
    print(f"Deletions (D)       : {deletions} (missing words)")
    print(f"Insertions (I)      : {insertions} (extra words)")
    print("-" * 55)
    print(f"Word Error Rate     : {wer:.4f} ({wer * 100:.2f}%)")
    print(f"Transcription Acc.  : {accuracy:.2f}%")
    print("=" * 55)

    # 5. Benchmark Verification (>= 90% Target)
    if accuracy >= 90.0:
        print("SUCCESS: Target accuracy (>= 90%) PASSED.")
        return True
    else:
        print("WARNING: Accuracy fell below 90% target.")
        return False

if __name__ == "__main__":
    audio_path = sys.argv[1] if len(sys.argv) > 1 else "transcipt_test2.mp3"
    
    # Spoken text from your recording
    ACTUAL_SPEECH = "Today's meeting date is 27th August and day is Thursday and the time is 6.45 pm."
    
    evaluate_accuracy(audio_path, ACTUAL_SPEECH)