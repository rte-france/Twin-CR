# Nomad job of one Twin-CR simulation session: the Nomad counterpart of docker-compose-session.yaml.
#
# Self-contained (no file(), refused when Nomad parses a job for its HTTP API): submitted by the session manager through
# that API (/v1/jobs/parse then /v1/jobs, see session-manager/backend/services/nomad_service.py), or with the CLI:
#   nomad job run -var session_id=... -var context_id=... docs/infra/twincr-session.nomad.hcl
#
# The services run their image defaults (start and healthcheck scripts baked in the images, see the Dockerfiles), as
# with compose: only the environment differs. All tasks share the network namespace of the group: they reach each
# other on 127.0.0.1, so the ports below are those of the image defaults and must not collide.
#
# Startup order: nats and clickhouse are prestart sidecars, the other services are main tasks that retry their
# dependencies (NATS connection retried at startup, argus waits for an initialized session), and session-init is
# a poststart task that initializes the session once (what session-manager does with compose).
#
# End of the simulation (normal or crash): the twincr-core container stays up (KEEP_ALIVE_AFTER_EXIT, see
# envs/docker-cmd-orchestrator.sh) after requesting the archive of the simulation, so the session, its services and logs remain
# available until the session is stopped explicitly (nomad job stop, by the session manager). Its health check turns
# critical when the orchestrator has exited.

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
  description = "Path to the configuration file inside context (URL-encoded: put in the /init URL)"
}

variable "resources" {
  type        = map(map(string))
  default     = {}
  description = <<EOT
Resources per service of the session, overriding the defaults of the tasks (sized for a French grid): task name ->
{ cpu (MHz), memory (MB, reserved), memory_max (MB, limit), java_opts (argus-scada, argus-gm: JVM options, e.g. heap) }.
Set by the session manager from the [resources.<task>] tables of the config.toml of the context.
EOT
}

variable "scenario_id" {
  type        = string
  default     = ""
  description = "DSL scenario of the context, URL-encoded (empty: the configurator generates a minimal script)"
}

variable "public_host" {
  type        = string
  default     = "localhost"
  description = "Host of the public URL of the infrastructure: the services are at https://<public_host>/sessions/<session_id>/<service> (passed by the session manager from its SESSION_PUBLIC_URL)"
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
  name        = var.session_id
  id          = var.session_id
  datacenters = ["dc1"]
  type        = "service"

  ui {
    description = "Twin-CR simulation session ${var.session_id}"

    link {
      label = "argus-scada"
      url   = "https://${var.public_host}/sessions/${var.session_id}/argus-scada"
    }

    link {
      label = "argus-gm"
      url   = "https://${var.public_host}/sessions/${var.session_id}/argus-gm"
    }

    link {
      label = "configurator-client"
      url   = "https://${var.public_host}/sessions/${var.session_id}/configurator-client"
    }

    link {
      label = "twincr-core"
      url   = "https://${var.public_host}/sessions/${var.session_id}/twincr-core"
    }

    link {
      label = "clickhouse"
      url   = "https://${var.public_host}/sessions/${var.session_id}/clickhouse"
    }
  }

  meta {
    session_id  = var.session_id
    context_id  = var.context_id
    config_path = var.config_path
    scenario_id = var.scenario_id
  }

  group "session" {
    count = 1

    # Resources, sized for a French transmission network case, smaller grids need less
    # memory is the typical use (reserved for scheduling)
    # memory_max the hard limit above the measured peak (needs memory oversubscription, enabled by the hashicorp role).
    # memory_max defaults to at least memory, so that a context may raise memory alone.

    # A session holds its state in memory and in its ClickHouse (no volume): a failed allocation is not rescheduled
    # elsewhere from scratch, it stays failed for the session manager to report.
    reschedule {
      attempts  = 0
      unlimited = false
    }

    vault {
      role = "nomad-workloads"
    }

    shutdown_delay = "5s"

    network {
      mode = "bridge"
      port "clickhouse"   { to = 8123 }
      port "nats"         { to = 4222 }
      port "core_dsl"     { to = 8000 }
      port "configurator" { to = 8080 }
      port "scada_http"   { to = 8082 }
      port "gm_http"      { to = 8083 }
    }

    # Health checks: the same scripts as the Dockerfile HEALTHCHECKs where the image has one.
    # The argus /health endpoints only answer once the session is initialized (the backends wait for it before
    # starting their HTTP server): on_update = "ignore" keeps them out of the deployment health, which would
    # otherwise never be healthy before session-init, and there is no check_restart on them.

    service {
      name     = "session-${var.session_id}-nats"
      port     = "nats"
      provider = "consul"

      check {
        type     = "tcp"
        interval = "5s"
        timeout  = "2s"
      }
    }

    service {
      name     = "session-${var.session_id}-argus-scada"
      port     = "scada_http"
      provider = "consul"

      tags = [
        "traefik.enable=true",
        "traefik.http.routers.argus-scada-${var.session_id}.rule=Host(`${var.public_host}`) && PathPrefix(`/sessions/${var.session_id}/argus-scada`)",
        "traefik.http.routers.argus-scada-${var.session_id}.entrypoints=web,websecure",
        "traefik.http.routers.argus-scada-${var.session_id}.tls=true",
        "traefik.http.routers.argus-scada-${var.session_id}.middlewares=strip-argus-scada-${var.session_id}",
        "traefik.http.middlewares.strip-argus-scada-${var.session_id}.stripprefix.prefixes=/sessions/${var.session_id}/argus-scada"
      ]

      check {
        type      = "script"
        task      = "argus-scada"
        command   = "sh"
        args      = ["/app/healthcheck.sh", "scada"]
        interval  = "10s"
        timeout   = "10s"
        on_update = "ignore"
      }
    }

    service {
      name     = "session-${var.session_id}-argus-gm"
      port     = "gm_http"
      provider = "consul"

      tags = [
        "traefik.enable=true",
        "traefik.http.routers.argus-gm-${var.session_id}.rule=Host(`${var.public_host}`) && PathPrefix(`/sessions/${var.session_id}/argus-gm`)",
        "traefik.http.routers.argus-gm-${var.session_id}.entrypoints=web,websecure",
        "traefik.http.routers.argus-gm-${var.session_id}.tls=true",
        "traefik.http.routers.argus-gm-${var.session_id}.middlewares=strip-argus-gm-${var.session_id}",
        "traefik.http.middlewares.strip-argus-gm-${var.session_id}.stripprefix.prefixes=/sessions/${var.session_id}/argus-gm"
      ]

      check {
        type      = "script"
        task      = "argus-gm"
        command   = "sh"
        args      = ["/app/healthcheck.sh", "gm"]
        interval  = "10s"
        timeout   = "10s"
        on_update = "ignore"
      }
    }

    service {
      name     = "session-${var.session_id}-configurator-client"
      port     = "configurator"
      provider = "consul"

      tags = [
        "traefik.enable=true",
        "traefik.http.routers.configurator-client-${var.session_id}.rule=Host(`${var.public_host}`) && PathPrefix(`/sessions/${var.session_id}/configurator-client`)",
        "traefik.http.routers.configurator-client-${var.session_id}.entrypoints=web,websecure",
        "traefik.http.routers.configurator-client-${var.session_id}.tls=true",
        "traefik.http.routers.configurator-client-${var.session_id}.middlewares=strip-configurator-client-${var.session_id}",
        "traefik.http.middlewares.strip-configurator-client-${var.session_id}.stripprefix.prefixes=/sessions/${var.session_id}/configurator-client"
      ]

      check {
        type     = "script"
        task     = "configurator-client"
        command  = "bash"
        args     = ["/home/orchestrator/configurator_client/healthcheck.sh"]
        interval = "5s"
        timeout  = "5s"
      }
    }

    # The DSL server of twincr-core only listens once the session is initialized: the check is the orchestrator's
    # healthcheck file instead (created when it waits for a simulation)
    service {
      name     = "session-${var.session_id}-twincr-core"
      port     = "core_dsl"
      provider = "consul"

      tags = [
        "traefik.enable=true",
        "traefik.http.routers.twincr-core-${var.session_id}.rule=Host(`${var.public_host}`) && PathPrefix(`/sessions/${var.session_id}/twincr-core`)",
        "traefik.http.routers.twincr-core-${var.session_id}.entrypoints=web,websecure",
        "traefik.http.routers.twincr-core-${var.session_id}.tls=true",
        "traefik.http.routers.twincr-core-${var.session_id}.middlewares=strip-twincr-core-${var.session_id}",
        "traefik.http.middlewares.strip-twincr-core-${var.session_id}.stripprefix.prefixes=/sessions/${var.session_id}/twincr-core"
      ]

      check {
        type     = "script"
        task     = "twincr-core"
        command  = "bash"
        args     = ["/home/orchestrator/envs/healthcheck_orchestrator.sh"]
        interval = "5s"
        timeout  = "5s"
      }
    }

    service {
      name     = "session-${var.session_id}-clickhouse"
      port     = "clickhouse"
      provider = "consul"

      tags = [
        "traefik.enable=true",
        "traefik.http.routers.clickhouse-${var.session_id}.rule=Host(`${var.public_host}`) && PathPrefix(`/sessions/${var.session_id}/clickhouse`)",
        "traefik.http.routers.clickhouse-${var.session_id}.entrypoints=web,websecure",
        "traefik.http.routers.clickhouse-${var.session_id}.tls=true",
        "traefik.http.routers.clickhouse-${var.session_id}.middlewares=strip-clickhouse-${var.session_id}",
        "traefik.http.middlewares.strip-clickhouse-${var.session_id}.stripprefix.prefixes=/sessions/${var.session_id}/clickhouse"
      ]

      check {
        type     = "http"
        path     = "/ping"
        interval = "5s"
        timeout  = "2s"
      }
    }

    # Same image and configuration as docker-compose-dependencies.yaml
    task "nats" {
      driver = "docker"

      lifecycle {
        hook    = "prestart"
        sidecar = true
      }

      # Same configuration as envs/nats.conf (compose)
      template {
        data        = <<EOT
port: 4222
http_port: 8222
websocket {
  port: 9222
  no_tls: true
}
jetstream {
  enable: true
}
EOT
        destination = "local/nats.conf"
      }

      config {
        # Same version as compose
        image = "${var.registry}/nats:2.14.3"
        args  = ["-c", "/local/nats.conf"]
        ports = ["nats"]
      }

      resources {
        cpu        = lookup(lookup(var.resources, "nats", {}), "cpu", "150")
        memory     = lookup(lookup(var.resources, "nats", {}), "memory", "128")
        memory_max = lookup(lookup(var.resources, "nats", {}), "memory_max", max(256, lookup(lookup(var.resources, "nats", {}), "memory", "128")))
      }
    }

    task "clickhouse" {
      driver = "docker"

      lifecycle {
        hook    = "prestart"
        sidecar = true
      }

      # S3 settings for the archive to Garage (INSERT INTO FUNCTION s3 of the configurator)
      # Same configuration as clickhouse/clickhouse_config.xml (compose)
      template {
        data        = <<EOT
<clickhouse>
    <s3>
        <region>garage</region>
    </s3>
</clickhouse>
EOT
        destination = "local/clickhouse_config.xml"
      }

      env {
        CLICKHOUSE_SKIP_USER_SETUP = "1"
        TZ                         = "Europe/Paris"
      }

      config {
        # Same version as compose
        image   = "${var.registry}/clickhouse/clickhouse-server:26.6.1.1193"
        ports   = ["clickhouse"]
        volumes = ["local/clickhouse_config.xml:/etc/clickhouse-server/config.d/config.xml"]
      }

      resources {
        cpu        = lookup(lookup(var.resources, "clickhouse", {}), "cpu", "800")
        memory     = lookup(lookup(var.resources, "clickhouse", {}), "memory", "1536")
        memory_max = lookup(lookup(var.resources, "clickhouse", {}), "memory_max", max(3072, lookup(lookup(var.resources, "clickhouse", {}), "memory", "1536")))
      }
    }

    # The orchestrator exiting does not end the task (KEEP_ALIVE_AFTER_EXIT). If the task itself dies, it is not
    # restarted: a new orchestrator would not match the state of the configurator (with compose, restart: true restarts
    # it with twincr-core), so the allocation fails instead.
    task "twincr-core" {
      driver = "docker"

      restart {
        attempts = 0
        mode     = "fail"
      }

      env {
        TZ       = "Europe/Paris"
        NATS_URL = "nats://127.0.0.1:4222"
        MODE     = "CLICKHOUSE"
        # Stay up after the simulation (end or crash) until the session is stopped
        KEEP_ALIVE_AFTER_EXIT = "true"
      }

      config {
        image = "${var.registry}/twincr-core:latest"
        force_pull = true
        ports = ["core_dsl"]

        # Provisioned on every client by the session_simulators role (from Twin-CR/simulators.zip)
        volumes = [
          "/opt/twincr/simulators:/home/orchestrator/simulators:ro"
        ]
      }

      resources {
        cpu        = lookup(lookup(var.resources, "twincr-core", {}), "cpu", "2000")
        memory     = lookup(lookup(var.resources, "twincr-core", {}), "memory", "3072")
        memory_max = lookup(lookup(var.resources, "twincr-core", {}), "memory_max", max(4096, lookup(lookup(var.resources, "twincr-core", {}), "memory", "3072")))
      }
    }

    task "configurator-client" {
      driver = "docker"

      template {
        data        = <<EOT
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
        AWS_ENDPOINT_URL_S3 = var.garage_endpoint
        STORAGE_TYPE        = "S3"
        BUCKET              = "context-library"
        BUCKET_ARCHIVE      = "archive"
        MODE                = "CLICKHOUSE"
      }

      config {
        image = "${var.registry}/configurator-client:latest"
        force_pull = true
        ports = ["configurator"]
      }

      resources {
        cpu        = lookup(lookup(var.resources, "configurator-client", {}), "cpu", "200")
        memory     = lookup(lookup(var.resources, "configurator-client", {}), "memory", "256")
        memory_max = lookup(lookup(var.resources, "configurator-client", {}), "memory_max", max(512, lookup(lookup(var.resources, "configurator-client", {}), "memory", "256")))
      }
    }

    # Heap sizes: JAVA_OPTS defaults of argus-backends/docker-cmd.sh (-Xmx2g scada, -Xmx1536m gm), plus JVM overhead
    task "argus-scada" {
      driver = "docker"

      env {
        NATS_URL = "nats://127.0.0.1:4222"
        MODE     = "CLICKHOUSE"
        # Empty: the default of argus-backends/docker-cmd.sh
        JAVA_OPTS = lookup(lookup(var.resources, "argus-scada", {}), "java_opts", "")
      }

      config {
        image = "${var.registry}/argus-backend-scada:latest"
        force_pull = true
        ports = ["scada_http"]
      }

      resources {
        cpu        = lookup(lookup(var.resources, "argus-scada", {}), "cpu", "1500")
        memory     = lookup(lookup(var.resources, "argus-scada", {}), "memory", "2560")
        memory_max = lookup(lookup(var.resources, "argus-scada", {}), "memory_max", max(3584, lookup(lookup(var.resources, "argus-scada", {}), "memory", "2560")))
      }
    }

    task "argus-gm" {
      driver = "docker"

      env {
        NATS_URL  = "nats://127.0.0.1:4222"
        MODE      = "CLICKHOUSE"
        JAVA_OPTS = lookup(lookup(var.resources, "argus-gm", {}), "java_opts", "")
      }

      config {
        image = "${var.registry}/argus-backend-gm:latest"
        force_pull = true
        ports = ["gm_http"]
      }

      resources {
        cpu        = lookup(lookup(var.resources, "argus-gm", {}), "cpu", "200")
        memory     = lookup(lookup(var.resources, "argus-gm", {}), "memory", "1024")
        memory_max = lookup(lookup(var.resources, "argus-gm", {}), "memory_max", max(2048, lookup(lookup(var.resources, "argus-gm", {}), "memory", "1024")))
      }
    }

    # Initializes the session once (session-manager's call with compose). /init needs the configurator, ClickHouse and
    # twincr-core waiting for a simulation (NATS "Start"), and only marks the session READY on success: it is retried
    # until it succeeds, or returns 409 (already initialized, e.g. this task was restarted), for about 5 minutes.
    task "session-init" {
      driver = "docker"

      lifecycle {
        hook    = "poststart"
        sidecar = false
      }

      config {
        # Pinned, from the registry of the cluster (copied by infra:push)
        image   = "${var.registry}/curlimages/curl:8.22.0"
        command = "/bin/sh"
        args = [
          "-c",
          <<EOT
url='http://127.0.0.1:8080/init/${var.context_id}?config_path=${var.config_path}${var.scenario_id != "" ? "&scenario_id=${var.scenario_id}" : ""}'
for i in $(seq 1 60); do
  rm -f /tmp/init.out /tmp/init.headers
  curl -s --noproxy '*' --max-time 300 -o /tmp/init.out -D /tmp/init.headers "$url"
  code=$(head -n 1 /tmp/init.headers 2>/dev/null | cut -d ' ' -f 2)
  case "$code" in
    200) echo "Session initialized: $(cat /tmp/init.out)"; exit 0 ;;
    409) echo "Session already initialized"; exit 0 ;;
    *) echo "Init attempt $i: HTTP $code $(cat /tmp/init.out 2>/dev/null)"; sleep 5 ;;
  esac
done
echo "Session initialization failed"
exit 1
EOT
        ]
      }

      resources {
        cpu    = 50
        memory = 64
      }
    }

    # Automata of the context (automata_commands of its config.toml, e.g. tcp_blocker.py of Nordic), started by the
    # automata launcher once the session is initialized (it waits for the configurator, then reads the input files of
    # the simulation). Poststart, not a sidecar: it ends when its automata end, or right away when there are none. As
    # with compose, its failure does not end the session: its exit code is only logged (a failed task would stop them all).
    task "automata" {
      driver = "docker"

      lifecycle {
        hook    = "poststart"
        sidecar = false
      }

      env {
        NATS_URL = "nats://127.0.0.1:4222"
        MODE     = "CLICKHOUSE"
      }

      config {
        image      = "${var.registry}/automata:latest"
        force_pull = true
        command    = "sh"
        args       = ["-c", "python -u automata_launcher.py || echo \"Automata launcher exited with code $?\""]
      }

      resources {
        cpu        = lookup(lookup(var.resources, "automata", {}), "cpu", "200")
        memory     = lookup(lookup(var.resources, "automata", {}), "memory", "256")
        memory_max = lookup(lookup(var.resources, "automata", {}), "memory_max", max(512, lookup(lookup(var.resources, "automata", {}), "memory", "256")))
      }
    }
  }
}
