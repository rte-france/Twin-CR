variable "session_id" {
  type        = string
  description = "Unique Twin-CR session ID"
  default     = "session-1"
}

variable "context_id" {
  type        = string
  description = "S3 context template UUID (e.g. 4Bus, Nordic)"
  default     = "4Bus"
}

variable "config_path" {
  type        = string
  default     = "config.toml"
  description = "Path to the configuration file inside context"
}

variable "base_domain" {
  type        = string
  default     = "twin.local"
  description = "Base domain for Traefik ingress"
}

variable "registry" {
  type        = string
  default     = "172.28.0.2:5000"
  description = "Docker registry URL"
}

variable "garage_endpoint" {
  type        = string
  default     = "http://172.28.0.2:3900"
  description = "S3 storage endpoint"
}

job "twincr-session" {
  datacenters = ["dc1"]
  type        = "service"

  meta {
    session_id  = var.session_id
    context_id  = var.context_id
    config_path = var.config_path
  }

  group "session" {
    count = 1

    vault {
      role = "nomad-workloads"
    }

    network {
      mode = "bridge"
      port "clickhouse"    { to = 8123 }
      port "nats"          { to = 4222 }
      port "core_dsl"      { to = 8000 }
      port "configurator"  { to = 8080 }
      port "scada_http"    { to = 8081 }
      port "gm_http"       { to = 8082 }
    }

    service {
      name         = "session-${var.session_id}-scada"
      port         = "scada_http"
      provider     = "consul"

      tags = [
        "traefik.enable=true",
        "traefik.http.routers.scada-${var.session_id}.rule=Host(`sessions.${var.base_domain}`) && PathPrefix(`/sessions/${var.session_id}/scada`)",
        "traefik.http.routers.scada-${var.session_id}.entrypoints=web,websecure",
        "traefik.http.routers.scada-${var.session_id}.tls=true",
        "traefik.http.routers.scada-${var.session_id}.middlewares=strip-scada-${var.session_id}",
        "traefik.http.middlewares.strip-scada-${var.session_id}.stripprefix.prefixes=/sessions/${var.session_id}/scada"
      ]
    }

    service {
      name         = "session-${var.session_id}-gm"
      port         = "gm_http"
      provider     = "consul"

      tags = [
        "traefik.enable=true",
        "traefik.http.routers.gm-${var.session_id}.rule=Host(`sessions.${var.base_domain}`) && PathPrefix(`/sessions/${var.session_id}/gm`)",
        "traefik.http.routers.gm-${var.session_id}.entrypoints=web,websecure",
        "traefik.http.routers.gm-${var.session_id}.tls=true",
        "traefik.http.routers.gm-${var.session_id}.middlewares=strip-gm-${var.session_id}",
        "traefik.http.middlewares.strip-gm-${var.session_id}.stripprefix.prefixes=/sessions/${var.session_id}/gm"
      ]
    }

    service {
      name         = "session-${var.session_id}-configurator"
      port         = "configurator"
      provider     = "consul"

      tags = [
        "traefik.enable=true",
        "traefik.http.routers.configurator-${var.session_id}.rule=Host(`sessions.${var.base_domain}`) && PathPrefix(`/sessions/${var.session_id}/configurator`)",
        "traefik.http.routers.configurator-${var.session_id}.entrypoints=web,websecure",
        "traefik.http.routers.configurator-${var.session_id}.tls=true",
        "traefik.http.routers.configurator-${var.session_id}.middlewares=strip-configurator-${var.session_id}",
        "traefik.http.middlewares.strip-configurator-${var.session_id}.stripprefix.prefixes=/sessions/${var.session_id}/configurator"
      ]
    }

    service {
      name         = "session-${var.session_id}-core"
      port         = "core_dsl"
      provider     = "consul"

      tags = [
        "traefik.enable=true",
        "traefik.http.routers.core-${var.session_id}.rule=Host(`sessions.${var.base_domain}`) && PathPrefix(`/sessions/${var.session_id}/core`)",
        "traefik.http.routers.core-${var.session_id}.entrypoints=web,websecure",
        "traefik.http.routers.core-${var.session_id}.tls=true",
        "traefik.http.routers.core-${var.session_id}.middlewares=strip-core-${var.session_id}",
        "traefik.http.middlewares.strip-core-${var.session_id}.stripprefix.prefixes=/sessions/${var.session_id}/core"
      ]
    }

    task "nats" {
      driver = "docker"

      lifecycle {
        hook    = "prestart"
        sidecar = true
      }

      config {
        image = "nats:latest"
        args  = ["-js"]
        ports = ["nats"]
      }

      resources {
        cpu    = 150
        memory = 128
      }
    }

    task "clickhouse" {
      driver = "docker"

      lifecycle {
        hook    = "prestart"
        sidecar = true
      }

      config {
        image = "clickhouse/clickhouse-server:latest"
        ports = ["clickhouse"]
      }

      env {
        CLICKHOUSE_SKIP_USER_SETUP = "1"
        TZ                         = "Europe/Paris"
      }

      resources {
        cpu    = 400
        memory = 512
      }
    }

    task "configurator-client" {
      driver = "docker"

      lifecycle {
        hook    = "prestart"
        sidecar = true
      }

      template {
        data = <<EOT
{{ with secret "secret/data/garage" }}
AWS_ACCESS_KEY_ID="{{ .Data.data.access_key }}"
AWS_SECRET_ACCESS_KEY="{{ .Data.data.secret_key }}"
{{ end }}
EOT
        destination = "secrets/s3.env"
        env         = true
      }

      env {
        NATS_URL            = "nats://127.0.0.1:4222"
        AWS_ENDPOINT_URL_S3 = "${var.garage_endpoint}"
        STORAGE_TYPE        = "S3"
        BUCKET              = "context-library"
        BUCKET_ARCHIVE      = "archive"
        MODE                = "CLICKHOUSE"
      }

      config {
        image = "${var.registry}/configurator-client:latest"
        ports = ["configurator"]
      }

      resources {
        cpu    = 200
        memory = 256
      }
    }

    task "session-init" {
      driver = "docker"

      config {
        image   = "curlimages/curl:latest"
        command = "/bin/sh"
        args = [
          "-c",
          "echo 'Waiting for configurator-client...'; until curl -sf http://127.0.0.1:8080/status >/dev/null; do sleep 1; done; echo 'Initializing context ${var.context_id}...'; until curl -fsSL -X GET 'http://127.0.0.1:8080/init/${var.context_id}?config_path=${var.config_path}' >/dev/null; do sleep 2; done; echo 'Session initialized!'"
        ]
      }

      resources {
        cpu    = 50
        memory = 64
      }
    }

    task "twincr-core" {
      driver = "docker"

      env {
        TZ       = "Europe/Paris"
        NATS_URL = "nats://127.0.0.1:4222"
        MODE     = "CLICKHOUSE"
      }

      config {
        image   = "${var.registry}/twincr-core:latest"
        command = "/usr/local/bin/orchestrator_exec"
        args    = ["--from-clickhouse"]
        ports   = ["core_dsl"]

        volumes = [
          "/opt/twincr/simulators:/home/orchestrator/simulators:ro"
        ]
      }

      resources {
        cpu    = 1000
        memory = 1024
      }
    }

    task "argus-scada" {
      driver = "docker"

      config {
        image = "${var.registry}/argus-backend-scada:latest"
        ports = ["scada_http"]
        entrypoint = [
          "java", "-Xmx1g", "-XX:+ExitOnOutOfMemoryError", "-jar", "/app/app_scada.jar"
        ]
        args = [
          "--http-port", "8081",
          "--nats-url", "nats://127.0.0.1:4222",
          "--config-path", "${var.config_path}",
          "--clickhouse-host", "127.0.0.1",
          "--clickhouse-port", "8123",
          "--configurator-host", "127.0.0.1",
          "--configurator-port", "8080",
          "--mode", "CLICKHOUSE",
          "--estim-period", "60"
        ]
      }

      resources {
        cpu    = 400
        memory = 1024
      }
    }

    task "argus-gm" {
      driver = "docker"

      config {
        image = "${var.registry}/argus-backend-gm:latest"
        ports = ["gm_http"]
        entrypoint = [
          "java", "-Xmx1g", "-XX:+ExitOnOutOfMemoryError", "-jar", "/app/app_gm.jar"
        ]
        args = [
          "--http-port", "8082",
          "--nats-url", "nats://127.0.0.1:4222",
          "--config-path", "${var.config_path}",
          "--clickhouse-host", "127.0.0.1",
          "--clickhouse-port", "8123",
          "--configurator-host", "127.0.0.1",
          "--configurator-port", "8080",
          "--mode", "CLICKHOUSE"
        ]
      }

      resources {
        cpu    = 400
        memory = 1024
      }
    }

    task "automata" {
      driver = "docker"

      env {
        NATS_URL = "nats://127.0.0.1:4222"
        MODE     = "CLICKHOUSE"
      }

      config {
        image   = "${var.registry}/automata:latest"
        command = "python"
        args    = ["-u", "automata_launcher.py"]
      }

      resources {
        cpu    = 200
        memory = 256
      }
    }
  }
}
