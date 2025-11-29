pipeline {
  agent any
  environment {
    IMAGE_REPO = 'diaordon/finalcicd'   // <- your Docker Hub repo
  }

  stages {
    stage('Checkout') {
      steps {
        deleteDir()
        checkout([$class: 'GitSCM',
          branches: [[name: '*/main']],
          userRemoteConfigs: [[url: 'https://github.com/diaordon/final-cicd.git']]
        ])
        sh 'git log -1 --oneline'
      }
    }

    stage('Unit tests') {
      steps {
        sh '''
          docker run --rm -v "$PWD":/work -w /work python:3.11 bash -lc '
            python -V && pip -V &&
            pip install -r requirements.txt pytest &&
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
          TAG=$(date +%Y.%m.%d-%H%M)
          docker build -t $IMAGE_REPO:$TAG -t $IMAGE_REPO:latest .
          docker push $IMAGE_REPO:$TAG
          docker push $IMAGE_REPO:latest
          echo $IMAGE_REPO:$TAG > image.txt
        '''
      }
    }

    stage('Deploy local (Docker)') {
      steps {
        withCredentials([string(credentialsId: 'webex_token', variable: 'WXT'),
                         string(credentialsId: 'webex_room',  variable: 'WXR')]) {
          sh '''
            IMG=$(cat image.txt)
            docker rm -f cvewatch || true
            docker run -d --name cvewatch -p 18080:8000 \
              -e WEBEX_TOKEN="$WXT" -e WEBEX_ROOM_ID="$WXR" \
              -v "$PWD/cvewatch.db:/app/cvewatch.db" "$IMG"

            # wait for the API to come up (max ~20s)
            for i in $(seq 1 20); do
              curl -fsS http://127.0.0.1:18080/ >/dev/null && break
              sleep 1
            done
          '''
        }
      }
    }

    stage('Trigger scan') {
      steps {
        sh '''
          # ensure a watch exists
          curl -sS -X POST "http://127.0.0.1:18080/watch?q=OpenSSL" >/dev/null || true
          # run one scan inside the container
          docker exec -i cvewatch python - <<'PY'
from app.schedule_job import run_once
run_once()
print("scan done from Jenkins")
PY
        '''
      }
    }

    stage('Notify Webex') {
      steps {
        withCredentials([string(credentialsId: 'webex_token', variable: 'WXT'),
                         string(credentialsId: 'webex_room',  variable: 'WXR')]) {
          sh '''
            IMG=$(cat image.txt)
            curl -sS -X POST https://webexapis.com/v1/messages \
              -H "Authorization: Bearer $WXT" -H "Content-Type: application/json" \
              -d '{"roomId":"'"$WXR"'","markdown":"✅ Deploy complete: **'"$IMG"'**"}' >/dev/null
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

