# cutter_worker.py
import cv2
import numpy as np
import os
import shutil
import re
import argparse
from paddleocr import PaddleOCR

TIME_PATTERN = re.compile(r"([01]?\d|2[0-3])[:：][0-5]\d")

def get_time_from_zone(img_segment, ocr_engine):
    try:
        if img_segment is None or img_segment.size == 0: return None
        result = ocr_engine.ocr(img_segment, cls=False)
        if not result or not result[0]: return None
        for line in result[0]:
            text = line[1][0].replace(" ", "")
            m = TIME_PATTERN.search(text)
            if m: return m.group(0).replace("：", ":")
    except Exception:
        return None
    return None

def is_summary_row(img_segment, ocr_engine):
    """检测该行是否为"小时小结"行（如24小时小结、72小时小结）"""
    try:
        if img_segment is None or img_segment.size == 0: return False
        result = ocr_engine.ocr(img_segment, cls=False)
        if not result or not result[0]: return False
        full_text = "".join([line[1][0] for line in result[0]]).replace(" ", "")
        if "小时" in full_text and "小结" in full_text:
            return True
    except Exception:
        return False
    return False

# 🌟 新增：从表头一次性提取所有竖线坐标和全局切分点（移植自王主任一单 cutter）
def get_global_splits_by_counting(header_img):
    h, w = header_img.shape[:2]
    gray = cv2.cvtColor(header_img, cv2.COLOR_BGR2GRAY)
    bw = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 35, 15)
    
    v_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 30))
    v_lines = cv2.morphologyEx(bw, cv2.MORPH_OPEN, v_kernel, iterations=2)
    contours, _ = cv2.findContours(v_lines, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    col_xs = []
    for c in contours:
        x, y, cw, ch = cv2.boundingRect(c)
        if ch > 30: col_xs.append(x + cw // 2)
            
    col_xs = sorted(list(set(col_xs)))
    if len(col_xs) > 0:
        merged_xs = [col_xs[0]]
        for v in col_xs[1:]:
            if v - merged_xs[-1] > 10: merged_xs.append(v)
        col_xs = merged_xs

    print(f"🔍 [Worker] 在表头区精确识别到 {len(col_xs)} 根网格竖线")
    
    # 金主任数据切两刀分三部分：生命体征区(L)、出入量区(M)、护理文本区(R)
    if len(col_xs) >= 32: 
        x1, x2 = col_xs[20], col_xs[31] 
        print(f"✅ [Worker] 按网格数定位切分坐标: x1={x1}, x2={x2}")
    else:
        print(f"⚠️ [Worker] 竖线数量异常 ({len(col_xs)} 根)，启用比例兜底")
        target1, target2 = int(w * 0.41), int(w * 0.72)
        x1 = min(col_xs, key=lambda x: abs(x - target1)) if col_xs else target1
        x2 = min(col_xs, key=lambda x: abs(x - target2)) if col_xs else target2
    coords = max(0, min(x1, w-1)), max(x1, min(x2, w-1))
    return coords, col_xs

# 🌟 修改：移除 2 倍放大，仅保留白边补边（彻底解决视觉 Token 爆炸导致的 OOM）
# 🌟 二次修改：新增最长边上限，防止高分辨率切片仍超出 num_ctx 导致模型输出乱码
# 设为 1400px：与 1280px 的 visual token 消耗相同（同为 10 tiles），但保留更多细节
def optimize_image_for_llm(img, max_long_side=1400):
    padded = cv2.copyMakeBorder(img, 40, 40, 40, 40, cv2.BORDER_CONSTANT, value=[255, 255, 255])
    h, w = padded.shape[:2]
    if max(h, w) > max_long_side:
        scale = max_long_side / max(h, w)
        padded = cv2.resize(padded, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
    return padded

# 🌟 新增：保存切片图片+OCR文本到同名txt（移植自王主任二单 cutter）
# 🌟 修改：解耦 OCR 输入图像与 LLM 输入图像
def save_part_with_ocr(img_for_ocr, img_for_llm, base_dir, name_prefix, ocr_engine):
    """
    分离处理逻辑：对纯数据区跑 OCR，对带表头的图像进行优化并保存给 LLM
    """
    # 1. 仅对纯数据区跑 OCR 提取文本，避免表头冗余信息
    res = ocr_engine.ocr(img_for_ocr, cls=False)
    texts = []
    if res and res[0]:
        texts = [line[1][0] for line in res[0]]
    txt_str = ", ".join(texts)
    
    # 2. 保存为同名 txt 字典文件
    with open(os.path.join(base_dir, f"{name_prefix}.txt"), "w", encoding="utf-8") as f:
        f.write(txt_str)
        
    # 3. 将带有表头的图像进行放大补边优化，并保存给 LLM 看
    cv2.imwrite(os.path.join(base_dir, f"{name_prefix}.png"), optimize_image_for_llm(img_for_llm))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--img", required=True, help="输入图片路径")
    parser.add_argument("--out", default="icu_slices", help="输出文件夹")
    args = parser.parse_args()

    img_path = args.img
    output_base = args.out
    # header_bottom_y = 526
    header_bottom_y = 450

    print(f"🔍 [Worker] 子进程启动，开始处理图片: {img_path}")

    if os.path.exists(output_base): shutil.rmtree(output_base)
    os.makedirs(output_base, exist_ok=True)

    img = cv2.imread(img_path)
    if img is None:
        print(f"❌ [Worker] 致命错误：OpenCV 无法读取图片 {img_path}")
        return

    H, W = img.shape[:2]
    print(f"🔍 [Worker] 图片读取成功，分辨率: 宽{W} x 高{H}")

    # 初始化 OCR（vLLM 版本：显式 CPU 模式，所有 GPU 由 vLLM 独占）
    ocr = PaddleOCR(use_angle_cls=False, lang='ch', show_log=False, use_gpu=False)
    print(f"🔍 [Worker] PaddleOCR 模型加载完成（CPU 模式）")

    try:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        bw = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 35, 15)
        h_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (W // 10, 1))
        h_lines = cv2.morphologyEx(bw, cv2.MORPH_OPEN, h_kernel, iterations=2)
        
        contours, _ = cv2.findContours(h_lines, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # 【重要放宽】：只要横线长度超过宽度的 50% 就认（原为 70%）
        all_y = sorted([cv2.boundingRect(c)[1] + cv2.boundingRect(c)[3]//2 for c in contours if cv2.boundingRect(c)[2] > W * 0.5])
        
        if not all_y: 
            print(f"❌ [Worker] 错误：未检测到有效横线 (长度>50%宽度)！")
            # 存下二值化线条图，看看究竟是什么干扰了 OpenCV
            debug_path = os.path.join(output_base, "debug_h_lines_failed.png")
            cv2.imwrite(debug_path, h_lines)
            print(f"📸 [Worker] 已将横线提取的诊断图保存至: {debug_path}，请检查。")
            return
            
        print(f"🔍 [Worker] 检测到 {len(all_y)} 条初筛横线...")
            
        merged_y = [all_y[0]]
        for y in all_y[1:]:
            if y - merged_y[-1] > 15: merged_y.append(y)
            
        print(f"🔍 [Worker] 合并后剩余 {len(merged_y)} 条有效横行边界")
            
    except Exception as e:
        print(f"❌ [Worker] 横线检测阶段发生异常: {e}")
        return

    # 🌟 改进：先把表头截出来，只对表头算一次全局的 X 切分坐标（替代原来每块独立算的 split_into_three_columns）
    header = img[0:header_bottom_y, :]
    (global_x1, global_x2), all_sub_lines = get_global_splits_by_counting(header)

    # 🌟 新增：截取患者信息区（移植自王主任二单 cutter）
    header_info_zone = img[0:300, :]
    cv2.imwrite(os.path.join(output_base, "_header_info.png"), optimize_image_for_llm(header_info_zone))

    time_col_width = int(W * 0.15)
    
    # ================= 🌟 智能孤儿行回收（移植自王主任一单 cutter） =================

    # 1. 动态寻找"数据区"的真正起始线索引 (跳过表头内部的横线)
    start_data_idx = 0
    for i, y in enumerate(merged_y):
        if y >= header_bottom_y - 10: 
            start_data_idx = i
            break

    # 2. 扫描真正的时间锚点与小时小结行 (从数据区起始线开始扫)
    print(f"🔍 [Worker] 正在扫描每一行的时间锚点与小时小结...")
    time_anchors = []
    summary_row_indices = []
    for i in range(start_data_idx, len(merged_y) - 1):
        y_top, y_btm = merged_y[i], merged_y[i+1]
        try:
            # 先用较宽区域检测是否为小时小结行（优先级高于时间检测）
            summary_scan_width = min(int(W * 0.25), W)
            summary_zone = img[y_top:y_btm, :summary_scan_width]
            if is_summary_row(summary_zone, ocr):
                summary_row_indices.append(i)
                print(f"📋 [Worker] 第 {i} 行检测为【小时小结】行 (y={y_top}~{y_btm})")
                continue
            # 再检测时间锚点
            time_zone = img[y_top:y_btm, :time_col_width]
            if get_time_from_zone(time_zone, ocr): 
                time_anchors.append(i) 
        except Exception as e: 
            print(f"⚠️ [Worker] 扫描第 {i} 行时间区域时出错: {e}")
            continue
    print(f"🔍 [Worker] 扫描完成：{len(time_anchors)} 个时间锚点，{len(summary_row_indices)} 个小时小结行")

    # 3. 智能孤儿行回收补丁 (不再无脑插 0，而是插入真正的起跑线；同时跳过小时小结行)
    block_starts = []
    summary_set = set(summary_row_indices)
    if not time_anchors:
        # 极端情况：整页都没时间，找到第一个非小结数据行
        first_non_summary = None
        for i in range(start_data_idx, len(merged_y) - 1):
            if i not in summary_set:
                first_non_summary = i
                break
        if first_non_summary is not None:
            block_starts.append((first_non_summary, ""))
            print(f"⚠️ [Worker] 未找到时间锚点，将非小结数据区整体作为一个块处理")
        else:
            print(f"⚠️ [Worker] 数据区全为小时小结行，无常规数据块")
    else:
        # 🌟 如果第一个时间锚点不在数据区第一行，说明顶部有孤儿行！
        if time_anchors[0] > start_data_idx:
            # 跳过小时小结行，找到第一个非小结的孤儿行作为起始
            first_non_summary = None
            for i in range(start_data_idx, time_anchors[0]):
                if i not in summary_set:
                    first_non_summary = i
                    break
            if first_non_summary is not None:
                block_starts.append((first_non_summary, ""))
            
        for idx in time_anchors:
            block_starts.append((idx, ""))

    # ================= 🌟 孤儿行回收结束 =================

    if not block_starts:
        print(f"❌ [Worker] 致命错误：未能从横线区域提取到任何有效的时间(00:00 格式)！")
        if len(merged_y) > 1:
            cv2.imwrite(os.path.join(output_base, "debug_time_zone.png"), img[merged_y[-2]:merged_y[-1], :time_col_width])
        return

    vis_img = img.copy()
    success_count = 0
    
    for idx in range(len(block_starts)):
        try:
            start_node_idx = block_starts[idx][0]
            y_start = merged_y[start_node_idx]
            
            # 默认的 y_end 逻辑
            if idx < len(block_starts) - 1:
                y_end = merged_y[block_starts[idx+1][0]]
            else:
                y_end = merged_y[-1]

            # 🌟 如果当前块范围内有小时小结行，截断至第一个小结行（避免将小结混入普通数据块）
            for s_idx in sorted(summary_row_indices):
                if start_node_idx < s_idx and merged_y[s_idx] < y_end:
                    y_end = merged_y[s_idx]
                    print(f"  ✂️ [Worker] 数据块 {idx} 因【小时小结】行 (第{s_idx}行) 而截断至 Y={y_end}")
                    break

            # =====================================================================
            # 🌟 新增核心：动态去空白（防 LLM 注意力稀释机制）
            # =====================================================================
            if idx == len(block_starts) - 1:
                # 只有最后一个时间块可能会盲目切到底，我们需要探明其真实的文本底部
                huge_roi = img[y_start:y_end, :]
                
                # 借助已加载的 OCR 引擎快速做一次粗扫（只为获取 Bounding Box 坐标）
                # PaddleOCR 对于大面积空白图片的扫描速度极快，不会造成性能负担
                res = ocr.ocr(huge_roi, cls=False)
                
                max_text_y = 0
                if res and res[0]:
                    for line in res[0]:
                        box = line[0] # 坐标格式: [[x1, y1], [x2, y2], [x3, y3], [x4, y4]]
                        # box[2][1] 和 box[3][1] 是文本框底部的两个 Y 坐标
                        bottom_y = max(box[2][1], box[3][1])
                        if bottom_y > max_text_y:
                            max_text_y = bottom_y
                
                if max_text_y > 0:
                    # 找到了文本，计算其在原图的绝对 Y 坐标（加 15 个像素的容错缓冲，防止切掉偏旁部首）
                    abs_true_bottom = y_start + max_text_y + 15
                    
                    # 将 y_end 向上收缩，吸附到文本下方最近的那条有效网格横线上
                    for y in merged_y[start_node_idx+1:]:
                        if y >= abs_true_bottom:
                            y_end = y
                            break
                    print(f"✂️ [Worker] 触发防空白截断：检测文本真实底部在 Y={int(abs_true_bottom)}，y_end 边界由 {merged_y[-1]} 动态收缩至 {y_end}")
                else:
                    # 极端兜底情况：这一行下面连一个字都没有，纯粹是空表单
                    # 我们只保留当前行及其下面的一行空行（防止高度为0），砍掉多余空白
                    fallback_idx = min(start_node_idx + 2, len(merged_y) - 1)
                    y_end = merged_y[fallback_idx]
                    print(f"✂️ [Worker] 触发防空白截断：下方无任何文本，启用极简兜底边界 Y={y_end}")
            # =====================================================================

            # 1. 提取纯数据行 (专供 OCR 使用)
            data_row = img[y_start:y_end, :]

            # 2. 拼接表头 (专供 LLM 视觉输入使用)
            final_block = np.vstack((header, data_row))
            header_h = header.shape[0]
            
            # 🌟 严谨处理：仅在提供给 LLM 的 final_block 上绘制红色垂直辅助线
            # 这样不仅可以引导 LLM，还避免了红线干扰 PaddleOCR 的文本检测
            for x_line in all_sub_lines:
                cv2.line(final_block, (x_line, header_h), (x_line, final_block.shape[0]), (0, 0, 255), 4)
            
            # --- 3. 分别对两种图像进行列向切分 ---

            # 用于 LLM 的带表头切片 (final_block)
            part_L_llm = final_block[:, 0:global_x1]
            part_M_llm = final_block[:, global_x1:global_x2]
            part_R_llm = final_block[:, global_x2:W]
            
            # 用于 OCR 的纯数据切片 (data_row)
            part_L_ocr = data_row[:, 0:global_x1]
            part_M_ocr = data_row[:, global_x1:global_x2]
            part_R_ocr = data_row[:, global_x2:W]
            
            # 🌟 4. 调用重构后的函数，分别传入 OCR 源图和 LLM 源图
            save_part_with_ocr(part_L_ocr, part_L_llm, output_base, f"block_{idx:02d}_L", ocr)
            save_part_with_ocr(part_M_ocr, part_M_llm, output_base, f"block_{idx:02d}_M", ocr)
            save_part_with_ocr(part_R_ocr, part_R_llm, output_base, f"block_{idx:02d}_R", ocr)
            
            # 画上诊断线，方便预览
            cv2.rectangle(vis_img, (2, y_start), (W-2, y_end), (255, 0, 0), 2) 
            cv2.line(vis_img, (global_x1, y_start), (global_x1, y_end), (0, 0, 255), 3)      
            cv2.line(vis_img, (global_x2, y_start), (global_x2, y_end), (0, 255, 0), 3)  
            success_count += 1
        except Exception as e: 
            print(f"⚠️ [Worker] 切割第 {idx} 块时出错: {e}")
            continue

    # 🌟 保存小时小结行为独立切片（不分 L/M/R，保持全宽）
    summary_count = 0
    for s_idx in summary_row_indices:
        s_y_start = merged_y[s_idx]
        s_y_end = merged_y[s_idx + 1] if (s_idx + 1) < len(merged_y) else merged_y[-1]
        
        summary_data_row = img[s_y_start:s_y_end, :]
        summary_with_header = np.vstack((header, summary_data_row))
        
        # 对纯数据行做 OCR，对带表头图做优化后保存给 LLM
        save_part_with_ocr(summary_data_row, summary_with_header, output_base, f"summary_{summary_count:02d}", ocr)
        
        # 在预览图上用橙色标记小结行
        cv2.rectangle(vis_img, (2, s_y_start), (W-2, s_y_end), (0, 165, 255), 3)
        
        summary_count += 1
        print(f"📋 [Worker] 已保存小时小结切片: summary_{summary_count-1:02d} (y={s_y_start}~{s_y_end})")

    cv2.imwrite(os.path.join(output_base, "_block_preview.png"), vis_img)
    print(f"✅ [Worker] 图片切割顺利完成！共切出 {success_count} 行常规记录碎片 + {summary_count} 行小时小结。")

if __name__ == "__main__":
    main()