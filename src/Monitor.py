import argparse
import sounddevice as sd
import numpy as np
import parselmouth
import librosa
import pygame
import threading
import time
from scipy.signal import butter, lfilter

SOUNDS = {
    "error": None,
    "pinpon": None
}

# ================================
# === Audio feature detection  ===
# ================================

def bandpass_filter(data, sr, lowcut=75.0, highcut=4000.0, order=4):
    nyq = 0.5 * sr
    low = lowcut / nyq
    high = highcut / nyq
    b, a = butter(order, [low, high], btype='band')
    return lfilter(b, a, data)

# Parselmouth-based pitch
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

def is_audio_present(indata, sr=22050, threshold=0.005):
    filtered = bandpass_filter(indata, sr)
    energy = np.abs(filtered).mean()
    return energy > threshold

def resonance_from_audio(frame, sr):
    """
    Uses Parselmouth (Praat) to extract formants from the audio signal.
    Returns the average of the first three formants as a resonance proxy.
    """
    snd = parselmouth.Sound(frame, sampling_frequency=sr)
    formant = snd.to_formant_burg()  # You could also use to_formant_keep_all()
    
    # Measure over the duration of the audio
    duration = snd.duration
    num_samples = 50
    times = np.linspace(0, duration, num=num_samples)
    
    f1_vals, f2_vals, f3_vals = [], [], []
    
    for t in times:
        try:
            f1 = formant.get_value_at_time(1, t)
            f2 = formant.get_value_at_time(2, t)
            f3 = formant.get_value_at_time(3, t)
            if all(v is not None and not np.isnan(v) for v in [f1, f2, f3]):
                f1_vals.append(f1)
                f2_vals.append(f2)
                f3_vals.append(f3)
        except Exception as e:
            print(f"[WARN] Failed to get formant at time {t:.2f}: {e}")
            continue
    
    if not f1_vals:
        return None  # Could not extract formants

    # Return the mean formant values (you could return all 3 separately if needed)
    return {
        "F1": float(np.mean(f1_vals)),
        "F2": float(np.mean(f2_vals)),
        "F3": float(np.mean(f3_vals)),
        "resonance_score": float(np.mean([np.mean(f1_vals), np.mean(f2_vals), np.mean(f3_vals)]))
    }
    
# ================================
# === Audio feature detection  ===
# ================================

# ================================
# ===  sound Effect Playback   ===
# ================================

def play_sound_threaded(sound_key):
    def _play():
        sound = SOUNDS.get(sound_key)
        if sound:
            sound.play()
    threading.Thread(target=_play, daemon=True).start()
    
def load_sounds():
    try:
        pygame.mixer.init()
        SOUNDS["error"] = pygame.mixer.Sound("src/error.wav")
        SOUNDS["pinpon"] = pygame.mixer.Sound("src/pin-pon.wav")
    except Exception as e:
        print(f"[ERROR] Failed to load sound: {e}")
        

# ================================
# ===  sound Effect Playback   ===
# ================================
    
# ================================
# = Callable monitor for instance=
# ================================
    
def parse_sample(args, audio, samplerate, trackers):
    pitch = pitch_from_audio(audio, samplerate)
    energy = np.mean(audio ** 2)
    

    current_time = time.time()
    # Check pitch range
    if args.min <= pitch <= args.max:
        trackers["in_range_time"] += 1.0
        trackers["streak"] += 1.0
    else:
        trackers["streak"] = 0
        if trackers["sentence"]:
            trackers["error"] = True
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

    # === Sentence tracking using time ===
    if args.sentence_monitor:
        if (trackers["sentence"] == False):
            trackers["sentence"] = True
            trackers["sentence_start"] = current_time
            trackers["sentence_last"] = current_time
        elif (trackers["error"] == False):
            trackers["sentence_last"] = current_time
        

    # Resonance display
    if args.resonance:
        r = resonance_from_audio(audio, samplerate)
        if not r:
            print("Could not extract resonance features.")
        else:
            f1, f2, f3 = r["F1"], r["F2"], r["F3"]
            resonance_score = r["resonance_score"]

            # Heuristic classification (simplified)
            if resonance_score < 1800:
                voice_type = "male"
            elif resonance_score < 2500:
                voice_type = "androgynous"
            else:
                voice_type = "female"

            print(f"[Resonance] F1: {f1:.1f} Hz | F2: {f2:.1f} Hz | F3: {f3:.1f} Hz | Type: {voice_type}")


    # Write score file every 60 seconds
    if args.score and int(trackers["total_time"]) % 60 == 0 and not trackers.get("score_written", False):
        with open("score.txt", "w") as f:
            f.write(f"{percent:.1f}% in range\n")
        trackers["score_written"] = True
    elif int(trackers["total_time"]) % 60 != 0:
        trackers["score_written"] = False
# ================================
# = Callable monitor for instance=
# ================================
            
# ================================
# ===       monitor loop       ===
# ================================

def monitor_loop(args):
    samplerate = 22050
    block_len = 1.0
    block_size = int(block_len * samplerate)

    trackers = {
        "in_range_time": 0.0,
        "total_time": 0.0,
        "streak": 0.0,
        "last_error_time": 0.0,
        "sentence_start": None,
        "sentence": False,
        "sentence_last": None,
        "error": False,
        "score": 0.0
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
                    silence(trackers)

        except KeyboardInterrupt:
            print("\n=== Monitoring stopped ===")
            if args.score and trackers["total_time"] > 0:
                final_pct = (trackers["in_range_time"] / trackers["total_time"]) * 100
                print(f"Final score: {final_pct:.1f}% in range")
        except Exception as e:
            print(f"\n[FATAL ERROR] {e}")
# ================================
# silence buffer
# ================================

def silence(trackers):
    now = time.time()
    sentence_last = trackers.get("sentence_last")

    # Don't play pinpon if there was an error
    if trackers.get("error"):
        trackers["sentence"] = False
        trackers["error"] = False  # Reset after suppressing reward
        return

    if trackers.get("sentence") and sentence_last is not None and (now - sentence_last > 1.75):
        play_sound_threaded("pinpon")
        trackers["sentence"] = False
        trackers["score"] = 100 * (sentence_last - trackers["sentence_start"])


# ================================
# silence buffer
# ================================


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
