# 尝试流程报告归档

本目录归档服务器 `/data1/jianf-vllm/runs` 下已保留的 Markdown 报告，方便在 GitHub 上集中查看我们已经做过的主要实验。

说明：

- 这里只同步报告 `.md`，不包含原始图片、JSONL、sidecar、模型输出大文件。
- 每个子目录名保留原远端 run_id，便于回到服务器 `/data1/jianf-vllm/runs/<run_id>/` 查完整产物。
- 原始远端项目路径：`/data1/jianf-vllm`
- 复盘总览：[`../experiment_attempts_review.md`](../experiment_attempts_review.md)

## 模型与主流程

| 实验 | GitHub 报告 | 原始远端路径 |
|---|---|---|
| 早期模型矩阵对比 | [`model_compare_report_20260525-023001/report.md`](model_compare_report_20260525-023001/report.md) | `/data1/jianf-vllm/runs/model_compare_report_20260525-023001/report.md` |
| 模型矩阵对比 | [`model_compare_report_20260525-041208/report.md`](model_compare_report_20260525-041208/report.md) | `/data1/jianf-vllm/runs/model_compare_report_20260525-041208/report.md` |
| eval attribution 版本模型报告 | [`model_compare_report_eval_20260525-050620/report.md`](model_compare_report_eval_20260525-050620/report.md) | `/data1/jianf-vllm/runs/model_compare_report_eval_20260525-050620/report.md` |

## M 区 Prompt 与泛化验证

| 实验 | GitHub 报告 | 原始远端路径 |
|---|---|---|
| M prompt v2 模型对比 | [`model_compare_report_prompt_v2_20260525-054856/report.md`](model_compare_report_prompt_v2_20260525-054856/report.md) | `/data1/jianf-vllm/runs/model_compare_report_prompt_v2_20260525-054856/report.md` |
| M prompt v2 双 gold 泛化 | [`prompt_v2_generalization_20260525-061220/report.md`](prompt_v2_generalization_20260525-061220/report.md) | `/data1/jianf-vllm/runs/prompt_v2_generalization_20260525-061220/report.md` |
| M prompt v2 三 gold 验证 | [`prompt_v2_validation_20260525-063531/report.md`](prompt_v2_validation_20260525-063531/report.md) | `/data1/jianf-vllm/runs/prompt_v2_validation_20260525-063531/report.md` |

## 高风险列：IV 与管路护理

| 实验 | GitHub 报告 | 原始远端路径 |
|---|---|---|
| 单列 VLM 初筛 | [`target_column_vlm_20260525-074656/target_column_vlm_report.md`](target_column_vlm_20260525-074656/target_column_vlm_report.md) | `/data1/jianf-vllm/runs/target_column_vlm_20260525-074656/target_column_vlm_report.md` |
| IV rawlines prompt | [`target_column_iv_rawlines_20260525-081135/target_column_iv_rawlines_report.md`](target_column_iv_rawlines_20260525-081135/target_column_iv_rawlines_report.md) | `/data1/jianf-vllm/runs/target_column_iv_rawlines_20260525-081135/target_column_iv_rawlines_report.md` |
| IV clean2x crop | [`target_column_iv_clean2x_20260525-082612/target_column_iv_rawlines_clean2x_report.md`](target_column_iv_clean2x_20260525-082612/target_column_iv_rawlines_clean2x_report.md) | `/data1/jianf-vllm/runs/target_column_iv_clean2x_20260525-082612/target_column_iv_rawlines_clean2x_report.md` |
| IV v3 unit-aware | [`target_column_iv_v3_unit_20260525-085732/target_column_iv_v3_unit_report.md`](target_column_iv_v3_unit_20260525-085732/target_column_iv_v3_unit_report.md) | `/data1/jianf-vllm/runs/target_column_iv_v3_unit_20260525-085732/target_column_iv_v3_unit_report.md` |
| IV v4 preserve-case | [`target_column_iv_v4_preserve_case_20260525-092139/target_column_iv_v4_preserve_case_report.md`](target_column_iv_v4_preserve_case_20260525-092139/target_column_iv_v4_preserve_case_report.md) | `/data1/jianf-vllm/runs/target_column_iv_v4_preserve_case_20260525-092139/target_column_iv_v4_preserve_case_report.md` |
| 高风险策略总览 | [`high_risk_strategy_review_20260525-171555/high_risk_strategy_review_report.md`](high_risk_strategy_review_20260525-171555/high_risk_strategy_review_report.md) | `/data1/jianf-vllm/runs/high_risk_strategy_review_20260525-171555/high_risk_strategy_review_report.md` |
| 高风险候选覆盖评估 | [`high_risk_column_candidate_20260525-173241/high_risk_column_candidate_report.md`](high_risk_column_candidate_20260525-173241/high_risk_column_candidate_report.md) | `/data1/jianf-vllm/runs/high_risk_column_candidate_20260525-173241/high_risk_column_candidate_report.md` |
| 高风险 enhanced 早期结果 | [`high_risk_enhanced_20260525-204525/enhanced_eval_report.md`](high_risk_enhanced_20260525-204525/enhanced_eval_report.md) | `/data1/jianf-vllm/runs/high_risk_enhanced_20260525-204525/enhanced_eval_report.md` |
| 高风险 enhanced 结果 | [`high_risk_enhanced_20260525-204625/enhanced_eval_report.md`](high_risk_enhanced_20260525-204625/enhanced_eval_report.md) | `/data1/jianf-vllm/runs/high_risk_enhanced_20260525-204625/enhanced_eval_report.md` |
| latest-method retry | [`latest-method-retry-20260528-210025/enhanced_eval_report.md`](latest-method-retry-20260528-210025/enhanced_eval_report.md) | `/data1/jianf-vllm/runs/latest-method-retry-20260528-210025/enhanced_eval_report.md` |

## 病情观察及处理

| 实验 | GitHub 报告 | 原始远端路径 |
|---|---|---|
| residual casebook 早期版 | [`observation_residual_casebook_20260525-211132/observation_residual_casebook.md`](observation_residual_casebook_20260525-211132/observation_residual_casebook.md) | `/data1/jianf-vllm/runs/observation_residual_casebook_20260525-211132/observation_residual_casebook.md` |
| residual casebook | [`observation_residual_casebook_20260525-211324/observation_residual_casebook.md`](observation_residual_casebook_20260525-211324/observation_residual_casebook.md) | `/data1/jianf-vllm/runs/observation_residual_casebook_20260525-211324/observation_residual_casebook.md` |
| refined eval | [`observation_eval_refined_20260526-151747/observation_eval_refined_report.md`](observation_eval_refined_20260526-151747/observation_eval_refined_report.md) | `/data1/jianf-vllm/runs/observation_eval_refined_20260526-151747/observation_eval_refined_report.md` |
| direct vs rawlines | [`observation_direct_vs_rawlines_20260525-084254/observation_direct_vs_rawlines_report.md`](observation_direct_vs_rawlines_20260525-084254/observation_direct_vs_rawlines_report.md) | `/data1/jianf-vllm/runs/observation_direct_vs_rawlines_20260525-084254/observation_direct_vs_rawlines_report.md` |
| whole-column verbatim | [`observation_verbatim_20260525-213954/observation_verbatim_report.md`](observation_verbatim_20260525-213954/observation_verbatim_report.md) | `/data1/jianf-vllm/runs/observation_verbatim_20260525-213954/observation_verbatim_report.md` |
| raw_col 图像预处理消融 | [`observation_preprocess_ablation_20260526-160017/observation_preprocess_ablation_report.md`](observation_preprocess_ablation_20260526-160017/observation_preprocess_ablation_report.md) | `/data1/jianf-vllm/runs/observation_preprocess_ablation_20260526-160017/observation_preprocess_ablation_report.md` |
| true clean crop 消融 | [`observation_true_clean_crop_20260526-172653/observation_true_clean_crop_report.md`](observation_true_clean_crop_20260526-172653/observation_true_clean_crop_report.md) | `/data1/jianf-vllm/runs/observation_true_clean_crop_20260526-172653/observation_true_clean_crop_report.md` |
| PDF DPI clip probe 早期版 1 | [`observation_pdf_dpi_probe_20260528-013306/observation_pdf_dpi_probe_report.md`](observation_pdf_dpi_probe_20260528-013306/observation_pdf_dpi_probe_report.md) | `/data1/jianf-vllm/runs/observation_pdf_dpi_probe_20260528-013306/observation_pdf_dpi_probe_report.md` |
| PDF DPI clip probe 早期版 2 | [`observation_pdf_dpi_probe_20260528-013451/observation_pdf_dpi_probe_report.md`](observation_pdf_dpi_probe_20260528-013451/observation_pdf_dpi_probe_report.md) | `/data1/jianf-vllm/runs/observation_pdf_dpi_probe_20260528-013451/observation_pdf_dpi_probe_report.md` |
| PDF DPI clip probe | [`observation_pdf_dpi_probe_20260528-013712/observation_pdf_dpi_probe_report.md`](observation_pdf_dpi_probe_20260528-013712/observation_pdf_dpi_probe_report.md) | `/data1/jianf-vllm/runs/observation_pdf_dpi_probe_20260528-013712/observation_pdf_dpi_probe_report.md` |
| line probe 早期版 | [`observation_line_probe_20260527-104924/observation_line_probe_report.md`](observation_line_probe_20260527-104924/observation_line_probe_report.md) | `/data1/jianf-vllm/runs/observation_line_probe_20260527-104924/observation_line_probe_report.md` |
| line probe | [`observation_line_probe_20260527-105255/observation_line_probe_report.md`](observation_line_probe_20260527-105255/observation_line_probe_report.md) | `/data1/jianf-vllm/runs/observation_line_probe_20260527-105255/observation_line_probe_report.md` |
| header-row probe | [`observation_header_row_probe_20260528-023041/observation_header_row_probe_report.md`](observation_header_row_probe_20260528-023041/observation_header_row_probe_report.md) | `/data1/jianf-vllm/runs/observation_header_row_probe_20260528-023041/observation_header_row_probe_report.md` |
| row prompt ablation | [`observation_row_prompt_ablation_20260528-030002/observation_row_prompt_ablation_report.md`](observation_row_prompt_ablation_20260528-030002/observation_row_prompt_ablation_report.md) | `/data1/jianf-vllm/runs/observation_row_prompt_ablation_20260528-030002/observation_row_prompt_ablation_report.md` |
| recognition bottleneck probe | [`observation_recognition_bottleneck_probe_20260528-031512/observation_recognition_bottleneck_report.md`](observation_recognition_bottleneck_probe_20260528-031512/observation_recognition_bottleneck_report.md) | `/data1/jianf-vllm/runs/observation_recognition_bottleneck_probe_20260528-031512/observation_recognition_bottleneck_report.md` |
| medical context prompt probe | [`observation_med_context_prompt_probe_20260528-034617/observation_med_context_prompt_report.md`](observation_med_context_prompt_probe_20260528-034617/observation_med_context_prompt_report.md) | `/data1/jianf-vllm/runs/observation_med_context_prompt_probe_20260528-034617/observation_med_context_prompt_report.md` |
| text reviewer experiment | [`observation_text_reviewer_experiment_20260528-041615/observation_text_reviewer_report.md`](observation_text_reviewer_experiment_20260528-041615/observation_text_reviewer_report.md) | `/data1/jianf-vllm/runs/observation_text_reviewer_experiment_20260528-041615/observation_text_reviewer_report.md` |
| text reviewer tolerant eval 早期版 | [`observation_text_reviewer_tolerant_eval_20260528-225148/observation_text_reviewer_tolerant_eval_report.md`](observation_text_reviewer_tolerant_eval_20260528-225148/observation_text_reviewer_tolerant_eval_report.md) | `/data1/jianf-vllm/runs/observation_text_reviewer_tolerant_eval_20260528-225148/observation_text_reviewer_tolerant_eval_report.md` |
| text reviewer tolerant eval | [`observation_text_reviewer_tolerant_eval_20260528-225417/observation_text_reviewer_tolerant_eval_report.md`](observation_text_reviewer_tolerant_eval_20260528-225417/observation_text_reviewer_tolerant_eval_report.md) | `/data1/jianf-vllm/runs/observation_text_reviewer_tolerant_eval_20260528-225417/observation_text_reviewer_tolerant_eval_report.md` |
