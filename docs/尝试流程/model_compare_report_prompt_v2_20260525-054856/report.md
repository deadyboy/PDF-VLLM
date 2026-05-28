# Jin M Prompt V2 Continuation Experiment

- stamp: `20260525-054856`
- old_run: `modelcmp-qwen3_32b_rep1-20260525-041208`
- new_run: `modelcmp-qwen3_32b_m_prompt_v2-20260525-054601`
- target: `/data1/jianf/新提取pdf/180data/0013807667_2023_10_15_3.png`
- gold: `/tmp/0013807667_2023_10_15_3_gold.json`

## Overall Eval
| run | strict_total | L | M | R | canonical_only | separator_error | missing | overfill | substantive_mismatch |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| old_qwen3_32b_rep1 | 27 | 5 | 11 | 8 | 1 | 4 | 4 | 6 | 12 |
| new_qwen3_32b_m_prompt_v2 | 22 | 4 | 7 | 8 | 2 | 3 | 4 | 4 | 9 |

## M Only Eval
| run | strict_total | canonical_only | separator_error | missing | overfill | substantive_mismatch |
|---|---:|---:|---:|---:|---:|---:|
| old_qwen3_32b_rep1 | 11 | 1 | 3 | 0 | 1 | 6 |
| new_qwen3_32b_m_prompt_v2 | 7 | 2 | 2 | 0 | 0 | 3 |

## L/R Old-New Changes
- count: `1`
- block_05 `意识`: old=76 | new=null

## Focus Cases
| block | field | gold | old_actual | old_eval | new_actual | new_eval |
|---|---|---|---|---|---|---|
| block_00 | 入量_静脉用药 | 钠钾镁钙葡萄糖注射液250mliv.gtt250 | 钠钾镁钙葡萄糖注射液250mliv.gtt | substantive_mismatch | 钠钾镁钙葡萄糖注射液250mliv.gtt250 | equal |
| block_00 | 入量_其他 | null | 250 | overfill | null | equal |
| block_00 | 管路护理 | 鼻胃管/是/墨绿色// | 鼻胃管/是/墨绿色/ | substantive_mismatch | 鼻胃管/是/墨绿色// | equal |
| block_04 | 入量_静脉用药 | 钠钾镁钙葡萄糖注射液250mliv.gtt250 | 钠钾镁钙葡萄糖注射液250mliv.gtt;250 | separator_error | 钠钾镁钙葡萄糖注射液250mliv.gtt250 | equal |
| block_04 | 管路护理 | 颈内深静脉导管/是///;气管插管/是///23;导尿管/是///;桡动脉导管/是///;静脉留置针/是///;鼻胃管/是///;锁骨下深静脉导管/是///15;股静脉导管/是///43 | 颈内深静脉导管/是///;气管插管/是///23;导尿管/是///;桡动脉导管/是///;静脉留置针/是///;鼻胃管/是///;锁骨下深静脉导管/是///15;股静脉导管/是///;43 | separator_error | 颈内深静脉导管/是///气管插管/是///23导尿管/是///桡动脉导管/是///静脉留置针/是///鼻胃管/是///锁骨下深静脉导管/是///15股静脉导管/是///43 | separator_error |
| block_08 | 入量_其他 | 肠内营养液（SP）500ml胃管滴入 | 肠内营养液（SP）500ml胃管;滴入 | separator_error | 肠内营养液（SP）500ml胃管;滴入 | separator_error |
| block_12 | 入量_静脉用药 | NS100ml+甲泼尼龙琥珀酸钠80mgiv.gtt100;咪达唑仑注射液（苏恩华-5mg：1ml）50MG+氯化钠注射液（丰原-100ml：0.9%，软袋双阀）45MLiv微泵维持 | NS100ml+甲泼尼龙琥珀酸钠80mgiv.gt;咪达唑仑注射液（苏恩华-5mg:1ml）50M;G+氯化钠注射液（丰原-100ml:0.9%，软袋双阀）45MLiv微泵维持 | substantive_mismatch | NS100ml+甲泼尼龙琥珀酸钠80mgiv.gtt100;咪达唑仑注射液（苏恩华-5mg:1ml）50MG+氯化钠注射液（丰原-100ml:0.9%，软袋双阀）45MLiv微泵维持 | canonical_equal |

## New M Errors Not Present In Old
- none

## Old M Errors Resolved
- block_00 `入量_其他` old_eval=overfill: gold=null | old_actual=250
- block_00 `入量_静脉用药` old_eval=substantive_mismatch: gold=钠钾镁钙葡萄糖注射液250mliv.gtt250 | old_actual=钠钾镁钙葡萄糖注射液250mliv.gtt
- block_00 `管路护理` old_eval=substantive_mismatch: gold=鼻胃管/是/墨绿色// | old_actual=鼻胃管/是/墨绿色/
- block_04 `入量_静脉用药` old_eval=separator_error: gold=钠钾镁钙葡萄糖注射液250mliv.gtt250 | old_actual=钠钾镁钙葡萄糖注射液250mliv.gtt;250

## New M Diffs
- block_02 `入量_静脉用药` strict=mismatch eval=substantive_mismatch: gold=氯化钠注射液(丰原-100ml：0.9%，软袋双阀)续用12ml/h+咪达唑仑注射液（苏恩华-5mg：1ml)50MGiv微泵维持 | actual=氯化钠注射液（丰原-100ml：0.9%，软袋，双阀）续用12ml/hr+咪达唑仑注射液（苏恩华-5mg：1ml）50MGiv微泵维持
- block_04 `管路护理` strict=mismatch eval=separator_error: gold=颈内深静脉导管/是///;气管插管/是///23;导尿管/是///;桡动脉导管/是///;静脉留置针/是///;鼻胃管/是///;锁骨下深静脉导管/是///15;股静脉导管/是///43 | actual=颈内深静脉导管/是///气管插管/是///23导尿管/是///桡动脉导管/是///静脉留置针/是///鼻胃管/是///锁骨下深静脉导管/是///15股静脉导管/是///43
- block_08 `入量_其他` strict=mismatch eval=separator_error: gold=肠内营养液（SP）500ml胃管滴入 | actual=肠内营养液（SP）500ml胃管;滴入
- block_12 `入量_静脉用药` strict=mismatch eval=canonical_equal: gold=NS100ml+甲泼尼龙琥珀酸钠80mgiv.gtt100;咪达唑仑注射液（苏恩华-5mg：1ml）50MG+氯化钠注射液（丰原-100ml：0.9%，软袋双阀）45MLiv微泵维持 | actual=NS100ml+甲泼尼龙琥珀酸钠80mgiv.gtt100;咪达唑仑注射液（苏恩华-5mg:1ml）50MG+氯化钠注射液（丰原-100ml:0.9%，软袋双阀）45MLiv微泵维持
- block_14 `入量_静脉用药` strict=mismatch eval=substantive_mismatch: gold=枸橼酸舒芬太尼注射液(鄂宜昌人福,-50ug:1ml)200UG+氯化钠注射液(丰原,-100ml:0.9%,软袋双阀)50MLiv微泵维持 | actual=枸橼酸舒芬太尼注射液（鄂宜昌人福-50ug:1ml）200UG+氯化钠注射液（丰原-100ml:0.9%,软袋双阀）50MLiv微泵维持
- block_16 `入量_其他` strict=mismatch eval=canonical_equal: gold=磷酸奥司他韦75mgpo;复方磺胺甲噁唑片（华中药业-0.48gX100片）4片胃管滴入;水100ml | actual=磷酸奥司他韦75mgpo;复方磺胺甲噁唑片(华中药业-0.48gX100片)4片胃管滴入;水100ml
- block_16 `入量_静脉用药` strict=mismatch eval=substantive_mismatch: gold=氯化钠注射液(丰原-100ml：0.9%，软袋双阀)48ML+盐酸右美托咪定注射液（辰欣药业-0.2mg：2ml）0.4MGiv微泵维持 | actual=氯化钠注射液(丰原-100ml:0.9%,软袋双阀)48L+盐酸右美托咪定注射液(辰欣药业-0.2mg:2ml)0.4MGiv微泵维持
