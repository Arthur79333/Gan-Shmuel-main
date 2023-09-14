import requests
import json
from datetime import datetime
import os

BASE_URL = "http://localhost:8081"

# return dicty[healh] = {passed: True, message: "OK"}

def test_health_check():
    response = requests.get(f"{BASE_URL}/health")

    if response.status_code == 200:
        print("{status: OK}, 200")
    else:
        print("{status: Failure}, 500")


def test_get_session(session_id):
    response = requests.get(f"{BASE_URL}/session/{session_id}")

    if response.status_code == 404:
        print(f"Session with id {session_id} does not exist.")
        return

    if response.status_code != 200:
        print(f"Unexpected status code {response.status_code} for session_id {session_id}.")
        return

    json_data = response.json()

    if not all(key in json_data for key in ["id", "truck", "bruto"]):
        print(f"Failed for session_id {session_id}: Base keys (id, truck, bruto) not found in response.")
        print(f"Related session data: {json_data}")
        return

    if "truckTara" in json_data:
        if not all(key in json_data for key in ["truckTara", "neto"]):
            print(f"Failed for session_id {session_id}: It's an OUT session, but keys (truckTara, neto) are missing.")
            print(f"Related session data: {json_data}")
            return

    print(f"Successfully validated data for session_id {session_id}.")
    print(f"Related session data: {json_data}")


def check_post_weight(data: dict) -> None:
    url = f"{BASE_URL}/weight"
    headers = {
        "Content-Type": "application/json"
    }
    response = requests.post(url=url, data=json.dumps(data), headers=headers)
    
    # # Extract the ID of the created record for deletion later
    # created_record_id = None
    # if 'id' in response.json():
    #     created_record_id = response.json()['id']
    
    if response.status_code == 201:
        print(f"Created: {response.json()}")

    elif data["direction"] == 'in':
        print({"Error, status code: 400": "Consecutive 'in' records not allowed. Use force to override."})

    elif data["direction"] == 'out':
        print({"Error, status code: 400": "No 'in' record found for the truck."})

    else:
        print(f"Unexpected response: {response.status_code} - {response.json()}")
    
    # # Remove the new post if it was created
    # if created_record_id:
    #     delete_url = f"{url}/{created_record_id}"
    #     delete_response = requests.delete(delete_url)
    #     if delete_response.status_code == 200:
    #         print(f"Successfully deleted record with ID {created_record_id}.")
    #     else:
    #         print(f"Failed to delete record with ID {created_record_id}. Status Code: {delete_response.status_code}")

in_payload = {
    "direction": "out",
    "truck": "T-14045",
    "containers": "C-73281",
    "weight": 1000,
    "unit": "kg",
    "produce": "Mandarin"
}


def check_item(item_id: str, from_time: str = None, to_time: str = None) -> None:
    url = f"{BASE_URL}/item/{item_id}"
    
    if not from_time:
        from_time = datetime.now().replace(day=1).strftime('%Y%m%d%H%M%S')
    if not to_time:
        to_time = datetime.now().strftime('%Y%m%d%H%M%S')
    
    params = {'from': from_time, 'to': to_time}
    
    response = requests.get(url, params=params)
    
    if response.status_code == 200:
        json_data = response.json()
        if all(key in json_data for key in ['id', 'tara', 'sessions']) and isinstance(json_data['sessions'], list):
            
            if json_data['id'] == item_id:
                if str(item_id) in [str(session_id) for session_id in json_data['sessions']]:
                    print(f"Error: Item ID {item_id} should not be in the sessions list.")
                    return
                else:
                    print(f"Item ID: {json_data['id']}")
                    print(f"Tara: {json_data['tara']}")
                    print(f"Sessions: {json_data['sessions']}")
            else:
                print(f"Error: Returned ID {json_data['id']} does not match queried item_id {item_id}.")
            
        else:
            print(f"Unexpected response format for item_id {item_id}.")
            
    elif response.status_code == 404:
        print(f"Item with ID {item_id} not found (neither a truck nor a container).")
    
    else:
        print(f"Unexpected status code {response.status_code} for item_id {item_id}.")


def check_weight_records(from_time: str = None, to_time: str = None, filter_criteria: str = "in,out,none") -> None:
    url = f"{BASE_URL}/weight"
    
    params = {}
    if from_time:
        params['from'] = from_time
    if to_time:
        params['to'] = to_time
    if filter_criteria:
        params['filter'] = filter_criteria

    response = requests.get(url, params=params)
    
    if response.status_code == 200:
        records = response.json()
        if isinstance(records, list) and all(isinstance(record, dict) for record in records):
            if records:
                print(f"Found {len(records)} weight records:")
                for record in records:
                    print(record)
            else:
                print("No weight records found for the given filters.")
        else:
            print("Unexpected response format. Expected a list of dictionaries.")
    elif response.status_code == 404:
        print("No weight records found for the given filters.")
    else:
        print(f"Unexpected status code {response.status_code}. Response: {response.json()}")


def check_unknown_containers() -> None:
    url = f"{BASE_URL}/unknown"
    response = requests.get(url)
    
    json_data = response.json()
    
    if response.status_code == 200:
        if isinstance(json_data, list):
            if json_data:
                print(f"Found unknown containers: {json_data}")

            else:
                print("No unknown containers found.")
        else:
            print("Unexpected response format. Expected a list.")

    elif response.status_code == 500 and 'error' in json_data:
        print(f"Internal server error: {json_data['error']}")

    else:
        print(f"Unexpected response: {response.status_code} - {json_data}")


def test_upload_weights_from_file(filename):
    try:
        filepath = os.path.join('./in', filename)
        with open(filepath, 'rb') as file:
            files = {'file': (filename, file)}
            response = requests.post(f"{BASE_URL}/batch-weight", files=files)
            status_code = response.status_code
            response_data = response.json()

            if status_code == 201:
                print(f"Successfully uploaded weights from {filename}. Response: {response_data}")

            elif status_code == 400:
                print(f"Bad request while uploading {filename}. Response: {response_data}")
            elif status_code == 500:
                print(f"Server error while uploading {filename}. Response: {response_data}")
            else:
                print(f"Unexpected status code {status_code} for {filename}. Response: {response_data}")

    except Exception as e:
        print(f"Error while testing {filename}: {e}")


def main():
    test_health_check()
    ##########################
    test_get_session(10005)
    test_get_session(10006)
    test_get_session(10007)
    ##########################
    check_post_weight(in_payload)
    ##########################
    check_item("T-14409")
    ##########################
    check_weight_records()
    ##########################
    check_unknown_containers()
    ##########################
    test_upload_weights_from_file("containers2.csv")
    test_upload_weights_from_file("trucks.json")
    test_upload_weights_from_file("unsupported_file.txt")


if __name__ == "__main__":
    main()