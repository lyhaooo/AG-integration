# MA4PGO V3 Frontend

React + Vite 前端，统一运行 EoH、FunSearch、Our，并比较 gap 与单实例平均耗时。

## 启动

```bash
cd frontend
npm install
npm run dev
```

默认访问 http://localhost:5173，API 通过 Vite 代理转发至后端 `http://127.0.0.1:8000`。

## 页面

- **运行中心**：三种方法均可运行；仅 Our 展示生成代码
- **方法比较**：比较各数据集 gap 与平均耗时，下载 compare.csv
- **Our 参数/提示词**：保留原模板的配置功能
