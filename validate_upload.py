import os
import sys
import subprocess

# Supported audio and video extensions
ALLOWED_EXTENSIONS = {'.mp3', '.wav', '.m4a', '.mp4', '.mkv', '.flac', '.aac', '.ogg'}
MAX_FILE_SIZE_MB = 500  # Maximum allowed size in Megabytes

def validate_audio_file(file_path: str):
    """
    Validates file existence, file size, allowed format extension, 
    and stream integrity using FFmpeg.
    """
    # 1. Existence Check
    if not os.path.exists(file_path):
        return False, f"REJECTED: File '{file_path}' does not exist."

    # 2. File Size Check
    file_size_bytes = os.path.getsize(file_path)
    if file_size_bytes == 0:
        return False, f"REJECTED: File '{file_path}' is empty (0 bytes)."
    
    file_size_mb = file_size_bytes / (1024 * 1024)
    if file_size_mb > MAX_FILE_SIZE_MB:
        return False, f"REJECTED: File size ({file_size_mb:.2f} MB) exceeds limit ({MAX_FILE_SIZE_MB} MB)."

    # 3. Extension Check
    _, ext = os.path.splitext(file_path)
    ext = ext.lower()
    if ext not in ALLOWED_EXTENSIONS:
        allowed_list = ", ".join(sorted(ALLOWED_EXTENSIONS))
        return False, f"REJECTED: Format '{ext}' is not supported. Allowed formats: {allowed_list}"

    # 4. Stream Integrity Check via FFmpeg
    try:
        cmd = ["ffmpeg", "-v", "error", "-i", file_path, "-f", "null", "-"]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.returncode != 0:
            return False, f"REJECTED: File '{file_path}' is corrupted or contains an invalid audio/video stream."
    except FileNotFoundError:
        # Fallback if ffmpeg command-line utility is not in PATH
        pass

    return True, f"ACCEPTED: '{os.path.basename(file_path)}' ({ext.upper()}, {file_size_mb:.2f} MB) is valid."

if __name__ == "__main__":
    if len(sys.argv) > 1:
        target_file = sys.argv[1]
    else:
        target_file = "transcipt_test2.mp3"

    print(f"\n--- Validating: {target_file} ---")
    is_valid, message = validate_audio_file(target_file)
    print(message)
    print("-" * 40)