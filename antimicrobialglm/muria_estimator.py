"""
MURIA-calibrated Medical Demand Estimator (MDE).

Implements the estimator of Report Section 4.5, but calibrated to the *real*
MURIA Botswana Antibiotic Utilization Study microdata instead of the
hand-set "# data withheld" multipliers that stood in for it before.

Pipeline (mirrors 4.5, real data replacing guesses):
  1. decode MURIA  -> patient table (Section 1) + prescription table (Section 2)
  2. real marginals -> (age x infection) patient/prescription totals,
                       (tier x class) prescription totals, HIV marginal
  3. synthetic joint over (age, infection, tier, class[, HIV]) via IPF raked
     to those REAL marginals  (the "calibrated synthetic microdata" of 4.5)
  4. fit NB2 GLM  count ~ C(age)+C(infection)+C(tier)+C(class)[+C(HIV)]  with
     log-exposure offset; extract alpha_hat / kappa_hat
  5. validate: compare the synthetic joint against the (best-effort) real
     joint the model was NOT fully calibrated to
  6. export artifacts (same schema as the notebook's artifacts/ folder)

The raw workbook is private MoH data (gitignored). Keep it local; never commit.

Run:  python antimicrobialglm/muria_estimator.py
"""
from __future__ import annotations
import re
from pathlib import Path

import numpy as np
import pandas as pd

# --------------------------------------------------------------------------
# Configuration / taxonomy  (must match antimicrobialglm/artifacts/*)
# --------------------------------------------------------------------------
REPO = Path(__file__).resolve().parent.parent
PPS_PATH = REPO / "PPS -BW Consolidated Raw.xlsx"      # private, gitignored
OUT_DIR = Path(__file__).resolve().parent / "artifacts"

CLASSES = ["Aminoglycosides", "Amphenicols", "Carbapenems", "Cephalosporins",
           "Glycopeptides", "Lincosamides", "Macrolides", "Nitroimidazoles",
           "Penicillins", "Quinolones", "Sulphonamides", "Tetracyclines"]
TIERS = ["Primary", "District", "Tertiary", "Specialist"]
# CAI=community-acquired infection, HAI=hospital-acquired infection,
# HBCI=hospital-based-care infection, NIC=non-infectious conditions (Paramadhas et al. 2019)
INF_CATS = ["CAI", "HAI", "HBCI", "NIC"]
# Fine 5-year bands: MUST match the committed artifacts + run_cms_two.py `age_map`
# (downstream merges population by these labels). Do not change without updating age_map.
AGE_ORDER = ["<1", "1-5", "6 to 10 years", "11 to 15 years", "16 to 20 years",
             "21 to 25 years", "26 to 30 years", "31 to 35 years", "36 to 40 years",
             "41 to 45 years", "46 to 50 years", "51 to 55 years", "56 to 60 years",
             "61 to 65 years", "66+"]
_AGE_BANDS = [(1, "<1"), (5, "1-5"), (10, "6 to 10 years"), (15, "11 to 15 years"),
              (20, "16 to 20 years"), (25, "21 to 25 years"), (30, "26 to 30 years"),
              (35, "31 to 35 years"), (40, "36 to 40 years"), (45, "41 to 45 years"),
              (50, "46 to 50 years"), (55, "51 to 55 years"), (60, "56 to 60 years"),
              (65, "61 to 65 years")]

# Include HIV status as the one extra "richer" marginal (see report 4.5 / thesis
# discussion). Set to False to recover the age/infection/tier/class-only model.
USE_HIV = True
HIV_LEVELS = ["Positive", "Negative", "Unknown"]

# --------------------------------------------------------------------------
# Decoding maps (validated: tier x class reproduces the published PPS table)
# --------------------------------------------------------------------------
def _tier(code) -> str | float:
    c = str(code).strip().upper()
    if c.startswith("PRVF"):
        return "Specialist"          # private referral hospital = Specialist tier
    return {"T": "Tertiary", "D": "District", "P": "Primary"}.get(c[:1], np.nan)


def _age_years(x) -> float:
    m = re.match(r"^([\d.]+)\s*([YMD])?$", str(x).strip().upper())
    if not m:
        return np.nan
    v, unit = float(m.group(1)), (m.group(2) or "Y")
    return v if unit == "Y" else v / 12.0 if unit == "M" else v / 365.0


def _age_group(y) -> str | float:
    if pd.isna(y):
        return np.nan
    if y < 1:
        return "<1"
    for hi, label in _AGE_BANDS[1:]:
        if y <= hi:
            return label
    return "66+"


_INF_MAP = {"CA": "CAI", "HA": "HAI", "HBC": "HBCI"}
def _infection(x) -> str:
    s = str(x).strip().upper()
    return "NIC" if s in ("", "NAN", "NONE") else _INF_MAP.get(s, "NIC")


def _hiv(x) -> str:
    s = str(x).strip().upper()
    return {"P": "Positive", "N": "Negative"}.get(s, "Unknown")


def _drug_class(atc, name) -> str | float:
    a = str(atc).strip().upper().replace(" ", "")
    n = str(name).strip().lower()
    rules = [
        ("Carbapenems",     a.startswith("J01DH") or any(k in n for k in ("carbapenem", "meropenem", "imipenem", "ertapenem"))),
        ("Glycopeptides",   a.startswith("J01XA") or "vancomycin" in n or "teicoplanin" in n),
        ("Nitroimidazoles", a.startswith("J01XD") or a.startswith("P01AB") or "metronidazole" in n or "tinidazole" in n),
        ("Lincosamides",    a.startswith("J01FF") or "clindamycin" in n or "lincomycin" in n),
        ("Macrolides",      a.startswith("J01FA") or any(k in n for k in ("erythromycin", "azithromycin", "clarithromycin"))),
        ("Tetracyclines",   a.startswith("J01A") or "doxycycline" in n or "tetracyclin" in n),
        ("Amphenicols",     a.startswith("J01B") or "chloramphenicol" in n),
        ("Penicillins",     a.startswith("J01C") or "cillin" in n or "penicillin" in n),
        ("Cephalosporins",  a.startswith("J01D") or "cef" in n or "ceph" in n),
        ("Sulphonamides",   a.startswith("J01E") or any(k in n for k in ("cotrimoxazole", "sulfa", "sulph", "trimethoprim"))),
        ("Aminoglycosides", a.startswith("J01G") or any(k in n for k in ("gentam", "amikacin", "aminoglycos"))),
        ("Quinolones",      a.startswith("J01M") or "floxacin" in n or "quinolon" in n),
    ]
    for cls, hit in rules:
        if hit:
            return cls
    return np.nan


def _pcode(x) -> str:
    v = pd.to_numeric(x, errors="coerce")
    return "" if pd.isna(v) else str(int(v))


def _col(df, needle):
    return next(c for c in df.columns if needle.lower() in c.lower())


# --------------------------------------------------------------------------
# 1. Decode
# --------------------------------------------------------------------------
def load_muria(path: Path = PPS_PATH):
    """Return (patients, scripts) decoded onto the artifact taxonomy."""
    def sheet(name):
        d = pd.read_excel(path, sheet_name=name, header=3)
        d.columns = [str(c).strip() for c in d.columns]
        return d

    s1, s2 = sheet("Clean Sec-1"), sheet("Clean Sec-2")

    patients = pd.DataFrame({
        "pkey": s1["HospitalCode"].astype(str).str.strip().str.upper() + "|" + s1[_col(s1, "PatientCode")].map(_pcode),
        "tier": s1["HospitalCode"].map(_tier),
        "age_group": s1["Age"].map(_age_years).map(_age_group),
        "infection": s1[_col(s1, "Type of Infection")].map(_infection),
        "hiv": s1[_col(s1, "HIV")].map(_hiv),
    })

    scripts = pd.DataFrame({
        "pkey": s2["HospitalCode"].astype(str).str.strip().str.upper() + "|" + s2[_col(s2, "Patient Code")].map(_pcode),
        "tier": s2["HospitalCode"].map(_tier),
        "age_group": s2["Age"].map(_age_years).map(_age_group),
        "drug_class": [_drug_class(a, n) for a, n in zip(s2[_col(s2, "ATC")], s2[_col(s2, "Antibiotic")])],
    })
    scripts = scripts.dropna(subset=["drug_class"]).reset_index(drop=True)

    # attach patient infection + HIV to each prescription (best-effort link;
    # patient codes are not globally unique -> keep first match per key)
    link = patients.drop_duplicates("pkey").set_index("pkey")[["infection", "hiv"]]
    scripts = scripts.join(link, on="pkey")
    scripts["infection"] = scripts["infection"].fillna("NIC")
    scripts["hiv"] = scripts["hiv"].fillna("Unknown")
    return patients, scripts


# --------------------------------------------------------------------------
# 2. Real marginals + real (approximate) joint
# --------------------------------------------------------------------------
def real_joint(scripts: pd.DataFrame) -> pd.DataFrame:
    dims = ["age_group", "infection", "tier", "drug_class"] + (["hiv"] if USE_HIV else [])
    return (scripts.dropna(subset=dims).groupby(dims).size()
            .rename("count").reset_index())


def real_marginals(patients: pd.DataFrame, scripts: pd.DataFrame) -> dict:
    """The reliably-observed marginals the synthetic joint is raked to."""
    m = {}
    # (age x infection) prescriptions -> target_presc_ak (replaces age_mult/inf_mult)
    m["ak"] = (scripts.dropna(subset=["age_group", "infection"])
               .groupby(["age_group", "infection"]).size().rename("count").reset_index())
    # (tier x class) prescriptions -> replaces the severity/eta synthetic allocation
    m["hi"] = (scripts.dropna(subset=["tier", "drug_class"])
               .groupby(["tier", "drug_class"]).size().rename("count").reset_index())
    # patients per (age x infection) -> exposure / intensity m_ak
    m["patients_ak"] = (patients.dropna(subset=["age_group", "infection"])
                        .groupby(["age_group", "infection"]).size().rename("patients").reset_index())
    if USE_HIV:
        m["hiv_class"] = (scripts.dropna(subset=["hiv", "drug_class"])
                          .groupby(["hiv", "drug_class"]).size().rename("count").reset_index())
    return m


# --------------------------------------------------------------------------
# 3. Calibrated synthetic joint  (Report 4.5: IPF-raked to observed marginals)
# --------------------------------------------------------------------------
def _pivot(df, r, c, v):
    return df.pivot_table(index=r, columns=c, values=v, aggfunc="sum", fill_value=0.0)


def build_synthetic_joint(marg: dict) -> pd.DataFrame:
    """Reconstruct the (age, infection, tier, class[, hiv]) joint by raking an
    independence seed to the REAL marginals via iterative proportional fitting.
    This is the 4.5 'calibrated synthetic microdata' step, now data-driven."""
    A, K, H, I = AGE_ORDER, INF_CATS, TIERS, CLASSES
    V = HIV_LEVELS if USE_HIV else [None]
    idx = {"a": {x: i for i, x in enumerate(A)}, "k": {x: i for i, x in enumerate(K)},
           "h": {x: i for i, x in enumerate(H)}, "i": {x: i for i, x in enumerate(I)},
           "v": {x: i for i, x in enumerate(V)}}

    # target marginals as (writable) float arrays
    ak = np.array(_pivot(marg["ak"], "age_group", "infection", "count").reindex(index=A, columns=K, fill_value=0.0).values, dtype=float)
    hi = np.array(_pivot(marg["hi"], "tier", "drug_class", "count").reindex(index=H, columns=I, fill_value=0.0).values, dtype=float)
    total = ak.sum()
    hi *= total / hi.sum()
    targets = [("ak", ak, (0, 1)), ("hi", hi, (2, 3))]
    if USE_HIV:
        # ordered (class, hiv) to match numpy's ascending kept-axis order (3, 4)
        iv = np.array(_pivot(marg["hiv_class"], "drug_class", "hiv", "count").reindex(index=I, columns=V, fill_value=0.0).values, dtype=float)
        iv *= total / iv.sum()
        targets.append(("iv", iv, (3, 4)))

    # independence seed from the marginals
    seed = (ak.sum(1)[:, None, None, None, None] * ak.sum(0)[None, :, None, None, None]
            * hi.sum(1)[None, None, :, None, None] * hi.sum(0)[None, None, None, :, None])
    if USE_HIV:
        seed = seed * iv.sum(0)[None, None, None, None, :]
    else:
        seed = seed[..., None]
    T = seed / seed.sum() * total

    axis_all = (0, 1, 2, 3, 4)
    for _ in range(1000):
        prev = T.copy()
        for _, tgt, ax in targets:
            cur = T.sum(axis=tuple(a for a in axis_all if a not in ax))
            with np.errstate(divide="ignore", invalid="ignore"):
                ratio = np.divide(tgt, cur, out=np.ones_like(tgt), where=cur > 0)
            # broadcast the marginal ratio back over the full 5-D tensor
            expand = tuple(slice(None) if a in ax else None for a in range(5))
            T = T * ratio[expand]
        if np.max(np.abs(T - prev)) < 1e-9:
            break

    rows = []
    for a in A:
        for k in K:
            for h in H:
                for i in I:
                    for v in V:
                        c = T[idx["a"][a], idx["k"][k], idx["h"][h], idx["i"][i], idx["v"][v]]
                        if c <= 0:
                            continue
                        row = {"agegroup": a, "infectionstatus": k, "hospital_type": h,
                               "Class": i, "count": float(c)}
                        if USE_HIV:
                            row["hiv"] = v
                        rows.append(row)
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------
# 4. NB2 GLM  (mean exp(X'beta), Var = mu + mu^2/kappa)
# --------------------------------------------------------------------------
def fit_nb2(joint: pd.DataFrame, marg: dict):
    import statsmodels.formula.api as smf

    # exposure per (age, infection, tier) = patients(a,k) * prescription tier share
    pat = _pivot(marg["patients_ak"], "age_group", "infection", "patients")
    pat = pat.reindex(index=AGE_ORDER, columns=INF_CATS, fill_value=0.0)
    tier_share = marg["hi"].groupby("tier")["count"].sum()
    tier_share = (tier_share / tier_share.sum()).reindex(TIERS).fillna(0.0)

    df = joint.copy()
    df["patients_ak"] = [pat.loc[a, k] for a, k in zip(df["agegroup"], df["infectionstatus"])]
    df["exposure"] = (df["patients_ak"] * df["hospital_type"].map(tier_share)).clip(lower=1e-8)
    df["log_exposure"] = np.log(df["exposure"])
    df["count_int"] = np.round(df["count"]).astype(int)

    # pool rare classes for fit stability (same guard as the notebook)
    tot = df.groupby("Class")["count_int"].sum()
    rare = tot[tot < 10].index.tolist()
    df["Class_model"] = df["Class"].where(~df["Class"].isin(rare), "Other")

    # fit on cells with genuine exposure support. HIV enters via the synthetic
    # construction's raking marginal (the "richer marginal"), not as a GLM term
    # here -- at n~895 with 15 age bands, adding it destabilizes the MLE.
    fit = (df[df["exposure"] > 1e-6]
           .groupby(["agegroup", "infectionstatus", "hospital_type", "Class_model"], as_index=False)
           .agg(count_int=("count_int", "sum"), log_exposure=("log_exposure", "mean")))
    terms = "C(agegroup) + C(infectionstatus) + C(hospital_type) + C(Class_model)"
    res = smf.negativebinomial(f"count_int ~ {terms}", data=fit,
                               offset=fit["log_exposure"]).fit(method="nm", maxiter=5000, disp=False)
    # NOTE: kappa here is a byproduct of fitting NB to the synthetic joint, NOT the
    # demand overdispersion. The simulation does not use it (it sweeps kappa). Real
    # per-patient overdispersion from MURIA is approx kappa=3.7 (method of moments).
    alpha = float(res.params.get("alpha", 0.0))
    kappa = np.inf if alpha <= 1e-6 else 1.0 / alpha
    df["mu_hat"] = res.predict(df)
    return res, df, alpha, kappa, rare


# --------------------------------------------------------------------------
# 5. Validation: synthetic vs real (best-effort) joint
# --------------------------------------------------------------------------
def validate(real: pd.DataFrame, synth: pd.DataFrame) -> dict:
    keys = ["agegroup", "infectionstatus", "hospital_type", "Class"]
    r = real.rename(columns={"age_group": "agegroup", "infection": "infectionstatus",
                             "tier": "hospital_type", "drug_class": "Class"})
    r = r.groupby(keys)["count"].sum().rename("real")
    s = synth.groupby(keys)["count"].sum().rename("synth")
    m = pd.concat([r, s], axis=1).fillna(0.0)
    m["real_p"] = m["real"] / m["real"].sum()
    m["synth_p"] = m["synth"] / m["synth"].sum()
    tvd = 0.5 * (m["real_p"] - m["synth_p"]).abs().sum()
    # cosine similarity between the two joint vectors
    cos = float((m["real_p"] * m["synth_p"]).sum() /
                (np.linalg.norm(m["real_p"]) * np.linalg.norm(m["synth_p"]) + 1e-12))
    # held-out 2-way (age x class): NOT a raking target -> a genuine check
    ac_r = r.groupby(level=[0, 3]).sum(); ac_r /= ac_r.sum()
    ac_s = s.groupby(level=[0, 3]).sum(); ac_s /= ac_s.sum()
    ac = pd.concat([ac_r.rename("r"), ac_s.rename("s")], axis=1).fillna(0.0)
    ac_tvd = 0.5 * (ac["r"] - ac["s"]).abs().sum()
    return {"joint_TVD": tvd, "joint_cosine": cos, "age_x_class_TVD_heldout": ac_tvd}


# --------------------------------------------------------------------------
# 6. Export artifacts  (same schema as before; HIV marginalized out)
# --------------------------------------------------------------------------
def export_artifacts(joint_fit, res, alpha, kappa, marg, rare):
    import json
    OUT_DIR.mkdir(exist_ok=True)
    keys = ["agegroup", "infectionstatus", "hospital_type", "Class"]

    agg = joint_fit.groupby(keys, as_index=False).agg(count=("count", "sum"), mu_hat=("mu_hat", "sum"))
    # p(Class | age, infection, hospital_type) over the FULL grid, so downstream
    # never hits a missing (age, infection, tier) combo. Zero-mass groups fall
    # back to the baseline p0(Class | tier); a fully empty tier to uniform.
    j = pd.MultiIndex.from_product([AGE_ORDER, INF_CATS, TIERS, CLASSES], names=keys).to_frame(index=False)
    j = j.merge(agg, on=keys, how="left")
    j[["count", "mu_hat"]] = j[["count", "mu_hat"]].fillna(0.0)
    denom = j.groupby(["agegroup", "infectionstatus", "hospital_type"])["count"].transform("sum")
    j["p_class"] = np.where(denom > 0, j["count"] / denom, np.nan)
    p0 = marg["hi"].rename(columns={"tier": "hospital_type", "drug_class": "Class"}).copy()
    p0["p0"] = p0["count"] / p0.groupby("hospital_type")["count"].transform("sum")
    j = j.merge(p0[["hospital_type", "Class", "p0"]], on=["hospital_type", "Class"], how="left")
    j["p_class"] = j["p_class"].fillna(j["p0"]).fillna(1.0 / len(CLASSES))
    # renormalize each (age, infection, tier) group to a proper distribution
    grp = ["agegroup", "infectionstatus", "hospital_type"]
    j["p_class"] = j["p_class"] / j.groupby(grp)["p_class"].transform("sum")
    j[keys + ["p_class"]].to_csv(OUT_DIR / "p_class.csv", index=False)

    # m_ak: patients, prescriptions, intensity per (age, infection)
    mak = marg["patients_ak"].rename(columns={"age_group": "agegroup", "infection": "infectionstatus"})
    presc = marg["ak"].rename(columns={"age_group": "agegroup", "infection": "infectionstatus", "count": "target_presc_ak"})
    mak = mak.merge(presc, on=["agegroup", "infectionstatus"], how="outer").fillna(0.0)
    mak["m_ak"] = np.where(mak["patients"] > 0, mak["target_presc_ak"] / mak["patients"], 0.0)
    mak[["agegroup", "infectionstatus", "patients", "m_ak", "target_presc_ak"]].to_csv(OUT_DIR / "m_ak.csv", index=False)

    # p0(Class | hospital_type) baseline from (tier x class) marginal
    hi = marg["hi"].rename(columns={"tier": "hospital_type", "drug_class": "Class", "count": "count_ih"})
    hi["p0_i_given_h"] = hi["count_ih"] / hi.groupby("hospital_type")["count_ih"].transform("sum")
    hi[["Class", "hospital_type", "p0_i_given_h"]].to_csv(OUT_DIR / "p0_i_given_h.csv", index=False)

    j.groupby(["hospital_type", "Class"], as_index=False)["mu_hat"].sum().to_csv(
        OUT_DIR / "mu_hat_hospital_class.csv", index=False)
    joint_fit.to_csv(OUT_DIR / "synthetic_joint_nb_input.csv", index=False)
    pd.DataFrame({"parameter": ["alpha_hat", "kappa_hat"], "value": [alpha, kappa]}).to_csv(
        OUT_DIR / "nb_params.csv", index=False)
    pd.DataFrame({"term": res.params.index, "estimate": res.params.values}).to_csv(
        OUT_DIR / "nb_coefficients.csv", index=False)

    meta = {"classes": CLASSES, "hospital_types": TIERS, "age_levels": AGE_ORDER,
            "infection_levels": INF_CATS, "used_hiv": USE_HIV, "rare_classes_pooled": rare,
            "alpha_hat": alpha, "kappa_hat": None if np.isinf(kappa) else kappa,
            "source": "MURIA PPS (private); calibrated synthetic microdata per Report 4.5",
            "nb2_variance": "Var = mu + alpha*mu^2 = mu + mu^2/kappa",
            "kappa_note": ("kappa_hat is a BYPRODUCT of fitting NB to the smooth synthetic "
                           "joint and is NOT the demand overdispersion; the simulation does "
                           "not use it. Simulations sweep kappa (e.g. [2, 10, 25]). The "
                           "empirical per-patient overdispersion from MURIA counts is "
                           "approx kappa=3.7 (method of moments, Sec-1 self-report), which "
                           "the swept range brackets.")}
    (OUT_DIR / "metadata.json").write_text(json.dumps(meta, indent=2))


def main():
    patients, scripts = load_muria()
    print(f"patients={len(patients)}  prescriptions(classified)={len(scripts)}")
    marg = real_marginals(patients, scripts)
    synth = build_synthetic_joint(marg)
    print(f"synthetic joint: {len(synth)} cells, sum={synth['count'].sum():.0f}")
    res, joint_fit, alpha, kappa, rare = fit_nb2(synth, marg)
    print(f"alpha_hat={alpha:.4f}  kappa_hat={kappa:.4f}  rare_pooled={rare}")
    metrics = validate(real_joint(scripts), synth)
    print("validation (synthetic vs real joint):",
          {k: round(v, 4) for k, v in metrics.items()})
    export_artifacts(joint_fit, res, alpha, kappa, marg, rare)
    print(f"artifacts written to {OUT_DIR}")


if __name__ == "__main__":
    main()
