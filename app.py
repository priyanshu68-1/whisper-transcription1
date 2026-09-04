import os
import tempfile
import streamlit as st
import whisper
import jiwer
from validate_upload import validate_audio_file

# Page Configuration
st.set_page_config(
    page_title="Whisper Audio Transcriber", 
    page_icon="🎙️", 
    layout="centered"
)

# Custom CSS applying your color palette
st.markdown("""
    <style>
    /* Main Background */
    .stApp {
        background-color: #FFF5F5;
        color: #4A4A4A;
    }
    
    /* Headers & Typography */
    h1, h2, h3, h4, label, .stMarkdown {
        color: #4A4A4A !important;
    }

    /* Cards & Container Containers */
    div[data-testid="stMetricValue"], div[data-testid="stMetricLabel"] {
        color: #4A4A4A !important;
    }
    
    /* Text Inputs & Text Area */
    .stTextArea textarea, .stTextInput input {
        background-color: #FFFFFF !important;
        border: 1px solid #E2B4BD !important;
        color: #4A4A4A !important;
        border-radius: 8px;
    }

    /* File Uploader Box */
    div[data-testid="stFileUploader"] {
        background-color: #F7D6D0 !important;
        padding: 15px;
        border-radius: 10px;
        border: 1px dashed #E2B4BD;
    }

    /* Primary Action Buttons */
    div.stButton > button:first-child {
        background-color: #E2B4BD !important;
        color: #4A4A4A !important;
        border: none !important;
        font-weight: bold !important;
        border-radius: 8px !important;
        padding: 0.5rem 1rem !important;
    }
    
    div.stButton > button:first-child:hover {
        background-color: #4A4A4A !important;
        color: #FFF5F5 !important;
    }

    /* Download Button */
    div.stDownloadButton > button:first-child {
        background-color: #4A4A4A !important;
        color: #FFF5F5 !important;
        border-radius: 8px !important;
    }

    /* Divider Lines */
    hr {
        border-color: #E2B4BD !important;
    }
    </style>
""", unsafe_allow_html=True)

st.title("🎙️ Audio Processing & Transcription")
st.write("Upload an audio recording to generate transcripts and calculate accuracy metrics.")

# 1. File Upload
uploaded_file = st.file_uploader(
    "Upload Meeting Recording", 
    type=["mp3", "wav", "m4a", "mp4", "mkv", "flac", "aac", "ogg"]
)

# Optional Ground Truth Input (Empty by default to prevent false WER calculations)
ground_truth = st.text_area(
    "Expected Ground Truth Text (Optional - for Accuracy Testing):",
    value="",
    placeholder="Paste expected spoken text here to evaluate WER and Accuracy %...",
    help="Leave empty if you only want to generate a transcript."
)

@st.cache_resource
def load_whisper_model(model_name="base"):
    return whisper.load_model(model_name)

if uploaded_file is not None:
    st.info(f"📁 Selected File: **{uploaded_file.name}** ({uploaded_file.size / (1024*1024):.2f} MB)")

    # 2. Transcribe Button
    if st.button("🚀 Transcribe & Evaluate"):
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded_file.name)[1]) as temp_file:
            temp_file.write(uploaded_file.read())
            temp_path = temp_file.name

        try:
            # File Upload Validation Check
            is_valid, msg = validate_audio_file(temp_path)
            
            if not is_valid:
                st.error(f"❌ Validation Failed: {msg}")
            else:
                # Processing Status
                with st.status("Processing audio with Whisper...", expanded=True) as status:
                    st.write("🔄 Validating audio stream...")
                    st.write("🧠 Loading Whisper model...")
                    model = load_whisper_model("base")
                    
                    st.write("⚡ Transcribing audio...")
                    result = model.transcribe(temp_path)
                    status.update(label="✅ Processing Complete!", state="complete", expanded=False)

                raw_text = result.get("text", "").strip()
                segments = result.get("segments", [])

                # 3. Accuracy Evaluation Card (Only calculates if user pastes Ground Truth)
                if ground_truth.strip():
                    transformation = jiwer.Compose([
                        jiwer.ToLowerCase(),
                        jiwer.RemovePunctuation(),
                        jiwer.RemoveMultipleSpaces(),
                        jiwer.Strip()
                    ])
                    
                    ref_clean = transformation(ground_truth)
                    hyp_clean = transformation(raw_text)
                    
                    output = jiwer.process_words(ref_clean, hyp_clean)
                    wer = output.wer
                    accuracy = (1.0 - wer) * 100.0

                    st.subheader("📊 Accuracy Metrics")
                    col1, col2, col3 = st.columns(3)
                    col1.metric("Word Accuracy", f"{accuracy:.1f}%")
                    col2.metric("Word Error Rate (WER)", f"{wer * 100:.1f}%")
                    col3.metric("Total Words", len(ref_clean.split()))

                    if accuracy >= 90.0:
                        st.success("🎯 Accuracy Benchmark Passed (≥ 90%)")
                    else:
                        st.warning("⚠️ Accuracy fell below target threshold (90%)")

                # 4. Display Transcript
                st.subheader("📝 Generated Transcript")
                st.caption(f"Detected Language: {result.get('language', 'N/A').upper()}")
                
                for seg in segments:
                    start_time = f"{int(seg['start'] // 60):02d}:{int(seg['start'] % 60):02d}"
                    end_time = f"{int(seg['end'] // 60):02d}:{int(seg['end'] % 60):02d}"
                    st.markdown(f"**`[{start_time} ➔ {end_time}]`** {seg['text'].strip()}")

                st.divider()
                st.download_button(
                    label="📄 Download Transcript (.txt)",
                    data=raw_text,
                    file_name=f"{os.path.splitext(uploaded_file.name)[0]}_transcript.txt",
                    mime="text/plain"
                )

        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)