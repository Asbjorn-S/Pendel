import os
import sys
import time
import json
import serial
from datetime import datetime
from pathlib import Path 
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.lines as mlines
import matplotlib.gridspec as gridspec
from scipy.stats import norm, shapiro, kstest, probplot
import pandas as pd
import re
import winsound


# -----------------------------  PARAMETRE  -----------------------------
COM_PORT  = "COM13"
BAUDRATE  = 115200

# -------------------------------
# Aktiveringsvariabler
# ------------------------------

x_res = 15 # Oppløsning på x-akse for utslagsvinkel plot

enable_avgstd = False # Plot med standardavvik og gjennomsnitt
enable_vinkelutslag = False # Plot vinkelutslag med filtrering og median
enable_vinkelutslag_enkel = False # Plot vinkelutslag uten filtrering og median
enable_3_vinkelutslag = False # Plot med vinkelutslag for 3 sprett
enable_all_series = False # Plot av alle måleserier over hverandre

enable_angle_diff = False # Plot som differensierer sprettberegninger for forskjellige målinger
interval_size = 15  # antall runs per gruppe

# ---- Beregner gjennomsnitt for 1 sprett av hver ring med parameter som angir n-tester ---
enable_avg_calc = False # Enable
avg_tol = 0.25 # Feiltoleranse for avik i vinkelutslag
DEFAULT_BLOCK_SIZE = 15   # Antall tester per rotasjon
DEFAULT_TOL        = 0.3  # Toleranse for avvik i grader fra blokkvis snitt basert på typetall


enable_vinkelutslag_enkel = True      # ← slå av/på plottet
tick_size = 15                        # ← x-akse-tick-tetthet (15 er std)
# --------------------------------------------------------------------


# =======================================================================
#  HJELPEFUNKSJONER  -----------------------------------------------------
# =======================================================================


# ------------------------------------------------------------------
# 1) Fargegenerator -------------------------------------------------
# ------------------------------------------------------------------
def make_run_colours(n_runs: int,
                     excluded_runs: set[int] | list[int] = (),
                     *,
                     cmap_name: str = "RdYlGn") -> list:
    """
    Returnerer en fargeliste med lengde n_runs.
    Utkastede run (1-basert i excluded_runs) får grå farge ("0.5").

    Eksempel
    --------
    colours = make_run_colours(len(trough_vals), excluded_runs)
    """
    cmap = plt.get_cmap(cmap_name)
    base = [cmap(i / (n_runs - 1)) for i in range(n_runs)]
    excluded = set(excluded_runs)
    return ["0.5" if (i + 1) in excluded else base[i]
            for i in range(n_runs)]


# Hjelpefunksjon for å trekke ut siste tall i filnavnet for å sortere på testnummer
def natural_key(fn: str):
    import re
    nums = re.findall(r'\d+', fn)
    return int(nums[-1]) if nums else -1




# -------------------------------------------------------
#  Variasjons­kontroll for indre variasjoner i ring
# -------------------------------------------------------
def check_block_variation(means, *,
                          range_tol=None):
    """Returnerer (bestått: bool, beregnet_mål: float)"""
    means = np.array(means, float)

    if range_tol is not None:                         
        rng = means.max() - means.min()
        return rng <= range_tol, rng

    raise ValueError("Spesifiser nøyaktig én toleranse‐type")







# ------------------------------------------------------------
#  Visualisering av analyse. Plot og forskjellige parameter
# ------------------------------------------------------------
def plot_test_results(trough_vals: np.ndarray,
                      temps: np.ndarray,
                      hums: np.ndarray,
                      excluded_runs: list[int],
                      base_name: str,
                      *,
                      overall_mean: float,
                      range_metric: float,
                      range_tol: float,
                      block_size: int,  
                      tick_size: int = 15,
                      cmap_name: str = "RdYlGn") -> None:
    """
    Tegner scatter-plottet (øverst) + tekst med nøkkeldata (nederst).

    Tilleggsparametre:
        overall_mean : float  – samlet η̄ over blokker
        range_metric : float  – faktisk maks-min mellom blokker
        range_tol    : float  – akseptgrense for range
    """
    n_runs = trough_vals.size
    cmap   = plt.get_cmap(cmap_name)

    # ------------------ robust senter ------------------
    clean = np.round(trough_vals[~np.isnan(trough_vals)], 1)
    modes, counts = np.unique(clean, return_counts=True)
    order = np.lexsort((modes, -counts))
    mode1 = modes[order[0]]
    mode2 = modes[order[1]] if modes.size > 1 else mode1
    center = (mode1 + mode2) / 2

    # ------------------ farger -------------------------
    colours = make_run_colours(n_runs, excluded_runs, cmap_name=cmap_name)
    excl_pct  = 100 * len(excluded_runs) / n_runs
    status_ok = range_metric <= range_tol

    # ------------------ figuroppsett -------------------
    fig = plt.figure(figsize=(7, 6))
    gs  = gridspec.GridSpec(2, 1, height_ratios=[3, 1.1],
                            hspace=0.35)

    ax  = fig.add_subplot(gs[0])           # scatter
    ax_txt = fig.add_subplot(gs[1])        # tekstpanel
    ax_txt.axis("off")

    # --------------- scatter-plott ---------------------
    ax.scatter(np.arange(n_runs), trough_vals, color=colours, zorder=3)
    ax.set_xlabel("Test #")
    ax.set_ylabel("Vinkel [°]")
    ax.set_title(f"{base_name}: Testresultat")
    ax.set_xticks(np.arange(0, n_runs, tick_size))
    ax.grid(True, zorder=0)

    # ---------- Løft øvre y-grense med +2° for bedre synlighet på legends --------
    y_low, y_high = ax.get_ylim()
    ax.set_ylim(y_low, y_high + 2)


    # ---------------------------------------------------------
    # 2) BLOKK-VISE SENTERLINJER  ------------------------------
    # ---------------------------------------------------------
    n_blocks = int(np.ceil(n_runs / block_size))
    proxy_center = None                       # legende-proxy

    for b in range(n_blocks):
        s = b * block_size
        e = min((b + 1) * block_size, n_runs)
        block = trough_vals[s:e]

        # robust center i AKKURAT denne blokken
        clean = np.round(block[~np.isnan(block)], 1)
        if clean.size == 0:
            continue
        u, c = np.unique(clean, return_counts=True)
        order = np.lexsort((u, -c))
        m1, m2 = u[order[0]], u[order[1]] if len(order) > 1 else u[order[0]]
        center_b = (m1 + m2) / 2

        # trekk en linje som bare går over blokkens x-område
        ax.hlines(center_b, s - 0.5, e - 0.5,
                  colors="black", linestyles="--", linewidth=1, zorder=2)

        # lag én proxy for legenden bare første gang
        if proxy_center is None:
            proxy_center = mlines.Line2D([], [], color="black",
                                         linestyle="--", label="Blokk-senterverdi")

     # ---------------------------------------------------------
    # 3) SEKUNDÆR AKSE (temp / RH)  ----------------------------
    # ---------------------------------------------------------
    ax2 = ax.twinx()
    ax2.set_ylabel("Temp [°C] / RH [%]")
    ax2.tick_params(axis="y", colors="black")
    ax2.spines["right"].set_color("black")
    ax2.plot(np.arange(n_runs), hums,  "k--", linewidth=1.2,
             label="Relativ fukt (%)")
    ax2.plot(np.arange(n_runs), temps, "b--", linewidth=1.2,
             label="Temperatur (°C)")

    # ---------------------------------------------------------
    # 4) LEGENDE  ---------------------------------------------
    # ---------------------------------------------------------
    red_dot   = mlines.Line2D([], [], color=cmap(0.0), marker="o",
                              linestyle="None", label="Første test")
    green_dot = mlines.Line2D([], [], color=cmap(1.0), marker="o",
                              linestyle="None", label="Siste test")
    grey_dot  = mlines.Line2D([], [], color="0.5", marker="o",
                              linestyle="None",
                              label=f"Ekskludert ({excl_pct:.1f} %)")

    ax.legend(handles=[red_dot, green_dot, grey_dot, proxy_center],
              loc="upper left")

    ax2.legend(loc="upper right")

    # ---------------------------------------------------------
    # 5) TEKSTPANEL  --------------------------------
    # ---------------------------------------------------------
    avg_temp = np.nanmean(temps) if np.isfinite(temps).any() else np.nan
    avg_hum  = np.nanmean(hums)  if np.isfinite(hums).any()  else np.nan

    # Beregn temperatur‑variasjon og vurder status
    temp_range = np.nanmax(temps) - np.nanmin(temps) if np.isfinite(temps).any() else np.nan
    TEMP_TOL = 1.0  # ↔ ±0,5 °C
    delta_t_status = "✅ Temperatur OK" if temp_range <= TEMP_TOL else "❌ Temperatur FOR STORE VARIASJONER"

    # ---------- status på ekskluderte -------------------
    excl_fail_threshold = 15.0       # grense i prosent
    excl_status = "TEST UGYLDIG - for stor spredning i alle målinger" if excl_pct > excl_fail_threshold else "Spredning OK"
    # -----------------------------------------------------

    lines = [
     f"Gjennomsnittlig Δθ: {overall_mean:.3f}°",
    f"Indre spredning i ring: {range_metric:.3f}° ≤ {range_tol:.3f}°  →  "
    + ("✅ OK" if range_metric <= range_tol else "❌ FAIL - store indre variasjoner"),
    f"Ekskluderte målinger: {len(excluded_runs)} "
    f"({excl_pct:.1f} %)  →  {excl_status}",    # Feil hvis for stor spredning
    f"Middel­temperatur: {avg_temp:.1f} °C",
    f"Middel RH:         {avg_hum:.1f} %",
    f"Temp‑variasjon ΔT: {temp_range:.2f} °C  →  {delta_t_status}",
    ]

    ax_txt.text(0.02, 0.78, "\n".join(lines),
                fontsize=11, va="top", family="monospace")

    #plt.tight_layout()
    return fig







# ----------------------------------------------------
# ---------- prosessér én katalog --------------------
# ----------------------------------------------------

def process_dataset(directory: os.PathLike):

    # Sorter filene på numerering
    file_list = sorted(
        (f for f in os.listdir(directory) if f.lower().endswith(".json")),
        key=natural_key
    )
    if not file_list:                       # tom mappe?
        raise FileNotFoundError("Ingen .json-filer!")

    enc_list, t_list = [], []
    temps, hums = [], []                          

    for fn in file_list:
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
    encoder = np.array([np.interp(t_new, st, e)
                        for st, e in zip(shifted_t, enc_list)])

    # ---------- retur --------------------------------------------------
    return t_new, encoder, np.array(temps), np.array(hums), file_list   

# ---------------------------------------------------------------------------
# ---------- Hjelpefunksjon for å filtrere ut outliers -----------------------
# -----------------------------------------------------------------------------

def interval_stats(block_vals, tol):
    """
    Parameters
    ----------
    block_vals : 1-D np.ndarray  (én blokk på block_size verdier)
    tol        : float          (± grense rundt senter)
    """

    clean = block_vals[~np.isnan(block_vals)]
    if clean.size == 0:
        return np.nan, np.ones_like(block_vals, dtype=bool)  # alt ekskludert

    # Finner linjen imellom to typetall
    uniq, cnt = np.unique(np.round(clean, 1), return_counts=True)
    order = np.lexsort((uniq, -cnt))
    center = (uniq[order[0]] + (uniq[order[1]] if len(order) > 1 else uniq[order[0]])) / 2

    keep_mask = np.abs(block_vals - center) <= tol # Boolsk rekke, false for
    mean_val  = float(block_vals[keep_mask].mean()) if keep_mask.any() else np.nan

    return mean_val, ~keep_mask     # bool-array: True = ekskludert



# ------------------------------------------------------------
#  Hovedfunksjon for dataanalyse
# ------------------------------------------------------------
def analyze(outdir, base_name, *, block_size=15, tol=0.25, plot_first_bounce=False, range_tol=0.4):
    """
    Kjører komplett η-analyse på katalogen `outdir`. Dette skal være en ring.

    Parameters
    ----------
    outdir : str
        Mappesti som inneholder .json-filene.
    base_name : str
        Navn som skal brukes i utskrifter / plott.
    block_size : int, default 15
        Antall filer per blokk (tidligere n_trials).
    tol : float, default 0.25
        Maksimalt avvik ±tol rundt senter for å inkludere en måling.

    Returns
    -------
    overall_mean : float
        Gjennomsnittlig η over samtlige blokker (etter filtrering).
    """
    outdir = Path(outdir)

    # --------------------------------------------------------
    #  Pakk ut data
    # --------------------------------------------------------
    t_new, encoder, temps, hums, files = process_dataset(outdir)


    # --------------------------------------------------------
    # Kvitter for rekkefølge på filer
    # --------------------------------------------------------
   
    # –– sjekk at antall filer er delelig med block_size ––
    if len(files) % block_size:
        raise ValueError(
            f"Antall filer ({len(files)}) må være delelig med block_size={block_size}"
        )

    df_files = pd.DataFrame({
        "Run": range(1, len(files)+1),
        "Filename": files
    })
    print(f"\nKvittering for «{base_name}» "
          f"({len(files)} filer, block_size={block_size}):")
    print(df_files.to_string(index=False))


    # --------------------------------------------------------
    # 3) Beregn første bunnpunkt for hver måleserie
    # --------------------------------------------------------
    diffs = np.diff(encoder, axis=1)
    minima = (diffs[:, :-1] < 0) & (diffs[:, 1:] >= 0)
    idx_first = minima.argmax(axis=1) + 1          # 0 hvis ingen minima
    trough_vals = np.abs(encoder[np.arange(encoder.shape[0]), idx_first])

    # --------------------------------------------------------
    # 4) Blokk-vis gjennomsnitt med outlier-filtrering
    # --------------------------------------------------------
    n_blocks = len(trough_vals) // block_size
    means_per_block = []
    excluded_runs = []

    for b in range(n_blocks):
        start = b * block_size
        end   = start + block_size
        block = trough_vals[start:end]

        mean_val, excl_mask = interval_stats(block, tol)
        means_per_block.append(mean_val)

        # Lag indeks for verdier som ble indeksert:
        excluded_runs.extend(
            (np.arange(start, end)[excl_mask] + 1).tolist()
        )

        # Kvittering for ekskludering
        print(f"\nBlokk {b+1}/{n_blocks} "
              f"(runs {start+1}–{end}):  η̄ = {mean_val:.2f}° "
              f"({excl_mask.sum()} ekskludert)")

    # Sjekker om intre variasjon er avvikende    
    ok, metric = check_block_variation(means_per_block,
                                range_tol=range_tol)
    if ok:
        print(f"\n✅ Indre variasjon OK: range = {metric:.3f}° ≤ {range_tol}")
    else:
        print(f"\n❌ Indre variasjon for stor: range = {metric:.3f}° > {range_tol}")

    overall_mean = float(np.nanmean(means_per_block))
    print(f"\n⟹  Samlet gjennomsnitt η over {n_blocks} blokker: "
          f"{overall_mean:.2f}°")

    if excluded_runs:
        print("   Ekskluderte målinger:", ", ".join(map(str, excluded_runs)))


    # --------------------------------------------------------
    # 5) Plot testresultater via egne plot-funksjoner
    # --------------------------------------------------------
    if plot_first_bounce:        # Parameter fra input
        plot_test_results(trough_vals, temps, hums,
                      excluded_runs, base_name,
                      overall_mean=overall_mean,
                      range_metric=metric,
                      range_tol=range_tol,
                      block_size=block_size) 


    plt.show()

    return overall_mean


# =======================================================================
#  HOVEDPROGRAM 
# Input for datamappe og input for navn på test er de som i hovedsak endres
#                                                           
# =======================================================================
if __name__ == "__main__":
    import os
    import sys

    

    try:
        # ----------------- velg mappe -----------------
        outdir = input("Oppgi datamappe for JSON-filer: ").strip()
        if not os.path.isdir(outdir):          # Opretter ikke mappe som mangler
            print(f"❌  Mappen «{outdir}» finnes ikke.")
            sys.exit(1)

        # ---------------- Angi navn på test -----------------
        base_name = input("Angi navn på test [test]: ").strip() or "test"

        # ------------- Antall målinger per rotasjon ---------------
        bs_str = input(f"Block size – antall filer per blokk "
                       f"[{DEFAULT_BLOCK_SIZE}]: ").strip()
        block_size = int(bs_str) if bs_str else DEFAULT_BLOCK_SIZE
        if block_size <= 0:
            raise ValueError("block_size må være > 0")

        # ----------------- tol (0.25) ----------------
        tol_str = input(f"Toleranse tol i grader "
                        f"[{DEFAULT_TOL}]: ").strip()
        tol = float(tol_str) if tol_str else DEFAULT_TOL
        if tol <= 0:
            raise ValueError("tol må være > 0")
        
        # ---------- Presentasjon av testdata? ----------
        resp = input("Presenter test-data? (J/n): ").strip().lower()
        plot_first_bounce = (resp != "n")      # tom streng, “j”, “ja” → True
        
        range_tol_str = input("Tillatt forskjell maks–min mellom blokker [0.4]: ").strip()
        range_tol = float(range_tol_str) if range_tol_str else 0.4

        # -------------- kjør analyse -----------------
        analyze(outdir, base_name, block_size=block_size, tol=tol, plot_first_bounce=plot_first_bounce, range_tol=range_tol)

    except KeyboardInterrupt:
        print("\nAvbrutt av bruker.")
    



