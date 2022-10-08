# Zip Archive python lambda layer
layer:
	poetry export -f requirements.txt --without-hashes --output requirements.txt && \
	pip install -r requirements.txt -t lambda_layer/python && \
	cd lambda_layer && \
	zip -FSrm9 layer.zip python -x python/bin/* && \
	rm -rf python && \
	cd ../

# Deploy Lambda Wsgi Test Enviroment
wsgi:
	poetry run python lambda_func/serve.py . ec2_control.api.app 5000 localhost