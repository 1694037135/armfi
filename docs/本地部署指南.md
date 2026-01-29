# 🚀 Zero 机械臂部署指南

本指南涵盖所有部署方式，从零开始搭建 Zero 机械臂控制系统。

---

## 📋 目录

- [Docker 部署（推荐新手）](#docker-部署推荐新手)
- [本地开发环境搭建](#本地开发环境搭建)
- [配置说明](#配置说明)
- [常见问题排查](#常见问题排查)

---

## 🐳 Docker 部署（推荐新手）

### 前置要求

- [Docker Desktop](https://www.docker.com/products/docker-desktop/)（已安装并运行）
- Git

### 快速开始

#### Windows 用户

```cmd
# 1. 克隆仓库
git clone https://github.com/YOUR_USERNAME/zero-robotic-arm.git
cd zero-robotic-arm\robot-control-system

# 2. 一键启动
deploy.bat
```

#### Linux/Mac 用户

```bash
# 1. 克隆仓库
git clone https://github.com/YOUR_USERNAME/zero-robotic-arm.git
cd zero-robotic-arm/robot-control-system

# 2. 给脚本执行权限并启动
chmod +x deploy.sh
./deploy.sh
```

#### 手动启动

```bash
# 拉取预构建镜像并启动
docker-compose pull
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

### 访问系统

启动成功后，在浏览器中访问：

| 服务 | 地址 | 说明 |
|------|------|------|
| 🎮 **控制界面** | http://localhost | 机械臂 3D 可视化控制 |
| 📡 **后端 API** | http://localhost:8080 | REST API 文档 |
| 🤖 **AI 服务** | http://localhost:8000 | AI 服务状态 |

### 常用 Docker 命令

```bash
# 查看运行状态
docker-compose ps

# 查看日志
docker-compose logs -f [service_name]

# 重启服务
docker-compose restart

# 更新到最新版本
git pull
docker-compose pull
docker-compose down
docker-compose up -d
```

---

## 💻 本地开发环境搭建

如果你需要修改代码或不想使用 Docker，可以直接在本地运行。

### 前置要求

1. **Python 3.10+** - [下载地址](https://www.python.org/)（安装时勾选 "Add Python to PATH"）
2. **Node.js 18+** - [下载地址](https://nodejs.org/)（推荐 LTS 版本）
3. **Java 17+** - [下载地址](https://adoptium.net/)（可选，仅后端需要）

### 启动步骤

#### 1️⃣ 启动 AI 服务（Python）

```bash
cd robot-control-system/ai-service

# 创建虚拟环境（推荐）
python -m venv venv

# 激活虚拟环境
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 复制配置文件
cp config.json.example config.json
# 编辑 config.json 填写你的 GEMINI_API_KEY

# 启动服务
python main.py
```

**服务地址**: http://localhost:5000

#### 2️⃣ 启动前端（Vue）

```bash
cd robot-control-system/frontend

# 安装依赖（仅首次）
npm install

# 启动开发服务器
npm run dev
```

**访问地址**: http://localhost:5173

#### 3️⃣ 启动后端（Spring Boot，可选）

如果你的硬件控制逻辑在 Java 端，则需要启动。若直接串口通信到 AI 服务，可跳过。

```bash
cd robot-control-system/backend

# 运行
mvn spring-boot:run
```

**服务地址**: http://localhost:8080

### 快速启动脚本

项目根目录提供了 `start-local.bat`（Windows）一键启动所有本地服务。

---

## ⚙️ 配置说明

### AI 服务配置

复制并编辑 `ai-service/config.json`：

```json
{
  "GEMINI_API_KEY": "your-gemini-api-key-here",
  "GEMINI_MODEL": "gemini-2.0-flash-exp",
  "HTTP_PROXY": "http://127.0.0.1:7890",
  
  "SERIAL_ENABLED": false,
  "SERIAL_PORT": "COM3",
  "SERIAL_BAUDRATE": 115200,
  
  "CAMERA_ENABLED": false,
  "IP_CAMERA_URL": "http://192.168.1.100:8080/video"
}
```

#### 关键配置项

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `GEMINI_API_KEY` | Gemini API 密钥 | 必填 |
| `GEMINI_MODEL` | LLM 模型名称 | `gemini-2.0-flash-exp` |
| `HTTP_PROXY` | 代理设置（可选） | 空 |
| `SERIAL_ENABLED` | 启用串口硬件 | `false` |
| `SERIAL_PORT` | 串口号（Windows: COM3, Linux: /dev/ttyUSB0） | `COM3` |
| `CAMERA_ENABLED` | 启用摄像头 | `false` |
| `IP_CAMERA_URL` | IP Camera 地址 | 空 |

### 获取 Gemini API Key

1. 访问 [Google AI Studio](https://aistudio.google.com/app/apikey)
2. 创建新的 API Key
3. 复制并粘贴到 `config.json` 中

### Docker 串口设备支持（Linux）

如果要在 Docker 中使用串口：

```yaml
# docker-compose.yml
ai-service:
  devices:
    - "/dev/ttyUSB0:/dev/ttyUSB0"
  privileged: true
```

### 端口映射修改

如果默认端口被占用，可修改 `docker-compose.yml`：

```yaml
frontend:
  ports:
    - "3000:80"  # 将主机的 3000 端口映射到容器的 80 端口
```

---

## 🐛 常见问题排查

### Docker 部署问题

#### 问题 1：`docker` 命令找不到

**错误信息**：
```
'docker' 不是内部或外部命令
```

**解决方案**：
1. 确认 Docker Desktop 已安装
2. 重启电脑
3. 打开 Docker Desktop，等待启动完成

---

#### 问题 2：端口被占用

**错误信息**：
```
Error: port 80 is already allocated
```

**解决方案**：

**方式 A**：停止占用端口的程序
```bash
# Windows
netstat -ano | findstr :80
taskkill /PID <进程ID> /F

# Mac/Linux
sudo lsof -i :80
sudo kill -9 <PID>
```

**方式 B**：修改端口映射（见上方配置说明）

---

#### 问题 3：镜像拉取失败

**错误信息**：
```
Error: failed to pull image
```

**解决方案**：

**方式 A**：使用本地构建
```bash
# 编辑 docker-compose.yml，注释 image 行，取消注释 build 部分
docker-compose build
docker-compose up -d
```

**方式 B**：配置镜像加速
在 Docker Desktop 设置 → Docker Engine 添加：
```json
{
  "registry-mirrors": [
    "https://docker.mirrors.ustc.edu.cn"
  ]
}
```

---

#### 问题 4：容器启动后页面打不开

**检查清单**：

1. ✅ Docker 容器是否在运行？
   ```bash
   docker-compose ps
   ```

2. ✅ 是否有错误日志？
   ```bash
   docker-compose logs -f
   ```

3. ✅ 浏览器访问的地址是否正确？
   - ✅ http://localhost（正确）
   - ❌ https://localhost（错误）
   
4. ✅ 防火墙是否阻止？
   - Windows：允许 Docker 通过防火墙
   - Mac/Linux：`sudo ufw allow 80`

---

#### 问题 5：Docker Desktop 启动失败

**Windows 用户**：

1. 启用 WSL 2：
   ```powershell
   # 以管理员运行 PowerShell
   wsl --install
   ```

2. 启用虚拟化（BIOS 设置）：
   - 重启电脑 → 进入 BIOS
   - 启用 `Intel VT-x` 或 `AMD-V`

**Mac 用户**：
- 确认给予了 Docker Desktop 必要的权限（系统偏好设置 → 安全性与隐私）

---

### 本地开发问题

#### 问题 1：Python 依赖安装失败

**错误信息**：某些包无法安装

**解决方案**：
```bash
# 使用国内镜像源
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

---

#### 问题 2：npm 安装速度慢

**解决方案**：
```bash
# 使用淘宝镜像
npm install --registry=https://registry.npmmirror.com
```

---

#### 问题 3：前端无法连接后端

**症状**：浏览器显示连接错误

**解决方案**：
1. 确认 AI 服务正在运行（http://localhost:5000）
2. 检查防火墙设置
3. 查看 AI 服务日志是否有错误

---

### 硬件连接问题

#### 问题 1：串口权限不足（Linux）

**错误信息**：`Permission denied: '/dev/ttyUSB0'`

**解决方案**：
```bash
# 添加用户到 dialout 组
sudo usermod -aG dialout $USER
# 或临时修改权限
sudo chmod 666 /dev/ttyUSB0
```

---

#### 问题 2：找不到串口设备

**解决方案**：
1. 确认 USB 线已连接
2. 安装驱动（CH340/CP2102）
3. Windows：查看设备管理器确认端口号
4. Linux：运行 `ls /dev/ttyUSB* /dev/ttyACM*`

---

## 🎓 下一步

部署成功后，你可以：

1. 📘 阅读 [硬件调试指南](HARDWARE_DEBUG_GUIDE.md) - 连接实体机械臂
2. 📊 查看 [项目状态报告](PROJECT_STATUS.md) - 了解当前进度
3. 🎮 开始使用控制界面 - 探索系统功能

---

## 💬 获取帮助

遇到问题？

- 🐛 提交 [GitHub Issue](https://github.com/YOUR_USERNAME/zero-robotic-arm/issues)
- 💬 加入 [GitHub Discussions](https://github.com/YOUR_USERNAME/zero-robotic-arm/discussions)

---

**文档更新时间**: 2026-01-28
