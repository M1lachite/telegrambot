// Jenkinsfile
pipeline {
    agent any

    environment {
        APP_NAME = "telegramnotesbot"
        REPO_URL = credentials('REPO_URL')
        CONTAINER_PORT = 8000
        HOST_PORT = 8080
        DOCKERFILE_NAME = "Dockerfile.txt"
        PYTEST_SCRIPT_NAME = "pytest.sh"
        TELEGRAM_API_KEY = credentials('TELEGRAM_API_KEY')
    }

    stages {
        stage('Checkout Code') {
            steps {
                echo "Klonowanie repozytorium Git: ${env.REPO_URL}"
                git url: env.REPO_URL, credentialsId: 'github_ssh_key', branch: 'main'
            }
        }

        stage('Run Pytest Tests') {
            steps {
                echo "Uruchamianie testów Pytest..."
                script {
                    sh "chmod +x ${WORKSPACE}/${PYTEST_SCRIPT_NAME}"
                    sh "${WORKSPACE}/${PYTEST_SCRIPT_NAME} ${WORKSPACE}"
                }
            }
        }

        stage('Build Docker Image') {
            steps {
                script {
                    echo "Budowanie obrazu Docker: ${env.APP_NAME}:${env.BUILD_NUMBER}"
                    dockerImage = docker.build("${env.APP_NAME}:${env.BUILD_NUMBER}", "--file ${DOCKERFILE_NAME} .")
                    echo "Obraz Docker zbudowany: ${dockerImage.id}"
                }
            }
        }

        stage('Stop Old Container') {
            steps {
                script {
                    def containerName = "${env.APP_NAME}-container"
                    echo "Sprawdzanie, czy kontener ${containerName} jest uruchomiony..."
                    def existingContainer = sh(script: "docker ps -aq -f name=^${containerName}" + '$' + " || true", returnStdout: true).trim()

                    if (existingContainer) {
                        echo "Zatrzymywanie i usuwanie istniejącego kontenera: ${containerName} (ID: ${existingContainer})"
                        sh "docker stop ${existingContainer}"
                        sh "docker rm ${existingContainer}"
                        echo "Kontener ${containerName} zatrzymany i usunięty."
                    } else {
                        echo "Kontener ${containerName} nie jest uruchomiony, kontynuowanie."
                    }
                }
            }
        }

        stage('Run New Container') {
            steps {
                script {
                    def containerName = "${env.APP_NAME}-container"
                    def appPort = env.CONTAINER_PORT
                    def hostPort = env.HOST_PORT

                    echo "Uruchamianie nowego kontenera: ${containerName} z obrazu ${dockerImage.id}"
                    sh """
                        docker run -d --name ${containerName} \
                        -p ${hostPort}:${appPort} \
                        -e TELEGRAM_API_KEY='${env.TELEGRAM_API_KEY}' \
                        -e REPO_URL='${env.REPO_URL}' \
                        ${dockerImage.id}
                    """
                    echo "Nowy kontener ${containerName} uruchomiony na porcie ${env.HOST_PORT}."
                }
            }
        }
    }

    post {
        always {
            echo "Potok CI/CD dla ${env.APP_NAME} zakończony."
        }
        success {
            echo "Potok zakończony SUKCESEM!"
        }
        failure {
            echo "Potok zakończony BŁĘDEM!"
        }
    }
}
