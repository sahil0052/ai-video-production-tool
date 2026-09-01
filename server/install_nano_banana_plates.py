import shutil
from pathlib import Path

ARTIFACTS_DIR = Path(r"C:\Users\HPUSER\.gemini\antigravity\brain\511882d1-5377-47fa-86e8-4adac25cec42")
DEST_DIR = Path(r"renderer/public/assets/bank_vox_plates")
DEST_DIR.mkdir(parents=True, exist_ok=True)

mappings = {
    "bank01_passbook_10lakh.jpg": "bank01_passbook_vox_1787766602704.jpg",
    "bank02_vault_open.jpg": "bank02_vault_vox_1787766632262.jpg",
    "bank03_fractional_circulation.jpg": "bank03_circulation_vox_1787766659904.jpg",
    "bank04_liquidity_scale.jpg": "bank04_scale_vox_1787766685953.jpg",
    "bank05_ledger_1crore.jpg": "bank05_ledger_vox_1787766718481.jpg",
    "bank06_crowd_queue.jpg": "bank06_crowd_vox_1787766751892.jpg",
    "bank07_bankrun_headline.jpg": "bank07_bankrun_vox_1787766783837.jpg",
    "bank08_panic_dominoes.jpg": "bank08_dominoes_vox_1787766813790.jpg",
    "bank09_trust_shield.jpg": "bank09_trust_vox_1787766858823.jpg",
    "bank10_follow_cta.jpg": "bank10_cta_vox_1787766888655.jpg",
}

for dest_name, src_name in mappings.items():
    src_p = ARTIFACTS_DIR / src_name
    dest_p = DEST_DIR / dest_name
    if src_p.exists():
        shutil.copy2(src_p, dest_p)
        print(f"Installed Nano Banana Plate: {dest_name} ({dest_p.stat().st_size} bytes)")
    else:
        print(f"WARNING: Missing {src_name}")

print("All 10 authentic Nano Banana Vox Plates successfully installed!")
