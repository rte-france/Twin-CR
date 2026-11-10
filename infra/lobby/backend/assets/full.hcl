job "twineu-coucou" {
  datacenters = ["dc1"]
  type        = "service"

  group "twineu-stack" {

    network {
      mode = "bridge"
      port "clickhouse"        { to = 8123 }
      port "nats_client"       { to = 4222 }
      port "gamemaster_http"   { to = 8000 }
      port "scada_http"        { to = 8081 }
      port "gm_http"           { to = 8082 }
      port "configurator_http" { to = 8080 }
    }

    # ----------------------------------------------------
    # FETCH ARTIFACTS (prestart)
    # ----------------------------------------------------
    task "fetch-artifacts" {
      driver = "docker"

      lifecycle {
        hook    = "prestart"
        sidecar = false
      }

      config {
        image   = "busybox:latest"
        command = "true"
      }

      resources {
        cpu    = 50
        memory = 64
      }
    }

    # ----------------------------------------------------
    # CLICKHOUSE
    # ----------------------------------------------------
    task "clickhouse" {
      driver = "docker"

      config {
        image   = "registry.twin.eu/clickhouse-server:latest"
        volumes = ["/alloc/envs/clickhouse_config.xml:/etc/clickhouse-server/config.d/config.xml"]
      }

      env {
        CLICKHOUSE_SKIP_USER_SETUP = "1"
        TZ                         = "Europe/Paris"
      }

      resources {
        cpu        = 200
        memory     = 512
        memory_max = 1024
      }

      service {
        name = "ch-${NOMAD_ALLOC_ID}"
        port = "clickhouse"
        check {
          name     = "Clickhouse Health"
          type     = "http"
          path     = "/ping"
          interval = "10s"
          timeout  = "2s"
        }
      }
    }

    # ----------------------------------------------------
    # NATS
    # ----------------------------------------------------
    task "nats" {
      driver = "docker"

      config {
        image   = "registry.twin.eu/nats:latest"
        command = "-c"
        args    = ["/alloc/envs/nats.conf"]
      }

      resources {
        cpu    = 100
        memory = 256
      }

      service {
        name = "nats-${NOMAD_ALLOC_ID}"
        port = "nats_client"
        check {
          name     = "NATS Client Port"
          type     = "tcp"
          interval = "10s"
          timeout  = "2s"
        }
      }
    }

    task "twineu-core" {
        driver = "docker"

        template {
            destination = "local/wait-deps.env"
            data        = <<EOF
        {{ range service (print "ch-" (env "NOMAD_ALLOC_ID") "|passing") }}CLICKHOUSE_READY=1{{ end }}
        {{ range service (print "nats-" (env "NOMAD_ALLOC_ID") "|passing") }}NATS_READY=1{{ end }}
        EOF
        }

        config {
            image   = "registry.twin.eu/twineu-core:latest"
            command = "/bin/bash"
            args = [
            "-c",
            "chmod +x /alloc/envs/run_orchestrator.sh && bash -c /home/orchestrator/envs/run_orchestrator.sh"
            ]
        }

        env {
            TZ       = "Europe/Paris"
            NATS_URL = "nats://nats-${NOMAD_ALLOC_ID}.service.consul:4222"
        }

        resources {
            cpu    = 200
            memory = 512
        }

        service {
            name = "twineu-core-${NOMAD_ALLOC_ID}"
            check {
            name     = "Orchestrator Healthcheck"
            type     = "script"
            command  = "test"
            args     = ["-f", "/tmp/orchestrator_healthcheck"]
            interval = "5s"
            timeout  = "5s"
            task     = "twineu-core"
            }
        }
    }

  }
}
