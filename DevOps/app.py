from flask import Flask, request, json, jsonify
import subprocess
import smtplib
from email.message import EmailMessage
from decouple import config

app = Flask(__name__)

# Health check API
@app.route('/health', methods=['GET'])
def health_check():
        return jsonify({"status": "OK"}), 200

@app.route("/webhook", methods=["POST"])
def webhook():
    payload = json.loads(request.data)
    branch_name = payload['ref'].split('/')[-1]
    author = payload['sender']['login']
    time = payload['commits'][0]['timestamp']
    commit_info = payload['head_commit'] # Gather commit information
    commit_owner_email = commit_info['author']['email']

    # Check if the branch is 'main'
    #if branch_name == 'main':
    if True:
        # Extract changes (modify as needed based on actual payload structure)
        #changes = commit_info['added'] + commit_info['removed'] + commit_info['modified']
        #print(f"Changes ARE: {changes}")


        # TODO: excute bash script to test the changes here
        #result = subprocess.run(["./blue_ci_script.sh"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)

        # TODO: Complete intergration with email functionality 
        #if build_result.returncode == 0:
        print(f"{commit_owner_email}, 'Build Success', 'Your commit was successful!'")
        #else:
         #   print(f"{commit_owner_email}, 'Build Failure', 'Your commit failed and the changes were not applied.'")
         #   Todo: revert changes if testing failed

        #return jsonify(status='success' if build_result.returncode == 0 else 'failure'), 200
        #return jsonify(branch_name, author, commit_owner_email, time, commit_info, commit_owner_email), 200

   # return jsonify(status='ignored', message='Not a main branch commit'), 200
    return [branch_name, author, commit_owner_email, time, commit_info, commit_owner_email], 200


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

    # Logic to decide email content based on status
    if status == "E2E_FAILURE":
        send_email(
            subject="E2E Test Failure",
            body="The end-to-end tests failed in the test environment.",
            recipients=emails
        )
    elif status == "DEV_SUCCESS":
        send_email(
            subject="Development Branch Test Success",
            body="The tests in the development branch passed successfully.",
            recipients=emails
        )
    elif status == "MAIN_SUCCESS":
        # Deploy to server logic can be added here

        send_email(
            subject="Main Branch Test Success",
            body="The tests in the main branch passed successfully and the changes have been deployed to the server.",
            recipients=emails
        )
    else:
        print(f"Unknown status: {status}")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
