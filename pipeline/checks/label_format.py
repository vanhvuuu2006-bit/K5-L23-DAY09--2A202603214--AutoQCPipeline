"""CHECK 2 — Dòng nhãn YOLO: sai định dạng, ID lớp lạ, box tràn ảnh, box rỗng, box lặp.   (Script 2 trong slide)   ★★

Test:  pytest tests/test_label_format.py -q

Mỗi dòng nhãn: `id cx cy w h` (5 số, toạ độ 0–1). Trả về list[Issue]; `Issue.line` = số dòng (đếm từ 1).

| code             | severity | khi nào                                                                  |
|------------------|----------|--------------------------------------------------------------------------|
| BAD_FORMAT       | ERROR    | không đúng 5 cột số (dùng `parse_yolo_line`, bắt `ValueError`)           |
| BAD_CLASS_ID     | ERROR    | id lớp ngoài 0..len(ds.classes)-1                                        |
| BOX_ZERO         | ERROR    | w <= 0 hoặc h <= 0                                                       |
| BOX_OUT_OF_IMAGE | ERROR    | mép box vượt [0,1] quá `cfg["label_format"]["overflow_tol"]`; extra={"overflow": mức tràn} |
| DUP_BOX          | ERROR    | cùng lớp với một dòng TRƯỚC ĐÓ và IoU > `dup_box_iou`; báo ở dòng SAU    |
| BOX_TINY         | WARN     | cạnh ngắn của box (px) < `min_box_px`  (cần `ds.image_size(stem)`)       |
| BOX_HUGE         | WARN     | w*h > `max_box_frac`                                                     |
"""
from ..common import ERROR, WARN, Issue, iou_xywh, parse_yolo_line


def run(ds, cfg):
    issues = []
    c = cfg["label_format"]
    overflow_tol = c["overflow_tol"]
    dup_box_iou = c["dup_box_iou"]
    min_box_px = c["min_box_px"]
    max_box_frac = c["max_box_frac"]
    n_classes = len(ds.classes)

    for lab_path in sorted(ds.label_files()):
        stem = lab_path.stem
        raw_lines = lab_path.read_text(encoding="utf-8").splitlines()
        img_size = ds.image_size(stem)
        seen_boxes = []

        for line_no, line in enumerate(raw_lines, start=1):
            if not line.strip():
                continue

            try:
                cls_id, cx, cy, w, h = parse_yolo_line(line)
            except ValueError as e:
                issues.append(Issue("label_format", ERROR, "BAD_FORMAT", stem, str(e), line=line_no))
                continue

            if cls_id < 0 or cls_id >= n_classes:
                issues.append(Issue("label_format", ERROR, "BAD_CLASS_ID", stem, f"id lớp không hợp lệ: {cls_id}", line=line_no))
                continue

            if w <= 0 or h <= 0:
                issues.append(Issue("label_format", ERROR, "BOX_ZERO", stem, f"kích thước box <= 0 ({w}, {h})", line=line_no))
                continue

            x1, y1 = cx - w / 2.0, cy - h / 2.0
            x2, y2 = cx + w / 2.0, cy + h / 2.0
            overflow = max(0.0, -x1, -y1, x2 - 1.0, y2 - 1.0)
            if overflow > overflow_tol:
                issues.append(
                    Issue(
                        "label_format",
                        ERROR,
                        "BOX_OUT_OF_IMAGE",
                        stem,
                        f"box tràn khỏi biên ảnh (mức tràn {overflow:.4f})",
                        line=line_no,
                        extra={"overflow": overflow},
                    )
                )

            box = (cx, cy, w, h)
            is_dup = any(
                prev_cls == cls_id and iou_xywh(prev_box, box) > dup_box_iou
                for prev_cls, prev_box in seen_boxes
            )
            if is_dup:
                issues.append(Issue("label_format", ERROR, "DUP_BOX", stem, "box trùng lặp với dòng trước đó", line=line_no))
            seen_boxes.append((cls_id, box))

            if img_size is not None:
                img_w, img_h = img_size
                short_side_px = min(w * img_w, h * img_h)
                if short_side_px < min_box_px:
                    issues.append(
                        Issue(
                            "label_format",
                            WARN,
                            "BOX_TINY",
                            stem,
                            f"box quá nhỏ ({short_side_px:.1f} px < {min_box_px} px)",
                            line=line_no,
                        )
                    )

            if w * h > max_box_frac:
                issues.append(
                    Issue(
                        "label_format",
                        WARN,
                        "BOX_HUGE",
                        stem,
                        f"diện tích box quá lớn ({w * h:.3f} > {max_box_frac})",
                        line=line_no,
                    )
                )

    return issues
