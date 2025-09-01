variable "redis_password" {
  description = "Redis password"
  type        = string
  default     = "trading_password"
  sensitive   = true
}

variable "postgres_password" {
  description = "PostgreSQL password"
  type        = string
  default     = "trading_password"
  sensitive   = true
}

variable "grafana_password" {
  description = "Grafana admin password"
  type        = string
  default     = "admin"
  sensitive   = true
}

variable "sentiment_service_image" {
  description = "Sentiment service Docker image"
  type        = string
  default     = "sentiment-trading-sentiment-service:latest"
}

variable "trading_service_image" {
  description = "Trading service Docker image"
  type        = string
  default     = "sentiment-trading-trading-service:latest"
}

variable "dashboard_service_image" {
  description = "Dashboard service Docker image"
  type        = string
  default     = "sentiment-trading-dashboard-service:latest"
}

variable "twitter_api_key" {
  description = "Twitter API key"
  type        = string
  default     = ""
  sensitive   = true
}

variable "twitter_api_secret" {
  description = "Twitter API secret"
  type        = string
  default     = ""
  sensitive   = true
}

variable "reddit_client_id" {
  description = "Reddit client ID"
  type        = string
  default     = ""
  sensitive   = true
}

variable "reddit_client_secret" {
  description = "Reddit client secret"
  type        = string
  default     = ""
  sensitive   = true
}

variable "news_api_key" {
  description = "News API key"
  type        = string
  default     = ""
  sensitive   = true
}

variable "alpaca_api_key" {
  description = "Alpaca API key"
  type        = string
  default     = ""
  sensitive   = true
}

variable "alpaca_secret_key" {
  description = "Alpaca secret key"
  type        = string
  default     = ""
  sensitive   = true
}

variable "alpaca_base_url" {
  description = "Alpaca base URL"
  type        = string
  default     = "https://paper-api.alpaca.markets"
}
