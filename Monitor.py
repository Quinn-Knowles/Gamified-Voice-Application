# Monitor.py

import argparse
import sounddevice as sd
import numpy as np
import librosa
import threading
import time
import simpleaudio as sa

def play_sound(path):
    wave_obj = sa.WaveObject.from_wave_file(path)
    wave_obj.play()

def pitch_from_audio(frame, sr):
    # Use librosa.yin to estimate fundamental frequency
    f0 = librosa.yin(frame, fmin=librosa.note_to_hz('C2'),
                     fmax=librosa.note_to_hz('C7'), sr=sr)
    # yin returns an array over hops; take median non‑nan
    f0 = f0[~np.isnan(f0)]
    return float(np.median(f0)) if len(f0) else 0.0

def resonance_from_audio(frame, sr):
    # A crude proxy: use spectral centroid (higher = brighter/“more resonant”)
    centroid = librosa.feature.spectral_centroid(y=frame, sr=sr)
    return float(np.mean(centroid))

def monitor_loop(args):
    sr = 22050
    block_len = 1.0  # seconds
    block_size = int(block_len * sr)

    in_range_time = 0.0
    total_time = 0.0
    streak = 0.0

    def callback(indata, frames, time_info, status):
        nonlocal in_range_time, total_time, streak
        audio = indata[:, 0]
        p = pitch_from_audio(audio, sr)

        # Print detected pitch every time
        if p > 0:
            print(f"Detected pitch: {p:.1f} Hz")
        else:
            print("No pitch detected")

        # Out-of-range logic
        if args.min <= p <= args.max:
            in_range_time += block_len
            streak += block_len
        else:
            streak = 0
            if args.out_of_range:
                play_sound("error.wav")
            if args.self_mute:
                print("[MUTED]")

        total_time += block_len

        # Print current score every time
        if total_time > 0:
            percent = (in_range_time / total_time) * 100
            print(f"Current in-range score: {percent:.1f}%")

        # Sentence monitor
        if args.sentence_monitor:
            energy = np.mean(audio ** 2)
            if energy < 1e-4 and streak > 1.0:
                play_sound("pin-pon.wav")

        # Resonance monitor
        if args.resonance:
            r = resonance_from_audio(audio, sr)
            print(f"Resonance (centroid): {r:.1f} Hz")

        # Periodic file update every minute
        if args.score and total_time >= 60.0 and total_time % 60 < block_len:
            with open("score.txt", "w") as f:
                f.write(f"{percent:.1f}% in range\n")

    # Start streaming
    with sd.InputStream(channels=1, samplerate=sr, blocksize=block_size, callback=callback):
        print("=== Monitoring started — press Ctrl+C to stop ===")
        try:
            while True:
                time.sleep(0.1)
        except KeyboardInterrupt:
            print("\n=== Monitoring stopped ===")
            if args.score:
                final_pct = (in_range_time / total_time) * 100
                print(f"Final score: {final_pct:.1f}% in range")

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--max",   type=int, required=True, help="Maximum pitch")
    p.add_argument("--min",   type=int, required=True, help="Minimum pitch")
    p.add_argument("--sentence-monitor", action="store_true",
                   help="Play pin-pon at end of sentences")
    p.add_argument("--out-of-range", action="store_true",
                   help="Play error sound when outside range")
    p.add_argument("--self-mute", action="store_true",
                   help="Mute mic when outside range (stub)")
    p.add_argument("--resonance", action="store_true",
                   help="Print resonance (spectral centroid)")
    p.add_argument("--score", action="store_true",
                   help="Write percent-in-range to score.txt every minute")
    args = p.parse_args()

    print("Running with:", args)
    monitor_loop(args)

if __name__=="__main__":
    main()