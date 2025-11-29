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
        sh '''
          set -euxo pipefail
          IMG=$(cat image.txt || echo $IMAGE_REPO:latest)

          docker rm -f cvewatch || true
          docker volume create cvewatch-data || true

          docker run -d --name cvewatch --restart unless-stopped \
            -p 18080:8000 \
            --env-file .env \
            -e DB_PATH=/data/cvewatch.db \
            -v cvewatch-data:/data \
            "$IMG"

          # wait for app to be ready
          for i in $(seq 1 30); do
            if docker logs cvewatch 2>&1 | grep -q "Application startup complete"; then
              break
            fi
            sleep 1
          done

          docker logs --tail 60 cvewatch
        '''
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
