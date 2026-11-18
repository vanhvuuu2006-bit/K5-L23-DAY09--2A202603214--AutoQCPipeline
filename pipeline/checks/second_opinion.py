"""CHECK 6 — Ý kiến thứ hai: so nhãn với một model LỚN HƠN (yolo26l).   ★★★ (khó nhất, đáng điểm nhất)

Test:  pytest tests/test_second_opinion.py -q

Máy kiểm quy tắc, người kiểm ý nghĩa (slide). Các lỗi như thiếu nhãn / gán nhầm lớp hợp lệ / box lỏng
KHÔNG bắt được bằng quy tắc cú pháp. Ta nhờ một model mạnh hơn "nhìn lại" và CHỈ CẢNH BÁO (model cũng có thể sai):
những ảnh bị cờ sẽ vào hàng đợi cho NGƯỜI duyệt.

`preds[stem]` = list `[id_lớp, conf, cx, cy, w, h]` của model (lấy qua `get_preds(ds, cfg, "checker")` nếu preds=None).
`L = ds.valid_boxes(stem)` = list `(id_lớp, cx, cy, w, h)` của nhãn (đã bỏ dòng hỏng).
Ngưỡng ở `cfg["second_opinion"]`: conf, min_area_px, fp_conf, iou_missing, iou_match, iou_loose.

Thuật toán gợi ý, với từng ảnh (bỏ qua ảnh không có trong preds hoặc không có file nhãn):
  P = dự đoán có conf >= conf  VÀ diện tích px (w*W * h*H) >= min_area_px
  Với mỗi dự đoán r trong P: lấy các nhãn có IoU(r, nhãn) >= iou_missing  (cands)
   - không có cands                            -> POSSIBLE_MISSING     (model thấy vật mà nhãn không có box)
   - có cands cùng lớp, tốt nhất IoU < iou_loose -> POSSIBLE_LOOSE_BOX  (đúng vật, box lỏng/lệch)
   - không có cands cùng lớp, nhưng cands tốt nhất IoU >= iou_match (khác lớp) -> POSSIBLE_WRONG_CLASS
  Với mỗi dòng nhãn hợp lệ: nếu IoU với MỌI dự đoán (conf >= fp_conf, không lọc diện tích) đều < iou_missing
                                             -> POSSIBLE_FALSE_POS  (box nhãn không khớp vật nào model thấy; Issue.line = số dòng)

Chi tiết các ca biên (test kiểm đúng các ca này)
- `cands` gồm nhãn MỌI lớp có IoU >= iou_missing; "tốt nhất cùng lớp" = cands cùng lớp có IoU lớn nhất; "tốt nhất khác lớp" tương tự với cands khác lớp.
- Thứ tự quyết định cho mỗi dự đoán: (1) cands rỗng -> MISSING. (2) có cands cùng lớp: IoU tốt nhất < iou_loose -> LOOSE_BOX, ngược lại KHÔNG cờ
  (nhãn đúng lớp đã phủ vật này, kể cả khi còn nhãn khác lớp chồng lên). (3) không có cands cùng lớp: nếu IoU tốt nhất khác lớp >= iou_match -> WRONG_CLASS;
  nếu chỉ có khác lớp với IoU trong [iou_missing, iou_match) -> không cờ gì (mơ hồ: để cho FALSE_POS / lần duyệt khác).
- Một dự đoán sinh tối đa MỘT issue (MISSING / LOOSE_BOX / WRONG_CLASS); một ảnh có thể có nhiều issue.
- Thứ tự issue: theo `ds.image_files()` rồi theo thứ tự dự đoán trong `preds[stem]`, cuối cùng là các FALSE_POS theo số dòng; `Issue.image` = stem, `Issue.line` chỉ đặt cho FALSE_POS.

Lưu ý số dòng: dùng `ds.read_label_lines(stem)` (giữ số dòng gốc, kể cả dòng hỏng/trống) để lấy `Issue.line`; `valid_boxes` KHÔNG giữ số dòng.

Tất cả severity WARN; `Issue.extra` nên có {"conf": ...} hoặc {"iou": ...} (hàng đợi duyệt dùng conf để xếp ưu tiên).

Gợi ý
- `iou_xywh` có sẵn. Dòng nhãn hỏng không được làm script chết (dùng `ds.valid_boxes` và `parse_yolo_line` trong try).
- Kết quả phụ thuộc mạnh vào ngưỡng: calibrate chúng ở Bước 3 thay vì đoán.
"""
from ..common import WARN, Issue, iou_xywh, parse_yolo_line  # noqa: F401
from ..model_cache import get_preds  # noqa: F401


def run(ds, cfg, preds=None):
    # raise NotImplementedError("check second_opinion chưa làm")
    if preds is None:
        preds = get_preds(ds, cfg, "checker")

    c = cfg["second_opinion"]
    conf_thr = c["conf"]
    min_area_px = c["min_area_px"]
    fp_conf = c["fp_conf"]
    iou_missing = c["iou_missing"]
    iou_match = c["iou_match"]
    iou_loose = c["iou_loose"]
    n_classes = len(ds.classes)

    issues = []

    for img_path in ds.image_files():
        stem = img_path.stem
        if stem not in preds or not ds.label_path(stem).exists():
            continue

        img_size = ds.image_size(stem)
        if img_size is None:
            continue
        img_w, img_h = img_size

        raw_preds = preds[stem]
        valid_labels = ds.valid_boxes(stem)

        # 1. Duyet tung du doan cua model theo thu tu trong preds[stem]
        for pred in raw_preds:
            p_cls, p_conf, p_cx, p_cy, p_w, p_h = pred
            p_cls = int(p_cls)
            area_px = (p_w * img_w) * (p_h * img_h)
            if p_conf < conf_thr or area_px < min_area_px:
                continue

            p_box = (p_cx, p_cy, p_w, p_h)
            cands = []
            for l_cls, l_cx, l_cy, l_w, l_h in valid_labels:
                iou = iou_xywh(p_box, (l_cx, l_cy, l_w, l_h))
                if iou >= iou_missing:
                    cands.append((int(l_cls), iou))

            if not cands:
                issues.append(
                    Issue(
                        "second_opinion",
                        WARN,
                        "POSSIBLE_MISSING",
                        stem,
                        f"Model phat hien lop {p_cls} (conf={p_conf:.2f}) nhung chua co box nhan",
                        extra={"conf": float(p_conf)},
                    )
                )
                continue

            same_cls_ious = [iou for l_cls, iou in cands if l_cls == p_cls]
            if same_cls_ious:
                best_same_iou = max(same_cls_ious)
                if best_same_iou < iou_loose:
                    issues.append(
                        Issue(
                            "second_opinion",
                            WARN,
                            "POSSIBLE_LOOSE_BOX",
                            stem,
                            f"Box nhan lop {p_cls} co the bi long/lech (IoU={best_same_iou:.2f} < {iou_loose})",
                            extra={"conf": float(p_conf), "iou": float(best_same_iou)},
                        )
                    )
                continue

            diff_cls_ious = [iou for l_cls, iou in cands if l_cls != p_cls]
            if diff_cls_ious:
                best_diff_iou = max(diff_cls_ious)
                if best_diff_iou >= iou_match:
                    issues.append(
                        Issue(
                            "second_opinion",
                            WARN,
                            "POSSIBLE_WRONG_CLASS",
                            stem,
                            f"Co the gan nham lop (model du doan lop {p_cls}, IoU={best_diff_iou:.2f})",
                            extra={"conf": float(p_conf), "iou": float(best_diff_iou)},
                        )
                    )

        # 2. Duyet tung dong nhan hop le goc de tim POSSIBLE_FALSE_POS
        fp_preds = [
            (pred[2], pred[3], pred[4], pred[5])
            for pred in raw_preds
            if pred[1] >= fp_conf
        ]
        for item in ds.read_label_lines(stem):
            line_no, raw_line = item if isinstance(item, tuple) else (None, item)
            if not raw_line.strip():
                continue
            try:
                l_cls, l_cx, l_cy, l_w, l_h = parse_yolo_line(raw_line)
            except ValueError:
                continue
            if l_cls < 0 or l_cls >= n_classes or l_w <= 0 or l_h <= 0:
                continue

            l_box = (l_cx, l_cy, l_w, l_h)
            max_iou = max((iou_xywh(l_box, pb) for pb in fp_preds), default=0.0)
            if max_iou < iou_missing:
                issues.append(
                    Issue(
                        "second_opinion",
                        WARN,
                        "POSSIBLE_FALSE_POS",
                        stem,
                        f"Box nhan dong {line_no} khong khop voi vat the nao model phat hien (max IoU={max_iou:.2f})",
                        line=line_no,
                        extra={"iou": float(max_iou)},
                    )
                )

    return issues
