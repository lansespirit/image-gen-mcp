#!/bin/bash

# Image Gen MCP Server - VPS Deployment Script
# This script sets up the complete production environment on Ubuntu 22.04

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
check_root() {
    if [[ $EUID -eq 0 ]]; then
        log_error "This script should not be run as root. Please run as a regular user with sudo privileges."
        exit 1
    fi
}

# Update system
update_system() {
    log_info "Updating system packages..."
    sudo apt update && sudo apt upgrade -y
    log_success "System updated successfully"
}

# Install Docker
install_docker() {
    log_info "Installing Docker..."
    
    # Remove old versions
    sudo apt remove -y docker docker-engine docker.io containerd runc || true
    
    # Install dependencies
    sudo apt install -y apt-transport-https ca-certificates curl gnupg lsb-release
    
    # Add Docker GPG key
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
    
    # Add Docker repository
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
    
    # Install Docker
    sudo apt update
    sudo apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
    
    # Add user to docker group
    sudo usermod -aG docker $USER
    
    log_success "Docker installed successfully"
}

# Install Docker Compose
install_docker_compose() {
    log_info "Installing Docker Compose..."
    
    # Download and install docker-compose
    DOCKER_COMPOSE_VERSION="2.24.1"
    sudo curl -L "https://github.com/docker/compose/releases/download/v${DOCKER_COMPOSE_VERSION}/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
    
    log_success "Docker Compose installed successfully"
}

# Install Nginx
install_nginx() {
    log_info "Installing and configuring Nginx..."
    
    sudo apt install -y nginx
    sudo systemctl enable nginx
    sudo systemctl start nginx
    
    log_success "Nginx installed and started"
}

# Configure UFW Firewall
configure_firewall() {
    log_info "Configuring UFW firewall..."
    
    # Reset UFW to default
    sudo ufw --force reset
    
    # Default policies
    sudo ufw default deny incoming
    sudo ufw default allow outgoing
    
    # Allow SSH (adjust port if needed)
    sudo ufw allow ssh
    
    # Allow HTTP and HTTPS
    sudo ufw allow 80/tcp
    sudo ufw allow 443/tcp
    
    # Enable UFW
    sudo ufw --force enable
    
    log_success "Firewall configured successfully"
}

# Install Fail2ban
install_fail2ban() {
    log_info "Installing and configuring Fail2ban..."
    
    sudo apt install -y fail2ban
    
    # Create custom jail configuration
    sudo tee /etc/fail2ban/jail.local > /dev/null <<EOF
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 5

[ssh]
enabled = true
port = ssh
filter = sshd
logpath = /var/log/auth.log
maxretry = 3

[nginx-http-auth]
enabled = true
filter = nginx-http-auth
port = http,https
logpath = /var/log/nginx/error.log

[nginx-limit-req]
enabled = true
filter = nginx-limit-req
port = http,https
logpath = /var/log/nginx/error.log
maxretry = 10
EOF

    sudo systemctl enable fail2ban
    sudo systemctl start fail2ban
    
    log_success "Fail2ban installed and configured"
}

# Create application directories
create_directories() {
    log_info "Creating application directories..."
    
    # Create app directory
    sudo mkdir -p /opt/image-gen-mcp
    sudo chown $USER:$USER /opt/image-gen-mcp
    
    # Create data directories
    mkdir -p /opt/image-gen-mcp/{storage,logs,monitoring,nginx,ssl}
    mkdir -p /opt/image-gen-mcp/storage/{images,cache}
    mkdir -p /opt/image-gen-mcp/monitoring/{prometheus,grafana}
    
    log_success "Directories created successfully"
}

# Configure Nginx for the application
configure_nginx() {
    log_info "Configuring Nginx reverse proxy..."
    
    # Remove default site
    sudo rm -f /etc/nginx/sites-enabled/default
    
    # Create application config
    sudo tee /etc/nginx/sites-available/image-gen-mcp > /dev/null <<EOF
# Rate limiting
limit_req_zone \$binary_remote_addr zone=api:10m rate=10r/m;

server {
    listen 80;
    server_name your-domain.com;  # Replace with your domain
    
    # Rate limiting
    limit_req zone=api burst=20 nodelay;
    
    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "no-referrer-when-downgrade" always;
    add_header Content-Security-Policy "default-src 'self' http: https: data: blob: 'unsafe-inline'" always;
    
    # Proxy to Docker container
    location / {
        proxy_pass http://127.0.0.1:3001;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_cache_bypass \$http_upgrade;
        
        # Timeouts
        proxy_connect_timeout       60s;
        proxy_send_timeout          60s;
        proxy_read_timeout          60s;
    }
    
    # Health check endpoint
    location /health {
        proxy_pass http://127.0.0.1:3001/health;
        access_log off;
    }
    
    # Monitoring endpoints (restrict access)
    location /metrics {
        allow 127.0.0.1;
        deny all;
        proxy_pass http://127.0.0.1:3001/metrics;
    }
    
    # Static files (if any)
    location /static/ {
        alias /opt/image-gen-mcp/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}

# Grafana dashboard (optional)
server {
    listen 3000;
    server_name your-domain.com;  # Replace with your domain
    
    # Basic auth for Grafana
    auth_basic "Monitoring Dashboard";
    auth_basic_user_file /etc/nginx/.htpasswd;
    
    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

    # Enable the site
    sudo ln -sf /etc/nginx/sites-available/image-gen-mcp /etc/nginx/sites-enabled/
    
    # Test nginx configuration
    sudo nginx -t
    
    # Reload nginx
    sudo systemctl reload nginx
    
    log_success "Nginx configured successfully"
}

# Create systemd service for auto-start
create_systemd_service() {
    log_info "Creating systemd service..."
    
    sudo tee /etc/systemd/system/image-gen-mcp.service > /dev/null <<EOF
[Unit]
Description=Image Gen MCP Server
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/image-gen-mcp
ExecStart=/usr/local/bin/docker-compose -f docker-compose.prod.yml up -d
ExecStop=/usr/local/bin/docker-compose -f docker-compose.prod.yml down
ExecReload=/usr/local/bin/docker-compose -f docker-compose.prod.yml restart image-gen-mcp
TimeoutStartSec=0
User=$USER
Group=docker

[Install]
WantedBy=multi-user.target
EOF

    sudo systemctl daemon-reload
    sudo systemctl enable image-gen-mcp
    
    log_success "Systemd service created and enabled"
}

# Create environment file template
create_env_template() {
    log_info "Creating environment configuration..."
    
    cat > /opt/image-gen-mcp/.env.example <<EOF
# OpenAI Configuration
PROVIDERS__OPENAI__API_KEY=your-openai-api-key-here
OPENAI_ORGANIZATION=
OPENAI_BASE_URL=https://api.openai.com/v1

# Server Configuration
SERVER_PORT=3001
LOG_LEVEL=INFO
RATE_LIMIT_RPM=50

# Image Defaults
DEFAULT_QUALITY=auto
DEFAULT_SIZE=1536x1024
DEFAULT_STYLE=vivid
MODERATION_LEVEL=auto

# Storage Configuration
STORAGE_BASE_PATH=/app/storage
STORAGE_RETENTION_DAYS=30
STORAGE_MAX_SIZE_GB=10
STORAGE_CLEANUP_INTERVAL_HOURS=24

# Cache Configuration
CACHE_ENABLED=true
CACHE_BACKEND=redis
CACHE_TTL_HOURS=24
MAX_CACHE_SIZE_MB=500

# Monitoring
GRAFANA_PASSWORD=your-secure-password-here
EOF

    log_warning "Please copy .env.example to .env and configure your settings:"
    log_info "cd /opt/image-gen-mcp && cp .env.example .env && nano .env"
}

# Create monitoring configuration
create_monitoring_config() {
    log_info "Creating monitoring configuration..."
    
    # Prometheus configuration
    mkdir -p /opt/image-gen-mcp/monitoring
    cat > /opt/image-gen-mcp/monitoring/prometheus.yml <<EOF
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  # - "first_rules.yml"
  # - "second_rules.yml"

scrape_configs:
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']

  - job_name: 'image-gen-mcp'
    static_configs:
      - targets: ['image-gen-mcp:3001']
    metrics_path: '/metrics'
    scrape_interval: 30s

  - job_name: 'redis'
    static_configs:
      - targets: ['redis:6379']

  - job_name: 'node-exporter'
    static_configs:
      - targets: ['localhost:9100']
EOF

    # Redis configuration
    cat > /opt/image-gen-mcp/redis.conf <<EOF
# Redis configuration for production
bind 127.0.0.1
protected-mode yes
port 6379
timeout 0
keepalive 300
maxmemory 256mb
maxmemory-policy allkeys-lru
save 900 1
save 300 10
save 60 10000
EOF

    log_success "Monitoring configuration created"
}

# Install SSL certificate (Let's Encrypt)
install_ssl() {
    log_info "Installing Certbot for SSL certificates..."
    
    sudo apt install -y certbot python3-certbot-nginx
    
    log_warning "To enable SSL, run: sudo certbot --nginx -d your-domain.com"
    log_info "Don't forget to set up automatic renewal: sudo crontab -e"
    log_info "Add: 0 12 * * * /usr/bin/certbot renew --quiet"
}

# Create backup script
create_backup_script() {
    log_info "Creating backup script..."
    
    cat > /opt/image-gen-mcp/backup.sh <<'EOF'
#!/bin/bash

# Image Gen MCP Server Backup Script
BACKUP_DIR="/opt/backups/image-gen-mcp"
DATE=$(date +%Y%m%d_%H%M%S)
APP_DIR="/opt/image-gen-mcp"

# Create backup directory
mkdir -p $BACKUP_DIR

# Backup application data
tar -czf "$BACKUP_DIR/storage_$DATE.tar.gz" -C "$APP_DIR" storage/
tar -czf "$BACKUP_DIR/logs_$DATE.tar.gz" -C "$APP_DIR" logs/

# Backup Redis data
docker exec image-gen-mcp-redis redis-cli BGSAVE
sleep 5
docker cp image-gen-mcp-redis:/data/dump.rdb "$BACKUP_DIR/redis_$DATE.rdb"

# Backup configuration
tar -czf "$BACKUP_DIR/config_$DATE.tar.gz" -C "$APP_DIR" .env docker-compose.prod.yml nginx/

# Clean old backups (keep 7 days)
find $BACKUP_DIR -name "*.tar.gz" -mtime +7 -delete
find $BACKUP_DIR -name "*.rdb" -mtime +7 -delete

echo "Backup completed: $DATE"
EOF

    chmod +x /opt/image-gen-mcp/backup.sh
    
    log_success "Backup script created"
    log_info "Set up daily backups with: crontab -e"
    log_info "Add: 0 2 * * * /opt/image-gen-mcp/backup.sh"
}

# Main installation function
main() {
    log_info "Starting Image Gen MCP Server VPS deployment..."
    
    check_root
    update_system
    install_docker
    install_docker_compose
    install_nginx
    configure_firewall
    install_fail2ban
    create_directories
    configure_nginx
    create_systemd_service
    create_env_template
    create_monitoring_config
    install_ssl
    create_backup_script
    
    log_success "VPS setup completed successfully!"
    echo
    log_info "Next steps:"
    echo "1. Configure your environment: cd /opt/image-gen-mcp && cp .env.example .env && nano .env"
    echo "2. Upload your application code to /opt/image-gen-mcp"
    echo "3. Start the services: sudo systemctl start image-gen-mcp"
    echo "4. Configure SSL: sudo certbot --nginx -d your-domain.com"
    echo "5. Set up monitoring access: sudo htpasswd -c /etc/nginx/.htpasswd admin"
    echo
    log_warning "Please reboot the system to ensure all changes take effect"
    log_info "After reboot, you may need to run: newgrp docker"
}

# Run main function
main "$@"
