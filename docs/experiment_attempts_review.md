# PDF-VLLM 抽取准确率尝试全流程复盘

更新时间：2026-05-28

本文件整理 `/data1/jianf-vllm` 项目从 vLLM 迁移、模型选择、M 区改造、高风险列 sidecar，到“病情观察及处理”多轮实验和 reviewer 评估的主要尝试。它不是生产配置说明，也不代表所有实验结果都应进入主流程；它的目标是把我们已经验证过的路线、失败原因和仍然可继续的方向记录清楚，避免后续重复试错。

## 当前结论先行

1. `Qwen3-VL-32B` 是当前主模型的合理基线：三次重复输出稳定；`Qwen2.5-VL-72B` 没有在 smoke 页上显示出明显优势；更小模型速度可能更快，但过填、串列、漏识别风险更高。
2. 对半结构化字段，单列 sidecar 是有效路线。`入量_静脉用药` 和 `管路护理` 经过单列裁图、专用 prompt、候选覆盖评估后，在 3 页 gold 上共修复 10 条主流程错误，新增错误 0。
3. 对 `病情观察及处理`，截至目前没有找到稳定可覆盖主结果的图像或 prompt 路线。单列、逐行、true clean crop、DPI clip、图像增强、医学上下文 prompt 都只有局部收益或无净收益。
4. OCR 对病情观察不是可替代主力：PaddleOCR 在未放大的 row-only 小行图上大量漏检，放大或 canvas 标准化后可恢复一部分，但整体仍明显弱于 Qwen/VLM。
5. 外部医学知识有两种不同作用：直接塞进识别 prompt 只带来小幅局部改善；作为 reviewer/QC 的词表与宽容评估，可以帮助区分“格式等价”和“危险实质错误”，但目前不适合自动覆盖主结果。
6. 目前最可继续的方向不是继续盲目图像增强，而是：
   - 将 `入量_静脉用药`、`管路护理` 的候选覆盖做成可配置、可审计、可回滚的实验开关。
   - 对 `病情观察及处理` 保留主结果，用 reviewer 作为 QC suggestion / semantic normalization 辅助，而不是 raw transcription 覆盖源。
   - 继续完善 gold 复核、format-tolerant / clinical-semantic 评估和人工复核队列。

## 数据和报告来源

远端项目路径：

- `/data1/jianf-vllm`

旧输入数据来源：

- `/data1/jianf/新提取pdf/180data`

主要 gold 页面：

- `gold_smoke_001`：`0013807667_2023_10_15_3_result.json`
- `gold_dev_m_002`：`0013807667_2023_10_15_10_result.json`
- `gold_validation_003`：`0014865104_2024_10_16_24_result.json`

主要报告目录都在远端：

- `/data1/jianf-vllm/runs/<run_id>/`

本文件引用的数字来自这些 run 的 `summary.json`、`*_summary.json` 和 `*_report.md`。如果后续 gold 被修正，旧报告的绝对数值需要按新 gold 重算，但“实验路线是否有效”的相对结论仍有参考价值。

## 0. vLLM 迁移和评估基础设施

最初目标是从旧的 Ollama 混合输出中切出干净 vLLM 项目：

- 新工作区：`/data1/jianf-vllm`
- 旧项目：`/data1/jianf/新提取pdf`，只作为只读输入来源
- 输出隔离到 `/data1/jianf-vllm/runs/<run_id>/`
- 新增 `results_json/`、`patient_cache/`、`excel/`、`logs/`、`debug/` 等运行结构
- 不复用旧 `180data_result`、旧 Excel、旧 Ollama 缓存

这一步的价值不是直接提升准确率，而是建立了后续所有实验的前提：

- 每次实验有独立 run 目录。
- gold 对比可复现。
- raw response、evidence、casebook 可以保留。
- 不再把 Ollama 结果和 vLLM 结果混在一起。

同时新增了多类评估工具：

- strict diff：保留完全不一致统计。
- canonical comparison：区分全半角、空格、标点差异。
- separator error：识别只因为错误分号导致的差异。
- residual casebook：把 gold、主结果、sidecar、图片证据合在一起。
- later tolerant eval：把 strict transcription、format-tolerant equivalence、clinical semantic equivalence 分开。

## 1. 模型选择尝试

代表报告：

- `/data1/jianf-vllm/runs/model_compare_report_20260525-041208/report.md`
- `/data1/jianf-vllm/runs/model_compare_report_20260525-041208/summary.json`

| 模型/设置 | 主要观察 | 结论 |
|---|---|---|
| `Qwen3-VL-32B` 三次重复 | 三次结果完全一致；总 diff 约 27 | 当前主模型基线，稳定性足够 |
| `Qwen2.5-VL-72B` | smoke 页总 diff 约 27，未明显优于 Qwen3-32B | 不适合直接当作全量一阶段替代 |
| `Qwen2.5-VL-32B` | 总 diff 约 55 | 明显弱于 Qwen3-32B |
| `Qwen3-VL-8B` | 总 diff 约 50 | 速度候选，但准确率不足 |
| `Qwen2.5-VL-7B` | 过填、串列严重 | 已从后续 review 矩阵中移除 |

经验教训：

- 小模型不是简单“快一点、差一点”，而是更容易在空白格无中生有、跨列填充、续行错分方面出系统性错误。
- 72B 并没有在当前任务上证明能抵消成本。
- 后续优化重点不应是盲目换大模型，而应是按字段风险拆解输入和审查链路。

## 2. M 区 evidence 和 PROMPT_M_V2_CONTINUATION

### 2.1 M 区可审计证据

改造目标是先不修结果，只保存证据，用于区分错误来源：

- `block_*_M.png`
- `block_*_M.txt`
- `block_*_M.ocr.json`
- `block_*_M.raw_response.txt`

配置项：

- `keep_success_m_evidence = false` 默认关闭。

价值：

- 能看到 M 区图片是否裁到字段。
- 能看到 OCR 是否读到对应行。
- 能看到 raw response 是否已经提到但 JSON 输出丢失。
- 不改变 `result.json` schema，不改变 merge。

### 2.2 M prompt v2 continuation

代表报告：

- `/data1/jianf-vllm/runs/prompt_v2_validation_20260525-063531/report.md`
- `/data1/jianf-vllm/runs/prompt_v2_validation_20260525-063531/summary.json`

尝试内容：

- 保留旧 `PROMPT_M`。
- 新增 `PROMPT_M_V2_CONTINUATION`，只强化多行、续行、分号和管路占位符规则。
- 通过 `jin_m_prompt_variant = "continuation_v2"` 启用。
- 默认仍为旧 prompt。

3 页 gold 的 M 区汇总：

| 指标 | old | v2 | delta |
|---|---:|---:|---:|
| M strict_total | 26 | 20 | -6 |
| M separator_error | 4 | 3 | -1 |
| M overfill | 2 | 1 | -1 |
| M substantive_mismatch | 14 | 10 | -4 |

代表性页面：

- `gold_smoke_001`：M strict_total 从 11 降到 7。
- `gold_dev_m_002`：M 区基本持平，无新增明显错误。
- `gold_validation_003`：M strict_total 从 8 降到 6。

结论：

- M prompt v2 对“视觉换行被误判为分号”和“续行接错字段”确实有帮助。
- 它通过了初步 no-regression，但仍只是候选，不应直接默认替换。

## 3. 高风险列：管路护理与入量_静脉用药

这条路线是目前最成功的自动增强方向。核心思想是：主流程仍输出原始 `result.json`，高风险字段另跑 sidecar，只有满足安全条件时才生成实验性增强结果。

### 3.1 单列 VLM 初筛

代表报告：

- `/data1/jianf-vllm/runs/target_column_vlm_20260525-074656/target_column_vlm_report.md`
- `/data1/jianf-vllm/runs/target_column_vlm_20260525-074656/target_column_vlm_summary.json`

| 字段 | main_correct | col_correct | main_wrong_col_correct | main_correct_col_wrong | 初步结论 |
|---|---:|---:|---:|---:|---|
| 入量_静脉用药 | 45 | 45 | 2 | 2 | direct 单列无净收益 |
| 管路护理 | 53 | 56 | 3 | 0 | 单列有净收益 |
| 病情观察及处理 | 46 | 46 | 1 | 1 | 单列无净收益 |

关键区别：

- “单列做不行”只适用于病情观察和早期 IV direct prompt。
- 管路护理单列是有效的。
- IV 后续通过 raw_lines 和 clean2x/v4 prompt 变成有效路线。

### 3.2 入量_静脉用药 raw_lines prompt

代表报告：

- `/data1/jianf-vllm/runs/target_column_iv_rawlines_20260525-081135/target_column_iv_rawlines_report.md`

尝试内容：

- 新增 `PROMPT_COL_IV_DRUG_V2_RAWLINES`。
- 先逐视觉行转录 raw_lines，再合并 final_value。
- 目标是保留 `250`、`t100`、`G+...`、`持` 这类尾部碎片。

结果：

| 指标 | old_col | iv_v2_rawlines |
|---|---:|---:|
| col_correct | 45 | 50 |
| main_wrong_col_correct | 2 | 6 |
| both_wrong | 10 | 6 |
| raw_lines_missing_tail | - | 7 |

结论：

- 对 IV 来说，“先忠实转录，再结构合并”明显优于直接让模型输出最终分号串。
- 但 raw_lines 仍会漏尾部数字或误读单位，说明还有图像/字符识别瓶颈。

### 3.3 IV clean2x crop

代表报告：

- `/data1/jianf-vllm/runs/target_column_iv_clean2x_20260525-082612/target_column_iv_rawlines_clean2x_report.md`

尝试内容：

- 从 clean block 裁出 IV 单列。
- 2x 放大。
- 复用 V2 rawlines prompt。

结果：

| 指标 | old_crop | clean_2x |
|---|---:|---:|
| col_correct | 50 | 52 |
| main_wrong_col_correct | 6 | 7 |
| main_correct_col_wrong | 1 | 0 |
| raw_lines_missing_tail | 7 | 5 |
| char_level_mismatch | 7 | 5 |

结论：

- clean2x 对 IV 有实际收益。
- 这说明 IV 的残留问题里有一部分确实来自输入图像质量或缩放。

### 3.4 IV v3 unit-aware 与 v4 preserve-case

代表报告：

- `/data1/jianf-vllm/runs/target_column_iv_v3_unit_20260525-085732/target_column_iv_v3_unit_report.md`
- `/data1/jianf-vllm/runs/target_column_iv_v4_preserve_case_20260525-092139/target_column_iv_v4_preserve_case_report.md`

v3 尝试：

- 加强 `/h+` 不要误读成 `/hr`。
- 加强 `UG/0G`、`ml/m1` 等单位提示。
- 校准 `needs_review`。

v3 问题：

- 虽然改善了部分 `/h+` 和 review 标记，但引入过度规范化，例如把图像里的 `ML` 改成 `ml`。
- `col_correct` 从 52 降到 50，`main_correct_col_wrong` 从 0 增到 1。

v4 尝试：

- 保留 v3 的 `/h+` 和 review 校准。
- 明确要求保留图像中的大小写和单位写法，不把 `ML/MG/UG` 自动规范化成小写。

v4 结果：

| 方法 | report_correct | true_char_mismatch | main_wrong_method_correct | main_correct_method_wrong |
|---|---:|---:|---:|---:|
| v2_clean2x | 55 | 2 | - | - |
| v3_units | 55 | 2 | - | - |
| v4_preserve_case | 56 | 1 | 8 | 0 |

结论：

- IV 当前最佳候选是 `clean_2x + PROMPT_COL_IV_DRUG_V4_PRESERVE_CASE`。
- 对 IV，prompt 不是越“医学规范化”越好；保留原图大小写和表面形式更安全。

### 3.5 高风险候选覆盖评估与 enhanced 结果

代表报告：

- `/data1/jianf-vllm/runs/high_risk_column_candidate_20260525-173241/high_risk_column_candidate_report.md`
- `/data1/jianf-vllm/runs/high_risk_enhanced_20260525-204625/enhanced_eval_report.md`

候选评估只处理：

- `管路护理`
- `入量_静脉用药`

候选规则：

- 不处理病情观察。
- 不应用 `needs_review`。
- 不应用 main 为 null、candidate 非 null 的风险项。
- 只应用 `decision = propose_override`。

候选报告结果：

| 字段 | total | main_correct | candidate_correct | propose_override | needs_review | main_correct_candidate_wrong |
|---|---:|---:|---:|---:|---:|---:|
| 管路护理 | 57 | 53 | 56 | 2 | 1 | 0 |
| 入量_静脉用药 | 57 | 47 | 55 | 8 | 0 | 0 |
| 合计 | 114 | 100 | 111 | 10 | 1 | 0 |

增强结果：

| 字段 | main_correct | enhanced_correct | fixed_by_override | new_errors |
|---|---:|---:|---:|---:|
| 管路护理 | 53 | 55 | 2 | 0 |
| 入量_静脉用药 | 47 | 55 | 8 | 0 |

结论：

- 这是目前最明确的净收益路线。
- 但它仍应作为实验性增强结果或可配置覆盖，不应静默改主 `result.json`。

## 4. 病情观察及处理：残留问题拆解

`病情观察及处理` 与 IV/管路不同，它是文字密集、自由文本、容易出现近形字误读、标点差异和轻微改写的字段。我们已经尝试了多条路线，但没有找到稳定覆盖源。

### 4.1 residual casebook 与 refined eval

代表报告：

- `/data1/jianf-vllm/runs/observation_residual_casebook_20260525-211324/observation_residual_summary.json`
- `/data1/jianf-vllm/runs/observation_eval_refined_20260526-151747/observation_eval_refined_report.md`

早期 residual casebook：

- 总 residual case：12
- `canonical_only`：1
- `punctuation_only`：5
- `rewrite_or_paraphrase`：4
- `col_better_than_main`：2

refined eval 后，57 个 block 的 main / old_col 分布：

| 来源 | exact | canonical | punctuation | text_equivalent_minor | missing_text | char_level_mismatch | gold_needs_check |
|---|---:|---:|---:|---:|---:|---:|---:|
| main | 45 | 1 | 3 | 1 | 1 | 5 | 1 |
| old_col | 47 | 1 | 3 | 1 | 0 | 4 | 1 |

结论：

- 病情观察中的“错误”有相当一部分其实是标点、全半角或 gold 复核问题。
- 剩余真正难的是字符级错误，例如近形字、英数混排、单位和评分。

### 4.2 whole-column direct / rawlines / verbatim prompt

代表报告：

- `/data1/jianf-vllm/runs/observation_direct_vs_rawlines_20260525-084254/observation_direct_vs_rawlines_report.md`
- `/data1/jianf-vllm/runs/observation_verbatim_20260525-213954/observation_verbatim_report.md`

direct-vs-rawlines 观察：

- `direct_v2` 比 main/old_col 有小幅改善。
- rawlines final 不稳定，有时 raw_lines 能读到字，但 final 合并引入问题。
- 整体没有达到“可作为覆盖源”的安全性。

verbatim whole-column prompt：

| 方法 | correct | 主要问题 |
|---|---:|---|
| main | 45 | 基线 |
| old_col | 47 | 小幅优于 main |
| verbatim | 27 | overfill 17，main 正确却被 verbatim 搞错 23 条 |

结论：

- 对病情观察，整列“严格逐行转录”反而使模型过填和误读变多。
- 病情观察不能简单照搬 IV 的 raw_lines 思路。

### 4.3 图像预处理：raw_col 插值、去线、CLAHE、二值化

代表报告：

- `/data1/jianf-vllm/runs/observation_preprocess_ablation_20260526-160017/observation_preprocess_ablation_report.md`

结果：

| variant | correct | 结论 |
|---|---:|---|
| raw_col | 45 | baseline |
| clean_2x | 44 | 无收益 |
| clean_3x | 44 | 无收益 |
| line_removed_2x | 42 | 更差 |
| clahe_2x | 44 | 无收益 |
| binary_2x | 44 | 局部修字，但整体无收益 |

重要纠偏：

- 这一轮的 `clean_2x/clean_3x` 名称有误导性；代码实际是从已保存 `raw_col` 直接插值放大，不是真正从 clean block 重新裁图。
- 所以这轮只能说明“raw_col 插值放大/去线/CLAHE/二值化”无净收益，不能证明 true clean crop 无效。

### 4.4 true clean crop：native / 2x / 3x

代表报告：

- `/data1/jianf-vllm/runs/observation_true_clean_crop_20260526-172653/observation_true_clean_crop_report.md`

尝试内容：

- 从原始输入重新走金主任 cutter 的时间锚点和表头拼接逻辑。
- 在画红线之前、`optimize_image_for_llm` 之前保存 `clean_final_block`。
- 从 clean_final_block 裁出病情观察列。
- 测试 native、2x、3x。

结果：

| variant | correct | 观察 |
|---|---:|---|
| raw_col | 45 | baseline |
| true_clean_native | 45 | 无净收益 |
| true_clean_2x | 45 | char_level_mismatch 略降，但 correct 不升 |
| true_clean_3x | 45 | 同上 |

结论：

- 真正 clean crop 没有带来决定性提升。
- 这说明病情观察残留错误不是简单由红线、表头拼接或普通缩放造成。

### 4.5 PDF 高 DPI clip

代表报告：

- `/data1/jianf-vllm/runs/observation_pdf_dpi_probe_20260528-013712/observation_pdf_dpi_probe_report.md`

PDF 质量诊断：

- 目标页 `image_count = 74`
- `possible_tiled_pdf = true`
- 护理记录主体不是可用文字层，而是图像层。
- 1200 DPI 局部 clip 技术可行，但可能只是更细采样已有图像块。

识别验证结果：

| variant | correct |
|---|---:|
| pdf_clip_300dpi | 0 |
| pdf_clip_600dpi | 1 |
| pdf_clip_900dpi | 0 |
| pdf_clip_1200dpi | 0 |
| pdf_clip_900dpi_down_to_300dpi | 1 |
| pdf_clip_1200dpi_down_to_300dpi | 0 |

结论：

- 高 DPI 局部重渲染没有可靠收益。
- 如果 PDF 内部本身是图像块拼接或低质量扫描，提升 DPI 只是重采样，不能创造新字符信息。

### 4.6 行级识别：header+row、row-only、2x/3x

代表报告：

- `/data1/jianf-vllm/runs/observation_header_row_probe_20260528-023041/observation_header_row_probe_report.md`
- `/data1/jianf-vllm/runs/observation_row_prompt_ablation_20260528-030002/observation_row_prompt_ablation_report.md`

核心问题：

- header+row crop 里大块表头空白可能稀释正文视觉分辨率。
- row-only crop 只保留正文文字带，看是否能减少字符错误。
- 新 prompt 强调精密转录、弱医学上下文、不确定就标注。

row prompt ablation 的关键结果：

| 输入/方法 | 平均编辑距离 | exact | 主要问题 |
|---|---:|---:|---|
| header_row + PaddleOCR | 4.50 | 0 | OCR 不稳定 |
| header_row + Qwen old | 3.17 | 1 | 仍有字符错 |
| header_row + Qwen precise | 3.58 | - | prompt 未改善 |
| row_only + PaddleOCR | 36.25 | 0 | 检测器大量漏识别 |
| row_only + Qwen old | 3.00 | - | 小幅改善 |
| row_only + Qwen precise | 2.75 | - | 小幅改善 |
| row_only_2x + PaddleOCR | 6.00 | - | 放大后 OCR 检测恢复一部分 |
| row_only_3x + PaddleOCR | 5.08 | - | 仍弱于 Qwen |
| row_only_3x + Qwen old | 2.75 | - | 小幅改善，不是质变 |

结论：

- row-only 和 3x 对 Qwen 有小幅帮助，但没有质变。
- PaddleOCR 在未放大的细小 row-only 上彻底失败，说明 OCR detection/input size 是严重瓶颈。
- 但放大后 OCR 仍不如 Qwen，说明 OCR 识别器本身也不是可靠替代。

### 4.7 OCR/VLM 字符识别瓶颈定位

代表报告：

- `/data1/jianf-vllm/runs/observation_recognition_bottleneck_probe_20260528-031512/observation_recognition_bottleneck_report.md`

新增输入：

- `row_only_original`
- `row_only_canvas_h48`
- `row_only_canvas_h64`
- `row_only_canvas_h96`

关键结果：

| 方法/输入 | 平均编辑距离 | 观察 |
|---|---:|---|
| Qwen precise row_only_original | 2.75 | 基线较好 |
| Qwen precise canvas_h48 | 2.92 | 无提升 |
| Qwen precise canvas_h64 | 2.67 | 小幅最好 |
| Qwen precise canvas_h96 | 2.75 | 无进一步提升 |
| PaddleOCR det+rec h48 | 5.42 | 比 raw row-only 好，但仍弱 |
| PaddleOCR det+rec h64 | 5.33 | 仍弱 |
| PaddleOCR det+rec h96 | 5.00 | 仍弱 |
| PaddleOCR rec-only h96 | 6.92 | rec-only 也不够好 |

结论：

- canvas 标准化能缓解 PaddleOCR 的检测失败，但不能让 OCR 接近 Qwen。
- Qwen 对画布形态有轻微敏感，但瓶颈主要是局部字形辨认能力。
- 继续在普通 crop/scale 上调参，大概率收益很低。

### 4.8 医学上下文 prompt

代表报告：

- `/data1/jianf-vllm/runs/observation_med_context_prompt_probe_20260528-034617/observation_med_context_prompt_report.md`

尝试内容：

- 在病情观察行级 prompt 中加入常见医学/护理表达参考，如 `遵医嘱`、`泵入`、`ECMO`、`CPOT0分`、`ml/h`、`r/min` 等。
- 不做 OCR。
- 不改主流程。

结果：

- overall：improved 6，same 41，worse 1。
- `h64`：平均编辑距离 2.67 -> 2.67，基本不变。
- `h96`：平均编辑距离 2.75 -> 2.58，小幅改善。
- 局部可修复 `CPOT0`、`医嘱继观` 等问题，但不是系统性提升。

结论：

- 医学上下文提示有局部帮助，但不能解决主要瓶颈。
- 它属于 prompt/knowledge 层，不属于图像增强层。
- 直接把领域词表塞进识别 prompt，仍可能带来过度先验和误补风险。

## 5. 病情观察 reviewer：从“识别”转向“审查”

这一阶段的目标不是继续让 OCR/VLM 直接识别得更准，而是在 raw OCR/raw Qwen 输出后，用 reviewer 模型审查疑似字符错误、单位格式和医学短语问题。gold 只用于最终评估，不进入 prompt。

### 5.1 reviewer strict 评估

代表报告：

- `/data1/jianf-vllm/runs/observation_text_reviewer_experiment_20260528-041615/observation_text_reviewer_report.md`

实验组：

- `llm_reviewer_no_lexicon`
- `llm_reviewer_with_lexicon`
- `regex_candidates_only`
- `regex_candidates_plus_llm_reviewer`

raw Qwen strict 结果：

| reviewer | CER before | CER after | exact before -> after | 观察 |
|---|---:|---:|---|---|
| no lexicon | 0.0391 | 0.0496 | 1 -> 2 | 修少数错，但过改 |
| with lexicon | 0.0391 | 0.0814 | 1 -> 1 | 词表导致更多规范化/误改 |
| regex + LLM | 0.0391 | 0.0507 | 1 -> - | 修 1 条，过改 4 条 |

典型成功：

- `80m1/h -> 80ml/h`

典型问题：

- `转/分 -> r/min`
- `L/分 -> L/min`
- `CPOT0分 -> CPOT 0分`
- `ML/mL/ml`、`UG/ug/μg` 规范化
- 部分单位或数字推断属于危险修改

strict 结论：

- reviewer 按逐字转录 CER 看没有净收益。
- 它会把“原文转录”改成“临床规范表达”，这在 strict transcription 任务里是错误。

### 5.2 reviewer 宽容评估

代表报告：

- `/data1/jianf-vllm/runs/observation_text_reviewer_tolerant_eval_20260528-225417/observation_text_reviewer_tolerant_eval_report.md`

新增三层评估：

1. strict transcription：是否逐字还原。
2. format-tolerant：标点、空格、单位表面写法是否临床等价。
3. clinical semantic：关键临床槽位是否保持。

关键结果：

| 来源/组别 | strict CER before -> after | tolerant CER before -> after | slot F1 before -> after | 结论 |
|---|---:|---:|---:|---|
| raw_qwen + no lexicon | 0.0391 -> 0.0496 | 0.0253 -> 0.0241 | 基本不变 | strict 变差，format 略好 |
| raw_qwen + with lexicon | 0.0391 -> 0.0814 | 0.0253 -> 0.0326 | 有危险变化 | 不适合 |
| raw_qwen + regex+LLM | 0.0391 -> 0.0507 | 0.0253 -> 0.0233 | 0.9167 -> 0.9167 | format 有小收益，semantic 不变 |
| raw_ocr + regex+LLM | - | 0.0797 -> 0.0721 | 0.7239 -> 0.7500 | OCR 文本上也有小收益，但 OCR 本身弱 |

edit 重新分类：

| 类别 | 含义 | 数量 |
|---|---|---:|
| true_character_correction | gold 支持的真实字符修正 | 29 |
| benign_format_normalization | 格式/单位表面规范化 | 51 |
| punctuation_only | 仅标点 | 14 |
| semantic_inference | 补充原文没有显式出现的单位/语义 | 5 |
| risky_unit_substitution | 高风险单位替换 | 10 |
| harmful_deletion_or_insertion | 删除/新增关键内容 | 39 |

宽容评估结论：

- reviewer 不是 raw transcription 覆盖源。
- reviewer 可以作为 QC suggestion 或 semantic normalization 辅助。
- format-tolerant 能解释一部分 strict CER 变差，但仍有 risky substitution 和 harmful insertion/deletion，不能自动放入主流程。

## 6. 尝试路线总表

| 层级 | 尝试 | 代表 run | 结果 | 决策 |
|---|---|---|---|---|
| 模型 | Qwen3-32B / Qwen2.5-72B / 小模型矩阵 | `model_compare_report_20260525-041208` | Qwen3-32B 稳定；72B 无明显胜出；小模型差 | Qwen3-32B 继续做主基线 |
| M prompt | `PROMPT_M_V2_CONTINUATION` | `prompt_v2_validation_20260525-063531` | M strict_total 26 -> 20 | 保留候选，不默认替换 |
| 管路护理 | 单列 VLM + shadow | `target_column_vlm_20260525-074656` | col_correct 56 vs main 53，main_correct_col_wrong 0 | 有覆盖候选价值 |
| IV | raw_lines prompt | `target_column_iv_rawlines_20260525-081135` | col_correct 45 -> 50 | 有效 |
| IV | clean2x crop | `target_column_iv_clean2x_20260525-082612` | col_correct 50 -> 52 | 有效 |
| IV | v3 unit-aware | `target_column_iv_v3_unit_20260525-085732` | 过度规范化，准确率回退 | 不作为最佳 |
| IV | v4 preserve-case | `target_column_iv_v4_preserve_case_20260525-092139` | report_correct 最高，true_char_mismatch 最低 | 当前最佳 IV 候选 |
| 高风险覆盖 | IV + 管路 propose_override | `high_risk_enhanced_20260525-204625` | 修复 10，新增 0 | 值得做可配置实验开关 |
| 病情观察 | 单列 direct | `target_column_vlm_20260525-074656` | 无净收益 | 不覆盖 |
| 病情观察 | direct_v2 / rawlines | `observation_direct_vs_rawlines_20260525-084254` | direct_v2 小幅好，仍不安全 | 不覆盖 |
| 病情观察 | whole-column verbatim | `observation_verbatim_20260525-213954` | correct 27，overfill 17 | 停止 |
| 病情观察 | raw_col 图像增强 | `observation_preprocess_ablation_20260526-160017` | 无净收益，部分更差 | 停止 |
| 病情观察 | true clean native/2x/3x | `observation_true_clean_crop_20260526-172653` | correct 都 45 | 停止作为主方向 |
| 病情观察 | PDF 高 DPI clip | `observation_pdf_dpi_probe_20260528-013712` | 无可靠收益 | 停止作为主方向 |
| 病情观察 | header+row / row-only / 2x/3x | `observation_row_prompt_ablation_20260528-030002` | Qwen 小幅收益；OCR 仍差 | 可作人工审查证据，不覆盖 |
| 病情观察 | canvas h48/h64/h96 | `observation_recognition_bottleneck_probe_20260528-031512` | h64 小幅最好；仍非质变 | 停止大规模图像调参 |
| 病情观察 | 医学上下文 prompt | `observation_med_context_prompt_probe_20260528-034617` | improved 6, worse 1，小幅 | 可用于 reviewer/QC，不单独覆盖 |
| 病情观察 | reviewer strict | `observation_text_reviewer_experiment_20260528-041615` | strict CER 变差 | 不覆盖 |
| 病情观察 | reviewer tolerant/semantic | `observation_text_reviewer_tolerant_eval_20260528-225417` | format 有小收益，危险修改仍存在 | 只做 QC suggestion / 宽容评估 |

## 7. 对用户原始总结的细化

用户原始记录：

> 提示词增强 不行
> 单列做 不行
> 单列逐行做 不行
> OCR 的彻底失败可能预示着提取难度确实很大
> 去边界 光扫文字 不行
> 图像处理增强 不行
> 外界医疗知识 不行
> 审查 ing

细化后应改成：

1. **提示词增强：字段相关。**
   - M 区 continuation prompt 有效果。
   - IV rawlines/v4 prompt 有效果。
   - 病情观察整列/逐行 prompt 没有系统性收益。

2. **单列做：不是全都不行。**
   - 管路护理单列有效。
   - IV direct 单列最初无净收益，但 rawlines + clean2x + v4 后有效。
   - 病情观察单列无稳定净收益。

3. **单列逐行做：对病情观察没有质变。**
   - row-only / 3x / canvas h64 对 Qwen 有小幅改善。
   - 仍无法解决近形字、英数混排和局部字符辨认。
   - 可作为人工审查证据，不适合自动覆盖。

4. **OCR 不是完全“什么都不行”，但不适合当主力。**
   - 未放大的 row-only 小图会让 PaddleOCR detection 大量失败。
   - 放大或 canvas 标准化后检测恢复，但平均错误仍明显高于 Qwen。
   - OCR 可以作为 evidence 或辅助对照，不适合作为病情观察覆盖源。

5. **去边界/只扫文字/图像处理增强：对病情观察无净收益。**
   - raw_col 插值、去线、CLAHE、二值化无效。
   - true clean crop native/2x/3x 也无明显提升。
   - PDF 高 DPI clip 无可靠收益。

6. **外界医疗知识：直接识别 prompt 中收益小，reviewer/QC 中更有意义。**
   - 医学上下文 prompt 局部改善，但不是系统方案。
   - reviewer 加词表会更容易规范化甚至过改。
   - 更合理的位置是评估侧和 QC suggestion，而不是原始转录覆盖。

7. **审查是目前病情观察方向里更值得继续的，但不能自动覆盖。**
   - strict transcription 下 reviewer 失败。
   - tolerant/semantic 下能解释格式等价，并发现部分真实修正。
   - 仍存在 risky unit substitution 和 harmful insertion/deletion，必须保留人工复核或配置开关。

## 8. 下一阶段建议

### 应继续推进

1. **高风险列增强实验开关**
   - 只针对 `入量_静脉用药` 和 `管路护理`。
   - 只应用 `propose_override`。
   - 保留 `override_log.jsonl`、候选来源、raw response、evidence。
   - 默认仍不覆盖主 `result.json`，先生成 `result_enhanced.json`。

2. **病情观察 reviewer 作为 QC suggestion**
   - 不覆盖原始转录。
   - 输出：疑似字符错误、格式等价、危险单位替换、需要人工复核。
   - 对 reviewer 输出按 strict / tolerant / semantic 三层评估。

3. **gold 与评估口径复核**
   - 病情观察里不少 residual 是标点、格式、gold 可能错误。
   - 需要明确哪些是 raw transcription 任务，哪些是 clinical semantic 任务。
   - 不应把格式规范化错误和危险字符错误混在一个 mismatch 里。

4. **人工可视化 casebook**
   - 对病情观察保留 row-only / header-row / crop / raw Qwen / reviewer suggestion。
   - 用于人工判断，而不是自动修正。

### 应暂时停止或降优先级

1. 继续尝试普通插值放大、CLAHE、二值化、去表格线。
2. 继续把病情观察整列 prompt 写得更长。
3. 用 PaddleOCR 替代 Qwen/VLM 做病情观察主识别。
4. 直接把 reviewer 的 `reviewed_text` 覆盖主结果。
5. 把医学词表当成“自动纠错规则”写进 parser。
6. 不带 casebook 和 no-regression 统计地继续改 prompt。

## 9. 关键报告索引

模型与主流程：

- `/data1/jianf-vllm/runs/model_compare_report_20260525-041208/report.md`
- `/data1/jianf-vllm/runs/model_compare_report_eval_20260525-050620/report.md`

M 区：

- `/data1/jianf-vllm/runs/model_compare_report_prompt_v2_20260525-054856/report.md`
- `/data1/jianf-vllm/runs/prompt_v2_generalization_20260525-061220/report.md`
- `/data1/jianf-vllm/runs/prompt_v2_validation_20260525-063531/report.md`

IV / 管路：

- `/data1/jianf-vllm/runs/target_column_vlm_20260525-074656/target_column_vlm_report.md`
- `/data1/jianf-vllm/runs/target_column_iv_rawlines_20260525-081135/target_column_iv_rawlines_report.md`
- `/data1/jianf-vllm/runs/target_column_iv_clean2x_20260525-082612/target_column_iv_rawlines_clean2x_report.md`
- `/data1/jianf-vllm/runs/target_column_iv_v3_unit_20260525-085732/target_column_iv_v3_unit_report.md`
- `/data1/jianf-vllm/runs/target_column_iv_v4_preserve_case_20260525-092139/target_column_iv_v4_preserve_case_report.md`
- `/data1/jianf-vllm/runs/high_risk_strategy_review_20260525-171555/high_risk_strategy_review_report.md`
- `/data1/jianf-vllm/runs/high_risk_column_candidate_20260525-173241/high_risk_column_candidate_report.md`
- `/data1/jianf-vllm/runs/high_risk_enhanced_20260525-204625/enhanced_eval_report.md`

病情观察：

- `/data1/jianf-vllm/runs/observation_residual_casebook_20260525-211324/observation_residual_casebook.md`
- `/data1/jianf-vllm/runs/observation_eval_refined_20260526-151747/observation_eval_refined_report.md`
- `/data1/jianf-vllm/runs/observation_direct_vs_rawlines_20260525-084254/observation_direct_vs_rawlines_report.md`
- `/data1/jianf-vllm/runs/observation_verbatim_20260525-213954/observation_verbatim_report.md`
- `/data1/jianf-vllm/runs/observation_preprocess_ablation_20260526-160017/observation_preprocess_ablation_report.md`
- `/data1/jianf-vllm/runs/observation_true_clean_crop_20260526-172653/observation_true_clean_crop_report.md`
- `/data1/jianf-vllm/runs/observation_pdf_dpi_probe_20260528-013712/observation_pdf_dpi_probe_report.md`
- `/data1/jianf-vllm/runs/observation_line_probe_20260527-105255/observation_line_probe_report.md`
- `/data1/jianf-vllm/runs/observation_header_row_probe_20260528-023041/observation_header_row_probe_report.md`
- `/data1/jianf-vllm/runs/observation_row_prompt_ablation_20260528-030002/observation_row_prompt_ablation_report.md`
- `/data1/jianf-vllm/runs/observation_recognition_bottleneck_probe_20260528-031512/observation_recognition_bottleneck_report.md`
- `/data1/jianf-vllm/runs/observation_med_context_prompt_probe_20260528-034617/observation_med_context_prompt_report.md`
- `/data1/jianf-vllm/runs/observation_text_reviewer_experiment_20260528-041615/observation_text_reviewer_report.md`
- `/data1/jianf-vllm/runs/observation_text_reviewer_tolerant_eval_20260528-225417/observation_text_reviewer_tolerant_eval_report.md`

## 10. 最短决策摘要

如果下一步要做生产方向的实验，优先级应是：

1. **把 IV + 管路的 high-risk candidate override 做成可配置实验开关**，继续扩大验证。
2. **病情观察不做自动覆盖**，先用 reviewer 输出 QC suggestion 与人工复核队列。
3. **病情观察停止普通图像增强方向**，除非有新的源图质量或模型能力变化。
4. **评估报告必须区分 strict / tolerant / semantic**，否则会把格式等价、gold 问题和真实危险错误混在一起。
