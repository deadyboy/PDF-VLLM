# High Risk Column Enhanced Eval Report

## Page Summary

| page | result_type | strict_total | canonical_only | separator_error | missing | overfill | substantive_mismatch |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| gold_smoke_001 | main | 28 | 0 | 2 | 0 | 0 | 6 |
| gold_smoke_001 | enhanced | 31 | 3 | 1 | 0 | 0 | 1 |
| gold_dev_m_002 | main | 44 | 2 | 0 | 0 | 0 | 2 |
| gold_dev_m_002 | enhanced | 44 | 3 | 0 | 0 | 0 | 1 |
| gold_validation_003 | main | 23 | 3 | 0 | 0 | 0 | 4 |
| gold_validation_003 | enhanced | 25 | 4 | 0 | 0 | 0 | 1 |

## Field Summary

| field | main_correct | enhanced_correct | fixed_by_override | new_errors |
| --- | ---: | ---: | ---: | ---: |
| 管路护理 | 53 | 55 | 2 | 0 |
| 入量_静脉用药 | 47 | 55 | 8 | 0 |

## Overrides

| page | block_id | field | old_value | new_value | candidate_source | reason |
| --- | --- | --- | --- | --- | --- | --- |
| gold_smoke_001 | block_00 | 管路护理 | 鼻胃管/是/墨绿色/ | 鼻胃管/是/墨绿色// | tube_col_vlm | tube_col_matches_shadow |
| gold_smoke_001 | block_00 | 入量_静脉用药 | 钠钾镁钙葡萄糖注射液250mliv.gtt | 钠钾镁钙葡萄糖注射液250mliv.gtt250 | iv_clean2x_v4 | iv_candidate_correct_without_review |
| gold_smoke_001 | block_02 | 入量_静脉用药 | 氯化钠注射液(丰原-100ml:0.9%,软袋双阀)续用12ml/hr+咪达唑仑注射液(苏恩华-5mg:1ml)50MGiv微泵维持 | 氯化钠注射液(丰原-100ml:0.9%,软袋双阀)续用12ml/h+咪达唑仑注射液(苏恩华-5mg:1ml)50MGiv微泵维持 | iv_clean2x_v4 | iv_candidate_correct_without_review |
| gold_smoke_001 | block_04 | 入量_静脉用药 | 钠钾镁钙葡萄糖注射液250mliv.gtt;250 | 钠钾镁钙葡萄糖注射液250mliv.gtt250 | iv_clean2x_v4 | iv_candidate_correct_without_review |
| gold_smoke_001 | block_12 | 入量_静脉用药 | NS100ml+甲泼尼龙琥珀酸钠80mgiv.gt;咪达唑仑注射液（苏恩华-5mg:1ml）50M;G+氯化钠注射液（丰原-100ml:0.9%，软袋双阀）45MLiv微泵维持 | NS100ml+甲泼尼龙琥珀酸钠80mgiv.gtt100;咪达唑仑注射液(苏恩华-5mg:1ml)50MG+氯化钠注射液(丰原-100ml:0.9%,软袋双阀)45MLiv微泵维持 | iv_clean2x_v4 | iv_candidate_correct_without_review |
| gold_smoke_001 | block_16 | 入量_静脉用药 | 氯化钠注射液(丰原-100ml:0.9%,软袋双阀)48L+盐酸右美托咪定注射液(辰欣药业-0.2mg:2ml)0.4MGiv微泵维持 | 氯化钠注射液(丰原-100ml:0.9%,软袋双阀)48ML+盐酸右美托咪定注射液(辰欣药业-0.2mg:2ml)0.4MGiv微泵维持 | iv_clean2x_v4 | iv_candidate_correct_without_review |
| gold_dev_m_002 | block_02 | 入量_静脉用药 | 氯化钠注射液(丰原-100ml:0.9%软袋双阀)100ML+克林霉素磷酸酯注射液(鲁方明-0.3g:2ml)0.60Giv.gtt100 | 氯化钠注射液(丰原-100ml:0.9%,软袋双阀)100ML+克林霉素磷酸酯注射液(鲁方明-0.3g:2ml)0.60Giv.gtt100 | iv_clean2x_v4 | iv_candidate_correct_without_review |
| gold_validation_003 | block_01 | 管路护理 | 鼻胃管/是/咖啡色/55 | 鼻胃管/是/咖啡色//55 | tube_col_vlm | tube_col_matches_shadow |
| gold_validation_003 | block_06 | 入量_静脉用药 | NS100ml+亚胺培南西司他丁钠1giv.gt | NS100ml+亚胺培南西司他丁钠1giv.gtt100 | iv_clean2x_v4 | iv_candidate_correct_without_review |
| gold_validation_003 | block_13 | 入量_静脉用药 | NS100ml+异甘草酸镁200mgiv.gtt100;葡萄糖注射液(丰原-100ml:5%,直立式软袋双阀)60ml+去乙酰毛花苷注射液(成都倍特-0.4mg:2ml)0.40MGiv微泵;维持 | NS100ml+异甘草酸镁200mgiv.gtt100;葡萄糖注射液(丰原-100ml:5%, 直立式软袋双阀)60min+去乙酰毛花苷注射液(成都倍特-0.4mg:2ml)0.40MGiv微泵维持 | iv_clean2x_v4 | iv_candidate_correct_without_review |
