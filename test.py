import sounddevice as sd
import numpy as np
import librosa

def pitch_from_audio(frame, sr):
    """Estimate pitch using librosa.yin like in Monitor.py."""
    f0 = librosa.yin(frame, fmin=librosa.note_to_hz('C2'),
                     fmax=librosa.note_to_hz('C7'), sr=sr)
    f0 = f0[~np.isnan(f0)]
    return float(np.median(f0)) if len(f0) else 0.0

def is_audio_present(indata, threshold=0.01):
    """Simple energy threshold detection."""
    return np.abs(indata).mean() > threshold

def monitor_audio():
    samplerate = 22050
    blocksize = samplerate  # 1 second blocks

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
                    print("Heard — Pitch not detected")
            else:
                print("silence")

if __name__ == "__main__":
    try:
        monitor_audio()
    except KeyboardInterrupt:
        print("\nStopped by user")
    except Exception as e:
        print(f"Error: {e}")
