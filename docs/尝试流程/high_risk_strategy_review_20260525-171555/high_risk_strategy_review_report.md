# High Risk Strategy Review

## Current Strategies

| field | strategy |
| --- | --- |
| 入量_静脉用药 | iv_v4_preserve_case_clean2x |
| 管路护理 | tube_care_single_col_vlm |
| 病情观察及处理 | observation_direct_v2 |

## Summary

| field | total | main_correct | candidate_correct | main_wrong_candidate_correct | main_correct_candidate_wrong | both_wrong | candidate_missing | candidate_overfill | needs_review_true | correct_but_needs_review | eval_kind_counts |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| OVERALL | 171 | 147 | 159 | 13 | 1 | 11 | 0 | 0 | 1 | 1 | {"equal": 146, "canonical_equal": 10, "substantive_mismatch": 10, "manufacturer_punctuation_equal": 2, "separator_error": 1, "gold_needs_check": 1, "true_char_mismatch": 1} |
| 入量_静脉用药 | 57 | 48 | 56 | 8 | 0 | 1 | 0 | 0 | 1 | 1 | {"equal": 45, "canonical_equal": 8, "manufacturer_punctuation_equal": 2, "gold_needs_check": 1, "true_char_mismatch": 1} |
| 管路护理 | 57 | 53 | 56 | 3 | 0 | 1 | 0 | 0 | 0 | 0 | {"equal": 55, "canonical_equal": 1, "substantive_mismatch": 1} |
| 病情观察及处理 | 57 | 46 | 47 | 2 | 1 | 9 | 0 | 0 | 0 | 0 | {"equal": 46, "substantive_mismatch": 9, "separator_error": 1, "canonical_equal": 1} |

## Details

| page | block_id | field | strategy | gold | main_actual | candidate_actual | main_eval_kind | candidate_eval_kind | needs_review | tail_kind | reason |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| gold_smoke_001 | block_00 | 入量_静脉用药 | iv_v4_preserve_case_clean2x | 钠钾镁钙葡萄糖注射液250mliv.gtt250 | 钠钾镁钙葡萄糖注射液250mliv.gtt | 钠钾镁钙葡萄糖注射液250mliv.gtt250 | true_char_mismatch | equal | False | none |  |
| gold_smoke_001 | block_00 | 管路护理 | tube_care_single_col_vlm | 鼻胃管/是/墨绿色// | 鼻胃管/是/墨绿色/ | 鼻胃管/是/墨绿色// | substantive_mismatch | equal | False | none |  |
| gold_smoke_001 | block_00 | 病情观察及处理 | observation_direct_v2 | 患者出入量总计已汇报医生，医嘱继观。患者尿液浑浊，汇报值班医生，医嘱观察。鼻鼻胃管固定在位，引流通畅，量约0ml。 | 患者出入量总计已汇报医生，医嘱继观。患者尿液浑浊，汇报值班医生，医嘱观察。鼻鼻胃管固定在位，引流通畅，量约0ml。 | 患者出入量总计已汇报医生，医嘱继观。患者尿液浑浊，汇报值班医生，医嘱观察。鼻鼻胃管固定在位，引流通畅，量约0ml。 | equal | equal | False | none |  |
| gold_smoke_001 | block_01 | 入量_静脉用药 | iv_v4_preserve_case_clean2x | null | null | null | equal | equal | False | none |  |
| gold_smoke_001 | block_01 | 管路护理 | tube_care_single_col_vlm | null | null | null | equal | equal | False | none |  |
| gold_smoke_001 | block_01 | 病情观察及处理 | observation_direct_v2 | CPOT0分 | null | CPOT0分 | missing | equal | False | none |  |
| gold_smoke_001 | block_02 | 入量_静脉用药 | iv_v4_preserve_case_clean2x | 氯化钠注射液(丰原-100ml：0.9%，软袋双阀)续用12ml/h+咪达唑仑注射液（苏恩华-5mg：1ml)50MGiv微泵维持 | 氯化钠注射液(丰原-100ml:0.9%,软袋双阀)续用12ml/hr+咪达唑仑注射液(苏恩华-5mg:1ml)50MGiv微泵维持 | 氯化钠注射液(丰原-100ml:0.9%,软袋双阀)续用12ml/h+咪达唑仑注射液(苏恩华-5mg:1ml)50MGiv微泵维持 | true_char_mismatch | canonical_equal | False | none |  |
| gold_smoke_001 | block_02 | 管路护理 | tube_care_single_col_vlm | null | null | null | equal | equal | False | none |  |
| gold_smoke_001 | block_02 | 病情观察及处理 | observation_direct_v2 | 咪达唑仑组液续用12ml/h泵入。 | 咪达唑仑组液续用12ml/h泵入。 | 咪达唑仑组液续用12ml/h泵入。 | equal | equal | False | none |  |
| gold_smoke_001 | block_03 | 入量_静脉用药 | iv_v4_preserve_case_clean2x | 速尿20mgiv0 | 速尿20mgiv0 | 速尿20mgiv0 | equal | equal | False | none |  |
| gold_smoke_001 | block_03 | 管路护理 | tube_care_single_col_vlm | null | null | null | equal | equal | False | none |  |
| gold_smoke_001 | block_03 | 病情观察及处理 | observation_direct_v2 | 遵医嘱用药。 | 遵医嘱用药。 | 遵医嘱用药。 | equal | equal | False | none |  |
| gold_smoke_001 | block_04 | 入量_静脉用药 | iv_v4_preserve_case_clean2x | 钠钾镁钙葡萄糖注射液250mliv.gtt250 | 钠钾镁钙葡萄糖注射液250mliv.gtt;250 | 钠钾镁钙葡萄糖注射液250mliv.gtt250 | separator_error | equal | False | none |  |
| gold_smoke_001 | block_04 | 管路护理 | tube_care_single_col_vlm | 颈内深静脉导管/是///;气管插管/是///23;导尿管/是///;桡动脉导管/是///;静脉留置针/是///;鼻胃管/是///;锁骨下深静脉导管/是///15;股静脉导管/是///43 | 颈内深静脉导管/是///;气管插管/是///23;导尿管/是///;桡动脉导管/是///;静脉留置针/是///;鼻胃管/是///;锁骨下深静脉导管/是///15;股静脉导管/是///;43 | 颈内深静脉导管/是///；气管插管/是///23；导尿管/是///；桡动脉导管/是///；静脉留置针/是///；鼻胃管/是///；锁骨下深静脉导管/是///15；股静脉导管/是///43 | separator_error | canonical_equal | False | none |  |
| gold_smoke_001 | block_04 | 病情观察及处理 | observation_direct_v2 | 患者ECMO持续应用，机器运转正常，转速：3900转/分，流速：4.56L/分，氧浓度：100%，空氧混合器流速：4L/分，肝素余液以4ml/h泵入，力月西余液以12ml/h泵入，去甲肾上腺素组液以1ml/h泵入，患者右侧颈部颈内深静脉导管置入深度15cm，管道通畅。标识明确，固定良好，继续使用。RASS-4分 | 患者ECMO持续应用，机器运转正常，转速：3900转/分，流速：4.56L/分，氧浓度：100%，空氧混合器流速：4L/分，肝素余液以4ml/h泵入，力月西余液以12ml/h泵入，去甲肾上腺素组液以1ml/h泵入，患者右侧颈部颈内深静脉导管置入深度15cm，管道通畅。标识明确，固定良好，继续使用。RASS-4分 | 患者ECMO持续应用，机器运转正常，转速：3900转/分，流速：4.56L/分，氧浓度：100%，空氧混合器流速：4L/分，肝素余液以4ml/h泵入，力月西余液以12ml/h泵入，去甲肾上腺素组液以1ml/h泵入，患者右侧颈部颈内深静脉导管置入深度15cm，管道通畅。标识明确，固定良好，继续使用。RASS-4分 | equal | equal | False | none |  |
| gold_smoke_001 | block_05 | 入量_静脉用药 | iv_v4_preserve_case_clean2x | 莫西沙星250mliv.gtt250 | 莫西沙星250mliv.gtt250 | 莫西沙星250mliv.gtt250 | equal | equal | False | none |  |
| gold_smoke_001 | block_05 | 管路护理 | tube_care_single_col_vlm | null | null | null | equal | equal | False | none |  |
| gold_smoke_001 | block_05 | 病情观察及处理 | observation_direct_v2 | null | null | null | equal | equal | False | none |  |
| gold_smoke_001 | block_06 | 入量_静脉用药 | iv_v4_preserve_case_clean2x | 白蛋白10giv.gtt0 | 白蛋白10giv.gtt0 | 白蛋白10giv.gtt0 | equal | equal | False | none |  |
| gold_smoke_001 | block_06 | 管路护理 | tube_care_single_col_vlm | null | null | null | equal | equal | False | none |  |
| gold_smoke_001 | block_06 | 病情观察及处理 | observation_direct_v2 | 肝素钠医嘱予调整至5ml/h泵入 | 肝素钠医嘱予调整至5ml/h泵入 | 肝素钠医嘱予调整至5ml/h泵入 | equal | equal | False | none |  |
| gold_smoke_001 | block_07 | 入量_静脉用药 | iv_v4_preserve_case_clean2x | null | null | null | equal | equal | False | none |  |
| gold_smoke_001 | block_07 | 管路护理 | tube_care_single_col_vlm | null | null | null | equal | equal | False | none |  |
| gold_smoke_001 | block_07 | 病情观察及处理 | observation_direct_v2 | 医嘱予床边行纤维支气管镜检查，予床边配合；继续观察 | 医嘱予床边行纤维支气管镜检查，予床边配合，继续观察 | 医嘱予床边行纤维支气管镜检查，予床边配合，继续观察 | substantive_mismatch | substantive_mismatch | False | none |  |
| gold_smoke_001 | block_08 | 入量_静脉用药 | iv_v4_preserve_case_clean2x | null | null | null | equal | equal | False | none |  |
| gold_smoke_001 | block_08 | 管路护理 | tube_care_single_col_vlm | null | null | null | equal | equal | False | none |  |
| gold_smoke_001 | block_08 | 病情观察及处理 | observation_direct_v2 | null | null | null | equal | equal | False | none |  |
| gold_smoke_001 | block_09 | 入量_静脉用药 | iv_v4_preserve_case_clean2x | 5%GS100ml+葡萄糖酸钙20MLiv.gtt120 | 5%GS100ml+葡萄糖酸钙20MLiv.gtt120 | 5%GS100ml+葡萄糖酸钙20MLiv.gtt120 | equal | equal | False | none |  |
| gold_smoke_001 | block_09 | 管路护理 | tube_care_single_col_vlm | null | null | null | equal | equal | False | none |  |
| gold_smoke_001 | block_09 | 病情观察及处理 | observation_direct_v2 | null | null | null | equal | equal | False | none |  |
| gold_smoke_001 | block_10 | 入量_静脉用药 | iv_v4_preserve_case_clean2x | NS100ml+泰能2giv.gtt100 | NS100ml+泰能2giv.gtt100 | NS100ml+泰能2giv.gtt100 | equal | equal | False | none |  |
| gold_smoke_001 | block_10 | 管路护理 | tube_care_single_col_vlm | null | null | null | equal | equal | False | none |  |
| gold_smoke_001 | block_10 | 病情观察及处理 | observation_direct_v2 | null | null | null | equal | equal | False | none |  |
| gold_smoke_001 | block_11 | 入量_静脉用药 | iv_v4_preserve_case_clean2x | NS50ml+肝素0.5支iv微泵维持 | NS50ml+肝素0.5支iv微泵维持 | NS50ml+肝素0.5支iv微泵维持 | equal | equal | False | none |  |
| gold_smoke_001 | block_11 | 管路护理 | tube_care_single_col_vlm | null | null | null | equal | equal | False | none |  |
| gold_smoke_001 | block_11 | 病情观察及处理 | observation_direct_v2 | ECMO转速调整至3660，流速4.28，肝素钠泵毕，医嘱予氯化钠注射液（丰原-100ml：0.9%，软袋双阀）50ML肝素钠注射液（沪第一生化-1.25万ux10支）0.5支以5ml/h泵入执行。 | ECMO转速调整至3660，流速4.28，肝素钠泵毕，医嘱予氯化钠注射液(丰原-100ml:0.9%，软袋双阀)50ML肝素钠注射液(沪第一生化-1.25万uX10支)0.5支以5ml/h泵入执行。 | ECMO转速调整至3660，流速4.28，肝素钠泵毕，医嘱予氯化钠注射液（丰原-100ml:0.9%，软袋双阀）50ML肝素钠注射液（沪第一生化-1.25万u×10支）0.5支以5ml/h泵入执行。 | substantive_mismatch | substantive_mismatch | False | none |  |
| gold_smoke_001 | block_12 | 入量_静脉用药 | iv_v4_preserve_case_clean2x | NS100ml+甲泼尼龙琥珀酸钠80mgiv.gtt100;咪达唑仑注射液（苏恩华-5mg：1ml）50MG+氯化钠注射液（丰原-100ml：0.9%，软袋双阀）45MLiv微泵维持 | NS100ml+甲泼尼龙琥珀酸钠80mgiv.gt;咪达唑仑注射液（苏恩华-5mg:1ml）50M;G+氯化钠注射液（丰原-100ml:0.9%，软袋双阀）45MLiv微泵维持 | NS100ml+甲泼尼龙琥珀酸钠80mgiv.gtt100;咪达唑仑注射液(苏恩华-5mg:1ml)50MG+氯化钠注射液(丰原-100ml:0.9%,软袋双阀)45MLiv微泵维持 | true_char_mismatch | canonical_equal | False | none |  |
| gold_smoke_001 | block_12 | 管路护理 | tube_care_single_col_vlm | null | null | null | equal | equal | False | none |  |
| gold_smoke_001 | block_12 | 病情观察及处理 | observation_direct_v2 | APTT：44.8，遵医嘱予肝素钠调整至6ml/h泵入，力月西泵毕，医嘱予咪达唑仑注射液（苏恩华-5mg:1ml）50MG氯化钠注射液（丰原-100ml:0.9%，软袋双阀)45M调整至10ml/h泵入执行。 | APTT：44.8，遵医嘱予肝素钠调整至6ml/h泵入，力月西泵毕，医嘱予咪达唑仑注射液(苏恩华-5mg:1ml)50MG氯化钠注射液(丰原-100ml:0.9%,软袋双阀)45ML调整至10ml/h泵入执行。 | APTT：44.8，遵医嘱予肝素钠调整至6ml/h泵入，力月西泵毕，医嘱予咪达唑仑注射液(苏思华-5mg:1ml)50MG氯化钠注射液(丰原-100ml:0.9%,软袋双阀)45ML调整至10ml/h泵入执行。 | substantive_mismatch | substantive_mismatch | False | none |  |
| gold_smoke_001 | block_13 | 入量_静脉用药 | iv_v4_preserve_case_clean2x | NS100ml+泮托拉唑40mgiv.gtt100 | NS100ml+泮托拉唑40mgiv.gtt100 | NS100ml+泮托拉唑40mgiv.gtt100 | equal | equal | False | none |  |
| gold_smoke_001 | block_13 | 管路护理 | tube_care_single_col_vlm | null | null | null | equal | equal | False | none |  |
| gold_smoke_001 | block_13 | 病情观察及处理 | observation_direct_v2 | RASS-4分，CPOT0分 | RASS-4分，CPOT0分 | RASS-4分，CPOT0分 | equal | equal | False | none |  |
| gold_smoke_001 | block_14 | 入量_静脉用药 | iv_v4_preserve_case_clean2x | 枸橼酸舒芬太尼注射液(鄂宜昌人福,-50ug:1ml)200UG+氯化钠注射液(丰原,-100ml:0.9%,软袋双阀)50MLiv微泵维持 | 枸橼酸舒芬太尼注射液（鄂宜昌人福-50ug:1ml）200UG+氯化钠注射液（丰原-100ml:0.9%,软袋双阀）50MLiv微泵维持 | 枸橼酸舒芬太尼注射液(鄂宜昌人福-50ug:1ml)200UG+氯化钠注射液(丰原-100ml:0.9%,软袋双阀)50MLiv微泵维持 | manufacturer_punctuation_equal | manufacturer_punctuation_equal | False | raw_lines_missing_tail |  |
| gold_smoke_001 | block_14 | 管路护理 | tube_care_single_col_vlm | null | null | null | equal | equal | False | none |  |
| gold_smoke_001 | block_14 | 病情观察及处理 | observation_direct_v2 | 舒芬太尼泵毕，医嘱予枸橼酸舒芬太尼注射液(鄂,宜昌人福-50ug：1ml)200UG氯化钠注射液（丰原,-100ml：0.9%，软袋双阀）50M调整至2ml/h执行。 | 舒芬太尼泵毕，医嘱予枸橼酸舒芬太尼注射液(鄂宜昌人福-50ug:1ml)200UG氯化钠注射液(丰原-100ml:0.9%,软袋双阀)50ML调整至2ml/h执行。 | 舒芬太尼泵毕，医嘱予枸橼酸舒芬太尼注射液(鄂宜昌人福-50ug:1ml)2000G氯化钠注射液(丰原-100ml:0.9%,软袋双阀)50ML调整至2ml/h执行。 | substantive_mismatch | substantive_mismatch | False | none |  |
| gold_smoke_001 | block_15 | 入量_静脉用药 | iv_v4_preserve_case_clean2x | null | null | null | equal | equal | False | none |  |
| gold_smoke_001 | block_15 | 管路护理 | tube_care_single_col_vlm | null | null | null | equal | equal | False | none |  |
| gold_smoke_001 | block_15 | 病情观察及处理 | observation_direct_v2 | APTT:63.3，遵医嘱予APTT调整至5ml/h泵入，继续观察 | APTT:63.3，遵医嘱予APTT调整至5ml/h泵入，继续观察 | APTT:63.3，遵医嘱予APTT调整至5ml/h泵入，继续观察 | equal | equal | False | none |  |
| gold_smoke_001 | block_16 | 入量_静脉用药 | iv_v4_preserve_case_clean2x | 氯化钠注射液(丰原-100ml：0.9%，软袋双阀)48ML+盐酸右美托咪定注射液（辰欣药业-0.2mg：2ml）0.4MGiv微泵维持 | 氯化钠注射液(丰原-100ml:0.9%,软袋双阀)48L+盐酸右美托咪定注射液(辰欣药业-0.2mg:2ml)0.4MGiv微泵维持 | 氯化钠注射液(丰原-100ml:0.9%,软袋双阀)48ML+盐酸右美托咪定注射液(辰欣药业-0.2mg:2ml)0.4MGiv微泵维持 | true_char_mismatch | canonical_equal | False | none |  |
| gold_smoke_001 | block_16 | 管路护理 | tube_care_single_col_vlm | null | null | null | equal | equal | False | none |  |
| gold_smoke_001 | block_16 | 病情观察及处理 | observation_direct_v2 | 氯化钠注射液(丰原-100ml:0.9%,软袋双阀)48ML;盐酸右美托咪定注射液(辰欣药业-0.2mg:2ml)0.4;MG以4ml/h续泵执行。 | 氯化钠注射液(丰原-100ml:0.9%,软袋双阀)48ML；盐酸右美托咪定注射液(辰欣药业-0.2mg:2ml)0.4MG以4ml/h续泵执行。 | 氯化钠注射液(丰原-100ml:0.9%,软袋双阀)48ML 盐酸右美托咪定注射液(辰欣药业-0.2mg:2ml)0.4 MG以4ml/h续泵执行。 | separator_error | separator_error | False | none |  |
| gold_smoke_001 | block_17 | 入量_静脉用药 | iv_v4_preserve_case_clean2x | NS100ml+泰能2giv.gtt100 | NS100ml+泰能2giv.gtt100 | NS100ml+泰能2giv.gtt100 | equal | equal | False | none |  |
| gold_smoke_001 | block_17 | 管路护理 | tube_care_single_col_vlm | null | null | null | equal | equal | False | none |  |
| gold_smoke_001 | block_17 | 病情观察及处理 | observation_direct_v2 | null | null | null | equal | equal | False | none |  |
| gold_dev_m_002 | block_00 | 入量_静脉用药 | iv_v4_preserve_case_clean2x | 白蛋白10giv.gtt50;NS50m1+肝素0.5支iv微泵维持 | 白蛋白10giv.gtt50;NS50ml+肝素0.5支iv微泵维持 | 白蛋白10giv.gtt50;NS50ml+肝素0.5支iv微泵维持 | gold_needs_check | gold_needs_check | False | raw_lines_missing_tail |  |
| gold_dev_m_002 | block_00 | 管路护理 | tube_care_single_col_vlm | null | null | null | equal | equal | False | none |  |
| gold_dev_m_002 | block_00 | 病情观察及处理 | observation_direct_v2 | 纤支镜检查结束，予标本送检。予肠内营养液80ml/h胃管泵入。肝素钠7ml/h续泵。 | 纤支镜检查结束，予标本送检。予肠内营养液80m；1/h胃管泵入。肝素钠7ml/h续泵。 | 纤支镜检查结束，予标本送检。予肠内营养液80ml/h胃管泵入。肝素钠7ml/h续泵。 | substantive_mismatch | equal | False | none |  |
| gold_dev_m_002 | block_01 | 入量_静脉用药 | iv_v4_preserve_case_clean2x | NS50ml+力月西50mgiv微泵维持 | NS50ml+力月西50mgiv微泵维持 | NS50ml+力月西50mgiv微泵维持 | equal | equal | False | none |  |
| gold_dev_m_002 | block_01 | 管路护理 | tube_care_single_col_vlm | null | null | null | equal | equal | False | none |  |
| gold_dev_m_002 | block_01 | 病情观察及处理 | observation_direct_v2 | 咪达唑仑12ml/h续泵。 | 咪达唑仑12ml/h续泵。 | 咪达唑仑12ml/h续泵。 | equal | equal | False | none |  |
| gold_dev_m_002 | block_02 | 入量_静脉用药 | iv_v4_preserve_case_clean2x | 氯化钠注射液(丰原-100ml：0.9%，软袋双阀)100ML+克林霉素磷酸酯注射液(鲁方明-0.3g:2ml)0.60Giv.gtt100 | 氯化钠注射液(丰原-100ml:0.9%软袋双阀)100ML+克林霉素磷酸酯注射液(鲁方明-0.3g:2ml)0.60Giv.gtt100 | 氯化钠注射液(丰原-100ml:0.9%,软袋双阀)100ML+克林霉素磷酸酯注射液(鲁方明-0.3g:2ml)0.60Giv.gtt100 | true_char_mismatch | canonical_equal | False | none |  |
| gold_dev_m_002 | block_02 | 管路护理 | tube_care_single_col_vlm | null | null | null | equal | equal | False | none |  |
| gold_dev_m_002 | block_02 | 病情观察及处理 | observation_direct_v2 | null | null | null | equal | equal | False | none |  |
| gold_dev_m_002 | block_03 | 入量_静脉用药 | iv_v4_preserve_case_clean2x | null | null | null | equal | equal | False | none |  |
| gold_dev_m_002 | block_03 | 管路护理 | tube_care_single_col_vlm | null | null | null | equal | equal | False | none |  |
| gold_dev_m_002 | block_03 | 病情观察及处理 | observation_direct_v2 | 出入量汇报值班医生，嘱予密观。 | 出入量汇报值班医生，嘱予密观。 | 出入量汇报值班医生，嘱予密观。 | equal | equal | False | none |  |
| gold_dev_m_002 | block_04 | 入量_静脉用药 | iv_v4_preserve_case_clean2x | 枸橼酸舒芬太尼注射液(鄂宜昌人福-50ug:1ml)12h+氯化钠注射液(丰原-100ml:0.9%,软袋双阀)50MLiv微泵维持 | 枸橼酸舒芬太尼注射液（鄂宜昌人福-50ug:1ml）12h+氯化钠注射液（丰原-100ml:0.9%，软袋双阀）50MLiv微泵维持 | 枸橼酸舒芬太尼注射液(鄂宜昌人福-50ug:1ml)12h+氯化钠注射液(丰原-100ml:0.9%,软袋双阀)50MLiv微泵维持 | canonical_equal | equal | False | none |  |
| gold_dev_m_002 | block_04 | 管路护理 | tube_care_single_col_vlm | null | null | null | equal | equal | False | none |  |
| gold_dev_m_002 | block_04 | 病情观察及处理 | observation_direct_v2 | 舒芬太尼4ml/h续泵。 | 舒芬太尼4ml/h续泵。 | 舒芬太尼4ml/h续泵。 | equal | equal | False | none |  |
| gold_dev_m_002 | block_05 | 入量_静脉用药 | iv_v4_preserve_case_clean2x | null | null | null | equal | equal | False | none |  |
| gold_dev_m_002 | block_05 | 管路护理 | tube_care_single_col_vlm | 气管插管/是///23;锁骨下深静脉导管/是///15;股静脉导管/是///43;颈内深静脉导管/是///;鼻胃管/是///55;导尿管/是/黄色//;桡动脉导管/是///;静脉留置针/是/// | 气管插管/是///23;锁骨下深静脉导管/是///15;股静脉导管/是///43;颈内深静脉导管/是///;鼻胃管/是///55;导尿管/是/黄色//;桡动脉导管/是///;静脉留置针/是/// | 气管插管/是///23;锁骨下深静脉导管/是///15;股静脉导管/是///43;颈内深静脉导管/是///;鼻胃管/是///55;导尿管/是/黄色//;桡动脉导管/是///;静脉留置针/是/// | equal | equal | False | none |  |
| gold_dev_m_002 | block_05 | 病情观察及处理 | observation_direct_v2 | 患者持续床边VVECMO治疗中，转速：3220转/分，流速：3.67L/分，空氧混合器流速4升/分，氧浓度100%，机器运转正常，管路妥善固定中，外露刻度无变化，敷料清洁干燥。胰岛素组液以2ml/h泵入，力月西组液以12ml/h泵入，舒芬太尼组液以4ml/h泵入，肝素组液以7ml/h泵入中，右美组液以2ml/h泵入中，生命体征汇报值班医生，嘱予密观。Braden10分，RASS-4分，CPOT0分 | 患者持续床边VVECMO治疗中，转速：3220转/分，流速：3.67L/分，空氧混合器流速4升/分，氧浓度100%，机器运转正常，管路妥善固定中，外露刻度无变化，敷料清洁干燥。胰岛素组液以2ml/h泵入，力月西组液以12ml/h泵入，舒芬太尼组液以4ml/h泵入，肝素组液以7ml/h泵入中，右美组液以2ml/h泵入中，生命体征汇报值班医生，嘱予密观。Braden10分，RASS-4分，CPOT0分 | 患者持续床边VVECMO治疗中，转速：3220转/分，流速：3.67L/分，空氧混合器流速4升/分，氧浓度100%，机器运转正常，管路妥善固定中，外露刻度无变化，敷料清洁干燥。胰岛素组液以2ml/h泵入，力月西组液以12ml/h泵入，舒芬太尼组液以4ml/h泵入，肝素组液以7ml/h泵入中，右美组液以2ml/h泵入中，生命体征汇报值班医生，嘱予密观。Braden10分，RASS-4分，CPOT0分 | equal | equal | False | none |  |
| gold_dev_m_002 | block_06 | 入量_静脉用药 | iv_v4_preserve_case_clean2x | null | null | null | equal | equal | False | none |  |
| gold_dev_m_002 | block_06 | 管路护理 | tube_care_single_col_vlm | null | null | null | equal | equal | False | none |  |
| gold_dev_m_002 | block_06 | 病情观察及处理 | observation_direct_v2 | null | null | null | equal | equal | False | none |  |
| gold_dev_m_002 | block_07 | 入量_静脉用药 | iv_v4_preserve_case_clean2x | NS50ml+力月西50mgiv微泵维持 | NS50ml+力月西50mgiv微泵维持 | NS50ml+力月西50mgiv微泵维持 | equal | equal | False | none |  |
| gold_dev_m_002 | block_07 | 管路护理 | tube_care_single_col_vlm | null | null | null | equal | equal | False | none |  |
| gold_dev_m_002 | block_07 | 病情观察及处理 | observation_direct_v2 | null | null | null | equal | equal | False | none |  |
| gold_dev_m_002 | block_08 | 入量_静脉用药 | iv_v4_preserve_case_clean2x | null | null | null | equal | equal | False | none |  |
| gold_dev_m_002 | block_08 | 管路护理 | tube_care_single_col_vlm | null | null | null | equal | equal | False | none |  |
| gold_dev_m_002 | block_08 | 病情观察及处理 | observation_direct_v2 | null | null | null | equal | equal | False | none |  |
| gold_dev_m_002 | block_09 | 入量_静脉用药 | iv_v4_preserve_case_clean2x | NS50ml+胰岛素50uiv微泵维持 | NS50ml+胰岛素50uiv微泵维持 | NS50ml+胰岛素50uiv微泵维持 | equal | equal | False | none |  |
| gold_dev_m_002 | block_09 | 管路护理 | tube_care_single_col_vlm | null | null | null | equal | equal | False | none |  |
| gold_dev_m_002 | block_09 | 病情观察及处理 | observation_direct_v2 | 医生予床边查视后更改呼吸机参数。 | 医生予床边查视后更改呼吸机参数。 | 医生予床边查视后更改呼吸机参数。 | equal | equal | False | none |  |
| gold_dev_m_002 | block_10 | 入量_静脉用药 | iv_v4_preserve_case_clean2x | NS50ml+肝素0.5支iv微泵维持 | NS50ml+肝素0.5支iv微泵维持 | NS50ml+肝素0.5支iv微泵维持 | equal | equal | False | none |  |
| gold_dev_m_002 | block_10 | 管路护理 | tube_care_single_col_vlm | null | null | null | equal | equal | False | none |  |
| gold_dev_m_002 | block_10 | 病情观察及处理 | observation_direct_v2 | APTT:43.6s;遵医嘱予肝素组液以7.5ml/h泵入。 | APTT:43.6s,遵医嘱予肝素组液以7.5ml/h泵入。 | APTT:43.6s,遵医嘱予肝素组液以7.5ml/h泵入。 | substantive_mismatch | substantive_mismatch | False | none |  |
| gold_dev_m_002 | block_11 | 入量_静脉用药 | iv_v4_preserve_case_clean2x | NS100ml+泰能2giv.gtt100 | NS100ml+泰能2giv.gtt100 | NS100ml+泰能2giv.gtt100 | equal | equal | False | none |  |
| gold_dev_m_002 | block_11 | 管路护理 | tube_care_single_col_vlm | null | null | null | equal | equal | False | none |  |
| gold_dev_m_002 | block_11 | 病情观察及处理 | observation_direct_v2 | 血糖值汇报值班医生，遵医嘱予调RI组液以3ml/h泵入。 | 血糖值汇报值班医生，遵医嘱予调RI组液以3ml/h泵入。 | 血糖值汇报值班医生，遵医嘱予调RI组液以3ml/h泵入。 | equal | equal | False | none |  |
| gold_dev_m_002 | block_12 | 入量_静脉用药 | iv_v4_preserve_case_clean2x | null | null | null | equal | equal | False | none |  |
| gold_dev_m_002 | block_12 | 管路护理 | tube_care_single_col_vlm | null | null | null | equal | equal | False | none |  |
| gold_dev_m_002 | block_12 | 病情观察及处理 | observation_direct_v2 | null | null | null | equal | equal | False | none |  |
| gold_dev_m_002 | block_13 | 入量_静脉用药 | iv_v4_preserve_case_clean2x | null | null | null | equal | equal | False | none |  |
| gold_dev_m_002 | block_13 | 管路护理 | tube_care_single_col_vlm | null | null | null | equal | equal | False | none |  |
| gold_dev_m_002 | block_13 | 病情观察及处理 | observation_direct_v2 | null | null | null | equal | equal | False | none |  |
| gold_dev_m_002 | block_14 | 入量_静脉用药 | iv_v4_preserve_case_clean2x | NS50ml+力月西50mgiv微泵维持 | NS50ml+力月西50mgiv微泵维持 | NS50ml+力月西50mgiv微泵维持 | equal | equal | False | none |  |
| gold_dev_m_002 | block_14 | 管路护理 | tube_care_single_col_vlm | null | null | null | equal | equal | False | none |  |
| gold_dev_m_002 | block_14 | 病情观察及处理 | observation_direct_v2 | null | null | null | equal | equal | False | none |  |
| gold_dev_m_002 | block_15 | 入量_静脉用药 | iv_v4_preserve_case_clean2x | 氯化钠注射液（丰原-100ml：0.9%，软袋,双阀）100ML+克林霉素磷酸酯注射液（鲁方明-0.3g:2ml)0.6Giv.gtt100 | 氯化钠注射液(丰原-100ml:0.9%,软袋双阀)100ML+克林霉素磷酸酯注射液(鲁方明-0.3g:2ml)0.6Giv.gtt100 | 氯化钠注射液(丰原-100ml:0.9%,软袋双阀)100ML+克林霉素磷酸酯注射液(鲁方明-0.3g:2ml)0.6Giv.gtt100 | manufacturer_punctuation_equal | manufacturer_punctuation_equal | False | raw_lines_missing_tail |  |
| gold_dev_m_002 | block_15 | 管路护理 | tube_care_single_col_vlm | null | null | null | equal | equal | False | none |  |
| gold_dev_m_002 | block_15 | 病情观察及处理 | observation_direct_v2 | null | null | null | equal | equal | False | none |  |
| gold_dev_m_002 | block_16 | 入量_静脉用药 | iv_v4_preserve_case_clean2x | null | null | null | equal | equal | False | none |  |
| gold_dev_m_002 | block_16 | 管路护理 | tube_care_single_col_vlm | null | null | null | equal | equal | False | none |  |
| gold_dev_m_002 | block_16 | 病情观察及处理 | observation_direct_v2 | APTT:64.4s，遵医嘱予肝素组液以7ml/h泵入。 | APTT:64.4s,遵医嘱予肝素组液以7ml/h泵入。 | APTT:64.4s,遵医嘱予肝素组液以7ml/h泵入。 | canonical_equal | canonical_equal | False | none |  |
| gold_dev_m_002 | block_17 | 入量_静脉用药 | iv_v4_preserve_case_clean2x | null | null | null | equal | equal | False | none |  |
| gold_dev_m_002 | block_17 | 管路护理 | tube_care_single_col_vlm | null | null | null | equal | equal | False | none |  |
| gold_dev_m_002 | block_17 | 病情观察及处理 | observation_direct_v2 | null | null | null | equal | equal | False | none |  |
| gold_dev_m_002 | block_18 | 入量_静脉用药 | iv_v4_preserve_case_clean2x | null | null | null | equal | equal | False | none |  |
| gold_dev_m_002 | block_18 | 管路护理 | tube_care_single_col_vlm | null | null | null | equal | equal | False | none |  |
| gold_dev_m_002 | block_18 | 病情观察及处理 | observation_direct_v2 | null | null | null | equal | equal | False | none |  |
| gold_dev_m_002 | block_19 | 入量_静脉用药 | iv_v4_preserve_case_clean2x | NS50ml+力月西50mgiv微泵维持 | NS50ml+力月西50mgiv微泵维持 | NS50ml+力月西50mgiv微泵维持 | equal | equal | False | none |  |
| gold_dev_m_002 | block_19 | 管路护理 | tube_care_single_col_vlm | null | null | null | equal | equal | False | none |  |
| gold_dev_m_002 | block_19 | 病情观察及处理 | observation_direct_v2 | null | null | null | equal | equal | False | none |  |
| gold_dev_m_002 | block_20 | 入量_静脉用药 | iv_v4_preserve_case_clean2x | null | null | null | equal | equal | False | none |  |
| gold_dev_m_002 | block_20 | 管路护理 | tube_care_single_col_vlm | null | null | null | equal | equal | False | none |  |
| gold_dev_m_002 | block_20 | 病情观察及处理 | observation_direct_v2 | 患者出入量总计已汇报医生，医嘱继观。血糖值汇报值班医生，遵医嘱予调RI组液以4ml/h泵入。CPOT0分 | 患者出入量总计已汇报医生，医嘱继观。血糖值汇报值班医生，遵医嘱予调RI组液以4ml/h泵入。CPOT0分 | 患者出入量总计已汇报医生，医嘱维观。血糖值汇报值班医生，遵医嘱予调RI组液以4ml/h泵入。CPOT0分 | equal | substantive_mismatch | False | none |  |
| gold_dev_m_002 | block_21 | 入量_静脉用药 | iv_v4_preserve_case_clean2x | NS50ml+肝素0.5支iv微泵维持 | NS50ml+肝素0.5支iv微泵维持 | NS50ml+肝素0.5支iv微泵维持 | equal | equal | False | none |  |
| gold_dev_m_002 | block_21 | 管路护理 | tube_care_single_col_vlm | null | null | null | equal | equal | False | none |  |
| gold_dev_m_002 | block_21 | 病情观察及处理 | observation_direct_v2 | null | null | null | equal | equal | False | none |  |
| gold_dev_m_002 | block_22 | 入量_静脉用药 | iv_v4_preserve_case_clean2x | null | null | null | equal | equal | False | none |  |
| gold_dev_m_002 | block_22 | 管路护理 | tube_care_single_col_vlm | null | null | null | equal | equal | False | none |  |
| gold_dev_m_002 | block_22 | 病情观察及处理 | observation_direct_v2 | null | null | null | equal | equal | False | none |  |
| gold_dev_m_002 | block_23 | 入量_静脉用药 | iv_v4_preserve_case_clean2x | NS100ml+泰能2giv.gtt100;枸橼酸舒芬太尼注射液（鄂宜昌人福-50ug：1ml）4ml/l+氯化钠注射液（丰原-100ml：0.9%，软袋双阀）46MLiv微泵维 | NS100ml+泰能2giv.gtt100;枸橼酸舒芬太尼注射液（鄂宜昌人福-50ug:1ml)4ml/1+氯化钠注射液（丰原-100ml:0.9%,软袋双阀）46MLiv微泵维 | NS100ml+泰能2giv.gtt100;枸橼酸舒芬太尼注射液(鄂宜昌人福-50ug:1ml)4ml/1+氯化钠注射液(丰原-100ml:0.9%,软袋双阀)46MLiv微泵维 | true_char_mismatch | true_char_mismatch | False | raw_lines_missing_tail |  |
| gold_dev_m_002 | block_23 | 管路护理 | tube_care_single_col_vlm | 桡动脉导管/是///;锁骨下深静脉导管/是/// | 桡动脉导管/是///;锁骨下深静脉导管/是/// | 桡动脉导管/是///;锁骨下深静脉导管/是/// | equal | equal | False | none |  |
| gold_dev_m_002 | block_23 | 病情观察及处理 | observation_direct_v2 | 遵医嘱肝素钠调整至6.5ml/h泵入，患者ECMO应用；机器运转正常，转速：3220转/分，流量：3.74L/分；舒芬太尼液泵毕，医嘱予原量以4ml/h泵入；肠内营养液暂停应用，胰岛素余液调整至2ml/h | 遵医嘱肝素钠调整至6.5ml/h泵入，患者ECMO应用，机器运转正常，转速：3220转/分，流量：3.74L/分，舒芬太尼液泵毕，医嘱予原量以4ml/h泵入，肠内营养液暂停应用，胰岛素余液调整至2ml/h | 遵医嘱肝素钠调整至6.5ml/h泵入，患者ECMO应用，机器运转正常，转速：3220转/分，流量：3.74L/分，舒芬太尼液泵毕，医嘱予原量以4ml/h泵入，肠内营养液暂停应用，胰岛素余液调整至2ml/h | substantive_mismatch | substantive_mismatch | False | none |  |
| gold_validation_003 | block_00 | 入量_静脉用药 | iv_v4_preserve_case_clean2x | null | null | null | equal | equal | False | none |  |
| gold_validation_003 | block_00 | 管路护理 | tube_care_single_col_vlm | null | null | null | equal | equal | False | none |  |
| gold_validation_003 | block_00 | 病情观察及处理 | observation_direct_v2 | null | null | null | equal | equal | False | none |  |
| gold_validation_003 | block_01 | 入量_静脉用药 | iv_v4_preserve_case_clean2x | 0.9%NS50ml+胰岛素注射液50uiv微泵维持(暂停使用余量43ml) | 0.9%NS50ml+胰岛素注射液50uiv微泵维持（暂停使用余量43ml） | 0.9%NS50ml+胰岛素注射液50uiv微泵维持（暂停使用余量43ml） | canonical_equal | canonical_equal | False | none |  |
| gold_validation_003 | block_01 | 管路护理 | tube_care_single_col_vlm | 鼻胃管/是/咖啡色//55 | 鼻胃管/是/咖啡色/55 | 鼻胃管/是/咖啡色//55 | substantive_mismatch | equal | False | none |  |
| gold_validation_003 | block_01 | 病情观察及处理 | observation_direct_v2 | 血糖值汇报值班医生，遵医嘱予暂停胰岛素应用;。CPOT0分 | 血糖值汇报值班医生，遵医嘱予暂停胰岛素应用；CPOT0分 | 血糖值汇报值班医生，遵医嘱予暂停胰岛素应用·CPOT0分 | substantive_mismatch | substantive_mismatch | False | none |  |
| gold_validation_003 | block_02 | 入量_静脉用药 | iv_v4_preserve_case_clean2x | null | null | null | equal | equal | False | none |  |
| gold_validation_003 | block_02 | 管路护理 | tube_care_single_col_vlm | null | null | null | equal | equal | False | none |  |
| gold_validation_003 | block_02 | 病情观察及处理 | observation_direct_v2 | 患者出入量总计已汇报医生，医嘱继观。 | 患者出入量总计已汇报医生，医嘱继观。 | 患者出入量总计已汇报医生，医嘱继观。 | equal | equal | False | none |  |
| gold_validation_003 | block_03 | 入量_静脉用药 | iv_v4_preserve_case_clean2x | null | null | null | equal | equal | False | none |  |
| gold_validation_003 | block_03 | 管路护理 | tube_care_single_col_vlm | 导尿管/是/黄褐色/;股静脉导管/是///;鼻胃管/是/暗红色//55;股静脉导管/是///20;鼻肠管/是///100;颈内深静脉导管/是///13;气管插管/是///23;颈静脉导管/是/// | 导尿管/是/黄褐色//;股静脉导管/是///;鼻胃管/是/暗红色//55;股静脉导管/是///20;鼻肠管/是///100;颈内深静脉导管/是///13;气管插管/是///23;颈静脉导管/是/// | 导尿管/是/黄褐色//;股静脉导管/是///;鼻胃管/是/暗红色//55;股静脉导管/是///20;鼻肠管/是///100;颈内深静脉导管/是///13;气管插管/是///23;颈静脉导管/是/// | substantive_mismatch | substantive_mismatch | False | none |  |
| gold_validation_003 | block_03 | 病情观察及处理 | observation_direct_v2 | 患者现气管插管接呼吸机辅助通气中，床边予右颈内静脉+右股静脉处行VV-ECMO联合CVVHDF治疗中，ECMO转速：3000r/min，血流量：3.45L/min，空氧混合器流速4L/min，氧浓度100%，水箱：37.0℃；CRRT血流速150ml/min，后置换液1000ml/h，透析液1000ml/h，脱水量100ml/h，泵前泵（枸橼酸钠）230ml/h，5%碳酸氢钠调至45ml/h，5%氯化钙5ml/h，各机器均运转正常。ECMO有凝血倾向，值班医生已知。患者四肢末梢皮肤温暖。左颈内CVC在位通畅：予妥善固定。持续胃肠减压中，可见少量黄褐色液体引出。现去甲肾上腺素组液以11ml/h泵入，瑞芬太尼组液以6ml/h泵入，咪达唑仑组液以10ml/h泵入，艾司洛尔组液以6ml/h泵入，新活素2.1ml/h泵入，患者左手食指指端发黑，值班医生已知，予保暖。在医护协同下辅助患者行俯卧位通气治疗，生命体征汇报值班医生，医嘱继观。遵医嘱予碘伏擦浴一次。遵医嘱暂停肠内营养泵入。Braden10分，RASS-4分 | 患者现气管插管接呼吸机辅助通气中，床边予右颈内静脉+右股静脉处行VV-ECMO联合CVVHDF治疗中，ECMO转速：3000r/min，血流量：3.45L/min，空氧混合器流速4L/min，氧浓度100%，水箱：37.0℃；CRRT血流速150ml/min，后置换液1000ml/h，透析液1000ml/h，脱水量100ml/h，泵前泵（枸橼酸钠）230ml/h，5%碳酸氢钠调至45ml/h，5%氯化钙5ml/h，各机器均运转正常。ECMO有凝血倾向，值班医生已知。患者四肢末梢皮肤温暖。左颈内CVC在位通畅，予妥善固定。持续胃肠减压中，可见少量黄褐色液体引出。现去甲肾上腺素组液以11ml/h泵入，瑞芬太尼组液以6ml/h泵入，咪达唑仑组液以10ml/h泵入，艾司洛尔组液以6ml/h泵入，新活素2.1ml/h泵入，患者左手食指指端发黑，值班医生已知，予保暖。在医护协同下辅助患者行俯卧位通气治疗，生命体征汇报值班医生，医嘱继观。遵医嘱予碘优擦浴一次。遵医嘱暂停肠内营养泵入。Braden10分，RASS-4分 | 患者现气管插管接呼吸机辅助通气中，床边予右颈内静脉+右股静脉处行VV-ECMO联合CVVHDF治疗中，ECMO转速：3000r/min，血流量：3.45L/min，空氧混合器流速4L/min，氧浓度100%，水箱：37.0℃；CRRT血流速150ml/min，后置换液1000ml/h，透析液1000ml/h，脱水量100ml/h，泵前泵（枸橼酸钠）230ml/h，5%碳酸氢钠调至45ml/h，5%氯化钙5ml/h，各机器均运转正常。ECMO有凝血倾向，值班医生已知。患者四肢末梢皮肤温暖。左颈内CVC在位通畅，予妥善固定。持续胃肠减压中，可见少量黄褐色液体引出。现去甲肾上腺素组液以11ml/h泵入，瑞芬太尼组液以6ml/h泵入，咪达唑仑组液以10ml/h泵入，艾司洛尔组液以6ml/h泵入，新活素2.1ml/h泵入，患者左手食指指端发黑，值班医生已知，予保暖。在医护协同下辅助患者行俯卧位通气治疗，生命体征汇报值班医生，医嘱难观。遵医嘱予碘伏擦浴一次。遵医嘱暂停肠内营养泵入。Braden10分，RASS-4分 | substantive_mismatch | substantive_mismatch | False | none |  |
| gold_validation_003 | block_04 | 入量_静脉用药 | iv_v4_preserve_case_clean2x | 白蛋白50mliv.gtt50;氯化钠注射液(丰原-100ml：0.9%，直立式软袋双阀)40ML+咪达唑仑注射液(苏恩华-5mg：1ml)50MGiv微泵维持 | 白蛋白50mliv.gtt50;氯化钠注射液(丰原-100ml:0.9%,直立式软袋双阀)40ML+咪达唑仑注射液(苏恩华-5mg:1ml)50MGiv微泵维持 | 白蛋白50mliv.gtt50;氯化钠注射液(丰原-100ml:0.9%,直立式软袋双阀)40ML+咪达唑仑注射液(苏恩华-5mg:1ml)50MGiv微泵维持 | canonical_equal | canonical_equal | False | none |  |
| gold_validation_003 | block_04 | 管路护理 | tube_care_single_col_vlm | null | null | null | equal | equal | False | none |  |
| gold_validation_003 | block_04 | 病情观察及处理 | observation_direct_v2 | 力月西组液泵毕，遵医嘱续用10ml/h。 | 力月西组液泵毕，遵医嘱续用10ml/h。 | 力月西组液泵毕，遵医嘱续用10ml/h。 | equal | equal | False | none |  |
| gold_validation_003 | block_05 | 入量_静脉用药 | iv_v4_preserve_case_clean2x | NS50ml+盐酸瑞芬太尼4mgiv微泵维持 | NS50ml+盐酸瑞芬太尼4mgiv微泵维持 | NS50ml+盐酸瑞芬太尼4mgiv微泵维持 | equal | equal | False | none |  |
| gold_validation_003 | block_05 | 管路护理 | tube_care_single_col_vlm | null | null | null | equal | equal | False | none |  |
| gold_validation_003 | block_05 | 病情观察及处理 | observation_direct_v2 | 瑞芬太尼组液泵毕，遵医嘱续用6ml/h。 | 瑞芬太尼组液泵毕，遵医嘱续用6ml/h。 | 瑞芬太尼组液泵毕，遵医嘱续用6ml/h。 | equal | equal | False | none |  |
| gold_validation_003 | block_06 | 入量_静脉用药 | iv_v4_preserve_case_clean2x | NS100ml+亚胺培南西司他丁钠1giv.gtt100 | NS100ml+亚胺培南西司他丁钠1giv.gt | NS100ml+亚胺培南西司他丁钠1giv.gtt100 | true_char_mismatch | equal | False | none |  |
| gold_validation_003 | block_06 | 管路护理 | tube_care_single_col_vlm | null | null | null | equal | equal | False | none |  |
| gold_validation_003 | block_06 | 病情观察及处理 | observation_direct_v2 | null | null | null | equal | equal | False | none |  |
| gold_validation_003 | block_07 | 入量_静脉用药 | iv_v4_preserve_case_clean2x | NS20ml+氨溴索30mgiv20;氯化钠注射液(丰原-100ml：0.9%，直立式软袋双阀)20ML+注射用艾司奥美拉唑钠(湖北人民制药-40mg)40MGiv20 | NS20ml+氨溴索30mgiv20;氯化钠注射液(丰原-100ml:0.9%,直立式软袋双阀)20ML+注射用艾司奥美拉唑钠(湖北人民制药-40mg)40MGiv20 | NS20ml+氨溴索30mgiv20;氯化钠注射液(丰原-100ml:0.9%,直立式软袋双阀)20ML+注射用艾司奥美拉唑钠(湖北人民制药-40mg)40MGiv20 | canonical_equal | canonical_equal | False | none |  |
| gold_validation_003 | block_07 | 管路护理 | tube_care_single_col_vlm | null | null | null | equal | equal | False | none |  |
| gold_validation_003 | block_07 | 病情观察及处理 | observation_direct_v2 | null | null | null | equal | equal | False | none |  |
| gold_validation_003 | block_08 | 入量_静脉用药 | iv_v4_preserve_case_clean2x | 5%GS40ml+去甲肾上腺素20mgiv微泵维持 | 5%GS40ml+去甲肾上腺素20mgiv微泵维持 | 5%GS40ml+去甲肾上腺素20mgiv微泵维持 | equal | equal | False | none |  |
| gold_validation_003 | block_08 | 管路护理 | tube_care_single_col_vlm | null | null | null | equal | equal | False | none |  |
| gold_validation_003 | block_08 | 病情观察及处理 | observation_direct_v2 | 去甲肾上腺素组液泵毕，遵医嘱续用15ml/h。 | 去甲肾上腺素组液泵毕，遵医嘱续用15ml/h。 | 去甲肾上腺素组液泵毕，遵医嘱续用15ml/h。 | equal | equal | False | none |  |
| gold_validation_003 | block_09 | 入量_静脉用药 | iv_v4_preserve_case_clean2x | 氯化钠注射液(丰原-100ml:0.9%,直立式软袋双阀)100ML+注射用盐酸万古霉素(礼来-0.5g)0.50Giv.gtt100 | 氯化钠注射液(丰原-100ml:0.9%,直立式软袋双阀)100ML+注射用盐酸万古霉素(礼来-0.5g)0.50Giv.gtt100 | 氯化钠注射液(丰原-100ml:0.9%,直立式软袋双阀)100ML+注射用盐酸万古霉素(礼来-0.5g)0.50Giv.gtt100 | equal | equal | False | none |  |
| gold_validation_003 | block_09 | 管路护理 | tube_care_single_col_vlm | null | null | null | equal | equal | False | none |  |
| gold_validation_003 | block_09 | 病情观察及处理 | observation_direct_v2 | null | null | null | equal | equal | False | none |  |
| gold_validation_003 | block_10 | 入量_静脉用药 | iv_v4_preserve_case_clean2x | null | null | null | equal | equal | False | none |  |
| gold_validation_003 | block_10 | 管路护理 | tube_care_single_col_vlm | null | null | null | equal | equal | False | none |  |
| gold_validation_003 | block_10 | 病情观察及处理 | observation_direct_v2 | null | null | null | equal | equal | False | none |  |
| gold_validation_003 | block_11 | 入量_静脉用药 | iv_v4_preserve_case_clean2x | 白蛋白50mliv.gtt50 | 白蛋白50mliv.gtt50 | 白蛋白50mliv.gtt50 | equal | equal | False | none |  |
| gold_validation_003 | block_11 | 管路护理 | tube_care_single_col_vlm | null | null | null | equal | equal | False | none |  |
| gold_validation_003 | block_11 | 病情观察及处理 | observation_direct_v2 | null | null | null | equal | equal | False | none |  |
| gold_validation_003 | block_12 | 入量_静脉用药 | iv_v4_preserve_case_clean2x | 白蛋白50mliv.gtt50 | 白蛋白50mliv.gtt50 | 白蛋白50mliv.gtt50 | equal | equal | False | none |  |
| gold_validation_003 | block_12 | 管路护理 | tube_care_single_col_vlm | null | null | null | equal | equal | False | none |  |
| gold_validation_003 | block_12 | 病情观察及处理 | observation_direct_v2 | null | null | null | equal | equal | False | none |  |
| gold_validation_003 | block_13 | 入量_静脉用药 | iv_v4_preserve_case_clean2x | NS100ml+异甘草酸镁200mgiv.gtt100;葡萄糖注射液（丰原-100ml：5%，直立式软袋双阀）60min+去乙酰毛花苷注射液（成都倍特-0.4mg：2ml）0.40MGiv微泵维持 | NS100ml+异甘草酸镁200mgiv.gtt100;葡萄糖注射液(丰原-100ml:5%,直立式软袋双阀)60ml+去乙酰毛花苷注射液(成都倍特-0.4mg:2ml)0.40MGiv微泵;维持 | NS100ml+异甘草酸镁200mgiv.gtt100;葡萄糖注射液(丰原-100ml:5%, 直立式软袋双阀)60min+去乙酰毛花苷注射液(成都倍特-0.4mg:2ml)0.40MGiv微泵维持 | true_char_mismatch | canonical_equal | False | none |  |
| gold_validation_003 | block_13 | 管路护理 | tube_care_single_col_vlm | null | null | null | equal | equal | False | none |  |
| gold_validation_003 | block_13 | 病情观察及处理 | observation_direct_v2 | 遵医嘱予西地兰组液静推1h。 | 遵医嘱予西地兰组液静推1h。 | 遵医嘱予西地兰组液静推1h。 | equal | equal | False | none |  |
| gold_validation_003 | block_14 | 入量_静脉用药 | iv_v4_preserve_case_clean2x | 氯化钠注射液(丰原-100ml:0.9%,直立式软袋双阀)40ML+苯磺顺阿曲库铵注 | 氯化钠注射液(丰原-100ml:0.9%,直立式软袋双阀)40ML+苯磺顺阿曲库铵注 | 氯化钠注射液(丰原-100ml:0.9%,直立式软袋双阀)40ML+苯磺顺阿曲库铵注 | equal | equal | True | none | 静脉用药内容在两行中截断，第二行以'注'结尾，未完整显示药物名称，无法判断是否为完整药物项或是否需续行合并，存在截断风险。 |
| gold_validation_003 | block_14 | 管路护理 | tube_care_single_col_vlm | null | null | null | equal | equal | False | none |  |
| gold_validation_003 | block_14 | 病情观察及处理 | observation_direct_v2 | 遵医嘱予阿曲库铵组液5ml/h泵入。 | 遵医嘱予阿曲库铵组液5ml/h泵入。 | 遵医嘱予阿曲库铵组液5ml/h泵入。 | equal | equal | False | none |  |
