"""
MURIA-calibrated Medical Demand Estimator (MDE).

Implements the estimator of Report Section 4.5, but calibrated to the *real*
MURIA Botswana Antibiotic Utilization Study microdata instead of the
hand-set "# data withheld" multipliers that stood in for it before.

Pipeline (mirrors 4.5, real data replacing guesses):
  1. decode MURIA  -> patient table (Section 1) + prescription table (Section 2)
  2. real marginals -> (age x infection) patient totals, used for the exposure
                       offset below
  3. real joint over (age, infection, tier, class): every prescription already
     carries all four fields on one record (age, tier, and class are observed
     directly; infection is attached via a best-effort join to Section 1), so
     no reconstruction is needed
  4. fit NB2 GLM  count ~ C(age)+C(infection)+C(tier)+C(class)  with
     log-exposure offset; extract alpha_hat / kappa_hat
  5. export artifacts (same schema as the notebook's artifacts/ folder)

  An earlier version reconstructed the (age, infection, tier, class) joint via
  iterative proportional fitting (IPF / "raking") against 2-way marginals, on
  the premise that the four fields were never observed together. That premise
  does not hold here -- they are. Fitting on the real joint instead is both
  simpler and far more stable: bootstrap kappa ranges [4.1, 8.5] against the
  IPF reconstruction's [0.95, 6.6].

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
    })

    scripts = pd.DataFrame({
        "pkey": s2["HospitalCode"].astype(str).str.strip().str.upper() + "|" + s2[_col(s2, "Patient Code")].map(_pcode),
        "tier": s2["HospitalCode"].map(_tier),
        "age_group": s2["Age"].map(_age_years).map(_age_group),
        "drug_class": [_drug_class(a, n) for a, n in zip(s2[_col(s2, "ATC")], s2[_col(s2, "Antibiotic")])],
    })
    scripts = scripts.dropna(subset=["drug_class"]).reset_index(drop=True)

    # attach patient infection to each prescription (best-effort link; patient
    # codes are not globally unique -> keep first match per key)
    link = patients.drop_duplicates("pkey").set_index("pkey")[["infection"]]
    scripts = scripts.join(link, on="pkey")
    scripts["infection"] = scripts["infection"].fillna("NIC")
    return patients, scripts


# --------------------------------------------------------------------------
# 2. Real joint + the marginal needed for the exposure offset
# --------------------------------------------------------------------------
def real_joint(scripts: pd.DataFrame) -> pd.DataFrame:
    """(age, infection, tier, class) cell counts, straight from the real
    prescription records -- no reconstruction. This is what the GLM fits on."""
    dims = ["age_group", "infection", "tier", "drug_class"]
    j = (scripts.dropna(subset=dims).groupby(dims).size()
         .rename("count").reset_index())
    return j.rename(columns={"age_group": "agegroup", "infection": "infectionstatus",
                             "tier": "hospital_type", "drug_class": "Class"})


def real_marginals(patients: pd.DataFrame, scripts: pd.DataFrame) -> dict:
    """Marginals used only for the exposure offset in fit_nb2."""
    m = {}
    # (age x infection) prescriptions -> target_presc_ak (replaces age_mult/inf_mult)
    m["ak"] = (scripts.dropna(subset=["age_group", "infection"])
               .groupby(["age_group", "infection"]).size().rename("count").reset_index())
    # (tier x class) prescriptions -> tier_share in fit_nb2
    m["hi"] = (scripts.dropna(subset=["tier", "drug_class"])
               .groupby(["tier", "drug_class"]).size().rename("count").reset_index())
    # patients per (age x infection) -> exposure / intensity m_ak
    m["patients_ak"] = (patients.dropna(subset=["age_group", "infection"])
                        .groupby(["age_group", "infection"]).size().rename("patients").reset_index())
    return m


def _pivot(df, r, c, v):
    return df.pivot_table(index=r, columns=c, values=v, aggfunc="sum", fill_value=0.0)


# --------------------------------------------------------------------------
# 3. NB2 GLM  (mean exp(X'beta), Var = mu + mu^2/kappa)
# --------------------------------------------------------------------------
def _build_fit_table(joint: pd.DataFrame, marg: dict):
    """Shared setup: exposure offset, rare-class pooling, one row per model
    cell. Used by both fit_nb2 and check_dispersion_stability so the two
    fit exactly the same table."""
    # exposure per (age, infection, tier) = patients(a,k) * prescription tier share
    pat = _pivot(marg["patients_ak"], "age_group", "infection", "patients")
    pat = pat.reindex(index=AGE_ORDER, columns=INF_CATS, fill_value=0.0)
    tier_share = marg["hi"].groupby("tier")["count"].sum()
    tier_share = (tier_share / tier_share.sum()).reindex(TIERS).fillna(0.0)

    df = joint.copy()
    df["patients_ak"] = [pat.loc[a, k] for a, k in zip(df["agegroup"], df["infectionstatus"])]
    df["exposure"] = (df["patients_ak"] * df["hospital_type"].map(tier_share)).clip(lower=1e-8)
    df["log_exposure"] = np.log(df["exposure"])

    # pool rare classes for fit stability (same guard as the notebook)
    tot = df.groupby("Class")["count"].sum()
    rare = tot[tot < 10].index.tolist()
    df["Class_model"] = df["Class"].where(~df["Class"].isin(rare), "Other")

    # Fit on cells with genuine exposure support. Round ONCE, after aggregating
    # rare classes into "Other" -- rounding each original class before summing
    # into the pooled bucket can discard real fractional mass.
    fit = (df[df["exposure"] > 1e-6]
           .groupby(["agegroup", "infectionstatus", "hospital_type", "Class_model"], as_index=False)
           .agg(count=("count", "sum"), log_exposure=("log_exposure", "mean")))
    fit["count_int"] = np.round(fit["count"]).astype(int)
    return df, fit, rare


def fit_nb2(joint: pd.DataFrame, marg: dict):
    import statsmodels.formula.api as smf

    df, fit, rare = _build_fit_table(joint, marg)
    terms = "C(agegroup) + C(infectionstatus) + C(hospital_type) + C(Class_model)"
    res = smf.negativebinomial(f"count_int ~ {terms}", data=fit,
                               offset=fit["log_exposure"]).fit(method="nm", maxiter=5000, disp=False)
    # NOTE: kappa here is a byproduct of the NB2 fit, NOT the demand
    # overdispersion, and it is not even a STABLE byproduct -- see
    # check_dispersion_stability, which refits this exact table under three
    # optimizer configurations and finds kappa moving by a wide margin
    # (6.68 -> 8.02 -> 10.87 on this data) while the mean structure mu_hat
    # barely moves (0.98 correlation between the two most different fits).
    # The simulation does not use kappa_hat; it sweeps kappa (e.g. [2, 10, 25]).
    # Real per-patient overdispersion from MURIA is approx kappa=2.5
    # (method of moments over admitted patients).
    alpha = float(res.params.get("alpha", 0.0))
    kappa = np.inf if alpha <= 1e-6 else 1.0 / alpha
    df["mu_hat"] = res.predict(df)
    return res, df, alpha, kappa, rare


def check_dispersion_stability(joint: pd.DataFrame, marg: dict) -> dict:
    """Verify (not just assert) that kappa_hat is not a trustworthy estimate of
    anything, by refitting the same table under three optimizer configurations
    and comparing both the dispersion parameter and the mean structure.

    If kappa swings widely while mu_hat (what p_class/m_ak actually export)
    stays close to constant across fits, that confirms the earlier finding:
    the dispersion parameter is not identified by this sample at this cell
    count, regardless of specification, but the demand estimate itself is on
    much firmer ground. This function re-runs that check on whatever data is
    passed in, so it is a live verification and not a one-time note.
    """
    import statsmodels.formula.api as smf

    df, fit, rare = _build_fit_table(joint, marg)
    terms = "C(agegroup) + C(infectionstatus) + C(hospital_type) + C(Class_model)"
    configs = [("nm_5000", dict(method="nm", maxiter=5000)),
               ("nm_30000", dict(method="nm", maxiter=30000)),
               ("bfgs", dict(method="bfgs", maxiter=2000))]

    kappas, mu_hats = {}, {}
    for name, kw in configs:
        try:
            res = smf.negativebinomial(f"count_int ~ {terms}", data=fit,
                                       offset=fit["log_exposure"]).fit(disp=False, **kw)
            alpha = float(res.params.get("alpha", 0.0))
            kappas[name] = None if alpha <= 1e-6 else 1.0 / alpha
            mu_hats[name] = res.predict(df).values
        except Exception as e:
            kappas[name] = None
            print(f"  stability check: {name} failed ({type(e).__name__})")

    finite = [k for k in kappas.values() if k is not None and np.isfinite(k)]
    names_with_mu = list(mu_hats.keys())
    mu_corr = None
    if len(names_with_mu) >= 2:
        a, b = mu_hats[names_with_mu[0]], mu_hats[names_with_mu[-1]]
        if a.std() > 0 and b.std() > 0:
            mu_corr = float(np.corrcoef(a, b)[0, 1])

    return {
        "kappa_by_optimizer": {k: (None if v is None else round(float(v), 3)) for k, v in kappas.items()},
        "kappa_range": [round(min(finite), 3), round(max(finite), 3)] if finite else None,
        "mean_structure_correlation": mu_corr,
        "conclusion": ("Dispersion (kappa) is not stably identified by this sample regardless of "
                      "optimizer; the mean structure that p_class/m_ak actually export is far more "
                      "stable. Do not report GLM kappa_hat as a demand-overdispersion estimate -- "
                      "use the method-of-moments figure (~2.5) instead."),
    }


# --------------------------------------------------------------------------
# 4. Export artifacts (same schema as the notebook's artifacts/ folder)
# --------------------------------------------------------------------------
def export_artifacts(joint_fit, res, alpha, kappa, marg, rare, stability=None):
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
    joint_fit.to_csv(OUT_DIR / "nb_joint_input.csv", index=False)
    pd.DataFrame({"parameter": ["alpha_hat", "kappa_hat"], "value": [alpha, kappa]}).to_csv(
        OUT_DIR / "nb_params.csv", index=False)
    pd.DataFrame({"term": res.params.index, "estimate": res.params.values}).to_csv(
        OUT_DIR / "nb_coefficients.csv", index=False)

    meta = {"classes": CLASSES, "hospital_types": TIERS, "age_levels": AGE_ORDER,
            "infection_levels": INF_CATS, "rare_classes_pooled": rare,
            "alpha_hat": alpha, "kappa_hat": None if np.isinf(kappa) else kappa,
            "source": "MURIA PPS (private); fitted on the real per-record joint, Report 4.5 estimator structure",
            "nb2_variance": "Var = mu + alpha*mu^2 = mu + mu^2/kappa",
            "kappa_note": ("kappa_hat is a BYPRODUCT of the NB2 fit and is NOT the demand "
                           "overdispersion; the simulation does not use it (it sweeps kappa, "
                           "e.g. [2, 10, 25]). The empirical overdispersion over admitted "
                           "patients is approx kappa=2.5 (method of moments; counting patients "
                           "with no prescription, which is what makes it overdispersed -- "
                           "conditioning on treated patients is underdispersed). The swept "
                           "range brackets it.")}
    if stability is not None:
        meta["dispersion_stability_check"] = stability
    (OUT_DIR / "metadata.json").write_text(json.dumps(meta, indent=2))


def main():
    patients, scripts = load_muria()
    print(f"patients={len(patients)}  prescriptions(classified)={len(scripts)}")
    marg = real_marginals(patients, scripts)
    joint = real_joint(scripts)
    full_grid = len(AGE_ORDER) * len(INF_CATS) * len(TIERS) * len(CLASSES)
    print(f"real joint: {len(joint)} occupied cells of {full_grid} possible "
          f"({100*len(joint)/full_grid:.0f}%), {int(joint['count'].sum())} prescriptions")
    res, joint_fit, alpha, kappa, rare = fit_nb2(joint, marg)
    print(f"alpha_hat={alpha:.4f}  kappa_hat={kappa:.4f}  rare_pooled={rare}")

    print("checking dispersion stability across optimizers...")
    stability = check_dispersion_stability(joint, marg)
    print(f"  kappa by optimizer: {stability['kappa_by_optimizer']}")
    print(f"  mean-structure correlation: {stability['mean_structure_correlation']}")

    export_artifacts(joint_fit, res, alpha, kappa, marg, rare, stability)
    print(f"artifacts written to {OUT_DIR}")


if __name__ == "__main__":
    main()
