#!/usr/bin/env python3
import os
import json
import time
import psutil
import subprocess
from typing import Dict, List, Optional
import argparse

def get_active_downloads(output_dir: str) -> Dict:
    """获取活动下载信息"""
    active_file = os.path.join(output_dir, "active_downloads.json")
    if os.path.exists(active_file):
        with open(active_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def get_download_status(output_dir: str) -> Dict:
    """获取下载状态"""
    status_file = os.path.join(output_dir, "download_status.json")
    if os.path.exists(status_file):
        with open(status_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"completed": [], "failed": [], "progress": {}}

def get_progress(output_dir: str, ep_num: int) -> Optional[float]:
    """从日志文件中获取下载进度"""
    log_file = os.path.join(output_dir, f"episode_{ep_num}_progress.log")
    if not os.path.exists(log_file):
        return None

    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            if not lines:
                return 0.0

            # 从最后100行中查找进度
            for line in reversed(lines[-100:]):
                if "[download]" in line and "%" in line:
                    try:
                        percent = float(line.split("[download]")[1].split("%")[0].strip())
                        return min(100.0, max(0.0, percent))
                    except (IndexError, ValueError):
                        continue
        return 0.0
    except Exception:
        return None

def is_process_running(pid: int) -> bool:
    """检查进程是否在运行"""
    try:
        return psutil.pid_exists(pid)
    except psutil.NoSuchProcess:
        return False

def monitor_downloads(output_dir: str):
    """监控下载状态"""
    active_downloads = get_active_downloads(output_dir)
    status = get_download_status(output_dir)

    print("\n=== 下载状态监控 ===")
    print(f"存储目录: {output_dir}")

    # 检查已完成和失败的下载
    print("\n✅ 已完成下载:")
    for ep_num in status.get("completed", []):
        print(f"  第 {ep_num} 集: 已完成")

    print("\n❌ 下载失败:")
    for ep_num in status.get("failed", []):
        print(f"  第 {ep_num} 集: 失败")

    # 检查活动下载
    print("\n⏳ 正在下载:")
    if not active_downloads:
        print("   无活动下载")
    else:
        for ep_num, info in active_downloads.items():
            pid = info["pid"]
            progress = get_progress(output_dir, int(ep_num))
            status = "运行中" if is_process_running(pid) else "已停止"

            progress_str = f"{progress:.1f}%" if progress is not None else "未知"
            print(f"  第 {ep_num} 集: {status} (PID: {pid}, 进度: {progress_str})")

def stop_downloads(output_dir: str):
    """停止所有下载进程"""
    active_downloads = get_active_downloads(output_dir)

    if not active_downloads:
        print("没有活动下载需要停止")
        return

    print("正在停止下载进程...")
    stopped = 0

    # 1. 设置停止标志
    stop_flag = os.path.join(output_dir, "stop_flag")
    with open(stop_flag, 'w') as f:
        f.write('1')

    # 2. 终止所有活动进程
    for ep_num, info in active_downloads.items():
        pid = info["pid"]

        try:
            # 尝试优雅地停止进程
            process = psutil.Process(pid)
            for child in process.children(recursive=True):
                child.terminate()
            process.terminate()

            # 等待一段时间后强制终止
            try:
                process.wait(timeout=5)
            except psutil.TimeoutExpired:
                process.kill()

            stopped += 1
            print(f"已停止第 {ep_num} 集的下载进程 (PID: {pid})")
        except psutil.NoSuchProcess:
            print(f"进程 {pid} (第 {ep_num} 集) 已不存在")
        except Exception as e:
            print(f"停止进程 {pid} 时出错: {str(e)}")

    # 3. 清除活动下载记录
    active_file = os.path.join(output_dir, "active_downloads.json")
    if os.path.exists(active_file):
        os.remove(active_file)

    # 4. 检查并终止主进程
    pid_file = os.path.join(output_dir, "download_manager.pid")
    if os.path.exists(pid_file):
        with open(pid_file, 'r') as f:
            main_pid = int(f.read().strip())

        try:
            main_process = psutil.Process(main_pid)
            main_process.terminate()
            print(f"已停止主管理进程 (PID: {main_pid})")
        except psutil.NoSuchProcess:
            print(f"主管理进程 {main_pid} 已不存在")
        except Exception as e:
            print(f"停止主管理进程时出错: {str(e)}")

        os.remove(pid_file)

    print(f"\n已成功停止 {stopped} 个下载进程")

def main():
    parser = argparse.ArgumentParser(description="下载监控和管理工具")
    parser.add_argument("output_dir", help="下载目录路径")
    parser.add_argument("--stop", action="store_true", help="停止所有下载进程")

    args = parser.parse_args()

    if not os.path.exists(args.output_dir):
        print(f"错误: 目录 {args.output_dir} 不存在")
        return

    if args.stop:
        stop_downloads(args.output_dir)
    else:
        monitor_downloads(args.output_dir)

if __name__ == "__main__":
    main()