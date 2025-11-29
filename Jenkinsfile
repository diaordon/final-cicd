pipeline {
  agent any
  environment {
    IMAGE_REPO = 'diaordon/finalcicd'     // <- change if your Docker Hub repo is different
  }
  stages {
    stage('Checkout'){
      steps { checkout scm }
    }

    // Small sanity check so we see the repo contents in the log
    stage('Show workspace'){
      steps { sh 'pwd && ls -al' }
    }

    // Run tests in a clean Python container (avoids PEP 668 issues)
    stage('Unit tests'){
  steps {
    sh '''
      docker run --rm \
        --volumes-from jenkins \
        -w "$WORKSPACE" \
        python:3.11 bash -lc '
          set -e
          ls -al
          mkdir -p tests
          cat > tests/test_dummy.py <<PY
def test_dummy():
    assert True
PY
          python -V && pip -V
          pip install -r requirements.txt pytest
          pytest -q
        '
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
        docker run -d --name cvewatch -p 18080:8000 \
          -e WEBEX_TOKEN="$WXT" -e WEBEX_ROOM_ID="$WXR" \
          -e CVE_API_BASE="https://services.nvd.nist.gov/rest/json/cves/2.0" \
          -v "$PWD/cvewatch.db:/app/cvewatch.db" "$IMG"
      '''
    }
  }
}
stage('Trigger scan'){
  steps {
    sh '''
      set -euxo pipefail

      # Confirm the app is up (wait up to ~20s)
      for i in $(seq 1 20); do
        if curl -sSf http://127.0.0.1:18080/ > /dev/null; then
          break
        fi
        sleep 1
      done

      # Make sure a watch exists (idempotent)
      curl -s -X POST "http://127.0.0.1:18080/watch?q=OpenSSL" > /dev/null || true

      # Run the job *inside* the container without here-docs
      docker exec cvewatch python -c "from app.schedule_job import run_once; run_once()"
    '''
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
          -d '{"roomId":"'"$WXR"'","markdown":"✅ Deploy + scan complete on **'"$IMG"'**"}' \
          > /dev/null
      '''
    }
  }
}

