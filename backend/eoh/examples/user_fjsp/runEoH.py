from eoh import eoh
from eoh.utils.getParas import Paras
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from prob import FJSP

# Parameter initilization #
paras = Paras() 

# Set your local problem
problem_local = FJSP()

# Set parameters #
paras.set_paras(method = "eoh",    # ['ael','eoh']          # AEL是什么方法？
                problem = problem_local, # Set local problem, else use default problems
                llm_api_endpoint = "one.ocoolai.com", # set your LLM endpoint
                llm_api_key = os.environ.get("LLM_API_KEY", ""),
                llm_model = "gpt-3.5-turbo",
                # llm_model = "qwen3-14b",
                # llm_model = "gpt-5.2",
                ec_pop_size = 2, # number of samples in each population
                ec_n_pop = 4,  # number of populations
                exp_n_proc = 1,  # multi-core parallel
                # eva_numba_decorator = True  # 使用 numba 加速器加速评估函数的计算，使用时会报错，没有看出来这个参数如何影响Parallel的使用
                )

# initilization
evolution = eoh.EVOL(paras)

# run 
evolution.run()
