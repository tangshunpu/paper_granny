#!/usr/bin/env bash
# =============================================================
# Paper Granny (论文奶奶) - 一键部署脚本
# 支持 macOS / Ubuntu / Debian / CentOS / Fedora / Arch
#
# 一键安装 (从 GitHub 下载并部署):
#   curl -fsSL https://raw.githubusercontent.com/tangshunpu/paper_granny/main/deploy.sh | bash
#   wget -qO- https://raw.githubusercontent.com/tangshunpu/paper_granny/main/deploy.sh | bash
#
# Linux 后台常驻 (systemd):
#   ./deploy.sh              # 安装依赖 + 注册 systemd 服务并启动
#   sudo systemctl status paper-granny
#   sudo systemctl stop paper-granny
#   journalctl -u paper-granny -f
# =============================================================
set -euo pipefail

APP_NAME="Paper Granny"
REPO_URL="https://github.com/tangshunpu/paper_granny.git"
INSTALL_DIR="${INSTALL_DIR:-$HOME/paper_granny}"
PORT="${PORT:-8000}"
HOST="${HOST:-0.0.0.0}"
SERVICE_NAME="paper-granny"

# ---------- 颜色输出 ----------
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

info()  { echo -e "${BLUE}[INFO]${NC}  $*"; }
ok()    { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
err()   { echo -e "${RED}[ERROR]${NC} $*"; exit 1; }

# ---------- 平台检测 ----------
detect_os() {
    if [[ "$OSTYPE" == "darwin"* ]]; then
        OS="macos"
        INIT_SYSTEM="launchd"
    elif [[ -f /etc/os-release ]]; then
        . /etc/os-release
        case "$ID" in
            ubuntu|debian|linuxmint|pop) OS="debian" ;;
            centos|rhel|rocky|alma|fedora) OS="rhel" ;;
            arch|manjaro|endeavouros) OS="arch" ;;
            *) OS="linux-unknown" ;;
        esac
        # 检测 init 系统
        if command -v systemctl &>/dev/null && systemctl --version &>/dev/null; then
            INIT_SYSTEM="systemd"
        else
            INIT_SYSTEM="other"
        fi
    else
        OS="linux-unknown"
        INIT_SYSTEM="other"
    fi
    info "检测到系统: $OS ($OSTYPE), init: $INIT_SYSTEM"
}

# ---------- 从 GitHub 下载项目 ----------
clone_or_update_repo() {
    if [[ -d "$INSTALL_DIR/.git" ]]; then
        info "项目已存在，拉取最新代码..."
        cd "$INSTALL_DIR"
        git pull --ff-only || warn "git pull 失败，使用现有代码继续"
    else
        info "从 GitHub 克隆项目到 $INSTALL_DIR ..."
        if command -v git &>/dev/null; then
            git clone "$REPO_URL" "$INSTALL_DIR"
        else
            # 没有 git 则用 tarball
            info "未找到 git，使用 tarball 下载..."
            mkdir -p "$INSTALL_DIR"
            curl -fsSL "https://github.com/tangshunpu/paper_granny/archive/refs/heads/main.tar.gz" \
                | tar -xz --strip-components=1 -C "$INSTALL_DIR"
        fi
        cd "$INSTALL_DIR"
    fi
    ok "项目目录: $INSTALL_DIR"
}

# ---------- 安装系统依赖 ----------
install_system_deps() {
    info "检查系统依赖..."

    case "$OS" in
        macos)
            if ! command -v brew &>/dev/null; then
                err "请先安装 Homebrew: https://brew.sh"
            fi
            if ! command -v python3 &>/dev/null; then
                info "安装 Python..."
                brew install python@3.12
            fi
            if ! command -v xelatex &>/dev/null; then
                info "安装 MacTeX (这可能需要一些时间)..."
                brew install --cask mactex-no-gui
                eval "$(/usr/libexec/path_helper)"
            fi
            if ! command -v git &>/dev/null; then
                brew install git
            fi
            ;;
        debian)
            info "更新包管理器..."
            sudo apt-get update -qq
            sudo apt-get install -y git curl python3 python3-pip python3-venv 2>/dev/null || true
            if ! command -v xelatex &>/dev/null; then
                info "安装 TeX Live + 中文支持 (这可能需要一些时间)..."
                sudo apt-get install -y \
                    texlive-xetex \
                    texlive-lang-chinese \
                    texlive-fonts-recommended \
                    texlive-fonts-extra \
                    texlive-latex-extra \
                    fonts-noto-cjk
            fi
            ;;
        rhel)
            if command -v dnf &>/dev/null; then
                PKG="dnf"
            else
                PKG="yum"
            fi
            sudo $PKG install -y git curl python3 python3-pip
            if ! command -v xelatex &>/dev/null; then
                info "安装 TeX Live + 中文支持..."
                sudo $PKG install -y \
                    texlive-xetex \
                    texlive-collection-langchinese \
                    texlive-collection-fontsrecommended \
                    texlive-collection-latexextra \
                    google-noto-sans-cjk-fonts
            fi
            ;;
        arch)
            sudo pacman -S --noconfirm --needed git curl python python-pip
            if ! command -v xelatex &>/dev/null; then
                info "安装 TeX Live + 中文支持..."
                sudo pacman -S --noconfirm --needed \
                    texlive-xetex \
                    texlive-langchinese \
                    texlive-fontsrecommended \
                    texlive-fontsextra \
                    texlive-latexextra \
                    noto-fonts-cjk
            fi
            ;;
        *)
            warn "未知发行版，请手动安装: git, Python 3.10+, XeLaTeX, 中文字体"
            ;;
    esac
}

# ---------- 版本检查 ----------
check_python_version() {
    local ver
    ver=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
    local major minor
    major=$(echo "$ver" | cut -d. -f1)
    minor=$(echo "$ver" | cut -d. -f2)
    if [[ "$major" -lt 3 ]] || { [[ "$major" -eq 3 ]] && [[ "$minor" -lt 10 ]]; }; then
        err "需要 Python 3.10+，当前版本: $ver"
    fi
    ok "Python $ver"
}

check_xelatex() {
    if command -v xelatex &>/dev/null; then
        ok "XeLaTeX 已安装"
    else
        err "XeLaTeX 未找到，请检查安装"
    fi
}

# ---------- Python 虚拟环境 ----------
setup_venv() {
    local venv_dir="$INSTALL_DIR/.venv"
    if [[ ! -d "$venv_dir" ]]; then
        info "创建虚拟环境..."
        python3 -m venv "$venv_dir"
    fi
    # shellcheck source=/dev/null
    source "$venv_dir/bin/activate"
    ok "虚拟环境已激活: $venv_dir"
}

install_python_deps() {
    info "安装 Python 依赖..."
    pip install --upgrade pip -q
    pip install -r "$INSTALL_DIR/requirements.txt" -q
    ok "Python 依赖安装完成"
}

# ---------- 配置文件 ----------
setup_config() {
    if [[ ! -f "$INSTALL_DIR/config.local.yaml" ]]; then
        info "创建 config.local.yaml (请填入你的 API Key)..."
        cat > "$INSTALL_DIR/config.local.yaml" << 'YAML'
# 本地配置覆盖 (此文件已被 gitignore)
# 取消注释并填入你的 API Key

llm:
  provider: openai
  model: gpt-4o
#  api_key: "sk-..."

# 或使用其他 provider:
# llm:
#   provider: deepseek
#   model: deepseek-chat
#   api_key: "sk-..."
YAML
        warn "请编辑 $INSTALL_DIR/config.local.yaml 填入 API Key，或设置环境变量"
    else
        ok "config.local.yaml 已存在"
    fi
}

# ---------- systemd 服务 (Linux 常驻后台) ----------
setup_systemd_service() {
    if [[ "$INIT_SYSTEM" != "systemd" ]]; then
        warn "当前系统不支持 systemd，跳过服务注册"
        return
    fi

    info "配置 systemd 服务..."

    local service_file="/etc/systemd/system/${SERVICE_NAME}.service"
    local venv_python="$INSTALL_DIR/.venv/bin/python"

    sudo tee "$service_file" > /dev/null << EOF
[Unit]
Description=Paper Granny - AI arXiv Paper Reader
After=network.target

[Service]
Type=simple
User=$(whoami)
Group=$(id -gn)
WorkingDirectory=$INSTALL_DIR
ExecStart=$venv_python -m uvicorn src.server:app --host $HOST --port $PORT
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal

# 环境变量 (API Key)
EnvironmentFile=-$INSTALL_DIR/.env

# 安全加固
NoNewPrivileges=true
ProtectSystem=strict
ReadWritePaths=$INSTALL_DIR/papers
ProtectHome=read-only

[Install]
WantedBy=multi-user.target
EOF

    sudo systemctl daemon-reload
    sudo systemctl enable "$SERVICE_NAME"
    sudo systemctl restart "$SERVICE_NAME"

    ok "systemd 服务已注册并启动: $SERVICE_NAME"
}

# ---------- launchd 服务 (macOS 常驻后台) ----------
setup_launchd_service() {
    if [[ "$INIT_SYSTEM" != "launchd" ]]; then
        return
    fi

    info "配置 launchd 服务..."

    local plist_label="com.papergranny.server"
    local plist_file="$HOME/Library/LaunchAgents/${plist_label}.plist"
    local venv_python="$INSTALL_DIR/.venv/bin/python"
    local log_dir="$HOME/Library/Logs/PaperGranny"
    mkdir -p "$log_dir"

    cat > "$plist_file" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>${plist_label}</string>
    <key>ProgramArguments</key>
    <array>
        <string>${venv_python}</string>
        <string>-m</string>
        <string>uvicorn</string>
        <string>src.server:app</string>
        <string>--host</string>
        <string>${HOST}</string>
        <string>--port</string>
        <string>${PORT}</string>
    </array>
    <key>WorkingDirectory</key>
    <string>${INSTALL_DIR}</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>${log_dir}/stdout.log</string>
    <key>StandardErrorPath</key>
    <string>${log_dir}/stderr.log</string>
</dict>
</plist>
EOF

    launchctl unload "$plist_file" 2>/dev/null || true
    launchctl load "$plist_file"

    ok "launchd 服务已注册并启动: $plist_label"
}

# ---------- 输出信息 ----------
print_banner() {
    echo ""
    echo -e "${GREEN}============================================${NC}"
    echo -e "${GREEN}  $APP_NAME 部署完成!${NC}"
    echo -e "${GREEN}============================================${NC}"
    echo ""
    echo -e "  Web UI:    ${BLUE}http://localhost:${PORT}${NC}"
    echo -e "  项目目录:  ${BLUE}${INSTALL_DIR}${NC}"
    echo ""

    if [[ "$INIT_SYSTEM" == "systemd" ]]; then
        echo -e "  ${GREEN}服务已在后台运行 (systemd)${NC}"
        echo ""
        echo -e "  常用命令:"
        echo -e "    ${YELLOW}sudo systemctl status  $SERVICE_NAME${NC}  # 查看状态"
        echo -e "    ${YELLOW}sudo systemctl stop    $SERVICE_NAME${NC}  # 停止"
        echo -e "    ${YELLOW}sudo systemctl restart $SERVICE_NAME${NC}  # 重启"
        echo -e "    ${YELLOW}journalctl -u $SERVICE_NAME -f${NC}       # 查看日志"
    elif [[ "$INIT_SYSTEM" == "launchd" ]]; then
        echo -e "  ${GREEN}服务已在后台运行 (launchd)${NC}"
        echo ""
        echo -e "  常用命令:"
        echo -e "    ${YELLOW}launchctl list | grep papergranny${NC}    # 查看状态"
        echo -e "    ${YELLOW}launchctl unload ~/Library/LaunchAgents/com.papergranny.server.plist${NC}  # 停止"
        echo -e "    ${YELLOW}tail -f ~/Library/Logs/PaperGranny/stdout.log${NC}  # 查看日志"
    fi

    echo ""
    echo -e "  CLI 用法:"
    echo -e "    ${YELLOW}cd $INSTALL_DIR && source .venv/bin/activate${NC}"
    echo -e "    ${YELLOW}python -m src.main --url <arxiv_url_or_id>${NC}"
    echo ""

    if [[ ! -f "$INSTALL_DIR/.env" ]] && ! grep -q 'api_key:.*"sk-' "$INSTALL_DIR/config.local.yaml" 2>/dev/null; then
        echo -e "  ${RED}[!] 请配置 API Key:${NC}"
        echo -e "      ${YELLOW}cp $INSTALL_DIR/.env.example $INSTALL_DIR/.env${NC}"
        echo -e "      ${YELLOW}vim $INSTALL_DIR/.env${NC}"
        echo -e "      然后重启服务: ${YELLOW}sudo systemctl restart $SERVICE_NAME${NC}"
        echo ""
    fi
}

# ---------- 主流程 ----------
main() {
    echo ""
    echo -e "${GREEN}=== $APP_NAME 一键部署 ===${NC}"
    echo ""

    detect_os
    install_system_deps
    clone_or_update_repo
    cd "$INSTALL_DIR"
    check_python_version
    check_xelatex
    setup_venv
    install_python_deps
    setup_config

    # 注册并启动后台服务
    if [[ "$INIT_SYSTEM" == "systemd" ]]; then
        setup_systemd_service
    elif [[ "$INIT_SYSTEM" == "launchd" ]]; then
        setup_launchd_service
    fi

    print_banner
}

main "$@"
