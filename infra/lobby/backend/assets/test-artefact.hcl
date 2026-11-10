job "test-lecture-s3" {
  datacenters = ["dc1"]

  # Type batch car le job se termine dès qu'il a fini de lire le fichier
  type = "batch"

  group "groupe-test" {
    task "lecture-task" {
      driver = "docker"

      config {
        image   = "alpine:latest"
        # La commande lit le fichier qui a été téléchargé dans le dossier local/
        command = "cat"
        args    = ["local/config-test.json"]
      }

      artifact {
        # Remplacez ceci par l'URL pré-signée générée par votre API backend
        source      = "http://localhost:3900/twineu-files/templates/tpl-jf1c654a_test.hcl?AWSAccessKeyId=..."

        # Le nom que le fichier prendra une fois téléchargé par Nomad
        destination = "local/config-test.json"

        # OBLIGATOIRE : Empêche Nomad d'essayer de dézipper ou d'altérer le fichier téléchargé
        options {
          archive = "false"
        }
      }
    }
  }
}
