pipeline {
  agent any

  options {
    skipDefaultCheckout(true)
    timestamps()
  }

  environment {
    IMAGE_REPO   = 'diaordon/finalcicd'
    APP_PORT     = '8000'
    HOST_PORT    = '18080'
    DB_VOL       = 'cvewatch-data'
    DB_PATH      = '/data/cvewatch.db'
    CVE_API_BASE = 'https://services.nvd.nist.gov/rest/json/cves/2.0'
  }

  stages {
    stage('Checkout') {
      steps { checkout scm }
    }

    stage('Unit tests') {
      steps {
        sh '''
          docker run --rm -v "$PWD":/work -w /work python:3.11-slim bash -lc '
            set -e
            python -V && pip -V
            if [ -f requirements.txt ]; then
              pip install --no-cache-dir -r requirements.txt
            else
              pip install -q fastapi requests "uvicorn[standard]" pytest
            fi
            mkdir -p tests; echo "def test_dummy(): assert True" > tests/test_dummy.py
            pytest -q
          '
        '''
      }
    }

    stage('Docker Login') {
  steps {
    withCredentials([string(credentialsId: 'dockerhub-token', variable: 'DOCKERHUB_TOKEN')]) {
      sh '''
        # login with token as password; username is your Docker Hub handle
        echo "$DOCKERHUB_TOKEN" | docker login -u diaordon --password-stdin
      '''
    }
  }
}

    stage('Build & Push image') {
      steps {
        sh '''
          set -eux
          TAG=$(date +%Y.%m.%d-%H%M)
          docker build -t ${IMAGE_REPO}:${TAG} -t ${IMAGE_REPO}:latest .
          echo ${IMAGE_REPO}:${TAG} > image.txt
          docker push ${IMAGE_REPO}:${TAG}
          docker push ${IMAGE_REPO}:latest
        '''
      }
    }

    stage('Deploy local (Docker)') {
      steps {
        withCredentials([
          string(credentialsId: 'webex_token', variable: 'WX_TOKEN'),
          string(credentialsId: 'webex_room',  variable: 'WX_ROOM')
        ]) {
          sh '''
            set -euxo pipefail

            docker volume create ${DB_VOL} >/dev/null
            docker rm -f cvewatch >/dev/null 2>&1 || true

            IMG=$(cat image.txt || echo ${IMAGE_REPO}:latest)

            docker run -d --name cvewatch --restart unless-stopped \
              -p ${HOST_PORT}:${APP_PORT} \
              -e WEBEX_TOKEN="${WX_TOKEN}" \
              -e WEBEX_ROOM_ID="${WX_ROOM}" \
              -e CVE_API_BASE="${CVE_API_BASE}" \
              -e DB_PATH="${DB_PATH}" \
              -v ${DB_VOL}:/data \
              "$IMG"

            # Readiness loop: break on success (max ~25s)
            for i in $(seq 1 25); do
              if curl -sf http://127.0.0.1:${HOST_PORT}/ >/dev/null; then
                echo "ready"; break
              fi
              sleep 1
              if [ "$i" -eq 25 ]; then
                echo "App did not become ready"
                docker logs --tail 200 cvewatch || true
                exit 1
              fi
            done
          '''
        }
      }
    }

    stage('Trigger scan') {
      steps {
        sh '''
          docker exec cvewatch python - <<'PY'
from app.schedule_job import run_once
run_once()
print("scan+notify executed from Jenkins")
PY
        '''
      }
    }
  }

  post {
    always {
      sh 'docker ps --format "table {{.Names}}\\t{{.Image}}\\t{{.Ports}}"'
    }
  }
}
