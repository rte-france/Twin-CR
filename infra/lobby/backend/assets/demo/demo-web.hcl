job "demo-nginx-dynamique" {
  datacenters = ["dc1"]
  group "web" {
    network {
      port "http" {
        to = 8080
      }
    }
    service {
      name     = "demo-nginx"
      port     = "http"
      provider = "consul"
     tags = [
        "traefik.enable=true",
        "traefik.http.routers.demo-nginx.rule=Host(`lobby.twin.eu`) && PathPrefix(`/demo-nginx`)",
        "traefik.http.routers.demo-nginx.entrypoints=web",
        "traefik.http.routers.demo-nginx.priority=100",
        "traefik.http.middlewares.demo-nginx-strip.stripprefix.prefixes=/demo-nginx",
        "traefik.http.routers.demo-nginx.middlewares=demo-nginx-strip",
      ]
      check {
        type     = "tcp"
        interval = "10s"
        timeout  = "2s"
      }
    }
    task "nginx" {
      driver = "docker"
      config {
        image = "nginx:alpine"
        ports = ["http"]
        command = "nginx"
        args    = ["-c", "/local/custom-nginx.conf", "-g", "daemon off;"]
      }
    }
  }
}
