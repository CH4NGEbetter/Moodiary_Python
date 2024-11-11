# 使用 Debian slim 版本
FROM debian:bookworm-slim

EXPOSE 5000

# 安装 Python 和基础工具
RUN apt-get update \
    && apt-get install -y python3 python3-venv python3-dev build-essential curl \
    && rm -rf /var/lib/apt/lists/*

# 设置工作目录
WORKDIR /app

# 创建虚拟环境
RUN python3 -m venv /opt/venv

# 激活虚拟环境，并安装依赖
COPY requirements.txt .
RUN /opt/venv/bin/pip install --upgrade pip \
    && /opt/venv/bin/pip install --no-cache-dir -r requirements.txt \
    && /opt/venv/bin/pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu

# 复制项目文件
COPY . .

# 启动Flask应用和RabbitMQ消费者
CMD ["/opt/venv/bin/python", "FlaskTest.py"]
