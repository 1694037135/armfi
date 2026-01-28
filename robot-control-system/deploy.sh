#!/bin/bash

# ==============================================================
# Zero 机械臂控制系统 - Docker 快速部署脚本
# ==============================================================

set -e  # 遇到错误立即退出

echo "🚀 开始部署 Zero 机械臂控制系统..."

# 检查 Docker 是否安装
if ! command -v docker &> /dev/null; then
    echo "❌ 错误: 未检测到 Docker，请先安装 Docker"
    exit 1
fi

# 检查 Docker Compose 是否安装
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "❌ 错误: 未检测到 Docker Compose，请先安装"
    exit 1
fi

# 进入项目目录
cd "$(dirname "$0")"

echo ""
echo "📋 请选择部署方式:"
echo "  1) 使用预构建镜像（推荐，快速）"
echo "  2) 本地构建镜像（完整，较慢）"
echo ""
read -p "请输入选项 [1/2]: " choice

case $choice in
    1)
        echo ""
        echo "📦 拉取预构建镜像..."
        docker-compose pull || {
            echo "⚠️  拉取镜像失败，将切换到本地构建模式"
            choice=2
        }
        ;;
    2)
        echo ""
        echo "🔨 开始本地构建镜像（这可能需要几分钟）..."
        docker-compose build
        ;;
    *)
        echo "❌ 无效选项，退出"
        exit 1
        ;;
esac

# 启动服务
echo ""
echo "🚀 启动所有服务..."
docker-compose up -d

# 等待服务启动
echo ""
echo "⏳ 等待服务启动..."
sleep 5

# 检查服务状态
echo ""
echo "📊 服务状态:"
docker-compose ps

echo ""
echo "✅ 部署完成！"
echo ""
echo "📍 访问地址:"
echo "  - 前端界面: http://localhost"
echo "  - 后端 API: http://localhost:8080"
echo "  - AI 服务: http://localhost:8000"
echo ""
echo "📝 常用命令:"
echo "  - 查看日志: docker-compose logs -f"
echo "  - 停止服务: docker-compose down"
echo "  - 重启服务: docker-compose restart"
echo ""
echo "🎉 祝使用愉快！"
