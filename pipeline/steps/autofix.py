"""BƯỚC 2/4 — Sửa tự động những lỗi bắt buộc mà máy sửa được AN TOÀN.   ★★

Test:  pytest tests/test_autofix.py -q

`fix(ds, issues, cfg) -> list[dict]`: duyệt `issues` (chỉ lỗi severity ERROR), sửa thẳng vào thư mục `ds`,
và trả về danh sách thay đổi; mỗi phần tử có khoá: image, line, action, before, after
(đây chính là file `03_fixes.csv` — bằng chứng pipeline đã làm gì, người có thể kiểm lại).
"""
from collections import defaultdict

import yaml

from ..common import ERROR, parse_yolo_line

DROP_CODES = {"BAD_FORMAT", "BAD_CLASS_ID", "BOX_ZERO", "DUP_BOX"}
REMOVE_IMG_CODES = {"LEAK_TEST", "CORRUPT_IMAGE", "BAD_SIZE"}


def _is_remove_image_code(code: str) -> bool:
    return code in REMOVE_IMG_CODES or code.startswith("DUP_IMAGE_")


def fix(ds, issues, cfg):
    fixes = []
    error_issues = [iss for iss in issues if iss.severity == ERROR]

    # 1. Xác định các ảnh cần xoá (DUP_IMAGE_*, LEAK_TEST, CORRUPT_IMAGE, BAD_SIZE)
    images_to_remove = {}
    for iss in error_issues:
        if _is_remove_image_code(iss.code) and iss.image not in images_to_remove:
            images_to_remove[iss.image] = iss.code

    for stem, reason_code in sorted(images_to_remove.items()):
        removed_any = False
        for img_p in ds.image_files():
            if img_p.stem == stem and img_p.exists():
                img_p.unlink()
                removed_any = True
        lab_p = ds.label_path(stem)
        if lab_p.exists():
            lab_p.unlink()
            removed_any = True
        if removed_any:
            fixes.append(
                {
                    "image": stem,
                    "line": "",
                    "action": "remove_image",
                    "before": reason_code,
                    "after": "(đã xoá ảnh và nhãn)",
                }
            )

    # 2. Sửa BAD_CLASS_NAME trong data.yaml (tối đa 1 lần)
    has_bad_class_name = any(iss.code == "BAD_CLASS_NAME" for iss in error_issues)
    yaml_p = getattr(ds, "yaml_path", None) or (ds.root / "data.yaml")
    if has_bad_class_name and yaml_p.exists():
        raw_yaml = yaml.safe_load(yaml_p.read_text(encoding="utf-8")) or {}
        old_names = raw_yaml.get("names")
        new_names = list(cfg["classes"])
        if old_names != new_names:
            raw_yaml["names"] = new_names
            raw_yaml["nc"] = len(new_names)
            yaml_p.write_text(
                yaml.safe_dump(raw_yaml, allow_unicode=True, sort_keys=False),
                encoding="utf-8",
            )
            fixes.append(
                {
                    "image": "data.yaml",
                    "line": "",
                    "action": "rename_classes",
                    "before": str(old_names),
                    "after": str(new_names),
                }
            )

    # 3. Ghi nhận MISSING_LABEL_FILE (không tạo file nhãn rỗng)
    missing_stems = sorted(
        {
            iss.image
            for iss in error_issues
            if iss.code == "MISSING_LABEL_FILE" and iss.image not in images_to_remove
        }
    )
    for stem in missing_stems:
        if not ds.label_path(stem).exists():
            fixes.append(
                {
                    "image": stem,
                    "line": "",
                    "action": "needs_label",
                    "before": "(không có file)",
                    "after": "chuyển người gán",
                }
            )

    # 4. Gom lỗi dòng theo từng file nhãn (bỏ qua ảnh đã xoá)
    line_actions = defaultdict(dict)  # stem -> {line_no: "drop" | "clip"}
    for iss in error_issues:
        if iss.image in images_to_remove or iss.line is None:
            continue
        if iss.code in DROP_CODES:
            line_actions[iss.image][iss.line] = "drop"
        elif iss.code == "BOX_OUT_OF_IMAGE":
            if line_actions[iss.image].get(iss.line) != "drop":
                line_actions[iss.image][iss.line] = "clip"

    for stem in sorted(line_actions.keys()):
        lab_p = ds.label_path(stem)
        if not lab_p.exists():
            continue
        orig_lines = lab_p.read_text(encoding="utf-8").splitlines()
        new_lines = []
        actions_map = line_actions[stem]

        for line_no, raw_line in enumerate(orig_lines, start=1):
            act = actions_map.get(line_no)
            if act == "drop":
                fixes.append(
                    {
                        "image": stem,
                        "line": line_no,
                        "action": "drop_line",
                        "before": raw_line.strip(),
                        "after": "(xoá dòng)",
                    }
                )
                continue

            if act == "clip":
                try:
                    cls_id, cx, cy, w, h = parse_yolo_line(raw_line)
                    x1 = max(0.0, min(1.0, cx - w / 2.0))
                    y1 = max(0.0, min(1.0, cy - h / 2.0))
                    x2 = max(0.0, min(1.0, cx + w / 2.0))
                    y2 = max(0.0, min(1.0, cy + h / 2.0))
                    nw = x2 - x1
                    nh = y2 - y1
                except ValueError:
                    nw, nh = 0.0, 0.0

                if nw <= 0.0 or nh <= 0.0:
                    fixes.append(
                        {
                            "image": stem,
                            "line": line_no,
                            "action": "drop_line",
                            "before": raw_line.strip(),
                            "after": "(xoá dòng)",
                        }
                    )
                    continue

                ncx = (x1 + x2) / 2.0
                ncy = (y1 + y2) / 2.0
                clipped_str = f"{cls_id} {ncx:.6f} {ncy:.6f} {nw:.6f} {nh:.6f}"
                new_lines.append(clipped_str)
                fixes.append(
                    {
                        "image": stem,
                        "line": line_no,
                        "action": "clip_box",
                        "before": raw_line.strip(),
                        "after": clipped_str,
                    }
                )
            else:
                new_lines.append(raw_line)

        out_text = "\n".join(new_lines)
        if orig_lines:
            out_text += "\n"
        lab_p.write_text(out_text, encoding="utf-8")

    return fixes
