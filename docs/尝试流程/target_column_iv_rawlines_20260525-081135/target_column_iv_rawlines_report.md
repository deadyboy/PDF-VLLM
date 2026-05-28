# Target Column IV Rawlines Report

## Summary

| metric | old_col | iv_v2_rawlines |
| --- | ---: | ---: |
| col_correct | 45 | 50 |
| main_wrong_col_correct | 2 | 6 |
| main_correct_col_wrong | 2 | 1 |
| both_wrong | 10 | 6 |
| col_overfill | 0 | 0 |
| col_missing | 0 | 0 |
| raw_lines_contains_tail_but_final_wrong | 0 | 0 |
| raw_lines_missing_tail | 0 | 7 |

## Details

| page | block_id | gold | main_actual | col_vlm_old | col_vlm_iv_v2_rawlines | main_eval_kind | old_col_eval_kind | iv_v2_eval_kind | raw_lines | needs_review | reason | iv_v2_tail_kind |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| gold_smoke_001 | block_00 | 钠钾镁钙葡萄糖注射液250mliv.gtt250 | 钠钾镁钙葡萄糖注射液250mliv.gtt | 钠钾镁钙葡萄糖注射液250mliv.gtt | 钠钾镁钙葡萄糖注射液250mliv.gtt250 | substantive_mismatch | substantive_mismatch | equal | ["钠钾镁钙葡萄糖注射液250mliv.gtt", "250"] | True | 250是否为续行剂量或新项目不明确，无法判断是否应合并 | none |
| gold_smoke_001 | block_01 | null | null | null | null | equal | equal | equal | [] | False |  | none |
| gold_smoke_001 | block_02 | 氯化钠注射液(丰原-100ml：0.9%，软袋双阀)续用12ml/h+咪达唑仑注射液（苏恩华-5mg：1ml)50MGiv微泵维持 | 氯化钠注射液(丰原-100ml:0.9%,软袋双阀)续用12ml/hr+咪达唑仑注射液(苏恩华-5mg:1ml)50MGiv微泵维持 | 氯化钠注射液(丰原-100ml:0.9%,软袋双阀)续用12ml/hr+咪达唑仑注射液(苏恩华-5mg:1ml)50MGiv微泵维持 | 氯化钠注射液(丰原-100ml:0.9%,软袋双阀)续用12ml/hr+咪达唑仑注射液(苏恩华-5mg:1ml)50MGiv微泵维持 | substantive_mismatch | substantive_mismatch | substantive_mismatch | ["氯化钠注射液(丰原-100ml:0.9%,软袋", "双阀)续用12ml/hr+咪达唑仑注射液(苏", "恩华-5mg:1ml)50MGiv微泵维持"] | False |  | raw_lines_missing_tail |
| gold_smoke_001 | block_03 | 速尿20mgiv0 | 速尿20mgiv0 | 速尿20mgiv0 | 速尿20mgiv0 | equal | equal | equal | ["速尿20mgiv0"] | False |  | none |
| gold_smoke_001 | block_04 | 钠钾镁钙葡萄糖注射液250mliv.gtt250 | 钠钾镁钙葡萄糖注射液250mliv.gtt;250 | 钠钾镁钙葡萄糖注射液250mliv.gtt;250 | 钠钾镁钙葡萄糖注射液250mliv.gtt250 | separator_error | separator_error | equal | ["钠钾镁钙葡萄糖注射液250mliv.gtt", "250"] | False |  | none |
| gold_smoke_001 | block_05 | 莫西沙星250mliv.gtt250 | 莫西沙星250mliv.gtt250 | 莫西沙星250mliv.gtt250 | 莫西沙星250mliv.gtt250 | equal | equal | equal | ["莫西沙星250mliv.gtt250"] | False |  | none |
| gold_smoke_001 | block_06 | 白蛋白10giv.gtt0 | 白蛋白10giv.gtt0 | 白蛋白10giv.gtt0 | 白蛋白10giv.gtt0 | equal | equal | equal | ["白蛋白10giv.gtt0"] | False |  | none |
| gold_smoke_001 | block_07 | null | null | null | null | equal | equal | equal | [] | False |  | none |
| gold_smoke_001 | block_08 | null | null | null | null | equal | equal | equal | [] | False |  | none |
| gold_smoke_001 | block_09 | 5%GS100ml+葡萄糖酸钙20MLiv.gtt120 | 5%GS100ml+葡萄糖酸钙20MLiv.gtt120 | 5%GS100ml+葡萄糖酸钙20MLiv.gtt120 | 5%GS100ml+葡萄糖酸钙20MLiv.gtt120 | equal | equal | equal | ["5%GS100ml+葡萄糖酸钙20MLiv.gtt120"] | False |  | none |
| gold_smoke_001 | block_10 | NS100ml+泰能2giv.gtt100 | NS100ml+泰能2giv.gtt100 | NS100ml+泰能2giv.gtt100 | NS100ml+泰能2giv.gtt100 | equal | equal | equal | ["NS100ml+泰能2giv.gtt100"] | False |  | none |
| gold_smoke_001 | block_11 | NS50ml+肝素0.5支iv微泵维持 | NS50ml+肝素0.5支iv微泵维持 | NS50ml + 肝素0.5支iv微泵维持 | NS50ml + 肝素0.5支iv微泵维持 | equal | canonical_equal | canonical_equal | ["NS50ml + 肝素0.5支iv微泵维持"] | False |  | none |
| gold_smoke_001 | block_12 | NS100ml+甲泼尼龙琥珀酸钠80mgiv.gtt100;咪达唑仑注射液（苏恩华-5mg：1ml）50MG+氯化钠注射液（丰原-100ml：0.9%，软袋双阀）45MLiv微泵维持 | NS100ml+甲泼尼龙琥珀酸钠80mgiv.gt;咪达唑仑注射液（苏恩华-5mg:1ml）50M;G+氯化钠注射液（丰原-100ml:0.9%，软袋双阀）45MLiv微泵维持 | NS100ml+甲泼尼龙琥珀酸钠80mgiv.gt t100;咪达唑仑注射液(苏思华-5mg:1ml)50M;G+氯化钠注射液(丰原-100ml:0.9%,软袋双阀)45MLiv微泵维持 | NS100ml+甲泼尼龙琥珀酸钠80mgiv.gtt100;咪达唑仑注射液(苏思华-5mg:1ml)50M;G+氯化钠注射液(丰原-100ml:0.9%,软袋双阀)45MLiv微泵维持 | substantive_mismatch | substantive_mismatch | substantive_mismatch | ["NS100ml+甲泼尼龙琥珀酸钠80mgiv.gt", "t100", "咪达唑仑注射液(苏思华-5mg:1ml)50M", "G+氯化钠注射液(丰原-100ml:0.9%,软", "袋双阀)45MLiv微泵维持"] | False |  | raw_lines_missing_tail |
| gold_smoke_001 | block_13 | NS100ml+泮托拉唑40mgiv.gtt100 | NS100ml+泮托拉唑40mgiv.gtt100 | NS100ml+泮托拉唑40mgiv.gtt100 | NS100ml+泮托拉唑40mgiv.gtt100 | equal | equal | equal | ["NS100ml+泮托拉唑40mgiv.gtt100"] | False |  | none |
| gold_smoke_001 | block_14 | 枸橼酸舒芬太尼注射液(鄂宜昌人福,-50ug:1ml)200UG+氯化钠注射液(丰原,-100ml:0.9%,软袋双阀)50MLiv微泵维持 | 枸橼酸舒芬太尼注射液（鄂宜昌人福-50ug:1ml）200UG+氯化钠注射液（丰原-100ml:0.9%,软袋双阀）50MLiv微泵维持 | 枸橼酸舒芬太尼注射液(鄂宜昌人福-50ug:1ml)2000g+氯化钠注射液(丰原-100ml:0.9%,软袋双阀)50ML.iv微泵维持 | 枸橼酸舒芬太尼注射液(鄂宜昌人福-50ug:1ml)2000G+氯化钠注射液(丰原-100ml:0.9%,软袋双阀)50MLiv微泵维持 | substantive_mismatch | substantive_mismatch | substantive_mismatch | ["枸橼酸舒芬太尼注射液(鄂宜昌人福", "-50ug:1ml)2000G+氯化钠注射液(丰原", "-100ml:0.9%,软袋双阀)50MLiv微泵维", "持"] | False |  | raw_lines_missing_tail |
| gold_smoke_001 | block_15 | null | null | null | null | equal | equal | equal | [] | False |  | none |
| gold_smoke_001 | block_16 | 氯化钠注射液(丰原-100ml：0.9%，软袋双阀)48ML+盐酸右美托咪定注射液（辰欣药业-0.2mg：2ml）0.4MGiv微泵维持 | 氯化钠注射液(丰原-100ml:0.9%,软袋双阀)48L+盐酸右美托咪定注射液(辰欣药业-0.2mg:2ml)0.4MGiv微泵维持 | 氯化钠注射液(丰原-100ml:0.9%,软袋双阀)48ML+盐酸右美托咪定注射液(辰欣药业-0.2mg:2ml)0.4MGiv微泵维持 | 氯化钠注射液(丰原-100ml:0.9%,软袋双阀)48ML+盐酸右美托咪定注射液(辰欣药业-0.2mg:2ml)0.4MGiv微泵维持 | substantive_mismatch | canonical_equal | canonical_equal | ["氯化钠注射液(丰原-100ml:0.9%,软袋", "双阀)48ML+盐酸右美托咪定注射液(辰", "欣药业-0.2mg:2ml)0.4MGiv微泵维持"] | False |  | none |
| gold_smoke_001 | block_17 | NS100ml+泰能2giv.gtt100 | NS100ml+泰能2giv.gtt100 | NS100ml+泵能2giv.gtt100 | NS100ml+泰能2giv.gtt100 | equal | substantive_mismatch | equal | ["NS100ml+泰能2giv.gtt100"] | False |  | none |
| gold_dev_m_002 | block_00 | 白蛋白10giv.gtt50;NS50m1+肝素0.5支iv微泵维持 | 白蛋白10giv.gtt50;NS50ml+肝素0.5支iv微泵维持 | 白蛋白10giv.gtt50;NS50ml+肝素0.5支iv微泵维持 | 白蛋白10giv.gtt50;NS50ml+肝素0.5支iv微泵维持 | substantive_mismatch | substantive_mismatch | substantive_mismatch | ["静脉用药", "白蛋白10giv.gtt50", "NS50ml+肝素0.5支iv微泵维持"] | False |  | raw_lines_missing_tail |
| gold_dev_m_002 | block_01 | NS50ml+力月西50mgiv微泵维持 | NS50ml+力月西50mgiv微泵维持 | NS50ml+力月西50mgiv微泵维持 | NS50ml+力月西50mgiv微泵维持 | equal | equal | equal | ["NS50ml+力月西50mgiv微泵维持"] | False |  | none |
| gold_dev_m_002 | block_02 | 氯化钠注射液(丰原-100ml：0.9%，软袋双阀)100ML+克林霉素磷酸酯注射液(鲁方明-0.3g:2ml)0.60Giv.gtt100 | 氯化钠注射液(丰原-100ml:0.9%软袋双阀)100ML+克林霉素磷酸酯注射液(鲁方明-0.3g:2ml)0.60Giv.gtt100 | 氯化钠注射液(丰原-100ml:0.9%,软袋双阀)100ML+克林霉素磷酸酯注射液(鲁方明-0.3g:2ml)0.60Giv.gtt100 | 氯化钠注射液(丰原-100ml:0.9%,软袋双阀)100ML+克林霉素磷酸酯注射液(鲁方明-0.3g:2ml)0.60Giv.gtt100 | substantive_mismatch | canonical_equal | canonical_equal | ["氯化钠注射液(丰原-100ml:0.9%,软袋", "双阀)100ML+克林霉素磷酸酯注射液(", "鲁方明-0.3g:2ml)0.60Giv.gtt100"] | False |  | none |
| gold_dev_m_002 | block_03 | null | null | null | null | equal | equal | equal | [] | False |  | none |
| gold_dev_m_002 | block_04 | 枸橼酸舒芬太尼注射液(鄂宜昌人福-50ug:1ml)12h+氯化钠注射液(丰原-100ml:0.9%,软袋双阀)50MLiv微泵维持 | 枸橼酸舒芬太尼注射液（鄂宜昌人福-50ug:1ml）12h+氯化钠注射液（丰原-100ml:0.9%，软袋双阀）50MLiv微泵维持 | 枸橼酸舒芬太尼注射液(鄂宜昌人福-50ug:1ml)12r+氯化钠注射液(丰原-100ml:0.9%,软袋双阀)50MLiv微泵维持 | 枸橼酸舒芬太尼注射液(鄂宜昌人福-50ug:1ml)12r+氯化钠注射液(丰原-100ml:0.9%,软袋双阀)50MLiv微泵维持 | canonical_equal | substantive_mismatch | substantive_mismatch | ["枸橼酸舒芬太尼注射液(鄂宜昌人福", "-50ug:1ml)12r+氯化钠注射液(丰原", "-100ml:0.9%,软袋双阀)50MLiv微泵维", "持"] | False |  | raw_lines_missing_tail |
| gold_dev_m_002 | block_05 | null | null | null | null | equal | equal | equal | [] | False |  | none |
| gold_dev_m_002 | block_06 | null | null | null | null | equal | equal | equal | [] | False |  | none |
| gold_dev_m_002 | block_07 | NS50ml+力月西50mgiv微泵维持 | NS50ml+力月西50mgiv微泵维持 | NS50ml+力月西50mgiv微泵维持 | NS50ml+力月西50mgiv微泵维持 | equal | equal | equal | ["NS50ml+力月西50mgiv微泵维持"] | False |  | none |
| gold_dev_m_002 | block_08 | null | null | null | null | equal | equal | equal | [] | False |  | none |
| gold_dev_m_002 | block_09 | NS50ml+胰岛素50uiv微泵维持 | NS50ml+胰岛素50uiv微泵维持 | NS50ml+胰岛素50uiv微泵维持 | NS50ml+胰岛素50uiv微泵维持 | equal | equal | equal | ["NS50ml+胰岛素50uiv微泵维持"] | False |  | none |
| gold_dev_m_002 | block_10 | NS50ml+肝素0.5支iv微泵维持 | NS50ml+肝素0.5支iv微泵维持 | NS50ml+肝素0.5支iv微泵维持 | NS50ml + 肝素0.5支iv微泵维持 | equal | equal | canonical_equal | ["NS50ml + 肝素0.5支iv微泵维持"] | False |  | none |
| gold_dev_m_002 | block_11 | NS100ml+泰能2giv.gtt100 | NS100ml+泰能2giv.gtt100 | NS100ml+泰能2giv.gtt100 | NS100ml+泰能2giv.gtt100 | equal | equal | equal | ["NS100ml+泰能2giv.gtt100"] | False |  | none |
| gold_dev_m_002 | block_12 | null | null | null | null | equal | equal | equal | [] | False |  | none |
| gold_dev_m_002 | block_13 | null | null | null | null | equal | equal | equal | [] | False |  | none |
| gold_dev_m_002 | block_14 | NS50ml+力月西50mgiv微泵维持 | NS50ml+力月西50mgiv微泵维持 | NS50ml+力月西50mgiv微泵维持 | NS50ml+力月西50mgiv微泵维持 | equal | equal | equal | ["NS50ml+力月西50mgiv微泵维持"] | False |  | none |
| gold_dev_m_002 | block_15 | 氯化钠注射液（丰原-100ml：0.9%，软袋,双阀）100ML+克林霉素磷酸酯注射液（鲁方明-0.3g:2ml)0.6Giv.gtt100 | 氯化钠注射液(丰原-100ml:0.9%,软袋双阀)100ML+克林霉素磷酸酯注射液(鲁方明-0.3g:2ml)0.6Giv.gtt100 | 氯化钠注射液(丰原-100ml:0.9%,软袋双阀)100ML+克林霉素磷酸酯注射液(鲁方明-0.3g:2ml)0.6Giv.gtt100 | 氯化钠注射液(丰原-100ml:0.9%,软袋双阀)100ML+克林霉素磷酸酯注射液(鲁方明-0.3g:2ml)0.6Giv.gtt100 | substantive_mismatch | substantive_mismatch | substantive_mismatch | ["氯化钠注射液(丰原-100ml:0.9%,软袋", "双阀)100ML+克林霉素磷酸酯注射液(", "鲁方明-0.3g:2ml)0.6Giv.gtt100"] | False |  | raw_lines_missing_tail |
| gold_dev_m_002 | block_16 | null | null | null | null | equal | equal | equal | [] | False |  | none |
| gold_dev_m_002 | block_17 | null | null | null | null | equal | equal | equal | [] | False |  | none |
| gold_dev_m_002 | block_18 | null | null | null | null | equal | equal | equal | [] | False |  | none |
| gold_dev_m_002 | block_19 | NS50ml+力月西50mgiv微泵维持 | NS50ml+力月西50mgiv微泵维持 | NS50ml+力月西50mgiv微泵维持 | NS50ml+力月西50mgiv微泵维持 | equal | equal | equal | ["NS50ml+力月西50mgiv微泵维持"] | False |  | none |
| gold_dev_m_002 | block_20 | null | null | null | null | equal | equal | equal | [] | False |  | none |
| gold_dev_m_002 | block_21 | NS50ml+肝素0.5支iv微泵维持 | NS50ml+肝素0.5支iv微泵维持 | NS50ml+肝素0.5支iv微泵维持 | NS50ml+肝素0.5支iv微泵维持 | equal | equal | equal | ["NS50ml + 肝素0.5支iv微泵维持"] | False |  | none |
| gold_dev_m_002 | block_22 | null | null | null | null | equal | equal | equal | [] | False |  | none |
| gold_dev_m_002 | block_23 | NS100ml+泰能2giv.gtt100;枸橼酸舒芬太尼注射液（鄂宜昌人福-50ug：1ml）4ml/l+氯化钠注射液（丰原-100ml：0.9%，软袋双阀）46MLiv微泵维 | NS100ml+泰能2giv.gtt100;枸橼酸舒芬太尼注射液（鄂宜昌人福-50ug:1ml)4ml/1+氯化钠注射液（丰原-100ml:0.9%,软袋双阀）46MLiv微泵维 | NS100ml+泰能2giv.gtt100;枸橼酸舒芬太尼注射液(鄂宜昌人福-50ug:1ml)4ml/1+氯化钠注射液(丰原-100ml:0.9%,软袋双阀)46MLiv微泵维 | NS100ml+泰能2giv.gtt100;枸橼酸舒芬太尼注射液(鄂宜昌人福-50ug:1ml)4ml/1+氯化钠注射液(丰原-100ml:0.9%,软袋双阀)46MLiv微泵维 | substantive_mismatch | substantive_mismatch | substantive_mismatch | ["NS100ml+泰能2giv.gtt100", "枸橼酸舒芬太尼注射液(鄂宜昌人福", "-50ug:1ml)4ml/1+氯化钠注射液(丰原", "-100ml:0.9%,软袋双阀)46MLiv微泵维"] | False |  | raw_lines_missing_tail |
| gold_validation_003 | block_00 | null | null | null | null | equal | equal | equal | [] | False |  | none |
| gold_validation_003 | block_01 | 0.9%NS50ml+胰岛素注射液50uiv微泵维持(暂停使用余量43ml) | 0.9%NS50ml+胰岛素注射液50uiv微泵维持（暂停使用余量43ml） | 0.9%NS50ml+胰岛素注射液50uiv微泵维持（暂停使用余量43ml） | 0.9%NS50ml+胰岛素注射液50uiv微泵维持（暂停使用余量43ml） | canonical_equal | canonical_equal | canonical_equal | ["0.9%NS50ml+胰岛素注射液50uiv微泵", "维持（暂停使用余量43ml）"] | False |  | none |
| gold_validation_003 | block_02 | null | null | null | null | equal | equal | equal | [] | False |  | none |
| gold_validation_003 | block_03 | null | null | null | null | equal | equal | equal | [] | False |  | none |
| gold_validation_003 | block_04 | 白蛋白50mliv.gtt50;氯化钠注射液(丰原-100ml：0.9%，直立式软袋双阀)40ML+咪达唑仑注射液(苏恩华-5mg：1ml)50MGiv微泵维持 | 白蛋白50mliv.gtt50;氯化钠注射液(丰原-100ml:0.9%,直立式软袋双阀)40ML+咪达唑仑注射液(苏恩华-5mg:1ml)50MGiv微泵维持 | 白蛋白50mliv.gtt50;氯化钠注射液(丰原-100ml:0.9%,直立式软袋双阀)40ML+咪达唑仑注射液(苏恩华-5mg:1ml)50MGiv微泵维持 | 白蛋白50mliv.gtt50;氯化钠注射液(丰原-100ml:0.9%,直立式软袋双阀)40ML+咪达唑仑注射液(苏恩华-5mg:1ml)50MGiv微泵维持 | canonical_equal | canonical_equal | canonical_equal | ["白蛋白50mliv.gtt50", "氯化钠注射液(丰原-100ml:0.9%,直立", "式软袋双阀)40ML+咪达唑仑注射液(苏", "恩华-5mg:1ml)50MGiv微泵维持"] | False |  | none |
| gold_validation_003 | block_05 | NS50ml+盐酸瑞芬太尼4mgiv微泵维持 | NS50ml+盐酸瑞芬太尼4mgiv微泵维持 | NS50ml+盐酸瑞芬太尼4mgiv微泵维持 | NS50ml+盐酸瑞芬太尼4mgiv微泵维持 | equal | equal | equal | ["NS50ml+盐酸瑞芬太尼4mgiv微泵维持"] | False |  | none |
| gold_validation_003 | block_06 | NS100ml+亚胺培南西司他丁钠1giv.gtt100 | NS100ml+亚胺培南西司他丁钠1giv.gt | NS100ml+亚胺培南西司他丁钠1g i.v. gt t100 | NS100ml+亚胺培南西司他丁钠1giv.gtt100 | substantive_mismatch | substantive_mismatch | equal | ["NS100ml+亚胺培南西司他丁钠1giv.gt", "t100"] | False |  | none |
| gold_validation_003 | block_07 | NS20ml+氨溴索30mgiv20;氯化钠注射液(丰原-100ml：0.9%，直立式软袋双阀)20ML+注射用艾司奥美拉唑钠(湖北人民制药-40mg)40MGiv20 | NS20ml+氨溴索30mgiv20;氯化钠注射液(丰原-100ml:0.9%,直立式软袋双阀)20ML+注射用艾司奥美拉唑钠(湖北人民制药-40mg)40MGiv20 | NS20ml+氨溴索30mgiv20;氯化钠注射液(丰原-100ml:0.9%,直立式软袋双阀)20ML+注射用艾司奥美拉唑钠(湖北人民制药-40mg)40MGiv20 | NS20ml+氨溴索30mgiv20;氯化钠注射液(丰原-100ml:0.9%,直立式软袋双阀)20ML+注射用艾司奥美拉唑钠(湖北人民制药-40mg)40MGiv20 | canonical_equal | canonical_equal | canonical_equal | ["NS20ml+氨溴索30mgiv20", "氯化钠注射液(丰原-100ml:0.9%,直立", "式软袋双阀)20ML+注射用艾司奥美拉", "唑钠(湖北人民制药-40mg)40MGiv20"] | False |  | none |
| gold_validation_003 | block_08 | 5%GS40ml+去甲肾上腺素20mgiv微泵维持 | 5%GS40ml+去甲肾上腺素20mgiv微泵维持 | 5%GS40ml+去甲肾上腺素20mgiv微泵维持 | 5%GS40ml+去甲肾上腺素20mgiv微泵维持 | equal | equal | equal | ["5%GS40ml+去甲肾上腺素20mgiv微泵维", "持"] | False |  | none |
| gold_validation_003 | block_09 | 氯化钠注射液(丰原-100ml:0.9%,直立式软袋双阀)100ML+注射用盐酸万古霉素(礼来-0.5g)0.50Giv.gtt100 | 氯化钠注射液(丰原-100ml:0.9%,直立式软袋双阀)100ML+注射用盐酸万古霉素(礼来-0.5g)0.50Giv.gtt100 | 氯化钠注射液(丰原-100ml:0.9%,直立式软袋双阀)100ML+注射用盐酸万古霉素(礼来-0.5g)0.50Giv.gtt100 | 氯化钠注射液(丰原-100ml:0.9%,直立式软袋双阀)100ML+注射用盐酸万古霉素(礼来-0.5g)0.50Giv.gtt100 | equal | equal | equal | ["氯化钠注射液(丰原-100ml:0.9%,直立", "式软袋双阀)100ML+注射用盐酸万古霉", "素(礼来-0.5g)0.50Giv.gtt100"] | False |  | none |
| gold_validation_003 | block_10 | null | null | null | null | equal | equal | equal | [] | False |  | none |
| gold_validation_003 | block_11 | 白蛋白50mliv.gtt50 | 白蛋白50mliv.gtt50 | 白蛋白50mliv.gtt50 | 白蛋白50mliv.gtt50 | equal | equal | equal | ["白蛋白50mliv.gtt50"] | False |  | none |
| gold_validation_003 | block_12 | 白蛋白50mliv.gtt50 | 白蛋白50mliv.gtt50 | 白蛋白50mliv.gtt50 | 白蛋白50mliv.gtt50 | equal | equal | equal | ["白蛋白50mliv.gtt50"] | False |  | none |
| gold_validation_003 | block_13 | NS100ml+异甘草酸镁200mgiv.gtt100;葡萄糖注射液（丰原-100ml：5%，直立式软袋双阀）60min+去乙酰毛花苷注射液（成都倍特-0.4mg：2ml）0.40MGiv微泵维持 | NS100ml+异甘草酸镁200mgiv.gtt100;葡萄糖注射液(丰原-100ml:5%,直立式软袋双阀)60ml+去乙酰毛花苷注射液(成都倍特-0.4mg:2ml)0.40MGiv微泵;维持 | NS100ml+异甘草酸镁200mgiv.gtt100;葡萄糖注射液(丰原-100ml:5%,直立式软袋双阀)60min+去乙酰毛花苷注射液(成都倍特-0.4mg:2ml)0.40MGiv微泵;维持 | NS100ml+异甘草酸镁200mgiv.gtt100;葡萄糖注射液(丰原-100ml:5%,直立式软袋双阀)60min+去乙酰毛花苷注射液(成都倍特-0.4mg:2ml)0.40MGiv微泵维持 | substantive_mismatch | separator_error | canonical_equal | ["NS100ml+异甘草酸镁200mgiv.gtt100", "葡萄糖注射液(丰原-100ml:5%,直立式", "软袋双阀)60min+去乙酰毛花苷注射液", "(成都倍特-0.4mg:2ml)0.40MGiv微泵", "维持"] | False |  | none |
| gold_validation_003 | block_14 | 氯化钠注射液(丰原-100ml:0.9%,直立式软袋双阀)40ML+苯磺顺阿曲库铵注 | 氯化钠注射液(丰原-100ml:0.9%,直立式软袋双阀)40ML+苯磺顺阿曲库铵注 | 氯化钠注射液(丰原-100ml:0.9%,直立式软袋双阀)40ML+苯磺顺阿曲库铵注 | 氯化钠注射液(丰原-100ml:0.9%,直立式软袋双阀)40ML+苯磺顺阿曲库铵注 | equal | equal | equal | ["静脉用药", "氯化钠注射液(丰原-100ml:0.9%,直立", "式软袋双阀)40ML+苯磺顺阿曲库铵注"] | False |  | none |
