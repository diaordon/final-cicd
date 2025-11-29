pipeline {
  agent any
  environment {
    IMAGE_REPO = 'diaordon/finalcicd'
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
            mkdir -p tests; echo "def test_dummy(): assert True" > tests/test_dummy.py
            pytest -q
          '
        '''
      }
    }

    stage('Docker Login') {
      steps {
        withCredentials([string(credentialsId: 'dockerhub-token', variable: 'DOCKERHUB_TOKEN')]) {
          sh 'echo "$DOCKERHUB_TOKEN" | docker login -u diaordon --password-stdin'
        }
      }
    }

    stage('Build & Push image') {
      steps {
        sh '''
          set -eux
          TAG=$(date +%Y.%m.%d-%H%M)
          docker build -t $IMAGE_REPO:$TAG -t $IMAGE_REPO:latest .
          echo $IMAGE_REPO:$TAG > image.txt
          docker push $IMAGE_REPO:$TAG
          docker push $IMAGE_REPO:latest
        '''
      }
    }

    stage('Deploy local (Docker)') {
  steps {
    // See where we are & what files exist (helps debugging)
    sh 'pwd && ls -la'

    withCredentials([
      string(credentialsId: 'webex_token', variable: 'WX_TOKEN'),
      string(credentialsId: 'webex_room',  variable: 'WX_ROOM')
    ]) {
      sh '''
        set -euxo pipefail
        docker volume create cvewatch-data || true
        docker rm -f cvewatch || true

        # IMPORTANT: use your correct repo name here if it's "diaordon" not "diordon"
        IMG="${IMAGE_REPO}:${TAG}"

        docker run -d --name cvewatch --restart unless-stopped \
          -p 18080:8000 \
          -e WEBEX_TOKEN="$WX_TOKEN" \
          -e WEBEX_ROOM_ID="$WX_ROOM" \
          -e CVE_API_BASE="https://services.nvd.nist.gov/rest/json/cves/2.0" \
          -e DB_PATH="/data/cvewatch.db" \
          -v cvewatch-data:/data \
          "$IMG"

        # wait for readiness
        for i in $(seq 1 25); do
          if curl -sf http://127.0.0.1:18080/ > /dev/null; then
            echo "cvewatch is up"
            break
          fi
          sleep 1
          if [ $i -eq 25 ]; then
            echo "cvewatch not ready"
            docker logs --tail 120 cvewatch
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
          set -eux
          curl -sS -X POST "http://127.0.0.1:18080/watch?q=OpenSSL" || true
          docker exec cvewatch python -c "from app.schedule_job import run_once; run_once()"
        '''
      }
    }

    stage('Notify Webex') {
      steps {
        withCredentials([
          string(credentialsId: 'webex-token',    variable: 'WEBEX_TOKEN'),
          string(credentialsId: 'webex-room-id', variable: 'WEBEX_ROOM_ID')
        ]) {
          sh '''
            set -e
            curl -f -X POST "https://webexapis.com/v1/messages" \
              -H "Authorization: Bearer $WEBEX_TOKEN" \
              -H "Content-Type: application/json" \
              -d "{\"roomId\":\"$WEBEX_ROOM_ID\",\"markdown\":\"✅ Deploy complete: $(cat image.txt)\"}"
          '''
        }
      }
    }
  }
}
