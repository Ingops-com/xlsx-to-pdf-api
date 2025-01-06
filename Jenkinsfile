pipeline {
    agent any

    environment {
        DOCKER_IMAGE = 'api-pdf'
        CONTAINER_NAME = 'api-pdf-container'
        PORT = 5050
    }

    stages {
        stage('Build') {
            steps {
                script {
                    // Construir la imagen Docker con un tag
                    sh 'docker build -t ${DOCKER_IMAGE}:${BUILD_NUMBER} .'
                }
            }
        }

        stage('Delete Container') {
            steps {
                script {
                    // Detener y eliminar el contenedor anterior si existe
                    sh 'docker stop ${CONTAINER_NAME} || true'
                    sh 'docker rm ${CONTAINER_NAME} || true'
                }
            }
        }

        stage('Deploy') {
           steps {
                script {
                        sh 'docker run -d -p ${PORT}:${PORT} -v "$(pwd)/app/static:/app/static" --name${CONTAINER_NAME} --restart=always ${DOCKER_IMAGE}:${BUILD_NUMBER}' 

                }
            }
        }

        stage('Clean') {
            steps {
                script {
                    // Limpieza: eliminar imágenes antiguas
                    sh 'docker image prune -f'
                }
            }
        }
    }
}
