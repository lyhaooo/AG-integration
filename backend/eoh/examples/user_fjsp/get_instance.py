import numpy as np
import pickle
import os

class GetData():
    def __init__(self, filename) -> None:
        self.filename = filename
        
    # 读取文件内容，返回文件内容的字符串格式
    # self.filename 为相对 Data 目录的路径，如 "Barnes/01a.fjs" 或 "Hurink/edata/01a.fjs"
    def read_dataset_from_file(self):
        # 基于本脚本所在目录定位 Data 根目录，与 experiment.py 中 DATA_DIR 一致
        _base_dir = os.path.dirname(os.path.abspath(__file__))
        data_dir = os.path.join(_base_dir, "Data")
        file_path = os.path.join(data_dir, self.filename)

        # 检查文件是否存在
        if not os.path.isfile(file_path):
            print(f"警告：文件不存在 -> {file_path}")
            return ""

        # 读取文件内容
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            print(f"读取文件 {self.filename} 失败：{e}")
            return ""
    
    # 解析文件内容，返回工件数、机器数、工序数据
    def parse_fjsp_data(self, input_data_str):
        try:
            # 按行分割，过滤空行和纯空格行
            lines = [line.strip() for line in input_data_str.split('\n') if line.strip()]
            if not lines:
                raise ValueError("文件内容为空")
            
            # 修复：第一行先按字符串分割，仅取前两个转整数（忽略后续浮点数）
            first_line_parts = lines[0].split()
            # 确保至少有2个元素
            if len(first_line_parts) < 2:
                raise ValueError(f"第一行数据不完整：{lines[0]}")
            # 仅提取工件数、机器数（转整数），忽略后续内容
            num_jobs = int(first_line_parts[0])
            num_machines = int(first_line_parts[1])
            
            jobs_data = []
            # 遍历每个工件的行（从第二行开始）
            for job_idx in range(num_jobs):
                # 防止文件行数不足（工件行缺失）
                if job_idx + 1 >= len(lines):
                    raise ValueError(f"工件{job_idx}的行缺失")
                
                job_line = lines[job_idx + 1]
                job_values = list(map(int, job_line.split()))  # 工序数据应为整数
                ptr = 0
                
                # 提取当前工件的工序数
                if ptr >= len(job_values):
                    raise ValueError(f"工件{job_idx}的工序数缺失")
                num_operations = job_values[ptr]
                ptr += 1
                
                operation_data = []
                # 解析每道工序
                for op_idx in range(num_operations):
                    # 防止可选机器数缺失
                    if ptr >= len(job_values):
                        raise ValueError(f"工件{job_idx}工序{op_idx}的可选机器数缺失")
                    num_available_machines = job_values[ptr]
                    ptr += 1
                    
                    machine_time_pairs = []
                    # 解析k对(机器, 时间)
                    for _ in range(num_available_machines):
                        # 防止机器/时间对缺失
                        if ptr + 1 >= len(job_values):
                            raise ValueError(f"工件{job_idx}工序{op_idx}的机器-时间对缺失")
                        machine_id = job_values[ptr] - 1  # 转0开始
                        process_time = job_values[ptr + 1]
                        machine_time_pairs.append((machine_id, process_time))
                        ptr += 2
                    
                    operation_data.append(machine_time_pairs)
                
                jobs_data.append(operation_data)
            
            return num_jobs, num_machines, jobs_data
        
        except Exception as e:
            print(f"解析数据时出错：{e}")
            return None, None, None
    
    # 获取实例数据
    def get_instance(self):
        fjsp_data = self.read_dataset_from_file()
        num_jobs, num_machines, jobs_data = self.parse_fjsp_data(fjsp_data)
        if jobs_data is None:
            return {}
        num_job_operations = [int(len(job_ops)) for job_ops in jobs_data]
        machine_process_times = []
        for job_ops in jobs_data:
            job_machines = [
                [(int(mid), int(ptime)) for mid, ptime in op_machines]
                for op_machines in job_ops
            ]
            machine_process_times.append(job_machines)
        return {
            "num_jobs": int(num_jobs),
            "num_job_operations": num_job_operations,
            "num_machines": int(num_machines),
            "machine_process_times": machine_process_times,
        }

if __name__ == "__main__":
    # 参数为相对 Data 目录的路径，与 experiment.py 中 collect_fjs_in_folder 返回的 rel_to_data 一致
    instance = GetData("Dauzere/01a.fjs").get_instance()
    print(instance)