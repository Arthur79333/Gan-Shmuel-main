import requests
import json
from datetime import datetime
import os

BASE_URL = "http://localhost:8081"


def test_health_check() -> bool:
    response = requests.get(f"{BASE_URL}/health")
    if response.status_code == 200:
        print("{status: OK}, 200")
        return True
    else:
        print("{status: Failure}, 500")
        return False


def test_get_session(session_id) -> bool:
    response = requests.get(f"{BASE_URL}/session/{session_id}")

    if response.status_code == 404:
        print(f"Session with id {session_id} does not exist.")
        return False

    if response.status_code != 200:
        print(f"Unexpected status code {response.status_code} for session_id {session_id}.")
        return False

    json_data = response.json()

    if not all(key in json_data for key in ["id", "truck", "bruto"]):
        print(f"Failed for session_id {session_id}: Base keys (id, truck, bruto) not found in response.")
        print(f"Related session data: {json_data}")
        return False

    if "truckTara" in json_data:
        if not all(key in json_data for key in ["truckTara", "neto"]):
            print(f"Failed for session_id {session_id}: It's an OUT session, but keys (truckTara, neto) are missing.")
            print(f"Related session data: {json_data}")
            return False

    print(f"Successfully validated data for session_id {session_id}.")
    print(f"Related session data: {json_data}")
    return True


def check_post_weight(data: dict) -> bool:
    url = f"{BASE_URL}/weight"
    headers = {
        "Content-Type": "application/json"
    }
    response = requests.post(url=url, data=json.dumps(data), headers=headers)
    
    if response.status_code == 201:
        print(f"Created: {response.json()}")
        return True

    elif data["direction"] == 'in':
        print({"Error, status code: 400": "Consecutive 'in' records not allowed. Use force to override."})
        return False

    elif data["direction"] == 'out':
        print({"Error, status code: 400": "No 'in' record found for the truck."})
        return False

    else:
        print(f"Unexpected response: {response.status_code} - {response.json()}")
        return False

in_payload = {
    "direction": "out",
    "truck": "T-14045",
    "containers": "C-73281",
    "weight": 1000,
    "unit": "kg",
    "produce": "Mandarin"
}

def check_item(item_id: str, from_time: str = None, to_time: str = None) -> bool:
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
                    return False
                else:
                    print(f"Item ID: {json_data['id']}")
                    print(f"Tara: {json_data['tara']}")
                    print(f"Sessions: {json_data['sessions']}")
                    return True
            else:
                print(f"Error: Returned ID {json_data['id']} does not match queried item_id {item_id}.")
                return False
        else:
            print(f"Unexpected response format for item_id {item_id}.")
            return False
            
    elif response.status_code == 404:
        print(f"Item with ID {item_id} not found (neither a truck nor a container).")
        return False
    
    else:
        print(f"Unexpected status code {response.status_code} for item_id {item_id}.")
        return False


def check_weight_records(from_time: str = None, to_time: str = None, filter_criteria: str = "in,out,none") -> bool:
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
                # for record in records:
                    # print(record)
                return True
            else:
                print("No weight records found for the given filters.")
                return False
        else:
            print("Unexpected response format. Expected a list of dictionaries.")
            return False
            
    elif response.status_code == 404:
        print("No weight records found for the given filters.")
        return False
    
    else:
        print(f"Unexpected status code {response.status_code}. Response: {response.json()}")
        return False


def check_unknown_containers() -> bool:
    url = f"{BASE_URL}/unknown"
    response = requests.get(url)
    
    json_data = response.json()
    
    if response.status_code == 200:
        if isinstance(json_data, list):
            if json_data:
                print(f"Found unknown containers: {json_data}")
                return True
            else:
                print("No unknown containers found.")
                return True
        else:
            print("Unexpected response format. Expected a list.")
            return False

    elif response.status_code == 500 and 'error' in json_data:
        print(f"Internal server error: {json_data['error']}")
        return False

    else:
        print(f"Unexpected response: {response.status_code} - {json_data}")
        return False


def test_upload_weights_from_file(filename: str) -> bool:
    try:
        filepath = os.path.join('./in', filename)
        with open(filepath, 'rb') as file:
            files = {'file': (filename, file)}
            response = requests.post(f"{BASE_URL}/batch-weight", files=files)
            status_code = response.status_code
            response_data = response.json()

            if status_code == 201:
                print(f"Successfully uploaded weights from {filename}. Response: {response_data}")
                return True

            elif status_code == 400:
                print(f"Bad request while uploading {filename}. Response: {response_data}")
                return False

            elif status_code == 500:
                print(f"Server error while uploading {filename}. Response: {response_data}")
                return False

            else:
                print(f"Unexpected status code {status_code} for {filename}. Response: {response_data}")
                return False

    except Exception as e:
        print(f"Error while testing {filename}: {e}")
        return False


def main() -> bool:
    functions = [
        test_health_check,
        lambda: test_get_session(10005),
        # lambda: test_get_session(10006),
        # lambda: test_get_session(10007),
        lambda: check_post_weight(in_payload),
        lambda: check_item("T-14409"),
        check_weight_records,
        check_unknown_containers,
        lambda: test_upload_weights_from_file("containers2.csv"),
        lambda: test_upload_weights_from_file("trucks.json"),
        # lambda: test_upload_weights_from_file("unsupported_file.txt")
    ]
    
    for func in functions:
        result = func()
        if not result:
            print(f"Function {func.__name__} failed. Exiting...")
            return False

    return True


if __name__ == "__main__":
    success = main()
    if not success:
        exit(1)
    else:
        exit(0)