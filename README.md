# 🦾 Zero 机械臂控制系统

一个基于 **Vue 3** + **Spring Boot** + **FastAPI** 的开源六轴机械臂控制系统，集成 **YOLO 视觉识别**、**大模型对话** 和 **逆运动学规划**。

[![Docker Build](https://github.com/YOUR_USERNAME/zero-robotic-arm/actions/workflows/docker-publish.yml/badge.svg)](https://github.com/YOUR_USERNAME/zero-robotic-arm/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## ✨ 核心特性

- 🎮 **3D 可视化控制**：实时显示机械臂状态，直观操作
- 🧠 **AI 视觉识别**：YOLOv8 物体检测，自动抓取
- 💬 **自然语言控制**：通过对话控制机械臂动作
- 🔧 **逆运动学规划**：自动计算最优路径
- 📡 **硬件集成**：串口通信，支持实体机械臂
- 🐳 **一键部署**：Docker Compose 快速启动

---

## 🚀 快速开始（2 分钟）

### 前置要求

- [Docker Desktop](https://www.docker.com/products/docker-desktop/)（已安装并运行）
- Git

### Windows 用户

```cmd
# 1. 克隆仓库
git clone https://github.com/YOUR_USERNAME/zero-robotic-arm.git
cd zero-robotic-arm\robot-control-system

# 2. 一键启动（使用自动脚本）
deploy.bat
```

### Linux/Mac 用户

```bash
# 1. 克隆仓库
git clone https://github.com/YOUR_USERNAME/zero-robotic-arm.git
cd zero-robotic-arm/robot-control-system

# 2. 给脚本执行权限并启动
chmod +x deploy.sh
./deploy.sh
```

### 手动启动

```bash
# 拉取预构建镜像并启动（首次约 1-2 分钟）
docker-compose pull
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

### 访问系统

- 🌐 **前端界面**: http://localhost
- 📡 **后端 API**: http://localhost:8080
- 🤖 **AI 服务**: http://localhost:8000

---

## 📖 文档导航

- 📘 **[部署指南](docs/DEPLOYMENT_GUIDE.md)** - Docker 和本地部署完整教程
- 🔧 **[硬件调试指南](docs/HARDWARE_DEBUG_GUIDE.md)** - 连接实体机械臂
- 📊 **[项目进度报告](docs/PROJECT_STATUS.md)** - 当前状态和开发计划


---

## 🛠️ 开发者模式

如果你需要修改代码并重新构建：

1. 编辑 `docker-compose.yml`，注释掉 `image` 行，取消注释 `build` 部分
2. 修改源码
3. 重新构建并启动：

```bash
docker-compose build
docker-compose up -d
```

---

## 🏗️ 系统架构

```
Frontend (Vue 3)  ←→  Backend (Spring Boot)  ←→  Hardware
      ↕                       ↕
AI Service (FastAPI + YOLO + LLM)
```

**技术栈**：
- **前端**：Vue 3 + Three.js + Element Plus
- **后端**：Spring Boot 3 + WebSocket
- **AI 服务**：FastAPI + YOLOv8 + Gemini API
- **容器化**：Docker + Docker Compose

---

## 📦 项目结构

```
zero-robotic-arm/
├── robot-control-system/       # 主项目
│   ├── frontend/               # Vue 前端
│   ├── backend/                # Spring Boot 后端
│   ├── ai-service/             # Python AI 服务
│   ├── docker-compose.yml      # Docker 编排配置
│   ├── deploy.bat              # Windows 快速启动脚本
│   └── deploy.sh               # Linux/Mac 快速启动脚本
├── docs/                       # 文档
│   ├── DEPLOYMENT_GUIDE.md    # 部署指南（Docker + 本地）
│   ├── HARDWARE_DEBUG_GUIDE.md # 硬件调试指南
│   └── PROJECT_STATUS.md      # 项目进度报告
└── .github/workflows/          # CI/CD 配置
    └── docker-publish.yml      # 自动构建镜像
```

---

## 🔧 配置说明

### AI 服务配置

复制配置模板并填写 API 密钥：

```bash
cd robot-control-system/ai-service
cp config.json.example config.json
# 编辑 config.json，填入你的 GEMINI_API_KEY
```

### 串口设备（可选）

如果要连接实体机械臂，在 `config.json` 中配置：

```json
{
  "SERIAL_ENABLED": true,
  "SERIAL_PORT": "COM3"  // Windows
  // "SERIAL_PORT": "/dev/ttyUSB0"  // Linux
}
```

---

## ❓ 常见问题

### 启动失败？

1. 确认 Docker Desktop 正在运行
2. 检查端口占用：`docker-compose ps`
3. 查看日志：`docker-compose logs -f`

### 镜像拉取慢？

配置 Docker 镜像加速器或使用本地构建：

```bash
# 注释 docker-compose.yml 中的 image 行
# 取消注释 build 部分
docker-compose build
```

### 更多问题？

查看 [部署指南](docs/DEPLOYMENT_GUIDE.md) 或提交 [Issue](https://github.com/YOUR_USERNAME/zero-robotic-arm/issues)

---

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

---

## 📄 开源协议

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件

---

## 🙏 致谢

- [YOLOv8](https://github.com/ultralytics/ultralytics) - 物体检测
- [Three.js](https://threejs.org/) - 3D 渲染
- [Vue.js](https://vuejs.org/) - 前端框架
- [Spring Boot](https://spring.io/projects/spring-boot) - 后端框架

---

⭐ **如果这个项目对你有帮助，请点个 Star！**
