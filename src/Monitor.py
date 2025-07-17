import argparse
import sounddevice as sd
import numpy as np
import parselmouth
import librosa
import pygame
import threading
import time

SOUNDS = {
    "error": None,
    "pinpon": None
}

# ================================
# Parselmouth-based pitch
# ================================

def pitch_from_audio(frame, sr):
    """
    Estimate pitch using parselmouth.
    Filters to human voice range 75–400 Hz.
    """
    frame = np.asarray(frame, dtype=np.float64)
    if not np.any(np.isfinite(frame)) or not np.any(frame):
        print("[WARN] Skipping pitch analysis: frame is empty or invalid")
        return 0.0
    
    frame = np.asarray(frame, dtype=np.float64).reshape(1, -1)
    snd = parselmouth.Sound(values=frame, sampling_frequency=sr)
    pitch = snd.to_pitch(time_step=0.01, pitch_floor=75, pitch_ceiling=400)
    values = pitch.selected_array['frequency']
    values = values[values > 0]
    return float(np.median(values)) if len(values) else 0.0



def is_audio_present(indata, threshold=0.01):
    return np.abs(indata).mean() > threshold

def play_sound_threaded(sound_key):
    def _play():
        sound = SOUNDS.get(sound_key)
        if sound:
            sound.play()
    threading.Thread(target=_play, daemon=True).start()
    
# ================================
# Parselmouth monitor
# ================================
    
def parse_sample(args, audio, samplerate, trackers):
    pitch = pitch_from_audio(audio, samplerate)
    energy = np.mean(audio ** 2)
    
    if pitch > 0:
        print(f"Detected pitch: {pitch:.1f} Hz")
    else:
        print("No pitch detected")

    current_time = time.time()
    # Check pitch range
    if args.min <= pitch <= args.max:
        trackers["in_range_time"] += 1.0
        trackers["streak"] += 1.0
    else:
        trackers["streak"] = 0
        if args.out_of_range:
            last_error = trackers.get("last_error_time", 0)
            if current_time - last_error > 4:
                play_sound_threaded("error")
                trackers["last_error_time"] = current_time
        if args.self_mute:
            print("[MUTED]")

    trackers["total_time"] += 1.0

    # In-range percentage
    if trackers["total_time"] > 0:
        percent = (trackers["in_range_time"] / trackers["total_time"]) * 100
        print(f"In-range score: {percent:.1f}%")

    # Sentence end detector
    if args.sentence_monitor:
        if energy < 1e-4 and trackers["streak"] > 1.0:
            play_sound_threaded("pinpon")

    # Resonance display
    if args.resonance:
        r = resonance_from_audio(audio, samplerate)
        print(f"Resonance (centroid): {r:.1f} Hz")

    # Write score file every 60 seconds
    if args.score and trackers["total_time"] >= 60 and trackers["total_time"] % 60 < 1:
        with open("score.txt", "w") as f:
            f.write(f"{percent:.1f}% in range\n")
            
            
def load_sounds():
    try:
        pygame.mixer.init()
        SOUNDS["error"] = pygame.mixer.Sound("src/error.wav")
        SOUNDS["pinpon"] = pygame.mixer.Sound("src/pin-pon.wav")
    except Exception as e:
        print(f"[ERROR] Failed to load sound: {e}")

def monitor_loop(args):
    samplerate = 22050
    block_len = 1.0
    block_size = int(block_len * samplerate)

    trackers = {
        "in_range_time": 0.0,
        "total_time": 0.0,
        "streak": 0.0,
        "last_error_time": 0.0
    }
    with sd.InputStream(channels=1, samplerate=samplerate, blocksize=block_size) as stream:
        print("=== Listening ===")
        try:
            while True:
                audio_block, overflowed = stream.read(block_size)
                if overflowed:
                    print("[WARN] Audio buffer overflowed")
                audio = audio_block[:, 0]

                if is_audio_present(audio):
                    print("Heard")
                    try:
                        parse_sample(args, audio, samplerate, trackers)
                    except Exception as e:
                        print(f"[ERROR] Sample parse failed: {e}")
                else:
                    print("silence " + str(trackers))

        except KeyboardInterrupt:
            print("\n=== Monitoring stopped ===")
            if args.score and trackers["total_time"] > 0:
                final_pct = (trackers["in_range_time"] / trackers["total_time"]) * 100
                print(f"Final score: {final_pct:.1f}% in range")
        except Exception as e:
            print(f"\n[FATAL ERROR] {e}")


# ================================
# UNUSED legacy functions (librosa)
# ================================

def legacy_pitch_from_audio(frame, sr):
    """
    Legacy version: librosa.yin pitch estimation.
    Not used in the main monitor_loop().
    """
    f0 = librosa.yin(frame,
                     fmin=librosa.note_to_hz('C2'),
                     fmax=librosa.note_to_hz('C7'),
                     sr=sr)
    f0 = f0[~np.isnan(f0)]
    return float(np.median(f0)) if len(f0) else 0.0

def resonance_from_audio(frame, sr):
    """
    Spectral centroid as proxy for resonance.
    Still used if --resonance flag is passed.
    """
    centroid = librosa.feature.spectral_centroid(y=frame, sr=sr)
    return float(np.mean(centroid))

# ================================
# CLI entry point
# ================================

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
    load_sounds()
    monitor_loop(args)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"[FATAL] Uncaught exception: {e}")
