job "test-advanced" {
  datacenters = ["dc1"]
  type        = "batch"

  group "demo" {
    task "run" {
      driver = "docker"

      config {
        image   = "alpine:latest"
        command = "sh"
        # On affiche le fichier template final (.out), le contenu du zip, et la liste des dossiers
        args    = [
          "-c",
          "echo '=== FICHIER TEMPLATE ===' && cat local/config.json.out && echo '\n\n=== FICHIER ZIP ===' && cat local/mondossier/message.txt && echo '\n\n=== ARBORESCENCE ===' && ls -la local/ && ls -la local/mondossier/"
        ]
      }
    }
  }
}
