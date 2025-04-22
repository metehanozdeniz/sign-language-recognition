# run.sh
# This script sets up the environment and starts the Flask application and Celery worker.

# start flask application
echo "Starting Flask application..."
flask run &

# start celery worker
echo "Starting Celery worker..."
celery -A celery_worker.celery worker --loglevel=info

wait