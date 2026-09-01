import cv2
from pathlib import Path

work_dir = Path(r"c:\websites\ai video production tool\storage\deliverables\voxpipe_0901_profitbricks")
vid_path = work_dir / "edited.mp4"
qc_dir = work_dir / "qc_audit"
qc_dir.mkdir(parents=True, exist_ok=True)

cap = cv2.VideoCapture(str(vid_path))
fps = cap.get(cv2.CAP_PROP_FPS)

audit_timestamps = [
    ("beat1_hook", 1.5),
    ("beat2_split_gold_rupee", 5.0),
    ("beat3_explainer_dollar_flow", 11.0),
    ("beat4_split_formula", 18.0),
    ("beat5_explainer_3_scenarios", 26.0),
    ("beat6_character_hud_tickers", 34.0),
    ("beat7_split_checklist", 41.0),
    ("beat8_profitbricks_outro", 46.0)
]

for name, sec in audit_timestamps:
    f_num = int(sec * fps)
    cap.set(cv2.CAP_PROP_POS_FRAMES, f_num)
    ret, frame = cap.read()
    if ret:
        out_f = qc_dir / f"{name}.jpg"
        cv2.imwrite(str(out_f), frame)
        print(f"Saved: {out_f.name} at {sec}s")

cap.release()
print("All 8 QC audit frames saved successfully!")
