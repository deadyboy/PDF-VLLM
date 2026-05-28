# Observation Verbatim Sidecar Report

## Summary

| metric | main | old_col | verbatim |
|---|---:|---:|---:|
| correct | 45 | 47 | 27 |
| canonical_only | 1 | 1 | 1 |
| punctuation_only | 5 | 4 | 1 |
| rewrite_or_paraphrase | 5 | 5 | 11 |
| missing | 1 | 0 | 0 |
| overfill | 0 | 0 | 17 |

## Comparisons

| metric | count |
|---|---:|
| total | 57 |
| main_wrong_verbatim_correct | 1 |
| main_correct_verbatim_wrong | 23 |
| old_col_wrong_verbatim_correct | 0 |
| old_col_correct_verbatim_wrong | 23 |
| verbatim_needs_review | 0 |

## Details

| page | block_id | gold | main_value | old_col_value | verbatim_value | main_eval_kind | old_col_eval_kind | verbatim_eval_kind |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| gold_smoke_001 | block_00 | 患者出入量总计已汇报医生，医嘱继观。患者尿液浑浊，汇报值班医生，医嘱观察。鼻鼻胃管固定在位，引流通畅，量约0ml。 | 患者出入量总计已汇报医生，医嘱继观。患者尿液浑浊，汇报值班医生，医嘱观察。鼻鼻胃管固定在位，引流通畅，量约0ml。 | 患者出入量总计已汇报医生，医嘱继观。患者尿液浑浊，汇报值班医生，医嘱观察。鼻鼻胃管固定在位，引流通畅，量约0ml。 | 患者出入量总计已汇报医生，医嘱继观。患者尿液浑浊，汇报值班医生，医嘱观察。鼻鼻胃管固定在位，引流通畅，量约0ml。 | equal | equal | equal |
| gold_smoke_001 | block_01 | CPOT0分 | null | CPOT0分 | 病情观察及处理CPOT0分 | missing | equal | substantive_mismatch |
| gold_smoke_001 | block_02 | 咪达唑仑组液续用12ml/h泵入。 | 咪达唑仑组液续用12ml/h泵入。 | 咪达唑仑组液续用12ml/h泵入。 | 咪达唑仑组液续用12ml/h泵入。 | equal | equal | equal |
| gold_smoke_001 | block_03 | 遵医嘱用药。 | 遵医嘱用药。 | 遵医嘱用药。 | 遵医嘱用药。 | equal | equal | equal |
| gold_smoke_001 | block_04 | 患者ECMO持续应用，机器运转正常，转速：3900转/分，流速：4.56L/分，氧浓度：100%，空氧混合器流速：4L/分，肝素余液以4ml/h泵入，力月西余液以12ml/h泵入，去甲肾上腺素组液以1ml/h泵入，患者右侧颈部颈内深静脉导管置入深度15cm，管道通畅。标识明确，固定良好，继续使用。RASS-4分 | 患者ECMO持续应用，机器运转正常，转速：3900转/分，流速：4.56L/分，氧浓度：100%，空氧混合器流速：4L/分，肝素余液以4ml/h泵入，力月西余液以12ml/h泵入，去甲肾上腺素组液以1ml/h泵入，患者右侧颈部颈内深静脉导管置入深度15cm，管道通畅。标识明确，固定良好，继续使用。RASS-4分 | 患者ECMO持续应用，机器运转正常，转速：3900转/分，流速：4.56L/分，氧浓度：100%，空氧混合器流速：4L/分，肝素余液以4ml/h泵入，力月西余液以12ml/h泵入，去甲肾上腺素组液以1ml/h泵入，患者右侧颈部颈内深静脉导管置入深度15cm，管道通畅。标识明确，固定良好，继续使用。RASS-4分 | 病情观察及处理患者ECMO持续应用，机器运转正常，转速：3900转/分，流速：4.56L/分，氧浓度：100%，空氧混合器流速：4L/分，肝素余液以4ml/h泵入，力月西余液以12ml/h泵入，去甲肾上腺素组液以1ml/h泵入，患者右侧颈部颈内深静脉导管置入深度15cm，管道通畅。标识明确，固定良好，继续使用。RASS-4分 | equal | equal | substantive_mismatch |
| gold_smoke_001 | block_05 | null | null | null | 病情观察及处理 | equal | equal | overfill |
| gold_smoke_001 | block_06 | 肝素钠医嘱予调整至5ml/h泵入 | 肝素钠医嘱予调整至5ml/h泵入 | 肝素钠医嘱予调整至5ml/h泵入 | 肝素钠医嘱予调整至5ml/h泵入 | equal | equal | equal |
| gold_smoke_001 | block_07 | 医嘱予床边行纤维支气管镜检查，予床边配合；继续观察 | 医嘱予床边行纤维支气管镜检查，予床边配合，继续观察 | 医嘱予床边行纤维支气管镜检查，予床边配合，继续观察 | 病情观察及处理医嘱予床边行纤维支气管镜检查，予床边配合，继续观察 | substantive_mismatch | substantive_mismatch | substantive_mismatch |
| gold_smoke_001 | block_08 | null | null | null | 病情观察及处理 | equal | equal | overfill |
| gold_smoke_001 | block_09 | null | null | null | null | equal | equal | equal |
| gold_smoke_001 | block_10 | null | null | null | null | equal | equal | equal |
| gold_smoke_001 | block_11 | ECMO转速调整至3660，流速4.28，肝素钠泵毕，医嘱予氯化钠注射液（丰原-100ml：0.9%，软袋双阀）50ML肝素钠注射液（沪第一生化-1.25万ux10支）0.5支以5ml/h泵入执行。 | ECMO转速调整至3660，流速4.28，肝素钠泵毕，医嘱予氯化钠注射液(丰原-100ml:0.9%，软袋双阀)50ML肝素钠注射液(沪第一生化-1.25万uX10支)0.5支以5ml/h泵入执行。 | ECMO转速调整至3660，流速4.28，肝素钠泵毕，医嘱予氯化钠注射液（丰原-100ml:0.9%，软袋双阀）50ML肝素钠注射液（沪第一生化-1.25万u×10支）0.5支以5ml/h泵入执行。 | ECMO转速调整至3660，流速4.28,肝素钠泵毕，医嘱予氯化钠注射液(丰原-100ml:0.9%,软袋双阀)50ML肝素钠注射液(沪第一生化-1.25万u×10支)0.5支以5ml/h泵入执行。 | substantive_mismatch | substantive_mismatch | substantive_mismatch |
| gold_smoke_001 | block_12 | APTT：44.8，遵医嘱予肝素钠调整至6ml/h泵入，力月西泵毕，医嘱予咪达唑仑注射液（苏恩华-5mg:1ml）50MG氯化钠注射液（丰原-100ml:0.9%，软袋双阀)45M调整至10ml/h泵入执行。 | APTT：44.8，遵医嘱予肝素钠调整至6ml/h泵入，力月西泵毕，医嘱予咪达唑仑注射液(苏恩华-5mg:1ml)50MG氯化钠注射液(丰原-100ml:0.9%,软袋双阀)45ML调整至10ml/h泵入执行。 | APTT：44.8，遵医嘱予肝素钠调整至6ml/h泵入，力月西泵毕，医嘱予咪达唑仑注射液(苏思华-5mg:1ml)50MG氯化钠注射液(丰原-100ml:0.9%,软袋双阀)45ML调整至10ml/h泵入执行。 | APTT：44.8，遵医嘱予肝素钠调整至6ml/h泵入，力月西泵毕，医嘱予咪达唑仑注射液(苏思华-5mg:1ml)50MG氯化钠注射液(丰原-100ml:0.9%,软袋双阀)45ML调整至10ml/h泵入执行。 | substantive_mismatch | substantive_mismatch | substantive_mismatch |
| gold_smoke_001 | block_13 | RASS-4分，CPOT0分 | RASS-4分，CPOT0分 | RASS-4分，CPOT0分 | RASS-4分, CPOT0分 | equal | equal | canonical_equal |
| gold_smoke_001 | block_14 | 舒芬太尼泵毕，医嘱予枸橼酸舒芬太尼注射液(鄂,宜昌人福-50ug：1ml)200UG氯化钠注射液（丰原,-100ml：0.9%，软袋双阀）50M调整至2ml/h执行。 | 舒芬太尼泵毕，医嘱予枸橼酸舒芬太尼注射液(鄂宜昌人福-50ug:1ml)200UG氯化钠注射液(丰原-100ml:0.9%,软袋双阀)50ML调整至2ml/h执行。 | 舒芬太尼泵毕，医嘱予枸橼酸舒芬太尼注射液(鄂宜昌人福-50ug:1ml)2000G氯化钠注射液(丰原-100ml:0.9%,软袋双阀)50ML调整至2ml/h执行。 | 舒芬太尼泵毕，医嘱予枸橼酸舒芬太尼注射液(鄂宜昌人福-50ug:1ml)2000G氯化钠注射液(丰原-100ml:0.9%,软袋双阀)50ML调整至2ml/h执行。 | substantive_mismatch | substantive_mismatch | substantive_mismatch |
| gold_smoke_001 | block_15 | APTT:63.3，遵医嘱予APTT调整至5ml/h泵入，继续观察 | APTT:63.3，遵医嘱予APTT调整至5ml/h泵入，继续观察 | APTT:63.3，遵医嘱予APTT调整至5ml/h泵入，继续观察 | APTT:63.3，遵医嘱予APTT调整至5ml/h泵入，继续观察 | equal | equal | equal |
| gold_smoke_001 | block_16 | 氯化钠注射液(丰原-100ml:0.9%,软袋双阀)48ML;盐酸右美托咪定注射液(辰欣药业-0.2mg:2ml)0.4;MG以4ml/h续泵执行。 | 氯化钠注射液(丰原-100ml:0.9%,软袋双阀)48ML；盐酸右美托咪定注射液(辰欣药业-0.2mg:2ml)0.4MG以4ml/h续泵执行。 | 氯化钠注射液(丰原-100ml:0.9%,软袋双阀)48ML盐酸右美托咪定注射液(辰欣药业-0.2mg:2ml)0.4MG以4ml/h续泵执行。 | 病情观察及处理氯化钠注射液(丰原-100ml:0.9%,软袋双阀)48ML盐酸右美托咪定注射液(辰欣药业-0.2mg:2ml)0.4MG以4ml/h续泵执行。 | separator_error | separator_error | substantive_mismatch |
| gold_smoke_001 | block_17 | null | null | null | 病情观察及处理 | equal | equal | overfill |
| gold_dev_m_002 | block_00 | 纤支镜检查结束，予标本送检。予肠内营养液80ml/h胃管泵入。肝素钠7ml/h续泵。 | 纤支镜检查结束，予标本送检。予肠内营养液80m；1/h胃管泵入。肝素钠7ml/h续泵。 | 纤支镜检查结束，予标本送检。予肠内营养液80ml/h胃管泵入。肝素钠7ml/h续泵。 | 纤支镜检查结束，予标本送检。予肠内营养液80ml/h胃管泵入。肝素钠7ml/h续泵。 | substantive_mismatch | equal | equal |
| gold_dev_m_002 | block_01 | 咪达唑仑12ml/h续泵。 | 咪达唑仑12ml/h续泵。 | 咪达唑仑12ml/h续泵。 | 咪达唑仑12ml/h续泵。 | equal | equal | equal |
| gold_dev_m_002 | block_02 | null | null | null | 病情观察及处理 | equal | equal | overfill |
| gold_dev_m_002 | block_03 | 出入量汇报值班医生，嘱予密观。 | 出入量汇报值班医生，嘱予密观。 | 出入量汇报值班医生，嘱予密观。 | 出入量汇报值班医生，嘱予密观。 | equal | equal | equal |
| gold_dev_m_002 | block_04 | 舒芬太尼4ml/h续泵。 | 舒芬太尼4ml/h续泵。 | 舒芬太尼4ml/h续泵。 | 舒芬太尼4ml/h续泵。 | equal | equal | equal |
| gold_dev_m_002 | block_05 | 患者持续床边VVECMO治疗中，转速：3220转/分，流速：3.67L/分，空氧混合器流速4升/分，氧浓度100%，机器运转正常，管路妥善固定中，外露刻度无变化，敷料清洁干燥。胰岛素组液以2ml/h泵入，力月西组液以12ml/h泵入，舒芬太尼组液以4ml/h泵入，肝素组液以7ml/h泵入中，右美组液以2ml/h泵入中，生命体征汇报值班医生，嘱予密观。Braden10分，RASS-4分，CPOT0分 | 患者持续床边VVECMO治疗中，转速：3220转/分，流速：3.67L/分，空氧混合器流速4升/分，氧浓度100%，机器运转正常，管路妥善固定中，外露刻度无变化，敷料清洁干燥。胰岛素组液以2ml/h泵入，力月西组液以12ml/h泵入，舒芬太尼组液以4ml/h泵入，肝素组液以7ml/h泵入中，右美组液以2ml/h泵入中，生命体征汇报值班医生，嘱予密观。Braden10分，RASS-4分，CPOT0分 | 患者持续床边VVECMO治疗中，转速：3220转/分，流速：3.67L/分，空氧混合器流速4升/分，氧浓度100%，机器运转正常，管路妥善固定中，外露刻度无变化，敷料清洁干燥。胰岛素组液以2ml/h泵入，力月西组液以12ml/h泵入，舒芬太尼组液以4ml/h泵入，肝素组液以7ml/h泵入中，右美组液以2ml/h泵入中，生命体征汇报值班医生，嘱予密观。Braden10分，RASS-4分，CPOT0分 | 病情观察及处理患者持续床边VVECMO治疗中，转速：3220转/分，流速：3.67L/分，空氧混合器流速4升/分，氧浓度100%，机器运转正常，管路妥善固定中，外露刻度无变化，敷料清洁干燥。胰岛素组液以2ml/h泵入，力月西组液以12ml/h泵入，舒芬太尼组液以4ml/h泵入，肝素组液以7ml/h泵入中，右美组液以2ml/h泵入中，生命体征汇报值班医生，嘱予密观。Braden10分，RASS-4分，CPOT0分 | equal | equal | substantive_mismatch |
| gold_dev_m_002 | block_06 | null | null | null | null | equal | equal | equal |
| gold_dev_m_002 | block_07 | null | null | null | 病情观察及处理 | equal | equal | overfill |
| gold_dev_m_002 | block_08 | null | null | null | null | equal | equal | equal |
| gold_dev_m_002 | block_09 | 医生予床边查视后更改呼吸机参数。 | 医生予床边查视后更改呼吸机参数。 | 医生予床边查视后更改呼吸机参数。 | 病情观察及处理医生予床边查视后更改呼吸机参数。 | equal | equal | substantive_mismatch |
| gold_dev_m_002 | block_10 | APTT:43.6s;遵医嘱予肝素组液以7.5ml/h泵入。 | APTT:43.6s,遵医嘱予肝素组液以7.5ml/h泵入。 | APTT:43.6s,遵医嘱予肝素组液以7.5ml/h泵入。 | 病情观察及处理APTT:43.6s,遵医嘱予肝素组液以7.5ml/h泵入。 | substantive_mismatch | substantive_mismatch | substantive_mismatch |
| gold_dev_m_002 | block_11 | 血糖值汇报值班医生，遵医嘱予调RI组液以3ml/h泵入。 | 血糖值汇报值班医生，遵医嘱予调RI组液以3ml/h泵入。 | 血糖值汇报值班医生，遵医嘱予调RI组液以3ml/h泵入。 | 血糖值汇报值班医生，遵医嘱予调RI组液以3ml/h泵入。 | equal | equal | equal |
| gold_dev_m_002 | block_12 | null | null | null | null | equal | equal | equal |
| gold_dev_m_002 | block_13 | null | null | null | null | equal | equal | equal |
| gold_dev_m_002 | block_14 | null | null | null | null | equal | equal | equal |
| gold_dev_m_002 | block_15 | null | null | null | null | equal | equal | equal |
| gold_dev_m_002 | block_16 | APTT:64.4s，遵医嘱予肝素组液以7ml/h泵入。 | APTT:64.4s,遵医嘱予肝素组液以7ml/h泵入。 | APTT:64.4s,遵医嘱予肝素组液以7ml/h泵入。 | 病情观察及处理APTT:64.4s,遵医嘱予肝素组液以7ml/h泵入。 | canonical_equal | canonical_equal | substantive_mismatch |
| gold_dev_m_002 | block_17 | null | null | null | null | equal | equal | equal |
| gold_dev_m_002 | block_18 | null | null | null | null | equal | equal | equal |
| gold_dev_m_002 | block_19 | null | null | null | null | equal | equal | equal |
| gold_dev_m_002 | block_20 | 患者出入量总计已汇报医生，医嘱继观。血糖值汇报值班医生，遵医嘱予调RI组液以4ml/h泵入。CPOT0分 | 患者出入量总计已汇报医生，医嘱继观。血糖值汇报值班医生，遵医嘱予调RI组液以4ml/h泵入。CPOT0分 | 患者出入量总计已汇报医生，医嘱继观。血糖值汇报值班医生，遵医嘱予调RI组液以4ml/h泵入。CPOT0分 | 患者出入量总计已汇报医生，医嘱维观。血糖值汇报值班医生，遵医嘱予调RI组液以4ml/h泵入。CFO10分 | equal | equal | substantive_mismatch |
| gold_dev_m_002 | block_21 | null | null | null | null | equal | equal | equal |
| gold_dev_m_002 | block_22 | null | null | null | 病情观察及处理 | equal | equal | overfill |
| gold_dev_m_002 | block_23 | 遵医嘱肝素钠调整至6.5ml/h泵入，患者ECMO应用；机器运转正常，转速：3220转/分，流量：3.74L/分；舒芬太尼液泵毕，医嘱予原量以4ml/h泵入；肠内营养液暂停应用，胰岛素余液调整至2ml/h | 遵医嘱肝素钠调整至6.5ml/h泵入，患者ECMO应用，机器运转正常，转速：3220转/分，流量：3.74L/分，舒芬太尼液泵毕，医嘱予原量以4ml/h泵入，肠内营养液暂停应用，胰岛素余液调整至2ml/h | 遵医嘱肝素钠调整至6.5ml/h泵入，患者ECMO应用，机器运转正常，转速：3220转/分，流量：3.74L/分，舒芬太尼液泵毕，医嘱予原量以4ml/h泵入，肠内营养液暂停应用，胰岛素余液调整至2ml/h | 遵医嘱肝素钠调整至6.5ml/h泵入，患者ECMO应用，机器运转正常，转速：3220转/分，流量：3.74L/分，舒芬太尼液泵毕，医嘱予原量以4ml/h泵入，肠内营养液暂停应用，胰岛素余液调整至2ml/h | substantive_mismatch | substantive_mismatch | substantive_mismatch |
| gold_validation_003 | block_00 | null | null | null | null | equal | equal | equal |
| gold_validation_003 | block_01 | 血糖值汇报值班医生，遵医嘱予暂停胰岛素应用;。CPOT0分 | 血糖值汇报值班医生，遵医嘱予暂停胰岛素应用；CPOT0分 | 血糖值汇报值班医生，遵医嘱予暂停胰岛素应用·CPOT0分 | 病情观察及处理血糖值汇报值班医生，遵医嘱予暂停胰岛素应用• CP0T0分 | substantive_mismatch | substantive_mismatch | substantive_mismatch |
| gold_validation_003 | block_02 | 患者出入量总计已汇报医生，医嘱继观。 | 患者出入量总计已汇报医生，医嘱继观。 | 患者出入量总计已汇报医生，医嘱继观。 | 病情观察及处理患者出入量总计已汇报医生，医嘱继观。 | equal | equal | substantive_mismatch |
| gold_validation_003 | block_03 | 患者现气管插管接呼吸机辅助通气中，床边予右颈内静脉+右股静脉处行VV-ECMO联合CVVHDF治疗中，ECMO转速：3000r/min，血流量：3.45L/min，空氧混合器流速4L/min，氧浓度100%，水箱：37.0℃；CRRT血流速150ml/min，后置换液1000ml/h，透析液1000ml/h，脱水量100ml/h，泵前泵（枸橼酸钠）230ml/h，5%碳酸氢钠调至45ml/h，5%氯化钙5ml/h，各机器均运转正常。ECMO有凝血倾向，值班医生已知。患者四肢末梢皮肤温暖。左颈内CVC在位通畅：予妥善固定。持续胃肠减压中，可见少量黄褐色液体引出。现去甲肾上腺素组液以11ml/h泵入，瑞芬太尼组液以6ml/h泵入，咪达唑仑组液以10ml/h泵入，艾司洛尔组液以6ml/h泵入，新活素2.1ml/h泵入，患者左手食指指端发黑，值班医生已知，予保暖。在医护协同下辅助患者行俯卧位通气治疗，生命体征汇报值班医生，医嘱继观。遵医嘱予碘伏擦浴一次。遵医嘱暂停肠内营养泵入。Braden10分，RASS-4分 | 患者现气管插管接呼吸机辅助通气中，床边予右颈内静脉+右股静脉处行VV-ECMO联合CVVHDF治疗中，ECMO转速：3000r/min，血流量：3.45L/min，空氧混合器流速4L/min，氧浓度100%，水箱：37.0℃；CRRT血流速150ml/min，后置换液1000ml/h，透析液1000ml/h，脱水量100ml/h，泵前泵（枸橼酸钠）230ml/h，5%碳酸氢钠调至45ml/h，5%氯化钙5ml/h，各机器均运转正常。ECMO有凝血倾向，值班医生已知。患者四肢末梢皮肤温暖。左颈内CVC在位通畅，予妥善固定。持续胃肠减压中，可见少量黄褐色液体引出。现去甲肾上腺素组液以11ml/h泵入，瑞芬太尼组液以6ml/h泵入，咪达唑仑组液以10ml/h泵入，艾司洛尔组液以6ml/h泵入，新活素2.1ml/h泵入，患者左手食指指端发黑，值班医生已知，予保暖。在医护协同下辅助患者行俯卧位通气治疗，生命体征汇报值班医生，医嘱继观。遵医嘱予碘优擦浴一次。遵医嘱暂停肠内营养泵入。Braden10分，RASS-4分 | 患者现气管插管接呼吸机辅助通气中，床边予右颈内静脉+右股静脉处行VV-ECMO联合CVVHDF治疗中，ECMO转速：3000r/min，血流量：3.45L/min，空氧混合器流速4L/min，氧浓度100%，水箱：37.0℃；CRRT血流速150ml/min，后置换液1000ml/h，透析液1000ml/h，脱水量100ml/h，泵前泵（枸橼酸钠）230ml/h，5%碳酸氢钠调至45ml/h，5%氯化钙5ml/h，各机器均运转正常。ECMO有凝血倾向，值班医生已知。患者四肢末梢皮肤温暖。左颈内CVC在位通畅，予妥善固定。持续胃肠减压中，可见少量黄褐色液体引出。现去甲肾上腺素组液以11ml/h泵入，瑞芬太尼组液以6ml/h泵入，咪达唑仑组液以10ml/h泵入，艾司洛尔组液以6ml/h泵入，新活素2.1ml/h泵入，患者左手食指指端发黑，值班医生已知，予保暖。在医护协同下辅助患者行俯卧位通气治疗，生命体征汇报值班医生，医嘱难观。遵医嘱予碘伏擦浴一次。遵医嘱暂停肠内营养泵入。Braden10分，RASS-4分 | 病情观察及处理患者现气管插管接呼吸机辅助通气中，床边予右颈内静脉+右股静脉处行VV-ECMO联合CVVHDF治疗中，ECMO转速：3000r/min，血流量：3.45L/min，空氧混合器流速4L/min，氧浓度100%，水箱：37.0℃；CRRT血流速150ml/min，后置换液1000ml/h，透析液1000ml/h，脱水量100ml/h，泵前泵（枸橼酸钠）230ml/h，5%碳酸氢钠调至45ml/h，5%氯化钙5ml/h，各机器均运转正常。ECMO有凝血倾向，值班医生已知。患者四肢末梢皮肤温暖。左颈内CVC在位通畅，予妥善固定。持续胃肠减压中，可见少量黄褐色液体引出。现去甲肾上腺素组液以11ml/h泵入，瑞芬太尼组液以6ml/h泵入，咪达唑仑组液以10ml/h泵入，艾司洛尔组液以6ml/h泵入，新活素2.1ml/h泵入，患者左手食指指端发黑，值班医生已知，予保暖。在医护协同下辅助患者行俯卧位通气治疗，生命体征汇报值班医生，医嘱难观。遵医嘱予碘伏擦浴一次。遵医嘱暂停肠内营养泵入。Braden10分，RASS-4分 | substantive_mismatch | substantive_mismatch | substantive_mismatch |
| gold_validation_003 | block_04 | 力月西组液泵毕，遵医嘱续用10ml/h。 | 力月西组液泵毕，遵医嘱续用10ml/h。 | 力月西组液泵毕，遵医嘱续用10ml/h。 | 病情观察及处理力月西组液泵毕，遵医嘱续用10ml/h。 | equal | equal | substantive_mismatch |
| gold_validation_003 | block_05 | 瑞芬太尼组液泵毕，遵医嘱续用6ml/h。 | 瑞芬太尼组液泵毕，遵医嘱续用6ml/h。 | 瑞芬太尼组液泵毕，遵医嘱续用6ml/h。 | 瑞芬太尼组液泵毕，遵医嘱续用6ml/h。 | equal | equal | equal |
| gold_validation_003 | block_06 | null | null | null | null | equal | equal | equal |
| gold_validation_003 | block_07 | null | null | null | 病情观察及处理 | equal | equal | overfill |
| gold_validation_003 | block_08 | 去甲肾上腺素组液泵毕，遵医嘱续用15ml/h。 | 去甲肾上腺素组液泵毕，遵医嘱续用15ml/h。 | 去甲肾上腺素组液泵毕，遵医嘱续用15ml/h。 | 病情观察及处理去甲肾上腺素组液泵毕，遵医嘱续用15ml/h。 | equal | equal | substantive_mismatch |
| gold_validation_003 | block_09 | null | null | null | 病情观察及处理 | equal | equal | overfill |
| gold_validation_003 | block_10 | null | null | null | 病情观察及处理 | equal | equal | overfill |
| gold_validation_003 | block_11 | null | null | null | 病情观察及处理 | equal | equal | overfill |
| gold_validation_003 | block_12 | null | null | null | null | equal | equal | equal |
| gold_validation_003 | block_13 | 遵医嘱予西地兰组液静推1h。 | 遵医嘱予西地兰组液静推1h。 | 遵医嘱予西地兰组液静推1h。 | 遵医嘱予西地兰组液静推1h。 | equal | equal | equal |
| gold_validation_003 | block_14 | 遵医嘱予阿曲库铵组液5ml/h泵入。 | 遵医嘱予阿曲库铵组液5ml/h泵入。 | 遵医嘱予阿曲库铵组液5ml/h泵入。 | 病情观察及处理遵医嘱予阿曲库铵组液5ml/h泵入。 | equal | equal | substantive_mismatch |
