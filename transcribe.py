import sys
import whisper
from validate_upload import validate_audio_file

def main():
    audio_file = sys.argv[1] if len(sys.argv) > 1 else "transcipt_test2.mp3"

    # Run Task 2 Validation
    is_valid, msg = validate_audio_file(audio_file)
    print(msg)

    if not is_valid:
        print("Stopping transcription due to validation error.")
        sys.exit(1)

    # Run Task 1 Transcription
    print("Loading Whisper model ('base')...")
    model = whisper.load_model("base")
    
    print("Transcribing audio...")
    result = model.transcribe(audio_file)

    print("\n" + "=" * 50)
    print("TRANSCRIPTION RESULT")
    print("=" * 50)
    for segment in result.get("segments", []):
        start = f"{int(segment['start'] // 60):02d}:{int(segment['start'] % 60):02d}"
        end = f"{int(segment['end'] // 60):02d}:{int(segment['end'] % 60):02d}"
        print(f"[{start} -> {end}] {segment['text'].strip()}")
    print("=" * 50)

if __name__ == "__main__":
    main()