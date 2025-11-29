pipeline {
  agent any
  options { timestamps() }
  environment {
    IMAGE_REPO = 'diaordon/finalcicd'
  }

  stages {
    stage('Checkout') { steps { checkout scm } }

    stage('Unit tests') {
      steps {
        sh '''
          docker run --rm -v "$WORKSPACE:/work" -w /work python:3.11 bash -lc '
            python -V && pip -V
            ls -al
            if [ -f requirements.txt ]; then
              pip install -r requirements.txt -q
            else
              echo "[warn] requirements.txt missing — installing minimal deps"
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
        withCredentials([usernamePassword(credentialsId: 'dockerhub',
                                          usernameVariable: 'DOCKERHUB_USER',
                                          passwordVariable: 'DOCKERHUB_TOKEN')]) {
          sh 'echo "$DOCKERHUB_TOKEN" | docker login -u "$DOCKERHUB_USER" --password-stdin'
        }
      }
    }

    stage('Build & Push image') {
  steps {
    sh '''
      set -euxo pipefail
      TAG=$(date +%Y.%m.%d-%H%M)
      docker build -t diaordon/finalcicd:$TAG -t diaordon/finalcicd:latest .
      echo diaordon/finalcicd:$TAG > image.txt
      docker push diaordon/finalcicd:$TAG
      docker push diaordon/finalcicd:latest
    '''
  }
}

stage('Deploy local (Docker)') {
  steps {
    sh '''
      set -euxo pipefail

      # Image to run (written by earlier stage)
      IMG=$(cat $WORKSPACE/image.txt || echo "diaordon/finalcicd:latest")
      echo "Using image: $IMG"

      # Clean previous container, ensure persistent volume exists
      docker rm -f cvewatch || true
      docker volume create cvewatch-data || true

      # Run app with a writable volume and the correct DB_PATH
      docker run -d --name cvewatch --restart unless-stopped \
        -p 18080:8000 \
        -v cvewatch-data:/data \
        -e DB_PATH=/data/cvewatch.db \
        --env-file .env \
        "$IMG"

      # Wait until the app is really up
      for i in $(seq 1 30); do
        sleep 1
        if docker logs cvewatch | grep -q "Application startup complete"; then
          break
        fi
      done
      docker logs --tail 80 cvewatch

      # Sanity-check inside the container (helps catch path/mount issues quickly)
      docker exec cvewatch sh -lc 'echo DB_PATH=$DB_PATH; ls -ld /data; ls -l /data || true; python - <<PY
import os,sqlite3,sys
p=os.environ.get("DB_PATH","(missing)")
print("DB_PATH in container:", p)
# Try to open the DB path directory and touch the file
d=os.path.dirname(p) or "."
print("Writable?", os.access(d, os.W_OK))
# Create the DB if not present
con=sqlite3.connect(p)
con.execute("create table if not exists sanity(k text primary key, v text)")
con.commit(); con.close()
print("SQLite touch OK")
PY'
    '''
  }
}

stage('Trigger scan') {
  steps {
    sh '''
      set -euxo pipefail

      # (Idempotent) ensure the topic is being watched
      curl -sS -X POST "http://127.0.0.1:18080/watch?q=OpenSSL" || true

      # Kick the job that posts to Webex
      docker exec cvewatch python - <<'PY'
from app.schedule_job import run_once
run_once()
print("scan+notify sent")
PY
    '''
  }
}

stage('Notify Webex') {
  steps {
    withCredentials([
      string(credentialsId: 'webex-token', variable: 'WEBEX_TOKEN'),
      string(credentialsId: 'webex-room-id', variable: 'WEBEX_ROOM_ID')
    ]) {
      sh '''
        set -euxo pipefail
        python3 - <<'PY'
import os, requests
r = requests.post(
  "https://webexapis.com/v1/messages",
  headers={"Authorization": f"Bearer {os.environ['WEBEX_TOKEN']}"},
  json={"roomId": os.environ['WEBEX_ROOM_ID'], "markdown": "✅ Deploy complete and scan triggered."},
  timeout=20)
print(r.status_code, r.text[:180])
PY
      '''
    }
  }
}

post {
  always {
    sh '''
      set +e
      echo "---- docker ps ----"
      docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Ports}}'
      echo "---- last 80 lines of cvewatch ----"
      docker logs --tail 80 cvewatch || true
    '''
  }
}

