import os


def get_data(file_path):
    """
    读取并解析 .fjs 文件，返回:
    - n_jobs: int
    - n_machines: int
    - durations: list[list[list[tuple[int, int]]]]
      结构为 durations[job_idx][op_idx] = [(machine_id, process_time), ...]
      其中 machine_id 为 0-based。
    """
    if not os.path.isfile(file_path):
        print("file_path is not a valid file path")
        return None, None, None

    try:
        with open(file_path, "r", encoding="utf-8") as file:
            lines = [line.strip() for line in file if line.strip()]
    except Exception:
        print("failed to read the file")
        return None, None, None

    if not lines:
        print("the file is empty")
        return None, None, None

    # 将文本统一拉平成 token 流，兼容不同换行组织方式
    all_tokens = []
    for line in lines:
        all_tokens.extend(line.split())

    if len(all_tokens) < 2:
        print("the file is not valid")
        return None, None, None

    try:
        n_jobs = int(all_tokens[0])
        n_machines = int(all_tokens[1])
    except ValueError:
        return None

    # 第一行可能包含第三个统计字段（如平均可选机器数）
    pos = 3 if len(all_tokens) > 2 else 2
    durations = []

    try:
        for _ in range(n_jobs):
            if pos >= len(all_tokens):
                print("the file is not valid")
                return None, None, None

            n_ops = int(all_tokens[pos])
            pos += 1

            job_ops = []
            for _ in range(n_ops):
                if pos >= len(all_tokens):
                    print("the file is not valid")
                    return None, None, None

                n_candidates = int(all_tokens[pos])
                pos += 1

                if n_candidates <= 0 or pos + 2 * n_candidates > len(all_tokens):
                    print("the file is not valid")
                    return None, None, None

                op_candidates = []
                for _ in range(n_candidates):
                    machine_id_1_based = int(all_tokens[pos])
                    process_time = int(all_tokens[pos + 1])
                    pos += 2

                    # 数据集一般为 1-based 机器编号，转换为 0-based
                    machine_id = max(0, machine_id_1_based - 1)
                    op_candidates.append((machine_id, process_time))

                job_ops.append(op_candidates)

            durations.append(job_ops)
    except ValueError:
        print("the file is not valid")
        return None, None, None

    return n_jobs, n_machines, durations


if __name__ == "__main__":
    fjsp_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    file_path = os.path.join(fjsp_dir, "data", "Barnes", "mt10x.fjs")
    n_jobs, n_machines, durations = get_data(file_path)
    print(n_jobs, n_machines, durations)

