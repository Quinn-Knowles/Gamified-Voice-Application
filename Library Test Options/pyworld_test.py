import sounddevice as sd
import numpy as np
import pyworld as pw

def pitch_from_audio(frame, sr):
    frame = frame.astype(np.float64)
    _f0, t = pw.harvest(frame, sr, f0_floor=75.0, f0_ceil=1000.0)
    f0 = _f0[_f0 > 0]
    return float(np.median(f0)) if len(f0) else 0.0

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
                    print("Heard — Pitch not detected")
            else:
                print("silence")

if __name__ == "__main__":
    try:
        monitor_audio()
    except KeyboardInterrupt:
        print("\nStopped by user")
