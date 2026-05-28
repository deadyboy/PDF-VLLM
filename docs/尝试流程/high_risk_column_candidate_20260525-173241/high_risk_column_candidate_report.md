# High Risk Column Candidate Report

## Summary

| field | total | main_correct | candidate_correct | propose_override | needs_review | possible_overfill_review | main_correct_candidate_wrong |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 管路护理 | 57 | 53 | 56 | 2 | 1 | 0 | 0 |
| 入量_静脉用药 | 57 | 47 | 55 | 8 | 0 | 0 | 0 |

## Candidates

| page | block_id | field | gold | main_value | candidate_value | candidate_source | main_eval_kind | candidate_eval_kind | needs_review | decision | reason |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| gold_smoke_001 | block_00 | 管路护理 | 鼻胃管/是/墨绿色// | 鼻胃管/是/墨绿色/ | 鼻胃管/是/墨绿色// | tube_col_vlm | substantive_mismatch | equal | False | propose_override | tube_col_matches_shadow |
| gold_smoke_001 | block_00 | 入量_静脉用药 | 钠钾镁钙葡萄糖注射液250mliv.gtt250 | 钠钾镁钙葡萄糖注射液250mliv.gtt | 钠钾镁钙葡萄糖注射液250mliv.gtt250 | iv_clean2x_v4 | true_char_mismatch | equal | False | propose_override | iv_candidate_correct_without_review |
| gold_smoke_001 | block_01 | 管路护理 | null | null | null | tube_col_vlm | equal | equal | False | keep_main | main_candidate_same |
| gold_smoke_001 | block_01 | 入量_静脉用药 | null | null | null | iv_clean2x_v4 | equal | equal | False | keep_main | main_candidate_same |
| gold_smoke_001 | block_02 | 管路护理 | null | null | null | tube_col_vlm | equal | equal | False | keep_main | main_candidate_same |
| gold_smoke_001 | block_02 | 入量_静脉用药 | 氯化钠注射液(丰原-100ml：0.9%，软袋双阀)续用12ml/h+咪达唑仑注射液（苏恩华-5mg：1ml)50MGiv微泵维持 | 氯化钠注射液(丰原-100ml:0.9%,软袋双阀)续用12ml/hr+咪达唑仑注射液(苏恩华-5mg:1ml)50MGiv微泵维持 | 氯化钠注射液(丰原-100ml:0.9%,软袋双阀)续用12ml/h+咪达唑仑注射液(苏恩华-5mg:1ml)50MGiv微泵维持 | iv_clean2x_v4 | true_char_mismatch | canonical_equal | False | propose_override | iv_candidate_correct_without_review |
| gold_smoke_001 | block_03 | 管路护理 | null | null | null | tube_col_vlm | equal | equal | False | keep_main | main_candidate_same |
| gold_smoke_001 | block_03 | 入量_静脉用药 | 速尿20mgiv0 | 速尿20mgiv0 | 速尿20mgiv0 | iv_clean2x_v4 | equal | equal | False | keep_main | main_candidate_same |
| gold_smoke_001 | block_04 | 管路护理 | 颈内深静脉导管/是///;气管插管/是///23;导尿管/是///;桡动脉导管/是///;静脉留置针/是///;鼻胃管/是///;锁骨下深静脉导管/是///15;股静脉导管/是///43 | 颈内深静脉导管/是///;气管插管/是///23;导尿管/是///;桡动脉导管/是///;静脉留置针/是///;鼻胃管/是///;锁骨下深静脉导管/是///15;股静脉导管/是///;43 | 颈内深静脉导管/是///；气管插管/是///23；导尿管/是///；桡动脉导管/是///；静脉留置针/是///；鼻胃管/是///；锁骨下深静脉导管/是///15；股静脉导管/是///43 | tube_col_vlm | separator_error | canonical_equal | True | needs_review | tube_shadow_missing_or_needs_review |
| gold_smoke_001 | block_04 | 入量_静脉用药 | 钠钾镁钙葡萄糖注射液250mliv.gtt250 | 钠钾镁钙葡萄糖注射液250mliv.gtt;250 | 钠钾镁钙葡萄糖注射液250mliv.gtt250 | iv_clean2x_v4 | separator_error | equal | False | propose_override | iv_candidate_correct_without_review |
| gold_smoke_001 | block_05 | 管路护理 | null | null | null | tube_col_vlm | equal | equal | False | keep_main | main_candidate_same |
| gold_smoke_001 | block_05 | 入量_静脉用药 | 莫西沙星250mliv.gtt250 | 莫西沙星250mliv.gtt250 | 莫西沙星250mliv.gtt250 | iv_clean2x_v4 | equal | equal | False | keep_main | main_candidate_same |
| gold_smoke_001 | block_06 | 管路护理 | null | null | null | tube_col_vlm | equal | equal | False | keep_main | main_candidate_same |
| gold_smoke_001 | block_06 | 入量_静脉用药 | 白蛋白10giv.gtt0 | 白蛋白10giv.gtt0 | 白蛋白10giv.gtt0 | iv_clean2x_v4 | equal | equal | False | keep_main | main_candidate_same |
| gold_smoke_001 | block_07 | 管路护理 | null | null | null | tube_col_vlm | equal | equal | False | keep_main | main_candidate_same |
| gold_smoke_001 | block_07 | 入量_静脉用药 | null | null | null | iv_clean2x_v4 | equal | equal | False | keep_main | main_candidate_same |
| gold_smoke_001 | block_08 | 管路护理 | null | null | null | tube_col_vlm | equal | equal | False | keep_main | main_candidate_same |
| gold_smoke_001 | block_08 | 入量_静脉用药 | null | null | null | iv_clean2x_v4 | equal | equal | False | keep_main | main_candidate_same |
| gold_smoke_001 | block_09 | 管路护理 | null | null | null | tube_col_vlm | equal | equal | False | keep_main | main_candidate_same |
| gold_smoke_001 | block_09 | 入量_静脉用药 | 5%GS100ml+葡萄糖酸钙20MLiv.gtt120 | 5%GS100ml+葡萄糖酸钙20MLiv.gtt120 | 5%GS100ml+葡萄糖酸钙20MLiv.gtt120 | iv_clean2x_v4 | equal | equal | False | keep_main | main_candidate_same |
| gold_smoke_001 | block_10 | 管路护理 | null | null | null | tube_col_vlm | equal | equal | False | keep_main | main_candidate_same |
| gold_smoke_001 | block_10 | 入量_静脉用药 | NS100ml+泰能2giv.gtt100 | NS100ml+泰能2giv.gtt100 | NS100ml+泰能2giv.gtt100 | iv_clean2x_v4 | equal | equal | False | keep_main | main_candidate_same |
| gold_smoke_001 | block_11 | 管路护理 | null | null | null | tube_col_vlm | equal | equal | False | keep_main | main_candidate_same |
| gold_smoke_001 | block_11 | 入量_静脉用药 | NS50ml+肝素0.5支iv微泵维持 | NS50ml+肝素0.5支iv微泵维持 | NS50ml+肝素0.5支iv微泵维持 | iv_clean2x_v4 | equal | equal | False | keep_main | main_candidate_same |
| gold_smoke_001 | block_12 | 管路护理 | null | null | null | tube_col_vlm | equal | equal | False | keep_main | main_candidate_same |
| gold_smoke_001 | block_12 | 入量_静脉用药 | NS100ml+甲泼尼龙琥珀酸钠80mgiv.gtt100;咪达唑仑注射液（苏恩华-5mg：1ml）50MG+氯化钠注射液（丰原-100ml：0.9%，软袋双阀）45MLiv微泵维持 | NS100ml+甲泼尼龙琥珀酸钠80mgiv.gt;咪达唑仑注射液（苏恩华-5mg:1ml）50M;G+氯化钠注射液（丰原-100ml:0.9%，软袋双阀）45MLiv微泵维持 | NS100ml+甲泼尼龙琥珀酸钠80mgiv.gtt100;咪达唑仑注射液(苏恩华-5mg:1ml)50MG+氯化钠注射液(丰原-100ml:0.9%,软袋双阀)45MLiv微泵维持 | iv_clean2x_v4 | true_char_mismatch | canonical_equal | False | propose_override | iv_candidate_correct_without_review |
| gold_smoke_001 | block_13 | 管路护理 | null | null | null | tube_col_vlm | equal | equal | False | keep_main | main_candidate_same |
| gold_smoke_001 | block_13 | 入量_静脉用药 | NS100ml+泮托拉唑40mgiv.gtt100 | NS100ml+泮托拉唑40mgiv.gtt100 | NS100ml+泮托拉唑40mgiv.gtt100 | iv_clean2x_v4 | equal | equal | False | keep_main | main_candidate_same |
| gold_smoke_001 | block_14 | 管路护理 | null | null | null | tube_col_vlm | equal | equal | False | keep_main | main_candidate_same |
| gold_smoke_001 | block_14 | 入量_静脉用药 | 枸橼酸舒芬太尼注射液(鄂宜昌人福-50ug:1ml)200UG+氯化钠注射液(丰原,-100ml:0.9%软袋双阀)50MLiv微泵维持 | 枸橼酸舒芬太尼注射液（鄂宜昌人福-50ug:1ml）200UG+氯化钠注射液（丰原-100ml:0.9%,软袋双阀）50MLiv微泵维持 | 枸橼酸舒芬太尼注射液(鄂宜昌人福-50ug:1ml)200UG+氯化钠注射液(丰原-100ml:0.9%,软袋双阀)50MLiv微泵维持 | iv_clean2x_v4 | true_char_mismatch | true_char_mismatch | False | keep_main | main_candidate_same |
| gold_smoke_001 | block_15 | 管路护理 | null | null | null | tube_col_vlm | equal | equal | False | keep_main | main_candidate_same |
| gold_smoke_001 | block_15 | 入量_静脉用药 | null | null | null | iv_clean2x_v4 | equal | equal | False | keep_main | main_candidate_same |
| gold_smoke_001 | block_16 | 管路护理 | null | null | null | tube_col_vlm | equal | equal | False | keep_main | main_candidate_same |
| gold_smoke_001 | block_16 | 入量_静脉用药 | 氯化钠注射液(丰原-100ml：0.9%，软袋双阀)48ML+盐酸右美托咪定注射液（辰欣药业-0.2mg：2ml）0.4MGiv微泵维持 | 氯化钠注射液(丰原-100ml:0.9%,软袋双阀)48L+盐酸右美托咪定注射液(辰欣药业-0.2mg:2ml)0.4MGiv微泵维持 | 氯化钠注射液(丰原-100ml:0.9%,软袋双阀)48ML+盐酸右美托咪定注射液(辰欣药业-0.2mg:2ml)0.4MGiv微泵维持 | iv_clean2x_v4 | true_char_mismatch | canonical_equal | False | propose_override | iv_candidate_correct_without_review |
| gold_smoke_001 | block_17 | 管路护理 | null | null | null | tube_col_vlm | equal | equal | False | keep_main | main_candidate_same |
| gold_smoke_001 | block_17 | 入量_静脉用药 | NS100ml+泰能2giv.gtt100 | NS100ml+泰能2giv.gtt100 | NS100ml+泰能2giv.gtt100 | iv_clean2x_v4 | equal | equal | False | keep_main | main_candidate_same |
| gold_dev_m_002 | block_00 | 管路护理 | null | null | null | tube_col_vlm | equal | equal | False | keep_main | main_candidate_same |
| gold_dev_m_002 | block_00 | 入量_静脉用药 | 白蛋白10giv.gtt50;NS50ml+肝素0.5支iv微泵维持 | 白蛋白10giv.gtt50;NS50ml+肝素0.5支iv微泵维持 | 白蛋白10giv.gtt50;NS50ml+肝素0.5支iv微泵维持 | iv_clean2x_v4 | equal | equal | False | keep_main | main_candidate_same |
| gold_dev_m_002 | block_01 | 管路护理 | null | null | null | tube_col_vlm | equal | equal | False | keep_main | main_candidate_same |
| gold_dev_m_002 | block_01 | 入量_静脉用药 | NS50ml+力月西50mgiv微泵维持 | NS50ml+力月西50mgiv微泵维持 | NS50ml+力月西50mgiv微泵维持 | iv_clean2x_v4 | equal | equal | False | keep_main | main_candidate_same |
| gold_dev_m_002 | block_02 | 管路护理 | null | null | null | tube_col_vlm | equal | equal | False | keep_main | main_candidate_same |
| gold_dev_m_002 | block_02 | 入量_静脉用药 | 氯化钠注射液(丰原-100ml：0.9%，软袋双阀)100ML+克林霉素磷酸酯注射液(鲁方明-0.3g:2ml)0.60Giv.gtt100 | 氯化钠注射液(丰原-100ml:0.9%软袋双阀)100ML+克林霉素磷酸酯注射液(鲁方明-0.3g:2ml)0.60Giv.gtt100 | 氯化钠注射液(丰原-100ml:0.9%,软袋双阀)100ML+克林霉素磷酸酯注射液(鲁方明-0.3g:2ml)0.60Giv.gtt100 | iv_clean2x_v4 | true_char_mismatch | canonical_equal | False | propose_override | iv_candidate_correct_without_review |
| gold_dev_m_002 | block_03 | 管路护理 | null | null | null | tube_col_vlm | equal | equal | False | keep_main | main_candidate_same |
| gold_dev_m_002 | block_03 | 入量_静脉用药 | null | null | null | iv_clean2x_v4 | equal | equal | False | keep_main | main_candidate_same |
| gold_dev_m_002 | block_04 | 管路护理 | null | null | null | tube_col_vlm | equal | equal | False | keep_main | main_candidate_same |
| gold_dev_m_002 | block_04 | 入量_静脉用药 | 枸橼酸舒芬太尼注射液(鄂宜昌人福-50ug:1ml)12h+氯化钠注射液(丰原-100ml:0.9%,软袋双阀)50MLiv微泵维持 | 枸橼酸舒芬太尼注射液（鄂宜昌人福-50ug:1ml）12h+氯化钠注射液（丰原-100ml:0.9%，软袋双阀）50MLiv微泵维持 | 枸橼酸舒芬太尼注射液(鄂宜昌人福-50ug:1ml)12h+氯化钠注射液(丰原-100ml:0.9%,软袋双阀)50MLiv微泵维持 | iv_clean2x_v4 | canonical_equal | equal | False | keep_main | main_candidate_same |
| gold_dev_m_002 | block_05 | 管路护理 | 气管插管/是///23;锁骨下深静脉导管/是///15;股静脉导管/是///43;颈内深静脉导管/是///;鼻胃管/是///55;导尿管/是/黄色//;桡动脉导管/是///;静脉留置针/是/// | 气管插管/是///23;锁骨下深静脉导管/是///15;股静脉导管/是///43;颈内深静脉导管/是///;鼻胃管/是///55;导尿管/是/黄色//;桡动脉导管/是///;静脉留置针/是/// | 气管插管/是///23;锁骨下深静脉导管/是///15;股静脉导管/是///43;颈内深静脉导管/是///;鼻胃管/是///55;导尿管/是/黄色//;桡动脉导管/是///;静脉留置针/是/// | tube_col_vlm | equal | equal | False | keep_main | main_candidate_same |
| gold_dev_m_002 | block_05 | 入量_静脉用药 | null | null | null | iv_clean2x_v4 | equal | equal | False | keep_main | main_candidate_same |
| gold_dev_m_002 | block_06 | 管路护理 | null | null | null | tube_col_vlm | equal | equal | False | keep_main | main_candidate_same |
| gold_dev_m_002 | block_06 | 入量_静脉用药 | null | null | null | iv_clean2x_v4 | equal | equal | False | keep_main | main_candidate_same |
| gold_dev_m_002 | block_07 | 管路护理 | null | null | null | tube_col_vlm | equal | equal | False | keep_main | main_candidate_same |
| gold_dev_m_002 | block_07 | 入量_静脉用药 | NS50ml+力月西50mgiv微泵维持 | NS50ml+力月西50mgiv微泵维持 | NS50ml+力月西50mgiv微泵维持 | iv_clean2x_v4 | equal | equal | False | keep_main | main_candidate_same |
| gold_dev_m_002 | block_08 | 管路护理 | null | null | null | tube_col_vlm | equal | equal | False | keep_main | main_candidate_same |
| gold_dev_m_002 | block_08 | 入量_静脉用药 | null | null | null | iv_clean2x_v4 | equal | equal | False | keep_main | main_candidate_same |
| gold_dev_m_002 | block_09 | 管路护理 | null | null | null | tube_col_vlm | equal | equal | False | keep_main | main_candidate_same |
| gold_dev_m_002 | block_09 | 入量_静脉用药 | NS50ml+胰岛素50uiv微泵维持 | NS50ml+胰岛素50uiv微泵维持 | NS50ml+胰岛素50uiv微泵维持 | iv_clean2x_v4 | equal | equal | False | keep_main | main_candidate_same |
| gold_dev_m_002 | block_10 | 管路护理 | null | null | null | tube_col_vlm | equal | equal | False | keep_main | main_candidate_same |
| gold_dev_m_002 | block_10 | 入量_静脉用药 | NS50ml+肝素0.5支iv微泵维持 | NS50ml+肝素0.5支iv微泵维持 | NS50ml+肝素0.5支iv微泵维持 | iv_clean2x_v4 | equal | equal | False | keep_main | main_candidate_same |
| gold_dev_m_002 | block_11 | 管路护理 | null | null | null | tube_col_vlm | equal | equal | False | keep_main | main_candidate_same |
| gold_dev_m_002 | block_11 | 入量_静脉用药 | NS100ml+泰能2giv.gtt100 | NS100ml+泰能2giv.gtt100 | NS100ml+泰能2giv.gtt100 | iv_clean2x_v4 | equal | equal | False | keep_main | main_candidate_same |
| gold_dev_m_002 | block_12 | 管路护理 | null | null | null | tube_col_vlm | equal | equal | False | keep_main | main_candidate_same |
| gold_dev_m_002 | block_12 | 入量_静脉用药 | null | null | null | iv_clean2x_v4 | equal | equal | False | keep_main | main_candidate_same |
| gold_dev_m_002 | block_13 | 管路护理 | null | null | null | tube_col_vlm | equal | equal | False | keep_main | main_candidate_same |
| gold_dev_m_002 | block_13 | 入量_静脉用药 | null | null | null | iv_clean2x_v4 | equal | equal | False | keep_main | main_candidate_same |
| gold_dev_m_002 | block_14 | 管路护理 | null | null | null | tube_col_vlm | equal | equal | False | keep_main | main_candidate_same |
| gold_dev_m_002 | block_14 | 入量_静脉用药 | NS50ml+力月西50mgiv微泵维持 | NS50ml+力月西50mgiv微泵维持 | NS50ml+力月西50mgiv微泵维持 | iv_clean2x_v4 | equal | equal | False | keep_main | main_candidate_same |
| gold_dev_m_002 | block_15 | 管路护理 | null | null | null | tube_col_vlm | equal | equal | False | keep_main | main_candidate_same |
| gold_dev_m_002 | block_15 | 入量_静脉用药 | 氯化钠注射液（丰原-100ml：0.9%，软袋,双阀）100ML+克林霉素磷酸酯注射液（鲁方明-0.3g:2ml)0.6Giv.gtt100 | 氯化钠注射液(丰原-100ml:0.9%,软袋双阀)100ML+克林霉素磷酸酯注射液(鲁方明-0.3g:2ml)0.6Giv.gtt100 | 氯化钠注射液(丰原-100ml:0.9%,软袋双阀)100ML+克林霉素磷酸酯注射液(鲁方明-0.3g:2ml)0.6Giv.gtt100 | iv_clean2x_v4 | manufacturer_punctuation_equal | manufacturer_punctuation_equal | False | keep_main | main_candidate_same |
| gold_dev_m_002 | block_16 | 管路护理 | null | null | null | tube_col_vlm | equal | equal | False | keep_main | main_candidate_same |
| gold_dev_m_002 | block_16 | 入量_静脉用药 | null | null | null | iv_clean2x_v4 | equal | equal | False | keep_main | main_candidate_same |
| gold_dev_m_002 | block_17 | 管路护理 | null | null | null | tube_col_vlm | equal | equal | False | keep_main | main_candidate_same |
| gold_dev_m_002 | block_17 | 入量_静脉用药 | null | null | null | iv_clean2x_v4 | equal | equal | False | keep_main | main_candidate_same |
| gold_dev_m_002 | block_18 | 管路护理 | null | null | null | tube_col_vlm | equal | equal | False | keep_main | main_candidate_same |
| gold_dev_m_002 | block_18 | 入量_静脉用药 | null | null | null | iv_clean2x_v4 | equal | equal | False | keep_main | main_candidate_same |
| gold_dev_m_002 | block_19 | 管路护理 | null | null | null | tube_col_vlm | equal | equal | False | keep_main | main_candidate_same |
| gold_dev_m_002 | block_19 | 入量_静脉用药 | NS50ml+力月西50mgiv微泵维持 | NS50ml+力月西50mgiv微泵维持 | NS50ml+力月西50mgiv微泵维持 | iv_clean2x_v4 | equal | equal | False | keep_main | main_candidate_same |
| gold_dev_m_002 | block_20 | 管路护理 | null | null | null | tube_col_vlm | equal | equal | False | keep_main | main_candidate_same |
| gold_dev_m_002 | block_20 | 入量_静脉用药 | null | null | null | iv_clean2x_v4 | equal | equal | False | keep_main | main_candidate_same |
| gold_dev_m_002 | block_21 | 管路护理 | null | null | null | tube_col_vlm | equal | equal | False | keep_main | main_candidate_same |
| gold_dev_m_002 | block_21 | 入量_静脉用药 | NS50ml+肝素0.5支iv微泵维持 | NS50ml+肝素0.5支iv微泵维持 | NS50ml+肝素0.5支iv微泵维持 | iv_clean2x_v4 | equal | equal | False | keep_main | main_candidate_same |
| gold_dev_m_002 | block_22 | 管路护理 | null | null | null | tube_col_vlm | equal | equal | False | keep_main | main_candidate_same |
| gold_dev_m_002 | block_22 | 入量_静脉用药 | null | null | null | iv_clean2x_v4 | equal | equal | False | keep_main | main_candidate_same |
| gold_dev_m_002 | block_23 | 管路护理 | 桡动脉导管/是///;锁骨下深静脉导管/是/// | 桡动脉导管/是///;锁骨下深静脉导管/是/// | 桡动脉导管/是///;锁骨下深静脉导管/是/// | tube_col_vlm | equal | equal | False | keep_main | main_candidate_same |
| gold_dev_m_002 | block_23 | 入量_静脉用药 | NS100ml+泰能2giv.gtt100;枸橼酸舒芬太尼注射液（鄂宜昌人福-50ug：1ml）4ml/l+氯化钠注射液（丰原-100ml：0.9%，软袋双阀）46MLiv微泵维 | NS100ml+泰能2giv.gtt100;枸橼酸舒芬太尼注射液（鄂宜昌人福-50ug:1ml)4ml/1+氯化钠注射液（丰原-100ml:0.9%,软袋双阀）46MLiv微泵维 | NS100ml+泰能2giv.gtt100;枸橼酸舒芬太尼注射液(鄂宜昌人福-50ug:1ml)4ml/1+氯化钠注射液(丰原-100ml:0.9%,软袋双阀)46MLiv微泵维 | iv_clean2x_v4 | true_char_mismatch | true_char_mismatch | False | keep_main | main_candidate_same |
| gold_validation_003 | block_00 | 管路护理 | null | null | null | tube_col_vlm | equal | equal | False | keep_main | main_candidate_same |
| gold_validation_003 | block_00 | 入量_静脉用药 | null | null | null | iv_clean2x_v4 | equal | equal | False | keep_main | main_candidate_same |
| gold_validation_003 | block_01 | 管路护理 | 鼻胃管/是/咖啡色//55 | 鼻胃管/是/咖啡色/55 | 鼻胃管/是/咖啡色//55 | tube_col_vlm | substantive_mismatch | equal | False | propose_override | tube_col_matches_shadow |
| gold_validation_003 | block_01 | 入量_静脉用药 | 0.9%NS50ml+胰岛素注射液50uiv微泵维持(暂停使用余量43ml) | 0.9%NS50ml+胰岛素注射液50uiv微泵维持（暂停使用余量43ml） | 0.9%NS50ml+胰岛素注射液50uiv微泵维持（暂停使用余量43ml） | iv_clean2x_v4 | canonical_equal | canonical_equal | False | keep_main | main_candidate_same |
| gold_validation_003 | block_02 | 管路护理 | null | null | null | tube_col_vlm | equal | equal | False | keep_main | main_candidate_same |
| gold_validation_003 | block_02 | 入量_静脉用药 | null | null | null | iv_clean2x_v4 | equal | equal | False | keep_main | main_candidate_same |
| gold_validation_003 | block_03 | 管路护理 | 导尿管/是/黄褐色/;股静脉导管/是///;鼻胃管/是/暗红色//55;股静脉导管/是///20;鼻肠管/是///100;颈内深静脉导管/是///13;气管插管/是///23;颈静脉导管/是/// | 导尿管/是/黄褐色//;股静脉导管/是///;鼻胃管/是/暗红色//55;股静脉导管/是///20;鼻肠管/是///100;颈内深静脉导管/是///13;气管插管/是///23;颈静脉导管/是/// | 导尿管/是/黄褐色//;股静脉导管/是///;鼻胃管/是/暗红色//55;股静脉导管/是///20;鼻肠管/是///100;颈内深静脉导管/是///13;气管插管/是///23;颈静脉导管/是/// | tube_col_vlm | substantive_mismatch | substantive_mismatch | False | keep_main | main_candidate_same |
| gold_validation_003 | block_03 | 入量_静脉用药 | null | null | null | iv_clean2x_v4 | equal | equal | False | keep_main | main_candidate_same |
| gold_validation_003 | block_04 | 管路护理 | null | null | null | tube_col_vlm | equal | equal | False | keep_main | main_candidate_same |
| gold_validation_003 | block_04 | 入量_静脉用药 | 白蛋白50mliv.gtt50;氯化钠注射液(丰原-100ml：0.9%，直立式软袋双阀)40ML+咪达唑仑注射液(苏恩华-5mg：1ml)50MGiv微泵维持 | 白蛋白50mliv.gtt50;氯化钠注射液(丰原-100ml:0.9%,直立式软袋双阀)40ML+咪达唑仑注射液(苏恩华-5mg:1ml)50MGiv微泵维持 | 白蛋白50mliv.gtt50;氯化钠注射液(丰原-100ml:0.9%,直立式软袋双阀)40ML+咪达唑仑注射液(苏恩华-5mg:1ml)50MGiv微泵维持 | iv_clean2x_v4 | canonical_equal | canonical_equal | False | keep_main | main_candidate_same |
| gold_validation_003 | block_05 | 管路护理 | null | null | null | tube_col_vlm | equal | equal | False | keep_main | main_candidate_same |
| gold_validation_003 | block_05 | 入量_静脉用药 | NS50ml+盐酸瑞芬太尼4mgiv微泵维持 | NS50ml+盐酸瑞芬太尼4mgiv微泵维持 | NS50ml+盐酸瑞芬太尼4mgiv微泵维持 | iv_clean2x_v4 | equal | equal | False | keep_main | main_candidate_same |
| gold_validation_003 | block_06 | 管路护理 | null | null | null | tube_col_vlm | equal | equal | False | keep_main | main_candidate_same |
| gold_validation_003 | block_06 | 入量_静脉用药 | NS100ml+亚胺培南西司他丁钠1giv.gtt100 | NS100ml+亚胺培南西司他丁钠1giv.gt | NS100ml+亚胺培南西司他丁钠1giv.gtt100 | iv_clean2x_v4 | true_char_mismatch | equal | False | propose_override | iv_candidate_correct_without_review |
| gold_validation_003 | block_07 | 管路护理 | null | null | null | tube_col_vlm | equal | equal | False | keep_main | main_candidate_same |
| gold_validation_003 | block_07 | 入量_静脉用药 | NS20ml+氨溴索30mgiv20;氯化钠注射液(丰原-100ml：0.9%，直立式软袋双阀)20ML+注射用艾司奥美拉唑钠(湖北人民制药-40mg)40MGiv20 | NS20ml+氨溴索30mgiv20;氯化钠注射液(丰原-100ml:0.9%,直立式软袋双阀)20ML+注射用艾司奥美拉唑钠(湖北人民制药-40mg)40MGiv20 | NS20ml+氨溴索30mgiv20;氯化钠注射液(丰原-100ml:0.9%,直立式软袋双阀)20ML+注射用艾司奥美拉唑钠(湖北人民制药-40mg)40MGiv20 | iv_clean2x_v4 | canonical_equal | canonical_equal | False | keep_main | main_candidate_same |
| gold_validation_003 | block_08 | 管路护理 | null | null | null | tube_col_vlm | equal | equal | False | keep_main | main_candidate_same |
| gold_validation_003 | block_08 | 入量_静脉用药 | 5%GS40ml+去甲肾上腺素20mgiv微泵维持 | 5%GS40ml+去甲肾上腺素20mgiv微泵维持 | 5%GS40ml+去甲肾上腺素20mgiv微泵维持 | iv_clean2x_v4 | equal | equal | False | keep_main | main_candidate_same |
| gold_validation_003 | block_09 | 管路护理 | null | null | null | tube_col_vlm | equal | equal | False | keep_main | main_candidate_same |
| gold_validation_003 | block_09 | 入量_静脉用药 | 氯化钠注射液(丰原-100ml:0.9%,直立式软袋双阀)100ML+注射用盐酸万古霉素(礼来-0.5g)0.50Giv.gtt100 | 氯化钠注射液(丰原-100ml:0.9%,直立式软袋双阀)100ML+注射用盐酸万古霉素(礼来-0.5g)0.50Giv.gtt100 | 氯化钠注射液(丰原-100ml:0.9%,直立式软袋双阀)100ML+注射用盐酸万古霉素(礼来-0.5g)0.50Giv.gtt100 | iv_clean2x_v4 | equal | equal | False | keep_main | main_candidate_same |
| gold_validation_003 | block_10 | 管路护理 | null | null | null | tube_col_vlm | equal | equal | False | keep_main | main_candidate_same |
| gold_validation_003 | block_10 | 入量_静脉用药 | null | null | null | iv_clean2x_v4 | equal | equal | False | keep_main | main_candidate_same |
| gold_validation_003 | block_11 | 管路护理 | null | null | null | tube_col_vlm | equal | equal | False | keep_main | main_candidate_same |
| gold_validation_003 | block_11 | 入量_静脉用药 | 白蛋白50mliv.gtt50 | 白蛋白50mliv.gtt50 | 白蛋白50mliv.gtt50 | iv_clean2x_v4 | equal | equal | False | keep_main | main_candidate_same |
| gold_validation_003 | block_12 | 管路护理 | null | null | null | tube_col_vlm | equal | equal | False | keep_main | main_candidate_same |
| gold_validation_003 | block_12 | 入量_静脉用药 | 白蛋白50mliv.gtt50 | 白蛋白50mliv.gtt50 | 白蛋白50mliv.gtt50 | iv_clean2x_v4 | equal | equal | False | keep_main | main_candidate_same |
| gold_validation_003 | block_13 | 管路护理 | null | null | null | tube_col_vlm | equal | equal | False | keep_main | main_candidate_same |
| gold_validation_003 | block_13 | 入量_静脉用药 | NS100ml+异甘草酸镁200mgiv.gtt100;葡萄糖注射液（丰原-100ml：5%，直立式软袋双阀）60min+去乙酰毛花苷注射液（成都倍特-0.4mg：2ml）0.40MGiv微泵维持 | NS100ml+异甘草酸镁200mgiv.gtt100;葡萄糖注射液(丰原-100ml:5%,直立式软袋双阀)60ml+去乙酰毛花苷注射液(成都倍特-0.4mg:2ml)0.40MGiv微泵;维持 | NS100ml+异甘草酸镁200mgiv.gtt100;葡萄糖注射液(丰原-100ml:5%, 直立式软袋双阀)60min+去乙酰毛花苷注射液(成都倍特-0.4mg:2ml)0.40MGiv微泵维持 | iv_clean2x_v4 | true_char_mismatch | canonical_equal | False | propose_override | iv_candidate_correct_without_review |
| gold_validation_003 | block_14 | 管路护理 | null | null | null | tube_col_vlm | equal | equal | False | keep_main | main_candidate_same |
| gold_validation_003 | block_14 | 入量_静脉用药 | 氯化钠注射液(丰原-100ml:0.9%,直立式软袋双阀)40ML+苯磺顺阿曲库铵注 | 氯化钠注射液(丰原-100ml:0.9%,直立式软袋双阀)40ML+苯磺顺阿曲库铵注 | 氯化钠注射液(丰原-100ml:0.9%,直立式软袋双阀)40ML+苯磺顺阿曲库铵注 | iv_clean2x_v4 | equal | equal | False | keep_main | main_candidate_same |
