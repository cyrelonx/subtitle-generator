import streamlit as st
from faster_whisper import WhisperModel
import subprocess
import os
import av

# Monkey-patch for PyAV / faster-whisper compatibility
_original_open = av.open
av.open = lambda *args, **kwargs: kwargs.pop('metadata_errors', None) and _original_open(*args, **kwargs) or _original_open(*args, **kwargs)

st.set_page_config(page_title="AI Subtitle Generator", page_icon="🎬", layout="centered")

st.title("🎬 AI Subtitle Generator for TikTok/Reels")
st.write("Upload your video and automatically generate stylish animated subtitles for free!")

# --- SIDEBAR OPTIONS FOR FONT SIZE & COLOR ---
st.sidebar.header("Subtitle Settings")

# Font size option
font_size = st.sidebar.slider("Font Size", min_value=40, max_value=100, value=65, step=5)

# Color selection option
color_option = st.sidebar.selectbox(
    "Subtitle Color",
    ["Yellow", "White", "Green", "Cyan", "Orange"]
)

# Map human-readable colors to ASS color codes (&HBBGGRR format in hex)
color_map = {
    "Yellow": "&H0000FFFF",  # B=00, G=FF, R=FF
    "White": "&H00FFFFFF",   # B=FF, G=FF, R=FF
    "Green": "&H0000FF00",   # B=00, G=FF, R=00
    "Cyan": "&H00FFFF00",    # B=FF, G=FF, R=00
    "Orange": "&H000080FF"   # B=00, G=80, R=FF
}
selected_color_code = color_map[color_option]

# --- MAIN FILE UPLOADER ---
uploaded_file = st.file_uploader("Choose an MP4 video file", type=["mp4", "mov"])

if uploaded_file is not None:
    with open("input_video.mp4", "wb") as f:
        f.write(uploaded_file.read())
    
    st.video("input_video.mp4")
    
    if st.button("🚀 Generate Subtitles"):
        with st.spinner("1/4 Checking video duration and analyzing speech (Whisper AI)..."):
            container = av.open("input_video.mp4")
            duration_seconds = float(container.duration) / av.time_base
            container.close()

            needs_watermark = duration_seconds > 15

            if needs_watermark:
                st.info(f"ℹ️ Video duration is {int(duration_seconds)}s (>15s). Creator watermark will be added.")
            else:
                st.success(f"⚡ Video duration is {int(duration_seconds)}s (<=15s). No watermark added!")

            model = WhisperModel("base", compute_type="int8")
            segments, info = model.transcribe("input_video.mp4", word_timestamps=True)
            
        with st.spinner("2/4 Creating ASS subtitle file..."):
            # Inject dynamic font size and color into ASS style
            ass_content = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, OutlineColour, BackColour, Bold, Alignment, MarginV, Outline, Shadow
Style: TikTokStyle, Impact, {font_size}, {selected_color_code}, &H00000000, &H80000000, 1, 2, 450, 4, 2

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
            def format_time(seconds):
                hrs = int(seconds // 3600)
                mins = int((seconds % 3600) // 60)
                secs = int(seconds % 60)
                centisecs = int((seconds - int(seconds)) * 100)
                return f"{hrs:01d}:{mins:02d}:{secs:02d}.{centisecs:02d}"

            for segment in segments:
                for word in segment.words:
                    start = format_time(word.start)
                    end = format_time(word.end)
                    text = word.word.strip().upper()
                    # Apply the chosen color tag directly to each word
                    ass_content += f"Dialogue: 0,{start},{end},TikTokStyle,,0,0,0,,{{\\c{selected_color_code}}}{text}\n"

            with open("subtitles.ass", "w", encoding="utf-8") as f:
                f.write(ass_content)

        with st.spinner("3/4 Burning subtitles and applying effects (FFmpeg)..."):
            video_filter = "ass=subtitles.ass"

            if needs_watermark:
                watermark_text = "Generated with SubAI • By Cyrelonx"
                
                drawtext_filter = (
                    f"drawtext=text='{watermark_text}':"
                    f"x=w-tw-40:y=40:"
                    f"fontsize=32:fontcolor=white@0.85:"
                    f"bordercolor=black:borderw=2"
                )
                video_filter = f"{video_filter},{drawtext_filter}"

            cmd = f'ffmpeg -y -i input_video.mp4 -vf "{video_filter}" -c:a copy output_video.mp4'
            subprocess.run(cmd, shell=True)

        st.success("✅ Done!")
        st.video("output_video.mp4")
        
        with open("output_video.mp4", "rb") as file:
            st.download_button(
                label="📥 Download Processed Video",
                data=file,
                file_name="video_with_subtitles.mp4",
                mime="video/mp4"
            )