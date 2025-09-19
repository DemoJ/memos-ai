# 使用官方 Python 镜像作为基础
FROM python:3.9-slim

# 设置工作目录
WORKDIR /app

# 将依赖文件复制到工作目录
COPY requirements.txt .

# 安装依赖
# 使用 --no-cache-dir 减小镜像体积
# 安装 requirements.txt 中定义的其他依赖
RUN pip install --no-cache-dir -r requirements.txt

# 将项目文件复制到工作目录
COPY . .

# 暴露 FastAPI 默认端口
EXPOSE 8000

# 设置容器启动命令
# 注意：在 app.main 中 uvicorn 应该绑定到 0.0.0.0 才能从外部访问
CMD ["python", "-m", "app.main"]