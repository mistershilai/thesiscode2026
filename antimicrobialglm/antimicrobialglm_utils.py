import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf

def estimate_antimicrobial_demand(pop_age_df, by=["agegroup", "Class"]):
    """
    Estimate antimicrobial demand by age group and class using negative binomial GLM.
    Args:
        pop_age_df (pd.DataFrame): Population breakdown DataFrame (must include age group column).
        by (list): Columns to group output by (default: ["agegroup", "Class"]).
    Returns:
        pd.DataFrame: DataFrame with demand estimates per group.
        dict: Overdispersion parameters by antimicrobial class.
    """
    # Load and prepare infection data 
    import os
    glm_dir = os.path.dirname(os.path.abspath(__file__))
    df = pd.read_csv(os.path.join(glm_dir, "DocumentedInfectionbyAgeGroup.csv"))
    df_clean = df.iloc[1:].copy()
    df_clean.columns = [
        "agegroup", "admissions", "cai_count", "cai_pct", "hai_count", "hai_pct", "hbci_count", "hbci_pct", "nic_count", "nic_pct"
    ]
    num_cols = ["admissions","cai_count","hai_count","hbci_count","nic_count"]
    for col in num_cols:
        df_clean[col] = pd.to_numeric(df_clean[col], errors="coerce").fillna(0).astype(int)
    coarse_map = {
        "0–29 days": "<1", "1 to 11 months": "<1", "1 to 5 years": "1-5", "6 to 10 years": "6-10", "11 to 15 years": "11-15",
        "16 to 20 years": "16-20", "21 to 25 years": "21-25", "26 to 30 years": "26-30", "31 to 35 years": "31-35",
        "36 to 40 years": "36-40", "41 to 45 years": "41-45", "46 to 50 years": "46-50", "51 to 55 years": "51-55",
        "56 to 60 years": "56-60", "61 to 65 years": "61-65", "66 to 70 years": "66+", "71 to 75 years": "66+",
        "76 to 80 years": "66+", "81 to 85 years": "66+", "86 to 90 years": "66+", "91 to 95 years": "66+", "96+ years": "66+"
    }
    df_clean["coarse_age"] = df_clean["agegroup"].map(coarse_map)
    grouped = df_clean.groupby("coarse_age", as_index=False).agg({
        "admissions":"sum", "cai_count":"sum", "hai_count":"sum", "hbci_count":"sum", "nic_count":"sum"
    })
    rows = []
    for _, row in grouped.iterrows():
        age = row["coarse_age"]
        a = row["admissions"]
        c = row["cai_count"]
        h = row["hai_count"]
        b = row["hbci_count"]
        nic = row["nic_count"]
        none = a - (c + h + b + nic)
        rows += [{"agegroup": age, "infectionstatus": "cai"}] * c
        rows += [{"agegroup": age, "infectionstatus": "hai"}] * h
        rows += [{"agegroup": age, "infectionstatus": "hbci"}] * b
        rows += [{"agegroup": age, "infectionstatus": "nic"}] * nic
        rows += [{"agegroup": age, "infectionstatus": "none"}] * none
    reconstructed_df = pd.DataFrame(rows)
    # Load antimicrobial classes 
    classes = pd.read_csv(os.path.join(glm_dir, "AntibioticClassesAcrossHealthFacilities.csv"))
    def extract_count(x):
        s = str(x)
        parts = s.split()
        num = ''.join(ch for ch in parts[0] if ch.isdigit())
        return int(num) if num.isdigit() else 0
    classes["count"] = classes["n = 982 (%)"].apply(extract_count)
    total_prescriptions = 711
    n_patients = 982
    classes["proportion"] = classes["count"] / total_prescriptions
    M = total_prescriptions / n_patients
    classes["expected_per_patient"] = classes["proportion"] * M
    expected_long = classes[["Class", "expected_per_patient"]].copy()
    reconstructed_with_class = (
        reconstructed_df.assign(key=1).merge(expected_long.assign(key=1), on="key").drop(columns="key")
    )
    # GLM setup 
    df_glm = reconstructed_with_class.copy()
    age_dummies = pd.get_dummies(df_glm["agegroup"], prefix="age", drop_first=True)
    inf_dummies = pd.get_dummies(df_glm["infectionstatus"], prefix="inf", drop_first=True)
    age_dummies.columns = (
        age_dummies.columns.str.replace("-", "_", regex=False).str.replace("<", "lt", regex=False).str.replace(">", "gt", regex=False)
    )
    inf_dummies.columns = (
        inf_dummies.columns.str.replace("-", "_", regex=False).str.replace("<", "lt", regex=False).str.replace(">", "gt", regex=False)
    )
    df_glm = pd.concat([df_glm, age_dummies, inf_dummies], axis=1)
    df_glm["y"] = df_glm["expected_per_patient"]
    predictor_cols = list(age_dummies.columns) + list(inf_dummies.columns)
    rhs = " + ".join(predictor_cols)
    df_model = df_glm.drop(columns=["agegroup", "infectionstatus", "Class"])
    # Fit negative binomial GLM per antimicrobial class
    models = {}
    mu_predictions = {}
    overdispersion = {}
    for class_name in df_glm["Class"].unique():
        sub = df_glm[df_glm["Class"] == class_name].copy()
        sub_model = sub.drop(columns=["agegroup", "infectionstatus", "Class"])
        formula = "y ~ " + rhs
        model = smf.glm(formula=formula, data=sub_model, family=sm.families.NegativeBinomial()).fit()
        models[class_name] = model
        mu_predictions[class_name] = model.predict(sub_model)
        overdispersion[class_name] = model.scale
    # --- Assemble predictions ---
    prediction_frames = []
    for class_name in df_glm["Class"].unique():
        sub = df_glm[df_glm["Class"] == class_name].copy()
        sub_model = sub.drop(columns=["agegroup", "infectionstatus", "Class"])
        sub["mu"] = mu_predictions[class_name]
        prediction_frames.append(sub[["agegroup", "infectionstatus", "Class", "mu"]])
    glm_output = pd.concat(prediction_frames, ignore_index=True)
    # --- Merge with population breakdown ---
    # Detect age group column name (could be 'agegroup' or 'AgeGroup')
    age_col = None
    for col in pop_age_df.columns:
        if col.lower() == 'agegroup':
            age_col = col
            break
    
    if age_col:
        pop_counts = pop_age_df.groupby(age_col).agg({"Population": "sum"}).reset_index()
        pop_counts.rename(columns={age_col: "agegroup"}, inplace=True)
        # Normalize age groups: replace en-dash with hyphen for matching
        pop_counts["agegroup"] = pop_counts["agegroup"].str.replace('–', '-')
    
    # Map by columns to internal names for grouping
    by_mapped = []
    for col in by:
        if col.lower() == 'agegroup':
            by_mapped.append('agegroup')
        else:
            by_mapped.append(col)
    
    # FIX: Aggregate FIRST (to get mean mu per age-class), THEN multiply by population
    # This prevents the "admissions squared" bug where each admission row was counted separately
    glm_aggregated = glm_output.groupby(by_mapped, as_index=False)["mu"].mean()
    
    if age_col:
        glm_aggregated = glm_aggregated.merge(pop_counts, on="agegroup", how="left")
        glm_aggregated["demand_estimate"] = glm_aggregated["mu"] * glm_aggregated["Population"]
    else:
        glm_aggregated["demand_estimate"] = glm_aggregated["mu"]
    
    return glm_aggregated[by_mapped + ["demand_estimate"]], overdispersion
