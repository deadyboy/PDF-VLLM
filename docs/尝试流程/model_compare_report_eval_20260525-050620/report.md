# Accuracy Model Review - Eval Attribution

- eval_stamp: `20260525-050620`
- source_model_stamp: `20260525-041208`
- target: `/data1/jianf/新提取pdf/180data/0013807667_2023_10_15_3.png`
- gold: `/tmp/0013807667_2023_10_15_3_gold.json`
- note: report-only regeneration; model outputs were not rerun

| label | model | run_id | seconds | strict_total | L | M | R | canonical_only | separator_error | missing | overfill | substantive_mismatch |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| qwen3_32b_rep1 | qwen3-vl-32b | modelcmp-qwen3_32b_rep1-20260525-041208 | 135.374 | 27 | 5 | 11 | 8 | 1 | 4 | 4 | 6 | 12 |
| qwen25_72b | qwen2.5vl-72b | modelcmp-qwen25_72b-20260525-041208 | 271.113 | 27 | 3 | 11 | 10 | 3 | 5 | 4 | 4 | 11 |
| qwen25_32b | qwen2.5vl-32b | modelcmp-qwen25_32b-20260525-041208 | 319.602 | 55 | 9 | 23 | 19 | 6 | 2 | 8 | 21 | 18 |
| qwen3_8b | qwen3vl-8b | modelcmp-qwen3_8b-20260525-041208 | 72.66 | 50 | 13 | 16 | 11 | 3 | 4 | 7 | 22 | 14 |

## Qwen3-VL-32B Repeatability
| pair | exact_equal | total | L | M | R |
|---|---:|---:|---:|---:|---:|
| qwen3_32b_rep1 vs qwen3_32b_rep2 | True | 0 | 0 | 0 | 0 |
| qwen3_32b_rep1 vs qwen3_32b_rep3 | True | 0 | 0 | 0 | 0 |
| qwen3_32b_rep2 vs qwen3_32b_rep3 | True | 0 | 0 | 0 | 0 |

## qwen3_32b_rep1 M Diffs
- block_00 `入量_其他` strict=overfill eval=overfill: gold=null | actual=250
- block_00 `入量_静脉用药` strict=mismatch eval=substantive_mismatch: gold=钠钾镁钙葡萄糖注射液250mliv.gtt250 | actual=钠钾镁钙葡萄糖注射液250mliv.gtt
- block_00 `管路护理` strict=mismatch eval=substantive_mismatch: gold=鼻胃管/是/墨绿色// | actual=鼻胃管/是/墨绿色/
- block_02 `入量_静脉用药` strict=mismatch eval=substantive_mismatch: gold=氯化钠注射液(丰原-100ml：0.9%，软袋双阀)续用12ml/h+咪达唑仑注射液（苏恩华-5mg：1ml)50MGiv微泵维持 | actual=氯化钠注射液(丰原-100ml:0.9%,软袋双阀)续用12ml/hr+咪达唑仑注射液(苏恩华-5mg:1ml)50MGiv微泵维持
- block_04 `入量_静脉用药` strict=mismatch eval=separator_error: gold=钠钾镁钙葡萄糖注射液250mliv.gtt250 | actual=钠钾镁钙葡萄糖注射液250mliv.gtt;250
- block_04 `管路护理` strict=mismatch eval=separator_error: gold=颈内深静脉导管/是///;气管插管/是///23;导尿管/是///;桡动脉导管/是///;静脉留置针/是///;鼻胃管/是///;锁骨下深静脉导管/是///15;股静脉导管/是///43 | actual=颈内深静脉导管/是///;气管插管/是///23;导尿管/是///;桡动脉导管/是///;静脉留置针/是///;鼻胃管/是///;锁骨下深静脉导管/是///15;股静脉导管/是///;43
- block_08 `入量_其他` strict=mismatch eval=separator_error: gold=肠内营养液（SP）500ml胃管滴入 | actual=肠内营养液（SP）500ml胃管;滴入
- block_12 `入量_静脉用药` strict=mismatch eval=substantive_mismatch: gold=NS100ml+甲泼尼龙琥珀酸钠80mgiv.gtt100;咪达唑仑注射液（苏恩华-5mg：1ml）50MG+氯化钠注射液（丰原-100ml：0.9%，软袋双阀）45MLiv微泵维持 | actual=NS100ml+甲泼尼龙琥珀酸钠80mgiv.gt;咪达唑仑注射液（苏恩华-5mg:1ml）50M;G+氯化钠注射液（丰原-100ml:0.9%，软袋双阀）45MLiv微泵维持
- block_14 `入量_静脉用药` strict=mismatch eval=substantive_mismatch: gold=枸橼酸舒芬太尼注射液(鄂宜昌人福,-50ug:1ml)200UG+氯化钠注射液(丰原,-100ml:0.9%,软袋双阀)50MLiv微泵维持 | actual=枸橼酸舒芬太尼注射液（鄂宜昌人福-50ug:1ml）200UG+氯化钠注射液（丰原-100ml:0.9%,软袋双阀）50MLiv微泵维持
- block_16 `入量_其他` strict=mismatch eval=canonical_equal: gold=磷酸奥司他韦75mgpo;复方磺胺甲噁唑片（华中药业-0.48gX100片）4片胃管滴入;水100ml | actual=磷酸奥司他韦75mgpo;复方磺胺甲噁唑片(华中药业-0.48gX100片)4片胃管滴入;水100ml
- block_16 `入量_静脉用药` strict=mismatch eval=substantive_mismatch: gold=氯化钠注射液(丰原-100ml：0.9%，软袋双阀)48ML+盐酸右美托咪定注射液（辰欣药业-0.2mg：2ml）0.4MGiv微泵维持 | actual=氯化钠注射液(丰原-100ml:0.9%,软袋双阀)48L+盐酸右美托咪定注射液(辰欣药业-0.2mg:2ml)0.4MGiv微泵维持

## qwen25_72b M Diffs
- block_00 `入量_静脉用药` strict=mismatch eval=separator_error: gold=钠钾镁钙葡萄糖注射液250mliv.gtt250 | actual=钠钾镁钙葡萄糖注射液250mliv.gtt;250
- block_00 `管路护理` strict=mismatch eval=substantive_mismatch: gold=鼻胃管/是/墨绿色// | actual=鼻胃管/是/墨绿色/50
- block_02 `入量_静脉用药` strict=mismatch eval=canonical_equal: gold=氯化钠注射液(丰原-100ml：0.9%，软袋双阀)续用12ml/h+咪达唑仑注射液（苏恩华-5mg：1ml)50MGiv微泵维持 | actual=氯化钠注射液（丰原-100ml：0.9%，软袋双阀）续用12ml/h+咪达唑仑注射液（苏恩华-5mg：1ml)50MGiv微泵维持
- block_04 `入量_静脉用药` strict=mismatch eval=separator_error: gold=钠钾镁钙葡萄糖注射液250mliv.gtt250 | actual=钠钾镁钙葡萄糖注射液250mliv.gtt;250
- block_04 `管路护理` strict=mismatch eval=separator_error: gold=颈内深静脉导管/是///;气管插管/是///23;导尿管/是///;桡动脉导管/是///;静脉留置针/是///;鼻胃管/是///;锁骨下深静脉导管/是///15;股静脉导管/是///43 | actual=颈内深静脉导管/是///;气管插管/是///23;导尿管/是///;桡动脉导管/是///;静脉留置针/是///;鼻胃管/是///;锁骨下深静脉导管/是///15;股静脉导管/是///;43
- block_08 `入量_其他` strict=mismatch eval=separator_error: gold=肠内营养液（SP）500ml胃管滴入 | actual=肠内营养液（SP）500ml胃管;滴入
- block_12 `入量_静脉用药` strict=mismatch eval=substantive_mismatch: gold=NS100ml+甲泼尼龙琥珀酸钠80mgiv.gtt100;咪达唑仑注射液（苏恩华-5mg：1ml）50MG+氯化钠注射液（丰原-100ml：0.9%，软袋双阀）45MLiv微泵维持 | actual=NS100ml+甲泼尼龙琥珀酸钠80mgiv.gt;t100;咪达唑仑注射液（苏恩华-5mg：1ml）50M;G+氯化钠注射液（丰原-100ml:0.9%，软袋双阀）45Liv微泵维持
- block_14 `入量_静脉用药` strict=mismatch eval=substantive_mismatch: gold=枸橼酸舒芬太尼注射液(鄂宜昌人福,-50ug:1ml)200UG+氯化钠注射液(丰原,-100ml:0.9%,软袋双阀)50MLiv微泵维持 | actual=枸酸舒芬太尼注射液(鄂宜昌人福,-50ug：1ml)200UG+氯化钠注射液(丰原,-100ml：0.9%，软袋双阀)50MLiv微泵维;持
- block_16 `入量_其他` strict=mismatch eval=substantive_mismatch: gold=磷酸奥司他韦75mgpo;复方磺胺甲噁唑片（华中药业-0.48gX100片）4片胃管滴入;水100ml | actual=磷酸奥司他韦75mgpo;复方磺胺甲唑片（华中药业-0.48gX100片）4片胃管滴入;水100ml
- block_16 `入量_静脉用药` strict=mismatch eval=canonical_equal: gold=氯化钠注射液(丰原-100ml：0.9%，软袋双阀)48ML+盐酸右美托咪定注射液（辰欣药业-0.2mg：2ml）0.4MGiv微泵维持 | actual=氯化钠注射液（丰原-100ml：0.9%，软袋双阀）48ML+盐酸右美托咪定注射液（辰欣药业-0.2mg：2ml）0.4MGiv微泵维持
- block_16 `出量_尿量` strict=overfill eval=overfill: gold=null | actual=800

## qwen25_32b M Diffs
- block_00 `入量_静脉用药` strict=mismatch eval=substantive_mismatch: gold=钠钾镁钙葡萄糖注射液250mliv.gtt250 | actual=钠钾镁钙葡萄糖注射液250ml iv.gtt
- block_00 `痰_色` strict=mismatch eval=substantive_mismatch: gold=7 | actual=T
- block_00 `痰_量` strict=mismatch eval=substantive_mismatch: gold=1 | actual=7
- block_00 `管路护理` strict=mismatch eval=substantive_mismatch: gold=鼻胃管/是/墨绿色// | actual=鼻胃管/是/墨绿色/
- block_02 `入量_静脉用药` strict=mismatch eval=separator_error: gold=氯化钠注射液(丰原-100ml：0.9%，软袋双阀)续用12ml/h+咪达唑仑注射液（苏恩华-5mg：1ml)50MGiv微泵维持 | actual=氯化钠注射液（丰原-100ml：0.9%，软袋;双阀）续用12ml/h+咪达唑仑注射液（苏;恩华-5mg：1ml)50MGiv微泵维持
- block_03 `入量_静脉用药` strict=mismatch eval=canonical_equal: gold=速尿20mgiv0 | actual=速尿20mg iv 0
- block_04 `入量_其他` strict=overfill eval=overfill: gold=null | actual=250
- block_04 `入量_静脉用药` strict=mismatch eval=substantive_mismatch: gold=钠钾镁钙葡萄糖注射液250mliv.gtt250 | actual=钠钾镁钙葡萄糖注射液250ml iv.gtt
- block_04 `出量_尿量` strict=overfill eval=overfill: gold=null | actual=1
- block_04 `出量_总量` strict=overfill eval=overfill: gold=null | actual=7
- block_04 `痰_色` strict=missing eval=missing: gold=7 | actual=null
- block_04 `痰_量` strict=missing eval=missing: gold=1 | actual=null
- block_04 `管路护理` strict=mismatch eval=substantive_mismatch: gold=颈内深静脉导管/是///;气管插管/是///23;导尿管/是///;桡动脉导管/是///;静脉留置针/是///;鼻胃管/是///;锁骨下深静脉导管/是///15;股静脉导管/是///43 | actual=颈内深静脉导管/是;气管插管/是///23;导尿管/是///;桡动脉导管/是///;静脉留置针/是///;鼻胃管/是///;锁骨下深静脉导管/是///15;股静脉导管/是///;43
- block_05 `入量_静脉用药` strict=mismatch eval=canonical_equal: gold=莫西沙星250mliv.gtt250 | actual=莫西沙星250ml iv.gtt 250
- block_07 `出量_总量` strict=overfill eval=overfill: gold=null | actual=570
- block_08 `入量_其他` strict=mismatch eval=substantive_mismatch: gold=肠内营养液（SP）500ml胃管滴入 | actual=肠内营养液（SP）500ml胃管
- block_09 `入量_其他` strict=mismatch eval=substantive_mismatch: gold=复方磺胺甲噁唑片(华中药业-0.48gX100片)4片胃管滴入 | actual=复方磺胺甲噁唑片（华中药业, -0.48gX100片)4片胃管滴入
- block_09 `入量_静脉用药` strict=mismatch eval=canonical_equal: gold=5%GS100ml+葡萄糖酸钙20MLiv.gtt120 | actual=5%GS100ml+葡萄糖酸钙20MLiv.gtt 120
- block_12 `入量_其他` strict=overfill eval=overfill: gold=null | actual=145;1485
- block_12 `入量_静脉用药` strict=mismatch eval=substantive_mismatch: gold=NS100ml+甲泼尼龙琥珀酸钠80mgiv.gtt100;咪达唑仑注射液（苏恩华-5mg：1ml）50MG+氯化钠注射液（丰原-100ml：0.9%，软袋双阀）45MLiv微泵维持 | actual=NS100ml+甲泼尼龙琥珀酸钠80mgiv.gt;t100;咪达唑仑注射液(苏恩华-5mg:1ml)50M;G+氯化钠注射液（丰原-100ml:0.9%，软;袋双阀）45Liv微泵维持
- block_14 `入量_静脉用药` strict=mismatch eval=substantive_mismatch: gold=枸橼酸舒芬太尼注射液(鄂宜昌人福,-50ug:1ml)200UG+氯化钠注射液(丰原,-100ml:0.9%,软袋双阀)50MLiv微泵维持 | actual=枸橼酸舒芬太尼注射液（鄂宜昌人福, -50ug：1ml）200UG+氯化钠注射液（丰原, 100ml：0.9%，软袋双阀）50MLiv微泵维, 持
- block_16 `入量_其他` strict=mismatch eval=separator_error: gold=磷酸奥司他韦75mgpo;复方磺胺甲噁唑片（华中药业-0.48gX100片）4片胃管滴入;水100ml | actual=磷酸奥司他韦75mgpo;复方磺胺甲噁唑片（华中药业;-0.48gX100片）4片胃管滴入;水100ml
- block_16 `入量_静脉用药` strict=mismatch eval=substantive_mismatch: gold=氯化钠注射液(丰原-100ml：0.9%，软袋双阀)48ML+盐酸右美托咪定注射液（辰欣药业-0.2mg：2ml）0.4MGiv微泵维持 | actual=氯化钠注射液（丰原-100ml：0.9%，软袋）;双阀）48L+盐酸右美托咪定注射液（辰;欣药业-0.2mg：2ml）0.4MGiv微泵维持

## qwen3_8b M Diffs
- block_00 `入量_其他` strict=overfill eval=overfill: gold=null | actual=250
- block_00 `入量_静脉用药` strict=mismatch eval=substantive_mismatch: gold=钠钾镁钙葡萄糖注射液250mliv.gtt250 | actual=钠钾镁钙葡萄糖注射液250mliv.gtt
- block_02 `入量_静脉用药` strict=mismatch eval=substantive_mismatch: gold=氯化钠注射液(丰原-100ml：0.9%，软袋双阀)续用12ml/h+咪达唑仑注射液（苏恩华-5mg：1ml)50MGiv微泵维持 | actual=氯化钠注射液(丰原-100ml:0.9%,软袋双阀)续用12ml/hr+咪达唑仑注射液(苏恩华-5mg:1ml)50MGiv微泵维持
- block_04 `入量_静脉用药` strict=mismatch eval=separator_error: gold=钠钾镁钙葡萄糖注射液250mliv.gtt250 | actual=钠钾镁钙葡萄糖注射液250mliv.gtt;250
- block_04 `出量_尿量` strict=overfill eval=overfill: gold=null | actual=7
- block_04 `痰_色` strict=missing eval=missing: gold=7 | actual=null
- block_08 `入量_其他` strict=mismatch eval=separator_error: gold=肠内营养液（SP）500ml胃管滴入 | actual=肠内营养液（SP）500ml胃管;滴入
- block_09 `入量_静脉用药` strict=mismatch eval=canonical_equal: gold=5%GS100ml+葡萄糖酸钙20MLiv.gtt120 | actual=5%GS100ml+葡萄糖酸钙20ML iv. gtt120
- block_12 `入量_静脉用药` strict=mismatch eval=separator_error: gold=NS100ml+甲泼尼龙琥珀酸钠80mgiv.gtt100;咪达唑仑注射液（苏恩华-5mg：1ml）50MG+氯化钠注射液（丰原-100ml：0.9%，软袋双阀）45MLiv微泵维持 | actual=NS100ml+甲泼尼龙琥珀酸钠80mgiv.gt;t100;咪达唑仑注射液(苏恩华-5mg:1ml)50M;G+氯化钠注射液(丰原-100ml:0.9%,软袋双阀)45MLiv微泵维持
- block_14 `入量_静脉用药` strict=mismatch eval=substantive_mismatch: gold=枸橼酸舒芬太尼注射液(鄂宜昌人福,-50ug:1ml)200UG+氯化钠注射液(丰原,-100ml:0.9%,软袋双阀)50MLiv微泵维持 | actual=枸橼酸舒芬太尼注射液(鄂宜昌人福-50ug:1ml)200UG+氯化钠注射液(丰原-100ml:0.9%,软袋双阀)50MLiv微泵维持
- block_16 `入量_其他` strict=mismatch eval=substantive_mismatch: gold=磷酸奥司他韦75mgpo;复方磺胺甲噁唑片（华中药业-0.48gX100片）4片胃管滴入;水100ml | actual=磷酸奥司他韦75mgpo;复方磺胺甲噁唑片(华中药业-0.2mg：2m1)0.4MGiv微泵维持;水100ml
- block_16 `入量_静脉用药` strict=mismatch eval=canonical_equal: gold=氯化钠注射液(丰原-100ml：0.9%，软袋双阀)48ML+盐酸右美托咪定注射液（辰欣药业-0.2mg：2ml）0.4MGiv微泵维持 | actual=氯化钠注射液(丰原-100ml:0.9%,软袋双阀)48ML+盐酸右美托咪定注射液(辰欣药业-0.2mg:2ml)0.4MGiv微泵维持
- block_16 `出量_大便_颜色性状` strict=overfill eval=overfill: gold=null | actual=1
- block_16 `出量_尿量` strict=overfill eval=overfill: gold=null | actual=7
- block_16 `痰_色` strict=missing eval=missing: gold=7 | actual=null
- block_16 `痰_量` strict=missing eval=missing: gold=1 | actual=null
