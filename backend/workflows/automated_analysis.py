"""
Cyclic voltammogram analysis: ipa, ipc, isp0, ipc0(Nicholson), and E_onset.

Same outputs as the original script, but using:
  - scipy.signal.find_peaks   -> anodic/cathodic peak detection
  - kneed.KneeLocator         -> onset (knee) detection on the rising edge
instead of manual derivative-threshold loops.
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.signal import find_peaks, savgol_filter
from kneed import KneeLocator


def scientific(value, precision=3):
    if value is None:
        return "None"
    return f"{value:.{precision}e}"


# ----------------------------------------------------------------------
# 1. Load data
# ----------------------------------------------------------------------
def run_analysis(file_name,save_path):
    pandas_data = pd.read_json(file_name)
    last_cycle = pandas_data.loc[pandas_data["cycle"] == max(pandas_data["cycle"])]
    np_data = np.array(last_cycle[["potential_V","current_A"]])
    # pandas_data = pd.read_csv("sample.csv")
    # np_data = np.array(pandas_data)

    x = np_data[:, 0]
    y = np_data[:, 1]

    min_x_index = np.argmin(x)   # switching potential index (most negative)
    max_x_index = np.argmax(x)   # switching potential index (most positive)

    # ----------------------------------------------------------------------
    # 2. Automatically find the extent of the flat baseline region
    # ----------------------------------------------------------------------
    # Rather than hand-picking "how many points are baseline", detect where
    # the curvature (2nd derivative) first rises meaningfully above its own
    # noise floor. The noise floor is estimated (via MAD, robust to outliers)
    # from a short seed region at the very start of the sweep, which is
    # assumed to be baseline almost by definition (nothing happens before
    # the sweep has even started moving away from its initial potential).
    def find_baseline_extent(x, y, end_search_idx, seed_frac=0.05, min_seed=10, k=6):
        """
        Returns the index at which the curvature first exceeds `k` times the
        robust noise floor measured over an initial seed window, searched up
        to `end_search_idx` (e.g. the index of the peak).
        """
        n = len(x)
        seed_n = max(min_seed, int(seed_frac * n))
        dy = np.gradient(y, x)
        d2y = np.gradient(dy, x)

        seed = d2y[1:seed_n]  # skip index 0 (edge artefact from np.gradient)
        noise_scale = 1.4826 * np.median(np.abs(seed - np.median(seed)))  # MAD -> std-equivalent
        threshold = k * noise_scale

        search = d2y[seed_n:end_search_idx]
        exceed = np.where(np.abs(search) > threshold)[0]
        return seed_n + exceed[0] if len(exceed) else seed_n


    ipa_idx_guess = np.argmax(y)  # rough peak location just to bound the search
    n_baseline_pts = find_baseline_extent(x, y, end_search_idx=ipa_idx_guess)
    print(f"Auto-detected forward baseline extent: {scientific(n_baseline_pts)} points (x up to {scientific(x[n_baseline_pts])} V)")
    # Same idea, run on the reverse sweep: starting right after the positive
    # switching potential (max_x_index) and walking forward in index (which
    # moves toward more negative x on the return branch) toward the cathodic
    # peak. This gives a baseline for the reduction wave, analogous to the
    # one above for the oxidation wave.
    ipc_idx_guess = max_x_index + np.argmin(y[max_x_index:])  # rough cathodic peak location
    n_rev_baseline_pts = find_baseline_extent(
        x[max_x_index:], y[max_x_index:], end_search_idx=ipc_idx_guess - max_x_index
    )
    rev_baseline_end_idx = max_x_index + n_rev_baseline_pts
    print(f"Auto-detected reverse baseline extent: {scientific(n_rev_baseline_pts)} points "
        f"(x down to {scientific(x[rev_baseline_end_idx])} V)")

    # ----------------------------------------------------------------------
    # 3. Peak detection with find_peaks (replaces the brentq zero-crossing loop)
    # ----------------------------------------------------------------------
    # `prominence` filters out noise-level wiggles; tune this relative to your
    # current's noise floor (e.g. a few % of the peak height, or a multiple
    # of np.std over a flat baseline region).
    prominence = 0.01 * (y.max() - y.min())

    pos_peak_idx, pos_props = find_peaks(y, prominence=prominence)
    neg_peak_idx, neg_props = find_peaks(-y, prominence=prominence)

    if len(pos_peak_idx) == 0:
        print(scientific(len(pos_peak_idx)), scientific(len(neg_peak_idx)))
        ValueError(
            "No peaks found — try lowering `prominence`, or check your data "
            "columns/units."
        )
        ipa_idx = ipa_idx_guess
        ipc_idx = ipc_idx_guess
    elif len(neg_peak_idx)==0:
        print("no Cathodic peak found")

        # Take the most prominent peak in each direction as the anodic/cathodic peak
        ipa_idx = pos_peak_idx[np.argmax(pos_props["prominences"])]
        #ipc_idx = neg_peak_idx[np.argmax(neg_props["prominences"])]
        ipc_idx = None
        ipc_x = None
        ipc_y = None
    else:
        ipa_idx = pos_peak_idx[np.argmax(pos_props["prominences"])]
        ipc_idx = neg_peak_idx[np.argmax(neg_props["prominences"])]

    if ipc_idx is not None:
        ipc_x, ipc_y = x[ipc_idx], y[ipc_idx]
        print(f"Cathodic peak (raw, not baseline-corrected):  Epc={scientific(ipc_x)} V, Ipc={scientific(ipc_y)}")
    ipa_x, ipa_y = x[ipa_idx], y[ipa_idx]
    print(f"Anodic peak (raw, not baseline-corrected):   Epa={scientific(ipa_x)} V, Ipa={scientific(ipa_y)}")


    # ----------------------------------------------------------------------
    # 4. Baseline fits, using the auto-detected extents from step 2
    # ----------------------------------------------------------------------
    a, b = np.polyfit(x[:n_baseline_pts], y[:n_baseline_pts], 1)
    baseline = a * x + b

    # ipa relative to baseline (this is the IUPAC-style baseline-corrected value)
    baseline_at_ipa = a * ipa_x + b
    ipa_corrected = ipa_y - baseline_at_ipa
    print(f"ipa (baseline-corrected): {scientific(ipa_corrected)}")

    # Reverse-sweep baseline, fit only over the auto-detected flat region
    # right after the switching potential (not the whole return branch).
    # cant do if no cathodic peak
    if ipc_idx is not None:
        a_rev, b_rev = np.polyfit(
            x[max_x_index:rev_baseline_end_idx], y[max_x_index:rev_baseline_end_idx], 1
        )
        baseline_at_ipc = a_rev * ipc_x + b_rev
        ipc_corrected = ipc_y - baseline_at_ipc
        print(f"ipc (baseline-corrected): {scientific(ipc_corrected)}")

        # isp0 / ipc0 for the Nicholson parameter, same definitions as before
        max_x_value = x[max_x_index]
        max_x_current = y[max_x_index]
        baseline_at_max_x = baseline[max_x_index]
        isp0 = max_x_current - baseline_at_max_x
        ipc0 = baseline_at_max_x - ipc_y
        print(f"isp0: {scientific(isp0)}")
        print(f"ipc0: {scientific(ipc0)}")

        # ----------------------------------------------------------------------
        # 4b. Nicholson peak-current-ratio method
        # ----------------------------------------------------------------------
        # Nicholson, R.S. Anal. Chem. 1966, 38, 1406. Gives ipc/ipa without
        # needing to construct a separate baseline under the cathodic peak —
        # isp0 and ipc0 are both measured relative to the *forward* (anodic)
        # baseline extrapolated across the switching potential, so only one
        # baseline choice is needed, which is the whole point of the method.
        nicholson_ratio = ipc0 / ipa_corrected + 0.485 * (isp0 / ipa_corrected) + 0.086
        ipc_nicholson = -nicholson_ratio * ipa_corrected  # sign: cathodic current is negative

        print(f"Nicholson ipc/ipa ratio: {scientific(nicholson_ratio)}")
        print(f"Nicholson-derived ipc:   {scientific(ipc_nicholson)}  "
            f"(vs. directly measured Ipc (corr.) = {scientific(ipc_corrected)})")

    # ----------------------------------------------------------------------
    # 5. Onset potential — two methods, compare them against each other
    # ----------------------------------------------------------------------
    # Smooth first: near the onset the signal is only slightly above the noise
    # floor, so raw derivatives/curvature are unreliable. window_length must be
    # odd and less than the number of points in the segment; tune to your data.
    y_smooth = savgol_filter(y, window_length=15, polyorder=3)

    # Tangent at the steepest point between the scan start and the anodic peak.
    forward_gradient = np.gradient(y_smooth[:ipa_idx_guess + 1], x[:ipa_idx_guess + 1])
    max_gradient_idx = int(np.argmax(forward_gradient))
    max_gradient_x = x[max_gradient_idx]
    max_gradient_y = y_smooth[max_gradient_idx]
    max_gradient_slope = forward_gradient[max_gradient_idx]
    tangent_end_y = -ipa_y / 2
    tangent_end_x = max_gradient_x + (tangent_end_y - max_gradient_y) / max_gradient_slope
    tangent_x = np.linspace(tangent_end_x, max_gradient_x, 100)
    tangent_y = max_gradient_y + max_gradient_slope * (tangent_x - max_gradient_x)

    # Intersection of the maximum-gradient tangent with the forward baseline
    # (baseline fit line from the start of the scan).
    # Solve: y_tangent = y_baseline -> y0 + m*(x - x0) = a*x + b
    baseline_slope = a
    baseline_intercept = b
    denom = max_gradient_slope - baseline_slope
    if abs(denom) > 1e-12:
        tangent_baseline_x = (baseline_intercept + max_gradient_slope * max_gradient_x - max_gradient_y) / denom
        tangent_baseline_y = baseline_slope * tangent_baseline_x + baseline_intercept
    else:
        tangent_baseline_x = np.nan
        tangent_baseline_y = np.nan
    print(f"Maximum forward gradient: {scientific(max_gradient_slope)} at E={scientific(max_gradient_x)} V")
    print(
        "Intersection of max-gradient tangent with forward baseline: "
        f"E={scientific(tangent_baseline_x)} V, I={scientific(tangent_baseline_y)}"
    )

    # --- Method A: KneeLocator on the rising edge -------------------------
    # IMPORTANT: the knee location is sensitive to how much of the "rounded
    # top" near the peak you include. Cut the window off well before the peak
    # (not all the way to it) or the knee gets pulled toward the peak instead
    # of sitting at the true foot of the rise. Tune `rise_end_idx` per dataset;
    # here it's the point where smoothed current reaches 60% of its rise from
    # baseline to peak — a pragmatic cutoff, not a universal rule.
    baseline_at_ipa_pt = a * x[ipa_idx] + b
    target = baseline_at_ipa_pt + 0.6 * ((y_smooth[ipa_idx]) - baseline_at_ipa_pt)
    candidates = np.where(y_smooth[n_baseline_pts:ipa_idx] >= target)[0]
    rise_end_idx = n_baseline_pts + (candidates[0] if len(candidates) else (ipa_idx - n_baseline_pts))

    x_rise = x[n_baseline_pts:rise_end_idx]
    y_rise = y_smooth[n_baseline_pts:rise_end_idx]

    kl = KneeLocator(x_rise, y_rise, curve="convex", direction="increasing", S=1.0)
    onset_knee_x = kl.knee
    #Satopa, V., Albrecht, J., Irwin, D., and Raghavan, B. (2011).
    #"Finding a 'Kneedle' in a Haystack: Detecting Knee Points in System Behavior." 
    #31st International Conference on Distributed Computing Systems Workshops, pp. 166-171.
    
    
    # --- Method B: threshold crossing (more robust to noise) --------------
    # Onset = potential where current first exceeds baseline by a fixed
    # multiple of the baseline noise (here 5 sigma), found by interpolation
    # for sub-point precision. This is a common, simple alternative to the
    # tangent-line/knee methods and is much less sensitive to window choice.
    baseline_noise_std = np.std(y[:n_baseline_pts] - baseline[:n_baseline_pts])
    threshold = baseline[n_baseline_pts:ipa_idx] + 5 * baseline_noise_std
    above = y[n_baseline_pts:ipa_idx] - threshold
    crossing = np.where(np.diff(np.sign(above)))[0]

    if len(crossing):
        i0 = n_baseline_pts + crossing[0]
        # linear interpolation between the two straddling points for sub-point precision
        frac = above[crossing[0]] / (above[crossing[0]] - above[crossing[0] + 1])
        onset_threshold_x = x[i0] + frac * (x[i0 + 1] - x[i0])
    else:
        onset_threshold_x = None

    print(f"E_onset (knee method):      {scientific(onset_knee_x)}")
    print(f"E_onset (threshold method): {scientific(onset_threshold_x)}")

    # Use whichever you trust more for your data — or flag a warning if they
    # disagree by more than your acceptable tolerance:
    if onset_knee_x is not None and onset_threshold_x is not None:
        if abs(onset_knee_x - onset_threshold_x) > 0.02:  # 20 mV, adjust as needed
            print("Warning: the two onset methods disagree by >2.000e-02 V — "
                "inspect the plot before trusting either value.")

    onset_x = onset_knee_x
    onset_y = np.interp(onset_x, x, y)
    if onset_x is not None:
        baseline_at_onset = a * onset_x + b

    # ----------------------------------------------------------------------
    # 6. Plot
    # ----------------------------------------------------------------------
    plt.figure(figsize=(8, 6))
    plt.plot(x, y, label="CV data", color="black", lw=1)
    plt.plot(x, baseline, label="Baseline fit", color="gray", linestyle="--")
    if ipc_idx is not None:
        plt.plot(
            x[max_x_index:rev_baseline_end_idx + 60],
            a_rev * x[max_x_index:rev_baseline_end_idx + 60] + b_rev,
            color="dimgray", linestyle="--", label="Reverse baseline fit",
        )
        plt.scatter(ipc_x, ipc_y, color="brown", zorder=5, label=f"Ipc (corr.) = {scientific(ipc_corrected)}")
        plt.vlines(ipc_x, baseline_at_ipc, ipc_y, colors="brown", linestyles="dashed")
        
    plt.plot(
        tangent_x,
        tangent_y,
        color="darkorange",
        linestyle="-.",
        label=f"Max-gradient tangent ({scientific(max_gradient_slope)}) to Ipc/2",
    )
    plt.scatter(
        max_gradient_x,
        max_gradient_y,
        color="darkorange",
        zorder=6,
        label=f"Max gradient at {scientific(max_gradient_x)} V",
    )
    if np.isfinite(tangent_baseline_x):
        plt.scatter(
            tangent_baseline_x,
            tangent_baseline_y,
            color="royalblue",
            zorder=7,
            label=f"Baseline/tangent intersection = {scientific(tangent_baseline_x)} V",
        )
        plt.axvline(tangent_baseline_x, color="royalblue", linestyle=":", alpha=0.5)

    plt.scatter(ipa_x, ipa_y, color="purple", zorder=5, label=f"Ipa (corr.) = {scientific(ipa_corrected)}")
    plt.vlines(ipa_x, baseline_at_ipa, ipa_y, colors="purple", linestyles="dashed")


    # Nicholson's ipc is measured relative to the *forward* baseline (not the
    # reverse-sweep baseline used for Ipc above), evaluated at the cathodic
    # peak potential for a fair visual comparison.
    #forward_baseline_at_ipc_x = a * ipc_x + b
    # plt.scatter(ipc_x, forward_baseline_at_ipc_x + ipc_nicholson, color="crimson", marker="x", s=70, zorder=6,
    #             label=f"Ipc (Nicholson) = {ipc_nicholson:.3g}")

    # plt.scatter(max_x_value, baseline_at_max_x, color="orange", zorder=5, label=f"isp0 = {isp0:.3g}")
    # plt.scatter(max_x_value, ipc_y, color="green", zorder=5, label=f"ipc0 = {ipc0:.3g}")
    # plt.vlines(max_x_value, baseline_at_max_x, max_x_current, colors="orange", linestyles="dashed")
    # plt.vlines(max_x_value, ipc_y, baseline_at_max_x, colors="green", linestyles="dotted")

    # plt.scatter(x[pos_peak_idx], y[pos_peak_idx], color="red", marker="^", label="Anodic peaks (find_peaks)")
    # plt.scatter(x[neg_peak_idx], y[neg_peak_idx], color="blue", marker="v", label="Cathodic peaks (find_peaks)")

    if onset_x is not None:
        plt.axvline(onset_x, color="darkgreen", linestyle=":", alpha=0.6)
    if onset_knee_x is not None:
        plt.axvline(onset_knee_x, color="teal", linestyle=":", alpha=0.5, label=f"E_onset (knee) = {scientific(onset_knee_x)} V")
    if onset_threshold_x is not None:
        plt.axvline(onset_threshold_x, color="magenta", linestyle=":", alpha=0.5, label=f"E_onset (threshold) = {scientific(onset_threshold_x)} V")

    plt.xlabel("E / V")
    plt.ylabel("I / A")
    plt.legend(fontsize=8)
    plt.tight_layout()
    plt.savefig(f"{save_path}/cv_analysis.png", dpi=150)
    #plt.show()
    if ipc_x is not None:
        peak_to_peak = abs(ipc_x - ipa_x)
    else:
        peak_to_peak = None
    output = {
        "Anodic peak current":ipa_y,
        "Anodic peak potential":ipa_x,
        "Cathodic peak current":ipc_y,
        "Cathodic peak potential":ipc_x,
        "Peak-to-peak separation":peak_to_peak,
        "Anodic onset potential (intersection)": tangent_baseline_x,
        "Anodic onset potential (knee)":onset_knee_x,
        "Anodic onset potential (gradient threshold)": onset_threshold_x
    }
    return output

if __name__ == "__main__":
    run_analysis("cv_raw_vit_c.json",".")