import sounddevice as sd
import numpy as np
import parselmouth

def pitch_from_audio(frame, sr):
    # Parselmouth wants shape (num_channels, num_samples)
    # Our audio is 1D already, so reshape to mono channel explicitly
    frame = np.asarray(frame, dtype=np.float64).reshape(1, -1)

    snd = parselmouth.Sound(values=frame, sampling_frequency=sr)
    pitch = snd.to_pitch(time_step=0.01, pitch_floor=75, pitch_ceiling=400)  # Human range
    values = pitch.selected_array['frequency']
    values = values[values > 0]
    return float(np.median(values)) if len(values) else 0.0

def is_audio_present(indata, threshold=0.01):
    return np.abs(indata).mean() > threshold

def monitor_audio():
    samplerate = 22050
    blocksize = samplerate  # 1 sec

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
