class GetPrompts():
    def __init__(self):
        self.prompt_task = "When solving Flexible Job Shop Scheduling (FJSP) with heuristic methods, two heuristic operators are needed: an operation selection operator and a machine selection operator. The operation selection operator is already available. Please design a machine selection operator. In each step, one operation has already been selected (by the existing operation selection operator); this operator selects one machine from the eligible machines for that operation; that operation will then be assigned to the selected machine. The overall goal is to minimize the makespan."
        self.prompt_func_structure = "def select_machine(machine_process_times, machine_available_time):\
            \n\t# Your code here\n\treturn machine_id"
        self.prompt_func_outputs = ["machine_id"]
        self.prompt_inout_inf = "'machine_process_times' is a list of tuples [(machine_id, process_time), ...] for the selected job's current operation, i.e., eligible machines and their processing times.\
            'machine_available_time' is an array where machine_available_time[machine_id] is the earliest available time (the time when the machine can start working) for that machine.\
            The output named 'machine_id' is the selected machine id (must be one of the eligible machine_ids from machine_process_times). If no eligible machine exists, return 0. If there are eligible machines, do not return None!"
        self.prompt_other_inf = "Note that all inputs are of type int or list. You must output exactly: \
(1) One-sentence algorithm description inside a brace; \
(2) Then a single Python code block that defines the machine selection function only: \
    - def select_machine(machine_process_times, machine_available_time): ... and it must return a variable named exactly 'machine_id' (an integer for one of the eligible machines). \
The function should be novel and sufficiently complex to achieve better performance. Ensure self-consistency and valid Python with proper 4-space indentation. \
Function content and output variables should be consistent, ensuring that variables in the function that have the same meaning as the output variable are defined with the same name as the output variable. \
Do not implement select_operation; only implement select_machine. \
Include the following imports at the beginning of the code: 'import numpy as np', and 'from numba import jit'. Place '@jit(nopython=True)' just above the 'priority' function definition if you define one."

    def get_task(self):
        return self.prompt_task

    def get_func_structure(self):
        return self.prompt_func_structure

    def get_func_outputs(self):
        return self.prompt_func_outputs

    def get_inout_inf(self):
        return self.prompt_inout_inf

    def get_other_inf(self):
        return self.prompt_other_inf
    
