import streamlit as st
import socketio
import speech_recognition as sr
from queue import Queue
from threading import Thread
from pydub import AudioSegment
from pydub.silence import detect_nonsilent

# SocketIO client
sio = socketio.Client()
sio.connect('https://3648-194-87-199-27.ngrok-free.app')  # Replace with your server URL

# Audio queue
audio_queue = Queue()
transcribed_text = ""

# Global variable for controlling threads
stop_threads = False

# Initialize session state variables
if "recording" not in st.session_state:
    st.session_state.recording = False

@sio.on('translated_audio')
def on_translated_audio(data):
    global transcribed_text
    transcribed_text = data['text']
    print(transcribed_text)

def send_audio_chunks(language='th'):
    global stop_threads
    while not stop_threads:
        audio_chunk = audio_queue.get()
        if audio_chunk is None:
            break
        print('Audio Detected and sending ...')
        sio.emit('audio_chunk', {'audio_bytes': audio_chunk, 'language': language})

def capture_audio():
    global stop_threads
    r = sr.Recognizer()
    with sr.Microphone() as source:
        r.adjust_for_ambient_noise(source)
        while not stop_threads:
            try:
                r.pause_threshold = 1
                audio = r.listen(source)
                audio_data = audio.get_wav_data()
                audio_segment = AudioSegment(data=audio_data, sample_width=2, frame_rate=16000, channels=1)
                nonsilent_ranges = detect_nonsilent(audio_segment, min_silence_len=500, silence_thresh=-30)
                if nonsilent_ranges:
                    audio_queue.put(audio_data)
            except sr.WaitTimeoutError:
                pass

def start_recording():
    global stop_threads
    stop_threads = False
    sio.emit('start_recording')
    st.session_state.recording = True

def stop_recording():
    global stop_threads
    stop_threads = True
    st.session_state.recording = False
    audio_queue.put(None)  # Signal sender thread to stop

def main():
    st.title("Speaker Page")
    st.write("This page allows you to record and send audio for translation.")
    language = st.selectbox("Select Target Language", options=['th', 'es', 'fr', 'de', 'ja'], index=0)

    # UI Message Placeholder
    message_placeholder = st.empty()

    # Start Recording Button
    if st.button("Start Recording"):
        if not st.session_state.recording:  # Start only if not already recording
            start_recording()
            message_placeholder.text("Recording... Speak into the microphone.")
            sender_thread = Thread(target=send_audio_chunks, args=(language,), daemon=True)
            sender_thread.start()
            audio_thread = Thread(target=capture_audio, daemon=True)
            audio_thread.start()

    # Stop Recording Button
    if st.button("Stop Recording"):
        if st.session_state.recording:  # Stop only if currently recording
            stop_recording()
            message_placeholder.text("Recording stopped.")

if __name__ == "__main__":
    main()
