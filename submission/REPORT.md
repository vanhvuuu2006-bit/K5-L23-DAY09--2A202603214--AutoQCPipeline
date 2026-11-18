# Báo cáo Day 09 — Vũ Việt Anh-2A202603214

## 1. Kết luận trước
Pipeline kết luận **HOLD** (mã thoát `10`). Từ 224 ảnh thô ban đầu, hệ thống giữ lại 203 ảnh hợp lệ ở bước kiểm tra đầu vào (loại 21 ảnh hỏng, sai kích thước, trùng lặp hoặc rò rỉ từ tập test) và xuất bản nháp 203 ảnh ra thư mục `submission/export/clean_v1` để thử nghiệm
Lý do chính: sau khi sửa tự động và duyệt mô phỏng hết ngân sách 80 ảnh, vẫn còn 38/203 ảnh mang cảnh báo chưa qua mắt người, nên hệ thống chặn phát hành chính thức.
## 2. Lỗi và phân việc
| Mã lỗi | Số ảnh/dòng | Ai sửa (máy/người) | Vì sao |
|---|---:|---|---|
| `DUP_IMAGE_EXACT`, `DUP_IMAGE_NEAR` | 11 ảnh (8 + 3) | Máy (`autofix`) | Ảnh trùng lặp gây lệch dữ liệu nên máy tự xóa. |
| `LEAK_TEST` | 5 ảnh | Máy (`autofix`) | Ảnh bị lộ từ tập `test` nên máy tự xóa để tránh gian lận. |
| `CORRUPT_IMAGE`, `BAD_SIZE` | 5 ảnh (2 + 3) | Máy (`autofix`) | Ảnh hỏng hoặc sai kích thước chuẩn nên máy tự loại. |
| `BAD_FORMAT`, `BAD_CLASS_ID`, `BOX_ZERO`, `DUP_BOX` | 20 dòng (3 + 6 + 4 + 7) | Máy (`autofix`) | Lỗi định dạng, sai mã lớp hoặc khung rỗng/trùng nên máy tự xóa dòng. |
| `BOX_OUT_OF_IMAGE` | 8 dòng | Máy (`autofix`) | Khung vẽ tràn mép ảnh nên máy tự cắt gọn về đúng biên. |
| `BAD_CLASS_NAME` | 2 | Máy (`autofix`) | Tên lớp trong `data.yaml` sai chuẩn nên máy tự sửa lại. |
| `MISSING_LABEL_FILE` | 6 ảnh | Người (hàng đợi) | Ảnh thiếu file nhãn; máy không được tự bịa nên đẩy cho người gán. |
| `POSSIBLE_MISSING`, `POSSIBLE_LOOSE_BOX`, `POSSIBLE_FALSE_POS`, `POSSIBLE_WRONG_CLASS` | 124 dòng (53 + 28 + 25 + 18) | Người (hàng đợi) | Lỗi ý nghĩa do AI kiểm tra phát hiện nhưng có thể báo nhầm nên người phải xem lại. |
| `EMPTY_LABEL`, `BOX_TINY`, `BOX_HUGE`, `CLASS_RARE` | 25 dòng (12 + 6 + 3 + 4) | Người (hàng đợi) | Cảnh báo nhãn trống hoặc khung bất thường nên cần người kiểm tra. |

- Cách xếp hàng đợi (`05_review_queue.csv`): Ưu tiên xếp 6 ảnh thiếu file nhãn lên đầu để gỡ chặn `Rework`, sau đó xếp các ảnh cảnh báo giảm dần theo độ tự tin của AI để xử lý lỗi rõ ràng trước.
- Hiệu quả ngân sách 80 ảnh: Người duyệt xử lý xong 6 ảnh thiếu file nhãn và 74 ảnh có cảnh báo ngữ nghĩa ưu tiên cao nhất (giải quyết được phần lớn trong 149 cảnh báo, chỉ còn lại 38/203 ảnh = 18.72% mang cảnh báo chưa kịp xem).

## 3. Calibration (2 ngưỡng)
| Tham số | Khởi đầu | Đã chọn | Precision / Recall (trước → sau) | Lý do (đánh đổi) |
|---|---|---|---|---|
| `duplicates.phash_dist` | 2 | 8 | `DUP_IMAGE_NEAR`: `1.00 / 0.50` → `1.00 / 0.67` (`F1: 0.67 → 0.80`); `DUP_IMAGE_EXACT`: `1.00 / 1.00` → `1.00 / 1.00` | Nâng ngưỡng giúp bắt thêm các ảnh trùng bị nén/thu nhỏ mà vẫn giữ `precision = 1.00`. Không chọn `16`vì rủi ro `autofix` xóa nhầm các ảnh khác nhau có bố cục giống nhau trên tập `raw`. |
| `second_opinion.conf` | 0.25 | 0.6 | `WRONG_CLASS`: `0.56 / 0.83` → `0.62 / 0.83` (`F1: 0.67 → 0.71`); `MISSING`: `0.50 / 1.00` → `0.57 / 1.00` (`F1: 0.67 → 0.73`) |Chọn `0.6` giúp tăng độ chính xác cảnh báo lên `0.57–0.62` trong khi vẫn giữ trọn `recall = 1.00` cho lỗi thiếu nhãn. |

- **Một chỗ hiệu chỉnh ngưỡng (calibration) có thể đánh lừa bạn (kèm bằng chứng thực tế):**
  1. Điểm số đẹp trên bộ thử nhỏ 39 ảnh có thể gây "ảo giác" an toàn: Khi thử nghiệm tìm ngưỡng lọc ảnh trùng trên bộ mẫu nhỏ `calib` (chỉ có 39 ảnh), mức nới lỏng `16` cho điểm tổng hợp cao nhất (`0.91`) vì bộ mẫu này tình cờ không có hai bức ảnh nào khác cảnh nhưng trông na ná nhau. Tuy nhiên, vì bước tự động sửa (`autofix`) sẽ xóa vĩnh viễn những ảnh bị đánh dấu là trùng, việc tin vào điểm số cao ở mức `16` dễ đánh lừa ta đặt ngưỡng quá rộng, dẫn đến rủi ro xóa nhầm nhiều ảnh sạch có góc chụp giống nhau (như cùng một ngã tư nhưng khác thời điểm) khi áp dụng lên 224 ảnh thực tế.
  2. Kiểm chứng thực tế trên 224 ảnh `raw` ở ngưỡng an toàn `8`: Khi hạ ngưỡng lọc trùng xuống mức an toàn `8` và mở kiểm tra danh sách các ảnh bị loại trong báo cáo `submission/reports/`, kết quả hoàn toàn hợp lý: hệ thống chỉ loại đúng 11 ảnh trùng lặp thật sự(8 ảnh giống hệt nhau và 3 ảnh bị thu nhỏ kích thước), không có bất kỳ bức ảnh hợp lệ nào bị xóa nhầm.


- **Chỗ calibration có thể đánh lừa (kèm bằng chứng):** Tập `calib` chỉ có 39 ảnh nên mức phash_dist = 16 đạt điểm tổng hợp cao nhất (F1 = 0.91) vì mẫu nhỏ này không có hai ảnh nào khác cảnh nhưng na ná nhau. Nếu tin theo mức 16 để áp dụng lên 224 ảnh thật, bước tự động sửa (`autofix`) sẽ xóa vĩnh viễn nhầm nhiều ảnh sạch có góc chụp tương đồng. Khi kiểm chứng thực tế ở ngưỡng an toàn 8, báo cáo `submission/reports/` cho thấy hệ thống chỉ loại đúng 11 ảnh trùng lặp thật sự(8 ảnh giống hệt và 3 ảnh thu nhỏ), không xóa nhầm ảnh hợp lệ nào.


## 4. Cửa chặn và điều pipeline KHÔNG bắt được
a. Khi chạy thử lệnh `python -m pipeline.run --budget 0 --reports work/rep_nb --export-dir work/exp_nb` (đặt ngân sách duyệt bằng `0`, tức không có người vào gán bổ sung nhãn), cả 6 ảnh thiếu file nhãn vẫn còn nguyên. Cửa chặn lập tức từ chối cho qua với kết luận Rework, trả về mã thoát `EXIT_CODE=20` và không xuất bất kỳ dữ liệu nào, thư mục `work/exp_nb` không được tạo ra, chứng minh hệ thống ngăn chặn thành công dữ liệu lỗi lọt ra ngoài.

b. Các điểm mù có bằng chứng:
1. Khung vẽ hơi rộng hoặc cắt lẹm vào vật thể
Máy chỉ bắt được những khung vẽ lệch quá nhiều. Nếu người gán nhãn vẽ khung hơi rộng ra ngoài khoảng trống xung quanh xe một chút, hoặc cắt lẹm nhẹ vào một góc xe (đặc biệt với các xe ở xa, kích thước nhỏ), máy vẫn coi là chấp nhận được và bỏ qua.
2. Gán sai tên loại xe mà ngay cả AI kiểm tra cũng nhầm theo:
Hệ thống dùng một mô hình AI lớn để "chấm chéo" lại nhãn có sẵn. Tuy nhiên, với những loại xe đặc thù trên đường phố châu Á (như xe ba gác, xe tuk-tuk hoặc xe bị che khuất một nửa), cả nhãn gốc lẫn AI kiểm tra đều dễ nhìn nhầm thành ô tô hoặc xe tải. Khi cả hai cùng nhầm giống nhau, hệ thống tưởng là đúng và không báo lỗi.

## 5. Train: raw vs clean (tùy chọn, chấm riêng)
Chưa train: ghi "chưa chạy" và lý do, rồi bỏ qua phần còn lại của mục này. Nếu đã train: dán bảng từ `submission/results/comparison.md` (model, epoch, seed, số ảnh train mỗi biến thể).
| biến thể | #ảnh train | số seed | map50 (TB ± độ lệch) | map50_95 (TB ± độ lệch) | precision (TB ± độ lệch) | recall (TB ± độ lệch) |
|---|---|---|---|---|---|---|
| raw | 224 | 2 | 0.726 ± 0.000 | 0.512 ± 0.004 | 0.764 ± 0.061 | 0.649 ± 0.028 |
| clean | 203 | 2 | 0.699 ± 0.025 | 0.486 ± 0.013 | 0.796 ± 0.050 | 0.596 ± 0.049 |

Chênh mAP50 (clean − raw) = **-0.027**.
Rò rỉ test và ảnh trùng: `raw` chứa 5 ảnh `LEAK_TEST` và 11 ảnh trùng làm điểm đo trên `test` bị cao ảo. 
Cách kiểm: Đo lại trên `gold_val` hoặc loại 5 ảnh rò rỉ khỏi `test`.
`clean` đang ở trạng thái `HOLD`: Còn 38/203 ảnh cảnh báo thiếu nhãn chưa duyệt khiến model học sót vật thể.
Cách kiểm: Duyệt nốt 38 ảnh để đạt `Release` rồi train lại.
Dữ liệu ít và ít epoch/seed: Tập `clean` ít hơn 21 ảnh và mới chạy 20 epoch, 2 seed nên dao động lớn. Cách kiểm: Chạy 3–5 seed với 40–50 epoch.

## 6. Quyết định và ghi chú AI
Prompt chính: yêu cầu trợ lý AI hỗ trợ viết mã nguồn cho 4 module
Cách kiểm tra: đọc và rà soát mã nguồn đảm bảo k ghi đè dữ liệu gốc
 Một lần AI sai: Ở lần viết đầu tiên của `second_opinion.py`, AI gọi `raw_line.strip()` trực tiếp trên phần tử trả về từ `ds.read_label_lines(stem)` gây lỗi `AttributeError`; đã phát hiện ngay khi chạy `pytest tests/test_second_opinion.py` 

