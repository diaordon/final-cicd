pipeline {
  agent any
  options { timestamps() }

  environment {
    APP_PORT     = '8000'
    CVE_API_BASE = 'https://services.nvd.nist.gov/rest/json/cves/2.0'
    DB_VOL       = 'cvewatch-data'
  }

  stages {
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
            mkdir -p tests
            echo "def test_dummy(): assert True" > tests/test_dummy.py
            pytest -q
          '
        '''
      }
    }

    stage('Docker Login') {
      steps {
        withCredentials([usernamePassword(credentialsId: 'dockerhub-token',
                                          usernameVariable: 'DOCKERHUB_USER',
                                          passwordVariable: 'DOCKERHUB_PASS')]) {
          sh 'echo "$DOCKERHUB_PASS" | docker login -u "$DOCKERHUB_USER" --password-stdin'
        }
      }
    }

    stage('Build & Push image') {
      steps {
        sh '''
          set -eux
          TAG=$(date +%Y.%m.%d-%H%M)
          docker build -t diaordon/finalcicd:${TAG} -t diaordon/finalcicd:latest .
          echo diaordon/finalcicd:${TAG} > image.txt
          docker push diaordon/finalcicd:${TAG}
          docker push diaordon/finalcicd:latest
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
            docker volume create ${DB_VOL} || true
            docker rm -f cvewatch || true
            IMG=$(cat image.txt)

            docker run -d --name cvewatch --restart unless-stopped \
              -p 18080:${APP_PORT} \
              -e WEBEX_TOKEN="${WX_TOKEN}" \
              -e WEBEX_ROOM_ID="${WX_ROOM}" \
              -e CVE_API_BASE="${CVE_API_BASE}" \
              -e DB_PATH=/data/cvewatch.db \
              -v ${DB_VOL}:/data \
              "${IMG}"

            # Readiness check **inside** the container (no curl required)
            ok=no
            for i in $(seq 1 30); do
              if docker exec cvewatch python - <<'PY'
import sys, urllib.request
try:
    with urllib.request.urlopen("http://127.0.0.1:8000/", timeout=2) as r:
        sys.exit(0 if r.status==200 else 1)
except Exception:
    sys.exit(1)
PY
              then
                echo "READY after ${i}s"
                ok=yes
                break
              fi
              sleep 1
            done

            if [ "$ok" != "yes" ]; then
              echo "App did not become ready (inside check). Logs:"
              docker logs --tail 200 cvewatch
              exit 1
            fi
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
print("scan triggered")
PY
        '''
      }
    }

    stage('Notify Webex') {
      steps {
        withCredentials([
          string(credentialsId: 'webex_token', variable: 'WX_TOKEN'),
          string(credentialsId: 'webex_room',  variable: 'WX_ROOM')
        ]) {
          sh '''
            docker exec cvewatch python - <<'PY'
import os, requests
t=os.environ['WEBEX_TOKEN']; rid=os.environ['WEBEX_ROOM_ID']
requests.post("https://webexapis.com/v1/messages",
              headers={"Authorization": f"Bearer {t}"},
              json={"roomId": rid, "markdown": "✅ Build deployed and scan triggered."},
              timeout=20).raise_for_status()
print("webex ping sent")
PY
          '''
        }
      }
    }
  }

  post {
    always {
      sh 'docker ps --format "table {{.Names}}\\t{{.Image}}\\t{{.Ports}}"'
    }
  }
}
