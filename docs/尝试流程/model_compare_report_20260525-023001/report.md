# model comparison summary

| label | model | run_id | seconds | total | L | M | R | missing | overfill | mismatch |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| qwen3_32b_rep1 | qwen3-vl-32b | modelcmp-qwen3_32b_rep1-20260525-023001 | 107.563 | 43 | 6 | 24 | 13 | 19 | 9 | 15 |
| qwen25_7b | qwen2.5vl-7b | modelcmp-qwen25_7b-20260525-023001 | 72.419 | 321 | 215 | 30 | 75 | 17 | 251 | 53 |
| qwen25_32b | qwen2.5vl-32b | modelcmp-qwen25_32b-20260525-023001 | 353.228 | 64 | 11 | 27 | 24 | 22 | 22 | 20 |
| qwen3_8b | qwen3vl-8b | modelcmp-qwen3_8b-20260525-023001 | 69.604 | 72 | 27 | 26 | 15 | 19 | 29 | 24 |

## qwen3_32b repetition
| pair | exact_equal | total diffs | L | M | R |
|---|---:|---:|---:|---:|---:|
| qwen3_32b_rep1 vs qwen3_32b_rep2 | False | 1 | 0 | 0 | 1 |
| qwen3_32b_rep1 vs qwen3_32b_rep3 | False | 1 | 0 | 0 | 1 |
| qwen3_32b_rep2 vs qwen3_32b_rep3 | True | 0 | 0 | 0 | 0 |

## qwen3_32b_rep1 M diffs
- block_00 `入量_静脉用药` mismatch: gold=钠钾镁钙葡萄糖注射液250mliv.gtt250 | actual=钠钾镁钙葡萄糖注射液250mliv.gtt;250
- block_00 `出量_其他出量` missing: gold=鼻胃管/50 | actual=null
- block_00 `痰_色` missing: gold=7 | actual=null
- block_00 `痰_量` missing: gold=1 | actual=null
- block_00 `管路护理` missing: gold=鼻胃管/是/墨绿色// | actual=null
- block_01 `痰_色` missing: gold=7 | actual=null
- block_01 `痰_量` missing: gold=1 | actual=null
- block_02 `入量_静脉用药` mismatch: gold=氯化钠注射液(丰原-100ml：0.9%，软袋双阀)续用12ml/h+咪达唑仑注射液（苏恩华-5mg：1ml)50MGiv微泵维持 | actual=氯化钠注射液(丰原-100ml:0.9%,软袋双阀)续用12ml/h+咪达唑仑注射液(苏恩华-5mg:1ml)50MGiv微泵维持
- block_04 `入量_静脉用药` mismatch: gold=钠钾镁钙葡萄糖注射液250mliv.gtt250 | actual=钠钾镁钙葡萄糖注射液250mliv.gtt;250
- block_04 `痰_色` missing: gold=7 | actual=null
- block_04 `痰_量` missing: gold=1 | actual=null
- block_04 `管路护理` missing: gold=颈内深静脉导管/是///;气管插管/是///23;导尿管/是///;桡动脉导管/是///;静脉留置针/是///;鼻胃管/是///;锁骨下深静脉导管/是///15;股静脉导管/是///43 | actual=null
- block_06 `痰_色` missing: gold=7 | actual=null
- block_06 `痰_量` missing: gold=1 | actual=null
- block_08 `入量_其他` mismatch: gold=肠内营养液（SP）500ml胃管滴入 | actual=肠内营养液（SP）500ml胃管;滴入
- block_09 `入量_其他` mismatch: gold=复方磺胺甲噁唑片(华中药业-0.48gX100片)4片胃管滴入 | actual=复方磺胺甲噁唑片（华中药业-0.48gX100片）4片胃管滴入
- block_12 `入量_静脉用药` mismatch: gold=NS100ml+甲泼尼龙琥珀酸钠80mgiv.gtt100;咪达唑仑注射液（苏恩华-5mg：1ml）50MG+氯化钠注射液（丰原-100ml：0.9%，软袋双阀）45MLiv微泵维持 | actual=NS100ml+甲泼尼龙琥珀酸钠80mgiv.gt; t100; 咪达唑仑注射液(苏恩华-5mg:1ml)50M; G+氯化钠注射液(丰原-100ml:0.9%,软袋双阀)45MLiv微泵维持
- block_13 `痰_色` missing: gold=7 | actual=null
- block_13 `痰_量` missing: gold=1 | actual=null
- block_14 `入量_静脉用药` mismatch: gold=枸橼酸舒芬太尼注射液(鄂宜昌人福,-50ug:1ml)200UG+氯化钠注射液(丰原,-100ml:0.9%,软袋双阀)50MLiv微泵维持 | actual=枸橼酸舒芬太尼注射液（鄂宜昌人福-50ug:1ml）200UG+氯化钠注射液（丰原-100ml:0.9%,软袋双阀）50MLiv微泵维持
- block_16 `入量_其他` mismatch: gold=磷酸奥司他韦75mgpo;复方磺胺甲噁唑片（华中药业-0.48gX100片）4片胃管滴入;水100ml | actual=磷酸奥司他韦75mgpo;复方磺胺甲噁唑片(华中药业-0.48gX100片)4片胃管滴入;水100ml
- block_16 `入量_静脉用药` mismatch: gold=氯化钠注射液(丰原-100ml：0.9%，软袋双阀)48ML+盐酸右美托咪定注射液（辰欣药业-0.2mg：2ml）0.4MGiv微泵维持 | actual=氯化钠注射液(丰原-100ml:0.9%,软袋双阀)48ML+盐酸右美托咪定注射液(辰欣药业-0.2mg:2ml)0.4MGiv微泵维持
- block_16 `痰_色` missing: gold=7 | actual=null
- block_16 `痰_量` missing: gold=1 | actual=null

## qwen25_7b M diffs
- block_00 `入量_静脉用药` mismatch: gold=钠钾镁钙葡萄糖注射液250mliv.gtt250 | actual=钠钾镁钙葡萄糖注射液250mliv.gtt
- block_00 `出量_其他出量` missing: gold=鼻胃管/50 | actual=null
- block_00 `痰_色` missing: gold=7 | actual=null
- block_00 `痰_量` missing: gold=1 | actual=null
- block_00 `管路护理` mismatch: gold=鼻胃管/是/墨绿色// | actual=气管插管/是///23
- block_01 `痰_色` missing: gold=7 | actual=null
- block_01 `痰_量` missing: gold=1 | actual=null
- block_02 `入量_其他` mismatch: gold=磷酸奥司他韦75mgpo水20ml | actual=磷酸奥司他韦75mgp0水20ml
- block_02 `入量_静脉用药` mismatch: gold=氯化钠注射液(丰原-100ml：0.9%，软袋双阀)续用12ml/h+咪达唑仑注射液（苏恩华-5mg：1ml)50MGiv微泵维持 | actual=氯化钠注射液(丰原-100ml:0.9%,软袋,磷酸奥司他韦75mgp0水20ml,双阀)续用12ml/h+咪达唑仑注射液(苏恩华-5mg:1ml)50MGiv微泵维持
- block_02 `管路护理` overfill: gold=null | actual=气管插管/是///23
- block_04 `入量_静脉用药` mismatch: gold=钠钾镁钙葡萄糖注射液250mliv.gtt250 | actual=钠钾镁钙葡萄糖注射液250mliv.gtt
- block_04 `痰_色` missing: gold=7 | actual=null
- block_04 `痰_量` missing: gold=1 | actual=null
- block_04 `管路护理` missing: gold=颈内深静脉导管/是///;气管插管/是///23;导尿管/是///;桡动脉导管/是///;静脉留置针/是///;鼻胃管/是///;锁骨下深静脉导管/是///15;股静脉导管/是///43 | actual=null
- block_06 `入量_总量` missing: gold=570 | actual=null
- block_06 `出量_总量` overfill: gold=null | actual=570
- block_06 `痰_色` missing: gold=7 | actual=null
- block_06 `痰_量` missing: gold=1 | actual=null
- block_08 `入量_其他` mismatch: gold=肠内营养液（SP）500ml胃管滴入 | actual=滴入
- block_08 `入量_静脉用药` overfill: gold=null | actual=肠内营养液（SP）500ml胃管
- block_08 `管路护理` overfill: gold=null | actual=气管插管/是///23
- block_09 `入量_其他` mismatch: gold=复方磺胺甲噁唑片(华中药业-0.48gX100片)4片胃管滴入 | actual=-0.48gX100片)4片胃管滴入
- block_12 `入量_静脉用药` mismatch: gold=NS100ml+甲泼尼龙琥珀酸钠80mgiv.gtt100;咪达唑仑注射液（苏恩华-5mg：1ml）50MG+氯化钠注射液（丰原-100ml：0.9%，软袋双阀）45MLiv微泵维持 | actual=NS100ml+甲泼尼龙琥珀酸钠80mgiv.gt;t100;咪达唑仑注射液(苏恩华-5mg:1ml)50M;G+氯化钠注射液(丰原-100ml:0.9%,软袋双阀)45MLiv微泵维持
- block_13 `痰_色` missing: gold=7 | actual=null
- block_13 `痰_量` missing: gold=1 | actual=null
- block_14 `入量_静脉用药` mismatch: gold=枸橼酸舒芬太尼注射液(鄂宜昌人福,-50ug:1ml)200UG+氯化钠注射液(丰原,-100ml:0.9%,软袋双阀)50MLiv微泵维持 | actual=枸橼酸舒芬太尼注射液(鄂宜昌人福-50ug:1ml)200UG+氯化钠注射液(丰原100ml:0.9%,软袋双阀)50MLiv微泵维持
- block_16 `入量_其他` missing: gold=磷酸奥司他韦75mgpo;复方磺胺甲噁唑片（华中药业-0.48gX100片）4片胃管滴入;水100ml | actual=null
- block_16 `入量_静脉用药` mismatch: gold=氯化钠注射液(丰原-100ml：0.9%，软袋双阀)48ML+盐酸右美托咪定注射液（辰欣药业-0.2mg：2ml）0.4MGiv微泵维持 | actual=氯化钠注射液(丰原-100ml:0.9%,软袋,磷酸奥司他韦75mgpo,148,1783,800,双阀)48瓜+盐酸右美托咪定注射液(辰,复方磺胺甲唑片(华中药业,欣药业-0.2mg:2ml)0.4MGiv微泵维持,-0.48gX100片)4片胃管滴入,水100ml
- block_16 `痰_色` missing: gold=7 | actual=null
- block_16 `痰_量` missing: gold=1 | actual=null

## qwen25_32b M diffs
- block_00 `入量_静脉用药` mismatch: gold=钠钾镁钙葡萄糖注射液250mliv.gtt250 | actual=钠钾镁钙葡萄糖注射液250ml iv.gtt;250
- block_00 `出量_其他出量` missing: gold=鼻胃管/50 | actual=null
- block_00 `痰_色` missing: gold=7 | actual=null
- block_00 `痰_量` missing: gold=1 | actual=null
- block_00 `管路护理` missing: gold=鼻胃管/是/墨绿色// | actual=null
- block_01 `痰_色` missing: gold=7 | actual=null
- block_01 `痰_量` missing: gold=1 | actual=null
- block_02 `入量_静脉用药` mismatch: gold=氯化钠注射液(丰原-100ml：0.9%，软袋双阀)续用12ml/h+咪达唑仑注射液（苏恩华-5mg：1ml)50MGiv微泵维持 | actual=氯化钠注射液(丰原-100ml:0.9%，软袋);双阀)续用12ml/h+咪达唑仑注射液(苏;恩华-5mg:1ml)50MGiv微泵维持
- block_03 `入量_静脉用药` mismatch: gold=速尿20mgiv0 | actual=速尿20mg iv 0
- block_04 `入量_静脉用药` mismatch: gold=钠钾镁钙葡萄糖注射液250mliv.gtt250 | actual=钠钾镁钙葡萄糖注射液250ml iv.gtt;250
- block_04 `痰_色` missing: gold=7 | actual=null
- block_04 `痰_量` missing: gold=1 | actual=null
- block_04 `管路护理` missing: gold=颈内深静脉导管/是///;气管插管/是///23;导尿管/是///;桡动脉导管/是///;静脉留置针/是///;鼻胃管/是///;锁骨下深静脉导管/是///15;股静脉导管/是///43 | actual=null
- block_05 `入量_静脉用药` mismatch: gold=莫西沙星250mliv.gtt250 | actual=莫西沙星250ml iv.gtt 250
- block_06 `痰_色` missing: gold=7 | actual=null
- block_06 `痰_量` missing: gold=1 | actual=null
- block_08 `入量_其他` mismatch: gold=肠内营养液（SP）500ml胃管滴入 | actual=肠内营养液（SP）500ml胃管;滴入
- block_09 `入量_其他` mismatch: gold=复方磺胺甲噁唑片(华中药业-0.48gX100片)4片胃管滴入 | actual=复方磺胺甲噁唑片（华中药业）-0.48gX100片）4片胃管滴入
- block_12 `入量_静脉用药` mismatch: gold=NS100ml+甲泼尼龙琥珀酸钠80mgiv.gtt100;咪达唑仑注射液（苏恩华-5mg：1ml）50MG+氯化钠注射液（丰原-100ml：0.9%，软袋双阀）45MLiv微泵维持 | actual=NS100ml+甲泼尼龙琥珀酸钠80mgiv.gt;t100;咪达唑仑注射液(苏恩华-5mg:1ml)50M;G+氯化钠注射液(丰原-100ml:0.9%，软;袋双阀) 45MLiv微泵维持
- block_13 `入量_静脉用药` mismatch: gold=NS100ml+泮托拉唑40mgiv.gtt100 | actual=NS100ml+泮托拉唑40mg iv.gtt 100
- block_13 `痰_色` missing: gold=7 | actual=null
- block_13 `痰_量` missing: gold=1 | actual=null
- block_14 `入量_静脉用药` mismatch: gold=枸橼酸舒芬太尼注射液(鄂宜昌人福,-50ug:1ml)200UG+氯化钠注射液(丰原,-100ml:0.9%,软袋双阀)50MLiv微泵维持 | actual=枸橼酸舒芬太尼注射液(鄂宜昌人福-50ug:1ml)200UG+氯化钠注射液(丰原-100ml:0.9%, 软袋双阀) 50ML.iv微泵维持
- block_16 `入量_其他` mismatch: gold=磷酸奥司他韦75mgpo;复方磺胺甲噁唑片（华中药业-0.48gX100片）4片胃管滴入;水100ml | actual=磷酸奥司他韦75mgpo;复方磺胺甲噁唑片(华中药业;-0.48gX100片) 4片胃管滴入;水100ml
- block_16 `入量_静脉用药` mismatch: gold=氯化钠注射液(丰原-100ml：0.9%，软袋双阀)48ML+盐酸右美托咪定注射液（辰欣药业-0.2mg：2ml）0.4MGiv微泵维持 | actual=氯化钠注射液(丰原-100ml:0.9%，软袋;双阀)48ml+盐酸右美托咪定注射液(辰;欣药业-0.2mg:2ml) 0.4MGiv微泵维持
- block_16 `痰_色` missing: gold=7 | actual=null
- block_16 `痰_量` missing: gold=1 | actual=null

## qwen3_8b M diffs
- block_00 `入量_其他` overfill: gold=null | actual=250
- block_00 `入量_静脉用药` mismatch: gold=钠钾镁钙葡萄糖注射液250mliv.gtt250 | actual=钠钾镁钙葡萄糖注射液250mliv.gtt
- block_00 `出量_其他出量` missing: gold=鼻胃管/50 | actual=null
- block_00 `痰_色` missing: gold=7 | actual=null
- block_00 `痰_量` missing: gold=1 | actual=null
- block_00 `管路护理` missing: gold=鼻胃管/是/墨绿色// | actual=null
- block_01 `痰_色` missing: gold=7 | actual=null
- block_01 `痰_量` missing: gold=1 | actual=null
- block_02 `入量_每时` overfill: gold=null | actual=12
- block_02 `入量_静脉用药` mismatch: gold=氯化钠注射液(丰原-100ml：0.9%，软袋双阀)续用12ml/h+咪达唑仑注射液（苏恩华-5mg：1ml)50MGiv微泵维持 | actual=氯化钠注射液(丰原-100ml:0.9%,软袋双阀)续用12ml/h+咪达唑仑注射液(苏恩华-5mg:1ml)50MGiv微泵维持
- block_04 `入量_其他` overfill: gold=null | actual=250
- block_04 `入量_静脉用药` mismatch: gold=钠钾镁钙葡萄糖注射液250mliv.gtt250 | actual=钠钾镁钙葡萄糖注射液250mliv.gtt
- block_04 `痰_色` missing: gold=7 | actual=null
- block_04 `痰_量` missing: gold=1 | actual=null
- block_04 `管路护理` missing: gold=颈内深静脉导管/是///;气管插管/是///23;导尿管/是///;桡动脉导管/是///;静脉留置针/是///;鼻胃管/是///;锁骨下深静脉导管/是///15;股静脉导管/是///43 | actual=null
- block_06 `痰_色` missing: gold=7 | actual=null
- block_06 `痰_量` missing: gold=1 | actual=null
- block_08 `入量_其他` mismatch: gold=肠内营养液（SP）500ml胃管滴入 | actual=肠内营养液（SP）500ml胃管;滴入
- block_12 `入量_静脉用药` mismatch: gold=NS100ml+甲泼尼龙琥珀酸钠80mgiv.gtt100;咪达唑仑注射液（苏恩华-5mg：1ml）50MG+氯化钠注射液（丰原-100ml：0.9%，软袋双阀）45MLiv微泵维持 | actual=NS100ml+甲泼尼龙琥珀酸钠80mgiv.gt;t100;咪达唑仑注射液(苏恩华-5mg:1ml)50M;G+氯化钠注射液(丰原-100ml:0.9%,软袋双阀)45MLiv微泵维持
- block_13 `痰_色` missing: gold=7 | actual=null
- block_13 `痰_量` missing: gold=1 | actual=null
- block_14 `入量_静脉用药` mismatch: gold=枸橼酸舒芬太尼注射液(鄂宜昌人福,-50ug:1ml)200UG+氯化钠注射液(丰原,-100ml:0.9%,软袋双阀)50MLiv微泵维持 | actual=枸橼酸舒芬太尼注射液(鄂宜昌人福-50ug:1ml)200UG+氯化钠注射液(丰原-100ml:0.9%,软袋双阀)50MLiv微泵维持
- block_16 `入量_其他` mismatch: gold=磷酸奥司他韦75mgpo;复方磺胺甲噁唑片（华中药业-0.48gX100片）4片胃管滴入;水100ml | actual=磷酸奥司他韦75mgpo-0.48gX100片)4片胃管滴入水100ml
- block_16 `入量_静脉用药` mismatch: gold=氯化钠注射液(丰原-100ml：0.9%，软袋双阀)48ML+盐酸右美托咪定注射液（辰欣药业-0.2mg：2ml）0.4MGiv微泵维持 | actual=氯化钠注射液(丰原-100ml:0.9%,软袋双阀)48ML+盐酸右美托咪定注射液(辰欣药业-0.2mg:2ml)0.4MGiv微泵维持
- block_16 `痰_色` missing: gold=7 | actual=null
- block_16 `痰_量` missing: gold=1 | actual=null
