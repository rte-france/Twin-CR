job "twineu-hello" {
  datacenters = ["dc1"]
  type        = "service"

  group "simulation" {
    count = 1

    network {
      mode = "bridge"

      port "http" {
        to = 80
      }
      port "nats" {
        to = 4222
      }
    }

    task "nginx" {
      driver = "docker"

      config {
        image = "nginx:alpine"
        ports = ["http"]
      }

      resources {
        cpu    = 100
        memory = 128
      }
    }

    # ==========================================
    # TASK 2: NATS
    # ==========================================
    task "nats" {
      driver = "docker"

      config {
        image = "nats:alpine"
        ports = ["nats"]
      }

      resources {
        cpu    = 100
        memory = 128
      }
    }

    service {
      name     = "nginx-test"
      port     = "http"
      provider = "consul"

      tags = [
        "traefik.enable=true",
        "traefik.http.routers.sim-test.rule=PathPrefix(`/sess-test`)",
        "traefik.http.routers.sim-test.entrypoints=web",
        "traefik.http.routers.sim-test.middlewares=sim-test-stripprefix@consulcatalog",
        "traefik.http.middlewares.sim-test-stripprefix.stripprefix.prefixes=/sess-test"
      ]

      check {
        type     = "http"
        path     = "/"
        interval = "10s"
        timeout  = "2s"
      }
    }

    service {
      name     = "nats-test"
      port     = "nats"
      provider = "consul"

      check {
        type     = "tcp"
        interval = "10s"
        timeout  = "2s"
      }
    }
  }
}
