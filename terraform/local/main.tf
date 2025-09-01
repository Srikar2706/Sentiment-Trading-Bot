terraform {
  required_version = ">= 1.0"
  required_providers {
    docker = {
      source  = "kreuzwerker/docker"
      version = "~> 3.0"
    }
    local = {
      source  = "hashicorp/local"
      version = "~> 2.0"
    }
  }
}

provider "docker" {
  host = "unix:///var/run/docker.sock"
}

# Local file for configuration
resource "local_file" "docker_compose_config" {
  filename = "${path.module}/generated-docker-compose.yml"
  content = templatefile("${path.module}/docker-compose.tftpl", {
    redis_password = var.redis_password
    postgres_password = var.postgres_password
    grafana_password = var.grafana_password
    sentiment_service_image = var.sentiment_service_image
    trading_service_image = var.trading_service_image
    dashboard_service_image = var.dashboard_service_image
  })
}

# Docker networks
resource "docker_network" "sentiment_network" {
  name = "sentiment-trading-network"
  driver = "bridge"
}

# Redis container
resource "docker_container" "redis" {
  name  = "sentiment-redis"
  image = "redis:7-alpine"
  
  networks_advanced {
    name = docker_network.sentiment_network.name
  }
  
  command = [
    "redis-server",
    "--appendonly", "yes",
    "--requirepass", var.redis_password
  ]
  
  ports {
    internal = 6379
    external = 6379
  }
  
  volumes {
    volume_name    = "redis_data"
    container_path = "/data"
  }
  
  healthcheck {
    test         = ["CMD", "redis-cli", "--raw", "incr", "ping"]
    interval     = "30s"
    timeout      = "10s"
    retries      = 3
    start_period = "10s"
  }
  
  restart = "unless-stopped"
}

# PostgreSQL container
resource "docker_container" "postgres" {
  name  = "sentiment-postgres"
  image = "postgres:15-alpine"
  
  networks_advanced {
    name = docker_network.sentiment_network.name
  }
  
  env = [
    "POSTGRES_DB=sentiment_trading",
    "POSTGRES_USER=trading_user",
    "POSTGRES_PASSWORD=${var.postgres_password}"
  ]
  
  ports {
    internal = 5432
    external = 5432
  }
  
  volumes {
    volume_name    = "postgres_data"
    container_path = "/var/lib/postgresql/data"
  }
  
  healthcheck {
    test         = ["CMD-SHELL", "pg_isready -U trading_user -d sentiment_trading"]
    interval     = "30s"
    timeout      = "10s"
    retries      = 3
    start_period = "10s"
  }
  
  restart = "unless-stopped"
}

# Sentiment Service container
resource "docker_container" "sentiment_service" {
  name  = "sentiment-analyzer"
  image = var.sentiment_service_image
  
  networks_advanced {
    name = docker_network.sentiment_network.name
  }
  
  env = [
    "REDIS_URL=redis://:${var.redis_password}@sentiment-redis:6379/0",
    "POSTGRES_URL=postgresql://trading_user:${var.postgres_password}@sentiment-postgres:5432/sentiment_trading",
    "TWITTER_API_KEY=${var.twitter_api_key}",
    "TWITTER_API_SECRET=${var.twitter_api_secret}",
    "REDDIT_CLIENT_ID=${var.reddit_client_id}",
    "REDDIT_CLIENT_SECRET=${var.reddit_client_secret}",
    "NEWS_API_KEY=${var.news_api_key}"
  ]
  
  ports {
    internal = 8001
    external = 8001
  }
  
  healthcheck {
    test         = ["CMD", "curl", "-f", "http://localhost:8001/health"]
    interval     = "30s"
    timeout      = "10s"
    retries      = 3
    start_period = "30s"
  }
  
  restart = "unless-stopped"
  
  depends_on = [
    docker_container.redis,
    docker_container.postgres
  ]
}

# Trading Service container
resource "docker_container" "trading_service" {
  name  = "trading-bot"
  image = var.trading_service_image
  
  networks_advanced {
    name = docker_network.sentiment_network.name
  }
  
  env = [
    "REDIS_URL=redis://:${var.redis_password}@sentiment-redis:6379/0",
    "POSTGRES_URL=postgresql://trading_user:${var.postgres_password}@sentiment-postgres:5432/sentiment_trading",
    "ALPACA_API_KEY=${var.alpaca_api_key}",
    "ALPACA_SECRET_KEY=${var.alpaca_secret_key}",
    "ALPACA_BASE_URL=${var.alpaca_base_url}"
  ]
  
  ports {
    internal = 8002
    external = 8002
  }
  
  healthcheck {
    test         = ["CMD", "curl", "-f", "http://localhost:8002/health"]
    interval     = "30s"
    timeout      = "10s"
    retries      = 3
    start_period = "30s"
  }
  
  restart = "unless-stopped"
  
  depends_on = [
    docker_container.redis,
    docker_container.postgres,
    docker_container.sentiment_service
  ]
}

# Dashboard Service container
resource "docker_container" "dashboard_service" {
  name  = "trading-dashboard"
  image = var.dashboard_service_image
  
  networks_advanced {
    name = docker_network.sentiment_network.name
  }
  
  env = [
    "REDIS_URL=redis://:${var.redis_password}@sentiment-redis:6379/0",
    "POSTGRES_URL=postgresql://trading_user:${var.postgres_password}@sentiment-postgres:5432/sentiment_trading"
  ]
  
  ports {
    internal = 8501
    external = 8501
  }
  
  healthcheck {
    test         = ["CMD", "curl", "-f", "http://localhost:8501/_stcore/health"]
    interval     = "30s"
    timeout      = "10s"
    retries      = 3
    start_period = "30s"
  }
  
  restart = "unless-stopped"
  
  depends_on = [
    docker_container.redis,
    docker_container.postgres
  ]
}

# Prometheus container
resource "docker_container" "prometheus" {
  name  = "sentiment-prometheus"
  image = "prom/prometheus:latest"
  
  networks_advanced {
    name = docker_network.sentiment_network.name
  }
  
  ports {
    internal = 9090
    external = 9090
  }
  
  volumes {
    volume_name    = "prometheus_data"
    container_path = "/prometheus"
  }
  
  command = [
    "--config.file=/etc/prometheus/prometheus.yml",
    "--storage.tsdb.path=/prometheus",
    "--web.console.libraries=/etc/prometheus/console_libraries",
    "--web.console.templates=/etc/prometheus/consoles",
    "--storage.tsdb.retention.time=200h",
    "--web.enable-lifecycle"
  ]
  
  restart = "unless-stopped"
}

# Grafana container
resource "docker_container" "grafana" {
  name  = "sentiment-grafana"
  image = "grafana/grafana:latest"
  
  networks_advanced {
    name = docker_network.sentiment_network.name
  }
  
  env = [
    "GF_SECURITY_ADMIN_PASSWORD=${var.grafana_password}"
  ]
  
  ports {
    internal = 3000
    external = 3000
  }
  
  volumes {
    volume_name    = "grafana_data"
    container_path = "/var/lib/grafana"
  }
  
  restart = "unless-stopped"
  
  depends_on = [
    docker_container.prometheus
  ]
}

# Outputs
output "services_urls" {
  description = "Service URLs"
  value = {
    dashboard = "http://localhost:8501"
    sentiment_api = "http://localhost:8001"
    trading_api = "http://localhost:8002"
    prometheus = "http://localhost:9090"
    grafana = "http://localhost:3000"
  }
}

output "network_name" {
  description = "Docker network name"
  value = docker_network.sentiment_network.name
}
