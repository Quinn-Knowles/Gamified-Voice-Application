import sounddevice as sd
import numpy as np
import librosa

def pitch_from_audio(frame, sr, fmin=75.0, fmax=400.0):
    """
    Estimate pitch using librosa.yin with typical human speech range.
    Adjust fmin/fmax for gender-specific tuning.
    """
    # Frame length for analysis (in samples)
    frame_length = 2048
    hop_length = 256

    # Pad if too short
    if len(frame) < frame_length:
        frame = np.pad(frame, (0, frame_length - len(frame)), mode='constant')

    # librosa.yin works over multiple frames
    f0_series = librosa.yin(frame,
                            fmin=fmin,
                            fmax=fmax,
                            sr=sr,
                            frame_length=frame_length,
                            hop_length=hop_length)
    # Filter out unvoiced (NaN or 0) and return median
    f0_series = f0_series[~np.isnan(f0_series)]
    f0_series = f0_series[f0_series > 0]
    return float(np.median(f0_series)) if len(f0_series) else 0.0

def is_audio_present(indata, threshold=0.01):
    """Simple energy threshold detection."""
    return np.abs(indata).mean() > threshold

def monitor_audio():
    samplerate = 22050
    blocksize = samplerate  # ~1 second

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
