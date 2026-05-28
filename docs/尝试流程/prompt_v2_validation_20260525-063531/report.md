# Prompt V2 Generalization Report

## Gold Pages

- `gold_smoke_001`: `eval_golds/gold_smoke_001.json`
- `gold_dev_m_002`: `eval_golds/gold_dev_m_002.json`
- `gold_validation_003`: `eval_golds/gold_validation_003.json`

## 每页总表

| page | prompt | strict_total | canonical_only | separator_error | missing | overfill | substantive_mismatch |
|---|---|---:|---:|---:|---:|---:|---:|
| gold_smoke_001 | old | 26 | 1 | 4 | 4 | 5 | 12 |
| gold_smoke_001 | v2 | 22 | 2 | 3 | 4 | 4 | 9 |
| gold_dev_m_002 | old | 20 | 3 | 1 | 4 | 2 | 10 |
| gold_dev_m_002 | v2 | 21 | 3 | 1 | 4 | 3 | 10 |
| gold_validation_003 | old | 28 | 3 | 0 | 7 | 6 | 12 |
| gold_validation_003 | v2 | 26 | 2 | 0 | 7 | 6 | 11 |

## M 区单独表

| page | prompt | M_strict_total | M_canonical_only | M_separator_error | M_missing | M_overfill | M_substantive_mismatch |
|---|---|---:|---:|---:|---:|---:|---:|
| gold_smoke_001 | old | 11 | 1 | 3 | 0 | 1 | 6 |
| gold_smoke_001 | v2 | 7 | 2 | 2 | 0 | 0 | 3 |
| gold_dev_m_002 | old | 7 | 2 | 1 | 0 | 0 | 4 |
| gold_dev_m_002 | v2 | 7 | 2 | 1 | 0 | 0 | 4 |
| gold_validation_003 | old | 8 | 3 | 0 | 0 | 1 | 4 |
| gold_validation_003 | v2 | 6 | 2 | 0 | 0 | 1 | 3 |

## old vs v2 delta

| page | metric | old | v2 | delta |
|---|---|---:|---:|---:|
| gold_smoke_001 | overall.strict_total | 26 | 22 | -4 |
| gold_smoke_001 | overall.canonical_equal | 1 | 2 | 1 |
| gold_smoke_001 | overall.separator_error | 4 | 3 | -1 |
| gold_smoke_001 | overall.missing | 4 | 4 | 0 |
| gold_smoke_001 | overall.overfill | 5 | 4 | -1 |
| gold_smoke_001 | overall.substantive_mismatch | 12 | 9 | -3 |
| gold_smoke_001 | M.strict_total | 11 | 7 | -4 |
| gold_smoke_001 | M.canonical_equal | 1 | 2 | 1 |
| gold_smoke_001 | M.separator_error | 3 | 2 | -1 |
| gold_smoke_001 | M.missing | 0 | 0 | 0 |
| gold_smoke_001 | M.overfill | 1 | 0 | -1 |
| gold_smoke_001 | M.substantive_mismatch | 6 | 3 | -3 |
| gold_dev_m_002 | overall.strict_total | 20 | 21 | 1 |
| gold_dev_m_002 | overall.canonical_equal | 3 | 3 | 0 |
| gold_dev_m_002 | overall.separator_error | 1 | 1 | 0 |
| gold_dev_m_002 | overall.missing | 4 | 4 | 0 |
| gold_dev_m_002 | overall.overfill | 2 | 3 | 1 |
| gold_dev_m_002 | overall.substantive_mismatch | 10 | 10 | 0 |
| gold_dev_m_002 | M.strict_total | 7 | 7 | 0 |
| gold_dev_m_002 | M.canonical_equal | 2 | 2 | 0 |
| gold_dev_m_002 | M.separator_error | 1 | 1 | 0 |
| gold_dev_m_002 | M.missing | 0 | 0 | 0 |
| gold_dev_m_002 | M.overfill | 0 | 0 | 0 |
| gold_dev_m_002 | M.substantive_mismatch | 4 | 4 | 0 |
| gold_validation_003 | overall.strict_total | 28 | 26 | -2 |
| gold_validation_003 | overall.canonical_equal | 3 | 2 | -1 |
| gold_validation_003 | overall.separator_error | 0 | 0 | 0 |
| gold_validation_003 | overall.missing | 7 | 7 | 0 |
| gold_validation_003 | overall.overfill | 6 | 6 | 0 |
| gold_validation_003 | overall.substantive_mismatch | 12 | 11 | -1 |
| gold_validation_003 | M.strict_total | 8 | 6 | -2 |
| gold_validation_003 | M.canonical_equal | 3 | 2 | -1 |
| gold_validation_003 | M.separator_error | 0 | 0 | 0 |
| gold_validation_003 | M.missing | 0 | 0 | 0 |
| gold_validation_003 | M.overfill | 1 | 1 | 0 |
| gold_validation_003 | M.substantive_mismatch | 4 | 3 | -1 |

## 汇总 M 区 delta

| metric | old | v2 | delta |
|---|---:|---:|---:|
| M.strict_total | 26 | 20 | -6 |
| M.canonical_equal | 6 | 6 | 0 |
| M.separator_error | 4 | 3 | -1 |
| M.missing | 0 | 0 | 0 |
| M.overfill | 2 | 1 | -1 |
| M.substantive_mismatch | 14 | 10 | -4 |

## No-Regression

- overall: `pass`

| page | passed | overfill_not_increased | substantive_not_increased | new_errors_not_more_than_resolved | casebook |
|---|---:|---:|---:|---:|---|
| gold_smoke_001 | True | True | True | True |  |
| gold_dev_m_002 | True | True | True | True |  |
| gold_validation_003 | True | True | True | True |  |

## M 区新增错误

- `gold_validation_003` block_13 `入量_其他` eval=overfill: gold=null | old=null | v2=维持

## M 区修复错误

- `gold_smoke_001` block_00 `入量_其他` old_eval=overfill: gold=null | old=250 | v2=null
- `gold_smoke_001` block_00 `入量_静脉用药` old_eval=substantive_mismatch: gold=钠钾镁钙葡萄糖注射液250mliv.gtt250 | old=钠钾镁钙葡萄糖注射液250mliv.gtt | v2=钠钾镁钙葡萄糖注射液250mliv.gtt250
- `gold_smoke_001` block_00 `管路护理` old_eval=substantive_mismatch: gold=鼻胃管/是/墨绿色// | old=鼻胃管/是/墨绿色/ | v2=鼻胃管/是/墨绿色//
- `gold_smoke_001` block_04 `入量_静脉用药` old_eval=separator_error: gold=钠钾镁钙葡萄糖注射液250mliv.gtt250 | old=钠钾镁钙葡萄糖注射液250mliv.gtt;250 | v2=钠钾镁钙葡萄糖注射液250mliv.gtt250
- `gold_validation_003` block_01 `管路护理` old_eval=substantive_mismatch: gold=鼻胃管/是/咖啡色//55 | old=鼻胃管/是/咖啡色/55 | v2=鼻胃管/是/咖啡色//55
- `gold_validation_003` block_06 `入量_每时` old_eval=overfill: gold=null | old=t100 | v2=null
- `gold_validation_003` block_06 `入量_静脉用药` old_eval=substantive_mismatch: gold=NS100ml+亚胺培南西司他丁钠1giv.gtt100 | old=NS100ml+亚胺培南西司他丁钠1giv.gt | v2=NS100ml+亚胺培南西司他丁钠1giv.gtt100
