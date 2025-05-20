"""
Datainnsamling fra ESP32 + påfølgende analyse.

*  Enkelt-modus   → spør hvor mange tester (som før)
*  Serie-modus    → NUM_TESTS_PER_ROT × NUM_ROTATIONS med pause/lyd mellom
*  Analyse        → kjøres til slutt via stats(outdir, user_name)
"""

import os
import sys
import time
import json
import serial
from datetime import datetime
import pathlib
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.lines as mlines
from scipy.stats import norm, shapiro, kstest, probplot
import pandas as pd
import re
import winsound

# -----------------------------  PARAMETRE  -----------------------------
COM_PORT  = "COM13"
BAUDRATE  = 115200

NUM_TESTS_PER_ROT = 15          # ← antall tester i hver rotasjon
NUM_ROTATIONS     = 4          # ← antall rotasjoner i serien

enable_vinkelutslag_enkel = True      # ← slå av/på plottet
tick_size = 15                        # ← x-akse-tick-tetthet (15 er std)
# -----------------------------------------------------------------------




# =======================================================================
#  HJELPEFUNKSJONER  -----------------------------------------------------
# =======================================================================
def beep(duration_ms: int = 200, freq: int = 880) -> None:
    winsound.MessageBeep(-1) 


def open_serial():
    print(f"Åpner {COM_PORT} @ {BAUDRATE} bps ...")
    ser_obj = serial.Serial(COM_PORT, BAUDRATE, timeout=1)
    time.sleep(2)                   # ESP32 resettes ved åpning
    return ser_obj


def _acquire_tests(ser, outdir, base_name, *, start_idx, stop_idx):
    """Henter tester i området [start_idx, stop_idx)."""
    for i in range(start_idx, stop_idx):
        ser.reset_input_buffer()
        ser.write(b'START\n')

        filename = f"{base_name}_{i+1}.json"
        print(f"\nTest #{i+1} ({filename}): START sendt, venter på JSON ...")

        # mottakssløyfe
        while True:
            raw = ser.readline()
            if not raw:
                continue
            line = raw.decode("utf-8", errors="replace").strip()
            print(f"RAW > {line}")
            if line.startswith("{") and line.endswith("}"):
                try:
                    data = json.loads(line)
                    print(f"JSON mottatt: {line}")
                    break
                except json.JSONDecodeError as e:
                    print(f"JSON decode error: {e}")

        # lagre
        filepath = os.path.join(outdir, filename)
        with open(filepath, "w", encoding="utf-8") as jf:
            json.dump(data, jf, indent=2, ensure_ascii=False)
        print(f"Lagrer rådata til: {filepath}")








# =======================================================================
#  ANALYSE  --------------------------------------------------------------
# =======================================================================



# ---------- KONFIG -----------------------------------------------------
AVG_TOL = 0.2                     # feiltoleranse for vinkelavvik

# ---------- hjelpefunksjoner -------------------------------------------
def autocorr(x: np.ndarray, maxlag: int) -> np.ndarray:
    x = x - np.mean(x)
    acf = np.correlate(x, x, mode="full")
    acf = acf[acf.size // 2:] / acf[acf.size // 2]
    return acf[:maxlag + 1]

def natural_key(fn: str) -> int:
    nums = re.findall(r"\d+", fn)
    return int(nums[-1]) if nums else -1

# ---------- Interval_stats -----------------------
def interval_stats(trough_vals, start, end, tol):
    block = trough_vals[start:end]
    runs  = np.arange(start + 1, end + 1)

    unique_vals, counts = np.unique(block, return_counts=True)
    order = np.lexsort((unique_vals, -counts))
    mode1 = unique_vals[order[0]]
    mode2 = unique_vals[order[1]] if len(order) > 1 else mode1

    center = (mode1 + mode2) / 2.0
    mask   = np.abs(block - center) <= tol

    included_runs = runs[mask]
    excluded_runs = runs[~mask]
    vals_incl     = block[mask]
    mean_val      = float(vals_incl.mean()) if vals_incl.size else np.nan

    df = pd.DataFrame({"Run": runs, "Value": block, "Included": mask})

    print(f"\nInterval {start+1}–{end}: "
          f"mode1={mode1:.2f}, mode2={mode2:.2f}, "
          f"center={center:.2f}, mean etter filter={mean_val:.2f}")
    print(df.to_string(index=False))

    if excluded_runs.size:
        excl_str = ", ".join(map(str, excluded_runs))
        print(f"   → Ekskluderte målinger (pga ±{tol}): {excl_str}")
    else:
        print("   → Ingen ekskluderte målinger")

    return {
        "mode1": mode1, "mode2": mode2, "center": center,
        "mean": mean_val,
        "included_runs": included_runs.tolist(),
        "excluded_runs": excluded_runs.tolist(),
        "df": df
    }

# ---------- prosessér én katalog ---------------------------------------
def process_dataset(directory: os.PathLike):
    stats_drop = dict(const=0, extreme=0)

    files = sorted(
        (f for f in os.listdir(directory) if f.lower().endswith(".json")),
        key=natural_key
    )

    enc_list, t_list = [], []
    temps, hums = [], []                          

    for fn in files:
        with open(os.path.join(directory, fn), encoding="utf-8") as f:
            data = json.load(f)

        # ---------- encoder & tid -----------------------------------
        enc = np.asarray(data["encoder"], float)
        if enc.ndim == 0:
            enc = enc.reshape(1)
        enc_list.append(enc)

        t = np.asarray(data.get("test_time_ms") or range(enc.size), float)
        if t.size != enc.size:
            t = np.resize(t, enc.size)
        t_list.append(t)

        # ---------- temp & hum -------------------------------------- 
        temp = data.get("temp")
        hum  = data.get("hum")
        if isinstance(temp, list):
            temp = temp[0] if temp else np.nan
        if isinstance(hum, list):
            hum = hum[0] if hum else np.nan
        temps.append(float(temp) if temp is not None else np.nan)
        hums.append(float(hum)  if hum  is not None else np.nan)

    # ---------- fasejustering + resampling (uendret) -------------------
    minima = [np.where((np.diff(e)[:-1] < 0) & (np.diff(e)[1:] >= 0))[0]
              for e in enc_list]
    minima_idx = [(m[0] + 1) if m.size else 0 for m in minima]
    ref_t0 = t_list[0][minima_idx[0]]
    shifted_t = [t + (ref_t0 - t[i]) for t, i in zip(t_list, minima_idx)]

    dt    = np.mean(np.diff(shifted_t[0]))
    t_new = np.arange(min(shifted_t[0]), max(shifted_t[0]), dt)
    all_enc = np.array([np.interp(t_new, st, e)
                        for st, e in zip(shifted_t, enc_list)])

    # ---------- retur --------------------------------------------------
    return t_new, all_enc, np.asarray(temps, float), np.asarray(hums, float)   




# ------------------------------------------------
# Kjør statistisk analyse og akseptansetest
# -----------------------------------------------------------------------
def stats(outdir: str | os.PathLike, user_name: str) -> None:
    """Kjør analyse + η-beregning på mappen `outdir`."""
    outdir = pathlib.Path(outdir)

    # ---- hent dataserien(e) ------------------------------------------
    t_new, all_enc, temps, hums = process_dataset(outdir)

    # ========= BEREGN η (first-bounce gjennomsnitt) ===================
    n_trials    = NUM_TESTS_PER_ROT
    n_rotations = NUM_ROTATIONS

    enc_arr = all_enc                              # alias som i koden din
    trough_vals = []
    for series in enc_arr:
        diffs = np.diff(series)
        minima = np.where((diffs[:-1] < 0) & (diffs[1:] >= 0))[0]
        idx = (minima[0] + 1) if minima.size else 0
        trough_vals.append(abs(series[idx]))
    trough_vals = np.asarray(trough_vals)

    # Beregner gjennomsnitt per blokk (15 er std, n_trials er variabelen)
    means_per_block = []
    all_excluded = [] 

    for k in range(n_rotations):
        start = k * n_trials
        end   = start + n_trials
        stats_blk = interval_stats(trough_vals, start, end, AVG_TOL)
        means_per_block.append(stats_blk["mean"])
        all_excluded.extend(stats_blk["excluded_runs"])

    overall_mean = float(np.nanmean(means_per_block))
    print(f"\nSamlet gjennomsnitt η over {n_rotations} blokker: "
          f"{overall_mean:.2f}°")




    # ---- (valgfritt) plot mean ±1 SD for hele serien -----------------
    if all_enc.shape[0] >= 2:
        mean_enc = all_enc.mean(axis=0)
        std_enc  = all_enc.std(axis=0)
        plt.fill_between(t_new, mean_enc - std_enc, mean_enc + std_enc,
                         alpha=0.25)
        plt.plot(t_new, mean_enc, label=f"{user_name} (mean ± 1 SD)")
        plt.xlabel("Tid [ms]")
        plt.ylabel("Vinkel [°]")
        plt.title(f"Ring {user_name}: gjennomsnittlig vinkelprofil")
        plt.legend()
        plt.tight_layout()
        
    
    # ---------- PLOTT: første sprett + temp/fukt ---------- 
    if enable_vinkelutslag_enkel:
        # 1) kalkuler første trough / utslag
        trough_vals = []
        for series in all_enc:
            diffs  = np.diff(series)
            minima = np.where((diffs[:-1] < 0) & (diffs[1:] >= 0))[0]
            idx    = (minima[0] + 1) if minima.size > 0 else 0
            trough_vals.append(abs(series[idx]))
        trough_vals = np.asarray(trough_vals)

         # ---------- fargeskala + grå for ekskluderte -------------  
        n      = len(trough_vals)
        cmap   = plt.get_cmap('RdYlGn')
        base_colours = [cmap(i / (n - 1)) for i in range(n)]

        excl_set = set(all_excluded)                        
        colours = ['0.5' if (i + 1) in excl_set else base_colours[i]
                for i in range(n)]                       

        # 3) figur
        fig, ax = plt.subplots(figsize=(6, 4))
        ax.scatter(np.arange(n), trough_vals, color=colours, zorder=3)

        ax.set_xlabel("Test #")
        ax.set_ylabel("Vinkel [°]")
        ax.set_title(f"{user_name}: Utslagsvinkel etter første støt")
        ax.set_xticks(np.arange(0, n, tick_size))
        ax.grid(True, zorder=0)

        # 4) temp + fukt på sekundær akse
        ax2 = ax.twinx()
        ax2.set_ylabel("Temp [°C] / RH [%]")

        # → sørg for svart aksisfarge:
        ax2.tick_params(axis='y', colors='black')           # y-ticks + tall
        ax2.spines['right'].set_color('black')              # y-akse-linjen

        # nå tegner vi linjene
        ax2.plot(np.arange(n), hums,  'k--', label='Relativ fukt (%)', linewidth=1.2)
        ax2.plot(np.arange(n), temps, 'b--', label='Temperatur (°C)',   linewidth=1.2)


        # 5) legender
        excl_pct = 100 * len(excl_set) / n                  

        grey_dot = mlines.Line2D([], [], color='0.5', marker='o',
                                linestyle='None',
                                label=f'Ekskludert ({excl_pct:.1f} %)')  

        red_dot   = mlines.Line2D([], [], color=cmap(0.0), marker='o',
                                  linestyle='None', label='Første test')
        green_dot = mlines.Line2D([], [], color=cmap(1.0), marker='o',
                                  linestyle='None', label='Siste test')
        leg1 = ax.legend(handles=[red_dot, green_dot, grey_dot],     
                     loc='upper left')
        leg2 = ax2.legend(loc='upper right')
        ax.add_artist(leg1)

        plt.tight_layout()
        
        
        
        plt.show()








# =======================================================================
#  MODI                                                                  |
# =======================================================================
def run_single_mode(ser, outdir):
    """Original logikk for ett sammenhengende sett med tester."""
    test_count = int(input("Angi nummer for siste test hvis fortsettelse (↵ = 0): ") or 0)
    max_tests  = test_count + int(input("Oppgi antall nye tester: ") or 1)

    date_str  = datetime.now().strftime("%Y%m%d")
    user_name = input("Angi ringID: ").strip() or "test"
    base_name = f"{date_str}_ring{user_name}_test"

    _acquire_tests(ser, outdir, base_name,
                   start_idx=test_count,
                   stop_idx=max_tests)

    print(f"\nAlle {max_tests} tester fullført.")
    # ---- kjør intern analyse -----------------------------------------
    stats(outdir, user_name)


def run_series_mode(ser, outdir):
    """NUM_TESTS_PER_ROT tester × NUM_ROTATIONS med pause/lyd mellom blokkene."""
    date_str  = datetime.now().strftime("%Y%m%d")
    ring_id   = input("Angi ringID: ").strip() or "test"
    base_name = f"{date_str}_ring{ring_id}_test"

    test_idx = 0
    for rot in range(1, NUM_ROTATIONS + 1):
        print(f"\n=== Start rotasjon {rot}/{NUM_ROTATIONS} ===")
        next_idx = test_idx + NUM_TESTS_PER_ROT
        _acquire_tests(ser, outdir, base_name,
                       start_idx=test_idx,
                       stop_idx=next_idx)
        test_idx = next_idx

        if rot < NUM_ROTATIONS:        # pause før neste rotasjon
            beep()
            input("\nRotasjon ferdig – trykk ↵ for å fortsette ...")

    total = NUM_TESTS_PER_ROT * NUM_ROTATIONS
    print(f"\nAlle {total} tester fullført.")
    # ---- kjør intern analyse -----------------------------------------
    stats(outdir, ring_id)


# =======================================================================
#  HOVEDPROGRAM                                                          |
# =======================================================================
if __name__ == "__main__":
    try:
        # ---------- velg mappe -------------------------------
        outdir = input("Oppgi utdatamappe for JSON-filer: ").strip()
        os.makedirs(outdir, exist_ok=True)

        # ---------- åpne seriell -----------------------------
        ser = open_serial()

        # ---------- velg modus -------------------------------
        series_ans = input("Ønsker du å kjøre testserie? (j/N): ").strip().lower()
        if series_ans == "j":
            run_series_mode(ser, outdir)
        else:
            run_single_mode(ser, outdir)

    except KeyboardInterrupt:
        print("\nAvbrutt av bruker.")
    finally:
        try:
            ser.close()
        except Exception:
            pass
        print("Serialport lukket.")









