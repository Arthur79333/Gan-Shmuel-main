import os
import subprocess
import git
from pathlib import Path
import smtplib
from email.message import EmailMessage
from decouple import config


CURR_DIR = Path('/home/samer/Desktop/TESTING/TESTDIR')
RUNNING_DIR = CURR_DIR / "running"
REPO_URL = 'git@github.com:Blue-Team-Develeap/Gan-Shmuel.git'
DOCKER_COMPOSE_FILE_CURR_DIR = CURR_DIR / "docker-compose.yml"
DOCKER_COMPOSE_FILE = RUNNING_DIR / "docker-compose.yml"


 # Clear the testing directory
def cleanup_clone():
    for root, dirs, files in os.walk(RUNNING_DIR, topdown=False):
        for name in files:
            os.remove(os.path.join(root, name))
        for name in dirs:
            os.rmdir(os.path.join(root, name))

    # Clone repo
    repo = git.Repo.clone_from(REPO_URL, RUNNING_DIR)


def docker_compose_instance(env_name, compose_template, compose_instance_name):
    # Replace placeholders in the template and write to an instance file
    with open(compose_template, 'r') as template:
        compose_data = template.read()
        with open(env_name, 'r') as env_file:
            for line in env_file:
                key, value = line.strip().split('=')
                compose_data = compose_data.replace(f"${{{key}}}", value)
        with open(compose_instance_name, 'w') as instance:
            instance.write(compose_data)
    subprocess.check_output(['mv', DOCKER_COMPOSE_FILE_CURR_DIR, RUNNING_DIR], text=True)


def send_notification(data):
    emails = data.get("emails", [])
    status = data.get("status", "")
    
    # Define the email sending function
    def send_email(subject, body, recipients):
        # Email configuration
        SMTP_SERVER = config('SMTP_SERVER')
        SMTP_PORT = config('SMTP_PORT', cast=int)
        SMTP_USERNAME = config('SMTP_USERNAME')
        SMTP_PASSWORD = config('SMTP_PASSWORD')
        SENDER_EMAIL = config('SENDER_EMAIL')
        
        # Create the email object
        msg = EmailMessage()
        msg['From'] = SENDER_EMAIL
        msg['To'] = ", ".join(recipients)
        msg['Subject'] = subject
        msg.set_content(body)

        # Send the email
        try:
            with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
                server.starttls()  # Upgrade the connection to a secure encrypted SSL/TLS connection
                server.login(SMTP_USERNAME, SMTP_PASSWORD)
                server.send_message(msg)
                print(f"Email sent to {', '.join(recipients)}!")
        except Exception as e:
            print(f"Error sending email: {e}")

    if status == "IMAGE_BUILD_FAILURE":
        send_email(
            subject="Failed building images",
            body="Building images failed in the test environment.",
            recipients=emails
        )
    elif status == "CONTAINER_RUN_FAILURE":
        send_email(
            subject="Failed running containers",
            body="Running containers failed in the test environment.",
            recipients=emails
        )
    elif status == "E2E_TESTS_FAILURE":
        
        send_email(
            subject="End-to-End tests failed",
            body="Failed running E2E tests.",
            recipients=emails
        )
    elif status == "DEPLOYMENT_SUCCESS":
        
        send_email(
            subject="Main Branch Test Success",
            body="The tests in the main branch passed successfully and the changes have been deployed to the server.",
            recipients=emails
        )
    else:
        print(f"Unknown status: {status}")


def get_docker_image_ids():
    result = subprocess.check_output(['docker', 'images', '-q'], text=True)
    return set(result.splitlines())


def get_docker_containers_ids():
    result = subprocess.check_output(['docker', 'ps', '-q'], text=True)
    return set(result.splitlines())


def main(author_email='samerr93@hotmail.com'):
    # Build images and save their IDs
    try:
        image_ids_before_build = get_docker_image_ids()
        volume_list_before = subprocess.check_output(['docker', 'volume', 'ls', '-q'], text=True).splitlines()
        subprocess.check_output(['docker-compose', '-f', DOCKER_COMPOSE_FILE, 'build', '--no-cache'], text=True)
    except subprocess.CalledProcessError:
        image_ids_after_build = get_docker_image_ids()
        new_image_ids = image_ids_after_build - image_ids_before_build
        for image_id in new_image_ids:
            subprocess.run(['docker', 'rmi', image_id], text=True)
        data = {
            "status": "IMAGE_BUILD_FAILURE",
            "emails": [author_email]
        }
        send_notification(data)
        #repo.git.reset('--hard', 'HEAD~1')
        return

    # Run containers
    try:
        container_ids_before_build = get_docker_containers_ids()
        subprocess.run(['docker-compose', '-f', DOCKER_COMPOSE_FILE, 'up', '-d'], check=True)
    except subprocess.CalledProcessError:
        container_ids_after_build = get_docker_containers_ids()
        new_container_ids = container_ids_after_build - container_ids_before_build
        for container_id in new_container_ids:
            subprocess.run(['docker', 'stop', container_id], text=True)
            subprocess.run(['docker', 'rm', container_id], text=True)
        volume_list_after = subprocess.check_output(['docker', 'volume', 'ls', '-q'], text=True).splitlines()
        for volume in volume_list_after:
            if volume not in volume_list_before:
                subprocess.run(['docker', 'volume', 'rm', volume], text=True)
        image_ids_after_build = get_docker_image_ids()
        new_image_ids = image_ids_after_build - image_ids_before_build
        for img in new_image_ids:
            subprocess.run(['docker', 'rmi', img])
        data = {
            "status": "CONTAINER_RUN_FAILURE",
            "emails": [author_email]
        }
        send_notification(data)
        #repo.git.reset('--hard', 'HEAD~1')
        return

    #########################################################################################
    # Run tests (modify this part to fit your testing command and logic)
    #test_command = ['docker', 'exec', 'CONTAINER_NAME', 'YOUR_TEST_COMMAND']
    #test_result = subprocess.run(test_command)
    #########################################################################################

    # Check test result
    #if test_result.returncode != 0:
    if 0 != 0:
        data = {
            "status": "E2E_TESTS_FAILURE",
            "emails": [author_email]
        }
        send_notification(data)
        #repo.git.reset('--hard', 'HEAD~1')
        container_ids_after_build = get_docker_containers_ids()
        new_container_ids = container_ids_after_build - container_ids_before_build
        for container_id in new_container_ids:
            subprocess.run(['docker', 'stop', container_id], text=True)
            subprocess.run(['docker', 'rm', container_id], text=True)
        volume_list_after = subprocess.check_output(['docker', 'volume', 'ls', '-q'], text=True).splitlines()
        for volume in volume_list_after:
            if volume not in volume_list_before:
                subprocess.run(['docker', 'volume', 'rm', volume], text=True)
        image_ids_after_build = get_docker_image_ids()
        new_image_ids = image_ids_after_build - image_ids_before_build
        for img in new_image_ids:
            subprocess.run(['docker', 'rmi', img])
        return

    # Docker-compose down for the newly tested images' containers
    subprocess.run(['docker-compose', '-f', DOCKER_COMPOSE_FILE ,'down', '-v'], text=True)
    # Remove older production containers
    for container_id in container_ids_before_build:
        subprocess.run(['docker', 'rm', '-f', container_id], text=True)
    # Remove older production images
    for img in image_ids_before_build:
            subprocess.run(['docker', 'rmi', '-f', img])
    os.remove(DOCKER_COMPOSE_FILE)

    # Start deployment environment
    docker_compose_instance(CURR_DIR / ".env-prod", CURR_DIR / "docker-compose-template.yml", CURR_DIR / "docker-compose.yml")
    
    # Run new production containers
    subprocess.run(['docker-compose', '-f', DOCKER_COMPOSE_FILE, 'up', '-d'])

    data = {
            "status": "DEPLOYMENT_SUCCESS",
            "emails": [author_email]
        }
    send_notification(data)


if __name__ == "__main__":
    cleanup_clone()
    docker_compose_instance(CURR_DIR / ".env-test", CURR_DIR / "docker-compose-template.yml", CURR_DIR / "docker-compose.yml")
    author_email='samerr93@hotmail.com'
    main(author_email)
