import os
import uuid
import tempfile
import json
from datetime import datetime
import streamlit as st
import whisper
import jiwer
import pandas as pd

from dotenv import load_dotenv
load_dotenv(override=True)

from validate_upload import validate_audio_file
from llm_service import LLMService
from participant_mapper import ParticipantMapper
from action_engine import ActionItemEngine
from database import DatabaseManager
from pipeline_service import ProcessingPipeline

# -----------------------------------------------------------------------------
# 1. PAGE CONFIGURATION
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="TruthShield AI • Meeting Intelligence",
    page_icon="🎙️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -----------------------------------------------------------------------------
# 2. VIBRANT, COLORFUL & ACCESSIBLE MODERN DESIGN SYSTEM
# Rich gradients, colorful accent borders, glowing pills, and crisp contrast.
# -----------------------------------------------------------------------------
COLORFUL_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');

:root {
    --primary-gradient: linear-gradient(135deg, #4F46E5 0%, #7C3AED 50%, #EC4899 100%);
    --indigo-gradient: linear-gradient(135deg, #3B82F6 0%, #6366F1 100%);
    --emerald-gradient: linear-gradient(135deg, #10B981 0%, #059669 100%);
    --amber-gradient: linear-gradient(135deg, #F59E0B 0%, #D97706 100%);
    --rose-gradient: linear-gradient(135deg, #F43F5E 0%, #E11D48 100%);
    --cyan-gradient: linear-gradient(135deg, #06B6D4 0%, #0284C7 100%);
    
    --text-dark: #0F172A;
    --text-body: #334155;
    --text-muted: #64748B;
    --card-bg: #FFFFFF;
    --card-border: #E2E8F0;
}

html, body, [class*="css"] {
    font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif !important;
}

/* Page Background: Subtle Colorful Ambient Mesh */
.stApp {
    background: 
        radial-gradient(at 0% 0%, rgba(99, 102, 241, 0.07) 0px, transparent 50%),
        radial-gradient(at 100% 0%, rgba(236, 72, 153, 0.06) 0px, transparent 50%),
        radial-gradient(at 50% 100%, rgba(16, 185, 129, 0.05) 0px, transparent 50%),
        #F8FAFC !important;
    color: var(--text-dark) !important;
}

/* Typography */
h1, h2, h3, h4, h5, h6 {
    color: var(--text-dark) !important;
    font-weight: 700 !important;
    letter-spacing: -0.02em !important;
}

p, span, li, label, div {
    color: var(--text-body);
}

/* Colorful Sidebar */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #1E1B4B 0%, #0F172A 100%) !important;
    border-right: 1px solid rgba(129, 140, 248, 0.25) !important;
    box-shadow: 4px 0 24px rgba(15, 23, 42, 0.15);
}

section[data-testid="stSidebar"] * {
    color: #F8FAFC !important;
}

section[data-testid="stSidebar"] h1,
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3,
section[data-testid="stSidebar"] strong {
    color: #FFFFFF !important;
}

section[data-testid="stSidebar"] .stCaption,
section[data-testid="stSidebar"] small {
    color: #94A3B8 !important;
}

section[data-testid="stSidebar"] hr {
    border-color: rgba(148, 163, 184, 0.15) !important;
    margin: 18px 0 !important;
}

section[data-testid="stSidebar"] div[data-baseweb="select"] > div {
    background-color: #1E293B !important;
    border: 1px solid #334155 !important;
    color: #FFFFFF !important;
    border-radius: 8px !important;
}

section[data-testid="stSidebar"] div[data-baseweb="select"] * {
    color: #FFFFFF !important;
}

/* Vibrant Hero Header */
.colorful-header {
    background: linear-gradient(135deg, #312E81 0%, #4F46E5 40%, #7C3AED 75%, #EC4899 100%);
    border-radius: 16px;
    padding: 26px 32px;
    color: #FFFFFF !important;
    box-shadow: 0 10px 30px -5px rgba(79, 70, 229, 0.35);
    margin-bottom: 22px;
    position: relative;
    overflow: hidden;
}

.colorful-header h1, .colorful-header p, .colorful-header span {
    color: #FFFFFF !important;
}

.header-chip {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: rgba(255, 255, 255, 0.18);
    backdrop-filter: blur(8px);
    padding: 5px 14px;
    border-radius: 9999px;
    font-size: 0.8rem;
    font-weight: 600;
    color: #FFFFFF !important;
    border: 1px solid rgba(255, 255, 255, 0.25);
}

/* Active Meeting Ribbon */
.active-ribbon {
    background: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-left: 5px solid #6366F1;
    border-radius: 12px;
    padding: 14px 20px;
    margin-bottom: 20px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 12px;
    box-shadow: 0 4px 12px rgba(99, 102, 241, 0.06);
}

/* Modern Colorful Containers & Cards */
div[data-testid="stVerticalBlockBorderWrapper"] > div {
    background-color: #FFFFFF !important;
    border: 1px solid var(--card-border) !important;
    border-radius: 14px !important;
    padding: 20px 22px !important;
    box-shadow: 0 4px 16px rgba(15, 23, 42, 0.04) !important;
    margin-bottom: 8px !important;
    transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease !important;
}

div[data-testid="stVerticalBlockBorderWrapper"]:hover > div {
    box-shadow: 0 8px 24px rgba(99, 102, 241, 0.1) !important;
    border-color: #C7D2FE !important;
}

.colorful-card {
    background-color: #FFFFFF;
    border: 1px solid var(--card-border);
    border-radius: 14px;
    padding: 22px;
    box-shadow: 0 4px 16px rgba(15, 23, 42, 0.04);
    margin-bottom: 20px;
    transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
}

.colorful-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 24px rgba(99, 102, 241, 0.12);
    border-color: #C7D2FE;
}

/* Metrics with Colorful Gradient Top Borders */
div[data-testid="stMetric"] {
    background-color: #FFFFFF !important;
    border: 1px solid #E2E8F0 !important;
    border-top: 4px solid #6366F1 !important;
    border-radius: 12px !important;
    padding: 18px !important;
    box-shadow: 0 4px 12px rgba(15, 23, 42, 0.03) !important;
    transition: transform 0.2s ease !important;
}

div[data-testid="stMetric"]:hover {
    transform: translateY(-2px) !important;
    border-color: #818CF8 !important;
}

div[data-testid="stMetricValue"] {
    font-size: 1.85rem !important;
    font-weight: 800 !important;
    color: #1E1B4B !important;
}

div[data-testid="stMetricLabel"] {
    color: #64748B !important;
    font-weight: 700 !important;
    font-size: 0.76rem !important;
    text-transform: uppercase !important;
    letter-spacing: 0.05em !important;
}

/* Custom Tabs with Vibrant Hover & Active Underlines */
button[data-baseweb="tab"] {
    background-color: transparent !important;
    color: #475569 !important;
    font-weight: 600 !important;
    font-size: 0.94rem !important;
    padding: 12px 18px !important;
    border-radius: 10px 10px 0 0 !important;
    border: none !important;
    transition: all 0.2s ease !important;
}

button[data-baseweb="tab"]:hover {
    color: #4F46E5 !important;
    background-color: #EEF2FF !important;
}

button[data-baseweb="tab"][aria-selected="true"] {
    background-color: #FFFFFF !important;
    color: #4F46E5 !important;
    font-weight: 700 !important;
    border-bottom: 3px solid #6366F1 !important;
    box-shadow: 0 -2px 10px rgba(99, 102, 241, 0.1) !important;
}

/* Vibrant Primary Buttons */
div.stButton > button:first-child {
    background: linear-gradient(135deg, #4F46E5 0%, #6366F1 50%, #7C3AED 100%) !important;
    color: #FFFFFF !important;
    border: none !important;
    font-weight: 700 !important;
    font-size: 0.92rem !important;
    padding: 11px 24px !important;
    border-radius: 10px !important;
    box-shadow: 0 4px 14px rgba(79, 70, 229, 0.35) !important;
    transition: all 0.25s ease !important;
}

div.stButton > button:first-child:hover {
    background: linear-gradient(135deg, #4338CA 0%, #4F46E5 50%, #6D28D9 100%) !important;
    transform: translateY(-2px);
    box-shadow: 0 8px 20px rgba(79, 70, 229, 0.45) !important;
}

div.stButton > button:first-child * {
    color: #FFFFFF !important;
}

/* Secondary Buttons */
div.stButton > button[kind="secondary"] {
    background-color: #FFFFFF !important;
    color: #334155 !important;
    border: 1px solid #CBD5E1 !important;
    border-radius: 10px !important;
    box-shadow: 0 2px 6px rgba(15, 23, 42, 0.04) !important;
}

/* Form Controls & Inputs (Normal & Active) - Crisp Dark Text */
.stTextInput input, 
.stTextArea textarea,
div[data-baseweb="input"] input,
div[data-baseweb="textarea"] textarea,
div[data-baseweb="base-input"] input,
div[data-baseweb="base-input"] textarea {
    background-color: #FFFFFF !important;
    color: #0F172A !important;
    -webkit-text-fill-color: #0F172A !important;
    border: 1.5px solid #CBD5E1 !important;
    border-radius: 10px !important;
    font-size: 0.95rem !important;
    line-height: 1.6 !important;
}

/* Disabled Form Controls (Fixes Invisible White-on-White Text) */
.stTextInput input:disabled, 
.stTextArea textarea:disabled,
.stTextInput input[disabled], 
.stTextArea textarea[disabled],
div[data-baseweb="input"] input:disabled,
div[data-baseweb="textarea"] textarea:disabled,
div[data-baseweb="base-input"][disabled],
div[data-baseweb="base-input"] textarea:disabled,
div[data-baseweb="base-input"] input:disabled {
    background-color: #F8FAFC !important;
    color: #0F172A !important;
    -webkit-text-fill-color: #0F172A !important;
    opacity: 1 !important;
    border: 1.5px solid #94A3B8 !important;
    font-weight: 500 !important;
    cursor: default !important;
}

.stTextInput input:focus, 
.stTextArea textarea:focus,
div[data-baseweb="input"]:focus-within,
div[data-baseweb="textarea"]:focus-within {
    border-color: #6366F1 !important;
    box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.2) !important;
}

/* Dropdowns & Selectboxes */
div[data-baseweb="select"] > div {
    background-color: #FFFFFF !important;
    color: #0F172A !important;
    -webkit-text-fill-color: #0F172A !important;
    border: 1.5px solid #CBD5E1 !important;
    border-radius: 10px !important;
}

div[data-baseweb="select"] * {
    color: #0F172A !important;
    -webkit-text-fill-color: #0F172A !important;
}

/* Dropdown Menu Popover Options */
ul[role="listbox"], div[role="listbox"] {
    background-color: #FFFFFF !important;
    border: 1px solid #CBD5E1 !important;
    border-radius: 10px !important;
    box-shadow: 0 10px 25px rgba(15, 23, 42, 0.15) !important;
}

li[role="option"] {
    color: #0F172A !important;
    -webkit-text-fill-color: #0F172A !important;
    background-color: #FFFFFF !important;
}

li[role="option"]:hover, li[role="option"][aria-selected="true"] {
    background-color: #EEF2FF !important;
    color: #4F46E5 !important;
    -webkit-text-fill-color: #4F46E5 !important;
}

/* Radio Button Labels in Main Page */
div[data-testid="stRadio"] label p,
div[data-testid="stRadio"] label span {
    color: #0F172A !important;
    font-weight: 600 !important;
}

/* Radio Button Labels in Sidebar */
section[data-testid="stSidebar"] div[data-testid="stRadio"] label p,
section[data-testid="stSidebar"] div[data-testid="stRadio"] label span {
    color: #FFFFFF !important;
    font-weight: 600 !important;
}

/* Ensure Alerts Have Clear Dark Text */
div[data-testid="stAlert"] * {
    color: #0F172A !important;
}

/* Code Blocks Styling */
div[data-testid="stCodeBlock"] pre {
    background-color: #0F172A !important;
    border: 1px solid #334155 !important;
    border-radius: 12px !important;
    padding: 16px !important;
}

div[data-testid="stCodeBlock"] code {
    color: #38BDF8 !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.88rem !important;
}

/* File Uploader with Gradient Dash */
div[data-testid="stFileUploader"] {
    background: linear-gradient(180deg, #FFFFFF 0%, #F8FAFC 100%) !important;
    border: 2px dashed #818CF8 !important;
    border-radius: 14px !important;
    padding: 24px !important;
    text-align: center;
    transition: all 0.25s ease !important;
}

div[data-testid="stFileUploader"]:hover {
    border-color: #4F46E5 !important;
    background: #EEF2FF !important;
}

/* Colorful Status Badges */
.badge-vibrant {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    padding: 4px 12px;
    border-radius: 9999px;
    font-size: 0.78rem;
    font-weight: 700;
    letter-spacing: 0.02em;
}

.badge-indigo {
    background-color: #EEF2FF;
    color: #4338CA;
    border: 1px solid #C7D2FE;
}

.badge-emerald {
    background-color: #ECFDF5;
    color: #065F46;
    border: 1px solid #6EE7B7;
}

.badge-amber {
    background-color: #FFFBEB;
    color: #92400E;
    border: 1px solid #FCD34D;
}

.badge-rose {
    background-color: #FFF1F2;
    color: #BE123C;
    border: 1px solid #FDA4AF;
}

.badge-cyan {
    background-color: #ECFEFF;
    color: #0E7490;
    border: 1px solid #A5F3FC;
}

.badge-fuchsia {
    background-color: #FDF4FF;
    color: #86198F;
    border: 1px solid #F0ABFC;
}

/* Stacked Accuracy Progress Bar */
.acc-bar-container {
    width: 100%;
    height: 18px;
    border-radius: 9999px;
    background-color: #E2E8F0;
    overflow: hidden;
    display: flex;
    margin: 14px 0 18px 0;
    box-shadow: inset 0 2px 4px rgba(0,0,0,0.06);
}

.acc-seg-hits {
    background: linear-gradient(90deg, #10B981 0%, #059669 100%);
    height: 100%;
}

.acc-seg-subs {
    background: linear-gradient(90deg, #F59E0B 0%, #D97706 100%);
    height: 100%;
}

.acc-seg-dels {
    background: linear-gradient(90deg, #F43F5E 0%, #E11D48 100%);
    height: 100%;
}

.acc-seg-ins {
    background: linear-gradient(90deg, #6366F1 0%, #4F46E5 100%);
    height: 100%;
}

/* Alignment Text Display */
.alignment-box {
    background-color: #0F172A;
    color: #38BDF8 !important;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.85rem;
    padding: 16px 20px;
    border-radius: 12px;
    border: 1px solid #334155;
    overflow-x: auto;
    white-space: pre-wrap;
    line-height: 1.5;
    margin-top: 10px;
}

/* Timestamp Pill */
.timestamp-chip {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.76rem;
    color: #4F46E5 !important;
    background-color: #EEF2FF;
    padding: 2px 8px;
    border-radius: 6px;
    border: 1px solid #C7D2FE;
    margin-right: 8px;
    font-weight: 600;
}
</style>
"""
st.markdown(COLORFUL_CSS, unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 3. DATABASE SETUP & STATE MANAGEMENT
# -----------------------------------------------------------------------------
@st.cache_resource
def get_db():
    return DatabaseManager()

db = get_db()
all_meetings = db.list_all_meetings()

# Manage active meeting state cleanly
if "active_meeting_id" not in st.session_state:
    if all_meetings:
        st.session_state["active_meeting_id"] = all_meetings[0]["meeting_id"]
    else:
        st.session_state["active_meeting_id"] = None

curr_mid = st.session_state.get("active_meeting_id")
if curr_mid:
    if "active_meeting" not in st.session_state or not st.session_state.get("active_meeting") or st.session_state["active_meeting"].get("meeting_id") != curr_mid:
        st.session_state["active_meeting"] = db.get_meeting(curr_mid)
else:
    st.session_state["active_meeting"] = None

if "ground_truth" not in st.session_state:
    st.session_state["ground_truth"] = "Today's meeting date is 27th August and day is Thursday and the time is 6.45 pm."

active_m = st.session_state.get("active_meeting")

# -----------------------------------------------------------------------------
# 4. COLORFUL SIDEBAR
# -----------------------------------------------------------------------------
with st.sidebar:
    st.markdown(
        """
        <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 8px;">
            <div style="background: linear-gradient(135deg, #6366F1 0%, #A855F7 100%); width: 44px; height: 44px; border-radius: 12px; display: flex; align-items: center; justify-content: center; font-size: 1.4rem; box-shadow: 0 4px 14px rgba(99, 102, 241, 0.4);">
                🎙️
            </div>
            <div>
                <h3 style="margin: 0; font-size: 1.25rem; font-weight: 800; color: #FFFFFF !important;">TruthShield AI</h3>
                <div style="font-size: 0.78rem; color: #A5B4FC !important; font-weight: 600;">Meeting Intelligence Suite</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )
    st.divider()

    # Main Menu Navigation
    st.markdown("<p style='font-size: 0.8rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; color: #C7D2FE !important;'>📌 Main Menu</p>", unsafe_allow_html=True)
    app_section = st.radio(
        "Navigation",
        ["🎙️ Meeting Notes", "🎯 Accuracy Checker"],
        index=0,
        label_visibility="collapsed"
    )
    st.divider()

    if app_section == "🎙️ Meeting Notes":
        # Active Meeting Switcher
        st.markdown("<p style='font-size: 0.8rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; color: #C7D2FE !important;'>📂 Select a Saved Meeting</p>", unsafe_allow_html=True)
        if all_meetings:
            meeting_dict = {m["meeting_id"]: f"{m['title'][:24]}... ({m['meeting_id']})" for m in all_meetings}
            meeting_id_list = list(meeting_dict.keys())

            if st.session_state.get("active_meeting_id") not in meeting_id_list:
                st.session_state["active_meeting_id"] = meeting_id_list[0]
                st.session_state["active_meeting"] = db.get_meeting(meeting_id_list[0])

            current_active = st.session_state.get("active_meeting_id")
            def_idx = meeting_id_list.index(current_active) if current_active in meeting_id_list else 0

            chosen_id = st.selectbox(
                "Select Meeting",
                options=meeting_id_list,
                format_func=lambda x: meeting_dict.get(x, x),
                index=def_idx,
                key=f"sb_meeting_select_{current_active}",
                label_visibility="collapsed"
            )
            if chosen_id != current_active:
                st.session_state["active_meeting_id"] = chosen_id
                st.session_state["active_meeting"] = db.get_meeting(chosen_id)
                st.rerun()
        else:
            st.caption("No saved meetings yet.")

        st.divider()

        # AI Transcription Speed / Size Setting
        st.markdown("<p style='font-size: 0.8rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; color: #C7D2FE !important;'>⚙️ AI Transcription Speed</p>", unsafe_allow_html=True)
        whisper_choice = st.selectbox(
            "Whisper Model",
            ["base", "tiny", "small", "medium"],
            index=0,
            label_visibility="collapsed"
        )
        model_labels = {
            "base": "Base: Fast & accurate (Recommended)",
            "tiny": "Tiny: Ultra-fast",
            "small": "Small: Higher accuracy",
            "medium": "Medium: Studio quality"
        }
        st.caption(model_labels[whisper_choice])
    else:
        whisper_choice = "base"
        st.markdown(
            """
            <div style="background: rgba(16, 185, 129, 0.15); border: 1px solid rgba(52, 211, 153, 0.3); border-radius: 10px; padding: 12px; margin-bottom: 8px;">
                <div style="font-size: 0.82rem; font-weight: 700; color: #A7F3D0; margin-bottom: 4px;">💡 What is Accuracy?</div>
                <div style="font-size: 0.78rem; color: #E2E8F0; line-height: 1.5;">
                    Word Accuracy measures what % of spoken words Whisper transcribed correctly compared to your expected text.
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    st.divider()

    # Repository KPI Summary
    st.markdown("<p style='font-size: 0.8rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; color: #C7D2FE !important;'>📊 Meeting Library Stats</p>", unsafe_allow_html=True)
    db_stats = db.get_dashboard_stats()
    
    col_sb1, col_sb2 = st.columns(2)
    with col_sb1:
        st.markdown(
            f"""
            <div style="background: rgba(99, 102, 241, 0.15); border: 1px solid rgba(129, 140, 248, 0.3); border-radius: 10px; padding: 10px 12px;">
                <div style="font-size: 0.72rem; color: #C7D2FE !important; font-weight: 700;">MEETINGS</div>
                <div style="font-size: 1.4rem; font-weight: 800; color: #FFFFFF !important;">{db_stats['total_meetings']}</div>
            </div>
            """,
            unsafe_allow_html=True
        )
    with col_sb2:
        st.markdown(
            f"""
            <div style="background: rgba(236, 72, 153, 0.15); border: 1px solid rgba(244, 114, 182, 0.3); border-radius: 10px; padding: 10px 12px;">
                <div style="font-size: 0.72rem; color: #FBCFE8 !important; font-weight: 700;">TO-DOS</div>
                <div style="font-size: 1.4rem; font-weight: 800; color: #FFFFFF !important;">{db_stats['total_action_items']}</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    st.markdown(
        f"<div style='margin-top: 10px; font-size: 0.82rem; color: #E2E8F0 !important;'>"
        f"Pending: <b style='color:#FDE68A;'>{db_stats['pending_action_items']}</b> &bull; "
        f"Completed: <b style='color:#6EE7B7;'>{db_stats['completed_action_items']}</b>"
        f"</div>",
        unsafe_allow_html=True
    )

    st.divider()
    st.markdown(
        """
        <div style="font-size: 0.74rem; color: rgba(255,255,255,0.6) !important; text-align: center;">
            TruthShield AI &bull; Vibrant Edition 2026<br>
            Powered by Whisper & Gemini
        </div>
        """,
        unsafe_allow_html=True
    )

# -----------------------------------------------------------------------------
# 5. SECTION ROUTING: MEETING NOTES vs ACCURACY CHECKER
# -----------------------------------------------------------------------------
if app_section == "🎙️ Meeting Notes":
    # Header: Clean & simple words
    st.markdown(
        """
        <div class="colorful-header">
            <h1 style="margin: 0; font-size: 2rem; font-weight: 800; letter-spacing: -0.02em;">
                🎙️ Meeting Notes & Tasks
            </h1>
            <p style="margin: 6px 0 0 0; font-size: 0.95rem; opacity: 0.95;">
                Simple audio transcription, clear meeting summaries, and easy task tracking.
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

    # Active Meeting Ribbon
    if active_m:
        col_rib1, col_rib2 = st.columns([3, 1])
        with col_rib1:
            st.markdown(
                f"""
                <div class="active-ribbon">
                    <div>
                        <div style="font-size: 0.74rem; font-weight: 700; color: #6366F1; text-transform: uppercase; letter-spacing: 0.05em;">CURRENT MEETING</div>
                        <div style="font-weight: 800; font-size: 1.12rem; color: #0F172A;">{active_m.get('title', 'Untitled Meeting')}</div>
                    </div>
                    <div style="display: flex; gap: 8px; align-items: center; flex-wrap: wrap;">
                        <span class="badge-vibrant badge-indigo">ID: {active_m.get('meeting_id')}</span>
                        <span class="badge-vibrant badge-cyan">⏱️ {active_m.get('duration_seconds', 0.0):.1f}s</span>
                        <span class="badge-vibrant badge-emerald">✅ Saved</span>
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )
        with col_rib2:
            if st.button("🚀 Try Sample Meeting", help="Test with our built-in 8-second meeting audio"):
                sample_file = "transcipt_test2.mp3"
                if os.path.exists(sample_file):
                    with st.spinner("Processing sample audio..."):
                        pipeline = ProcessingPipeline(model_size="base")
                        ok, res, msg = pipeline.run_full_pipeline(
                            sample_file,
                            meeting_title="Q3 Strategy & Date Alignment Sync",
                            custom_meeting_id="MEET-DEMO-SAMPLE"
                        )
                        if ok:
                            st.session_state["active_meeting_id"] = res["meeting_id"]
                            st.session_state["active_meeting"] = res
                            st.session_state["ground_truth"] = "Today's meeting date is 27th August and day is Thursday and the time is 6.45 pm."
                            st.toast("Sample Meeting loaded!", icon="🎉")
                            st.rerun()

    # 5 Clean Tabs (Accuracy is in its own separate page!)
    tab_upload, tab_summary, tab_people, tab_transcript, tab_saved = st.tabs([
        "🎙️ Upload Audio",
        "📋 Summary & Tasks",
        "👥 People",
        "📝 Transcript",
        "📁 Saved Meetings"
    ])

    # -------------------------------------------------------------------------
    # TAB 1: UPLOAD AUDIO
    # -------------------------------------------------------------------------
    with tab_upload:
        col_u1, col_u2 = st.columns([2, 1])

        with col_u1:
            with st.container(border=True):
                st.markdown("<h3 style='margin-top:0; color:#1E1B4B;'>📁 Upload Audio File</h3>", unsafe_allow_html=True)
                st.markdown("<p style='color:#64748B; font-size:0.92rem;'>Select an audio or video file to transcribe and create meeting notes.</p>", unsafe_allow_html=True)

                col_samp1, col_samp2 = st.columns([1, 2])
                with col_samp1:
                    use_sample = st.button("⚡ Use Sample Audio")
                with col_samp2:
                    st.caption("Quickly test with built-in `transcipt_test2.mp3`.")

                uploaded_audio = st.file_uploader(
                    "Drop your audio/video recording here",
                    type=["mp3", "wav", "m4a", "mp4", "mkv", "flac", "aac", "ogg"],
                    help="Supported: MP3, WAV, M4A, MP4, MKV, FLAC, AAC, OGG (Max 500 MB)"
                )

                sample_is_active = False
                if use_sample:
                    st.session_state["use_sample"] = True
                    st.toast("Sample audio chosen: transcipt_test2.mp3", icon="🎵")

                if st.session_state.get("use_sample", False) and not uploaded_audio:
                    sample_is_active = True
                    st.info("🎵 **Active File:** Built-in `transcipt_test2.mp3` (141 KB)")
                    if os.path.exists("transcipt_test2.mp3"):
                        st.audio("transcipt_test2.mp3")

                elif uploaded_audio is not None:
                    st.session_state["use_sample"] = False
                    size_mb = uploaded_audio.size / (1024 * 1024)
                    st.success(f"📁 **Loaded File:** `{uploaded_audio.name}` ({size_mb:.2f} MB)")
                    st.audio(uploaded_audio)

                title_input = st.text_input(
                    "🏷️ Meeting Title (Optional):",
                    value="Q3 Strategy & Date Alignment Sync" if sample_is_active else "",
                    placeholder="e.g. Weekly Team Sync"
                )

                can_start = (uploaded_audio is not None) or sample_is_active
                if st.button("🚀 Transcribe Audio & Create Notes", disabled=not can_start):
                    work_path = None
                    if sample_is_active:
                        work_path = "transcipt_test2.mp3"
                    else:
                        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded_audio.name)[1]) as tf:
                            tf.write(uploaded_audio.read())
                            work_path = tf.name

                    try:
                        valid, err = validate_audio_file(work_path)
                        if not valid:
                            st.error(f"❌ Audio validation failed: {err}")
                        else:
                            new_id = f"MEET-{uuid.uuid4().hex[:8].upper()}"
                            def_title = "Sample Meeting" if sample_is_active else uploaded_audio.name
                            final_title = title_input.strip() or os.path.splitext(def_title)[0].replace("_", " ").title()

                            with st.status("⚡ Transcribing audio and generating notes...", expanded=True) as box:
                                st.write("1️⃣ Checking audio format...")
                                st.write(f"2️⃣ Transcribing speech with Whisper ({whisper_choice})...")

                                pipeline = ProcessingPipeline(model_size=whisper_choice)
                                ok, data, pmsg = pipeline.run_full_pipeline(
                                    work_path,
                                    meeting_title=final_title,
                                    custom_meeting_id=new_id
                                )

                                st.write("3️⃣ Extracting key discussion points & decisions...")
                                st.write("4️⃣ Organizing action items and owners...")
                                st.write("5️⃣ Saving meeting to database...")

                                if ok:
                                    box.update(label="✅ Meeting Ready!", state="complete", expanded=False)
                                    st.session_state["active_meeting_id"] = new_id
                                    st.session_state["active_meeting"] = data
                                    st.balloons()
                                    st.success(f"🎉 Meeting saved with ID: `{new_id}`! View summary and tasks in the Summary tab.")
                                else:
                                    box.update(label="❌ Failed to process audio", state="error")
                                    st.error(pmsg)

                    finally:
                        if work_path and not sample_is_active and os.path.exists(work_path):
                            os.remove(work_path)

        with col_u2:
            st.markdown(
                """
                <div class="colorful-card" style="border-top: 4px solid #EC4899;">
                    <h4 style="margin-top:0; color:#1E1B4B;">✨ What You Get</h4>
                    <div style="margin-bottom:12px;">
                        <span class="badge-vibrant badge-indigo">1. Full Transcript</span>
                        <div style="font-size:0.85rem; color:#64748B; margin-top:4px;">Word-for-word text of everything spoken in the audio.</div>
                    </div>
                    <div style="margin-bottom:12px;">
                        <span class="badge-vibrant badge-fuchsia">2. Executive Summary</span>
                        <div style="font-size:0.85rem; color:#64748B; margin-top:4px;">Key discussion points and strategic decisions in simple bullet points.</div>
                    </div>
                    <div style="margin-bottom:12px;">
                        <span class="badge-vibrant badge-amber">3. Action Items</span>
                        <div style="font-size:0.85rem; color:#64748B; margin-top:4px;">Follow-up tasks assigned to team members with priority levels.</div>
                    </div>
                    <div>
                        <span class="badge-vibrant badge-emerald">4. Saved Library</span>
                        <div style="font-size:0.85rem; color:#64748B; margin-top:4px;">All meetings stored securely in SQLite database for quick reference.</div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

    active_m = st.session_state.get("active_meeting")

    # -----------------------------------------------------------------------------
    # TAB 2: EXECUTIVE SUMMARY & TO-DOS
    # -----------------------------------------------------------------------------
    with tab_summary:
        if active_m:
            words = len(active_m.get('transcript', '').split())
            mins = max(1, round(words / 180, 1))

            # Executive Summary Box
            st.markdown(
                f"""
                <div class="colorful-card" style="border-left: 6px solid #4F46E5;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; flex-wrap: wrap; gap: 8px;">
                        <h3 style="margin: 0; color: #1E1B4B;">💡 Executive Summary</h3>
                        <div style="display: flex; gap: 6px;">
                            <span class="badge-vibrant badge-indigo">📖 ~{mins} min read</span>
                            <span class="badge-vibrant badge-cyan">📝 {words} words</span>
                        </div>
                    </div>
                    <p style="font-size: 1.05rem; line-height: 1.7; color: #1E293B; margin: 0; font-weight: 500;">
                        {active_m.get('summary', 'No summary available.')}
                    </p>
                </div>
                """,
                unsafe_allow_html=True
            )

            col_sum1, col_sum2 = st.columns(2)
            with col_sum1:
                with st.container(border=True):
                    st.markdown("<h4 style='margin-top:0; color:#065F46;'>📌 Key Discussion Points</h4>", unsafe_allow_html=True)
                    pts = active_m.get("key_points", [])
                    if pts:
                        for idx, p in enumerate(pts, 1):
                            st.markdown(f"**{idx}.** {p}")
                    else:
                        st.caption("No key points listed.")

            with col_sum2:
                with st.container(border=True):
                    st.markdown("<h4 style='margin-top:0; color:#92400E;'>✅ Strategic Decisions Made</h4>", unsafe_allow_html=True)
                    decs = active_m.get("decisions", [])
                    if decs:
                        for idx, d in enumerate(decs, 1):
                            st.markdown(f"**{idx}.** {d}")
                    else:
                        st.caption("No decisions listed.")

            # Tasks Section
            st.markdown("<h3 style='margin-top: 16px;'>🎯 Interactive Tasks & Follow-ups</h3>", unsafe_allow_html=True)
            task_list = active_m.get("action_items", [])

            if task_list:
                col_filter, _ = st.columns([2, 2])
                with col_filter:
                    chosen_filter = st.radio(
                        "Filter by Status:",
                        ["All", "Pending", "In Progress", "Completed"],
                        horizontal=True
                    )

                filtered_tasks = task_list if chosen_filter == "All" else [t for t in task_list if t.get("status") == chosen_filter]
                st.caption(f"Showing **{len(filtered_tasks)}** of {len(task_list)} tasks")

                for t in filtered_tasks:
                    tid = t.get("id")
                    prio = t.get("priority", "Medium")
                    prio_badge = "badge-rose" if prio == "High" else ("badge-amber" if prio == "Medium" else "badge-emerald")
                    status = t.get("status", "Pending")

                    with st.container(border=True):
                        col_t_left, col_t_right = st.columns([4, 1.3])
                        with col_t_left:
                            st.markdown(f"**{t.get('task')}** &nbsp; <span class='badge-vibrant {prio_badge}'>{prio}</span>", unsafe_allow_html=True)
                            st.markdown(f"<span style='color:#475569; font-size:0.86rem;'>👤 <b>Owner:</b> {t.get('assignee', 'Unassigned')} &nbsp;|&nbsp; 📅 <b>Deadline:</b> {t.get('deadline', 'None')} &nbsp;|&nbsp; ⚡ <b>Status:</b> {status}</span>", unsafe_allow_html=True)
                        with col_t_right:
                            if tid:
                                new_st = st.selectbox(
                                    "Status",
                                    ["Pending", "In Progress", "Completed"],
                                    index=["Pending", "In Progress", "Completed"].index(status) if status in ["Pending", "In Progress", "Completed"] else 0,
                                    key=f"task_st_{tid}",
                                    label_visibility="collapsed"
                                )
                                if new_st != status:
                                    db.update_action_item_status(tid, new_st)
                                    t["status"] = new_st
                                    st.toast(f"Task marked as '{new_st}'", icon="✅")
                                    st.rerun()

                # Add Task Form
                with st.expander("➕ Add New Action Item"):
                    with st.form(f"add_t_{active_m.get('meeting_id')}"):
                        task_text = st.text_input("Task Description*", placeholder="e.g. Email the slide deck to client")
                        col_tf1, col_tf2, col_tf3 = st.columns(3)
                        with col_tf1:
                            task_person = st.text_input("Assigned To", value="Team")
                        with col_tf2:
                            task_priority = st.selectbox("Priority", ["High", "Medium", "Low"], index=1)
                        with col_tf3:
                            task_deadline = st.text_input("Deadline", placeholder="e.g. Tomorrow 5 PM")

                        if st.form_submit_button("Save Task"):
                            if task_text.strip():
                                db.add_action_item(
                                    meeting_id=active_m.get('meeting_id'),
                                    task=task_text.strip(),
                                    assignee=task_person.strip(),
                                    priority=task_priority,
                                    deadline=task_deadline.strip()
                                )
                                st.session_state["active_meeting"] = db.get_meeting(active_m.get('meeting_id'))
                                st.toast("Task added successfully!", icon="✅")
                                st.rerun()
                            else:
                                st.error("Please enter a task description.")
            else:
                st.info("No action items found in this meeting.")
        else:
            st.info("Upload audio in Tab 1 or click 'Load Sample Demo' to view summary and tasks.")

    # -----------------------------------------------------------------------------
    # TAB 3: PEOPLE & WORKLOAD
    # -----------------------------------------------------------------------------
    with tab_people:
        if active_m:
            st.subheader("👥 Meeting Participants & Workload Attribution")
            participants = active_m.get("participants", [])
            if not participants:
                participants = active_m.get("unique_participants", ["Narrator / Speaker"])

            col_p1, col_p2 = st.columns([1, 2])

            with col_p1:
                with st.container(border=True):
                    st.markdown("<h4 style='margin-top:0; color:#1E1B4B;'>Identified Speakers</h4>", unsafe_allow_html=True)
                    all_acts = active_m.get("action_items", [])
                    for person in participants:
                        p_acts = [a for a in all_acts if person.lower() in a.get("assignee", "").lower()]
                        st.markdown(
                            f"""
                            <div style="display: flex; justify-content: space-between; align-items: center; padding: 10px 0; border-bottom: 1px solid #E2E8F0;">
                                <span style="font-weight: 700; color: #1E1B4B;">👤 {person}</span>
                                <span class="badge-vibrant badge-indigo">{len(p_acts)} Tasks</span>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )

            with col_p2:
                with st.container(border=True):
                    st.markdown("<h4 style='margin-top:0; color:#1E1B4B;'>Assigned Tasks & Responsibilities</h4>", unsafe_allow_html=True)
                    if all_acts:
                        display_tasks = []
                        for a in all_acts:
                            display_tasks.append({
                                "Task": a.get("task"),
                                "Person": a.get("assignee"),
                                "Priority": a.get("priority"),
                                "Status": a.get("status")
                            })
                        st.dataframe(pd.DataFrame(display_tasks), width='stretch')
                    else:
                        st.caption("No tasks assigned yet.")
        else:
            st.info("Process an audio file to see participants.")

    # -----------------------------------------------------------------------------
    # TAB 4: TRANSCRIPT STUDIO
    # -----------------------------------------------------------------------------
    with tab_transcript:
        if active_m:
            full_text = active_m.get("transcript", "")
            duration_s = active_m.get("duration_seconds", 0.0)
            word_count = len(full_text.split())
            wpm_rate = round((word_count / (duration_s / 60))) if duration_s > 0 else 0

            # Numbers Row
            col_m1, col_m2, col_m3, col_m4 = st.columns(4)
            col_m1.metric("Word Count", word_count)
            col_m2.metric("Audio Duration", f"{duration_s:.1f}s")
            col_m3.metric("Speaking Rate", f"{wpm_rate} WPM")
            col_m4.metric("Language", active_m.get("language", "EN").upper())

            # Audio Player
            audio_name = active_m.get("audio_filename", "")
            if audio_name and os.path.exists(audio_name):
                with st.container(border=True):
                    st.markdown(f"🎧 **Audio Playback:** `{audio_name}`")
                    st.audio(audio_name)

            col_search, col_view = st.columns([3, 1])
            with col_search:
                search_query = st.text_input("🔍 Search within transcript:", placeholder="Type a keyword to filter segments...")
            with col_view:
                view_choice = st.radio("Display Mode:", ["Segments", "Plain Text"], horizontal=True)

            segments = active_m.get("segments", [])

            if view_choice == "Segments" and segments:
                filtered_segs = segments
                if search_query.strip():
                    filtered_segs = [s for s in segments if search_query.strip().lower() in s.get("text", "").lower()]
                    st.caption(f"Found **{len(filtered_segs)}** matching segments.")

                for s in filtered_segs:
                    st_time = s.get("start", 0.0)
                    end_time = s.get("end", 0.0)
                    seg_text = s.get("text", "").strip()

                    st.markdown(
                        f"""
                        <div style="background-color: #FFFFFF; border: 1px solid #E2E8F0; border-left: 4px solid #6366F1; border-radius: 8px; padding: 12px 16px; margin-bottom: 10px;">
                            <span class="timestamp-chip">⏱️ {st_time:05.2f}s - {end_time:05.2f}s</span>
                            <span style="color: #0F172A; font-size: 0.95rem;">{seg_text}</span>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
            else:
                st.text_area("Transcript Text:", value=full_text, height=280)

            # Export Buttons
            st.divider()
            st.markdown("#### 📥 Export Meeting Transcripts")
            col_d1, col_d2, col_d3 = st.columns(3)
            with col_d1:
                st.download_button("📄 Plain Text (.txt)", data=full_text, file_name=f"{active_m.get('meeting_id')}.txt", mime="text/plain")
            with col_d2:
                md_content = f"# Meeting Notes: {active_m.get('title')}\n\n## Summary\n{active_m.get('summary')}\n\n## Transcript\n{full_text}\n"
                st.download_button("📝 Executive Markdown (.md)", data=md_content, file_name=f"{active_m.get('meeting_id')}.md", mime="text/markdown")
            with col_d3:
                json_str = json.dumps({
                    "meeting_id": active_m.get("meeting_id"),
                    "title": active_m.get("title"),
                    "summary": active_m.get("summary"),
                    "transcript": full_text
                }, indent=2)
                st.download_button("💾 Structured JSON (.json)", data=json_str, file_name=f"{active_m.get('meeting_id')}.json", mime="application/json")
        else:
            st.info("Process an audio recording to view transcript.")

    # -----------------------------------------------------------------------------
    # TAB 5: SAVED MEETINGS REPOSITORY
    # -----------------------------------------------------------------------------
    with tab_saved:
        st.subheader("📁 Enterprise Meeting Knowledge Vault")
        st.caption("All transcribed meetings stored transactionally in SQLite database.")

        search_term_db = st.text_input("🔍 Search saved meetings:", placeholder="Search by title, speaker, keyword, or ID...")
    
        saved_list = db.search_meetings(search_term_db.strip()) if search_term_db.strip() else db.list_all_meetings()

        if saved_list:
            for m in saved_list:
                mid = m["meeting_id"]
                is_active_session = (active_m and active_m.get("meeting_id") == mid)

                with st.container(border=True):
                    col_head1, col_head2 = st.columns([3, 1.2])
                    with col_head1:
                        st.markdown(f"#### {m['title']}")
                    with col_head2:
                        current_badge = " :green[**● Current**]" if is_active_session else ""
                        st.markdown(f"`ID: {mid}` &nbsp; `Tasks: {m.get('action_count', 0)}`{current_badge}")

                    summary_text = m.get('summary') or 'No summary available.'
                    preview = summary_text[:220] + ("..." if len(summary_text) > 220 else "")
                    st.markdown(f"<p style='color: #475569; font-size: 0.92rem; margin: 4px 0 12px 0;'>{preview}</p>", unsafe_allow_html=True)

                    col_btn1, col_btn2 = st.columns([2, 1])
                    with col_btn1:
                        if st.button("📂 Open Meeting", key=f"open_{mid}"):
                            st.session_state["active_meeting_id"] = mid
                            st.session_state["active_meeting"] = db.get_meeting(mid)
                            st.toast(f"Opened '{m['title']}'!", icon="📂")
                            st.rerun()
                    with col_btn2:
                        if st.button("🗑️ Delete", key=f"del_{mid}"):
                            db.delete_meeting(mid)
                            st.toast("Meeting removed.", icon="🗑️")
                            if st.session_state.get("active_meeting_id") == mid:
                                rem = db.list_all_meetings()
                                if rem:
                                    st.session_state["active_meeting_id"] = rem[0]["meeting_id"]
                                    st.session_state["active_meeting"] = db.get_meeting(rem[0]["meeting_id"])
                                else:
                                    st.session_state["active_meeting_id"] = None
                                    st.session_state["active_meeting"] = None
                            st.rerun()

                    # Expandable Meeting History & Full Record
                    with st.expander("📖 View Meeting History & Full Notes", expanded=is_active_session):
                        detail_m = db.get_meeting(mid)
                        if detail_m:
                            if is_active_session:
                                st.success("✅ **Currently Active Meeting:** Loaded into **Summary & Tasks**, **People**, and **Transcript** tabs at the top.")

                            st.markdown("**Executive Summary:**")
                            st.info(detail_m.get("summary") or "No summary available.")

                            col_dh1, col_dh2 = st.columns(2)
                            with col_dh1:
                                st.markdown("**📌 Key Discussion Points:**")
                                kp = detail_m.get("key_points", [])
                                if kp:
                                    for p in kp:
                                        st.markdown(f"&bull; {p}")
                                else:
                                    st.caption("No key points logged.")

                            with col_dh2:
                                st.markdown("**✅ Strategic Decisions:**")
                                decs = detail_m.get("decisions", [])
                                if decs:
                                    for d in decs:
                                        st.markdown(f"&bull; {d}")
                                else:
                                    st.caption("No decisions logged.")

                            # Action items with status update right in Tab 5
                            m_actions = detail_m.get("action_items", [])
                            if m_actions:
                                st.markdown("**🎯 Tasks & Follow-ups:**")
                                for act in m_actions:
                                    c_a1, c_a2 = st.columns([3, 1.5])
                                    with c_a1:
                                        st.markdown(f"&bull; **{act['task']}** ({act['assignee']})")
                                        st.caption(f"Deadline: {act['deadline']} | Priority: {act['priority']}")
                                    with c_a2:
                                        act_id = act.get('id')
                                        cur_stat = act.get('status', 'Pending')
                                        new_stat = st.selectbox(
                                            "Status",
                                            ["Pending", "In Progress", "Completed"],
                                            index=["Pending", "In Progress", "Completed"].index(cur_stat) if cur_stat in ["Pending", "In Progress", "Completed"] else 0,
                                            key=f"tab5_st_{mid}_{act_id}",
                                            label_visibility="collapsed"
                                        )
                                        if new_stat != cur_stat:
                                            db.update_action_item_status(act_id, new_stat)
                                            act['status'] = new_stat
                                            st.toast(f"Task updated to '{new_stat}'!", icon="✅")
                                            st.rerun()

                            # Transcript
                            t_text = detail_m.get("transcript", "")
                            if t_text:
                                st.markdown("**📝 Full Transcript Text:**")
                                st.text_area("Full Transcript", value=t_text, height=200, key=f"t_view_{mid}", disabled=True, label_visibility="collapsed")
        else:
            st.info("No saved meetings found.")


# -----------------------------------------------------------------------------
# 6. ACCURACY CHECKER STUDIO
# -----------------------------------------------------------------------------
elif app_section == "🎯 Accuracy Checker":
    st.markdown(
        """
        <div class="colorful-header" style="background: linear-gradient(135deg, #065F46 0%, #059669 40%, #10B981 75%, #3B82F6 100%);">
            <h1 style="margin: 0; font-size: 2rem; font-weight: 800; letter-spacing: -0.02em;">
                🎯 Accuracy & Word Error Rate (WER) Checker
            </h1>
            <p style="margin: 6px 0 0 0; font-size: 0.95rem; opacity: 0.95;">
                Check how accurately Whisper AI transcribed your audio compared to what was actually spoken.
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

    col_acc_in1, col_acc_in2 = st.columns([1.15, 1.85])

    default_gt = "Today's meeting date is 27th August and day is Thursday and the time is 6.45 pm."

    with col_acc_in1:
        with st.container(border=True):
            st.markdown("<h4 style='margin-top:0; color:#1E1B4B;'>⚙️ 1. Choose What to Test</h4>", unsafe_allow_html=True)
            source_type = st.radio(
                "Pick an Audio or Text Source:",
                [
                    "🎵 Test Sample Audio (transcipt_test2.mp3)",
                    "📁 Test a Saved Meeting",
                    "🎙️ Upload Audio File",
                    "📝 Type or Paste Text Manually"
                ],
                index=0
            )

            audio_file_for_test = None
            preset_hypothesis = ""

            if source_type == "🎵 Test Sample Audio (transcipt_test2.mp3)":
                audio_file_for_test = "transcipt_test2.mp3"
                if os.path.exists("transcipt_test2.mp3"):
                    st.audio("transcipt_test2.mp3")
                st.caption("Using built-in recording (~8.0s).")

            elif source_type == "📁 Test a Saved Meeting":
                if all_meetings:
                    chosen_m_id = st.selectbox(
                        "Select Saved Meeting",
                        options=[m["meeting_id"] for m in all_meetings],
                        format_func=lambda x: f"{next((m['title'] for m in all_meetings if m['meeting_id'] == x), x)} ({x})"
                    )
                    meeting_data = db.get_meeting(chosen_m_id)
                    if meeting_data:
                        preset_hypothesis = meeting_data.get("transcript", "")
                        st.caption(f"Loaded meeting with {len(preset_hypothesis.split())} words.")
                else:
                    st.warning("No saved meetings found.")

            elif source_type == "🎙️ Upload Audio File":
                uploaded_test_file = st.file_uploader(
                    "Upload Audio for Accuracy Test",
                    type=["mp3", "wav", "m4a", "mp4", "ogg", "flac", "aac"],
                    key="acc_audio_uploader"
                )
                if uploaded_test_file:
                    st.audio(uploaded_test_file)
                    st.caption(f"Ready to evaluate `{uploaded_test_file.name}`.")
            else:
                uploaded_test_file = None

            whisper_model_eval = st.selectbox(
                "Whisper Model:",
                ["base", "tiny", "small", "medium"],
                index=0,
                help="Model size used if live Whisper transcription is executed."
            )

    with col_acc_in2:
        with st.container(border=True):
            st.markdown("<h4 style='margin-top:0; color:#1E1B4B;'>📝 2. Compare Expected Words vs Transcribed Words</h4>", unsafe_allow_html=True)
            
            # Ground truth determination
            curr_gt = st.session_state.get("ground_truth", default_gt)
            if source_type == "📁 Test a Saved Meeting" and preset_hypothesis and not st.session_state.get("ground_truth_custom"):
                curr_gt = preset_hypothesis

            ground_truth_input = st.text_area(
                "Expected Words (Ground Truth — What was actually spoken):",
                value=curr_gt,
                height=120,
                help="The true words spoken in the audio. Used as the gold standard."
            )

            custom_hypothesis_input = ""
            if source_type == "📝 Type or Paste Text Manually":
                custom_hypothesis_input = st.text_area(
                    "Transcribed Words (Hypothesis — What AI heard):",
                    value=st.session_state.get("hypothesis_text_custom", default_gt),
                    height=120,
                    placeholder="Paste or type transcribed words here to compare..."
                )
            elif preset_hypothesis:
                st.markdown("**🤖 Transcribed Words from Saved Meeting (Hypothesis):**")
                custom_hypothesis_input = st.text_area(
                    "Transcribed Words from Saved Meeting",
                    value=preset_hypothesis,
                    height=130,
                    help="Loaded from your saved meeting. You can also edit this text to test corrections.",
                    key=f"saved_hyp_{chosen_m_id}"
                )

            col_btn_run, col_btn_reset = st.columns([2, 1])
            with col_btn_run:
                run_acc_calc = st.button("🚀 Test Accuracy Now")
            with col_btn_reset:
                if st.button("🔄 Clear Results"):
                    st.session_state.pop("acc_eval_result", None)
                    st.rerun()

    # Calculation logic
    if run_acc_calc:
        if not ground_truth_input.strip():
            st.error("Please enter the Expected Words (Ground Truth).")
        else:
            hyp_text = ""
            error_occurred = False

            with st.spinner("Processing speech and calculating accuracy metrics..."):
                if source_type == "📝 Type or Paste Text Manually":
                    hyp_text = custom_hypothesis_input.strip()
                    if not hyp_text:
                        st.error("Please provide the Transcribed Hypothesis Text to compare.")
                        error_occurred = True
                elif source_type == "📁 Test a Saved Meeting":
                    hyp_text = (custom_hypothesis_input or preset_hypothesis).strip()
                    if not hyp_text:
                        st.error("The selected meeting has an empty transcript.")
                        error_occurred = True
                elif source_type == "🎵 Test Sample Audio (transcipt_test2.mp3)":
                    if os.path.exists("transcipt_test2.mp3"):
                        try:
                            model = whisper.load_model(whisper_model_eval)
                            res = model.transcribe("transcipt_test2.mp3")
                            hyp_text = res.get("text", "").strip()
                        except Exception as e:
                            st.error(f"Whisper transcription failed: {e}")
                            error_occurred = True
                    else:
                        st.error("Built-in transcipt_test2.mp3 was not found.")
                        error_occurred = True
                elif source_type == "🎙️ Upload Audio File":
                    if uploaded_test_file is not None:
                        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded_test_file.name)[1]) as tf:
                            tf.write(uploaded_test_file.read())
                            tmp_test_path = tf.name
                        try:
                            model = whisper.load_model(whisper_model_eval)
                            res = model.transcribe(tmp_test_path)
                            hyp_text = res.get("text", "").strip()
                        except Exception as e:
                            st.error(f"Whisper transcription failed: {e}")
                            error_occurred = True
                        finally:
                            if os.path.exists(tmp_test_path):
                                os.remove(tmp_test_path)
                    else:
                        st.error("Please select an audio file to upload.")
                        error_occurred = True

                if hyp_text and not error_occurred:
                    transformation = jiwer.Compose([
                        jiwer.ToLowerCase(),
                        jiwer.RemovePunctuation(),
                        jiwer.RemoveMultipleSpaces(),
                        jiwer.Strip()
                    ])
                    ref_clean = transformation(ground_truth_input.strip())
                    hyp_clean = transformation(hyp_text)

                    out = jiwer.process_words(ref_clean, hyp_clean)
                    wer = out.wer
                    acc = max(0.0, (1.0 - wer) * 100.0)
                    alignment_txt = jiwer.visualize_alignment(out)

                    st.session_state["acc_eval_result"] = {
                        "ground_truth": ground_truth_input.strip(),
                        "hypothesis": hyp_text,
                        "ref_clean": ref_clean,
                        "hyp_clean": hyp_clean,
                        "wer": wer,
                        "accuracy": acc,
                        "hits": out.hits,
                        "substitutions": out.substitutions,
                        "deletions": out.deletions,
                        "insertions": out.insertions,
                        "total_words": len(ref_clean.split()) if ref_clean else 0,
                        "alignment": alignment_txt
                    }
                    if acc >= 90.0:
                        st.balloons()
                    st.toast("Accuracy evaluation complete!", icon="🎯")

    # Render results
    eval_res = st.session_state.get("acc_eval_result")
    if eval_res:
        acc_val = eval_res["accuracy"]
        wer_val = eval_res["wer"]
        passed = acc_val >= 90.0

        st.divider()

        # Benchmark Passed / Warning Alert Banner
        if passed:
            st.markdown(
                f"""
                <div class="colorful-card" style="border-left: 6px solid #10B981; background: #ECFDF5; border-color: #A7F3D0;">
                    <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px;">
                        <div>
                            <h3 style="margin: 0; color: #065F46;">🎉 Accuracy Benchmark Passed (≥ 90%)</h3>
                            <p style="margin: 4px 0 0 0; color: #047857; font-size: 0.95rem;">
                                Model achieved <b>{acc_val:.2f}%</b> transcription accuracy, meeting the required production threshold.
                            </p>
                        </div>
                        <span class="badge-vibrant badge-emerald" style="font-size: 1rem; padding: 6px 16px;">
                            PASSED &bull; {acc_val:.1f}%
                        </span>
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )
        else:
            st.markdown(
                f"""
                <div class="colorful-card" style="border-left: 6px solid #F43F5E; background: #FFF1F2; border-color: #FECDD3;">
                    <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px;">
                        <div>
                            <h3 style="margin: 0; color: #9F1239;">⚠️ Accuracy Fell Below 90% Target</h3>
                            <p style="margin: 4px 0 0 0; color: #BE123C; font-size: 0.95rem;">
                                Model achieved <b>{acc_val:.2f}%</b> accuracy with <b>{wer_val * 100:.2f}%</b> Word Error Rate.
                            </p>
                        </div>
                        <span class="badge-vibrant badge-rose" style="font-size: 1rem; padding: 6px 16px;">
                            NEEDS REVIEW &bull; {acc_val:.1f}%
                        </span>
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

        # 4 KPI Metrics
        col_km1, col_km2, col_km3, col_km4 = st.columns(4)
        col_km1.metric("Word Accuracy", f"{acc_val:.2f}%", delta=f"{acc_val - 90.0:+.2f}% vs 90% Target")
        col_km2.metric("Word Error Rate (WER)", f"{wer_val * 100:.2f}%")
        col_km3.metric("Total Words Spoken", eval_res["total_words"])
        col_km4.metric("Correct Words", f"{eval_res['hits']} / {eval_res['total_words']}")

        # Stacked Accuracy Bar
        total_ops = max(1, eval_res['hits'] + eval_res['substitutions'] + eval_res['deletions'] + eval_res['insertions'])
        pct_hits = (eval_res['hits'] / total_ops) * 100
        pct_subs = (eval_res['substitutions'] / total_ops) * 100
        pct_dels = (eval_res['deletions'] / total_ops) * 100
        pct_ins = (eval_res['insertions'] / total_ops) * 100

        st.markdown(
            f"""
            <div style="margin-top: 12px; margin-bottom: 20px;">
                <div style="display: flex; justify-content: space-between; font-size: 0.82rem; font-weight: 700; color: #475569; margin-bottom: 6px;">
                    <span>ACCURACY & MISTAKE BREAKDOWN</span>
                    <span>Correct: {pct_hits:.1f}% | Mistakes: {(100.0 - pct_hits):.1f}%</span>
                </div>
                <div class="acc-bar-container">
                    <div class="acc-seg-hits" style="width: {pct_hits}%;" title="Hits: {eval_res['hits']}"></div>
                    <div class="acc-seg-subs" style="width: {pct_subs}%;" title="Substitutions: {eval_res['substitutions']}"></div>
                    <div class="acc-seg-dels" style="width: {pct_dels}%;" title="Deletions: {eval_res['deletions']}"></div>
                    <div class="acc-seg-ins" style="width: {pct_ins}%;" title="Insertions: {eval_res['insertions']}"></div>
                </div>
                <div style="display: flex; gap: 18px; font-size: 0.82rem; font-weight: 600; flex-wrap: wrap;">
                    <span style="color: #059669;">🟢 Correct Words: <b>{eval_res['hits']}</b> ({pct_hits:.1f}%)</span>
                    <span style="color: #D97706;">🟡 Wrong Words (Substituted): <b>{eval_res['substitutions']}</b> ({pct_subs:.1f}%)</span>
                    <span style="color: #E11D48;">🔴 Missed Words (Deleted): <b>{eval_res['deletions']}</b> ({pct_dels:.1f}%)</span>
                    <span style="color: #4F46E5;">🔵 Extra Words (Inserted): <b>{eval_res['insertions']}</b> ({pct_ins:.1f}%)</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

        # Side by Side Comparison
        st.markdown("<h4 style='margin-top: 20px; color: #1E1B4B;'>🔍 Side-by-Side Comparison</h4>", unsafe_allow_html=True)
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            with st.container(border=True):
                st.markdown("<span class='badge-vibrant badge-emerald'>Expected Words (Ground Truth)</span>", unsafe_allow_html=True)
                st.markdown(f"<div style='margin-top:8px; font-size: 0.95rem; color: #1E293B;'>{eval_res['ground_truth']}</div>", unsafe_allow_html=True)
                st.caption(f"Normalized: `{eval_res['ref_clean']}`")
        with col_c2:
            with st.container(border=True):
                st.markdown("<span class='badge-vibrant badge-indigo'>Transcribed Words (Hypothesis)</span>", unsafe_allow_html=True)
                st.markdown(f"<div style='margin-top:8px; font-size: 0.95rem; color: #1E293B;'>{eval_res['hypothesis']}</div>", unsafe_allow_html=True)
                st.caption(f"Normalized: `{eval_res['hyp_clean']}`")

        # Alignment Visualization Box
        st.markdown("<h4 style='margin-top: 20px; color: #1E1B4B;'>🔬 Word-by-Word Mistake Breakdown</h4>", unsafe_allow_html=True)
        st.caption("Shows each word side-by-side. Error flags: **S** = Word was replaced, **D** = Word was missed, **I** = Extra word was added:")
        st.code(eval_res['alignment'], language="text")
