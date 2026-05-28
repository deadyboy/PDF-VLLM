# 病情观察及处理 reviewer 宽容评估实验

## 实验目的

本轮只重算评估指标，不重跑 OCR、Qwen 或 reviewer。目标是区分 strict transcription、format-tolerant equivalence、clinical semantic equivalence，以及 unsafe inference / risky substitution。

## 输入

- reviewer run：`/data1/jianf-vllm/runs/observation_text_reviewer_experiment_20260528-041615`
- evaluated JSONL：`/data1/jianf-vllm/runs/observation_text_reviewer_experiment_20260528-041615/observation_text_reviewer_evaluated.jsonl`
- equivalence config：`config/clinical_equivalence_rules.yaml`
- 记录数：96

## strict metric 总表

| 文本来源 | reviewer组 | 样本数 | strict_CER_before | strict_CER_after | strict_exact_before | strict_exact_after |
|---|---|---:|---:|---:|---:|---:|
| 原始OCR文本 | LLM审查-无词表 | 12 | 0.1103 | 0.1182 | 0 | 1 |
| 原始OCR文本 | LLM审查-带词表 | 12 | 0.1103 | 0.1239 | 0 | 1 |
| 原始OCR文本 | 仅候选检测 | 12 | 0.1103 | 0.1103 | 0 | 0 |
| 原始OCR文本 | 候选+LLM审查 | 12 | 0.1103 | 0.1132 | 0 | 1 |
| 原始Qwen文本 | LLM审查-无词表 | 12 | 0.0391 | 0.0496 | 1 | 2 |
| 原始Qwen文本 | LLM审查-带词表 | 12 | 0.0391 | 0.0814 | 1 | 1 |
| 原始Qwen文本 | 仅候选检测 | 12 | 0.0391 | 0.0391 | 1 | 1 |
| 原始Qwen文本 | 候选+LLM审查 | 12 | 0.0391 | 0.0507 | 1 | 2 |

## format-tolerant metric 总表

| 文本来源 | reviewer组 | tolerant_CER_before | tolerant_CER_after | tolerant_exact_before | tolerant_exact_after | strict变差但tolerant不变 | strict变差但tolerant变好 | strict/tolerant都变差 |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| 原始OCR文本 | LLM审查-无词表 | 0.0797 | 0.0767 | 1 | 2 | 1 | 1 | 2 |
| 原始OCR文本 | LLM审查-带词表 | 0.0797 | 0.0791 | 1 | 2 | 1 | 2 | 2 |
| 原始OCR文本 | 仅候选检测 | 0.0797 | 0.0797 | 1 | 1 | 0 | 0 | 0 |
| 原始OCR文本 | 候选+LLM审查 | 0.0797 | 0.0721 | 1 | 2 | 2 | 1 | 1 |
| 原始Qwen文本 | LLM审查-无词表 | 0.0253 | 0.0241 | 2 | 3 | 3 | 0 | 1 |
| 原始Qwen文本 | LLM审查-带词表 | 0.0253 | 0.0326 | 2 | 3 | 6 | 0 | 1 |
| 原始Qwen文本 | 仅候选检测 | 0.0253 | 0.0253 | 2 | 2 | 0 | 0 | 0 |
| 原始Qwen文本 | 候选+LLM审查 | 0.0253 | 0.0233 | 2 | 3 | 4 | 0 | 0 |

## clinical semantic metric 总表

| 文本来源 | reviewer组 | slot_f1_before | slot_f1_after | value_match_before | value_match_after | unit_equiv_before | unit_equiv_after | dangerous_slot_change_count |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| 原始OCR文本 | LLM审查-无词表 | 0.7239 | 0.7407 | 0.5714 | 0.6665 | 0.6667 | 0.7500 | 10 |
| 原始OCR文本 | LLM审查-带词表 | 0.7239 | 0.7500 | 0.5714 | 0.7015 | 0.6667 | 0.7500 | 10 |
| 原始OCR文本 | 仅候选检测 | 0.7239 | 0.7239 | 0.5714 | 0.5714 | 0.6667 | 0.6667 | 11 |
| 原始OCR文本 | 候选+LLM审查 | 0.7239 | 0.7500 | 0.5714 | 0.7064 | 0.6667 | 0.7500 | 8 |
| 原始Qwen文本 | LLM审查-无词表 | 0.9167 | 0.9167 | 0.8958 | 0.9167 | 0.9167 | 0.9167 | 0 |
| 原始Qwen文本 | LLM审查-带词表 | 0.9167 | 0.9167 | 0.8958 | 0.9167 | 0.9167 | 0.9167 | 2 |
| 原始Qwen文本 | 仅候选检测 | 0.9167 | 0.9167 | 0.8958 | 0.8958 | 0.9167 | 0.9167 | 1 |
| 原始Qwen文本 | 候选+LLM审查 | 0.9167 | 0.9167 | 0.8958 | 0.9167 | 0.9167 | 0.9167 | 0 |

## edit_effect_category 统计

| category | count |
|---|---:|
| benign_format_normalization | 51 |
| harmful_deletion_or_insertion | 39 |
| punctuation_only | 14 |
| risky_unit_substitution | 11 |
| semantic_inference | 5 |
| true_character_correction | 28 |

## strict CER 变差但 tolerant 不变的例子

| case | 来源 | reviewer组 | gold | original_text | reviewed_text | strict_delta | tolerant_delta |
|---|---|---|---|---|---|---:|---:|
| gold_dev_m_002__block_23 | 原始Qwen文本 | LLM审查-带词表 | 遵医嘱肝素钠调整至6.5ml/h泵入，患者ECMO应用；机器运转正常，转速：3220转/分，流量：3.74L/分；舒芬太尼液泵毕，医嘱予原量以4ml/h泵入；肠内营养液暂停应用，胰岛素余液调整至2ml/h | 遵医嘱肝素钠调整至6.5ml/h泵入，患者ECMO应用，机器运转正常，转速：3220转/分，流量：3.74L/分，舒芬太尼液泵毕，医嘱予原量以4ml/h泵入，肠内营养液暂停应用，胰岛素余液调整至2ml/h | 遵医嘱肝素钠调整至6.5ml/h泵入，患者ECMO应用，机器运转正常，转速：3220r/min，流量：3.74L/min，舒芬太尼液泵毕，医嘱予原量以4ml/h泵入，肠内营养液暂停应用，胰岛素余液调整至2ml/h | 0.0686 | 0.0000 |
| gold_dev_m_002__block_23 | 原始Qwen文本 | 候选+LLM审查 | 遵医嘱肝素钠调整至6.5ml/h泵入，患者ECMO应用；机器运转正常，转速：3220转/分，流量：3.74L/分；舒芬太尼液泵毕，医嘱予原量以4ml/h泵入；肠内营养液暂停应用，胰岛素余液调整至2ml/h | 遵医嘱肝素钠调整至6.5ml/h泵入，患者ECMO应用，机器运转正常，转速：3220转/分，流量：3.74L/分，舒芬太尼液泵毕，医嘱予原量以4ml/h泵入，肠内营养液暂停应用，胰岛素余液调整至2ml/h | 遵医嘱肝素钠调整至6.5ml/h泵入，患者ECMO应用，机器运转正常，转速：3220转/分，流量：3.74L/min，舒芬太尼液泵毕，医嘱予原量以4ml/h泵入，肠内营养液暂停应用，胰岛素余液调整至2ml/h | 0.0294 | 0.0000 |
| gold_smoke_001__block_01 | 原始Qwen文本 | LLM审查-带词表 | CPOT0分 | CPOT0分 | CPOT 0分 | 0.1667 | 0.0000 |
| gold_smoke_001__block_12 | 原始OCR文本 | 候选+LLM审查 | APTT：44.8，遵医嘱予肝素钠调整至6ml/h泵入，力月西泵毕，医嘱予咪达唑仑注射液（苏恩华-5mg:1ml）50MG氯化钠注射液（丰原-100ml:0.9%，软袋双阀)45M调整至10ml/h泵入执行。 | APTT: 44.8, 遵医嘱予肝素钠调整至6m1/h泵入。力月西泵毕，医嘱予咪达唑仑注射液(苏恩华-5mg\|:1ml)50M配氯化钠注射液(丰原-100ml:0.9%,软袋双阀) 45胍调整至10ml/h泵入执行。 | APTT: 44.8, 遵医嘱予肝素钠调整至6ml/h泵入。力月西泵毕，医嘱予咪达唑仑注射液(苏恩华-5mg\|:1ml)50ml配氯化钠注射液(丰原-100ml:0.9%,软袋双阀) 45mg调整至10ml/h泵入执行。 | 0.0192 | 0.0000 |
| gold_smoke_001__block_12 | 原始Qwen文本 | LLM审查-无词表 | APTT：44.8，遵医嘱予肝素钠调整至6ml/h泵入，力月西泵毕，医嘱予咪达唑仑注射液（苏恩华-5mg:1ml）50MG氯化钠注射液（丰原-100ml:0.9%，软袋双阀)45M调整至10ml/h泵入执行。 | APTT：44.8，遵医嘱予肝素钠调整至6ml/h泵入，力月西泵毕，医嘱予咪达唑仑注射液（苏恩华-5mg：1ml)50MG氯化钠注射液(丰原-100ml:0.9%,软袋双阀)45ML调整至10ml/h泵入执行。 | APTT：44.8，遵医嘱予肝素钠调整至6ml/h泵入，力月西泵毕，医嘱予咪达唑仑注射液（苏恩华-5mg：1ml)50mg氯化钠注射液(丰原-100ml:0.9%,软袋双阀)45ml调整至10ml/h泵入执行。 | 0.0288 | 0.0000 |
| gold_smoke_001__block_12 | 原始Qwen文本 | LLM审查-带词表 | APTT：44.8，遵医嘱予肝素钠调整至6ml/h泵入，力月西泵毕，医嘱予咪达唑仑注射液（苏恩华-5mg:1ml）50MG氯化钠注射液（丰原-100ml:0.9%，软袋双阀)45M调整至10ml/h泵入执行。 | APTT：44.8，遵医嘱予肝素钠调整至6ml/h泵入，力月西泵毕，医嘱予咪达唑仑注射液（苏恩华-5mg：1ml)50MG氯化钠注射液(丰原-100ml:0.9%,软袋双阀)45ML调整至10ml/h泵入执行。 | APTT：44.8，遵医嘱予肝素钠调整至6ml/h泵入，力月西泵毕，医嘱予咪达唑仑注射液（苏恩华-5mg：1ml）50mg氯化钠注射液(丰原-100ml:0.9%,软袋双阀)45ml调整至10ml/h泵入执行。 | 0.0192 | 0.0000 |
| gold_smoke_001__block_12 | 原始Qwen文本 | 候选+LLM审查 | APTT：44.8，遵医嘱予肝素钠调整至6ml/h泵入，力月西泵毕，医嘱予咪达唑仑注射液（苏恩华-5mg:1ml）50MG氯化钠注射液（丰原-100ml:0.9%，软袋双阀)45M调整至10ml/h泵入执行。 | APTT：44.8，遵医嘱予肝素钠调整至6ml/h泵入，力月西泵毕，医嘱予咪达唑仑注射液（苏恩华-5mg：1ml)50MG氯化钠注射液(丰原-100ml:0.9%,软袋双阀)45ML调整至10ml/h泵入执行。 | APTT：44.8，遵医嘱予肝素钠调整至6ml/h泵入，力月西泵毕，医嘱予咪达唑仑注射液（苏恩华-5mg：1ml）50mg氯化钠注射液(丰原-100ml:0.9%,软袋双阀)45ml调整至10ml/h泵入执行。 | 0.0192 | 0.0000 |
| gold_smoke_001__block_14 | 原始Qwen文本 | LLM审查-无词表 | 舒芬太尼泵毕，医嘱予枸橼酸舒芬太尼注射液(鄂,宜昌人福-50ug：1ml)200UG氯化钠注射液（丰原,-100ml：0.9%，软袋双阀）50M调整至2ml/h执行。 | 舒芬太尼泵毕，医嘱予枸橼酸舒芬太尼注射液（鄂宜昌人福-50ug:1ml)200UG氯化钠注射液(丰原├-100ml:0.9%,软袋双阀)50ML调整至2ml/h执行。 | 舒芬太尼泵毕，医嘱予枸橼酸舒芬太尼注射液（鄂宜昌人福-50μg:1ml）200μg氯化钠注射液(丰原├-100ml:0.9%，软袋双阀）50ml调整至2ml/h执行。 | 0.0361 | 0.0000 |
| gold_smoke_001__block_14 | 原始Qwen文本 | LLM审查-带词表 | 舒芬太尼泵毕，医嘱予枸橼酸舒芬太尼注射液(鄂,宜昌人福-50ug：1ml)200UG氯化钠注射液（丰原,-100ml：0.9%，软袋双阀）50M调整至2ml/h执行。 | 舒芬太尼泵毕，医嘱予枸橼酸舒芬太尼注射液（鄂宜昌人福-50ug:1ml)200UG氯化钠注射液(丰原├-100ml:0.9%,软袋双阀)50ML调整至2ml/h执行。 | 舒芬太尼泵毕，医嘱予枸橼酸舒芬太尼注射液（鄂宜昌人福-50μg:1ml）200μg氯化钠注射液(丰原├-100ml:0.9%，软袋双阀）50ml调整至2ml/h执行。 | 0.0361 | 0.0000 |
| gold_smoke_001__block_14 | 原始Qwen文本 | 候选+LLM审查 | 舒芬太尼泵毕，医嘱予枸橼酸舒芬太尼注射液(鄂,宜昌人福-50ug：1ml)200UG氯化钠注射液（丰原,-100ml：0.9%，软袋双阀）50M调整至2ml/h执行。 | 舒芬太尼泵毕，医嘱予枸橼酸舒芬太尼注射液（鄂宜昌人福-50ug:1ml)200UG氯化钠注射液(丰原├-100ml:0.9%,软袋双阀)50ML调整至2ml/h执行。 | 舒芬太尼泵毕，医嘱予枸橼酸舒芬太尼注射液（鄂宜昌人福-50μg:1ml）200μg氯化钠注射液(丰原├-100ml:0.9%,软袋双阀)50ml调整至2ml/h执行。 | 0.0602 | 0.0000 |
| gold_smoke_001__block_16 | 原始OCR文本 | LLM审查-无词表 | 氯化钠注射液(丰原-100ml:0.9%,软袋双阀)48ML;盐酸右美托咪定注射液(辰欣药业-0.2mg:2ml)0.4;MG以4ml/h续泵执行。 | 氯化钠注射液（丰原-100ml:0.9%,软袋双阀).48m盐酸右美托咪定注射液(辰欣药业-0. 2mg:2ml)0.4MG以4ml/h续泵执行。 | 氯化钠注射液（丰原-100ml:0.9%,软袋双阀）.48mg盐酸右美托咪定注射液(辰欣药业-0.2mg:2ml)0.4mg以4ml/h续泵执行。 | 0.0270 | 0.0000 |
| gold_smoke_001__block_16 | 原始OCR文本 | LLM审查-带词表 | 氯化钠注射液(丰原-100ml:0.9%,软袋双阀)48ML;盐酸右美托咪定注射液(辰欣药业-0.2mg:2ml)0.4;MG以4ml/h续泵执行。 | 氯化钠注射液（丰原-100ml:0.9%,软袋双阀).48m盐酸右美托咪定注射液(辰欣药业-0. 2mg:2ml)0.4MG以4ml/h续泵执行。 | 氯化钠注射液（丰原-100ml:0.9%,软袋双阀）.48mg盐酸右美托咪定注射液(辰欣药业-0.2mg:2ml)0.4mg以4ml/h续泵执行。 | 0.0270 | 0.0000 |

## strict CER 变差但 semantic slot 不变的例子

| case | 来源 | reviewer组 | gold | original_text | reviewed_text | strict_delta | tolerant_delta |
|---|---|---|---|---|---|---:|---:|
| gold_dev_m_002__block_23 | 原始Qwen文本 | LLM审查-带词表 | 遵医嘱肝素钠调整至6.5ml/h泵入，患者ECMO应用；机器运转正常，转速：3220转/分，流量：3.74L/分；舒芬太尼液泵毕，医嘱予原量以4ml/h泵入；肠内营养液暂停应用，胰岛素余液调整至2ml/h | 遵医嘱肝素钠调整至6.5ml/h泵入，患者ECMO应用，机器运转正常，转速：3220转/分，流量：3.74L/分，舒芬太尼液泵毕，医嘱予原量以4ml/h泵入，肠内营养液暂停应用，胰岛素余液调整至2ml/h | 遵医嘱肝素钠调整至6.5ml/h泵入，患者ECMO应用，机器运转正常，转速：3220r/min，流量：3.74L/min，舒芬太尼液泵毕，医嘱予原量以4ml/h泵入，肠内营养液暂停应用，胰岛素余液调整至2ml/h | 0.0686 | 0.0000 |
| gold_dev_m_002__block_23 | 原始Qwen文本 | 候选+LLM审查 | 遵医嘱肝素钠调整至6.5ml/h泵入，患者ECMO应用；机器运转正常，转速：3220转/分，流量：3.74L/分；舒芬太尼液泵毕，医嘱予原量以4ml/h泵入；肠内营养液暂停应用，胰岛素余液调整至2ml/h | 遵医嘱肝素钠调整至6.5ml/h泵入，患者ECMO应用，机器运转正常，转速：3220转/分，流量：3.74L/分，舒芬太尼液泵毕，医嘱予原量以4ml/h泵入，肠内营养液暂停应用，胰岛素余液调整至2ml/h | 遵医嘱肝素钠调整至6.5ml/h泵入，患者ECMO应用，机器运转正常，转速：3220转/分，流量：3.74L/min，舒芬太尼液泵毕，医嘱予原量以4ml/h泵入，肠内营养液暂停应用，胰岛素余液调整至2ml/h | 0.0294 | 0.0000 |
| gold_smoke_001__block_01 | 原始Qwen文本 | LLM审查-带词表 | CPOT0分 | CPOT0分 | CPOT 0分 | 0.1667 | 0.0000 |
| gold_smoke_001__block_11 | 原始Qwen文本 | LLM审查-无词表 | ECMO转速调整至3660，流速4.28，肝素钠泵毕，医嘱予氯化钠注射液（丰原-100ml：0.9%，软袋双阀）50ML肝素钠注射液（沪第一生化-1.25万ux10支）0.5支以5ml/h泵入执行。 | ECMO转速调整至3660，流速4.28，肝素钠泵毕，医嘱予氯化钠注射液(丰原-100ml:0.9%,软袋双阀)50ML肝素钠注射液（沪第一生化-1.25万uX10支）0.5支以5ml/h泵入执行。 | ECMO转速调整至3660，流速4.28，肝素钠泵毕，医嘱予氯化钠注射液(丰原-100ml:0.9%,软袋双阀)50mL肝素钠注射液（沪第一生化-1.25万U×10支）0.5支以5mL/h泵入执行。 | 0.0303 | 0.0101 |
| gold_smoke_001__block_11 | 原始Qwen文本 | LLM审查-带词表 | ECMO转速调整至3660，流速4.28，肝素钠泵毕，医嘱予氯化钠注射液（丰原-100ml：0.9%，软袋双阀）50ML肝素钠注射液（沪第一生化-1.25万ux10支）0.5支以5ml/h泵入执行。 | ECMO转速调整至3660，流速4.28，肝素钠泵毕，医嘱予氯化钠注射液(丰原-100ml:0.9%,软袋双阀)50ML肝素钠注射液（沪第一生化-1.25万uX10支）0.5支以5ml/h泵入执行。 | ECMO转速调整至3660 r/min，流速4.28 L/min，肝素钠泵毕，医嘱予氯化钠注射液(丰原-100ml:0.9%,软袋双阀)50ml肝素钠注射液（沪第一生化-1.25万U×10支）0.5支以5ml/h泵入执行。 | 0.1515 | 0.1111 |
| gold_smoke_001__block_12 | 原始OCR文本 | LLM审查-无词表 | APTT：44.8，遵医嘱予肝素钠调整至6ml/h泵入，力月西泵毕，医嘱予咪达唑仑注射液（苏恩华-5mg:1ml）50MG氯化钠注射液（丰原-100ml:0.9%，软袋双阀)45M调整至10ml/h泵入执行。 | APTT: 44.8, 遵医嘱予肝素钠调整至6m1/h泵入。力月西泵毕，医嘱予咪达唑仑注射液(苏恩华-5mg\|:1ml)50M配氯化钠注射液(丰原-100ml:0.9%,软袋双阀) 45胍调整至10ml/h泵入执行。 | APTT: 44.8, 遵医嘱予肝素钠调整至6ml/h泵入。力月西泵毕，医嘱予咪达唑仑注射液(苏恩华-5mg:1ml)50mg配氯化钠注射液(丰原-100ml:0.9%,软袋双阀) 45mg调整至10ml/h泵入执行。 | 0.0096 | -0.0192 |
| gold_smoke_001__block_12 | 原始OCR文本 | LLM审查-带词表 | APTT：44.8，遵医嘱予肝素钠调整至6ml/h泵入，力月西泵毕，医嘱予咪达唑仑注射液（苏恩华-5mg:1ml）50MG氯化钠注射液（丰原-100ml:0.9%，软袋双阀)45M调整至10ml/h泵入执行。 | APTT: 44.8, 遵医嘱予肝素钠调整至6m1/h泵入。力月西泵毕，医嘱予咪达唑仑注射液(苏恩华-5mg\|:1ml)50M配氯化钠注射液(丰原-100ml:0.9%,软袋双阀) 45胍调整至10ml/h泵入执行。 | APTT: 44.8, 遵医嘱予肝素钠调整至6ml/h泵入。力月西泵毕，医嘱予咪达唑仑注射液(苏恩华-5mg\|:1ml)50mg配氯化钠注射液(丰原-100ml:0.9%,软袋双阀) 45ml调整至10ml/h泵入执行。 | 0.0192 | -0.0096 |
| gold_smoke_001__block_12 | 原始OCR文本 | 候选+LLM审查 | APTT：44.8，遵医嘱予肝素钠调整至6ml/h泵入，力月西泵毕，医嘱予咪达唑仑注射液（苏恩华-5mg:1ml）50MG氯化钠注射液（丰原-100ml:0.9%，软袋双阀)45M调整至10ml/h泵入执行。 | APTT: 44.8, 遵医嘱予肝素钠调整至6m1/h泵入。力月西泵毕，医嘱予咪达唑仑注射液(苏恩华-5mg\|:1ml)50M配氯化钠注射液(丰原-100ml:0.9%,软袋双阀) 45胍调整至10ml/h泵入执行。 | APTT: 44.8, 遵医嘱予肝素钠调整至6ml/h泵入。力月西泵毕，医嘱予咪达唑仑注射液(苏恩华-5mg\|:1ml)50ml配氯化钠注射液(丰原-100ml:0.9%,软袋双阀) 45mg调整至10ml/h泵入执行。 | 0.0192 | 0.0000 |
| gold_smoke_001__block_12 | 原始Qwen文本 | LLM审查-无词表 | APTT：44.8，遵医嘱予肝素钠调整至6ml/h泵入，力月西泵毕，医嘱予咪达唑仑注射液（苏恩华-5mg:1ml）50MG氯化钠注射液（丰原-100ml:0.9%，软袋双阀)45M调整至10ml/h泵入执行。 | APTT：44.8，遵医嘱予肝素钠调整至6ml/h泵入，力月西泵毕，医嘱予咪达唑仑注射液（苏恩华-5mg：1ml)50MG氯化钠注射液(丰原-100ml:0.9%,软袋双阀)45ML调整至10ml/h泵入执行。 | APTT：44.8，遵医嘱予肝素钠调整至6ml/h泵入，力月西泵毕，医嘱予咪达唑仑注射液（苏恩华-5mg：1ml)50mg氯化钠注射液(丰原-100ml:0.9%,软袋双阀)45ml调整至10ml/h泵入执行。 | 0.0288 | 0.0000 |
| gold_smoke_001__block_12 | 原始Qwen文本 | LLM审查-带词表 | APTT：44.8，遵医嘱予肝素钠调整至6ml/h泵入，力月西泵毕，医嘱予咪达唑仑注射液（苏恩华-5mg:1ml）50MG氯化钠注射液（丰原-100ml:0.9%，软袋双阀)45M调整至10ml/h泵入执行。 | APTT：44.8，遵医嘱予肝素钠调整至6ml/h泵入，力月西泵毕，医嘱予咪达唑仑注射液（苏恩华-5mg：1ml)50MG氯化钠注射液(丰原-100ml:0.9%,软袋双阀)45ML调整至10ml/h泵入执行。 | APTT：44.8，遵医嘱予肝素钠调整至6ml/h泵入，力月西泵毕，医嘱予咪达唑仑注射液（苏恩华-5mg：1ml）50mg氯化钠注射液(丰原-100ml:0.9%,软袋双阀)45ml调整至10ml/h泵入执行。 | 0.0192 | 0.0000 |
| gold_smoke_001__block_12 | 原始Qwen文本 | 候选+LLM审查 | APTT：44.8，遵医嘱予肝素钠调整至6ml/h泵入，力月西泵毕，医嘱予咪达唑仑注射液（苏恩华-5mg:1ml）50MG氯化钠注射液（丰原-100ml:0.9%，软袋双阀)45M调整至10ml/h泵入执行。 | APTT：44.8，遵医嘱予肝素钠调整至6ml/h泵入，力月西泵毕，医嘱予咪达唑仑注射液（苏恩华-5mg：1ml)50MG氯化钠注射液(丰原-100ml:0.9%,软袋双阀)45ML调整至10ml/h泵入执行。 | APTT：44.8，遵医嘱予肝素钠调整至6ml/h泵入，力月西泵毕，医嘱予咪达唑仑注射液（苏恩华-5mg：1ml）50mg氯化钠注射液(丰原-100ml:0.9%,软袋双阀)45ml调整至10ml/h泵入执行。 | 0.0192 | 0.0000 |
| gold_smoke_001__block_14 | 原始OCR文本 | LLM审查-无词表 | 舒芬太尼泵毕，医嘱予枸橼酸舒芬太尼注射液(鄂,宜昌人福-50ug：1ml)200UG氯化钠注射液（丰原,-100ml：0.9%，软袋双阀）50M调整至2ml/h执行。 | 舒芬太尼泵毕，医嘱予枸橡酸舒芬太尼注射液(鄂宜昌人福-50ug:1ml1) 2000G氯化钠注射液（丰原100ml:0.9%,软袋双阀)50M调整至2ml/h执行。 | 舒芬太尼泵毕，医嘱予枸橡酸舒芬太尼注射液(鄂宜昌人福-50μg:1ml) 2000ml氯化钠注射液（丰原100ml:0.9%,软袋双阀)50ml调整至2ml/h执行。 | 0.0482 | 0.0241 |

## strict 和 tolerant 都变差的真实失败例子

| case | 来源 | reviewer组 | gold | original_text | reviewed_text | strict_delta | tolerant_delta |
|---|---|---|---|---|---|---:|---:|
| gold_smoke_001__block_11 | 原始OCR文本 | LLM审查-无词表 | ECMO转速调整至3660，流速4.28，肝素钠泵毕，医嘱予氯化钠注射液（丰原-100ml：0.9%，软袋双阀）50ML肝素钠注射液（沪第一生化-1.25万ux10支）0.5支以5ml/h泵入执行。 | ECMO转速调整至3660，流速4.28,肝素钠泵毕，医「嘱予氯化钠注射液（丰原-100ml:0.9%,软袋双阀）[50ML肝素钠注射液（沪第一生化-1.25万ux10支）0.5支以5ml1/h泵入执行。 | ECMO转速调整至3660，流速4.28 L/min,肝素钠泵毕，医嘱予氯化钠注射液（丰原-100ml:0.9%,软袋双阀）[50ml肝素钠注射液（沪第一生化-1.25万U×10支）0.5支以5ml/h泵入执行。 | 0.0808 | 0.0505 |
| gold_smoke_001__block_11 | 原始OCR文本 | LLM审查-带词表 | ECMO转速调整至3660，流速4.28，肝素钠泵毕，医嘱予氯化钠注射液（丰原-100ml：0.9%，软袋双阀）50ML肝素钠注射液（沪第一生化-1.25万ux10支）0.5支以5ml/h泵入执行。 | ECMO转速调整至3660，流速4.28,肝素钠泵毕，医「嘱予氯化钠注射液（丰原-100ml:0.9%,软袋双阀）[50ML肝素钠注射液（沪第一生化-1.25万ux10支）0.5支以5ml1/h泵入执行。 | ECMO转速调整至3660 r/min，流速4.28 L/min,肝素钠泵毕，医嘱予氯化钠注射液（丰原-100ml:0.9%,软袋双阀）[50ml肝素钠注射液（沪第一生化-1.25万U×10支）0.5支以5ml/h泵入执行。 | 0.1414 | 0.1010 |
| gold_smoke_001__block_11 | 原始Qwen文本 | LLM审查-无词表 | ECMO转速调整至3660，流速4.28，肝素钠泵毕，医嘱予氯化钠注射液（丰原-100ml：0.9%，软袋双阀）50ML肝素钠注射液（沪第一生化-1.25万ux10支）0.5支以5ml/h泵入执行。 | ECMO转速调整至3660，流速4.28，肝素钠泵毕，医嘱予氯化钠注射液(丰原-100ml:0.9%,软袋双阀)50ML肝素钠注射液（沪第一生化-1.25万uX10支）0.5支以5ml/h泵入执行。 | ECMO转速调整至3660，流速4.28，肝素钠泵毕，医嘱予氯化钠注射液(丰原-100ml:0.9%,软袋双阀)50mL肝素钠注射液（沪第一生化-1.25万U×10支）0.5支以5mL/h泵入执行。 | 0.0303 | 0.0101 |
| gold_smoke_001__block_11 | 原始Qwen文本 | LLM审查-带词表 | ECMO转速调整至3660，流速4.28，肝素钠泵毕，医嘱予氯化钠注射液（丰原-100ml：0.9%，软袋双阀）50ML肝素钠注射液（沪第一生化-1.25万ux10支）0.5支以5ml/h泵入执行。 | ECMO转速调整至3660，流速4.28，肝素钠泵毕，医嘱予氯化钠注射液(丰原-100ml:0.9%,软袋双阀)50ML肝素钠注射液（沪第一生化-1.25万uX10支）0.5支以5ml/h泵入执行。 | ECMO转速调整至3660 r/min，流速4.28 L/min，肝素钠泵毕，医嘱予氯化钠注射液(丰原-100ml:0.9%,软袋双阀)50ml肝素钠注射液（沪第一生化-1.25万U×10支）0.5支以5ml/h泵入执行。 | 0.1515 | 0.1111 |
| gold_smoke_001__block_14 | 原始OCR文本 | LLM审查-无词表 | 舒芬太尼泵毕，医嘱予枸橼酸舒芬太尼注射液(鄂,宜昌人福-50ug：1ml)200UG氯化钠注射液（丰原,-100ml：0.9%，软袋双阀）50M调整至2ml/h执行。 | 舒芬太尼泵毕，医嘱予枸橡酸舒芬太尼注射液(鄂宜昌人福-50ug:1ml1) 2000G氯化钠注射液（丰原100ml:0.9%,软袋双阀)50M调整至2ml/h执行。 | 舒芬太尼泵毕，医嘱予枸橡酸舒芬太尼注射液(鄂宜昌人福-50μg:1ml) 2000ml氯化钠注射液（丰原100ml:0.9%,软袋双阀)50ml调整至2ml/h执行。 | 0.0482 | 0.0241 |
| gold_smoke_001__block_14 | 原始OCR文本 | LLM审查-带词表 | 舒芬太尼泵毕，医嘱予枸橼酸舒芬太尼注射液(鄂,宜昌人福-50ug：1ml)200UG氯化钠注射液（丰原,-100ml：0.9%，软袋双阀）50M调整至2ml/h执行。 | 舒芬太尼泵毕，医嘱予枸橡酸舒芬太尼注射液(鄂宜昌人福-50ug:1ml1) 2000G氯化钠注射液（丰原100ml:0.9%,软袋双阀)50M调整至2ml/h执行。 | 舒芬太尼泵毕，医嘱予枸橼酸舒芬太尼注射液(鄂宜昌人福-50μg:1ml) 2000ml氯化钠注射液（丰原100ml:0.9%,软袋双阀)50ml调整至2ml/h执行。 | 0.0361 | 0.0120 |
| gold_smoke_001__block_14 | 原始OCR文本 | 候选+LLM审查 | 舒芬太尼泵毕，医嘱予枸橼酸舒芬太尼注射液(鄂,宜昌人福-50ug：1ml)200UG氯化钠注射液（丰原,-100ml：0.9%，软袋双阀）50M调整至2ml/h执行。 | 舒芬太尼泵毕，医嘱予枸橡酸舒芬太尼注射液(鄂宜昌人福-50ug:1ml1) 2000G氯化钠注射液（丰原100ml:0.9%,软袋双阀)50M调整至2ml/h执行。 | 舒芬太尼泵毕，医嘱予枸橼酸舒芬太尼注射液(鄂宜昌人福-50μg:1ml） 2000ml氯化钠注射液（丰原100ml:0.9%,软袋双阀)50ml调整至2ml/h执行。 | 0.0482 | 0.0120 |

## semantic_inference 例子

| case | 来源 | reviewer组 | from | to | strict_effect | tolerant_effect | semantic_effect | reason |
|---|---|---|---|---|---|---|---|---|
| gold_smoke_001__block_11 | 原始OCR文本 | LLM审查-无词表 | 4.28 | 4.28 L/min | worsen | worsen | same | unit was inferred from context rather than surface-equivalent text |
| gold_smoke_001__block_11 | 原始OCR文本 | LLM审查-带词表 | 3660 | 3660 r/min | worsen | worsen | same | unit was inferred from context rather than surface-equivalent text |
| gold_smoke_001__block_11 | 原始OCR文本 | LLM审查-带词表 | 4.28 | 4.28 L/min | worsen | worsen | same | unit was inferred from context rather than surface-equivalent text |
| gold_smoke_001__block_11 | 原始Qwen文本 | LLM审查-带词表 | 3660 | 3660 r/min | worsen | worsen | same | unit was inferred from context rather than surface-equivalent text |
| gold_smoke_001__block_11 | 原始Qwen文本 | LLM审查-带词表 | 4.28 | 4.28 L/min | worsen | worsen | same | unit was inferred from context rather than surface-equivalent text |

## risky_unit_substitution 例子

| case | 来源 | reviewer组 | from | to | strict_effect | tolerant_effect | semantic_effect | reason |
|---|---|---|---|---|---|---|---|---|
| gold_smoke_001__block_11 | 原始Qwen文本 | 候选+LLM审查 | uX | ug | same | same | same | incomplete or mismatched unit type was converted to a concrete unit |
| gold_smoke_001__block_12 | 原始OCR文本 | LLM审查-无词表 | 5mg\|:1ml | 5mg:1ml | improve | improve | same | incomplete or mismatched unit type was converted to a concrete unit |
| gold_smoke_001__block_12 | 原始OCR文本 | LLM审查-无词表 | 50M | 50mg | worsen | improve | same | incomplete or mismatched unit type was converted to a concrete unit |
| gold_smoke_001__block_12 | 原始OCR文本 | LLM审查-无词表 | 45胍 | 45mg | worsen | worsen | same | incomplete or mismatched unit type was converted to a concrete unit |
| gold_smoke_001__block_12 | 原始OCR文本 | LLM审查-带词表 | 50M | 50mg | worsen | improve | same | incomplete or mismatched unit type was converted to a concrete unit |
| gold_smoke_001__block_12 | 原始OCR文本 | 候选+LLM审查 | 45胍 | 45mg | worsen | worsen | same | incomplete or mismatched unit type was converted to a concrete unit |
| gold_smoke_001__block_14 | 原始OCR文本 | LLM审查-无词表 | 50M | 50ml | worsen | worsen | same | incomplete or mismatched unit type was converted to a concrete unit |
| gold_smoke_001__block_14 | 原始OCR文本 | LLM审查-带词表 | 50M | 50ml | worsen | worsen | same | incomplete or mismatched unit type was converted to a concrete unit |
| gold_smoke_001__block_14 | 原始OCR文本 | 候选+LLM审查 | 50M | 50ml | worsen | worsen | same | incomplete or mismatched unit type was converted to a concrete unit |
| gold_smoke_001__block_16 | 原始OCR文本 | LLM审查-无词表 | 48m | 48mg | same | same | same | incomplete or mismatched unit type was converted to a concrete unit |
| gold_smoke_001__block_16 | 原始OCR文本 | LLM审查-带词表 | 48m | 48mg | same | same | same | incomplete or mismatched unit type was converted to a concrete unit |

## 结论

- strict transcription 仍然必须保留，因为 reviewer 会做单位和书写规范化，严格逐字任务下这些会被判错。
- format-tolerant metric 可以把 `转/分/r/min`、`L/分/L/min`、`CPOT0分/CPOT 0分`、`ML/mL/ml`、`UG/μg/ug` 归为表面等价。
- 但 `3660 -> 3660 r/min`、`4.28 -> 4.28 L/min` 属于 semantic_inference，不是表面等价。
- `50M -> 50ml`、`45M -> 45mg`、`MG/ML` 类型互换属于 risky_unit_substitution，必须禁止自动覆盖。
- reviewer 若进入系统，只适合先作为 QC suggestion / semantic normalization 辅助，不适合作为 raw transcription 覆盖来源。
