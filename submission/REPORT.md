# Báo cáo Day 09 — <Vũ Việt Anh>, <2A202603214>

> Xoá mọi `TODO(học viên)` và dòng gợi ý. Mỗi ý trả lời bằng **số lấy từ `submission/reports/`**, kèm mẫu số. Cả báo cáo ~1–2 trang.

## 1. Kết luận trước
TODO(học viên): pipeline kết luận **Release / Hold / Rework**? Bao nhiêu ảnh vào, bao nhiêu ảnh ra dataset? Lý do chính (1–3 câu).
Pipeline kết luận **HOLD** (mã thoát `10`). Từ 224 ảnh thô ban đầu, hệ thống giữ lại 203 ảnh hợp lệ ở bước kiểm tra đầu vào (loại 21 ảnh hỏng, sai kích thước, trùng lặp hoặc rò rỉ từ tập test) và xuất bản nháp 203 ảnh ra thư mục `submission/export/clean_v1` để thử nghiệm
Lý do chính: sau khi sửa tự động và duyệt mô phỏng hết ngân sách 80 ảnh, vẫn còn 38/203 ảnh mang cảnh báo chưa qua mắt người, nên hệ thống chặn phát hành chính thức.
## 2. Lỗi và phân việc
Lấy từ `02_error_list_v1` (gom theo mã lỗi). Cột "ai sửa": **máy** (autofix) hay **người** (hàng đợi); chỉ ghi những mã có mặt trong lô của bạn.

| Mã lỗi | Số ảnh/dòng | Ai sửa (máy/người) | Vì sao |
|---|---:|---|---|
| TODO(học viên) | | | |

TODO(học viên): vì sao `05_review_queue.csv` xếp ảnh đầu hàng như vậy? Với ngân sách 80 ảnh, người xem được bao nhiêu lỗi ngữ nghĩa?

## 3. Calibration (2 ngưỡng)
| Tham số | Khởi đầu | Đã chọn | Precision / Recall (trước → sau) | Lý do (đánh đổi) |
|---|---|---|---|---|
| `duplicates.phash_dist` | 2 | **8** | `DUP_IMAGE_NEAR`: `1.00 / 0.50` → **`1.00 / 0.67`** (`F1: 0.67 → 0.80`); `DUP_IMAGE_EXACT`: `1.00 / 1.00` → **`1.00 / 1.00`** | Nâng ngưỡng giúp bắt thêm các ảnh trùng bị nén/thu nhỏ mà vẫn giữ `precision = 1.00`. Không chọn `16`vì rủi ro `autofix` xóa nhầm các ảnh khác nhau có bố cục giống nhau trên tập `raw`. |
| `second_opinion.conf` | 0.25 | **0.6** | `WRONG_CLASS`: `0.56 / 0.83` → **`0.62 / 0.83`** (`F1: 0.67 → 0.71`); `MISSING`: `0.50 / 1.00` → **`0.57 / 1.00`** (`F1: 0.67 → 0.73`) |Chọn `0.6` giúp tăng độ chính xác cảnh báo lên `0.57–0.62` trong khi vẫn giữ trọn `recall = 1.00` cho lỗi thiếu nhãn. |

**Một chỗ calibration có thể đánh lừa bạn (kèm bằng chứng thực tế):**
1. **Ảo giác F1 tối đa ở ngưỡng cao trên mẫu nhỏ (`calib` chỉ có 39 ảnh):** Trên bảng sweep `duplicates.phash_dist`, mức `16` đạt điểm `F1 = 0.91` (`Precision = 1.00, Recall = 0.83`) cao nhất vì trong 39 ảnh `calib` có một ca biến đổi mạnh mà không có cặp ảnh "na ná nhau nhưng khác cảnh". Tuy nhiên, do `autofix` thực hiện hành động **xóa vĩnh viễn (`remove_image`)** nếu gắn cờ trùng, việc chạy theo điểm F1 tối đa trên 39 ảnh mẫu dễ đánh lừa ta đặt ngưỡng quá lỏng (`16`), gây nguy cơ xóa nhầm dữ liệu hợp lệ khi áp dụng sang 224 ảnh `raw` đa dạng hơn.
2. **Kiểm chứng trên dữ liệu `raw` sau khi chọn `phash_dist = 8`:** Khi chạy pipeline với `phash_dist = 8` và mở kiểm tra trực tiếp danh sách cặp ảnh bị gắn cờ `DUP_IMAGE_*` trong `submission/reports/`, số ảnh bị loại bỏ ở Bước 1 hoàn toàn hợp lý: máy bắt đúng các bản sao chép y hệt (`EXACT`) và các ảnh bị thu nhỏ/nén lại (`NEAR`), không có cặp ảnh khác cảnh nào bị xóa nhầm.

TODO(học viên): **một chỗ calibration có thể đánh lừa bạn**, kèm bằng chứng từ dữ liệu của bạn (vd. mở xem vài cặp ảnh bị cho là trùng; số ảnh bị loại ở bước 1 có hợp lý không?).

## 4. Cửa chặn và điều pipeline KHÔNG bắt được
TODO(học viên): (a) chứng minh gate chặn đúng: chạy `python -m pipeline.run --budget 0 --reports work/rep_nb --export-dir work/exp_nb` (không có người duyệt nên ảnh thiếu file nhãn còn nguyên), chỉ ra kết luận **Rework**, mã thoát 20 và việc **không xuất** dataset. (Đừng sửa tay `work/run/ds`: pipeline dựng lại thư mục này từ raw mỗi lần chạy.) (b) ≥ 2 điểm mù có bằng chứng (box lỏng nhẹ, nhầm lớp mà model lớn cũng nhầm, ảnh trùng biến đổi mạnh…).
a) 
b) Các điểm mù có bằng chứng:
1. Box vẽ hơi lỏng hoặc hơi cắt lẹm vào vật thể. Qua quan sát trực quan các ảnh, những khung box vẽ rộng hơn vật thể một chút nhưng vẫn đạt mức trùng khớp `IoU >= iou_loose` (hoặc nằm trên các đối tượng nhỏ bị lọc bởi `min_area_px`) sẽ không bị máy gắn cờ cảnh báo.
2. Gán nhầm lớp mà ngay cả model lớn `yolo26l` cũng nhầm theo (`POSSIBLE_WRONG_CLASS` bị lọt):** `second_opinion` dùng dự đoán của `yolo26l` làm mốc đối chiếu; do đó, với các đối tượng đặc thù đường phố châu Á (như xe ba gác/tuk-tuk bị nhận diện nhầm thành `car`/`truck` hoặc các vật thể bị che khuất nửa thân) mà cả nhãn gốc lẫn `yolo26l` đều gán cùng một lớp sai, máy sẽ coi là khớp lớp và bỏ qua hoàn toàn.
3. Ảnh trùng lặp có biến đổi hình học mạnh.  Trên tập hiệu chỉnh `calib`, tại ngưỡng an toàn `phash_dist = 8`, `DUP_IMAGE_NEAR` đạt `recall = 0.67` (còn sót 2/6 ảnh trùng). Các bản sao bị cắt cúp (crop) nhiều, xoay góc lớn hoặc lật ngang làm thay đổi cấu trúc tần số thấp của pHash vượt quá khoảng cách `8` sẽ vượt qua Bước 1 mà không bị phát hiện.
## 5. Train: raw vs clean (tùy chọn, chấm riêng)
Chưa train: ghi "chưa chạy" và lý do, rồi bỏ qua phần còn lại của mục này. Nếu đã train: dán bảng từ `submission/results/comparison.md` (model, epoch, seed, số ảnh train mỗi biến thể).
chưa chạy
tập trung hoàn thiện và kiểm chứng toàn bộ pipeline kiểm nhãn tự động, calibration và cửa chặn trên máy cục bộ
TODO(học viên): chênh mAP50 (clean − raw) so với **độ lệch chuẩn giữa các seed**; kết luận **trung thực** (nằm trong nhiễu thì nói là chưa kết luận được); ≥ 2 giả thuyết giải thích (ảnh trùng/rò rỉ test trong `raw`, nhãn máy còn lại trong `clean`, test chỉ 100 ảnh…) và cách kiểm.

## 6. Quyết định và ghi chú AI
TODO(học viên): (a) quyết định cuối; nếu Hold/Rework cần làm gì để thành Release? (b) Dùng AI viết code? Ghi 3 dòng: prompt chính, cách bạn kiểm code AI, 1 lần AI sai. Không dùng: ghi "không dùng".
Prompt chính: yêu cầu trợ lý AI hỗ trợ viết mã nguồn cho 4 module
Cách kiểm tra: đọc và rà soát mã nguồn đảm bảo k ghi đè dữ liệu gốc
 Một lần AI sai: Ở lần viết đầu tiên của `second_opinion.py`, AI gọi `raw_line.strip()` trực tiếp trên phần tử trả về từ `ds.read_label_lines(stem)` gây lỗi `AttributeError`; đã phát hiện ngay khi chạy `pytest tests/test_second_opinion.py` 
*(Thưởng +2, tùy chọn)* CVAT: lọc `width < 20`, ảnh/số box khớp, đối chiếu `BOX_TINY` (xem docs/CVAT_FILTER.md), 1 câu về `can_review`.
