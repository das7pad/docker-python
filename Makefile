python := python3

# house keeping: update the Jenkinsfile
Jenkinsfile: tools/gen_Jenkinsfile.py
	$(python) tools/gen_Jenkinsfile.py
