import sounddevice as sd
import numpy as np
import crepe
import librosa

CONFIDENCE_THRESHOLD = 0.5
MIN_VOICE_HZ = 75
MAX_VOICE_HZ = 350

def pitch_from_audio(frame, sr):
    # Resample if needed
    if sr != 16000:
        frame = librosa.resample(frame, orig_sr=sr, target_sr=16000)
        sr = 16000

    frame = np.expand_dims(frame, axis=0).astype(np.float32)
    _, frequency, confidence, _ = crepe.predict(frame, sr, viterbi=True)

    # Filter by confidence and voice range
    valid_freqs = frequency[
        (confidence > CONFIDENCE_THRESHOLD) &
        (frequency >= MIN_VOICE_HZ) &
        (frequency <= MAX_VOICE_HZ)
    ]
    
    if len(valid_freqs) > 0:
        return float(np.median(valid_freqs))
    else:
        return 0.0

def is_audio_present(indata, threshold=0.01):
    return np.abs(indata).mean() > threshold

def monitor_audio():
    samplerate = 22050
    blocksize = samplerate

    print("Opening microphone stream...")
    with sd.InputStream(channels=1, samplerate=samplerate, blocksize=blocksize) as stream:
        print("Listening... Press Ctrl+C to stop.")
        while True:
            audio_block, overflowed = stream.read(blocksize)
            audio = audio_block[:, 0]

            if is_audio_present(audio):
                pitch = pitch_from_audio(audio, samplerate)
                if pitch > 0:
                    print(f"Heard — Pitch: {pitch:.1f} Hz")
                else:
                    print("Heard — Pitch not detected (low confidence or out of range)")
            else:
                print("silence")

if __name__ == "__main__":
    try:
        monitor_audio()
    except KeyboardInterrupt:
        print("\nStopped by user")
