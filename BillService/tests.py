import requests

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    END = '\033[0m'

class Formats:
    BOLD = '\033[1m'
    RESET = '\033[0m'



# provider_post_url = "http://51.17.41.172:8086/provider"
# provider_put_url = "http://51.17.41.172:8086/provider/{id}"
# health_url = "http://51.17.41.172:8086/health"
# rates_url = "http://51.17.41.172:8086/rates"

# provider_post_url = "http://localhost:8086/provider"
# provider_put_url = "http://localhost:8086/provider/{id}"
# health_url = "http://localhost:8086/health"
# rates_url = "http://localhost:8086/rates"
# truck_post_url = "http://localhost:8086/truck"
# truck_put_url = "http://localhost:8086/truck/{id}"
# truck_get_url = "http://localhost:8086/truck/{id}"
# bill_get_url = "http://localhost:8086/bill/{id}"

# files = {"file": ("rates.xlsx", open("./in/rates.xlsx", "rb"))}



# Health check
def main():
    provider_post_url = "http://localhost:8086/provider"
    provider_put_url = "http://localhost:8086/provider/{id}"
    health_url = "http://localhost:8086/health"
    rates_url = "http://localhost:8086/rates"
    truck_post_url = "http://localhost:8086/truck"
    truck_put_url = "http://localhost:8086/truck/{id}"
    truck_get_url = "http://localhost:8086/truck/{id}"
    bill_get_url = "http://localhost:8086/bill/{id}"

    files = {"file": ("rates.xlsx", open("./in/rates.xlsx", "rb"))}
    try:
        response = requests.get(health_url)
        if response.status_code == 200:
            health_test = "Health check" + " " + Formats.BOLD + Colors.GREEN + "OK!" + Colors.END + Formats.RESET
            print(health_test)
            
        else:
            health_test = "Health check" + Formats.BOLD + Colors.RED + " FAILED!"  + Colors.END + Formats.RESET
            print(health_test)
            return False, response
    except requests.RequestException as e:
        health_test = "Health check" + Formats.BOLD + Colors.RED + " FAILED!"  + Colors.END + Formats.RESET
        print(health_test)
        return False, e
        



    # POST /provider
    try:
        response = requests.post(provider_post_url, json={"provider_name": "Test1"})
        response = requests.post(provider_post_url, json={"provider_name": "Test1"})
        if response.status_code == 201:
            post_id_test="Provider POST Test :" + Formats.BOLD + Colors.GREEN + " Passed OK!"  + Colors.END + Formats.RESET
            print(post_id_test)
            provider_id = response.json().get("id", None)
        else:
            post_id_test = ("Provider POST Test :" + Formats.BOLD + Colors.RED + " FAILED!"  + Colors.END + Formats.RESET)
            print(post_id_test)
            return False, response
    except requests.RequestException as e:
        post_id_test = ("Provider POST Test :" + Formats.BOLD + Colors.RED + " FAILED!"  + Colors.END + Formats.RESET)
        print(post_id_test)
        return False, e



    # PUT /provider/id
    if provider_id:
        try:
            provider_put_url = provider_put_url.format(id=provider_id)
            response = requests.put(provider_put_url, json={"name": "igor"})
            if response.status_code == 200:
                put_id_test =("Provider PUT Test :" + Formats.BOLD + Colors.GREEN + " Passed OK!"  + Colors.END + Formats.RESET)
                print (put_id_test)
            else:
                put_id_test =("Provider PUT Test :" + Formats.BOLD + Colors.RED + " FAILED!"  + Colors.END + Formats.RESET)
                print (put_id_test)
                return False, response
        except requests.RequestException as e:
            put_id_test =("Provider PUT Test :" + Formats.BOLD + Colors.RED + " FAILED!"  + Colors.END + Formats.RESET)
            print (put_id_test)
            return False, e



    #POST /rates
    try:
        response = requests.post(rates_url, files=files)
        if response.status_code == 201:
            post_rates = ("Rates POST Test :" + Formats.BOLD + Colors.GREEN + " Passed OK!"  + Colors.END + Formats.RESET)
            print(post_rates)
        else:
            post_rates = ("Rates POST Test :" + Formats.BOLD + Colors.RED + " FAILED!"  + Colors.END + Formats.RESET)
            print(post_rates)
            return False, response
    except requests.RequestException as e:
        post_rates =("Rates POST Test :" + Formats.BOLD + Colors.RED + " FAILED!"  + Colors.END + Formats.RESET)
        print(post_rates)
        return False, e



    # GET /rates
    try:
        response = requests.get(rates_url)
        if response.status_code == 200:
            get_rates = ("Rates GET Test :"  + Formats.BOLD + Colors.GREEN + " Passed OK!"  + Colors.END + Formats.RESET)
            print(get_rates)
        else:
            get_rates = ("Rates GET Test :" + Formats.BOLD + Colors.RED + " FAILED!"  + Colors.END + Formats.RESET)
            print(get_rates)
            return False, response
    except requests.RequestException as e:
        get_rates =("Rates GET Test :"  + Formats.BOLD + Colors.RED + " FAILED!"  + Colors.END + Formats.RESET)
        print(get_rates)
        return False, e


    # POST /truck
    try:
        truck_name = "T-14664"
        response = requests.post(truck_post_url, json={"id": truck_name, "provider_id": "10002"})
        if response.status_code == 201:
            truck_post = ("Truck POST Test :" + Formats.BOLD + Colors.GREEN + " Passed OK!" + Colors.END + Formats.RESET)
            print(truck_post)
            truck_id = response.json().get("status", None)
        else:
            truck_post = ("Truck POST Test :" + Formats.BOLD + Colors.RED + " FAILED!" + Colors.END + Formats.RESET)
            print(truck_post)
            return False, response
    except requests.RequestException as e:
        truck_post = ("Truck POST Test :" + Formats.BOLD + Colors.RED + " FAILED!" + Colors.END + Formats.RESET)
        print("Error:", e)
        return False, e

    # PUT /truck/{id}
    try:
        new_id = '10001'
        truck_put_url = truck_put_url.format(id=truck_name)
        response = requests.put(truck_put_url, json={"new_provider_id": new_id})
        if response.status_code == 200:
            put_id = ("Truck PUT Test :" + Formats.BOLD + Colors.GREEN + " Passed OK!" + Colors.END + Formats.RESET)
            print(put_id)
        else:
            put_id =("Truck PUT Test :" + Formats.BOLD + Colors.RED + " FAILED!" + Colors.END + Formats.RESET)
            print(put_id)
            return False, response
    except requests.RequestException as e:
        put_id =("Truck PUT Test :" + Formats.BOLD + Colors.RED + " FAILED!" + Colors.END + Formats.RESET)
        print(put_id)
        return False, e
    
    # GET /truck/<id>?from=t1&to=t2
    try:
        truck_get_url = truck_get_url.format(id=truck_name, t1="timestamp1", t2="timestamp2")
        response = requests.get(truck_get_url)
        if response.status_code == 200:
            get_id = ("Truck GET Test :" + Formats.BOLD + Colors.GREEN + " Passed OK!" + Colors.END + Formats.RESET)
            print(get_id)
        else:
            get_id = ("Truck GET Test :" + Formats.BOLD + Colors.RED + " FAILED!" + Colors.END + Formats.RESET)
            print(get_id)
            return False, response
    except requests.RequestException as e:
        get_id = ("Truck GET Test :" + Formats.BOLD + Colors.RED + " FAILED!" + Colors.END + Formats.RESET)
        print(get_id)
        return False, e


    # GET /bill/<id>?from=t1&to=t2
    try:
        bill_get_url = bill_get_url.format(id="10001", t1="timestamp1", t2="timestamp2")
        response = requests.get(bill_get_url)
        if response.status_code == 200:
            get_bill = ("Bill GET Test :" + Formats.BOLD + Colors.GREEN + " Passed OK!" + Colors.END + Formats.RESET)
            print(get_bill)
        else:
            get_bill = ("Bill GET Test :" + Formats.BOLD + Colors.RED + " FAILED!" + Colors.END + Formats.RESET)
            print(get_bill)
            return False, response
    except requests.RequestException as e:
        get_bill = ("Bill GET Test :" + Formats.BOLD + Colors.RED + " FAILED!" + Colors.END + Formats.RESET)
        print(get_bill)
        return False, e
    return True


if __name__ == '__main__':
    passed = main()
    if not passed:
        exit(1)
    else:
        exit(0)
