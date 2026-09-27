"""
AEGIS MIND - Synthetic Data Simulator

Generates an anonymized, clearly-labeled synthetic dataset standing in for
real CRPF personnel data (unavailable for a student prototype).

Every row uses a pseudonymous personnel_code. No real names, ranks, or units.
Run: python generate_synthetic_data.py
Output: ../data/synthetic_personnel_data.csv
"""
import numpy as np
import pandas as pd
from pathlib import Path

RNG = np.random.default_rng(42)
N_PERSONNEL = 1200


def generate():
    ids = [f"PID-{str(i).zfill(5)}" for i in range(1, N_PERSONNEL + 1)]
    unit_codes = [f"UNIT-{str(u).zfill(2)}" for u in range(1, 41)]

    weekly_duty_hours = np.clip(RNG.normal(52, 14, N_PERSONNEL), 30, 96)
    consecutive_duty_days = np.clip(RNG.poisson(6, N_PERSONNEL), 0, 30)
    leave_days_last_90 = np.clip(RNG.normal(9, 6, N_PERSONNEL), 0, 30).astype(int)
    night_shift_ratio = np.clip(RNG.beta(2, 5, N_PERSONNEL), 0, 1)
    deployment_months_last_year = np.clip(RNG.normal(5, 3, N_PERSONNEL), 0, 12)
    transfer_count_last_2yr = RNG.poisson(1.2, N_PERSONNEL)
    training_load_hours = np.clip(RNG.normal(20, 10, N_PERSONNEL), 0, 80)
    overdue_leave_flag = (leave_days_last_90 < 3) & (RNG.random(N_PERSONNEL) < 0.6)

    # Voluntary wellness responses (correlated with the organizational load,
    # plus noise, to simulate a realistic-but-synthetic relationship).
    load_index = (
        0.30 * (weekly_duty_hours / 96)
        + 0.15 * (consecutive_duty_days / 30)
        + 0.15 * (1 - leave_days_last_90 / 30)
        + 0.15 * night_shift_ratio
        + 0.15 * (deployment_months_last_year / 12)
        + 0.10 * (transfer_count_last_2yr / 5).clip(max=1)
    )

    def scaled_scale_1_5(base, noise_sd=0.6):
        val = 1 + base * 4 + RNG.normal(0, noise_sd, N_PERSONNEL)
        return np.clip(np.round(val), 1, 5).astype(int)

    stress_level = scaled_scale_1_5(load_index)
    fatigue_level = scaled_scale_1_5(load_index * 0.9 + 0.1 * (1 - night_shift_ratio))
    mood = scaled_scale_1_5(1 - load_index)  # inverse
    sleep_quality = scaled_scale_1_5(1 - (load_index * 0.8 + night_shift_ratio * 0.2))
    perceived_workload = scaled_scale_1_5(load_index)

    # Ground-truth-ish labels for supervised training (synthetic only).
    stress_prob = np.clip(load_index + RNG.normal(0, 0.08, N_PERSONNEL), 0, 1)
    stress_label = (stress_prob > 0.55).astype(int)  # 1 = elevated stress risk

    burnout_index = np.clip(
        0.5 * load_index + 0.3 * (fatigue_level / 5) + 0.2 * (1 - sleep_quality / 5)
        + RNG.normal(0, 0.05, N_PERSONNEL),
        0, 1,
    )

    df = pd.DataFrame({
        "personnel_code": ids,
        "unit_code": RNG.choice(unit_codes, N_PERSONNEL),
        "weekly_duty_hours": weekly_duty_hours.round(1),
        "consecutive_duty_days": consecutive_duty_days,
        "leave_days_last_90": leave_days_last_90,
        "night_shift_ratio": night_shift_ratio.round(2),
        "deployment_months_last_year": deployment_months_last_year.round(1),
        "transfer_count_last_2yr": transfer_count_last_2yr,
        "training_load_hours": training_load_hours.round(1),
        "overdue_leave_flag": overdue_leave_flag,
        "stress_level": stress_level,
        "mood": mood,
        "sleep_quality": sleep_quality,
        "fatigue_level": fatigue_level,
        "perceived_workload": perceived_workload,
        "burnout_index": burnout_index.round(3),
        "stress_label": stress_label,  # supervised target
        "data_source": "SYNTHETIC_DEMO_DATA",
    })
    return df


if __name__ == "__main__":
    df = generate()
    out_dir = Path(__file__).resolve().parent.parent / "data"
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / "synthetic_personnel_data.csv"
    df.to_csv(out_path, index=False)
    print(f"Generated {len(df)} synthetic personnel records -> {out_path}")
    print("NOTE: This is 100% synthetic/demo data. No real personnel data used.")
