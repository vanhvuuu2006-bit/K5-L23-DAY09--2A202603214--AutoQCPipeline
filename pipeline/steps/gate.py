"""BƯỚC 4 — Cửa chặn: quyết định Release / Hold / Rework.   ★

Test:  pytest tests/test_gate.py -q

Cây quyết định Day 07 (slide Day 09: "Lỗi bắt buộc chặn pipeline; lỗi cảnh báo chuyển người xem"):

  còn ≥ 1 lỗi bắt buộc (severity ERROR)                          -> "Rework"
  không còn lỗi bắt buộc, nhưng tỉ lệ ẢNH còn cảnh báo
      >= cfg["gate"]["warn_ratio_hold"]                          -> "Hold"
  còn lại                                                        -> "Release"

Tỉ lệ cảnh báo = (số ẢNH khác nhau có ≥ 1 cảnh báo) / (tổng số ảnh).  Chú ý:
- chỉ đếm issue có `image` nằm trong `image_stems` (bỏ "<dataset>", "data.yaml");
- bỏ qua ảnh nằm trong `reviewed` (người đã xem, cảnh báo của ảnh đó coi như đã xử lý) — nhưng LỖI BẮT BUỘC thì không bao giờ được bỏ qua;
- mẫu số là số ảnh, không phải số issue.

Trả về dict: decision, n_errors, n_warn_images, n_images, warn_ratio (làm tròn 4 chữ số), reasons (list[str], giải thích bằng tiếng Việt, có số liệu).
"""
from ..common import ERROR, WARN  # noqa: F401


def decide(issues, image_stems, cfg, reviewed=frozenset()):
    stems = set(image_stems)
    reviewed_set = set(reviewed)
    n_images = len(stems)
    warn_ratio_hold = cfg["gate"]["warn_ratio_hold"]

    n_errors = 0
    warn_images = set()

    for issue in issues:
        if issue.severity == ERROR:
            n_errors += 1
        elif issue.severity == WARN:
            if issue.image in stems and issue.image not in reviewed_set:
                warn_images.add(issue.image)

    n_warn_images = len(warn_images)
    warn_ratio = round(n_warn_images / n_images, 4) if n_images > 0 else 0.0

    reasons = []
    if n_errors >= 1:
        decision = "Rework"
        reasons.append(f"Còn {n_errors} lỗi bắt buộc (ERROR) chặn pipeline, cần sửa lại trước khi xuất bản.")
    elif warn_ratio >= warn_ratio_hold:
        decision = "Hold"
        reasons.append(
            f"Tỉ lệ ảnh còn cảnh báo là {n_warn_images}/{n_images} = {warn_ratio:.2%} "
            f"(>= ngưỡng Hold {warn_ratio_hold:.2%}), cần người duyệt kiểm tra thêm."
        )
    else:
        decision = "Release"
        reasons.append(
            f"Không còn lỗi bắt buộc (0 ERROR) và tỉ lệ ảnh còn cảnh báo là "
            f"{n_warn_images}/{n_images} = {warn_ratio:.2%} (< ngưỡng Hold {warn_ratio_hold:.2%})."
        )

    return {
        "decision": decision,
        "n_errors": n_errors,
        "n_warn_images": n_warn_images,
        "n_images": n_images,
        "warn_ratio": warn_ratio,
        "reasons": reasons,
    }
