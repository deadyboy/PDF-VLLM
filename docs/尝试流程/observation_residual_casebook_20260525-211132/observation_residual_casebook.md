# Observation Residual Casebook

## Error Type Summary

| error_type | count |
|---|---:|
| exact_equal | 0 |
| canonical_only | 1 |
| missing_sentence | 0 |
| extra_text | 0 |
| rewrite_or_paraphrase | 4 |
| char_level_mismatch | 0 |
| punctuation_only | 5 |
| linebreak_join_error | 0 |
| gold_needs_check | 0 |
| main_better_than_col | 0 |
| col_better_than_main | 2 |
| both_wrong | 0 |

## Cases

| page | block_id | gold | main_value | col_value | main_eval_kind | col_eval_kind | suggested_error_type |
| --- | --- | --- | --- | --- | --- | --- | --- |
| gold_smoke_001 | block_01 | CPOT0分 | null | CPOT0分 | missing | equal | col_better_than_main |
| gold_smoke_001 | block_07 | 医嘱予床边行纤维支气管镜检查，予床边配合；继续观察 | 医嘱予床边行纤维支气管镜检查，予床边配合，继续观察 | 医嘱予床边行纤维支气管镜检查，予床边配合，继续观察 | substantive_mismatch | substantive_mismatch | punctuation_only |
| gold_smoke_001 | block_11 | ECMO转速调整至3660，流速4.28，肝素钠泵毕，医嘱予氯化钠注射液（丰原-100ml：0.9%，软袋双阀）50ML肝素钠注射液（沪第一生化-1.25万ux10支）0.5支以5ml/h泵入执行。 | ECMO转速调整至3660，流速4.28，肝素钠泵毕，医嘱予氯化钠注射液(丰原-100ml:0.9%，软袋双阀)50ML肝素钠注射液(沪第一生化-1.25万uX10支)0.5支以5ml/h泵入执行。 | ECMO转速调整至3660，流速4.28，肝素钠泵毕，医嘱予氯化钠注射液（丰原-100ml:0.9%，软袋双阀）50ML肝素钠注射液（沪第一生化-1.25万u×10支）0.5支以5ml/h泵入执行。 | substantive_mismatch | substantive_mismatch | rewrite_or_paraphrase |
| gold_smoke_001 | block_12 | APTT：44.8，遵医嘱予肝素钠调整至6ml/h泵入，力月西泵毕，医嘱予咪达唑仑注射液（苏恩华-5mg:1ml）50MG氯化钠注射液（丰原-100ml:0.9%，软袋双阀)45M调整至10ml/h泵入执行。 | APTT：44.8，遵医嘱予肝素钠调整至6ml/h泵入，力月西泵毕，医嘱予咪达唑仑注射液(苏恩华-5mg:1ml)50MG氯化钠注射液(丰原-100ml:0.9%,软袋双阀)45ML调整至10ml/h泵入执行。 | APTT：44.8，遵医嘱予肝素钠调整至6ml/h泵入，力月西泵毕，医嘱予咪达唑仑注射液(苏思华-5mg:1ml)50MG氯化钠注射液(丰原-100ml:0.9%,软袋双阀)45ML调整至10ml/h泵入执行。 | substantive_mismatch | substantive_mismatch | rewrite_or_paraphrase |
| gold_smoke_001 | block_14 | 舒芬太尼泵毕，医嘱予枸橼酸舒芬太尼注射液(鄂,宜昌人福-50ug：1ml)200UG氯化钠注射液（丰原,-100ml：0.9%，软袋双阀）50M调整至2ml/h执行。 | 舒芬太尼泵毕，医嘱予枸橼酸舒芬太尼注射液(鄂宜昌人福-50ug:1ml)200UG氯化钠注射液(丰原-100ml:0.9%,软袋双阀)50ML调整至2ml/h执行。 | 舒芬太尼泵毕，医嘱予枸橼酸舒芬太尼注射液(鄂宜昌人福-50ug:1ml)2000G氯化钠注射液(丰原-100ml:0.9%,软袋双阀)50ML调整至2ml/h执行。 | substantive_mismatch | substantive_mismatch | rewrite_or_paraphrase |
| gold_smoke_001 | block_16 | 氯化钠注射液(丰原-100ml:0.9%,软袋双阀)48ML;盐酸右美托咪定注射液(辰欣药业-0.2mg:2ml)0.4;MG以4ml/h续泵执行。 | 氯化钠注射液(丰原-100ml:0.9%,软袋双阀)48ML；盐酸右美托咪定注射液(辰欣药业-0.2mg:2ml)0.4MG以4ml/h续泵执行。 | 氯化钠注射液(丰原-100ml:0.9%,软袋双阀)48ML盐酸右美托咪定注射液(辰欣药业-0.2mg:2ml)0.4MG以4ml/h续泵执行。 | separator_error | separator_error | punctuation_only |
| gold_dev_m_002 | block_00 | 纤支镜检查结束，予标本送检。予肠内营养液80ml/h胃管泵入。肝素钠7ml/h续泵。 | 纤支镜检查结束，予标本送检。予肠内营养液80m；1/h胃管泵入。肝素钠7ml/h续泵。 | 纤支镜检查结束，予标本送检。予肠内营养液80ml/h胃管泵入。肝素钠7ml/h续泵。 | substantive_mismatch | equal | col_better_than_main |
| gold_dev_m_002 | block_10 | APTT:43.6s;遵医嘱予肝素组液以7.5ml/h泵入。 | APTT:43.6s,遵医嘱予肝素组液以7.5ml/h泵入。 | APTT:43.6s,遵医嘱予肝素组液以7.5ml/h泵入。 | substantive_mismatch | substantive_mismatch | punctuation_only |
| gold_dev_m_002 | block_16 | APTT:64.4s，遵医嘱予肝素组液以7ml/h泵入。 | APTT:64.4s,遵医嘱予肝素组液以7ml/h泵入。 | APTT:64.4s,遵医嘱予肝素组液以7ml/h泵入。 | canonical_equal | canonical_equal | canonical_only |
| gold_dev_m_002 | block_23 | 遵医嘱肝素钠调整至6.5ml/h泵入，患者ECMO应用；机器运转正常，转速：3220转/分，流量：3.74L/分；舒芬太尼液泵毕，医嘱予原量以4ml/h泵入；肠内营养液暂停应用，胰岛素余液调整至2ml/h | 遵医嘱肝素钠调整至6.5ml/h泵入，患者ECMO应用，机器运转正常，转速：3220转/分，流量：3.74L/分，舒芬太尼液泵毕，医嘱予原量以4ml/h泵入，肠内营养液暂停应用，胰岛素余液调整至2ml/h | 遵医嘱肝素钠调整至6.5ml/h泵入，患者ECMO应用，机器运转正常，转速：3220转/分，流量：3.74L/分，舒芬太尼液泵毕，医嘱予原量以4ml/h泵入，肠内营养液暂停应用，胰岛素余液调整至2ml/h | substantive_mismatch | substantive_mismatch | punctuation_only |
| gold_validation_003 | block_01 | 血糖值汇报值班医生，遵医嘱予暂停胰岛素应用;。CPOT0分 | 血糖值汇报值班医生，遵医嘱予暂停胰岛素应用；CPOT0分 | 血糖值汇报值班医生，遵医嘱予暂停胰岛素应用·CPOT0分 | substantive_mismatch | substantive_mismatch | punctuation_only |
| gold_validation_003 | block_03 | 患者现气管插管接呼吸机辅助通气中，床边予右颈内静脉+右股静脉处行VV-ECMO联合CVVHDF治疗中，ECMO转速：3000r/min，血流量：3.45L/min，空氧混合器流速4L/min，氧浓度100%，水箱：37.0℃；CRRT血流速150ml/min，后置换液1000ml/h，透析液1000ml/h，脱水量100ml/h，泵前泵（枸橼酸钠）230ml/h，5%碳酸氢钠调至45ml/h，5%氯化钙5ml/h，各机器均运转正常。ECMO有凝血倾向，值班医生已知。患者四肢末梢皮肤温暖。左颈内CVC在位通畅：予妥善固定。持续胃肠减压中，可见少量黄褐色液体引出。现去甲肾上腺素组液以11ml/h泵入，瑞芬太尼组液以6ml/h泵入，咪达唑仑组液以10ml/h泵入，艾司洛尔组液以6ml/h泵入，新活素2.1ml/h泵入，患者左手食指指端发黑，值班医生已知，予保暖。在医护协同下辅助患者行俯卧位通气治疗，生命体征汇报值班医生，医嘱继观。遵医嘱予碘伏擦浴一次。遵医嘱暂停肠内营养泵入。Braden10分，RASS-4分 | 患者现气管插管接呼吸机辅助通气中，床边予右颈内静脉+右股静脉处行VV-ECMO联合CVVHDF治疗中，ECMO转速：3000r/min，血流量：3.45L/min，空氧混合器流速4L/min，氧浓度100%，水箱：37.0℃；CRRT血流速150ml/min，后置换液1000ml/h，透析液1000ml/h，脱水量100ml/h，泵前泵（枸橼酸钠）230ml/h，5%碳酸氢钠调至45ml/h，5%氯化钙5ml/h，各机器均运转正常。ECMO有凝血倾向，值班医生已知。患者四肢末梢皮肤温暖。左颈内CVC在位通畅，予妥善固定。持续胃肠减压中，可见少量黄褐色液体引出。现去甲肾上腺素组液以11ml/h泵入，瑞芬太尼组液以6ml/h泵入，咪达唑仑组液以10ml/h泵入，艾司洛尔组液以6ml/h泵入，新活素2.1ml/h泵入，患者左手食指指端发黑，值班医生已知，予保暖。在医护协同下辅助患者行俯卧位通气治疗，生命体征汇报值班医生，医嘱继观。遵医嘱予碘优擦浴一次。遵医嘱暂停肠内营养泵入。Braden10分，RASS-4分 | 患者现气管插管接呼吸机辅助通气中，床边予右颈内静脉+右股静脉处行VV-ECMO联合CVVHDF治疗中，ECMO转速：3000r/min，血流量：3.45L/min，空氧混合器流速4L/min，氧浓度100%，水箱：37.0℃；CRRT血流速150ml/min，后置换液1000ml/h，透析液1000ml/h，脱水量100ml/h，泵前泵（枸橼酸钠）230ml/h，5%碳酸氢钠调至45ml/h，5%氯化钙5ml/h，各机器均运转正常。ECMO有凝血倾向，值班医生已知。患者四肢末梢皮肤温暖。左颈内CVC在位通畅，予妥善固定。持续胃肠减压中，可见少量黄褐色液体引出。现去甲肾上腺素组液以11ml/h泵入，瑞芬太尼组液以6ml/h泵入，咪达唑仑组液以10ml/h泵入，艾司洛尔组液以6ml/h泵入，新活素2.1ml/h泵入，患者左手食指指端发黑，值班医生已知，予保暖。在医护协同下辅助患者行俯卧位通气治疗，生命体征汇报值班医生，医嘱难观。遵医嘱予碘伏擦浴一次。遵医嘱暂停肠内营养泵入。Braden10分，RASS-4分 | substantive_mismatch | substantive_mismatch | rewrite_or_paraphrase |

## Human Review Template

Candidate labels: exact_equal, canonical_only, missing_sentence, extra_text, rewrite_or_paraphrase, char_level_mismatch, punctuation_only, linebreak_join_error, gold_needs_check, main_better_than_col, col_better_than_main, both_wrong.
