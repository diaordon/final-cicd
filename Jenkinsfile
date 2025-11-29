pipeline {
  agent any
  environment {
    IMAGE_REPO = 'diordon/finalcicd'   // <-- change if your Docker Hub repo name differs
  }
  stages {

    stage('Checkout'){
      steps {
        checkout scm
        sh 'git log -1 --oneline || true'
        sh 'ls -al'
      }
    }

    stage('Unit tests'){
      steps {
        sh '''
          set -euxo pipefail
          # make sure venv is available in the Jenkins container
          if ! python3 -m venv --help >/dev/null 2>&1; then
            apt-get update && apt-get install -y python3-venv
          fi

          python3 -m venv .venv
          . .venv/bin/activate
          python -V
          pip install --upgrade pip
          pip install -r requirements.txt pytest
          pytest -q
        '''
      }
    }

    stage('Docker Login'){
      steps {
        withCredentials([usernamePassword(credentialsId: 'dockerhub',
                                          usernameVariable: 'DOCKERHUB_USER',
                                          passwordVariable: 'DOCKERHUB_TOKEN')]) {
          sh 'echo "$DOCKERHUB_TOKEN" | docker login -u "$DOCKERHUB_USER" --password-stdin'
        }
      }
    }

    stage('Build & Push image'){
      steps {
        sh '''
          set -euxo pipefail
          TAG=$(date +%Y.%m.%d-%H%M)
          docker build -t $IMAGE_REPO:$TAG -t $IMAGE_REPO:latest .
          docker push $IMAGE_REPO:$TAG
          docker push $IMAGE_REPO:latest
          echo $IMAGE_REPO:$TAG > image.txt
        '''
      }
    }

    stage('Deploy local (Docker)'){
      steps {
        withCredentials([string(credentialsId: 'webex_token', variable: 'WXT'),
                         string(credentialsId: 'webex_room',  variable: 'WXR')]) {
          sh '''
            set -euxo pipefail
            IMG=$(cat image.txt)
            docker rm -f cvewatch || true
            # Note: no bind mount of cvewatch.db to avoid host/volume path issues
            docker run -d --name cvewatch -p 18080:8000 \
              -e WEBEX_TOKEN="$WXT" -e WEBEX_ROOM_ID="$WXR" \
              -e CVE_API_BASE="https://services.nvd.nist.gov/rest/json/cves/2.0" \
              "$IMG"
          '''
        }
      }
    }

    stage('Notify Webex'){
      steps {
        withCredentials([string(credentialsId: 'webex_token', variable: 'WXT'),
                         string(credentialsId: 'webex_room',  variable: 'WXR')]) {
          sh '''
            IMG=$(cat image.txt)
            curl -sS -X POST "https://webexapis.com/v1/messages" \
              -H "Authorization: Bearer $WXT" -H "Content-Type: application/json" \
              -d '{"roomId":"'"$WXR"'","markdown":"✅ Deploy complete: **'"$IMG"'**"}' >/dev/null
          '''
        }
      }
    }
  }
}

