"""Generate the declarative Jenkins pipeline"""

__author__ = 'Jakob Ackermann <das7pad@outlook.com>'

import collections
import pathlib


VERSIONS = [
    '2.7.16',

    '3.5.3',
    '3.5.4',
    '3.5.5',
    '3.5.6',

    '3.6.0',
    '3.6.1',
    '3.6.2',
    '3.6.3',
    '3.6.4',
    '3.6.5',
    '3.6.6',
    '3.6.7',
    '3.6.8',

    '3.7.0',
    '3.7.1',
    '3.7.2',
    '3.7.3',
]


def indent(size: int, content: str):
    actual_indent = ' ' * size * 2
    return '\n'.join(
        ('' if line.startswith('%(') else actual_indent)
        + line
        for line in content.strip('\n').replace('    ', '  ').splitlines()
    )


PIPELINE = indent(0, """
//
// This file is autogenerated.
// To update, run:
//
//    make Jenkinsfile
//

pipeline {
    agent none
    environment {
        HOME = '/tmp/'
    }
    options {
        timestamps()
    }
    stages {
        stage('Prepare Build') {
            agent any
            steps {
                dir('official-images') {
                    git url: 'https://github.com/docker-library/official-images'
                }
                stash includes: 'official-images/**', name: 'official-images'
            }
        }
        stage('Build Stage') {
            parallel {
%(stages)s
            }
        }
    }
}
""")


STAGE = indent(4, """
stage('%(version)s') {
    agent {
        label 'docker_builder'
    }
    environment {
        IMAGE = "python:%(version)s-stretch-$BRANCH_NAME-$BUILD_NUMBER"
        IMAGE_CACHE = "$IMAGE-cache"
    }
    stages {
        stage('%(version)s Pull Cache') {
            steps {
                sh '''docker pull $DOCKER_REGISTRY/python:%(version)s \\
                    && docker tag $IMAGE_REPO:%(version)s $IMAGE_CACHE \\
                    || true
                '''
            }
        }
        stage('%(version)s Build') {
            steps {
                retry(10) {
                    sh '''docker build --tag $IMAGE \\
                            --build-arg PYTHON_VERSION=%(version)s \\
                            --file %(major_minor)s/stretch/Dockerfile \\
                            .
                    '''
                }
            }
        }
        stage('%(version)s Test') {
            steps {
                unstash 'official-images'
                retry(3) {
                    sh 'official-images/test/run.sh $IMAGE'
                }
            }
        }
        stage('%(version)s Push') {
            steps {
%(tags)s
            }
        }
    }
    post {
        cleanup {
            sh '''docker rmi \\
                $IMAGE \\
                $IMAGE_CACHE \\
%(rmi_tags)s
                --force
            '''
            sh '''test -e official-images/test/clean.sh \\
                && official-images/test/clean.sh \\
                || true
            '''
        }
    }
}
""")

TAGS = indent(8, """
sh 'docker tag $IMAGE $DOCKER_REGISTRY/python:%(tag)s'
retry(3) {
    sh 'docker push $DOCKER_REGISTRY/python:%(tag)s'
}
""")

RMI_TAG = indent(8, """
$DOCKER_REGISTRY/python:%(tag)s \\
""")


def main():
    jenkinsfile = pathlib.Path(__file__).parent.parent / 'Jenkinsfile'

    tags = {}
    for version in VERSIONS:
        major_minor, patch = version.rsplit('.', 1)
        major, minor = major_minor.split('.')
        tags[version] = version
        tags[major_minor] = version
        tags[major] = version
        tags['latest'] = version

    tags_by_version = collections.defaultdict(list)
    for tag, version in tags.items():
        tags_by_version[version].append(tag)

    stages = '\n'.join(
        STAGE % dict(
            version=version,
            major_minor=version.rsplit('.', 1)[0],
            rmi_tags='\n'.join(
                RMI_TAG % dict(tag=tag)
                for tag in sorted(tags_by_version[version])
            ),
            tags='\n'.join(
                TAGS % dict(tag=tag)
                for tag in sorted(tags_by_version[version])
            )
        )
        for version in VERSIONS
    )

    pipeline = PIPELINE % dict(stages=stages)
    jenkinsfile.write_text(pipeline + '\n')


if __name__ == '__main__':
    main()
