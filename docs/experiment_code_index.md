# 实验代码结构索引

本文件说明本仓库中与准确率探索相关的实验代码位置。原则上这些代码分为“主流程可选增强”和“离线实验/评估”两类；除明确说明外，实验脚本不会覆盖主 `result.json`。

## 主流程附近的支撑改动

| 文件 | 作用 |
|---|---|
| `icu_vllm/cutter_worker_jin.py` | 金主任 profile cutter。新增 M/R 等区域外的高风险单列 crop 能力，例如 IV、管路护理、病情观察单列切片；仍保留主 L/M/R 切图。 |
| `icu_vllm/prompts.py` | 保存主 prompt 与实验 prompt。实验 prompt 包括 M continuation、IV rawlines/v3/v4、管路护理单列、病情观察单列/逐行等。默认生产行为不应直接依赖这些实验 prompt，除非配置显式启用。 |
| `tests/test_jin_cutter_evidence.py` | cutter 边界、M evidence 和单列 crop 范围的基础测试。 |

## 通用评估与文本归因

| 文件 | 作用 |
|---|---|
| `icu_vllm/iv_eval.py` | IV 字段专用 eval 细分，例如单位大小写、厂商标点、gold 复核、真实字符错。 |
| `icu_vllm/observation_eval.py` | 病情观察字段专用 eval 细分，例如标点差异、轻微等价、改写、漏字、字符级错误。 |
| `icu_vllm/observation_layered_eval.py` | 对上一轮识别结果做 strict / punctuation / case / unit style 分层重算，不重跑模型。 |
| `icu_vllm/observation_text_reviewer_tolerant_eval.py` | reviewer 输出的 strict / format-tolerant / clinical-semantic 三层评估。 |
| `config/clinical_equivalence_rules.yaml` | 宽容评估侧使用的临床格式等价规则；只用于评估，不写回主结果。 |

## 高风险列候选与增强结果

| 文件 | 作用 |
|---|---|
| `icu_vllm/target_column_vlm.py` | 高风险单列 VLM 初筛：IV、管路护理、病情观察。 |
| `icu_vllm/target_column_iv_rawlines.py` | IV 单列 raw_lines prompt 实验。 |
| `icu_vllm/target_column_iv_clean2x.py` | IV clean2x crop + rawlines 实验。 |
| `icu_vllm/target_column_iv_v3_unit.py` | IV v3 unit-aware prompt 实验。 |
| `icu_vllm/target_column_iv_v4_preserve_case.py` | IV v4 preserve-case prompt 实验，当前 IV 最佳 sidecar 候选。 |
| `icu_vllm/high_risk_strategy_review.py` | 汇总 IV、管路护理、病情观察候选策略效果。 |
| `icu_vllm/high_risk_column_candidate.py` | 只针对 IV 和管路护理生成候选覆盖决策。 |
| `icu_vllm/apply_high_risk_candidates.py` | 把 `propose_override` 应用到新的 `result_enhanced.json`，不覆盖原始 `result.json`。 |

## 病情观察图像与识别探索

| 文件 | 作用 |
|---|---|
| `icu_vllm/target_column_observation_compare.py` | 病情观察 direct vs rawlines 对比实验。 |
| `icu_vllm/observation_residual_casebook.py` | 汇总病情观察 residual case、主结果、单列结果和图片路径。 |
| `icu_vllm/observation_verbatim_experiment.py` | 病情观察 whole-column verbatim prompt 实验。 |
| `icu_vllm/image_preprocess.py` | 图像预处理基础函数，用于 raw_col 插值、去线、CLAHE、二值化等离线实验。 |
| `icu_vllm/observation_preprocess_ablation.py` | 病情观察 raw_col 图像预处理消融。 |
| `icu_vllm/observation_true_clean_crop.py` | 从 clean final block 重新裁病情观察列做 native/2x/3x 实验。 |
| `icu_vllm/observation_true_clean_crop_worker.py` | true clean crop 的 worker 支撑。 |
| `icu_vllm/observation_line_probe.py` | 病情观察 residual case 行级转录 probe。 |
| `icu_vllm/observation_header_row_probe.py` | header+row 输入形态 probe。 |
| `icu_vllm/observation_row_prompt_ablation.py` | header-row、row-only、2x/3x 与 old/precise prompt 对照。 |
| `icu_vllm/observation_recognition_bottleneck_probe.py` | canvas h48/h64/h96、PaddleOCR det/rec 拆分、Qwen 输入形态瓶颈定位。 |
| `icu_vllm/observation_med_context_prompt_probe.py` | 病情观察医学上下文 prompt 小实验。 |

## PDF 渲染与 reviewer

| 文件 | 作用 |
|---|---|
| `icu_vllm/pdf_render_quality_probe.py` | PDF 内容审计和局部多 DPI clip 渲染质量诊断。 |
| `icu_vllm/observation_pdf_dpi_recognition_probe.py` | 对病情观察 residual case 的 PDF 高 DPI clip 识别验证。 |
| `icu_vllm/observation_text_reviewer_experiment.py` | raw OCR / raw Qwen 之后的 reviewer 文本审查实验。 |
| `config/domain_lexicon.yaml` | reviewer 使用的领域词表配置；gold 不进入 reviewer prompt。 |

## 测试组织

相关测试按模块一一对应放在 `tests/` 下，例如：

- `tests/test_target_column_iv_v4_preserve_case.py`
- `tests/test_high_risk_column_candidate.py`
- `tests/test_observation_row_prompt_ablation.py`
- `tests/test_observation_text_reviewer_tolerant_eval.py`

这些测试主要覆盖解析、分类、报告生成、输入输出 hash 不变、JSON 解析和边界条件。它们用于保证实验脚本可复现，不代表模型推理本身在本地单测中执行。
