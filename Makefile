python := python3
IMAGE_TAG ?= *

# house keeping: update the Jenkinsfile
Jenkinsfile: tools/gen_Jenkinsfile.py
	$(python) tools/gen_Jenkinsfile.py

clean:
	docker images 'librarytest/*:python-$(IMAGE_TAG)-*' \
		| awk 'NR>1 { print $$1 ":" $$2 }' \
		| xargs -r docker rmi
